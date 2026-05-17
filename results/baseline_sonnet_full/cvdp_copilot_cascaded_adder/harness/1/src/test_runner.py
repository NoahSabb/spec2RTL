import os
from cocotb_tools.runner import get_runner
import random
import pytest

verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")
wave            = bool(os.getenv("WAVE"))

def runner(IN_DATA_NS, IN_DATA_WIDTH):
    runner = get_runner(sim)
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        parameters= {'IN_DATA_NS': IN_DATA_NS , 'IN_DATA_WIDTH': IN_DATA_WIDTH },
        always=True,
        clean=True,
        verbose=False,
        timescale=("1ns", "1ns"),
        log_file="sim.log")
    runner.test(hdl_toplevel=toplevel, test_module=module, waves=wave)

test_param = [(random.randint(1, 500), random.randint(1, 500)) for _ in range(5)]

# random test
@pytest.mark.parametrize("IN_DATA_NS ,IN_DATA_WIDTH", test_param )

# random test
def test_tree_adder(IN_DATA_NS, IN_DATA_WIDTH):
    print(f'Running with: IN_DATA_NS = {IN_DATA_NS}, IN_DATA_WIDTH = {IN_DATA_WIDTH}')
    runner(IN_DATA_NS, IN_DATA_WIDTH)