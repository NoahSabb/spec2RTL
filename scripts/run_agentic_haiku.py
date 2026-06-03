#!/usr/bin/env python3
"""
Agentic loop — Haiku as reflector, Qwen as generator.

Architecture:
  1. Claude Haiku analyzes the spec + failing RTL + error → returns targeted repair instruction
  2. Qwen uses that instruction to generate corrected Verilog

This isolates the reflection step to Claude while keeping Qwen for code generation.
Run with --reflector-model to switch models without code changes.

Usage (via sbatch):
    python3 scripts/run_agentic_haiku.py \
        --adapter /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v2 \
        --initial-rtl /home/noahsabb/results/cid003_eval_rl_v2/rtl \
        --cocotb-errors /home/noahsabb/data/cocotb_errors_rl_v2_test10.json \
        --data /home/noahsabb/data/cid003_test10.jsonl \
        --out /home/noahsabb/results/cid003_eval_agentic_exp_b \
        --log /home/noahsabb/logs/agentic_exp_b.jsonl
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import anthropic
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
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
HAIKU_INPUT_COST_PER_MTOK = 0.80
HAIKU_OUTPUT_COST_PER_MTOK = 4.00
SHARED_CACHE = "/home/_shared/models"


# ── Args ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="/home/noahsabb/data/cid003_test10.jsonl")
    p.add_argument("--adapter", default="/home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v2")
    p.add_argument("--initial-rtl", default="/home/noahsabb/results/cid003_eval_rl_v2/rtl")
    p.add_argument("--cocotb-errors", default="/home/noahsabb/data/cocotb_errors_rl_v2.json")
    p.add_argument("--out", default="/home/noahsabb/results/cid003_eval_agentic_exp_b")
    p.add_argument("--log", default="/home/noahsabb/logs/agentic_exp_b.jsonl")
    p.add_argument("--max-compile-iter", type=int, default=3)
    p.add_argument("--max-cocotb-iter", type=int, default=2)
    p.add_argument("--temperature", type=float, default=0.3)
    p.add_argument("--max-new-tokens", type=int, default=2048)
    p.add_argument("--problem-id", default=None)
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
    log.info(f"Base model not in shared cache; downloading {MODEL_ID}")
    return MODEL_ID


def load_model(adapter_path: str):
    base = find_base_model()
    tokenizer = AutoTokenizer.from_pretrained(
        base, trust_remote_code=True, padding_side="left"
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    log.info("Loading base model in bf16 to CPU (no device_map)...")
    model = AutoModelForCausalLM.from_pretrained(
        base, torch_dtype=torch.bfloat16, trust_remote_code=True, low_cpu_mem_usage=True
    )
    log.info("Merging RL v2 LoRA adapter on CPU...")
    model = PeftModel.from_pretrained(model, adapter_path)
    model = model.merge_and_unload()
    log.info("Moving merged model to cuda:0...")
    model = model.to("cuda:0")
    model.eval()

    alloc = torch.cuda.memory_allocated() / 1e9
    total = torch.cuda.get_device_properties(0).total_memory / 1e9
    log.info(f"Model on cuda:0 — allocated={alloc:.1f}GB / {total:.1f}GB total")
    return model, tokenizer


# ── Inference ─────────────────────────────────────────────────────────────────

def generate(model, tokenizer, user_text: str, temperature: float,
             max_new_tokens: int) -> str:
    messages = [{"role": "user", "content": user_text}]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda:0")
    input_len = inputs["input_ids"].shape[-1]
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=(temperature > 0),
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = out[0][input_len:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


# ── Claude reflector ──────────────────────────────────────────────────────────

def reflect_with_claude(
    client: anthropic.Anthropic,
    spec: str,
    verilog: str,
    error: str,
    error_type: str,
) -> tuple[str, int, int]:
    """Ask Claude Haiku to analyze the error and return a targeted repair instruction.

    Returns (instruction, input_tokens, output_tokens).
    Falls back to a generic instruction on API error.
    """
    system = (
        "You are an expert RTL hardware engineer reviewing a failing Verilog module. "
        "Analyze the error and provide a concise, specific repair instruction. "
        "Do NOT write Verilog code — only describe what needs to change and why. "
        "Be precise about signal names, logic operations, and root cause. "
        "Keep your response under 300 words."
    )

    if error_type == "compile":
        user = (
            f"## Specification\n{spec[:1500]}\n\n"
            f"## Current RTL (fails iverilog compile)\n```verilog\n{verilog[:3000]}\n```\n\n"
            f"## Compile Error\n{error}\n\n"
            "What specific change fixes this compile error? Be precise and brief."
        )
    else:
        user = (
            f"## Specification\n{spec[:1500]}\n\n"
            f"## Current RTL (compiles but fails functionally)\n```verilog\n{verilog[:3000]}\n```\n\n"
            f"## Test Failure\n{error[:1500]}\n\n"
            "What specific logic change fixes this functional error? Be precise and brief."
        )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        instruction = response.content[0].text
        in_tok = response.usage.input_tokens
        out_tok = response.usage.output_tokens
        log.info(f"  Claude Haiku: {in_tok} in / {out_tok} out tokens")
        return instruction, in_tok, out_tok
    except Exception as e:
        log.warning(f"  Claude API error (falling back to generic instruction): {e}")
        fallback = (
            "Review the error above carefully and fix the root cause. "
            "Ensure all signals are correctly declared and logic matches the specification."
        )
        return fallback, 0, 0


# ── Verilog helpers ───────────────────────────────────────────────────────────

def extract_verilog(text: str) -> str:
    for pat in [
        r'```(?:verilog|systemverilog|sv)\n(.*?)```',
        r'```\n(.*?(?:module|endmodule).*?)```',
    ]:
        m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
    m = re.search(
        r'((?:^|\n)(?:`timescale\s+\S+|module\s+\w+).*?endmodule)', text, re.DOTALL
    )
    if m:
        return m.group(1).strip()
    if "module" in text and "endmodule" in text:
        return text.strip()
    return text.strip()


_IVERILOG_OK: bool | None = None


def iverilog_available() -> bool:
    global _IVERILOG_OK
    if _IVERILOG_OK is None:
        _IVERILOG_OK = shutil.which("iverilog") is not None
        if _IVERILOG_OK:
            log.info("iverilog found — compile checks enabled")
        else:
            log.warning("iverilog not found — compile checks disabled")
    return _IVERILOG_OK


def iverilog_check(verilog: str, rtl_filename: str) -> tuple[bool, str]:
    if not iverilog_available():
        return True, ""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, rtl_filename)
        with open(p, "w") as f:
            f.write(verilog)
        try:
            r = subprocess.run(
                ["iverilog", "-g2012", "-o", "/dev/null", p],
                capture_output=True, text=True, timeout=30
            )
            return r.returncode == 0, r.stderr.strip()
        except FileNotFoundError:
            return True, ""


def parse_iverilog_errors(stderr: str, rtl_filename: str) -> str:
    lines = []
    for ln in stderr.splitlines():
        if "error" in ln.lower() or "warning" in ln.lower():
            ln = re.sub(r'.+?(' + re.escape(rtl_filename) + r')', r'\1', ln)
            lines.append(ln.strip())
    return "\n".join(lines[:5]) if lines else stderr[:400]


# ── Prompt builders ───────────────────────────────────────────────────────────

SYSTEM_HEADER = (
    "You are an expert RTL hardware engineer. "
    "Output ONLY the corrected Verilog module inside a ```verilog ... ``` block. "
    "Do not change port names, module name, or add extra modules."
)


def build_guided_repair_prompt(spec: str, verilog: str, instruction: str) -> str:
    return (
        f"{SYSTEM_HEADER}\n\n"
        f"## Specification\n{spec}\n\n"
        f"## Current RTL\n```verilog\n{verilog}\n```\n\n"
        f"## Required Fix\n{instruction}\n\n"
        "Apply the fix above. Return only corrected Verilog in a ```verilog ... ``` block."
    )


# ── Logging ───────────────────────────────────────────────────────────────────

def write_log(log_path: str, entry: dict):
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log.warning(f"Log write failed: {e}")


# ── Per-problem agentic loop ──────────────────────────────────────────────────

def run_problem(
    pid: str, spec: str, rtl_filename: str,
    initial_verilog: str | None,
    cocotb_error: str,
    model, tokenizer,
    claude_client: anthropic.Anthropic,
    args,
    log_path: str,
    out_rtl_dir: Path,
) -> dict:
    t_start = time.time()
    best_verilog = initial_verilog or ""
    best_compiles = False
    total_iters = 0
    total_claude_in_tok = 0
    total_claude_out_tok = 0

    # ── Step 0: Check initial RTL ────────────────────────────────────────────
    if initial_verilog:
        ok, err = iverilog_check(initial_verilog, rtl_filename)
        best_compiles = ok
        log.info(f"[{pid}] initial iverilog: {'PASS' if ok else 'FAIL'}")
        write_log(log_path, {
            "problem_id": pid, "iteration": 0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "initial_check",
            "iverilog_pass": ok,
            "iverilog_error": err[:300] if not ok else "",
            "verilog_chars": len(initial_verilog),
        })
    else:
        ok, err = False, "no initial RTL provided"
        log.warning(f"[{pid}] no initial RTL — will generate from scratch")

    verilog = initial_verilog or ""

    # ── Step 1: Fix compile errors ───────────────────────────────────────────
    if not ok:
        for ci in range(1, args.max_compile_iter + 1):
            total_iters += 1
            log.info(f"[{pid}] compile repair iter {ci}/{args.max_compile_iter}")

            if verilog:
                parsed_err = parse_iverilog_errors(err, rtl_filename)
                instruction, in_tok, out_tok = reflect_with_claude(
                    claude_client, spec, verilog, parsed_err, "compile"
                )
                total_claude_in_tok += in_tok
                total_claude_out_tok += out_tok
                prompt = build_guided_repair_prompt(spec, verilog, instruction)
            else:
                instruction = ""
                prompt = (
                    f"Generate synthesizable Verilog RTL for the following specification.\n\n"
                    f"## Specification\n{spec}"
                )

            t0 = time.time()
            raw = generate(model, tokenizer, prompt, args.temperature, args.max_new_tokens)
            gen_s = time.time() - t0
            new_verilog = extract_verilog(raw)

            new_ok, new_err = iverilog_check(new_verilog, rtl_filename)
            log.info(
                f"[{pid}] compile iter {ci}: {'PASS' if new_ok else 'FAIL'} | "
                f"{gen_s:.0f}s | {len(new_verilog)} chars"
            )

            write_log(log_path, {
                "problem_id": pid, "iteration": total_iters,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "compile_repair",
                "compile_iter": ci,
                "iverilog_pass": new_ok,
                "iverilog_error": new_err[:300] if not new_ok else "",
                "verilog_chars": len(new_verilog),
                "gen_s": round(gen_s, 1),
                "claude_instruction": instruction[:200] if instruction else "",
                "claude_in_tok": in_tok,
                "claude_out_tok": out_tok,
                "verilog_head": new_verilog[:200],
            })

            if new_ok:
                verilog = new_verilog
                ok, err = new_ok, new_err
                best_verilog = verilog
                best_compiles = True
                break
            if not best_compiles:
                verilog = new_verilog
                err = new_err

    # ── Step 2: Fix functional (cocotb) errors ───────────────────────────────
    if ok and cocotb_error:
        for fi in range(1, args.max_cocotb_iter + 1):
            total_iters += 1
            log.info(f"[{pid}] cocotb repair iter {fi}/{args.max_cocotb_iter}")

            instruction, in_tok, out_tok = reflect_with_claude(
                claude_client, spec, verilog, cocotb_error[:1500], "cocotb"
            )
            total_claude_in_tok += in_tok
            total_claude_out_tok += out_tok
            prompt = build_guided_repair_prompt(spec, verilog, instruction)

            t0 = time.time()
            raw = generate(model, tokenizer, prompt, args.temperature, args.max_new_tokens)
            gen_s = time.time() - t0
            new_verilog = extract_verilog(raw)

            new_ok, new_err = iverilog_check(new_verilog, rtl_filename)
            log.info(
                f"[{pid}] cocotb iter {fi}: iverilog={'PASS' if new_ok else 'FAIL'} | "
                f"{gen_s:.0f}s | {len(new_verilog)} chars"
            )

            write_log(log_path, {
                "problem_id": pid, "iteration": total_iters,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "cocotb_repair",
                "cocotb_iter": fi,
                "iverilog_pass": new_ok,
                "iverilog_error": new_err[:300] if not new_ok else "",
                "verilog_chars": len(new_verilog),
                "gen_s": round(gen_s, 1),
                "claude_instruction": instruction[:200],
                "claude_in_tok": in_tok,
                "claude_out_tok": out_tok,
                "verilog_head": new_verilog[:200],
            })

            if new_ok:
                best_verilog = new_verilog
                verilog = new_verilog
            else:
                log.info(f"[{pid}] cocotb repair broke compile — reverting")

    # ── Save best RTL ─────────────────────────────────────────────────────────
    final_verilog = best_verilog if best_verilog else verilog
    final_compile_ok, final_compile_err = iverilog_check(final_verilog, rtl_filename)
    rtl_out_path = out_rtl_dir / f"{pid}.sv"
    with open(rtl_out_path, "w") as f:
        f.write(final_verilog.strip() + "\n")

    elapsed = time.time() - t_start
    log.info(
        f"[{pid}] DONE — compile={'PASS' if final_compile_ok else 'FAIL'} | "
        f"iters={total_iters} | {elapsed:.0f}s total | "
        f"claude={total_claude_in_tok}in/{total_claude_out_tok}out tok"
    )

    write_log(log_path, {
        "problem_id": pid, "iteration": "final",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "saved",
        "iverilog_pass": final_compile_ok,
        "total_iters": total_iters,
        "total_elapsed_s": round(elapsed, 1),
        "total_claude_in_tok": total_claude_in_tok,
        "total_claude_out_tok": total_claude_out_tok,
        "rtl_path": str(rtl_out_path),
    })

    return {
        "id": pid,
        "iverilog_pass": final_compile_ok,
        "iverilog_error": final_compile_err,
        "total_iters": total_iters,
        "elapsed_s": round(elapsed, 1),
        "claude_in_tok": total_claude_in_tok,
        "claude_out_tok": total_claude_out_tok,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rtl_dir = out_dir / "rtl"
    rtl_dir.mkdir(exist_ok=True)
    Path(args.log).parent.mkdir(parents=True, exist_ok=True)

    results_path = out_dir / "results.json"

    if results_path.exists():
        with open(results_path) as f:
            all_results = json.load(f)
        log.info(f"Resuming — {len(all_results)} problems already done")
    else:
        all_results = {}

    problems = []
    with open(args.data) as f:
        for line in f:
            if line.strip():
                problems.append(json.loads(line))

    if args.problem_id:
        problems = [p for p in problems if p["id"] == args.problem_id]

    remaining = [p for p in problems if p["id"] not in all_results]
    log.info(f"Total: {len(problems)} | Remaining: {len(remaining)}")

    cocotb_errors: dict[str, str] = {}
    if os.path.exists(args.cocotb_errors):
        with open(args.cocotb_errors) as f:
            cocotb_errors = json.load(f)
        log.info(f"Loaded cocotb errors for {sum(1 for v in cocotb_errors.values() if v)} problems")

    claude_client = anthropic.Anthropic()
    log.info(f"Claude reflector: {CLAUDE_MODEL}")

    if not remaining:
        log.info("All problems done — skipping model load")
        model = tokenizer = None
    else:
        model, tokenizer = load_model(args.adapter)

    initial_rtl_dir = Path(args.initial_rtl)

    for i, prob in enumerate(remaining):
        pid = prob["id"]
        spec = prob["input"]["prompt"]
        categories = prob.get("categories", [])

        harness_files = prob.get("harness", {}).get("files", {})
        env_content = harness_files.get("src/.env", "")
        rtl_filename = f"{pid}.sv"
        for line in env_content.splitlines():
            if line.startswith("VERILOG_SOURCES"):
                rtl_filename = line.split("=")[-1].strip().split("/")[-1]
                break

        initial_verilog = None
        for ext in (".sv", ".v"):
            p = initial_rtl_dir / f"{pid}{ext}"
            if p.exists():
                initial_verilog = p.read_text()
                break
        if not initial_verilog:
            log.warning(f"[{i+1}/{len(remaining)}] {pid} — no initial RTL")

        cocotb_error = cocotb_errors.get(pid, "")

        try:
            result = run_problem(
                pid=pid, spec=spec, rtl_filename=rtl_filename,
                initial_verilog=initial_verilog,
                cocotb_error=cocotb_error,
                model=model, tokenizer=tokenizer,
                claude_client=claude_client,
                args=args,
                log_path=args.log,
                out_rtl_dir=rtl_dir,
            )
        except Exception as e:
            log.error(f"[{pid}] CRASHED: {e}", exc_info=True)
            result = {
                "id": pid, "iverilog_pass": False,
                "iverilog_error": str(e), "total_iters": 0, "elapsed_s": 0,
                "claude_in_tok": 0, "claude_out_tok": 0,
            }

        result["categories"] = categories
        all_results[pid] = result

        with open(results_path, "w") as f:
            json.dump(all_results, f, indent=2)

    # ── Summary ────────────────────────────────────────────────────────────────
    total = len(all_results)
    if total == 0:
        return

    passed = sum(1 for r in all_results.values() if r.get("iverilog_pass"))
    easy = [r for r in all_results.values() if "easy" in r.get("categories", [])]
    medium = [r for r in all_results.values() if "medium" in r.get("categories", [])]
    easy_pass = sum(1 for r in easy if r.get("iverilog_pass"))
    medium_pass = sum(1 for r in medium if r.get("iverilog_pass"))

    total_in_tok = sum(r.get("claude_in_tok", 0) for r in all_results.values())
    total_out_tok = sum(r.get("claude_out_tok", 0) for r in all_results.values())
    cost_10 = (total_in_tok / 1e6 * HAIKU_INPUT_COST_PER_MTOK +
               total_out_tok / 1e6 * HAIKU_OUTPUT_COST_PER_MTOK)
    cost_78 = cost_10 * (78 / total) if total > 0 else 0

    total_elapsed = sum(r.get("elapsed_s", 0) for r in all_results.values())
    avg_elapsed = total_elapsed / total if total > 0 else 0

    lines = [
        "=" * 70,
        f"CVDP cid003 — Agentic Exp B (Haiku reflector + Qwen generator)",
        "=" * 70,
        f"Scoring: iverilog compile pass (run CVDP harness for cocotb pass@1)",
        "",
        f"Overall: {passed}/{total} = {100*passed/total:.1f}%",
        f"Easy:    {easy_pass}/{len(easy)}" if easy else "Easy: n/a",
        f"Medium:  {medium_pass}/{len(medium)}" if medium else "Medium: n/a",
        "",
        f"Timing:  {total_elapsed:.0f}s total | {avg_elapsed:.0f}s avg/problem",
        "",
        f"Claude Haiku API usage ({total} problems):",
        f"  Input tokens:  {total_in_tok:,}",
        f"  Output tokens: {total_out_tok:,}",
        f"  Cost ({total} problems): ${cost_10:.4f}",
        f"  Est. cost (78 problems): ${cost_78:.3f}",
        "",
        "Note: download rtl/ and run CVDP cocotb harness for final cocotb pass@1",
    ]
    summary = "\n".join(lines)
    print(summary)
    with open(out_dir / "summary.txt", "w") as f:
        f.write(summary + "\n")

    write_log(args.log, {
        "event": "job_complete",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "reflector": CLAUDE_MODEL,
        "total": total, "iverilog_pass": passed,
        "easy_pass": easy_pass, "easy_total": len(easy),
        "medium_pass": medium_pass, "medium_total": len(medium),
        "total_elapsed_s": total_elapsed,
        "avg_elapsed_s": round(avg_elapsed, 1),
        "total_claude_in_tok": total_in_tok,
        "total_claude_out_tok": total_out_tok,
        "cost_10_problems": round(cost_10, 5),
        "cost_78_problems_est": round(cost_78, 3),
    })


if __name__ == "__main__":
    main()
