import cocotb
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

def runner(N: int = 8, DATA_WIDTH: int = 16, DEC_FACTOR: int = 4):
    # Simulation parameters
    parameter = {
        "N": N,
        "DATA_WIDTH": DATA_WIDTH,
        "DEC_FACTOR": DEC_FACTOR
    }

    # Debug information
    print(f"[DEBUG] Running simulation with N={N}")
    print(f"[DEBUG] Running simulation with DATA_WIDTH={DATA_WIDTH}")
    print(f"[DEBUG] Running simulation with DEC_FACTOR={DEC_FACTOR}")
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

# Generate random valid parameters
random_n          = [8]  + [4, 8, random.randint(4, 32)]
random_data_width = [16] + [8, 16, random.randint(8, 32)]

def generate_valid_dec_factors(n):
    """Generate a list of valid DEC_FACTOR values that divide N."""
    return [i for i in range(1, n + 1) if n % i == 0]

# Parametrize test for different random sizes
@pytest.mark.parametrize("N", random_n)
@pytest.mark.parametrize("DATA_WIDTH", random_data_width)
@pytest.mark.parametrize("test", range(2))
def test_data(N, DATA_WIDTH, test):
    # Generate valid DEC_FACTOR values dynamically
    valid_dec_factors = generate_valid_dec_factors(N)
    # Randomly select a DEC_FACTOR from the valid options
    DEC_FACTOR = random.choice(valid_dec_factors)

    # Debug information
    print(f"[DEBUG] Selected DEC_FACTOR={DEC_FACTOR} for N={N}")

    # Run the simulation with specified parameters
    runner(N=N, DATA_WIDTH=DATA_WIDTH, DEC_FACTOR=DEC_FACTOR)
