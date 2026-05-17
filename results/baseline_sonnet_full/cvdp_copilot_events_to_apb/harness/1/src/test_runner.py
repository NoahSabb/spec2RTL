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

def runner():
    
    num_iterations = os.getenv("NUM_ITERATIONS", 5)
    os.environ["NUM_ITERATIONS"] = str(num_iterations)

    # Configure runner
    runner = get_runner(sim)
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        always=True,
        clean=True,
        verbose=True,
        timescale=("1ns", "1ns"),
        log_file="sim.log"
    )

    for i in range(num_iterations):
        runner.test(hdl_toplevel=toplevel, test_module=module, waves=True)


def test_apb():
    # Run the simulation
    runner()   
