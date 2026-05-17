from cocotb.triggers import RisingEdge
from cocotb.utils import get_sim_time
import random

# Reset the DUT
async def reset_dut(dut):
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    dut.rst_n._log.debug("Reset complete")

# Measure period of clk_out 
async def measure_clk_period(clk_out, clock, expected_period):
    # Wait for the first rising edge 
    await RisingEdge(clk_out)
    start_time = get_sim_time('ns')

    # Wait for the next rising edge 
    await RisingEdge(clk_out)
    end_time = get_sim_time('ns')

    # Calculating the period
    clk_out_period = end_time - start_time
    clk_out._log.debug(f"Measured clk_out period: {clk_out_period} ns")

    assert clk_out_period == expected_period, f"Error: clk_out period {clk_out_period} ns does not match expected {expected_period} ns"

    return clk_out_period