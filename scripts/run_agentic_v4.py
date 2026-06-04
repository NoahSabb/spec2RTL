#!/usr/bin/env python3
"""
Agentic loop v4 — LOCAL test version.

Key improvements over v3:
  1. History-aware reflection: show Sonnet last 2 iterations (diagnosis, fix, result)
     so it can avoid repeating failed approaches
  2. More iterations: 5 cocotb (was 3) — catches "almost there" problems like events_to_apb
  3. Fresh-start trigger: after 3 failed cocotb iterations, generate from scratch
     (instead of continued incremental repair which can oscillate)
  4. All v3 improvements retained: diagnosis step, live harness, full error context

Usage:
    python3 scripts/run_agentic_v4.py \
        --problems cvdp_copilot_GFCM_0001 cvdp_copilot_morse_code_0001 ... \
        --bench-dir cvdp_benchmark/work_qwen32b_lora_rl_v2 \
        --initial-rtl ~/Downloads/cid003_eval_rl_v2 \
        --out logs/cycle1_v3 \
        --log logs/agentic_improvement_cycle.jsonl
"""

import argparse
import glob
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
from pathlib import Path as _Path

# Load API key from .env file if not already set
def _load_env_key():
    for env_path in [
        _Path(__file__).parent.parent / ".env",
        _Path(__file__).parent.parent / "cvdp_benchmark/.env",
    ]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY"):
                    key = line.split("=", 1)[-1].strip().strip('"').strip("'")
                    if key:
                        os.environ.setdefault("ANTHROPIC_API_KEY", key)
                        return
_load_env_key()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-sonnet-4-6"
SONNET_INPUT_COST_PER_MTOK = 3.00
SONNET_OUTPUT_COST_PER_MTOK = 15.00

DATA_FILE = Path(__file__).parent.parent / "data/cid003_nonagentic.jsonl"


# ── Args ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--problems", nargs="+", default=None,
                   help="Problem IDs to run (default: all 8 cycle-1 targets)")
    p.add_argument("--bench-dir",
                   default="cvdp_benchmark/work_qwen32b_lora_rl_v2")
    p.add_argument("--initial-rtl",
                   default=os.path.expanduser("~/Downloads/cid003_eval_rl_v2"))
    p.add_argument("--out", default="logs/cycle1_v3")
    p.add_argument("--log", default="logs/agentic_improvement_cycle.jsonl")
    p.add_argument("--max-compile-iter", type=int, default=3)
    p.add_argument("--max-cocotb-iter", type=int, default=5)
    p.add_argument("--temperature", type=float, default=0.3)
    p.add_argument("--cycle", type=int, default=1)
    p.add_argument("--script-version", default="v4")
    return p.parse_args()


# ── Data loading ──────────────────────────────────────────────────────────────

def load_problems(data_file: Path) -> dict:
    probs = {}
    with open(data_file) as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                probs[d["id"]] = d
    return probs


# ── Harness runner ────────────────────────────────────────────────────────────

def run_harness(verilog: str, harness_dir: str, rtl_filename: str,
                timeout: int = 180) -> dict:
    """Run the CVDP Docker harness for one problem. Returns pass/fail + output."""
    # Resolve to absolute paths to avoid cwd-relative confusion
    harness_dir_abs = os.path.abspath(harness_dir)
    rtl_path = os.path.join(harness_dir_abs, "rtl", rtl_filename)

    # Back up original RTL
    orig = None
    if os.path.exists(rtl_path):
        orig = open(rtl_path).read()

    try:
        os.makedirs(os.path.dirname(rtl_path), exist_ok=True)
        with open(rtl_path, "w") as f:
            f.write(verilog.strip() + "\n")

        scripts = glob.glob(os.path.join(harness_dir_abs, "run_docker_harness_*.sh"))
        if not scripts:
            return {"passed": False, "output": "No harness script found",
                    "errors": "", "stage": "harness"}

        r = subprocess.run(
            ["bash", scripts[0]],
            capture_output=True, text=True, timeout=timeout,
            cwd=harness_dir_abs,
        )
        output = r.stdout + r.stderr

        # Check for passing pytest summary
        passed = (r.returncode == 0 and
                  bool(re.search(r'\d+ passed', output)) and
                  not bool(re.search(r'\d+ failed', output)))

        return {"passed": passed, "output": output, "errors": r.stderr,
                "returncode": r.returncode, "stage": "harness"}

    except subprocess.TimeoutExpired:
        return {"passed": False, "output": "TIMEOUT", "errors": "Timeout", "stage": "harness"}
    except Exception as e:
        return {"passed": False, "output": str(e), "errors": str(e), "stage": "harness"}
    finally:
        # Restore original RTL
        if orig is not None and os.path.exists(rtl_path):
            try:
                with open(rtl_path, "w") as f:
                    f.write(orig)
            except Exception:
                pass


def iverilog_check(verilog: str, rtl_filename: str) -> tuple[bool, str]:
    if not shutil.which("iverilog"):
        return True, ""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, rtl_filename)
        with open(p, "w") as f:
            f.write(verilog)
        r = subprocess.run(
            ["iverilog", "-g2012", "-o", "/dev/null", p],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0, r.stderr.strip()


# ── Error parsing ─────────────────────────────────────────────────────────────

def parse_harness_output(output: str) -> dict:
    """Extract structured error info from harness/cocotb output."""
    lines = output.splitlines()

    failed_tests = re.findall(r'FAILED\s+[\w./]+::([\w]+)', output)

    # Value mismatch patterns
    mismatches = []
    for m in re.finditer(
        r'(?:expected|Expected)\s+([^\n,]{1,80}),?\s*(?:got|got:)\s*([^\n]{1,80})',
        output, re.IGNORECASE
    ):
        mismatches.append({"expected": m.group(1).strip(), "actual": m.group(2).strip()})

    # AssertionError lines
    assertion_lines = []
    for i, ln in enumerate(lines):
        if "AssertionError" in ln or ("assert " in ln.lower() and "==" in ln):
            # grab surrounding context
            ctx = lines[max(0, i-2):i+3]
            assertion_lines.append("\n".join(ctx))
        if len(assertion_lines) >= 4:
            break

    # Timing warnings
    timing_warnings = [ln.strip() for ln in lines
                       if "WARNING" in ln and any(
                           kw in ln.lower() for kw in
                           ["glitch", "setup", "hold", "timing", "clock"]
                       )][:3]

    return {
        "failed_tests": list(dict.fromkeys(failed_tests))[:5],
        "mismatches": mismatches[:5],
        "assertion_context": assertion_lines,
        "timing_warnings": timing_warnings,
        "raw": output[-3000:],  # last 3K chars
    }


def format_error_for_reflector(parsed: dict, full_output: str) -> str:
    """Render parsed error into a compact block for the reflector."""
    parts = []

    if parsed["failed_tests"]:
        parts.append("Failed tests: " + ", ".join(parsed["failed_tests"]))

    if parsed["mismatches"]:
        parts.append("Value mismatches (expected vs actual):")
        for m in parsed["mismatches"]:
            parts.append(f"  expected: {m['expected']}")
            parts.append(f"  actual:   {m['actual']}")

    if parsed["assertion_context"]:
        parts.append("Assertion failures (with context):")
        for ctx in parsed["assertion_context"]:
            parts.append("  " + ctx.replace("\n", "\n  "))

    if parsed["timing_warnings"]:
        parts.append("Timing warnings:")
        for w in parsed["timing_warnings"]:
            parts.append(f"  {w}")

    if not parts:
        # Fall back to raw output
        parts.append("Full harness output (last 2500 chars):")
        parts.append(full_output[-2500:])
    else:
        # Append abbreviated raw for context
        parts.append("\nRaw output tail (last 1000 chars):")
        parts.append(full_output[-1000:])

    return "\n".join(parts)


# ── Reflector (two-step: diagnose + fix) ──────────────────────────────────────

REFLECTOR_SYSTEM = """You are an expert RTL hardware engineer reviewing a failing Verilog module.

Your task: analyze the failure and provide a SPECIFIC repair instruction.

Key rules:
- Do NOT write Verilog code — only describe what to change and why
- Be PRECISE about signal names, bit positions, and logic expressions
- Identify ROOT CAUSE not just symptoms

Common Verilog/cocotb failure patterns to consider:
- Bit/encoding order: MSB vs LSB, byte order, bit-reversal in output encoding
- Reset initialization: X/Z states from uninitialized regs at t=0
- Off-by-one: fence post errors in counters, loop bounds, state transitions
- Missing cases: incomplete case statements causing X propagation
- Async vs sync reset: wrong sensitivity list causing RTL/testbench mismatch
- Clock gating: combinational feedback into clocked logic causing glitches
- Timing: output registered when testbench expects combinational (or vice versa)
- Overflow/underflow: unsigned vs signed, bit-width truncation
"""


def reflect_with_sonnet_v4(
    client: anthropic.Anthropic,
    spec: str,
    verilog: str,
    error_block: str,
    error_type: str,
    history: list[dict] | None = None,
) -> tuple[str, str, int, int]:
    """
    History-aware two-step reflection.
    history: list of {diagnosis, fix_instruction, result} from previous iterations.

    Returns (diagnosis, fix_instruction, input_tokens, output_tokens).
    """
    history_block = ""
    if history:
        hist_lines = ["## Previous Repair Attempts (all FAILED — avoid repeating these)"]
        for i, h in enumerate(history[-2:], 1):  # show last 2 attempts
            hist_lines.append(f"\n### Attempt {i}")
            hist_lines.append(f"Diagnosis: {h.get('diagnosis', '')[:200]}")
            hist_lines.append(f"Fix tried: {h.get('fix_instruction', '')[:200]}")
            hist_lines.append(f"Result: still failing ({h.get('failed_tests', [])})")
        history_block = "\n".join(hist_lines) + "\n\n"

    if error_type == "compile":
        user = (
            f"## Specification\n{spec}\n\n"
            f"## Current RTL (fails iverilog compile)\n```verilog\n{verilog}\n```\n\n"
            f"## Compile Error\n{error_block}\n\n"
            f"{history_block}"
            "Respond in EXACTLY this format:\n\n"
            "## Diagnosis\n"
            "One sentence: what specific syntax/semantic error prevents compilation.\n\n"
            "## Fix Instruction\n"
            "Precise change: name exact line/expression to fix and what to change it to."
        )
    else:
        user = (
            f"## Specification\n{spec}\n\n"
            f"## Current RTL (compiles, fails functionally)\n```verilog\n{verilog}\n```\n\n"
            f"## Test Failure Details\n{error_block}\n\n"
            f"{history_block}"
            "Respond in EXACTLY this format:\n\n"
            "## Diagnosis\n"
            "One sentence: what specific signal/logic/encoding is wrong and why.\n\n"
            "## Fix Instruction\n"
            "Precise RTL change: name exact signal/always-block/expression and what to change it to.\n"
            "If previous fixes oscillated, take a DIFFERENT approach (e.g., rewrite the key block)."
        )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=700,
            system=REFLECTOR_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        text = response.content[0].text
        in_tok = response.usage.input_tokens
        out_tok = response.usage.output_tokens

        diag_m = re.search(r'## Diagnosis\s*\n(.+?)(?=## Fix|$)', text, re.DOTALL)
        fix_m = re.search(r'## Fix Instruction\s*\n(.+?)$', text, re.DOTALL)

        diagnosis = diag_m.group(1).strip() if diag_m else ""
        fix_instruction = fix_m.group(1).strip() if fix_m else text.strip()

        log.info(f"  [Sonnet diagnosis]: {diagnosis[:120]}")
        log.info(f"  [Sonnet fix]: {fix_instruction[:120]}")
        return diagnosis, fix_instruction, in_tok, out_tok

    except Exception as e:
        log.warning(f"  Claude API error: {e}")
        return "", "Review the error and fix the root cause.", 0, 0


# ── Generator (Claude Sonnet as generator for local test) ─────────────────────

GENERATOR_SYSTEM = (
    "You are an expert RTL hardware engineer. "
    "Output ONLY the complete, corrected Verilog module inside a ```verilog ... ``` block. "
    "Do NOT change any port names or the module name. "
    "Do NOT add explanations or comments outside the code block."
)


def generate_with_claude(client: anthropic.Anthropic, prompt: str,
                         temperature: float = 0.3) -> tuple[str, int, int]:
    """Generate RTL using Claude Sonnet."""
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=GENERATOR_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        text = response.content[0].text
        in_tok = response.usage.input_tokens
        out_tok = response.usage.output_tokens
        return text, in_tok, out_tok
    except Exception as e:
        log.error(f"Generation API error: {e}")
        return "", 0, 0


def extract_verilog(text: str) -> str:
    for pat in [
        r'```(?:verilog|systemverilog|sv)\n(.*?)```',
        r'```\n(.*?(?:module|endmodule).*?)```',
    ]:
        m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
    if "module" in text and "endmodule" in text:
        return text.strip()
    return text.strip()


def build_repair_prompt(spec: str, verilog: str, diagnosis: str,
                        fix_instruction: str) -> str:
    return (
        f"## Specification\n{spec}\n\n"
        f"## Current RTL (to be repaired)\n```verilog\n{verilog}\n```\n\n"
        f"## Diagnosed Bug\n{diagnosis}\n\n"
        f"## Required Fix\n{fix_instruction}\n\n"
        "Apply the fix above. Return ONLY the corrected Verilog in a ```verilog ... ``` block."
    )


# ── Logging ───────────────────────────────────────────────────────────────────

def write_log(path: str, entry: dict):
    try:
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log.warning(f"Log write failed: {e}")


# ── Per-problem loop ──────────────────────────────────────────────────────────

def run_problem(
    pid: str, prob_data: dict, initial_verilog: str | None,
    bench_dir: str, client: anthropic.Anthropic,
    args, log_path: str, out_dir: Path,
) -> dict:
    t_start = time.time()

    # Get harness dir and RTL filename
    parts = pid.rsplit("_", 1)
    base = parts[0]
    num = int(parts[1])
    harness_dir = os.path.join(bench_dir, base, "harness", str(num))

    # Get RTL filename from .env
    rtl_filename = f"{pid}.sv"
    env_content = (prob_data.get("harness", {}).get("files", {}).get("src/.env", ""))
    for line in env_content.splitlines():
        if line.startswith("VERILOG_SOURCES"):
            rtl_filename = line.split("=")[-1].strip().split("/")[-1]
            break

    spec = prob_data["input"]["prompt"]
    cats = prob_data.get("categories", [])

    total_iters = 0
    total_gen_in_tok = 0
    total_gen_out_tok = 0
    total_ref_in_tok = 0
    total_ref_out_tok = 0

    verilog = initial_verilog or ""
    best_verilog = verilog
    passed = False

    log.info(f"\n{'='*60}")
    log.info(f"[{pid}] Starting (harness_dir exists: {os.path.isdir(harness_dir)})")
    log.info(f"  RTL filename: {rtl_filename}")
    log.info(f"  Initial RTL: {'yes' if initial_verilog else 'none'} ({len(verilog)} chars)")

    # ── Step 0: Check initial RTL ────────────────────────────────────────────
    if verilog:
        compile_ok, compile_err = iverilog_check(verilog, rtl_filename)
        write_log(log_path, {
            "cycle": args.cycle, "script_version": args.script_version,
            "problem_id": pid, "iteration": 0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "initial_check",
            "iverilog_pass": compile_ok,
            "iverilog_error": compile_err[:200] if not compile_ok else "",
        })
        log.info(f"[{pid}] Initial iverilog: {'PASS' if compile_ok else 'FAIL'}")

        if compile_ok and os.path.isdir(harness_dir):
            log.info(f"[{pid}] Running initial harness...")
            t0 = time.time()
            harness_result = run_harness(verilog, harness_dir, rtl_filename)
            harness_s = time.time() - t0
            passed = harness_result["passed"]
            log.info(f"[{pid}] Initial harness: {'PASS' if passed else 'FAIL'} ({harness_s:.0f}s)")
            write_log(log_path, {
                "cycle": args.cycle, "script_version": args.script_version,
                "problem_id": pid, "iteration": 0,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "initial_harness",
                "passed": passed,
                "harness_s": round(harness_s, 1),
                "output_tail": harness_result["output"][-500:],
            })
            if passed:
                best_verilog = verilog
    else:
        compile_ok = False
        compile_err = "no initial RTL"

    # ── Step 1: Compile repair loop ───────────────────────────────────────────
    if not compile_ok:
        for ci in range(1, args.max_compile_iter + 1):
            total_iters += 1
            log.info(f"[{pid}] Compile repair iter {ci}/{args.max_compile_iter}")

            if verilog:
                diagnosis, fix_inst, ref_in, ref_out = reflect_with_sonnet_v4(
                    client, spec, verilog,
                    parse_iverilog_errors(compile_err, rtl_filename),
                    "compile",
                )
                total_ref_in_tok += ref_in
                total_ref_out_tok += ref_out
                prompt = build_repair_prompt(spec, verilog, diagnosis, fix_inst)
            else:
                diagnosis, fix_inst = "", ""
                prompt = (
                    "Generate synthesizable Verilog RTL for the following specification.\n\n"
                    f"## Specification\n{spec}"
                )

            raw, gen_in, gen_out = generate_with_claude(client, prompt, args.temperature)
            total_gen_in_tok += gen_in
            total_gen_out_tok += gen_out
            new_verilog = extract_verilog(raw)

            new_ok, new_err = iverilog_check(new_verilog, rtl_filename)
            log.info(f"[{pid}] Compile iter {ci}: {'PASS' if new_ok else 'FAIL'}")

            write_log(log_path, {
                "cycle": args.cycle, "script_version": args.script_version,
                "problem_id": pid, "iteration": total_iters,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "compile_repair",
                "compile_iter": ci,
                "iverilog_pass": new_ok,
                "diagnosis": diagnosis[:300],
                "fix_instruction": fix_inst[:300],
                "verilog_chars": len(new_verilog),
                "ref_in_tok": ref_in, "ref_out_tok": ref_out,
                "gen_in_tok": gen_in, "gen_out_tok": gen_out,
            })

            if new_ok:
                verilog = new_verilog
                compile_ok = True
                break
            else:
                verilog = new_verilog
                compile_err = new_err

    # ── Step 2: Cocotb repair loop (v4: history-aware, 5 iterations, fresh-start) ──
    if compile_ok and not passed and os.path.isdir(harness_dir):
        cocotb_history: list[dict] = []
        FRESH_START_THRESHOLD = 3  # after 3 failed iters, try a fresh rewrite

        for fi in range(1, args.max_cocotb_iter + 1):
            total_iters += 1
            log.info(f"[{pid}] Cocotb repair iter {fi}/{args.max_cocotb_iter}")

            # Fresh-start rewrite if stuck after FRESH_START_THRESHOLD iterations
            if fi == FRESH_START_THRESHOLD + 1 and not passed:
                log.info(f"[{pid}] FRESH START: {FRESH_START_THRESHOLD} iter failed, "
                         "rewriting from spec+harness errors")
                # Use the latest harness error but ask for a complete rewrite
                latest_error = cocotb_history[-1].get("error_block", "") if cocotb_history else ""
                fresh_prompt = (
                    f"## Specification\n{spec}\n\n"
                    f"## What the existing implementation gets wrong\n{latest_error[:1500]}\n\n"
                    "The previous incremental repairs failed. Write a COMPLETELY NEW Verilog "
                    "implementation from scratch that correctly implements the spec. "
                    "Return ONLY the new implementation in a ```verilog ... ``` block."
                )
                raw, gen_in, gen_out = generate_with_claude(client, fresh_prompt, args.temperature)
                total_gen_in_tok += gen_in
                total_gen_out_tok += gen_out
                candidate = extract_verilog(raw)
                new_ok, _ = iverilog_check(candidate, rtl_filename)
                if new_ok:
                    log.info(f"[{pid}] Fresh rewrite compiled OK — testing harness")
                    verilog = candidate
                    best_verilog = candidate
                    write_log(log_path, {
                        "cycle": args.cycle, "script_version": args.script_version,
                        "problem_id": pid, "iteration": total_iters,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "action": "fresh_rewrite",
                        "cocotb_iter": fi,
                        "gen_in_tok": gen_in, "gen_out_tok": gen_out,
                    })
                else:
                    log.info(f"[{pid}] Fresh rewrite did not compile, continuing repair")
                    # Don't update verilog; continue with previous

            # Run harness to get fresh error
            t0 = time.time()
            harness_result = run_harness(verilog, harness_dir, rtl_filename)
            harness_s = time.time() - t0

            if harness_result["passed"]:
                passed = True
                best_verilog = verilog
                log.info(f"[{pid}] Cocotb PASS at iter {fi}!")
                write_log(log_path, {
                    "cycle": args.cycle, "script_version": args.script_version,
                    "problem_id": pid, "iteration": total_iters,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "action": "cocotb_pass",
                    "cocotb_iter": fi,
                    "harness_s": round(harness_s, 1),
                })
                break

            parsed = parse_harness_output(harness_result["output"])
            error_block = format_error_for_reflector(parsed, harness_result["output"])

            log.info(f"[{pid}] Cocotb iter {fi}: FAIL ({harness_s:.0f}s harness)")
            log.info(f"  Failed tests: {parsed['failed_tests'][:3]}")
            if parsed["mismatches"]:
                log.info(f"  Mismatches: {parsed['mismatches'][:2]}")

            # History-aware reflection (v4 improvement)
            diagnosis, fix_inst, ref_in, ref_out = reflect_with_sonnet_v4(
                client, spec, verilog, error_block, "cocotb",
                history=cocotb_history,
            )
            total_ref_in_tok += ref_in
            total_ref_out_tok += ref_out

            # Track history for oscillation detection
            cocotb_history.append({
                "diagnosis": diagnosis,
                "fix_instruction": fix_inst,
                "failed_tests": parsed["failed_tests"],
                "error_block": error_block[:500],
            })

            repair_prompt = build_repair_prompt(spec, verilog, diagnosis, fix_inst)
            raw, gen_in, gen_out = generate_with_claude(client, repair_prompt, args.temperature)
            total_gen_in_tok += gen_in
            total_gen_out_tok += gen_out
            new_verilog = extract_verilog(raw)

            new_ok, new_err = iverilog_check(new_verilog, rtl_filename)
            log.info(f"[{pid}] Cocotb iter {fi} iverilog: {'PASS' if new_ok else 'FAIL'}")

            write_log(log_path, {
                "cycle": args.cycle, "script_version": args.script_version,
                "problem_id": pid, "iteration": total_iters,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "cocotb_repair",
                "cocotb_iter": fi,
                "iverilog_pass": new_ok,
                "harness_s": round(harness_s, 1),
                "failed_tests": parsed["failed_tests"],
                "mismatches": parsed["mismatches"],
                "diagnosis": diagnosis[:400],
                "fix_instruction": fix_inst[:400],
                "output_tail": harness_result["output"][-800:],
                "verilog_chars": len(new_verilog),
                "ref_in_tok": ref_in, "ref_out_tok": ref_out,
                "gen_in_tok": gen_in, "gen_out_tok": gen_out,
            })

            if new_ok:
                best_verilog = new_verilog
                verilog = new_verilog
            else:
                log.info(f"[{pid}] Repair broke compile — keeping previous verilog")

    # ── Save best RTL ─────────────────────────────────────────────────────────
    final_verilog = best_verilog if best_verilog else verilog
    out_rtl_dir = out_dir / "rtl"
    out_rtl_dir.mkdir(parents=True, exist_ok=True)
    rtl_out = out_rtl_dir / f"{pid}.sv"
    with open(rtl_out, "w") as f:
        f.write(final_verilog.strip() + "\n")

    elapsed = time.time() - t_start
    log.info(
        f"[{pid}] DONE — harness={'PASS' if passed else 'FAIL'} | "
        f"iters={total_iters} | {elapsed:.0f}s total"
    )

    result = {
        "id": pid, "categories": cats,
        "passed": passed,
        "total_iters": total_iters,
        "elapsed_s": round(elapsed, 1),
        "ref_in_tok": total_ref_in_tok,
        "ref_out_tok": total_ref_out_tok,
        "gen_in_tok": total_gen_in_tok,
        "gen_out_tok": total_gen_out_tok,
        "rtl_path": str(rtl_out),
    }
    write_log(log_path, {
        "cycle": args.cycle, "script_version": args.script_version,
        "problem_id": pid, "iteration": "final",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "saved",
        **result,
    })
    return result


def parse_iverilog_errors(stderr: str, rtl_filename: str) -> str:
    lines = []
    for ln in stderr.splitlines():
        if "error" in ln.lower() or "warning" in ln.lower():
            ln = re.sub(r'.+?(' + re.escape(rtl_filename) + r')', r'\1', ln)
            lines.append(ln.strip())
    return "\n".join(lines[:5]) if lines else stderr[:400]


# ── Main ──────────────────────────────────────────────────────────────────────

CYCLE2_TARGETS = [
    # 4 failed from Cycle 1
    "cvdp_copilot_GFCM_0001",
    "cvdp_copilot_digital_dice_roller_0001",
    "cvdp_copilot_events_to_apb_0001",
    "cvdp_copilot_digital_stopwatch_0001",
    # 4 new from priority pool (not yet tested)
    "cvdp_copilot_fsm_seq_detector_0001",
    "cvdp_copilot_hamming_code_tx_and_rx_0003",
    "cvdp_copilot_perf_counters_0001",
    "cvdp_copilot_convolutional_encoder_0001",
]


def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    Path(args.log).parent.mkdir(parents=True, exist_ok=True)

    problems_to_run = args.problems or CYCLE2_TARGETS

    all_probs = load_problems(DATA_FILE)
    client = anthropic.Anthropic()

    results = {}
    results_path = out_dir / "results.json"
    if results_path.exists():
        with open(results_path) as f:
            results = json.load(f)
        log.info(f"Resuming — {len(results)} already done")

    remaining = [p for p in problems_to_run if p not in results]
    log.info(f"Cycle {args.cycle} ({args.script_version}): {len(remaining)} problems to run")

    t_cycle_start = time.time()

    for pid in remaining:
        if pid not in all_probs:
            log.error(f"Problem {pid} not found in dataset")
            continue

        # Load initial RTL
        initial_verilog = None
        for ext in (".sv", ".v"):
            p = Path(args.initial_rtl) / f"{pid}{ext}"
            if p.exists():
                initial_verilog = p.read_text()
                break

        try:
            result = run_problem(
                pid=pid,
                prob_data=all_probs[pid],
                initial_verilog=initial_verilog,
                bench_dir=args.bench_dir,
                client=client,
                args=args,
                log_path=args.log,
                out_dir=out_dir,
            )
        except Exception as e:
            log.error(f"[{pid}] CRASHED: {e}", exc_info=True)
            result = {
                "id": pid, "passed": False,
                "total_iters": 0, "elapsed_s": 0,
                "ref_in_tok": 0, "ref_out_tok": 0,
                "gen_in_tok": 0, "gen_out_tok": 0,
                "error": str(e),
            }

        results[pid] = result
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)

    # ── Summary ────────────────────────────────────────────────────────────────
    cycle_elapsed = time.time() - t_cycle_start
    total = len(results)
    if total == 0:
        return

    passed_list = [pid for pid, r in results.items() if r.get("passed")]
    failed_list = [pid for pid, r in results.items() if not r.get("passed")]

    total_ref_in = sum(r.get("ref_in_tok", 0) for r in results.values())
    total_ref_out = sum(r.get("ref_out_tok", 0) for r in results.values())
    total_gen_in = sum(r.get("gen_in_tok", 0) for r in results.values())
    total_gen_out = sum(r.get("gen_out_tok", 0) for r in results.values())

    ref_cost = (total_ref_in / 1e6 * SONNET_INPUT_COST_PER_MTOK +
                total_ref_out / 1e6 * SONNET_OUTPUT_COST_PER_MTOK)
    gen_cost = (total_gen_in / 1e6 * SONNET_INPUT_COST_PER_MTOK +
                total_gen_out / 1e6 * SONNET_OUTPUT_COST_PER_MTOK)

    avg_elapsed = sum(r.get("elapsed_s", 0) for r in results.values()) / total

    lines = [
        "=" * 70,
        f"CYCLE {args.cycle} — Script {args.script_version} — Local Test",
        "=" * 70,
        f"Problems tested: {total}",
        f"Passed (harness): {len(passed_list)}/{total} = {100*len(passed_list)/total:.1f}%",
        "",
        f"Passed: {passed_list}",
        f"Failed: {failed_list}",
        "",
        f"Avg time/problem: {avg_elapsed:.0f}s | Total cycle: {cycle_elapsed:.0f}s",
        "",
        "API usage (reflector = Sonnet, generator = Sonnet local):",
        f"  Reflector: {total_ref_in:,} in / {total_ref_out:,} out → ${ref_cost:.3f}",
        f"  Generator: {total_gen_in:,} in / {total_gen_out:,} out → ${gen_cost:.3f}",
        f"  Total cost: ${ref_cost + gen_cost:.3f}",
    ]
    summary = "\n".join(lines)
    print("\n" + summary)
    with open(out_dir / "summary.txt", "w") as f:
        f.write(summary + "\n")

    write_log(args.log, {
        "event": "cycle_complete",
        "cycle": args.cycle,
        "script_version": args.script_version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total": total,
        "passed": len(passed_list),
        "passed_list": passed_list,
        "failed_list": failed_list,
        "avg_elapsed_s": round(avg_elapsed, 1),
        "cycle_elapsed_s": round(cycle_elapsed, 1),
        "ref_cost": round(ref_cost, 4),
        "gen_cost": round(gen_cost, 4),
    })

    log.info(f"\nCycle complete. Log: {args.log}")
    log.info(f"Output dir: {out_dir}")


if __name__ == "__main__":
    main()
