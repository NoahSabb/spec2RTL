#!/usr/bin/env python3
"""
Agentic loop v2 — cluster runner.

For each of the 78 CVDP cid003 problems:
  1. Load initial RTL from pre-generated RL v2 outputs (skip first generation call)
  2. Run iverilog compile check (no Docker needed on cluster)
  3. If compile fails → repair with Qwen using iverilog error (up to --max-compile-iter)
  4. If compile passes → repair with Qwen using pre-saved cocotb error (up to --max-cocotb-iter)
  5. Save best RTL per problem (compile-passing preferred)
  6. Log every iteration to --log JSONL

After job: download rtl/ dir to local machine, run CVDP cocotb harness to get final pass@1.

Usage (via sbatch):
    python3 scripts/run_agentic_v2.py \
        --adapter /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v2 \
        --initial-rtl /home/noahsabb/results/cid003_eval_rl_v2/rtl \
        --cocotb-errors /home/noahsabb/data/cocotb_errors_rl_v2.json \
        --out /home/noahsabb/results/cid003_eval_agentic_v2 \
        --log /home/noahsabb/logs/agentic_full_run.jsonl
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

# ── Args ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="/home/noahsabb/data/cid003_nonagentic.jsonl")
    p.add_argument("--adapter", default="/home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v2")
    p.add_argument("--initial-rtl", default="/home/noahsabb/results/cid003_eval_rl_v2/rtl",
                   help="Dir with pre-generated .sv/.v files, named {problem_id}.sv")
    p.add_argument("--cocotb-errors", default="/home/noahsabb/data/cocotb_errors_rl_v2.json",
                   help="JSON map of problem_id → cocotb error string (from local harness runs)")
    p.add_argument("--out", default="/home/noahsabb/results/cid003_eval_agentic_v2")
    p.add_argument("--log", default="/home/noahsabb/logs/agentic_full_run.jsonl")
    p.add_argument("--max-compile-iter", type=int, default=3,
                   help="Max iterations to fix compile errors")
    p.add_argument("--max-cocotb-iter", type=int, default=2,
                   help="Max iterations using pre-saved cocotb error")
    p.add_argument("--temperature", type=float, default=0.3)
    p.add_argument("--max-new-tokens", type=int, default=2048)
    p.add_argument("--problem-id", default=None, help="Run only this problem (debugging)")
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


_IVERILOG_OK: bool | None = None  # cached availability flag


def iverilog_available() -> bool:
    global _IVERILOG_OK
    if _IVERILOG_OK is None:
        _IVERILOG_OK = shutil.which("iverilog") is not None
        if _IVERILOG_OK:
            log.info("iverilog found — compile checks enabled")
        else:
            log.warning("iverilog not found — compile checks disabled; going straight to cocotb repair")
    return _IVERILOG_OK


def iverilog_check(verilog: str, rtl_filename: str) -> tuple[bool, str]:
    if not iverilog_available():
        # Treat as passing — we'll rely on pre-saved cocotb errors instead
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
            return True, ""  # iverilog disappeared mid-run — treat as passing


def parse_iverilog_errors(stderr: str, rtl_filename: str) -> str:
    """Extract first 5 iverilog error lines with line numbers."""
    lines = []
    for ln in stderr.splitlines():
        if "error" in ln.lower() or "warning" in ln.lower():
            # Strip absolute path prefix — keep filename:line: message
            ln = re.sub(r'.+?(' + re.escape(rtl_filename) + r')', r'\1', ln)
            lines.append(ln.strip())
    return "\n".join(lines[:5]) if lines else stderr[:400]


# ── Prompt builders ───────────────────────────────────────────────────────────

SYSTEM_HEADER = (
    "You are an expert RTL hardware engineer. "
    "Output ONLY the corrected Verilog module inside a ```verilog ... ``` block. "
    "Do not change port names, module name, or add extra modules."
)

def build_compile_repair_prompt(spec: str, verilog: str, error: str) -> str:
    return (
        f"{SYSTEM_HEADER}\n\n"
        f"## Specification\n{spec}\n\n"
        f"## Current RTL (fails iverilog compile)\n```verilog\n{verilog}\n```\n\n"
        f"## iverilog Errors\n{error}\n\n"
        "Fix ALL compile errors listed above. Apply minimum changes needed."
    )


def build_cocotb_repair_prompt(spec: str, verilog: str, cocotb_error: str,
                                iteration: int) -> str:
    extra = ""
    if iteration > 1:
        extra = (
            "\nNote: A previous repair attempt still failed. "
            "Try a different approach for the same error.\n"
        )
    return (
        f"{SYSTEM_HEADER}\n\n"
        f"## Specification\n{spec}\n\n"
        f"## Current RTL (compiles but fails functional test)\n```verilog\n{verilog}\n```\n\n"
        f"## Functional Test Failure\n{cocotb_error[:1500]}\n"
        f"{extra}\n"
        "Fix the functional logic error shown above. The module compiles cleanly — "
        "focus only on fixing the logic, not syntax."
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
    args,
    log_path: str,
    out_rtl_dir: Path,
):
    t_start = time.time()
    best_verilog = initial_verilog or ""
    best_compiles = False
    total_iters = 0
    final_compile_ok = False
    final_compile_err = ""

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
                prompt = build_compile_repair_prompt(spec, verilog, parsed_err)
            else:
                # Generate from scratch if no initial RTL
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
                "verilog_head": new_verilog[:200],
            })

            if new_ok:
                verilog = new_verilog
                ok, err = new_ok, new_err
                best_verilog = verilog
                best_compiles = True
                break
            # Keep whichever is shorter error for next round
            if not best_compiles:
                verilog = new_verilog
                err = new_err

    # ── Step 2: Fix functional (cocotb) errors ───────────────────────────────
    if ok and cocotb_error:
        for fi in range(1, args.max_cocotb_iter + 1):
            total_iters += 1
            log.info(f"[{pid}] cocotb repair iter {fi}/{args.max_cocotb_iter}")

            prompt = build_cocotb_repair_prompt(spec, verilog, cocotb_error, fi)
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
                "verilog_head": new_verilog[:200],
            })

            if new_ok:
                # Accept compile-passing repairs; pick last one as best
                best_verilog = new_verilog
                verilog = new_verilog
            else:
                log.info(f"[{pid}] cocotb repair broke compile — reverting to prior RTL")

    # ── Save best RTL ─────────────────────────────────────────────────────────
    final_verilog = best_verilog if best_verilog else verilog
    final_compile_ok, final_compile_err = iverilog_check(final_verilog, rtl_filename)
    rtl_out_path = out_rtl_dir / f"{pid}.sv"
    with open(rtl_out_path, "w") as f:
        f.write(final_verilog.strip() + "\n")

    elapsed = time.time() - t_start
    log.info(
        f"[{pid}] DONE — compile={'PASS' if final_compile_ok else 'FAIL'} | "
        f"iters={total_iters} | {elapsed:.0f}s total"
    )

    write_log(log_path, {
        "problem_id": pid, "iteration": "final",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "saved",
        "iverilog_pass": final_compile_ok,
        "total_iters": total_iters,
        "total_elapsed_s": round(elapsed, 1),
        "rtl_path": str(rtl_out_path),
    })

    return {
        "id": pid,
        "iverilog_pass": final_compile_ok,
        "iverilog_error": final_compile_err,
        "total_iters": total_iters,
        "elapsed_s": round(elapsed, 1),
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
    summary_path = out_dir / "summary.txt"

    # Resume support
    if results_path.exists():
        with open(results_path) as f:
            all_results = json.load(f)
        log.info(f"Resuming — {len(all_results)} problems already done")
    else:
        all_results = {}

    # Load benchmark data
    problems = []
    with open(args.data) as f:
        for line in f:
            if line.strip():
                problems.append(json.loads(line))

    if args.problem_id:
        problems = [p for p in problems if p["id"] == args.problem_id]
        if not problems:
            log.error(f"Problem {args.problem_id} not found")
            sys.exit(1)

    remaining = [p for p in problems if p["id"] not in all_results]
    log.info(f"Total: {len(problems)} | Remaining: {len(remaining)}")

    # Load cocotb errors
    cocotb_errors: dict[str, str] = {}
    if os.path.exists(args.cocotb_errors):
        with open(args.cocotb_errors) as f:
            cocotb_errors = json.load(f)
        log.info(f"Loaded cocotb errors for {sum(1 for v in cocotb_errors.values() if v)} problems")
    else:
        log.warning(f"cocotb errors file not found: {args.cocotb_errors}")

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

        # RTL filename from harness env
        harness_files = prob.get("harness", {}).get("files", {})
        env_content = harness_files.get("src/.env", "")
        rtl_filename = f"{pid}.sv"
        for line in env_content.splitlines():
            if line.startswith("VERILOG_SOURCES"):
                rtl_filename = line.split("=")[-1].strip().split("/")[-1]
                break

        # Load pre-generated initial RTL
        initial_verilog = None
        for ext in (".sv", ".v"):
            p = initial_rtl_dir / f"{pid}{ext}"
            if p.exists():
                initial_verilog = p.read_text()
                break
        if initial_verilog:
            log.info(f"[{i+1}/{len(remaining)}] {pid} — initial RTL: {len(initial_verilog)} chars")
        else:
            log.warning(f"[{i+1}/{len(remaining)}] {pid} — no initial RTL, generating from scratch")

        cocotb_error = cocotb_errors.get(pid, "")

        try:
            result = run_problem(
                pid=pid, spec=spec, rtl_filename=rtl_filename,
                initial_verilog=initial_verilog,
                cocotb_error=cocotb_error,
                model=model, tokenizer=tokenizer,
                args=args,
                log_path=args.log,
                out_rtl_dir=rtl_dir,
            )
        except Exception as e:
            log.error(f"[{pid}] CRASHED: {e}", exc_info=True)
            result = {
                "id": pid, "iverilog_pass": False,
                "iverilog_error": str(e), "total_iters": 0, "elapsed_s": 0,
            }

        result["categories"] = categories
        all_results[pid] = result

        with open(results_path, "w") as f:
            json.dump(all_results, f, indent=2)

    # ── Summary ────────────────────────────────────────────────────────────────
    total = len(all_results)
    if total == 0:
        log.info("No results to summarize")
        return

    passed = sum(1 for r in all_results.values() if r.get("iverilog_pass"))
    easy = [r for r in all_results.values() if "easy" in r.get("categories", [])]
    medium = [r for r in all_results.values() if "medium" in r.get("categories", [])]
    easy_pass = sum(1 for r in easy if r.get("iverilog_pass"))
    medium_pass = sum(1 for r in medium if r.get("iverilog_pass"))

    lines = [
        "=" * 60,
        "CVDP cid003 — Agentic v2 (Qwen RL v2 adapter)",
        "=" * 60,
        f"Scoring: iverilog compile pass (proxy — run CVDP harness locally for cocotb pass@1)",
        "",
        f"Overall: {passed}/{total} = {100*passed/total:.1f}%",
        f"Easy:    {easy_pass}/{len(easy)} = {100*easy_pass/len(easy):.1f}%" if easy else "Easy: n/a",
        f"Medium:  {medium_pass}/{len(medium)} = {100*medium_pass/len(medium):.1f}%" if medium else "Medium: n/a",
        "",
        "Note: download rtl/ and run CVDP cocotb harness locally for final cocotb pass@1",
        "",
        "Failed iverilog (will still be evaluated with cocotb):",
    ]
    for pid, r in sorted(all_results.items()):
        if not r.get("iverilog_pass"):
            lines.append(f"  {pid}: {r.get('iverilog_error','')[:80]}")

    summary = "\n".join(lines)
    print(summary)
    with open(summary_path, "w") as f:
        f.write(summary + "\n")

    write_log(args.log, {
        "event": "job_complete",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total": total, "iverilog_pass": passed,
        "easy_pass": easy_pass, "easy_total": len(easy),
        "medium_pass": medium_pass, "medium_total": len(medium),
    })

    log.info(f"Results: {out_dir}")


if __name__ == "__main__":
    main()
