# test_runner.py

import os
from cocotb_tools.runner import get_runner
import pytest
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch environment variables
verilog_sources = os.getenv("VERILOG_SOURCES", "").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG", "verilog")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")

def runner(gpio_width):
    """
    Runs the cocotb simulation with the specified GPIO_WIDTH parameter.

    Args:
        gpio_width (int): The GPIO_WIDTH value to test.
    """
    logger.info(f"Starting simulation with GPIO_WIDTH = {gpio_width}")

    # Initialize the simulator runner
    runner = get_runner(sim)

    # Build the simulation with the specified GPIO_WIDTH parameter
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        parameters={"GPIO_WIDTH": gpio_width},  # Pass GPIO_WIDTH parameter
        # Simulator Arguments
        always=True,
        clean=True,
        waves=False,        # Disable waveform generation for faster runs
        verbose=False,      # Set to True for detailed simulator logs
        timescale=("1ns", "1ps"),
        log_file=f"sim_{gpio_width}.log"
    )

    # Run the simulation
    runner.test(
        hdl_toplevel=toplevel,
        test_module=module,
        waves=False
    )

    logger.info(f"Completed simulation with GPIO_WIDTH = {gpio_width}")

@pytest.mark.parametrize("gpio_width", [8, 11, 30])  # Add desired GPIO_WIDTH values here
def test_cvdp_copilot_apb_gpio(gpio_width):
    """
    Pytest function to run cocotb simulations with different GPIO_WIDTH parameters.

    Args:
        gpio_width (int): The GPIO_WIDTH value to test.
    """
    try:
        runner(gpio_width)
    except Exception as e:
        logger.error(f"Simulation failed for GPIO_WIDTH = {gpio_width}: {e}")
        # Using assert False to report failure without halting other tests
        assert False, f"Simulation failed for GPIO_WIDTH = {gpio_width}: {e}"
