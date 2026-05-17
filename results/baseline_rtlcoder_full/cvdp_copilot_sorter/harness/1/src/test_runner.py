# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

# test_runner.py

import os
from pathlib import Path
from cocotb_tools.runner import get_runner
import pytest

verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")
wave            = os.getenv("WAVE")

def test_runner(WIDTH: int=5,N: int=4):
    
    parameter = {"WIDTH":WIDTH, "N":N}
    # Debug information
    print(f"[DEBUG] Running simulation with WIDTH={WIDTH}, N={N}")
    print(f"[DEBUG] Parameters: {parameter}")

    runner = get_runner(sim)
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,

        # Arguments
        always=True,
        clean=True,
        verbose=True,
        parameters=parameter,
        timescale=("1ns", "1ps"),
        log_file="sim.log")

    runner.test(hdl_toplevel=toplevel, test_module=module, waves=True)

# Parametrize test for different WIDTH and SIGNED_EN
@pytest.mark.parametrize("WIDTH", [4,8,12,16])
@pytest.mark.parametrize("N", [4,8,12,16])

def test_gcd(WIDTH,N):
    # Run the simulation with specified parameters
    test_runner(WIDTH=WIDTH,N=N)