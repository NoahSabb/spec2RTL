#!/usr/bin/env python3
"""
Agentic loop v10 — CLUSTER version (full 78-problem run).

Key differences vs run_agentic_v10.py (local test):
  - Generator: Qwen2.5-Coder-32B + RL v2 LoRA adapter (bf16, loaded to cuda:0)
  - Reflector: Claude Sonnet 4.6 (unchanged — all v10 improvements kept)
  - Runs all 78 problems (not just CYCLE7_TARGETS)
  - Cocotb feedback: pre-saved errors from --cocotb-errors JSON (no Docker on cluster)
  - Initial RTL: pre-generated RL v2 outputs

Usage (via sbatch):
    python3 /home/noahsabb/spec2rtl/scripts/run_agentic_v10_cluster.py \
        --adapter /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v2 \
        --data /home/noahsabb/data/cid003_nonagentic.jsonl \
        --initial-rtl /home/noahsabb/results/cid003_eval_rl_v2/rtl \
        --cocotb-errors /home/noahsabb/data/cocotb_errors_rl_v2.json \
        --out /home/noahsabb/results/cid003_eval_agentic_v10_full \
        --log /home/noahsabb/logs/agentic_v10_full.jsonl \
        --max-compile-iter 3 --max-cocotb-iter 4 --temperature 0.3
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
CLAUDE_MODEL = "claude-sonnet-4-6"
SONNET_INPUT_COST_PER_MTOK = 3.00
SONNET_OUTPUT_COST_PER_MTOK = 15.00
SHARED_CACHE = "/home/_shared/models"


# ── Args ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="/home/noahsabb/data/cid003_nonagentic.jsonl")
    p.add_argument("--adapter", default="/home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v2")
    p.add_argument("--initial-rtl", default="/home/noahsabb/results/cid003_eval_rl_v2/rtl",
                   help="Dir with pre-generated .sv/.v files named {problem_id}.sv")
    p.add_argument("--cocotb-errors", default="/home/noahsabb/data/cocotb_errors_rl_v2.json",
                   help="JSON map of problem_id → cocotb/iverilog error string")
    p.add_argument("--out", default="/home/noahsabb/results/cid003_eval_agentic_v10_full")
    p.add_argument("--log", default="/home/noahsabb/logs/agentic_v10_full.jsonl")
    p.add_argument("--max-compile-iter", type=int, default=3)
    p.add_argument("--max-cocotb-iter", type=int, default=4)
    p.add_argument("--temperature", type=float, default=0.3)
    p.add_argument("--max-new-tokens", type=int, default=2048)
    p.add_argument("--problem-id", default=None, help="Run only this problem (debugging)")
    return p.parse_args()


# ── Data loading ──────────────────────────────────────────────────────────────

def load_problems(data_file: str) -> dict:
    probs = {}
    with open(data_file) as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                probs[d["id"]] = d
    return probs


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
    log.info(f"Merging RL v2 LoRA adapter from {adapter_path}...")
    model = PeftModel.from_pretrained(model, adapter_path)
    model = model.merge_and_unload()
    log.info("Moving merged model to cuda:0...")
    model = model.to("cuda:0")
    model.eval()

    alloc = torch.cuda.memory_allocated() / 1e9
    total = torch.cuda.get_device_properties(0).total_memory / 1e9
    log.info(f"Model on cuda:0 — allocated={alloc:.1f}GB / {total:.1f}GB total")
    return model, tokenizer


# ── Qwen generator ────────────────────────────────────────────────────────────

GENERATOR_SYSTEM = (
    "You are an expert RTL hardware engineer. "
    "Output ONLY the complete, corrected Verilog module inside a ```verilog ... ``` block. "
    "Do NOT change any port names or the module name unless explicitly told to. "
    "Do NOT add explanations or comments outside the code block."
)


def generate_with_qwen(model, tokenizer, prompt: str, temperature: float,
                       max_new_tokens: int) -> str:
    messages = [
        {"role": "system", "content": GENERATOR_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt").to("cuda:0")
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


# ── Compile check ─────────────────────────────────────────────────────────────

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

def extract_testbench_info(prob_data: dict) -> tuple[str, str]:
    """Extract module name (TOPLEVEL) and testbench from JSONL harness data."""
    harness_files = prob_data.get("harness", {}).get("files", {})
    env_content = harness_files.get("src/.env", "")

    module_name = ""
    for line in env_content.splitlines():
        if line.startswith("TOPLEVEL") and "LANG" not in line:
            module_name = line.split("=", 1)[-1].strip()
            break

    testbench = ""
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


# ── Reflector (two-step: diagnose + fix) ─────────────────────────────────────

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
    """History-aware two-step reflection. Returns (diagnosis, fix_instruction, in_tok, out_tok)."""
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
    cocotb_error: str,
    model, tokenizer,
    client: anthropic.Anthropic,
    args,
    log_path: str,
    out_dir: Path,
) -> dict:
    t_start = time.time()

    rtl_filename = f"{pid}.sv"
    env_content = (prob_data.get("harness", {}).get("files", {}).get("src/.env", ""))
    for line in env_content.splitlines():
        if line.startswith("VERILOG_SOURCES"):
            rtl_filename = line.split("=")[-1].strip().split("/")[-1]
            break

    module_name, testbench = extract_testbench_info(prob_data)
    if module_name:
        log.info(f"  Module name (from TOPLEVEL): {module_name}")
    if testbench:
        log.info(f"  Testbench available: yes ({len(testbench)} chars)")

    spec = prob_data["input"]["prompt"]
    cats = prob_data.get("categories", [])

    total_iters = 0
    total_ref_in_tok = 0
    total_ref_out_tok = 0

    verilog = initial_verilog or ""
    best_verilog = verilog

    log.info(f"\n{'='*60}")
    log.info(f"[{pid}] Starting")
    log.info(f"  RTL filename: {rtl_filename}")
    log.info(f"  Initial RTL: {'yes' if initial_verilog else 'none'} ({len(verilog)} chars)")
    log.info(f"  Pre-saved cocotb error: {'yes' if cocotb_error else 'none'} ({len(cocotb_error)} chars)")

    # ── Step 0: Check initial RTL ────────────────────────────────────────────
    if verilog:
        compile_ok, compile_err = iverilog_check(verilog, rtl_filename)
        write_log(log_path, {
            "problem_id": pid, "iteration": 0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "initial_check",
            "iverilog_pass": compile_ok,
            "iverilog_error": compile_err[:200] if not compile_ok else "",
        })
        log.info(f"[{pid}] Initial iverilog: {'PASS' if compile_ok else 'FAIL'}")
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

            t0 = time.time()
            raw = generate_with_qwen(model, tokenizer, prompt,
                                     args.temperature, args.max_new_tokens)
            gen_s = time.time() - t0
            new_verilog = extract_verilog(raw)

            new_ok, new_err = iverilog_check(new_verilog, rtl_filename)
            log.info(f"[{pid}] Compile iter {ci}: {'PASS' if new_ok else 'FAIL'} ({gen_s:.0f}s gen)")

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
                "ref_in_tok": ref_in if verilog else 0,
                "ref_out_tok": ref_out if verilog else 0,
            })

            if new_ok:
                verilog = new_verilog
                best_verilog = new_verilog
                compile_ok = True
                break
            else:
                verilog = new_verilog
                compile_err = new_err

    # ── Step 2: Cocotb repair loop (using pre-saved errors) ──────────────────
    if compile_ok and cocotb_error and args.max_cocotb_iter > 0:
        cocotb_history: list[dict] = []
        parsed = parse_harness_output(cocotb_error)

        # Skip if there's no useful error content (e.g. already passes baseline)
        if not parsed["failed_tests"] and not parsed["mismatches"] and not parsed["assertion_context"]:
            # Try raw error as context anyway
            if len(cocotb_error.strip()) < 20:
                log.info(f"[{pid}] Cocotb error too short — skipping cocotb repair")
                parsed = None

        if parsed is not None:
            for fi in range(1, args.max_cocotb_iter + 1):
                total_iters += 1
                log.info(f"[{pid}] Cocotb repair iter {fi}/{args.max_cocotb_iter}")

                error_block = format_error_for_reflector(parsed, cocotb_error)
                log.info(f"  Failed tests: {parsed['failed_tests'][:3]}")
                if parsed["mismatches"]:
                    log.info(f"  Mismatches: {parsed['mismatches'][:2]}")

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

                include_tb = (fi <= 2)
                repair_prompt = build_repair_prompt(
                    spec, verilog, diagnosis, fix_inst,
                    module_name=module_name,
                    testbench_excerpt=testbench if include_tb else None,
                )

                t0 = time.time()
                raw = generate_with_qwen(model, tokenizer, repair_prompt,
                                         args.temperature, args.max_new_tokens)
                gen_s = time.time() - t0
                new_verilog = extract_verilog(raw)

                new_ok, new_err = iverilog_check(new_verilog, rtl_filename)
                log.info(f"[{pid}] Cocotb iter {fi} iverilog: {'PASS' if new_ok else 'FAIL'} ({gen_s:.0f}s gen)")

                write_log(log_path, {
                    "problem_id": pid, "iteration": total_iters,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "action": "cocotb_repair",
                    "cocotb_iter": fi,
                    "iverilog_pass": new_ok,
                    "failed_tests": parsed["failed_tests"],
                    "mismatches": parsed["mismatches"],
                    "diagnosis": diagnosis[:400],
                    "fix_instruction": fix_inst[:400],
                    "verilog_chars": len(new_verilog),
                    "gen_s": round(gen_s, 1),
                    "ref_in_tok": ref_in, "ref_out_tok": ref_out,
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
    log.info(f"[{pid}] DONE — iters={total_iters} | {elapsed:.0f}s total | RTL saved")

    result = {
        "id": pid, "categories": cats,
        "total_iters": total_iters,
        "elapsed_s": round(elapsed, 1),
        "ref_in_tok": total_ref_in_tok,
        "ref_out_tok": total_ref_out_tok,
        "rtl_path": str(rtl_out),
    }
    write_log(log_path, {
        "problem_id": pid, "iteration": "final",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "saved",
        **result,
    })
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    Path(args.log).parent.mkdir(parents=True, exist_ok=True)

    all_probs = load_problems(args.data)
    log.info(f"Loaded {len(all_probs)} problems from {args.data}")

    cocotb_errors: dict[str, str] = {}
    if args.cocotb_errors and os.path.exists(args.cocotb_errors):
        with open(args.cocotb_errors) as f:
            cocotb_errors = json.load(f)
        log.info(f"Loaded {len(cocotb_errors)} pre-saved cocotb errors")
    else:
        log.warning("No cocotb errors file — cocotb repair loop will be skipped")

    if args.problem_id:
        problems_to_run = [args.problem_id]
    else:
        problems_to_run = sorted(all_probs.keys())
    log.info(f"Problems to run: {len(problems_to_run)}")

    results = {}
    results_path = out_dir / "results.json"
    if results_path.exists():
        with open(results_path) as f:
            results = json.load(f)
        log.info(f"Resuming — {len(results)} already done")

    remaining = [p for p in problems_to_run if p not in results]
    log.info(f"Remaining: {len(remaining)} problems")

    if not remaining:
        log.info("All problems already done.")
        return

    log.info("=== Loading Qwen model + RL v2 adapter ===")
    model, tokenizer = load_model(args.adapter)

    client = anthropic.Anthropic()

    t_start = time.time()

    for pid in remaining:
        if pid not in all_probs:
            log.error(f"Problem {pid} not found in dataset")
            continue

        initial_verilog = None
        for ext in (".sv", ".v"):
            p = Path(args.initial_rtl) / f"{pid}{ext}"
            if p.exists():
                initial_verilog = p.read_text()
                break

        cocotb_error = cocotb_errors.get(pid, "")

        try:
            result = run_problem(
                pid=pid,
                prob_data=all_probs[pid],
                initial_verilog=initial_verilog,
                cocotb_error=cocotb_error,
                model=model,
                tokenizer=tokenizer,
                client=client,
                args=args,
                log_path=args.log,
                out_dir=out_dir,
            )
        except Exception as e:
            log.error(f"[{pid}] CRASHED: {e}", exc_info=True)
            result = {
                "id": pid,
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
    if total == 0:
        return

    total_ref_in = sum(r.get("ref_in_tok", 0) for r in results.values())
    total_ref_out = sum(r.get("ref_out_tok", 0) for r in results.values())
    ref_cost = (total_ref_in / 1e6 * SONNET_INPUT_COST_PER_MTOK +
                total_ref_out / 1e6 * SONNET_OUTPUT_COST_PER_MTOK)

    avg_elapsed = sum(r.get("elapsed_s", 0) for r in results.values()) / total

    lines = [
        "=" * 70,
        "Agentic Loop v10 — Cluster Full Run (78 problems)",
        "=" * 70,
        f"Problems processed: {total}",
        f"Avg time/problem: {avg_elapsed:.0f}s | Total: {cycle_elapsed:.0f}s",
        "",
        "API usage (reflector = Claude Sonnet 4.6):",
        f"  {total_ref_in:,} in / {total_ref_out:,} out → ${ref_cost:.3f}",
        "",
        "RTL saved to: " + str(out_dir / "rtl"),
        "Next step: run CVDP cocotb Docker harness on the rtl/ directory locally.",
    ]
    summary = "\n".join(lines)
    print("\n" + summary)
    with open(out_dir / "summary.txt", "w") as f:
        f.write(summary + "\n")

    write_log(args.log, {
        "event": "run_complete",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total": total,
        "avg_elapsed_s": round(avg_elapsed, 1),
        "cycle_elapsed_s": round(cycle_elapsed, 1),
        "ref_cost": round(ref_cost, 4),
    })

    log.info(f"\nRun complete. Log: {args.log}")
    log.info(f"Output dir: {out_dir}")


if __name__ == "__main__":
    main()
