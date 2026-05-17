import os
from cocotb_tools.runner import get_runner
import pytest

verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")
wave            = bool(os.getenv("WAVE"))

def runner(CHECK_MODE: int=0 , POLY_LENGTH: int=0, POLY_TAP: int=0, WIDTH: int=0):
    parameter = {"CHECK_MODE":CHECK_MODE, "POLY_LENGTH":POLY_LENGTH, "POLY_TAP":POLY_TAP, "WIDTH":WIDTH }
    # Debug information
    print(f"[DEBUG] Running simulation with CHECK_MODE={CHECK_MODE}, POLY_LENGTH={POLY_LENGTH}, POLY_TAP={POLY_TAP}, WIDTH={WIDTH}")
    print(f"[DEBUG] Parameters: {parameter}")
    
    runner = get_runner(sim)
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        always=True,
        clean=True,
        verbose=True,
        parameters=parameter,
        timescale=("1ns", "1ns"),
        log_file="sim.log")
    runner.test(hdl_toplevel=toplevel, test_module=module, waves=wave)

# Parametrize test for different parameters
@pytest.mark.parametrize("CHECK_MODE", [0,1])
@pytest.mark.parametrize("POLY_LENGTH", [7,23,31])
@pytest.mark.parametrize("POLY_TAP", [1,3,5])
@pytest.mark.parametrize("WIDTH", [8,16,32])
def test_prbs(CHECK_MODE, POLY_LENGTH, POLY_TAP, WIDTH):
    # Run the simulation with specified parameters
    runner(CHECK_MODE=CHECK_MODE, POLY_LENGTH=POLY_LENGTH, POLY_TAP=POLY_TAP, WIDTH=WIDTH)
