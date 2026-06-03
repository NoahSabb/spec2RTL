import subprocess
import tempfile
import os
import concurrent.futures
import logging

# ------------------------------- SIMULATION -------------------------------

def run_simulation(verilog_code: str, testbench: str = None) -> dict:
    """Fallback simulation using iverilog when harness not available."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rtl_path = os.path.join(tmpdir, "design.v")
        out_path = os.path.join(tmpdir, "sim.vvp")
        with open(rtl_path, "w") as f:
            f.write(verilog_code)
        sources = [rtl_path]
        if testbench:
            tb_path = os.path.join(tmpdir, "testbench.v")
            with open(tb_path, "w") as f:
                f.write(testbench)
            sources.append(tb_path)
        compile_result = subprocess.run(
            ["iverilog", "-g2012", "-o", out_path] + sources,
            capture_output=True, text=True
        )
        if compile_result.returncode != 0:
            return {"passed": False, "errors": compile_result.stderr, "output": "", "stage": "compile"}
        sim_result = subprocess.run(["vvp", out_path], capture_output=True, text=True, timeout=30)
        output = sim_result.stdout + sim_result.stderr
        failed = sim_result.returncode != 0 or "error" in output.lower() or "fatal" in output.lower()
        return {"passed": not failed, "errors": sim_result.stderr, "output": sim_result.stdout, "stage": "simulation"}

def run_harness(verilog_code: str, harness_dir: str, rtl_filename: str) -> dict:
    """
    Run the real CVDP harness by overwriting the RTL file and executing
    the pre-generated harness shell script. Returns structured result
    with stdout captured for the Reflector.

    harness_dir: path to harness/1/ directory (e.g. work_x/cvdp_copilot_gcd/harness/1)
    rtl_filename: the .sv or .v filename (e.g. gcd_top.sv)
    """
    import glob
    import re

    rtl_path = os.path.join(harness_dir, "rtl", rtl_filename)
    with open(rtl_path, "w") as f:
        f.write(verilog_code.strip() + "\n")

    scripts = glob.glob(os.path.join(harness_dir, "run_docker_harness_*.sh"))
    if not scripts:
        return {
            "passed": False,
            "errors": "No harness script found",
            "output": "",
            "stage": "harness"
        }
    script = scripts[0]

    result = subprocess.run(
        ["bash", script],
        capture_output=True,
        text=True,
        timeout=300
    )

    output = result.stdout + result.stderr

    # sim.log is often empty; the real failures are in sim_build/*.result.xml
    xml_failures = []
    for xml_file in glob.glob(os.path.join(harness_dir, "rundir", "sim_build", "*.result.xml")):
        try:
            with open(xml_file) as f:
                xml_content = f.read()
            # Pull out error_msg attributes — these contain the actual assertion failures
            for msg in re.findall(r'error_msg="([^"]*)"', xml_content):
                xml_failures.append(msg.replace("&#10;", "\n").replace("&#9;", "\t"))
        except Exception:
            pass

    if xml_failures:
        output += "\n\n=== TEST FAILURES ===\n" + "\n---\n".join(xml_failures)

    sim_log_path = os.path.join(harness_dir, "rundir", "sim.log")
    if os.path.exists(sim_log_path):
        with open(sim_log_path) as f:
            sim_log = f.read()
        if sim_log.strip():
            output += "\n\n=== SIM LOG ===\n" + sim_log

    passed = result.returncode == 0 and not xml_failures and "FAILED" not in output

    return {
        "passed": passed,
        "errors": result.stderr,
        "output": output,
        "stage": "harness"
    }

# ------------------------------- REFLECTOR -------------------------------

import anthropic


def reflect(client: anthropic.Anthropic, spec: str, verilog_code: str, sim_result: dict) -> str:
    """
    Analyzes simulation errors and produces fix guidance.
    Does NOT see test vectors - only sees error messages and signal behavior.
    """

    prompt = f"""You are an expert RTL hardware engineer analyzing a failed Verilog simulation.

## Specification
{spec}

## Current Verilog Implementation
{verilog_code}

## Simulation Failure
Stage: {sim_result['stage']}
Errors: {sim_result['errors']}
Output: {sim_result['output']}

Respond in exactly this format:
## Hypothesis
One sentence: what signal or logic block is wrong and why.

## Required Change
The single most important RTL change needed. Name the exact signal, always/logic block, or port. Do not suggest more than one change.
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text

# ------------------------------- COORDINATOR -------------------------------

def coordinate(client: anthropic.Anthropic, context: list, reflection: str,
               verilog_code: str, iteration: int, sim_result: dict, spec: str = "") -> dict:
    """
    Maintains self-evolving context across iterations. Returns a dict with:
      - decision: "CONTINUE" or "RESTART"
      - guidance: updated context / fix instructions for the generator
      - insights: (on RESTART only) high-level lessons distilled from failed attempts
    """

    # Record this iteration's outcome before asking coordinator to decide
    context.append({
        "iteration": iteration,
        "verilog_snippet": verilog_code[:300],
        "guidance_given": reflection,
        "outcome": "FAILED",
        "stage": sim_result.get("stage", "unknown"),
        "errors_summary": sim_result.get("output", "")[:2000],
    })

    history = ""
    for entry in context:
        history += f"""
Iteration {entry['iteration']} [{entry['outcome']}]:
  Stage: {entry['stage']}
  Error summary: {entry['errors_summary']}
  Guidance that was tried: {entry['guidance_given']}
"""

    prompt = f"""You are coordinating a Verilog debugging loop. Study the iteration history below and decide whether to CONTINUE refining the current implementation or RESTART from scratch.

## Debugging History
{history}

## Decision Rules
- Choose RESTART if: the same root error persists for 2+ consecutive iterations despite different guidance, OR the error pattern shows a fundamentally wrong architectural approach that cannot be patched incrementally.
- Choose CONTINUE if: each iteration shows a different or progressing error, OR this is only the first iteration of this failure type.

You are talking directly to a Verilog code generator that has the full RTL in front of it.
- Never reference filenames or file paths.
- Always give concrete, actionable RTL-level instructions (signal names, always/logic blocks, ports).

Respond in EXACTLY this format (no extra text):
## DECISION
CONTINUE  (or RESTART)

## GUIDANCE
<If CONTINUE: specific signal-level fix instructions for next attempt.>
<If RESTART: high-level architectural insight from the failures — what approach is fundamentally wrong and what different approach the generator should try from scratch.>

## FORBIDDEN
<One bullet per approach that has already been tried and failed. Be precise about what was tried.>
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text

    # Parse decision
    decision = "CONTINUE"
    if "## DECISION" in raw:
        decision_line = raw.split("## DECISION")[-1].split("##")[0].strip().upper()
        if "RESTART" in decision_line:
            decision = "RESTART"

    guidance = ""
    if "## GUIDANCE" in raw:
        guidance = raw.split("## GUIDANCE")[-1].split("## FORBIDDEN")[0].strip()

    forbidden = ""
    if "## FORBIDDEN" in raw:
        forbidden = raw.split("## FORBIDDEN")[-1].strip()

    return {
        "decision": decision,
        "guidance": guidance,
        "forbidden": forbidden,
        "raw": raw,
    }

# ------------------------------- MAIN LOOP -------------------------------

def extract_verilog(response) -> str:
    if isinstance(response, tuple):
        d = response[0]
        if isinstance(d, dict) and "direct_text" in d:
            response = d["direct_text"]
    if not isinstance(response, str):
        return ""
    import re
    match = re.search(r'```(?:verilog|systemverilog|sv)?\s*\n(.*?)```', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response.strip()


def run_single_process(generator, client, spec, max_iterations=10,
                       harness_dir=None, rtl_filename=None):
    context = []
    restart_count = 0
    max_restarts = 3

    verilog = extract_verilog(generator.prompt(spec, category=3, files=["design.v"]))

    iteration = 0
    while iteration < max_iterations:
        iteration += 1

        if harness_dir and rtl_filename and os.path.exists(harness_dir):
            sim_result = run_harness(verilog, harness_dir, rtl_filename)
        else:
            logging.warning("Harness not found, falling back to generated testbench")
            testbench = generate_testbench(client, spec, verilog)
            sim_result = run_simulation(verilog, testbench)

        if sim_result["passed"]:
            return {"passed": True, "verilog": verilog, "iterations": iteration,
                    "restarts": restart_count}

        reflection = reflect(client, spec, verilog, sim_result)
        coord = coordinate(client, context, reflection, verilog, iteration, sim_result, spec=spec)

        logging.info(f"=== ITERATION {iteration} REFLECTION ===\n{reflection}")
        logging.info(f"=== ITERATION {iteration} COORDINATOR: {coord['decision']} ===\n{coord['raw']}")

        # Truncate raw error to 1500 chars for generator prompts — enough to see the failure
        raw_error = sim_result.get("output", "")[-1500:] if sim_result.get("output") else ""

        if coord["decision"] == "RESTART" and restart_count < max_restarts:
            restart_count += 1
            logging.info(f"=== RESTART #{restart_count} triggered at iteration {iteration} ===")

            restart_prompt = (
                f"{spec}\n\n"
                f"## Lessons from failed attempts\n{coord['guidance']}\n\n"
                f"## Do NOT use these approaches\n{coord['forbidden']}\n\n"
                f"## Last seen error\n{raw_error}"
            )
            verilog = extract_verilog(generator.prompt(restart_prompt, category=3, files=["design.v"]))

            context = []
            logging.info(f"=== RESTART #{restart_count} new verilog (first 300 chars) ===\n{verilog[:300]}")
            continue

        # CONTINUE path: generator sees spec + previous RTL + actual error + targeted guidance
        fix_prompt = (
            f"## Specification\n{spec}\n\n"
            f"## Previous Attempt\n```verilog\n{verilog}\n```\n\n"
            f"## Actual Test Failure\n{raw_error}\n\n"
            f"## What To Fix\n{coord['guidance']}\n\n"
            f"## Do NOT repeat these approaches\n{coord['forbidden']}"
        )
        verilog = extract_verilog(generator.prompt(fix_prompt, category=3, files=["design.v"]))

        logging.info(f"=== ITERATION {iteration} NEW VERILOG (first 300 chars) ===\n{verilog[:300]}")

    return {"passed": False, "verilog": verilog, "iterations": iteration,
            "restarts": restart_count}


def run_parallel(generator, client, spec, num_processes=5, max_iterations=10,
                 harness_dir=None, rtl_filename=None):
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_processes) as executor:
        futures = [
            executor.submit(run_single_process, generator, client, spec,
                            max_iterations, harness_dir, rtl_filename)
            for _ in range(num_processes)
        ]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result["passed"]:
                for f in futures:
                    f.cancel()
                return result

    return futures[-1].result()

# ------------------------------- TESTBENCH -------------------------------

def generate_testbench(client: anthropic.Anthropic, spec: str, verilog_code: str) -> str:
    """
    Generate a simple self-checking Verilog testbench for the given RTL.
    Checks functional correctness without using specific test vectors from CVDP.
    """
    prompt = f"""You are an expert RTL verification engineer.

## Specification
{spec}

## Verilog Implementation
{verilog_code}

Write a simple self-checking Verilog testbench that:
1. Instantiates the module above
2. Applies a clock if needed
3. Tests basic functional behavior based on the spec
4. Uses $display and $finish
5. Uses $error or $fatal if outputs are wrong
6. Keeps it simple — no cocotb, no Python, pure Verilog only
7. Must finish with $finish

Only respond with the Verilog testbench code, nothing else.
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text.strip()
