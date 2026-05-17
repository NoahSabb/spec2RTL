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

    # 1. Overwrite the RTL file with candidate Verilog
    rtl_path = os.path.join(harness_dir, "rtl", rtl_filename)
    with open(rtl_path, "w") as f:
        f.write(verilog_code)

    # 2. Find the harness shell script
    scripts = glob.glob(os.path.join(harness_dir, "run_docker_harness_*.sh"))
    if not scripts:
        return {
            "passed": False,
            "errors": "No harness script found",
            "output": "",
            "stage": "harness"
        }
    script = scripts[0]

    # 3. Run it and capture output
    result = subprocess.run(
        ["bash", script],
        capture_output=True,
        text=True,
        timeout=300
    )

    output = result.stdout + result.stderr
    passed = result.returncode == 0 and "FAILED" not in output

    return {
        "passed": passed,
        "errors": result.stderr,
        "output": result.stdout,
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

Analyze the failure and provide:
## Primary Error
- What went wrong at the signal/logic level

## Error Analysis  
- Why this error is occurring in the implementation

## Fix Guidance
- Specific, actionable changes to fix the RTL (no test vectors, no expected values)
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text

# ------------------------------- COORDINATOR -------------------------------

def coordinate(client: anthropic.Anthropic, context: list, reflection: str, verilog_code: str, iteration: int) -> str:
    
    context.append({
        "iteration": iteration,
        "verilog": verilog_code,
        "guidance": reflection,
    })
    
    history = ""
    for entry in context:
        history += f"""
Iteration {entry['iteration']}:
- Guidance: {entry['guidance']}
"""

    # Build explicit exclusion list from previous attempts
    exclusions = ""
    for entry in context:
        exclusions += f"- Iteration {entry['iteration']}: {entry['guidance'][:300]}\n"

    prompt = f"""You are managing an iterative RTL debugging process.

## Debugging History
{history}

## CRITICAL: Approaches Already Tried — DO NOT Suggest These Again
{exclusions}

Based on this history:
1. Is progress being made or are we stuck in the same failure?
2. Should we continue refining or restart fresh?

Respond with:
## Status
CONTINUE or RESTART

## Explicitly Forbidden Approaches
List the specific fixes that have already been tried and failed, so the generator avoids them.

## Updated Context
A concise summary of what has been tried, what failed, and what NEW approach the generator should focus on next. Be specific about what is different from previous attempts.
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text

# ------------------------------- MAIN LOOP -------------------------------

def extract_verilog(response) -> str:
    """Extract Verilog string from factory response."""
    if isinstance(response, tuple):
        d = response[0]
        if isinstance(d, dict) and "direct_text" in d:
            return d["direct_text"]
    if isinstance(response, str):
        return response
    return ""

def run_verilator_lint(verilog_code: str) -> dict:
    """Fast structural lint check using Verilator before full simulation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rtl_path = os.path.join(tmpdir, "design.v")
        with open(rtl_path, "w") as f:
            f.write(verilog_code)

        result = subprocess.run(
        ["verilator", "--lint-only", "-Wall", "-Wno-DECLFILENAME", rtl_path],
        capture_output=True, text=True
        )

        return {
            "passed": result.returncode == 0,
            "errors": result.stderr,
            "output": "",
            "stage": "lint"
        }

def run_single_process(generator, client, spec, max_iterations=10,
                       harness_dir=None, rtl_filename=None):
    context = []
    verilog = extract_verilog(generator.prompt(spec, category=3, files=["design.v"]))

    for iteration in range(1, max_iterations + 1):
        # Fast lint first — free
        lint_result = run_verilator_lint(verilog)
        if not lint_result["passed"]:
            sim_result = lint_result
        elif harness_dir and rtl_filename and os.path.exists(harness_dir):
            # Real harness feedback
            sim_result = run_harness(verilog, harness_dir, rtl_filename)
        else:
            # Fallback to fake testbench if harness not available
            logging.warning("Harness not found, falling back to generated testbench")
            testbench = generate_testbench(client, spec, verilog)
            sim_result = run_simulation(verilog, testbench)

        if sim_result["passed"]:
            return {"passed": True, "verilog": verilog, "iterations": iteration}

        reflection = reflect(client, spec, verilog, sim_result)
        coord_output = coordinate(client, context, reflection, verilog, iteration)

        # ── LOGGING: show what feedback was produced and what the generator does with it ──
        logging.info(f"=== ITERATION {iteration} REFLECTION ===\n{reflection}")
        logging.info(f"=== ITERATION {iteration} COORDINATOR ===\n{coord_output}")
        # ─────────────────────────────────────────────────────────────────────────────────

        verilog = extract_verilog(generator.prompt(spec + "\n\n" + coord_output, category=3, files=["design.v"]))

        # ── LOGGING: show first 500 chars of new verilog to see if it changed ──
        logging.info(f"=== ITERATION {iteration} NEW VERILOG (first 500 chars) ===\n{verilog[:500]}")
        # ────────────────────────────────────────────────────────────────────────

    return {"passed": False, "verilog": verilog, "iterations": max_iterations}


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