import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
import harness_library as hrs_lb

@cocotb.test()
async def test_clock_divider(dut):
    # Start the clock
    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())
    # Reset the DUT
    await hrs_lb.reset_dut(dut)
    dut._log.info("Reset initialized, ready for sequential sel value tests.")
    
    # Perform test for each `sel` value sequentially
    for sel_value in range(3):  # sel = 0, 1, 2
        # Apply select value
        dut.sel.value = sel_value
        dut._log.info(f"Applying sel = {sel_value}")

        # Synchronize with clock and stabilize
        for _ in range(16):
            await RisingEdge(dut.clk)

        # Check clock behavior after applying `sel`
        div_factor = 2 ** (sel_value + 1)
        expected_period = div_factor * 10  # Adjust period according to the divider
        clk_out_period = await hrs_lb.measure_clk_period(dut.clk_out, dut.clk, expected_period)
        dut._log.info(f"Test passed for sel = {sel_value}, clk_out is clk/{div_factor}")

        # Now reset the DUT before moving to the next `sel` value
        dut._log.info(f"Asserting reset before changing sel from {sel_value}")
        dut.rst_n.value = 0  # Assert reset

        # Synchronize with clock
        for _ in range(2):  # Holding reset
            await RisingEdge(dut.clk)

        # Deassert reset
        dut.rst_n.value = 1
        dut._log.info(f"Reset deasserted, moving to next sel value after {sel_value}")

    # Test for sel = 3 (default case)
    dut.sel.value = 3
    for _ in range(4):
        await RisingEdge(dut.clk)

    # Check if clk_out is 0 when sel = 3
    assert dut.clk_out.value == 0, "Error: clk_out is not 0 when sel = 3"
    dut._log.info("Test passed for sel = 3: clk_out = 0")
