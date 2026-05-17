import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import harness_library as hrs_lb
import random

@cocotb.test()
async def bcd_to_excess_3(dut):
    """ Test BCD to Excess-3 conversion including error flag assertions. """
   
    # Initialize the DUT signals (e.g., reset all values to default 0)
    await hrs_lb.dut_init(dut)
   
    # Define expected outputs for valid BCD inputs
    expected_excess3 = {
        0: 3,  1: 4,  2: 5,  3: 6,
        4: 7,  5: 8,  6: 9,  7: 10,
        8: 11, 9: 12
    }
   
    # Test the BCD to Excess-3 conversion for valid inputs
    for bcd_value in range(10):  # Loop from 0 to 9
        dut.bcd.value = bcd_value  # Apply BCD value
        await Timer(10, unit='ns')  # Wait for 10 ns
        expected_value = expected_excess3[bcd_value]
        assert dut.excess3.value == expected_value, f"Error: BCD {bcd_value} should convert to {expected_value}, got {dut.excess3.value}"
        assert dut.error.value == 0, f"Error flag should be 0 for valid input {bcd_value}"
        print(f"Performing bcd to excess_3 operation: bcd = {bcd_value}, excess3 = {dut.excess3.value}")

    # Test invalid BCD inputs
    for bcd_value in range(10, 12):  # Loop from 10 to 11
        dut.bcd.value = bcd_value  # Apply BCD value
        await Timer(10, unit='ns')  # Wait for 10 ns
        assert dut.error.value == 1, f"Error flag should be 1 for invalid input {bcd_value}"
        print(f"Testing invalid input: bcd = {bcd_value}, error = {dut.error.value}")

    # Wait for a final 10 ns period before ending the test
    await Timer(10, unit='ns')
