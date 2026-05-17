import os
from pathlib import Path
from cocotb_tools.runner import get_runner
import random
import pytest

verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")
wave            = os.getenv("WAVE")
# plus_args       = os.getenv("PLUSARGS")
# compile_args    = os.getenv("COMPILE_ARGS")

@pytest.mark.parametrize("test", range(10))
def test_moving_run(test):
    encoder_in = random.randint(0, 255)

    plusargs=[f'+encoder_in={encoder_in}']

    runner = get_runner(sim)
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        # Arguments
        # parameters=parameter,
        always=True,
        clean=True,
        verbose=True,
        timescale=("1ns", "1ns"),
        log_file="sim.log")
    runner.test(hdl_toplevel=toplevel, test_module=module, plusargs=plusargs, waves=True)
