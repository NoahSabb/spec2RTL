import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ClockCycles, Timer
import random
import time
import harness_library as hrs_lb

@cocotb.test()
async def test_restoring_division(dut):
    # Retrieve the width of the data from the DUT's WIDTH parameter
    data_wd = int(dut.WIDTH.value)
    print(f"data_wd = {data_wd}")
    # Start the clock with a 10 nanosecond period
    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())
    
    # Initialize the DUT signals to default values (usually zero)
    await hrs_lb.dut_init(dut)

    # Apply an asynchronous reset to the DUT; reset is active low
    await hrs_lb.reset_dut(dut.rst, duration_ns=25, active=False)

    # Determine a random number of test cycles between 20 to 50
    cycle_num = random.randint(20, 50)
    # Schedule a reset at the midpoint of the test cycles
    reset_cycle = cycle_num // 2
    print(f"[INFO] Total cycles = {cycle_num}, Reset will be applied at cycle {reset_cycle}")
    
    # Execute a loop through the predetermined number of cycles
    for cycle in range(cycle_num):
        # Apply reset halfway through the test
        if cycle == reset_cycle:
            # Assert the reset signal (active low)
            dut.rst.value = 0
            # Wait for two clock cycles while the reset is active
            await RisingEdge(dut.clk)
            await RisingEdge(dut.clk)
            # Check if the outputs are correctly reset to zero
            assert dut.quotient.value == 0, f"[ERROR] quotient is not zero after reset: {dut.quotient.value}"
            assert dut.remainder.value == 0, f"[ERROR] remainder is not zero after reset: {dut.remainder.value}"
            assert dut.valid.value == 0, f"[ERROR] valid is not zero after reset: {dut.valid.value}"
            # Wait for 2 more cycles to allow the DUT to stabilize after reset
            for i in range(2):
                await RisingEdge(dut.clk)
            # Deactivate the reset signal
            dut.rst.value = 1
            print("[INFO] Reset applied to the DUT")

        # Generate random values for dividend and divisor within specified ranges
        wdata1 = random.randint(data_wd, (2**data_wd)-1)  # Dividend should be between WIDTH and 2^WIDTH - 1
        wdata2 = random.randint(1, data_wd)               # Divisor should be between 1 and WIDTH - 1
        
        # Write generated values to the DUT
        dut.dividend.value = wdata1
        dut.divisor.value = wdata2
        print(f"Performing write operation: dividend = {wdata1}, divisor = {wdata2}")
        
        # Start the division operation
        dut.start.value = 1
        await RisingEdge(dut.clk)
        # Ensure the start signal is only high for one clock cycle
        dut.start.value = 0

        # Wait for the division process to complete, indicated by the 'valid' signal
        #await RisingEdge(dut.valid)
       #Explicit Check for valid: Ensure valid asserts after WIDTH cycles
        for _ in range(data_wd):
            await RisingEdge(dut.clk)
            assert dut.valid.value == 0, "ERROR: Valid asserted prematurely"
        
        # Check for valid to assert indicating division complete
        await RisingEdge(dut.valid)
        assert dut.valid.value == 1, "ERROR: Valid did not assert as expected" 
        # Read the results from the DUT after the division is complete
        await RisingEdge(dut.clk)
        out_q = int(dut.quotient.value)
        out_r = int(dut.remainder.value)
        print(f"Read operation: quotient = {out_q}, remainder = {out_r}")
         
        # Checker: Validate quotient and remainder against expected values calculated by Python
        expected_q = wdata1 // wdata2
        expected_r = wdata1 % wdata2
           
        assert out_q == expected_q, f"ERROR: Quotient mismatch! Expected: {expected_q}, Got: {out_q}"
        assert out_r == expected_r, f"ERROR: Remainder mismatch! Expected: {expected_r}, Got: {out_r}"
 
	# Ensure valid remains high for only one cycle
        await RisingEdge(dut.clk)
        assert dut.valid.value == 0, "ERROR: Valid did not deassert as expected"

        print(f"Check Passed: quotient = {out_q}, remainder = {out_r}")