
import os
from cocotb_tools.runner import get_runner
import pytest

verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")
wave            = os.getenv("WAVE")

def test_runner(DATA_WIDTH: int=8, FILO_DEPTH: int=8 ):
    parameter = {"DATA_WIDTH":DATA_WIDTH, "FILO_DEPTH":FILO_DEPTH}
    
    # Debug information
    print(f"[DEBUG] Running simulation with DATA_WIDTH={DATA_WIDTH}, FILO_DEPTH={FILO_DEPTH}")
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
        timescale=("1ns", "1ns"),
        log_file="build.log")

    runner.test(hdl_toplevel=toplevel, test_module=module, waves=True)   

# Parametrize test for different WIDTH and WINDOW_SIZE
@pytest.mark.parametrize("DATA_WIDTH", [10,12])
@pytest.mark.parametrize("FILO_DEPTH", [12,16])

#@pytest.mark.parametrize("test", range(1))
def test_filo(DATA_WIDTH, FILO_DEPTH):
    # Run the simulation with specified parameters
    test_runner(DATA_WIDTH=DATA_WIDTH, FILO_DEPTH=FILO_DEPTH)
