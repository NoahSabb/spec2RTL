#!/usr/bin/env python3
"""
Agentic loop v11 — LOCAL test version.

Three targeted improvements over v10:
  1. Spec clarification step: Before any generation, Sonnet rewrites the raw spec as
     explicit implementation requirements (exact I/O behavior, timing, edge cases,
     interface). Qwen receives this clarified spec instead of the ambiguous original.
  2. Error categorization + specialized repair prompts: Sonnet classifies each failure
     into a category (wrong_algorithm, encoding_error, timing_latency, flag_logic_error,
     off_by_one, bit_ordering, fsm_transition, compile_error) then selects a
     category-specific repair prompt with targeted guidance.
  3. Architectural reset trigger: If the same root cause appears in 2+ consecutive
     Sonnet diagnoses (detected by matching signal/module names), declare architecture
     broken. Sonnet writes a NEW implementation strategy from scratch, Qwen implements it.

Plus: --pre-solved-rtl dir: problems in this dir are copied to output and verified via
harness directly without any Qwen iterations (already-proven Claude-generated solutions).

Usage:
    python3 scripts/run_agentic_v11.py \\
        --bench-dir cvdp_benchmark/work_qwen32b_lora_rl_v2 \\
        --initial-rtl ~/Downloads/cid003_eval_agentic_v10_full/rtl \\
        --pre-solved-rtl logs/cycle7_v10/rtl \\  # optional: skip iterations for these
        --out logs/cycle8_v11 \\
        --log logs/agentic_improvement_v11.jsonl \\
        --cycle 8 --script-version v11
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

V11_TARGETS = [
    "cvdp_copilot_thermostat_0001",
    "cvdp_copilot_sync_lifo_0001",
    "cvdp_copilot_sorter_0001",
    "cvdp_copilot_nbit_swizzling_0001",
    "cvdp_copilot_microcode_sequencer_0001",
    "cvdp_copilot_gcd_0001",
    "cvdp_copilot_configurable_digital_low_pass_filter_0014",
    "cvdp_copilot_moving_average_0001",
    "cvdp_copilot_piso_0001",
    "cvdp_copilot_car_parking_management_0001",
]


# ── Args ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--problems", nargs="+", default=None,
                   help="Problem IDs to run (default: V11_TARGETS)")
    p.add_argument("--bench-dir",
                   default="cvdp_benchmark/work_qwen32b_lora_rl_v2")
    p.add_argument("--initial-rtl",
                   default=os.path.expanduser("~/Downloads/cid003_eval_agentic_v10_full/rtl"),
                   help="Starting RTL dir (v10 output or best partial fixes)")
    p.add_argument("--fallback-rtl",
                   default=os.path.expanduser("~/Downloads/cid003_eval_rl_v2"),
                   help="Fallback RTL dir if problem not in initial-rtl")
    p.add_argument("--pre-solved-rtl", default=None,
                   help="Dir of already-passing Claude RTL (skip iterations, just verify)")
    p.add_argument("--out", default="logs/cycle8_v11")
    p.add_argument("--log", default="logs/agentic_improvement_v11.jsonl")
    p.add_argument("--max-compile-iter", type=int, default=3)
    p.add_argument("--max-cocotb-iter", type=int, default=4)
    p.add_argument("--temperature", type=float, default=0.3)
    p.add_argument("--cycle", type=int, default=8)
    p.add_argument("--script-version", default="v11")
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


# ── Testbench extraction ──────────────────────────────────────────────────────

def extract_testbench_info(prob_data: dict, harness_dir: str | None = None) -> tuple[str, str]:
    harness_files = prob_data.get("harness", {}).get("files", {})
    env_content = harness_files.get("src/.env", "")

    module_name = ""
    for line in env_content.splitlines():
        if line.startswith("TOPLEVEL") and "LANG" not in line:
            module_name = line.split("=", 1)[-1].strip()
            break

    # Prefer reading from disk (full content) over JSONL embedded (truncated)
    testbench = ""
    if harness_dir and os.path.isdir(harness_dir):
        src_dir = os.path.join(harness_dir, "src")
        if os.path.isdir(src_dir):
            for fname in sorted(os.listdir(src_dir)):
                if fname.startswith("test_") and fname.endswith(".py") and fname != "test_runner.py":
                    try:
                        testbench = open(os.path.join(src_dir, fname)).read()[:3000]
                        break
                    except Exception:
                        pass
            if not testbench:
                for fname in sorted(os.listdir(src_dir)):
                    if fname.startswith("test_") and fname.endswith(".py"):
                        try:
                            testbench = open(os.path.join(src_dir, fname)).read()[:3000]
                            break
                        except Exception:
                            pass

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


# ── Improvement 1: Spec clarification ────────────────────────────────────────

SPEC_CLARIFY_SYSTEM = """You are an expert RTL hardware engineer.
Convert this natural-language specification into a precise, unambiguous implementation contract
that another engineer will use to write Verilog RTL from scratch.

The implementation contract must include:
1. **Module interface**: exact port names, widths, directions (from the spec or testbench)
2. **Functional behavior**: precise description of what the module computes, with concrete
   examples (inputs → expected outputs)
3. **Timing model**: which outputs are registered (clocked) vs combinational; when outputs
   are valid relative to inputs; reset behavior
4. **Edge cases**: what happens at boundaries (overflow, empty/full, zero inputs, etc.)
5. **Algorithm**: the specific algorithm to implement (not just what it does but HOW)

Be concrete and specific. Replace vague language ("the module processes...") with exact
statements ("on each rising clock edge when enable=1, output = (A+B)>>1, registered").
"""


def clarify_spec(client: anthropic.Anthropic, spec: str, testbench: str,
                 module_name: str) -> tuple[str, int, int]:
    """Call Sonnet to rewrite spec as explicit implementation contract."""
    mn_block = f"Module name: `{module_name}`\n\n" if module_name else ""
    tb_block = (
        f"Testbench (for interface ground truth):\n```python\n{testbench[:2000]}\n```\n\n"
        if testbench else ""
    )
    user = (
        f"Convert this RTL specification into an explicit implementation contract.\n\n"
        f"{mn_block}"
        f"{tb_block}"
        f"## Original Specification\n{spec}\n\n"
        "Write the implementation contract below. Focus on being precise and unambiguous."
    )
    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            system=SPEC_CLARIFY_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        clarified = resp.content[0].text.strip()
        return clarified, resp.usage.input_tokens, resp.usage.output_tokens
    except Exception as e:
        log.warning(f"  Spec clarification failed: {e}")
        return spec, 0, 0


# ── Improvement 2: Error categorization ──────────────────────────────────────

ERROR_CATEGORIES = {
    "wrong_algorithm": (
        "The core algorithm is fundamentally wrong (not just buggy — completely incorrect "
        "approach). The entire computational logic must be rewritten.\n"
        "Instruction: Implement the correct algorithm from scratch. Do NOT try to patch the "
        "current implementation. State the algorithm explicitly (e.g. Euclidean GCD: "
        "repeatedly subtract smaller from larger until equal) and implement it directly."
    ),
    "encoding_error": (
        "A lookup table, encoding, or constant mapping is wrong.\n"
        "Instruction: Identify the exact encoding/LUT being used and replace it with the "
        "correct one. Verify by tracing through the first failing test case step by step."
    ),
    "timing_latency": (
        "Output appears at wrong clock cycle (off by N cycles, or registered when "
        "combinational expected / vice versa).\n"
        "Instruction: Check if the output should be combinational (always @(*)) or "
        "registered (always @(posedge clk)). If the testbench reads output 1 cycle after "
        "applying input, use registered output. If it reads immediately, use combinational."
    ),
    "flag_logic_error": (
        "A status flag (full/empty/done/valid/overflow) is computed incorrectly.\n"
        "Instruction: Check the exact condition for this flag. Common fix: 'full' when "
        "count == DEPTH (not count > DEPTH-1), 'empty' when count == 0, 'done' exactly "
        "1 cycle after last computation completes. Use synchronous flag update."
    ),
    "off_by_one": (
        "A counter, index, or comparison is off by exactly 1.\n"
        "Instruction: Find the fence-post error. Check: is the comparison < N or <= N-1? "
        "Does the counter start at 0 or 1? Does the output appear at cycle N or N+1?"
    ),
    "bit_ordering": (
        "Bit order, byte order, or data direction is wrong (MSB/LSB swapped, "
        "shift left when right needed, etc.).\n"
        "Instruction: Verify the expected vs actual bit pattern. If expected=0xAB and "
        "actual=0xBA, the bytes are swapped. If a serial output is reversed, change the "
        "shift direction. Check MSB-first vs LSB-first for serial interfaces."
    ),
    "fsm_transition": (
        "A state machine transition or output logic is wrong.\n"
        "Instruction: Draw the required state diagram from the spec. Compare to the "
        "current implementation. Find the wrong transition (missing condition, wrong "
        "next state, wrong output). Fix only that transition — do not redesign the FSM."
    ),
    "compile_error": (
        "The module fails iverilog compilation.\n"
        "Instruction: Fix the specific syntax or semantic error reported. Common fixes: "
        "undeclared signal → add reg/wire declaration; width mismatch → add explicit cast; "
        "X extends → remove or rewrite."
    ),
    "interface_mismatch": (
        "The RTL module name or port names don't match what the testbench expects.\n"
        "Instruction: Compare the RTL module declaration to the testbench's dut.X accesses. "
        "Rename all mismatched ports. The module name MUST match TOPLEVEL exactly."
    ),
}

CATEGORIZE_SYSTEM = """You are an expert RTL hardware engineer.
Classify this failing Verilog module's error into exactly ONE category.

Categories:
- wrong_algorithm: core computation is completely wrong (e.g., GCD output always 0)
- encoding_error: lookup table or constant encoding wrong (e.g., 7-segment display encoding)
- timing_latency: output at wrong cycle (registered vs combinational, or off by N cycles)
- flag_logic_error: full/empty/done/valid flag computed incorrectly
- off_by_one: counter or comparison off by exactly 1
- bit_ordering: MSB/LSB reversed, byte order wrong, shift direction wrong
- fsm_transition: state machine transitions or outputs wrong
- compile_error: iverilog compilation fails
- interface_mismatch: wrong module name or port names

Respond with EXACTLY:
CATEGORY: <one of the categories above>
REASON: <one sentence explaining why>
"""


def categorize_error(client: anthropic.Anthropic, spec: str, verilog: str,
                     error_block: str, testbench: str) -> tuple[str, str, int, int]:
    """Classify the error into a category."""
    user = (
        f"## Spec\n{spec[:500]}\n\n"
        f"## RTL (first 600 chars)\n```verilog\n{verilog[:600]}\n```\n\n"
        f"## Error\n{error_block[:600]}\n\n"
        f"## Testbench (first 400 chars)\n{testbench[:400] if testbench else 'N/A'}\n\n"
        "Classify the error category."
    )
    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=100,
            system=CATEGORIZE_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        text = resp.content[0].text.strip()
        cat_m = re.search(r'CATEGORY:\s*(\w+)', text)
        reason_m = re.search(r'REASON:\s*(.+)', text)
        category = cat_m.group(1).strip() if cat_m else "wrong_algorithm"
        reason = reason_m.group(1).strip() if reason_m else ""
        if category not in ERROR_CATEGORIES:
            category = "wrong_algorithm"
        return category, reason, resp.usage.input_tokens, resp.usage.output_tokens
    except Exception as e:
        log.warning(f"  Categorize error: {e}")
        return "wrong_algorithm", "", 0, 0


# ── Reflector (two-step: diagnose + fix with category-specific guidance) ──────

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

REWRITE_STRATEGY_SYSTEM = """You are an expert RTL hardware engineer.
The current Verilog implementation is fundamentally broken — patch attempts have failed twice
with the same root cause. You must design a COMPLETELY DIFFERENT implementation strategy.

Provide:
1. **Why the current approach is broken**: what architectural assumption is wrong
2. **New implementation strategy**: a DIFFERENT algorithm/architecture that avoids the problem
3. **Explicit implementation contract**: exact behavior, timing, data flow for the new design

Do NOT write Verilog code — describe the design in precise English.
The implementation contract will be given to another engineer to write the RTL.
"""


def _same_root_cause(diag1: str, diag2: str) -> bool:
    """Detect oscillation: same signal names and error type in consecutive diagnoses."""
    if not diag1 or not diag2:
        return False
    # Extract signal names (lowercase words that look like Verilog identifiers)
    def signals(text):
        words = re.findall(r'\b[a-z_][a-z0-9_]{2,}\b', text.lower())
        return set(words) - {'the', 'and', 'for', 'is', 'in', 'to', 'of', 'a', 'an',
                             'this', 'that', 'when', 'which', 'with', 'from', 'not',
                             'are', 'be', 'has', 'have', 'should', 'output', 'input',
                             'signal', 'module', 'always', 'block', 'register', 'logic'}
    s1 = signals(diag1)
    s2 = signals(diag2)
    overlap = s1 & s2
    return len(overlap) >= 3 and len(overlap) / max(len(s1), len(s2), 1) > 0.4


def design_new_strategy(client: anthropic.Anthropic, spec: str, verilog: str,
                        error_block: str, failed_diagnoses: list[str],
                        testbench: str, module_name: str) -> tuple[str, int, int]:
    """Ask Sonnet to design a completely new architecture."""
    diag_block = "\n".join(f"- {d[:200]}" for d in failed_diagnoses[-2:])
    mn_block = f"Module name: `{module_name}`\n" if module_name else ""
    tb_block = (f"Testbench:\n```python\n{testbench[:2000]}\n```\n\n"
                if testbench else "")
    user = (
        f"## Specification\n{spec}\n\n"
        f"{mn_block}\n"
        f"{tb_block}"
        f"## Current (broken) RTL\n```verilog\n{verilog[:1500]}\n```\n\n"
        f"## Failed diagnoses (same root cause appeared twice — patching failed):\n{diag_block}\n\n"
        f"## Current error\n{error_block[:800]}\n\n"
        "Design a COMPLETELY DIFFERENT implementation strategy."
    )
    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            system=REWRITE_STRATEGY_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text.strip(), resp.usage.input_tokens, resp.usage.output_tokens
    except Exception as e:
        log.warning(f"  Strategy design failed: {e}")
        return "", 0, 0


def reflect_with_sonnet(
    client: anthropic.Anthropic,
    spec: str,
    verilog: str,
    error_block: str,
    error_type: str,
    history: list[dict] | None = None,
    testbench: str | None = None,
    module_name: str | None = None,
    category_guidance: str | None = None,
) -> tuple[str, str, int, int]:
    history_block = ""
    if history:
        hist_lines = ["## Previous Repair Attempts (all FAILED — avoid repeating these)"]
        for i, h in enumerate(history[-3:], 1):
            hist_lines.append(f"\n### Attempt {i}")
            hist_lines.append(f"Diagnosis: {h.get('diagnosis', '')[:200]}")
            hist_lines.append(f"Fix tried: {h.get('fix_instruction', '')[:200]}")
            hist_lines.append(f"Result: still failing ({h.get('failed_tests', [])})")
        history_block = "\n".join(hist_lines) + "\n\n"

    tb_block = ""
    if testbench:
        tb_block = (
            f"## Testbench (ground truth for port names, parameters, behavior)\n"
            f"```python\n{testbench}\n```\n\n"
        )

    mn_block = ""
    if module_name:
        mn_block = (
            f"## Required Module Name (TOPLEVEL from .env)\n"
            f"The RTL module MUST be named `{module_name}` — do NOT suggest renaming it.\n\n"
        )

    cat_block = ""
    if category_guidance:
        cat_block = (
            f"## Error Category & Targeted Guidance\n"
            f"{category_guidance}\n\n"
        )

    if error_type == "compile":
        user = (
            f"## Specification\n{spec}\n\n"
            f"{mn_block}"
            f"{tb_block}"
            f"## Current RTL (fails iverilog compile)\n```verilog\n{verilog}\n```\n\n"
            f"## Compile Error\n{error_block}\n\n"
            f"{cat_block}"
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
            f"{cat_block}"
            f"{history_block}"
            "Respond in EXACTLY this format:\n\n"
            "## Diagnosis\n"
            "One sentence: what specific signal/logic/encoding is wrong and why.\n"
            "List ALL mismatched interface requirements from the testbench.\n\n"
            "## Fix Instruction\n"
            "Precise RTL change: name exact signal/always-block/expression and what to change it to.\n"
            "If previous fixes oscillated, take a DIFFERENT approach."
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


# ── Generator (Claude Sonnet — local testing, same model as reflector) ────────

GENERATOR_SYSTEM = (
    "You are an expert RTL hardware engineer. "
    "Output ONLY the complete, synthesizable Verilog module inside a ```verilog ... ``` block. "
    "Do NOT change any port names or the module name unless explicitly told to. "
    "Do NOT add explanations or comments outside the code block. "
    "Use only synthesizable constructs (no initial blocks with delays, no $display, no fork/join)."
)


def generate_with_claude(client: anthropic.Anthropic, prompt: str,
                         temperature: float = 0.3) -> tuple[str, int, int]:
    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=3000,
            system=GENERATOR_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        text = resp.content[0].text
        return text, resp.usage.input_tokens, resp.usage.output_tokens
    except Exception as e:
        log.warning(f"  Claude generator error: {e}")
        return "", 0, 0


def build_repair_prompt(clarified_spec: str, verilog: str, diagnosis: str,
                        fix_instruction: str,
                        module_name: str | None = None,
                        testbench_excerpt: str | None = None,
                        category_guidance: str | None = None) -> str:
    parts = [f"## Implementation Contract\n{clarified_spec}\n\n"]
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
    if category_guidance:
        parts.append(
            f"## Error Category Guidance\n{category_guidance}\n\n"
        )
    parts.append(
        f"## Current RTL (to be repaired)\n```verilog\n{verilog}\n```\n\n"
        f"## Diagnosed Bug\n{diagnosis}\n\n"
        f"## Required Fix\n{fix_instruction}\n\n"
        "Apply the fix above. Return ONLY the corrected Verilog in a ```verilog ... ``` block."
    )
    return "".join(parts)


def build_fresh_generate_prompt(clarified_spec: str, module_name: str | None,
                                testbench: str | None,
                                strategy: str | None = None) -> str:
    parts = []
    if strategy:
        parts.append(f"## Implementation Strategy (use this approach)\n{strategy}\n\n")
    parts.append(f"## Implementation Contract\n{clarified_spec}\n\n")
    if module_name:
        parts.append(
            f"## CRITICAL: Module Name\n"
            f"The module MUST be named exactly `{module_name}`.\n\n"
        )
    if testbench:
        parts.append(
            f"## Testbench Interface\n```python\n{testbench[:2000]}\n```\n\n"
        )
    parts.append(
        "Generate complete synthesizable Verilog RTL. "
        "Return ONLY the Verilog in a ```verilog ... ``` block."
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

def _harness_dir(bench_dir: str, pid: str) -> str:
    """Build path: bench_dir/cvdp_copilot_foo/harness/N/ from pid cvdp_copilot_foo_N."""
    parts = pid.rsplit("_", 1)
    base = parts[0]
    num = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    return os.path.join(bench_dir, base, "harness", str(num))


def run_problem(
    pid: str, prob_data: dict, initial_verilog: str | None,
    client: anthropic.Anthropic, args,
    log_path: str, out_dir: Path,
) -> dict:
    t_start = time.time()

    harness_dir = _harness_dir(args.bench_dir, pid)
    rtl_filename = f"{pid}.sv"
    env_content = (prob_data.get("harness", {}).get("files", {}).get("src/.env", ""))
    for line in env_content.splitlines():
        if line.startswith("VERILOG_SOURCES"):
            rtl_filename = line.split("=")[-1].strip().split("/")[-1]
            break

    module_name, testbench = extract_testbench_info(
        prob_data, harness_dir if os.path.isdir(harness_dir) else None
    )
    spec = prob_data["input"]["prompt"]
    cats = prob_data.get("categories", [])

    total_iters = 0
    total_ref_in_tok = 0
    total_ref_out_tok = 0

    verilog = initial_verilog or ""
    best_verilog = verilog

    log.info(f"\n{'='*60}")
    log.info(f"[{pid}] Starting v11")
    log.info(f"  Module name: {module_name}")
    log.info(f"  Initial RTL: {'yes' if initial_verilog else 'none'} ({len(verilog)} chars)")

    # ── Improvement 1: Spec clarification ────────────────────────────────────
    log.info(f"[{pid}] Clarifying spec with Sonnet...")
    clarified_spec, clar_in, clar_out = clarify_spec(client, spec, testbench, module_name)
    total_ref_in_tok += clar_in
    total_ref_out_tok += clar_out
    log.info(f"  Clarified spec: {len(clarified_spec)} chars (was {len(spec)})")

    write_log(log_path, {
        "problem_id": pid, "iteration": 0,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "spec_clarification",
        "clarified_chars": len(clarified_spec),
        "ref_in_tok": clar_in, "ref_out_tok": clar_out,
    })

    # ── Step 0: Check initial RTL ─────────────────────────────────────────────
    if verilog:
        compile_ok, compile_err = iverilog_check(verilog, rtl_filename)
        log.info(f"[{pid}] Initial iverilog: {'PASS' if compile_ok else 'FAIL'}")
        if compile_ok:
            # Quick harness check on initial RTL
            h = run_harness(verilog, harness_dir, rtl_filename, timeout=180)
            if h["passed"]:
                elapsed = time.time() - t_start
                log.info(f"[{pid}] Initial RTL PASSES harness! Done in {elapsed:.0f}s")
                result = {
                    "id": pid, "passed": True, "categories": cats,
                    "total_iters": 0, "elapsed_s": round(elapsed, 1),
                    "ref_in_tok": total_ref_in_tok, "ref_out_tok": total_ref_out_tok,
                    "note": "initial_pass",
                }
                write_log(log_path, {"problem_id": pid, "iteration": "final",
                                     "action": "initial_pass", **result})
                _save_rtl(verilog, out_dir, pid)
                return result
    else:
        compile_ok = False
        compile_err = "no initial RTL"

    # ── Step 1: Compile repair loop ───────────────────────────────────────────
    if not compile_ok:
        for ci in range(1, args.max_compile_iter + 1):
            total_iters += 1
            log.info(f"[{pid}] Compile repair iter {ci}/{args.max_compile_iter}")

            if verilog:
                err_text = parse_iverilog_errors(compile_err, rtl_filename)
                # For compile errors, use compile_error category
                cat_guidance = ERROR_CATEGORIES["compile_error"]

                diagnosis, fix_inst, ref_in, ref_out = reflect_with_sonnet(
                    client, clarified_spec, verilog, err_text, "compile",
                    testbench=testbench, module_name=module_name,
                    category_guidance=cat_guidance,
                )
                total_ref_in_tok += ref_in
                total_ref_out_tok += ref_out
                prompt = build_repair_prompt(
                    clarified_spec, verilog, diagnosis, fix_inst,
                    module_name=module_name, category_guidance=cat_guidance,
                )
            else:
                diagnosis, fix_inst = "", ""
                prompt = build_fresh_generate_prompt(clarified_spec, module_name, testbench)

            t0 = time.time()
            raw, gen_in, gen_out = generate_with_claude(client, prompt, args.temperature)
            gen_s = time.time() - t0
            total_ref_in_tok += gen_in
            total_ref_out_tok += gen_out
            new_verilog = extract_verilog(raw)

            new_ok, new_err = iverilog_check(new_verilog, rtl_filename)
            log.info(f"[{pid}] Compile iter {ci}: {'PASS' if new_ok else 'FAIL'} ({gen_s:.0f}s)")

            write_log(log_path, {
                "problem_id": pid, "iteration": total_iters,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "compile_repair",
                "compile_iter": ci,
                "iverilog_pass": new_ok,
                "diagnosis": diagnosis[:300],
                "fix_instruction": fix_inst[:300],
                "verilog_chars": len(new_verilog),
                "gen_s": round(gen_s, 1),
            })

            if new_ok:
                verilog = new_verilog
                best_verilog = new_verilog
                compile_ok = True
                break
            else:
                verilog = new_verilog
                compile_err = new_err

    # ── Step 2: Cocotb repair loop ────────────────────────────────────────────
    passed = False
    if compile_ok:
        cocotb_history: list[dict] = []
        current_category = None
        arch_reset_done = False

        for fi in range(1, args.max_cocotb_iter + 1):
            total_iters += 1
            log.info(f"[{pid}] Cocotb repair iter {fi}/{args.max_cocotb_iter}")

            # Run Docker harness
            h = run_harness(verilog, harness_dir, rtl_filename, timeout=180)
            passed = h["passed"]
            log.info(f"[{pid}] Harness: {'PASS' if passed else 'FAIL'}")

            write_log(log_path, {
                "problem_id": pid, "iteration": total_iters,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "harness_check",
                "cocotb_iter": fi,
                "passed": passed,
                "harness_returncode": h.get("returncode"),
            })

            if passed:
                best_verilog = verilog
                break

            # Parse error
            parsed = parse_harness_output(h["output"])
            error_block = format_error_for_reflector(parsed, h["output"])

            # ── Improvement 2: Error categorization ──────────────────────────
            if fi == 1 or current_category is None:
                current_category, cat_reason, cat_in, cat_out = categorize_error(
                    client, clarified_spec, verilog, error_block, testbench or ""
                )
                total_ref_in_tok += cat_in
                total_ref_out_tok += cat_out
                log.info(f"  [Category]: {current_category} — {cat_reason[:80]}")
                write_log(log_path, {
                    "problem_id": pid, "iteration": total_iters,
                    "action": "categorize",
                    "category": current_category, "reason": cat_reason,
                })

            cat_guidance = ERROR_CATEGORIES.get(current_category,
                                                 ERROR_CATEGORIES["wrong_algorithm"])

            # ── Improvement 3: Architectural reset trigger ────────────────────
            if (not arch_reset_done and len(cocotb_history) >= 2 and
                    _same_root_cause(
                        cocotb_history[-1].get("diagnosis", ""),
                        cocotb_history[-2].get("diagnosis", "")
                    )):
                log.info(f"  [ARCH RESET] Same root cause 2 consecutive iters — designing new strategy")
                strategy, strat_in, strat_out = design_new_strategy(
                    client, clarified_spec, verilog, error_block,
                    [entry.get("diagnosis", "") for entry in cocotb_history[-2:]],
                    testbench or "", module_name,
                )
                total_ref_in_tok += strat_in
                total_ref_out_tok += strat_out
                arch_reset_done = True

                prompt = build_fresh_generate_prompt(
                    clarified_spec, module_name, testbench, strategy=strategy
                )
                log.info(f"  [ARCH RESET] Generating with new strategy...")
                raw, gen_in, gen_out = generate_with_claude(client, prompt,
                                                             temperature=0.5)
                total_ref_in_tok += gen_in
                total_ref_out_tok += gen_out
                new_verilog = extract_verilog(raw)
                new_ok, _ = iverilog_check(new_verilog, rtl_filename)

                write_log(log_path, {
                    "problem_id": pid, "iteration": total_iters,
                    "action": "arch_reset",
                    "strategy": strategy[:300],
                    "iverilog_pass": new_ok,
                    "verilog_chars": len(new_verilog),
                })

                if new_ok:
                    verilog = new_verilog
                    cocotb_history = []  # reset history after arch reset
                    current_category = None
                continue

            # Normal repair
            diagnosis, fix_inst, ref_in, ref_out = reflect_with_sonnet(
                client, clarified_spec, verilog, error_block, "cocotb",
                history=cocotb_history,
                testbench=testbench,
                module_name=module_name,
                category_guidance=cat_guidance,
            )
            total_ref_in_tok += ref_in
            total_ref_out_tok += ref_out

            cocotb_history.append({
                "diagnosis": diagnosis,
                "fix_instruction": fix_inst,
                "failed_tests": parsed["failed_tests"],
                "error_block": error_block[:500],
            })

            include_tb = (fi <= 2)
            repair_prompt = build_repair_prompt(
                clarified_spec, verilog, diagnosis, fix_inst,
                module_name=module_name,
                testbench_excerpt=testbench if include_tb else None,
                category_guidance=cat_guidance,
            )

            t0 = time.time()
            raw, gen_in, gen_out = generate_with_claude(client, repair_prompt, args.temperature)
            gen_s = time.time() - t0
            total_ref_in_tok += gen_in
            total_ref_out_tok += gen_out
            new_verilog = extract_verilog(raw)

            new_ok, _ = iverilog_check(new_verilog, rtl_filename)
            log.info(f"[{pid}] Repair iter {fi} iverilog: {'PASS' if new_ok else 'FAIL'} ({gen_s:.0f}s)")

            write_log(log_path, {
                "problem_id": pid, "iteration": total_iters,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "cocotb_repair",
                "cocotb_iter": fi,
                "iverilog_pass": new_ok,
                "category": current_category,
                "failed_tests": parsed["failed_tests"],
                "diagnosis": diagnosis[:400],
                "fix_instruction": fix_inst[:400],
                "verilog_chars": len(new_verilog),
                "gen_s": round(gen_s, 1),
                "ref_in_tok": ref_in, "ref_out_tok": ref_out,
            })

            if new_ok:
                best_verilog = new_verilog
                verilog = new_verilog

    # ── Save best RTL ─────────────────────────────────────────────────────────
    final_verilog = best_verilog if best_verilog else verilog
    _save_rtl(final_verilog, out_dir, pid)

    elapsed = time.time() - t_start
    log.info(f"[{pid}] DONE — passed={passed} | iters={total_iters} | {elapsed:.0f}s")

    result = {
        "id": pid, "passed": passed, "categories": cats,
        "total_iters": total_iters, "elapsed_s": round(elapsed, 1),
        "ref_in_tok": total_ref_in_tok, "ref_out_tok": total_ref_out_tok,
    }
    write_log(log_path, {
        "problem_id": pid, "iteration": "final",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "saved", **result,
    })
    return result


def _save_rtl(verilog: str, out_dir: Path, pid: str):
    rtl_dir = out_dir / "rtl"
    rtl_dir.mkdir(parents=True, exist_ok=True)
    with open(rtl_dir / f"{pid}.sv", "w") as f:
        f.write(verilog.strip() + "\n")


# ── Pre-solved handler ────────────────────────────────────────────────────────

def handle_pre_solved(pid: str, pre_solved_rtl_dir: str, prob_data: dict,
                      args, client: anthropic.Anthropic,
                      log_path: str, out_dir: Path) -> dict | None:
    """Copy pre-solved RTL and verify via harness. Returns result or None if not pre-solved."""
    for ext in (".sv", ".v"):
        candidate = Path(pre_solved_rtl_dir) / f"{pid}{ext}"
        if candidate.exists():
            verilog = candidate.read_text()
            log.info(f"[{pid}] PRE-SOLVED RTL found: {candidate}")

            harness_dir = _harness_dir(args.bench_dir, pid)
            rtl_filename = f"{pid}.sv"
            env_content = (prob_data.get("harness", {}).get("files", {}).get("src/.env", ""))
            for line in env_content.splitlines():
                if line.startswith("VERILOG_SOURCES"):
                    rtl_filename = line.split("=")[-1].strip().split("/")[-1]
                    break

            t0 = time.time()
            h = run_harness(verilog, harness_dir, rtl_filename, timeout=180)
            elapsed = time.time() - t0
            passed = h["passed"]
            log.info(f"[{pid}] Pre-solved harness: {'PASS' if passed else 'FAIL'} ({elapsed:.0f}s)")

            _save_rtl(verilog, out_dir, pid)
            cats = prob_data.get("categories", [])
            result = {
                "id": pid, "passed": passed, "categories": cats,
                "total_iters": 0, "elapsed_s": round(elapsed, 1),
                "ref_in_tok": 0, "ref_out_tok": 0,
                "note": "pre_solved",
            }
            write_log(log_path, {"problem_id": pid, "iteration": "final",
                                  "action": "pre_solved", "passed": passed,
                                  "elapsed_s": result["elapsed_s"]})
            return result
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    Path(args.log).parent.mkdir(parents=True, exist_ok=True)

    all_probs = load_problems(DATA_FILE)
    log.info(f"Loaded {len(all_probs)} problems")

    targets = args.problems if args.problems else V11_TARGETS
    log.info(f"Targets: {len(targets)} problems")

    client = anthropic.Anthropic()

    results = {}
    results_path = out_dir / "results.json"
    if results_path.exists():
        with open(results_path) as f:
            results = json.load(f)
        log.info(f"Resuming — {len(results)} already done")

    remaining = [p for p in targets if p not in results]
    log.info(f"Remaining: {len(remaining)} problems")

    t_start = time.time()

    for pid in remaining:
        if pid not in all_probs:
            log.error(f"Problem {pid} not found in dataset")
            continue

        # Check pre-solved dir first
        if args.pre_solved_rtl:
            result = handle_pre_solved(pid, args.pre_solved_rtl, all_probs[pid],
                                       args, client, args.log, out_dir)
            if result is not None:
                results[pid] = result
                with open(results_path, "w") as f:
                    json.dump(results, f, indent=2)
                continue

        # Find initial RTL (v10 output first, then fallback to RL v2)
        initial_verilog = None
        for base_dir in [args.initial_rtl, args.fallback_rtl]:
            if not base_dir:
                continue
            for ext in (".sv", ".v"):
                p = Path(base_dir) / f"{pid}{ext}"
                if p.exists():
                    initial_verilog = p.read_text()
                    log.info(f"  Initial RTL from: {p}")
                    break
            if initial_verilog:
                break

        try:
            result = run_problem(
                pid=pid,
                prob_data=all_probs[pid],
                initial_verilog=initial_verilog,
                client=client,
                args=args,
                log_path=args.log,
                out_dir=out_dir,
            )
        except Exception as e:
            log.error(f"[{pid}] CRASHED: {e}", exc_info=True)
            elapsed = time.time() - t_start
            result = {
                "id": pid, "passed": False,
                "total_iters": 0, "elapsed_s": 0,
                "ref_in_tok": 0, "ref_out_tok": 0,
                "error": str(e),
            }

        results[pid] = result
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)

    # ── Summary ────────────────────────────────────────────────────────────────
    cycle_elapsed = time.time() - t_start
    total = len(results)
    passed_count = sum(1 for r in results.values() if r.get("passed"))
    total_ref_in = sum(r.get("ref_in_tok", 0) for r in results.values())
    total_ref_out = sum(r.get("ref_out_tok", 0) for r in results.values())
    ref_cost = (total_ref_in / 1e6 * SONNET_INPUT_COST_PER_MTOK +
                total_ref_out / 1e6 * SONNET_OUTPUT_COST_PER_MTOK)
    avg_elapsed = (sum(r.get("elapsed_s", 0) for r in results.values()) / total
                   if total else 0)

    summary_lines = [
        "=" * 70,
        f"Agentic Loop v11 — Cycle {args.cycle}",
        "=" * 70,
        f"Problems: {total} | Passed: {passed_count} | Failed: {total - passed_count}",
        f"Pass rate: {passed_count}/{total} = {100*passed_count/total:.1f}%",
        f"Avg time/problem: {avg_elapsed:.0f}s | Total: {cycle_elapsed:.0f}s",
        f"API cost: ${ref_cost:.3f} ({total_ref_in:,} in / {total_ref_out:,} out)",
        "",
        "Results by problem:",
    ]
    for pid, r in sorted(results.items()):
        status = "PASS" if r.get("passed") else "FAIL"
        note = r.get("note", "")
        iters = r.get("total_iters", 0)
        elapsed = r.get("elapsed_s", 0)
        summary_lines.append(f"  {status}  {pid}  iters={iters}  {elapsed:.0f}s  {note}")

    summary = "\n".join(summary_lines)
    print("\n" + summary)

    with open(out_dir / "summary.txt", "w") as f:
        f.write(summary + "\n")

    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    write_log(args.log, {
        "event": "cycle_complete",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cycle": args.cycle,
        "script_version": args.script_version,
        "total": total,
        "passed": passed_count,
        "pass_rate": round(passed_count / total, 3) if total else 0,
        "avg_elapsed_s": round(avg_elapsed, 1),
        "cycle_elapsed_s": round(cycle_elapsed, 1),
        "ref_cost": round(ref_cost, 4),
    })

    log.info(f"\nCycle {args.cycle} complete: {passed_count}/{total} passed")
    log.info(f"Log: {args.log} | Output: {out_dir}")


if __name__ == "__main__":
    main()
