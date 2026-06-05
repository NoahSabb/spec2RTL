import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.regression import TestFactory
import random

# Function to calculate GCD in software for comparison
def gcd(a, b):
    while b != 0:
        a, b = b, a % b
    return a

# Coroutine to reset the DUT
async def reset_dut(dut):
    dut.rst.value = 1
    dut.go.value  = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert dut.OUT.value == 0, f"Reset Test failed OUT Expected 0, got {int(dut.OUT.value)}"
    assert dut.done.value == 0, f"Reset Test failed done Expected 0, got {int(dut.done.value)}"
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    assert dut.OUT.value == 0, f"Reset Test failed OUT Expected 0, got {int(dut.OUT.value)}"
    assert dut.done.value == 0, f"Reset Test failed done Expected 0, got {int(dut.done.value)}"

# Main GCD test coroutine
@cocotb.test()
async def gcd_test(dut):
    """ Test GCD calculation for different combinations of A and B """
    
    # Start the clock with 10ns period
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    width  = int(dut.WIDTH.value)
    max = (1 << width) - 1
    # Reset the DUT
    await reset_dut(dut)
    
    # Define test cases for non-zero, positive numbers
    test_cases = [
        (1, 1),    # GCD(1, 1) = 1
        (4, 2),    # GCD(4, 2) = 2
        (6, 3),    # GCD(6, 3) = 3
        (15, 5),   # GCD(15, 5) = 5
        (8, 4),    # GCD(8, 4) = 4
        (9, 6),    # GCD(9, 6) = 3
        (12, 8),   # GCD(12, 8) = 4
        (14, 7),   # GCD(14, 7) = 7
        (max, 1),   # (worst case for WIDTH )
        (max, max)  # (best case for WIDTH )
    ]
    
    # Test all pre-defined test cases
    for A, B in test_cases:
        # Apply inputs
        dut.A.value  = A
        dut.B.value  = B
        dut.go.value = 1
        latency      = 0
        
        # Wait for the `done` signal
        await RisingEdge(dut.clk)
        # Release go signal
        dut.go.value = 0
        await RisingEdge(dut.clk)
        latency      = latency + 1
        while (dut.done.value == 0):
            await RisingEdge(dut.clk)
            latency      = latency + 1
        
        # Compare the result with expected GCD
        expected_gcd = gcd(A, B)
        assert dut.OUT.value == expected_gcd, f"Test failed with A={A}, B={B}. Expected {expected_gcd}, got {int(dut.OUT.value)}"
        if((A==2**width-1) & (B==1)):
            assert latency == 2**width+1,f"The design latency to calculate the GCD is incorrect. A={A}, B={B}, Out={int(dut.OUT.value)}"
        elif((A==1) & (B==2**width-1)):
            assert latency == 2**width+1,f"The design latency to calculate the GCD is incorrect. A={A}, B={B}, Out={int(dut.OUT.value)}"
        elif((A==B)):
            assert latency == 2,f"The design latency to calculate the GCD is incorrect. A={A}, B={B}, Out={int(dut.OUT.value)}"
        await RisingEdge(dut.clk)
        assert dut.done.value == 0, f"Done should be high for only 1 clk cycle expected 0, got {int(dut.done.value)}"
        latency = 0
    # Reset the DUT
    await reset_dut(dut)
        
# Additional stress test with random values for A and B
@cocotb.test()
async def gcd_stress_test(dut):
    """ Stress test GCD calculation with random non-zero, positive values """
    
    # Start the clock with 10ns period
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    latency      = 0
    
    # Reset the DUT
    await reset_dut(dut)
    
    width  = int(dut.WIDTH.value)
    
    # Run random test cases
    for _ in range(100):
        A = random.randint(1, 2**width-1)  # A is positive number
        B = random.randint(1, 2**width-1)  # B is positive number
        latency = 0

        # Apply inputs
        dut.A.value  = A
        dut.B.value  = B
        dut.go.value = 1
        
        # Wait for the `done` signal
        await RisingEdge(dut.clk)
        # Release go signal
        dut.go.value = 0
        while (dut.done.value == 0):
            await RisingEdge(dut.clk)
            latency      = latency + 1
        
        # Compare the result with expected GCD
        expected_gcd = gcd(A, B)
        assert dut.OUT.value == expected_gcd, f"Test failed with A={A}, B={B}. Expected {expected_gcd}, got {int(dut.OUT.value)}"
        if((A==2**width-1) & (B==1)):
            assert latency == 2**width+1,f"The design latency to calculate the GCD is incorrect. A={A}, B={B}, Out={int(dut.OUT.value)}"
        elif((A==1) & (B==2**width-1)):
            assert latency == 2**width+1,f"The design latency to calculate the GCD is incorrect. A={A}, B={B}, Out={int(dut.OUT.value)}"
        elif((A==B)):
            assert latency == 2,f"The design latency to calculate the GCD is incorrect. A={A}, B={B}, Out={int(dut.OUT.value)}"
        
        await RisingEdge(dut.clk)
        assert dut.done.value == 0, f"Done should be high for only 1 clk cycle expected 0, got {int(dut.done.value)}"
        latency = 0
    
    # Reset the DUT
    await reset_dut(dut)