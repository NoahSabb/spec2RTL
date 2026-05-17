import os
# from cocotb_tools.runner import get_runner
from cocotb_tools.runner import get_runner
import pytest
import pickle

verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")

@pytest.mark.tb
def test_palindrome_detect():
    # os.rmdir("sim_build")
    # os.remove("./sim_build/sim.vvp")
    runner = get_runner(sim)
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        # Arguments
        always=True,
        clean=True,
        verbose=True,
        timescale=("1ns", "1ns"),
        log_file="sim.log")
    runner.test(hdl_toplevel=toplevel, test_module=module, waves=True)