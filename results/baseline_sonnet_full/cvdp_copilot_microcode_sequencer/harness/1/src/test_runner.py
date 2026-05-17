import os
from pathlib import Path
from cocotb_tools.runner import get_runner
import pytest

# Fetch environment variables for simulation setup
verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang = os.getenv("TOPLEVEL_LANG", "verilog")
sim = os.getenv("SIM", "icarus")
toplevel = os.getenv("TOPLEVEL", "microcode_sequencer")
module = os.getenv("MODULE", "test_microcode_sequencer")
wave = os.getenv("WAVE", "0")

# Function to configure and run the simulation
def runner():
    """Runs the simulation for the microcode sequencer."""
    # Get the simulation runner
    simulation_runner = get_runner(sim)

    # Build the simulation environment
    simulation_runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        always=True,         # Always rebuild
        clean=True,          # Clean previous build files
        waves=True ,   # Enable waveform generation if WAVE=1
        verbose=True,        # Verbose build and simulation output
        timescale=("1ns", "1ns"),  # Set the timescale for simulation
        log_file="build.log"      # Log file for the build process
    )

    # Run the testbench
    simulation_runner.test(
        hdl_toplevel=toplevel,
        test_module=module,
        waves=True    # Enable waveform dump if WAVE=1
    )

# Pytest function to run the simulation
##@pytest.mark.simulation
def test_microcode_sequencer():
    """Pytest function to execute the microcode sequencer testbench."""
    print("Running microcode sequencer testbench...")
    runner()

