#!/usr/bin/env python3
"""
Inference + iverilog scoring of fine-tuned Qwen2.5-Coder-32B-Instruct on CVDP cid003.

Runs every problem through the model (no agentic loop), scores iverilog compile,
and writes per-problem outputs + a summary JSON to RESULTS_DIR.

Usage (via sbatch — see run_cid003_eval.sbatch):
    python3 scripts/run_cid003_eval.py \
        --data /home/noahsabb/data/cid003_nonagentic.jsonl \
        --adapter /home/noahsabb/adapters/qwen32b-lora-35e941c1 \
        --out /home/noahsabb/results/cid003_eval
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"
SHARED_CACHE = "/home/_shared/models"

USER_TEMPLATE = (
    "Generate synthesizable Verilog RTL for the following specification.\n\n"
    "## Specification\n{spec}"
)


# ── Args ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="/home/noahsabb/data/cid003_nonagentic.jsonl")
    p.add_argument("--adapter", default="/home/noahsabb/adapters/qwen32b-lora-35e941c1",
                   help="Path to LoRA adapter dir (omit or pass empty string for base model)")
    p.add_argument("--out", default="/home/noahsabb/results/cid003_eval")
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--max-new-tokens", type=int, default=2048)
    p.add_argument("--problem-id", default=None, help="Run only this problem (for debugging)")
    return p.parse_args()


# ── Model loading ─────────────────────────────────────────────────────────────

def find_base_model() -> str:
    cache_name = "models--" + MODEL_ID.replace("/", "--")
    shared_hub = os.path.join(SHARED_CACHE, "hub", cache_name)
    if os.path.isdir(shared_hub):
        snapshots_dir = Path(shared_hub) / "snapshots"
        snapshots = sorted(snapshots_dir.iterdir())
        if snapshots:
            log.info(f"Base model found in shared cache: {snapshots[-1]}")
            return str(snapshots[-1])
    log.info(f"Base model not in shared cache; will download {MODEL_ID}")
    return MODEL_ID


def load_model_and_tokenizer(adapter_path: str | None):
    base_path = find_base_model()

    tokenizer = AutoTokenizer.from_pretrained(
        base_path,
        trust_remote_code=True,
        padding_side="left",  # left-padding for generation
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load to CPU first — no device_map means zero Accelerate dispatch hooks.
    # Accelerate hooks fire per-module (~448 linear layers in Qwen-32B), adding
    # ~1s of Python overhead per token even for a single-device map. Without
    # device_map, the model is a plain PyTorch model with no hooks at all.
    log.info("Loading base model in bf16 to CPU (no device_map, no Accelerate hooks)...")
    model = AutoModelForCausalLM.from_pretrained(
        base_path,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    log.info("Base model loaded to CPU.")

    if adapter_path:
        log.info(f"Loading LoRA adapter from {adapter_path} ...")
        model = PeftModel.from_pretrained(model, adapter_path)
        log.info("Merging LoRA weights on CPU...")
        model = model.merge_and_unload()
        log.info("Merge complete on CPU.")
    else:
        log.info("No adapter.")

    log.info("Moving merged model to cuda:0...")
    model = model.to("cuda:0")
    log.info("Model on cuda:0. No Accelerate hooks. Ready for inference.")

    model.eval()
    return model, tokenizer


# ── Inference ─────────────────────────────────────────────────────────────────

def build_prompt(spec: str, tokenizer) -> str:
    messages = [{"role": "user", "content": USER_TEMPLATE.format(spec=spec)}]
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )


def generate(model, tokenizer, prompt: str, temperature: float, max_new_tokens: int) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda:0")
    input_len = inputs["input_ids"].shape[-1]

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=(temperature > 0),
            pad_token_id=tokenizer.eos_token_id,
        )

    new_tokens = output_ids[0][input_len:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


# ── Verilog extraction ─────────────────────────────────────────────────────────

def extract_verilog(text: str) -> str:
    # Prefer fenced code block
    patterns = [
        r'```(?:verilog|systemverilog|sv)\n(.*?)```',
        r'```\n(.*?(?:module|endmodule).*?)```',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
    # Fall back to bare module...endmodule
    m = re.search(r'((?:^|\n)(?:`timescale\s+\S+|module\s+\w+).*?endmodule)', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Return full text if it contains verilog keywords (model may skip the fence)
    if "module" in text and "endmodule" in text:
        return text.strip()
    return text.strip()


# ── Scoring ────────────────────────────────────────────────────────────────────

def iverilog_compile(verilog_code: str, filename: str) -> tuple[bool, str]:
    """Compile generated Verilog with iverilog. Returns (success, stderr)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rtl_path = os.path.join(tmpdir, filename)
        with open(rtl_path, "w") as f:
            f.write(verilog_code)
        try:
            result = subprocess.run(
                ["iverilog", "-g2012", "-o", "/dev/null", rtl_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0, result.stderr.strip()
        except FileNotFoundError:
            return False, "iverilog not found"
        except subprocess.TimeoutExpired:
            return False, "iverilog compile timeout"


# ── Data loading ───────────────────────────────────────────────────────────────

def load_problems(path: str) -> list[dict]:
    problems = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                problems.append(json.loads(line))
    return problems


def parse_harness_env(harness_files: dict) -> dict:
    env_content = harness_files.get("src/.env", "")
    env = {}
    for line in env_content.strip().split("\n"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rtl_dir = out_dir / "rtl"
    rtl_dir.mkdir(exist_ok=True)

    results_path = out_dir / "results.json"
    summary_path = out_dir / "summary.txt"

    # Load any previous results (for resume)
    if results_path.exists():
        with open(results_path) as f:
            all_results = json.load(f)
        log.info(f"Resuming — {len(all_results)} problems already done")
    else:
        all_results = {}

    problems = load_problems(args.data)
    if args.problem_id:
        problems = [p for p in problems if p["id"] == args.problem_id]
        if not problems:
            log.error(f"Problem {args.problem_id} not found")
            sys.exit(1)

    remaining = [p for p in problems if p["id"] not in all_results]
    log.info(f"Total problems: {len(problems)} | Remaining: {len(remaining)}")

    if not remaining:
        log.info("All problems already evaluated — skipping model load")
        model = tokenizer = None
    else:
        model, tokenizer = load_model_and_tokenizer(args.adapter)

    # ── Per-problem loop ──────────────────────────────────────────────────────
    for i, prob in enumerate(remaining):
        pid = prob["id"]
        spec = prob["input"]["prompt"]
        harness_env = parse_harness_env(prob["harness"]["files"])
        rtl_filename = os.path.basename(harness_env.get("VERILOG_SOURCES", f"{pid}.sv").split()[0])
        categories = prob.get("categories", [])

        log.info(f"[{i+1}/{len(remaining)}] {pid}")

        t0 = time.time()
        try:
            prompt = build_prompt(spec, tokenizer)
            raw_output = generate(
                model, tokenizer, prompt,
                temperature=args.temperature,
                max_new_tokens=args.max_new_tokens,
            )
            elapsed = time.time() - t0
        except Exception as e:
            log.error(f"  Generation failed: {e}")
            all_results[pid] = {
                "id": pid,
                "categories": categories,
                "error": str(e),
                "iverilog_pass": False,
                "iverilog_error": "",
                "elapsed_s": time.time() - t0,
            }
            with open(results_path, "w") as f:
                json.dump(all_results, f, indent=2)
            continue

        verilog = extract_verilog(raw_output)

        # Save RTL file
        rtl_file = rtl_dir / f"{pid}.sv"
        with open(rtl_file, "w") as f:
            f.write(verilog)

        # Save raw model output
        with open(out_dir / f"{pid}_raw.txt", "w") as f:
            f.write(raw_output)

        # iverilog compile check
        compile_ok, compile_err = iverilog_compile(verilog, rtl_filename)
        status = "PASS" if compile_ok else "FAIL"
        log.info(f"  iverilog {status} | {elapsed:.1f}s | {len(verilog)} chars")
        if not compile_ok:
            log.info(f"  Error: {compile_err[:200]}")

        all_results[pid] = {
            "id": pid,
            "categories": categories,
            "iverilog_pass": compile_ok,
            "iverilog_error": compile_err,
            "elapsed_s": elapsed,
            "verilog_chars": len(verilog),
            "rtl_file": str(rtl_file),
        }

        # Checkpoint after each problem
        with open(results_path, "w") as f:
            json.dump(all_results, f, indent=2)

    # ── Summary ────────────────────────────────────────────────────────────────
    total = len(all_results)
    passed = sum(1 for r in all_results.values() if r.get("iverilog_pass"))
    easy = [r for r in all_results.values() if "easy" in r.get("categories", [])]
    medium = [r for r in all_results.values() if "medium" in r.get("categories", [])]
    easy_pass = sum(1 for r in easy if r.get("iverilog_pass"))
    medium_pass = sum(1 for r in medium if r.get("iverilog_pass"))

    model_desc = f"{MODEL_ID} + LoRA {args.adapter}" if args.adapter else f"{MODEL_ID} (base, no adapter)"
    lines = [
        "=" * 60,
        f"CVDP cid003 — {model_desc}",
        "=" * 60,
        f"Model:    {model_desc}",
        f"Scoring:  iverilog compile pass (proxy for pass@1)",
        f"Note:     Full cocotb pass@1 requires Docker + CVDP harness.",
        f"          Download rtl/ and run CVDP benchmark locally.",
        "",
        f"Overall:  {passed}/{total} = {100*passed/total:.1f}%",
        f"Easy:     {easy_pass}/{len(easy)} = {100*easy_pass/len(easy):.1f}%" if easy else "Easy: n/a",
        f"Medium:   {medium_pass}/{len(medium)} = {100*medium_pass/len(medium):.1f}%" if medium else "Medium: n/a",
        "",
        "Failed problems:",
    ]
    for pid, r in sorted(all_results.items()):
        if not r.get("iverilog_pass"):
            lines.append(f"  {pid}: {r.get('iverilog_error','')[:80]}")

    summary = "\n".join(lines)
    print(summary)
    with open(summary_path, "w") as f:
        f.write(summary + "\n")

    log.info(f"Results saved to {out_dir}")


if __name__ == "__main__":
    main()
