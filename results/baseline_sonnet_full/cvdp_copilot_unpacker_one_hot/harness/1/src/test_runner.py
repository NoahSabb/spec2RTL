# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

# test_runner.py

import os
from cocotb_tools.runner import get_runner
import pytest
import pickle

verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")

@pytest.mark.tb
def test_runner():

    runner = get_runner(sim)
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        # Arguments
        always=True,
        clean=True,
        verbose=True,
        timescale=("1ns", "1ps"),
        log_file="sim.log")
    runner.test(hdl_toplevel=toplevel, test_module=module, waves=True)


if __name__ == "__main__":
   test_runner()