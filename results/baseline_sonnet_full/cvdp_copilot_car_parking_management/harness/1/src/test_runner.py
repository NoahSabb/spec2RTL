import os
from pathlib import Path
from cocotb_tools.runner import get_runner
import pytest
import re
import logging

# List from Files
verilog_sources = os.getenv("VERILOG_SOURCES").split()
    
# Language of Top Level File
toplevel_lang = os.getenv("TOPLEVEL_LANG")
sim = os.getenv("SIM", "icarus")
toplevel = os.getenv("TOPLEVEL")
module = os.getenv("MODULE")

def test_runner(TOTAL_SPACES: int = 9):
    """
    Test Runner for Car Parking System
    """

    # Parameterize the test
    parameter_defines = {
        "TOTAL_SPACES": TOTAL_SPACES,
    }
    print(f"Running simulation with TOTAL_SPACES={TOTAL_SPACES}")
    
    runner = get_runner(sim)
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        parameters=parameter_defines,
        always=True,
        clean=True,
        verbose=True,
        timescale=("1ns", "1ps"),
        log_file="sim.log",
        defines={"SIMULATION": 1}
    )

    plusargs = [f"+TOTAL_SPACES={TOTAL_SPACES}"]
    runner.test(hdl_toplevel=toplevel, test_module=module, waves=True, plusargs=plusargs)

@pytest.mark.parametrize("TOTAL_SPACES", [14, 12, 9])
def test_car_parking_system(TOTAL_SPACES):
    """Parameterized test for Car Parking System"""

    print(f"Test Runner: TOTAL_SPACES={TOTAL_SPACES}")
    test_runner(TOTAL_SPACES=TOTAL_SPACES)
