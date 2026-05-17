import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock

# Utility function to calculate the next Fibonacci number in Python
def next_fibonacci(a, b):
    return a + b

# Function to continuously calculate the Fibonacci series up to overflow
async def calculate_fibonacci(dut):
    a, b = 0, 1
    while True:
        # Capture the DUT output
        dut_output = int(dut.fib_out.value)
        
        # Check if overflow flag is set in DUT
        if dut.overflow_flag.value == 1:
            dut._log.info("Overflow detected. Fibonacci sequence will reset.")
            break
        
        # Assert to ensure DUT output matches the expected value
        assert dut_output == a, f"Expected {a}, but got {dut_output} from DUT."
        dut._log.info(f"DUT Fibonacci Output = {dut_output}, Expected = {a}")
        
        # Advance the expected Fibonacci numbers
        a, b = b, next_fibonacci(a, b)
        
        # Wait for the next clock cycle
        await RisingEdge(dut.clk)

# Function to apply reset to DUT
async def apply_reset(dut, duration=2):
    dut.rst.value = 1  # Assert reset
    await Timer(duration, unit="ns")  # Hold reset for the specified duration
    dut.rst.value = 0  # Deassert reset
    await RisingEdge(dut.clk)  # Synchronize with clock edge after reset
    dut._log.info("Reset applied to DUT.")

# Test to verify Fibonacci sequence restarts after reset
@cocotb.test()
async def test_reset_scenario(dut):
    """ Test case to cover the scenario where the sequence is interrupted by reset. """
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())  # Start clock with 10ns period

    # Apply initial reset to start the module
    await apply_reset(dut)

    # Run the Fibonacci sequence for a few cycles, then apply reset
    await calculate_fibonacci(dut)  # Run sequence until reset or overflow
    dut._log.info("Sequence running; applying reset to interrupt it.")
    
    # Apply reset during the sequence generation
    await apply_reset(dut)

    # After reset, check that the sequence starts from F(0) = 0
    await calculate_fibonacci(dut)

# Test to verify overflow scenario and reset handling after overflow
@cocotb.test()
async def test_overflow_and_reset(dut):
    """ Test case to cover overflow scenario and reset after overflow. """
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())  # Start clock with 10ns period

    # Apply initial reset to start the module
    await apply_reset(dut)

    # Run the Fibonacci sequence until overflow is detected
    await calculate_fibonacci(dut)

    # Apply reset after overflow has occurred
    dut._log.info("Applying reset after overflow.")
    await apply_reset(dut)

    # Verify that the sequence restarts from F(0) = 0 after reset
    await calculate_fibonacci(dut)