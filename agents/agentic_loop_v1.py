import subprocess
import tempfile
import os
import concurrent.futures

# ------------------------------- SIMULATION -------------------------------

def run_simulation(verilog_code: str) -> dict:
    """
    Compile and simulate Verilog using iverilog + vvp.
    Returns a dict with: passed (bool), errors (str), output (str)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        rtl_path = os.path.join(tmpdir, "design.v")
        out_path = os.path.join(tmpdir, "sim.vvp")

        # Write Verilog to file
        with open(rtl_path, "w") as f:
            f.write(verilog_code)

        # Compile
        compile_result = subprocess.run(
            ["iverilog", "-g2012", "-o", out_path, rtl_path],
            capture_output=True, text=True
        )

        if compile_result.returncode != 0:
            return {
                "passed": False,
                "errors": compile_result.stderr,
                "output": "",
                "stage": "compile"
            }

        # Simulate
        sim_result = subprocess.run(
            ["vvp", out_path],
            capture_output=True, text=True, timeout=30
        )

        passed = sim_result.returncode == 0
        return {
            "passed": passed,
            "errors": sim_result.stderr,
            "output": sim_result.stdout,
            "stage": "simulation"
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
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text

# ------------------------------- COORDINATOR -------------------------------

def coordinate(client: anthropic.Anthropic, context: list, reflection: str, verilog_code: str, iteration: int) -> str:
    """
    Maintains the self-evolving context across iterations.
    Decides whether to continue refining or trigger a restart.
    Returns the updated context as a string to feed back to the Generator.
    """
    
    # Append this iteration to the history
    context.append({
        "iteration": iteration,
        "verilog": verilog_code,
        "guidance": reflection,
    })
    
    # Build the history string
    history = ""
    for entry in context:
        history += f"""
Iteration {entry['iteration']}:
- Guidance: {entry['guidance']}
"""

    prompt = f"""You are managing an iterative RTL debugging process.

## Debugging History
{history}

Based on this history:
1. Is progress being made or are we stuck in the same failure?
2. Should we continue refining the current implementation or restart fresh?

Respond with:
## Status
CONTINUE or RESTART

## Updated Context
A concise summary of what has been tried, what failed, and what the generator should focus on next.
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
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

def run_single_process(generator, client: anthropic.Anthropic, spec: str, max_iterations: int = 10) -> dict:
    """
    Single ACE-RTL process: Generator → Simulate → Reflect → Coordinate → repeat.
    """
    context = []
    verilog = extract_verilog(generator.prompt(spec, category=3, files=["design.v"]))

    for iteration in range(1, max_iterations + 1):
        sim_result = run_simulation(verilog)

        if sim_result["passed"]:
            return {"passed": True, "verilog": verilog, "iterations": iteration}

        reflection = reflect(client, spec, verilog, sim_result)
        coord_output = coordinate(client, context, reflection, verilog, iteration)

        # Feed evolved context back to generator
        verilog = extract_verilog(generator.prompt(spec + "\n\n" + coord_output, category=3, files=["design.v"]))

    return {"passed": False, "verilog": verilog, "iterations": max_iterations}


def run_parallel(generator, client: anthropic.Anthropic, spec: str, num_processes: int = 5, max_iterations: int = 10) -> dict:
    """
    Launch N independent processes in parallel.
    First to pass kills the rest.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_processes) as executor:
        futures = [
            executor.submit(run_single_process, generator, client, spec, max_iterations)
            for _ in range(num_processes)
        ]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result["passed"]:
                for f in futures:
                    f.cancel()
                return result

    return futures[-1].result()