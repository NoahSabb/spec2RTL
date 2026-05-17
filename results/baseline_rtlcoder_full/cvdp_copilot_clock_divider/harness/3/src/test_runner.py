import os
from cocotb_tools.runner import get_runner
import pytest
import pickle

# Gather environment variables for simulation settings
verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")

# Parametrized test to run the simulation
@pytest.mark.parametrize("test", range(1))
def test_clock_divider_run(test):
    # os.rmdir("sim_build")
    # os.remove("./sim_build/sim.vvp")    
    # Get the simulator runner for the specified simulator (e.g., icarus)
    runner = get_runner(sim)
    
    # Build the simulation environment
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        clean=True,              # Clean previous builds
        # verbose=True,            
        timescale=("1ns", "1ns"), # Set timescale
        log_file="sim.log"        # Log the output of the simulation
    )
    
    # Run the test module
    runner.test(hdl_toplevel=toplevel, test_module=module)

# Uncomment the following line if you want to run the test directly (for standalone execution)
# if __name__ == "__main__":
#     test_clock_divider_run()
