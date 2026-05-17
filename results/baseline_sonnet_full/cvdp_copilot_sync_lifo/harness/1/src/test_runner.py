import os
from cocotb_tools.runner import get_runner
import pytest
import math

verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")
wave            = bool(os.getenv("WAVE"))

def runner(DATA_WIDTH: int=0):
    ADDR_WIDTH = math.ceil(math.log2(DATA_WIDTH))  # Calculate ADDR_WIDTH based on DATA_WIDTH
    parameter = {"DATA_WIDTH":DATA_WIDTH,"ADDR_WIDTH":ADDR_WIDTH}
    runner = get_runner(sim)
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        # Arguments
        parameters=parameter,
        always=True,
        clean=True,
        verbose=True,
        timescale=("1ns", "1ns"),
        log_file="sim.log")
    runner.test(hdl_toplevel=toplevel, test_module=module, waves=wave)


@pytest.mark.parametrize("DATA_WIDTH", [4,8,16,64,128])
def test_areg_param(DATA_WIDTH):
        runner(DATA_WIDTH = DATA_WIDTH)