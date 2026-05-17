import os
from cocotb_tools.runner import get_runner
import pytest

verilog_sources = os.getenv("VERILOG_SOURCES").split()
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")
wave            = bool(os.getenv("WAVE"))

def runner(C_S_AXI_ADDR_WIDTH : int = 8 ,C_S_AXI_DATA_WIDTH: int= 32 ):

    parameter = {
        "C_S_AXI_ADDR_WIDTH": C_S_AXI_ADDR_WIDTH,
        "C_S_AXI_DATA_WIDTH": C_S_AXI_DATA_WIDTH
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
@pytest.mark.parametrize("C_S_AXI_ADDR_WIDTH", [8,16,32])
@pytest.mark.parametrize("C_S_AXI_DATA_WIDTH", [32,64,48])
def test_axi_reg(test,C_S_AXI_ADDR_WIDTH,C_S_AXI_DATA_WIDTH):
        runner(C_S_AXI_DATA_WIDTH = C_S_AXI_DATA_WIDTH ,C_S_AXI_ADDR_WIDTH = C_S_AXI_ADDR_WIDTH )