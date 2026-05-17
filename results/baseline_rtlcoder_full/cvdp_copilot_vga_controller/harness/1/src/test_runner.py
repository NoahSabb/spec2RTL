import os
from pathlib import Path
from cocotb_tools.runner import get_runner
import pytest
import logging

# Getting environment variables
verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang = os.getenv("TOPLEVEL_LANG")
sim = os.getenv("SIM", "icarus")
toplevel = os.getenv("TOPLEVEL")
module = os.getenv("MODULE", "vga_controller_cocotb_testbench")
wave = os.getenv("WAVE")

# Define the runner function
def runner():
    """Runs the simulation for the VGA driver."""
    runner = get_runner(sim)
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        always=True,
        clean=True,
        waves=True if wave == "1" else False,
        verbose=True,
        timescale=("1ns", "1ns"),
        log_file="build.log"
    )

    runner.test(hdl_toplevel=toplevel, test_module=module, waves=True if wave == "1" else False)

# Pytest function to run the testbench
def test_vga_driver():
    """Pytest function to invoke the Cocotb test for VGA driver."""
    print("Running VGA Driver Cocotb Test...")
    runner()

