import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import harness_library as hrs_lb
import random


@cocotb.test()
async def lifo_test(dut):
    """
    Test the basic functionality of the LIFO with continuous write and read enable.
    The first read has a two-clock cycle delay, and subsequent reads occur on each clock cycle.
    Also, tests overflow and underflow scenarios.
    """

    # Extract the data width (assumed to be the LIFO depth) from the DUT
    DATA_WIDTH = int(dut.DATA_WIDTH.value)

    dut._log.info(f"ADDR_WIDTH = {int(dut.ADDR_WIDTH.value)}, DATA_WIDTH = {DATA_WIDTH}")

    # Start the clock with a period of 10ns
    cocotb.start_soon(Clock(dut.clock, 10, unit='ns').start())

    # Initialize the DUT signals (e.g., reset all values to default 0)
    await hrs_lb.dut_init(dut)

    # Apply reset to the DUT for 25ns, reset is active low
    await hrs_lb.reset_dut(dut.reset, duration_ns=25, active=False)

    # Create a reference Python stack to model LIFO behavior
    reference_stack = []

    # Writing data into the LIFO more than its capacity to test overflow behavior
    await Timer(10, unit='ns')  # Wait for the reset to settle
    dut.write_en.value = 1  # Enable continuous write

    # Loop to write data beyond LIFO depth to check overflow condition
    for i in range(DATA_WIDTH + 2):  
        # Generate random data to write into the LIFO
        data = random.randint(0, 2**DATA_WIDTH-1)
        await write_lifo(dut, data)  # Perform the write operation

        # Push data into the reference stack if the LIFO is not full
        if dut.full.value == 0:
            reference_stack.append(data)
        else:
            # If LIFO is full, check if overflow is handled correctly
            await Timer(10, unit='ns')  # Short delay to allow full flag to settle
            assert dut.full.value == 1, f"Failed: LIFO should be full on iteration {i}"

        # Check if the LIFO becomes full after all writes are complete
        if i >= DATA_WIDTH:
            await Timer(10, unit='ns')  # Extra delay to check overflow properly
            assert dut.full.value == 1, f"Failed: Overflow not set when LIFO is full on iteration {i}"
            dut._log.info(f"Overflow occurred on iteration {i} when attempting to write to a full LIFO.")

    # Disable the write enable after completing the write sequence
    dut.write_en.value = 0

    # Read operations from the LIFO to test underflow behavior
    await Timer(10, unit='ns')  # Wait for a short period before starting reads
    dut.read_en.value = 1  # Enable continuous read

    # Loop to read data from LIFO, including underflow test
    for i in range(DATA_WIDTH + 2):
        data_out = await read_lifo(dut, first_read=(i == 0))  # Perform the read operation

        # Pop data from the reference stack if the LIFO is not empty
        if i <= DATA_WIDTH and dut.empty.value == 0:
            await Timer(10, unit='ns')  # Short delay to allow empty flag to settle
            expected_data = reference_stack.pop()
            assert int(data_out) == expected_data, f"Expected {expected_data}, got {int(data_out)}"
        else:  # Check if underflow occurs when attempting to read from an empty LIFO
            assert dut.empty.value == 1, f"LIFO should be empty after all reads on iteration {i}"

        # Delay empty check to allow LIFO to update its internal state after reading
        if i >= DATA_WIDTH:
            await Timer(20, unit='ns')  # Allow extra time for empty flag to assert
            assert dut.empty.value == 1, f"Underflow not set when LIFO empty on iteration {i}"
            dut._log.info(f"Underflow occurred on iteration {i} when attempting to read from an empty LIFO.")

    # Disable the read enable after completing the read sequence
    dut.read_en.value = 0


async def write_lifo(dut, data):
    """Perform a write operation into the LIFO."""
    # Assign the input data to the LIFO's data_in port
    dut.data_in.value = data
    # Wait for one clock cycle to simulate the write operation
    await RisingEdge(dut.clock)
    # Log the data that was written to the LIFO
    dut._log.info(f"Wrote {data} to LIFO")


async def read_lifo(dut, first_read=False):
    """Perform a read operation from the LIFO, with a two-clock cycle delay for the first read."""
    if first_read:
        # Introduce an additional delay before the first read
        await Timer(10, unit='ns')
        dut._log.info("Two-clock cycle delay before first read")
    
    # Capture the output data from the LIFO at the clock edge
    data_out = dut.data_out.value
    
    # Log the data that was read from the LIFO
    dut._log.info(f"Read {int(data_out)} from LIFO")
    return data_out
