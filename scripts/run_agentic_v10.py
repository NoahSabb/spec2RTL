#!/usr/bin/env python3
"""
Agentic loop v10 — LOCAL test version.

Key changes vs v9:
  - Two-directory RTL lookup: --initial-rtl is checked first (previous cycle's best RTL),
    then --fallback-rtl (raw RL v2 output). Retry problems start from partially-fixed code
    rather than rediscovering and re-fixing already-diagnosed bugs from scratch.
    New problems that don't appear in --initial-rtl silently fall back to --fallback-rtl.
  - Iteration cap unchanged: 3 compile + 4 cocotb = 7 total.

Usage:
    python3 scripts/run_agentic_v10.py \\
        --bench-dir cvdp_benchmark/work_qwen32b_lora_rl_v2 \\
        --initial-rtl logs/cycle6_v9/rtl \\
        --fallback-rtl ~/Downloads/cid003_eval_rl_v2 \\
        --out logs/cycle7_v10 \\
        --log logs/agentic_improvement_cycle.jsonl \\
        --cycle 7 --script-version v10
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
                   help="Problem IDs to run (default: CYCLE5_TARGETS)")
    p.add_argument("--bench-dir",
                   default="cvdp_benchmark/work_qwen32b_lora_rl_v2")
    p.add_argument("--initial-rtl", default="logs/cycle6_v9/rtl",
                   help="Primary RTL dir — checked first (previous cycle best RTL)")
    p.add_argument("--fallback-rtl",
                   default=os.path.expanduser("~/Downloads/cid003_eval_rl_v2"),
                   help="Fallback RTL dir — used when problem not found in --initial-rtl")
    p.add_argument("--out", default="logs/cycle7_v10")
    p.add_argument("--log", default="logs/agentic_improvement_cycle.jsonl")
    p.add_argument("--max-compile-iter", type=int, default=3)
    p.add_argument("--max-cocotb-iter", type=int, default=4)
    p.add_argument("--temperature", type=float, default=0.3)
    p.add_argument("--cycle", type=int, default=7)
    p.add_argument("--script-version", default="v10")
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
    harness_dir_abs = os.path.abspath(harness_dir)
    rtl_path = os.path.join(harness_dir_abs, "rtl", rtl_filename)

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

    mismatches = []
    for m in re.finditer(
        r'(?:expected|Expected)\s+([^\n,]{1,80}),?\s*(?:got|got:)\s*([^\n]{1,80})',
        output, re.IGNORECASE
    ):
        mismatches.append({"expected": m.group(1).strip(), "actual": m.group(2).strip()})

    assertion_lines = []
    for i, ln in enumerate(lines):
        if "AssertionError" in ln or ("assert " in ln.lower() and "==" in ln):
            ctx = lines[max(0, i-2):i+3]
            assertion_lines.append("\n".join(ctx))
        if len(assertion_lines) >= 4:
            break

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
        "raw": output[-3000:],
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
        parts.append("Full harness output (last 2500 chars):")
        parts.append(full_output[-2500:])
    else:
        parts.append("\nRaw output tail (last 1000 chars):")
        parts.append(full_output[-1000:])

    return "\n".join(parts)


# ── Testbench extraction (v6: from disk, full content) ────────────────────────

def extract_testbench_info(prob_data: dict, harness_dir: str | None = None) -> tuple[str, str]:
    """Extract module name (TOPLEVEL) and full testbench.

    v6: reads actual test file from disk (harness_dir) with up to 3000 chars.
    Falls back to JSONL harness data if disk not available.
    Prefers specific test file (test_*.py excluding test_runner.py).
    """
    harness_files = prob_data.get("harness", {}).get("files", {})
    env_content = harness_files.get("src/.env", "")

    module_name = ""
    for line in env_content.splitlines():
        if line.startswith("TOPLEVEL") and "LANG" not in line:
            module_name = line.split("=", 1)[-1].strip()
            break

    testbench = ""

    # v6: try to read from disk first (full content)
    if harness_dir and os.path.isdir(harness_dir):
        src_dir = os.path.join(harness_dir, "src")
        if os.path.isdir(src_dir):
            # Prefer specific test file over test_runner.py
            candidates = sorted(os.listdir(src_dir))
            for fname in candidates:
                if fname.startswith("test_") and fname.endswith(".py") and fname != "test_runner.py":
                    try:
                        testbench = open(os.path.join(src_dir, fname)).read()[:3000]
                        break
                    except Exception:
                        pass
            if not testbench:
                for fname in candidates:
                    if fname.endswith(".py") and fname != "test_runner.py":
                        try:
                            testbench = open(os.path.join(src_dir, fname)).read()[:3000]
                            break
                        except Exception:
                            pass

    # Fallback: JSONL harness data (600 chars as before)
    if not testbench:
        for k, v in harness_files.items():
            if k.startswith("src/test_") and k.endswith(".py") and "runner" not in k:
                testbench = v[:3000]
                break
        if not testbench:
            for k, v in harness_files.items():
                if k.startswith("src/test_") and k.endswith(".py"):
                    testbench = v[:3000]
                    break

    return module_name, testbench


def is_opaque_failure(harness_output: str, parsed: dict) -> bool:
    """Return True when the test just says FAILED with no assertion details."""
    has_mismatches = bool(parsed.get("mismatches"))
    has_assertions = bool(parsed.get("assertion_context"))
    has_cocotb_values = bool(re.search(r'expected.*got|AssertionError', harness_output, re.IGNORECASE))
    return not (has_mismatches or has_assertions or has_cocotb_values)


# ── Reflector (two-step: diagnose + fix) ──────────────────────────────────────

REFLECTOR_SYSTEM = """You are an expert RTL hardware engineer reviewing a failing Verilog module.

Your task: analyze the failure and provide a SPECIFIC repair instruction.

Key rules:
- Do NOT write Verilog code — only describe what to change and why
- Be PRECISE about signal names, bit positions, and logic expressions
- Identify ROOT CAUSE not just symptoms
- If a testbench is provided, ensure the RTL matches ALL port names, parameter names,
  and module name EXACTLY as shown — these are non-negotiable interface requirements

Common Verilog/cocotb failure patterns to consider:
- Bit/encoding order: MSB vs LSB, byte order, bit-reversal in output encoding
- Reset initialization: X/Z states from uninitialized regs at t=0
- Off-by-one: fence post errors in counters, loop bounds, state transitions
- Missing cases: incomplete case statements causing X propagation
- Async vs sync reset: wrong sensitivity list causing RTL/testbench mismatch
- Clock gating: combinational feedback into clocked logic causing glitches
- Timing: output registered when testbench expects combinational (or vice versa)
- Overflow/underflow: unsigned vs signed, bit-width truncation
- Missing parameters: testbench reads RTL parameters via dut.PARAM — must be declared
"""


def reflect_with_sonnet(
    client: anthropic.Anthropic,
    spec: str,
    verilog: str,
    error_block: str,
    error_type: str,
    history: list[dict] | None = None,
    testbench: str | None = None,
    module_name: str | None = None,
) -> tuple[str, str, int, int]:
    """
    History-aware two-step reflection. v7: adds module_name to reflector prompt
    to prevent hallucination of wrong TOPLEVEL names.

    Returns (diagnosis, fix_instruction, input_tokens, output_tokens).
    """
    history_block = ""
    if history:
        hist_lines = ["## Previous Repair Attempts (all FAILED — avoid repeating these)"]
        for i, h in enumerate(history[-3:], 1):
            hist_lines.append(f"\n### Attempt {i}")
            hist_lines.append(f"Diagnosis: {h.get('diagnosis', '')[:200]}")
            hist_lines.append(f"Fix tried: {h.get('fix_instruction', '')[:200]}")
            hist_lines.append(f"Result: still failing ({h.get('failed_tests', [])})")
        history_block = "\n".join(hist_lines) + "\n\n"

    # v7: always include testbench when available (not just on opaque failures)
    tb_block = ""
    if testbench:
        tb_block = (
            f"## Testbench (ground truth for port names, parameters, behavior)\n"
            f"```python\n{testbench}\n```\n\n"
        )

    # v7: add explicit module name to prevent reflector hallucination
    mn_block = ""
    if module_name:
        mn_block = (
            f"## Required Module Name (TOPLEVEL from .env)\n"
            f"The RTL module MUST be named `{module_name}` — do NOT suggest renaming it. "
            f"The issue is NOT the module name.\n\n"
        )

    if error_type == "compile":
        user = (
            f"## Specification\n{spec}\n\n"
            f"{mn_block}"
            f"{tb_block}"
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
            f"{mn_block}"
            f"{tb_block}"
            f"## Current RTL (compiles, fails functionally)\n```verilog\n{verilog}\n```\n\n"
            f"## Test Failure Details\n{error_block}\n\n"
            f"{history_block}"
            "Respond in EXACTLY this format:\n\n"
            "## Diagnosis\n"
            "One sentence: what specific signal/logic/encoding is wrong and why.\n"
            "If the testbench shows interface requirements (port names, parameters) that "
            "differ from the RTL, list ALL of them — not just the most prominent one.\n\n"
            "## Fix Instruction\n"
            "Precise RTL change: name exact signal/always-block/expression and what to change it to.\n"
            "If previous fixes oscillated, take a DIFFERENT approach (e.g., rewrite the key block)."
        )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
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


# ── Generator ─────────────────────────────────────────────────────────────────

GENERATOR_SYSTEM = (
    "You are an expert RTL hardware engineer. "
    "Output ONLY the complete, corrected Verilog module inside a ```verilog ... ``` block. "
    "Do NOT change any port names or the module name unless explicitly told to. "
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
                        fix_instruction: str,
                        module_name: str | None = None,
                        testbench_excerpt: str | None = None) -> str:
    parts = [f"## Specification\n{spec}\n\n"]
    if module_name:
        parts.append(
            f"## CRITICAL: Module Name Requirement\n"
            f"The module MUST be named exactly `{module_name}`. "
            f"The testbench will not compile if the name differs.\n\n"
        )
    if testbench_excerpt:
        parts.append(
            f"## Testbench Interface (exact port/parameter names required)\n"
            f"```python\n{testbench_excerpt}\n```\n\n"
        )
    parts.append(
        f"## Current RTL (to be repaired)\n```verilog\n{verilog}\n```\n\n"
        f"## Diagnosed Bug\n{diagnosis}\n\n"
        f"## Required Fix\n{fix_instruction}\n\n"
        "Apply the fix above. Return ONLY the corrected Verilog in a ```verilog ... ``` block."
    )
    return "".join(parts)


def parse_iverilog_errors(stderr: str, rtl_filename: str) -> str:
    lines = []
    for ln in stderr.splitlines():
        if "error" in ln.lower() or "warning" in ln.lower():
            ln = re.sub(r'.+?(' + re.escape(rtl_filename) + r')', r'\1', ln)
            lines.append(ln.strip())
    return "\n".join(lines[:5]) if lines else stderr[:400]


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

    parts = pid.rsplit("_", 1)
    base = parts[0]
    num = int(parts[1])
    harness_dir = os.path.join(bench_dir, base, "harness", str(num))

    rtl_filename = f"{pid}.sv"
    env_content = (prob_data.get("harness", {}).get("files", {}).get("src/.env", ""))
    for line in env_content.splitlines():
        if line.startswith("VERILOG_SOURCES"):
            rtl_filename = line.split("=")[-1].strip().split("/")[-1]
            break

    # v6: pass harness_dir to extract full testbench from disk
    module_name, testbench = extract_testbench_info(
        prob_data, harness_dir if os.path.isdir(harness_dir) else None
    )
    if module_name:
        log.info(f"  Module name (from TOPLEVEL): {module_name}")
    if testbench:
        log.info(f"  Testbench available: yes ({len(testbench)} chars) [v6: from disk]")

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
                diagnosis, fix_inst, ref_in, ref_out = reflect_with_sonnet(
                    client, spec, verilog,
                    parse_iverilog_errors(compile_err, rtl_filename),
                    "compile",
                    testbench=testbench,
                    module_name=module_name,
                )
                total_ref_in_tok += ref_in
                total_ref_out_tok += ref_out
                prompt = build_repair_prompt(spec, verilog, diagnosis, fix_inst,
                                             module_name=module_name)
            else:
                diagnosis, fix_inst = "", ""
                mn_req = (f"CRITICAL: Module must be named exactly `{module_name}`.\n\n"
                          if module_name else "")
                tb_req = (f"## Testbench Interface\n```python\n{testbench}\n```\n\n"
                          if testbench else "")
                prompt = (
                    "Generate synthesizable Verilog RTL for the following specification.\n\n"
                    f"## Specification\n{spec}\n\n"
                    f"{mn_req}{tb_req}"
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

    # ── Step 2: Cocotb repair loop (v8: 3 iters max, no fresh-starts) ───────────
    if compile_ok and not passed and os.path.isdir(harness_dir):
        cocotb_history: list[dict] = []

        for fi in range(1, args.max_cocotb_iter + 1):
            total_iters += 1
            log.info(f"[{pid}] Cocotb repair iter {fi}/{args.max_cocotb_iter}")

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

            # v7: always pass testbench AND module_name to reflector
            diagnosis, fix_inst, ref_in, ref_out = reflect_with_sonnet(
                client, spec, verilog, error_block, "cocotb",
                history=cocotb_history,
                testbench=testbench,
                module_name=module_name,
            )
            total_ref_in_tok += ref_in
            total_ref_out_tok += ref_out

            cocotb_history.append({
                "diagnosis": diagnosis,
                "fix_instruction": fix_inst,
                "failed_tests": parsed["failed_tests"],
                "error_block": error_block[:500],
            })

            # v6: include testbench in repair prompt when error is opaque OR first 2 iters
            opaque = is_opaque_failure(harness_result["output"], parsed)
            include_tb_in_repair = opaque or fi <= 2

            repair_prompt = build_repair_prompt(
                spec, verilog, diagnosis, fix_inst,
                module_name=module_name,
                testbench_excerpt=testbench if include_tb_in_repair else None,
            )
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


# ── Main ──────────────────────────────────────────────────────────────────────

CYCLE7_TARGETS = [
    # 3 retries — start from cycle6_v9/rtl/ (partially fixed); skip re-diagnosing known bugs
    "cvdp_copilot_ttc_lite_0001",       # two-always-block match_flag race; specific final fix known
    "cvdp_copilot_wb2ahb_0001",         # data_o stale in IDLE after write; one-line fix known
    "cvdp_copilot_hebbian_rule_0017",   # FSM re-enters State_0; structural fix needed
    # 2 new — fall back to RL v2 initial RTL
    "cvdp_copilot_load_store_unit_0001",
    "cvdp_copilot_packet_controller_0001",
]


def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    Path(args.log).parent.mkdir(parents=True, exist_ok=True)

    problems_to_run = args.problems or CYCLE7_TARGETS

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

        initial_verilog = None
        rtl_dirs = [args.initial_rtl]
        if hasattr(args, "fallback_rtl") and args.fallback_rtl:
            rtl_dirs.append(args.fallback_rtl)
        for rtl_dir in rtl_dirs:
            for ext in (".sv", ".v"):
                p = Path(rtl_dir) / f"{pid}{ext}"
                if p.exists():
                    initial_verilog = p.read_text()
                    log.info(f"  [{pid}] Initial RTL from: {rtl_dir}")
                    break
            if initial_verilog:
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
