import os
import pytest
import random
from cocotb_tools.runner import get_runner

# Environment configuration
verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")
wave            = bool(os.getenv("WAVE"))

def runner(N: int = 4):
    # Simulation parameters
    parameter = {
        "N": N
    }

    # Debug information
    print(f"[DEBUG] Running simulation with N={N}")
    print(f"[DEBUG] Parameters: {parameter}")

    # Configure and run the simulation
    sim_runner = get_runner(sim)
    sim_runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        parameters=parameter,
        always=True,
        clean=True,
        verbose=True,
        timescale=("1ns", "1ns"),
        log_file="sim.log"
    )

    # Run the test
    sim_runner.test(hdl_toplevel=toplevel, test_module=module, waves=True)

# Generate minimum(2), default(4), and random even values for N
random_n_values = [2] + [4] + [random.randint(2, 8) * 2 for _ in range(10)]

# Parametrize test for different even sizes of N
@pytest.mark.parametrize("N", random_n_values)
@pytest.mark.parametrize("test", range(5))
def test_data(N, test):
    # Run the simulation with specified parameters
    runner(N=N)