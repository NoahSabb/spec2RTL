"""
Agentic loop v2 — improved over v1 with:
  - Structured error parsing (iverilog line numbers + cocotb assertion values)
  - Targeted repair prompts (spec + full prev RTL + parsed error + fix instruction)
  - 5-iteration cap, no restarts — iterate then stop
  - Per-iteration JSON logging
"""

import json
import logging
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic

log = logging.getLogger(__name__)


# ─────────────────────────── simulation / harness ────────────────────────────

def run_iverilog_check(verilog_code: str) -> dict:
    """Quick iverilog compile check (no simulation)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rtl_path = os.path.join(tmpdir, "design.sv")
        out_path = os.path.join(tmpdir, "sim.vvp")
        with open(rtl_path, "w") as f:
            f.write(verilog_code)
        r = subprocess.run(
            ["iverilog", "-g2012", "-o", out_path, rtl_path],
            capture_output=True, text=True
        )
        return {
            "passed": r.returncode == 0,
            "errors": r.stderr,
            "output": r.stdout,
            "stage": "compile",
        }


def run_harness(verilog_code: str, harness_dir: str, rtl_filename: str) -> dict:
    """Run the CVDP Docker harness and return structured result."""
    import glob
    rtl_path = os.path.join(harness_dir, "rtl", rtl_filename)
    with open(rtl_path, "w") as f:
        f.write(verilog_code.strip() + "\n")

    scripts = glob.glob(os.path.join(harness_dir, "run_docker_harness_*.sh"))
    if not scripts:
        return {"passed": False, "errors": "No harness script found", "output": "", "stage": "harness"}

    result = subprocess.run(["bash", scripts[0]], capture_output=True, text=True, timeout=300)
    output = result.stdout + result.stderr

    # Pull assertion failures from result XML files
    xml_failures = []
    for xml_file in glob.glob(os.path.join(harness_dir, "rundir", "sim_build", "*.result.xml")):
        try:
            with open(xml_file) as f:
                for msg in re.findall(r'error_msg="([^"]*)"', f.read()):
                    xml_failures.append(msg.replace("&#10;", "\n").replace("&#9;", "\t"))
        except Exception:
            pass

    if xml_failures:
        output += "\n\n=== TEST FAILURES ===\n" + "\n---\n".join(xml_failures)

    sim_log = os.path.join(harness_dir, "rundir", "sim.log")
    if os.path.exists(sim_log):
        with open(sim_log) as f:
            sim_log_text = f.read()
        if sim_log_text.strip():
            output += "\n\n=== SIM LOG ===\n" + sim_log_text

    passed = result.returncode == 0 and not xml_failures and "FAILED" not in output
    return {"passed": passed, "errors": result.stderr, "output": output, "stage": "harness"}


# ─────────────────────────── error parsing ───────────────────────────────────

def parse_errors(sim_result: dict) -> dict:
    """
    Extract structured error info from simulation output.
    Returns a dict with:
      - stage: 'compile' or 'harness'
      - iverilog_errors: list of {file, line, message}
      - test_failures: list of {test_name, expected, actual, message}
      - raw_tail: last 2000 chars for context
    """
    stage = sim_result.get("stage", "unknown")
    errors_text = sim_result.get("errors", "")
    output_text = sim_result.get("output", "")
    combined = (errors_text + "\n" + output_text).strip()

    # iverilog compile errors: "file.sv:42: error: some message"
    iverilog_errors = []
    for m in re.finditer(r'(\S+\.(?:sv|v)):(\d+):\s*(error|warning):\s*(.+)', combined):
        iverilog_errors.append({
            "file": m.group(1).split("/")[-1],
            "line": int(m.group(2)),
            "type": m.group(3),
            "message": m.group(4).strip(),
        })

    # cocotb test names that failed
    failed_tests = re.findall(r'FAILED\s+[\w./]+::([\w]+)', combined)

    # assertion mismatches: "Expected X, got Y" patterns
    test_failures = []
    for m in re.finditer(
        r'(?:expected|Expected)\s+([^\n,]+),?\s*(?:got|got:)\s*([^\n]+)', combined, re.IGNORECASE
    ):
        test_failures.append({"expected": m.group(1).strip(), "actual": m.group(2).strip()})

    # assert a == b style
    for m in re.finditer(r'assert\s+(.+?)\s*==\s*(.+)', combined):
        lhs, rhs = m.group(1).strip(), m.group(2).strip()
        if lhs != rhs:
            test_failures.append({"actual": lhs, "expected": rhs})

    # AssertionError lines
    assertion_lines = [
        line.strip() for line in combined.splitlines()
        if "AssertionError" in line or "assert " in line.lower()
    ][:5]

    return {
        "stage": stage,
        "iverilog_errors": iverilog_errors[:5],
        "failed_tests": list(dict.fromkeys(failed_tests))[:5],  # deduplicate
        "test_failures": test_failures[:5],
        "assertion_lines": assertion_lines,
        "raw_tail": combined[-2000:],
    }


def format_parsed_error(parsed: dict) -> str:
    """Render parsed error into a compact text block for prompts."""
    parts = [f"Stage: {parsed['stage']}"]

    if parsed["iverilog_errors"]:
        parts.append("iverilog errors:")
        for e in parsed["iverilog_errors"]:
            parts.append(f"  {e['file']} line {e['line']}: {e['type']}: {e['message']}")

    if parsed["failed_tests"]:
        parts.append("Failed tests: " + ", ".join(parsed["failed_tests"]))

    if parsed["test_failures"]:
        parts.append("Value mismatches:")
        for f in parsed["test_failures"]:
            parts.append(f"  expected={f['expected']}  actual={f['actual']}")

    if parsed["assertion_lines"]:
        parts.append("Assertion failures:")
        for a in parsed["assertion_lines"]:
            parts.append(f"  {a}")

    if not parsed["iverilog_errors"] and not parsed["test_failures"]:
        parts.append("Raw error tail (last 1500 chars):")
        parts.append(parsed["raw_tail"][-1500:])

    return "\n".join(parts)


# ─────────────────────────── reflector ───────────────────────────────────────

def reflect_v2(client: anthropic.Anthropic, spec: str, verilog_code: str,
               sim_result: dict, parsed_error: dict) -> str:
    """
    Analyzes parsed error and returns a targeted fix instruction.
    Returns a single concrete repair action suitable for passing to the generator.
    """
    error_text = format_parsed_error(parsed_error)

    prompt = f"""You are an expert RTL hardware engineer. A Verilog module failed simulation.

## Specification
{spec[:1500]}

## Current Verilog (first 80 lines)
```verilog
{chr(10).join(verilog_code.splitlines()[:80])}
```

## Failure Details
{error_text}

Respond in EXACTLY this format — two sections, no extra text:

## Root Cause
One sentence: what specific signal, logic block, or expression is wrong and why.

## Fix Instruction
One concrete RTL-level change: name the exact signal/always block/expression to change
and what to change it to. Do not suggest more than one change.
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


# ─────────────────────────── verilog extraction ──────────────────────────────

def extract_verilog(response) -> str:
    """Extract Verilog code from a generator response (handles various formats)."""
    if isinstance(response, tuple):
        d = response[0]
        if isinstance(d, dict) and "direct_text" in d:
            response = d["direct_text"]
    if not isinstance(response, str):
        return ""
    m = re.search(r'```(?:verilog|systemverilog|sv)?\s*\n(.*?)```', response, re.DOTALL)
    if m:
        return m.group(1).strip()
    return response.strip()


# ─────────────────────────── main loop ───────────────────────────────────────

def run_agentic_loop_v2(
    generator,
    client: anthropic.Anthropic,
    spec: str,
    *,
    max_iterations: int = 5,
    harness_dir: Optional[str] = None,
    rtl_filename: Optional[str] = None,
    initial_verilog: Optional[str] = None,
    log_file: Optional[str] = None,
    problem_id: str = "unknown",
) -> dict:
    """
    Improved agentic loop.

    Args:
        generator:        Model with .prompt(text, category, files) interface
        client:           Anthropic client for Reflector
        spec:             Problem specification text
        max_iterations:   Stop after this many attempts (default 5)
        harness_dir:      Path to harness/N directory for cocotb testing
        rtl_filename:     RTL filename inside harness/N/rtl/
        initial_verilog:  Skip initial generation and start from this RTL
        log_file:         Path to JSONL file for iteration logs
        problem_id:       Problem identifier for logs
    """
    iterations = []

    def _log(entry: dict):
        if log_file:
            try:
                with open(log_file, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception as e:
                log.warning(f"Log write failed: {e}")

    def _simulate(verilog: str) -> dict:
        if harness_dir and rtl_filename and os.path.isdir(harness_dir):
            return run_harness(verilog, harness_dir, rtl_filename)
        # Fallback: compile-only check
        log.warning("No harness available, falling back to iverilog compile check")
        return run_iverilog_check(verilog)

    # ── iteration 0: initial generation or pre-supplied RTL ─────────────────
    if initial_verilog:
        verilog = initial_verilog
        log.info(f"[{problem_id}] Using pre-supplied initial RTL ({len(verilog)} chars)")
    else:
        log.info(f"[{problem_id}] Generating initial RTL from spec")
        verilog = extract_verilog(generator.prompt(spec, category=3, files=["design.sv"]))

    # ── iterative repair loop ────────────────────────────────────────────────
    for iteration in range(1, max_iterations + 1):
        t0 = time.time()
        sim_result = _simulate(verilog)
        elapsed = time.time() - t0

        parsed = parse_errors(sim_result)
        entry = {
            "problem_id": problem_id,
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "passed": sim_result["passed"],
            "sim_elapsed_s": round(elapsed, 1),
            "stage": sim_result["stage"],
            "verilog_chars": len(verilog),
            "verilog_head": verilog[:400],
            "parsed_error": {
                "iverilog_errors": parsed["iverilog_errors"],
                "failed_tests": parsed["failed_tests"],
                "test_failures": parsed["test_failures"],
            },
            "reflection": None,
            "repair_prompt_head": None,
        }

        if sim_result["passed"]:
            log.info(f"[{problem_id}] PASS at iteration {iteration}")
            entry["reflection"] = "PASSED"
            iterations.append(entry)
            _log(entry)
            return {
                "passed": True,
                "verilog": verilog,
                "iterations": iteration,
                "log": iterations,
            }

        log.info(f"[{problem_id}] iter {iteration}: FAIL (stage={sim_result['stage']}, "
                 f"iverilog_errs={len(parsed['iverilog_errors'])}, "
                 f"test_fails={len(parsed['test_failures'])})")

        if iteration == max_iterations:
            iterations.append(entry)
            _log(entry)
            break

        # ── reflect: get targeted fix instruction ────────────────────────────
        reflection = reflect_v2(client, spec, verilog, sim_result, parsed)
        entry["reflection"] = reflection
        log.info(f"[{problem_id}] iter {iteration} reflection:\n{reflection}")

        # ── targeted repair prompt ────────────────────────────────────────────
        error_summary = format_parsed_error(parsed)
        repair_prompt = (
            f"## Specification\n{spec}\n\n"
            f"## Previous RTL Attempt\n```verilog\n{verilog}\n```\n\n"
            f"## Simulation Failure\n{error_summary}\n\n"
            f"## Required Fix\n{reflection}\n\n"
            "Output ONLY the corrected Verilog module. "
            "Do not change any port names or module name. "
            "Apply the minimum change needed to fix the described error."
        )

        entry["repair_prompt_head"] = repair_prompt[:300]
        iterations.append(entry)
        _log(entry)

        # ── generate repaired RTL ─────────────────────────────────────────────
        raw = generator.prompt(repair_prompt, category=3, files=["design.sv"])
        verilog = extract_verilog(raw)
        log.info(f"[{problem_id}] iter {iteration} new RTL head:\n{verilog[:200]}")

    return {
        "passed": False,
        "verilog": verilog,
        "iterations": max_iterations,
        "log": iterations,
    }
