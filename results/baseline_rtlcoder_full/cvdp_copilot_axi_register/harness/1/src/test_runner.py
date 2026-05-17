import os
from cocotb_tools.runner import get_runner
import pytest

verilog_sources = os.getenv("VERILOG_SOURCES").split()
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")
wave            = bool(os.getenv("WAVE"))

def runner(ADDR_WIDTH : int = 32 ,DATA_WIDTH: int= 32 ):

    parameter = {
        "ADDR_WIDTH": ADDR_WIDTH,
        "DATA_WIDTH": DATA_WIDTH
    }
    print(f"[DEBUG] Parameters: {parameter}") 
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


@pytest.mark.parametrize("test", range(1))
@pytest.mark.parametrize("ADDR_WIDTH", [12,16,32])
@pytest.mark.parametrize("DATA_WIDTH", [8,16,32,64])
def test_axi_reg(test,ADDR_WIDTH,DATA_WIDTH):
        runner(DATA_WIDTH = DATA_WIDTH ,ADDR_WIDTH = ADDR_WIDTH )