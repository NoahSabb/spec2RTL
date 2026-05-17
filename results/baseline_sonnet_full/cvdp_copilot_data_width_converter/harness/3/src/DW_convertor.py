import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

# Helper function to generate reset signal
async def reset_dut(dut, duration_ns):
    dut.reset.value = 1
    await Timer(duration_ns, unit="ns")
    dut.reset.value = 0
    await RisingEdge(dut.clk)

# Helper function to send data to DUT
async def send_data(dut, data, valid):
    dut.data_in.value = data
    dut.data_valid.value = valid
    await RisingEdge(dut.clk)

# Helper function to calculate the expected concatenated output
def concatenate_data(test_data):
    expected_output = 0
    for i in range(len(test_data)):
        expected_output = (expected_output << 32) | test_data[i]
    return expected_output

# Test case 1: Send the first set of data and check the output
async def test_case_1(dut):
    """ Test case 1: Send 4 consecutive valid 32-bit data words """

    # Test data to be fed into the DUT (32-bit data)
    test_data = [0x12345678, 0x9ABCDEF0, 0x0FEDCBA9, 0x87654321]

    # Expected output (concatenation of the input data in order)
    expected_output = concatenate_data(test_data)

    # Apply the input data and check output
    for i in range(4):
        dut._log.info(f"Sending data {hex(test_data[i])}")
        await send_data(dut, test_data[i], 1)  # Send valid data
        await Timer(10, unit="ns")

    

    # Check if the output matches the expected concatenation
    dut._log.info(f"Expected output: {hex(expected_output)}")
   

    assert dut.o_data_out.value == expected_output, f"Output mismatch: Expected {hex(expected_output)}, got {hex(dut.o_data_out.value)}"

    dut._log.info("Test case 1 completed successfully")


# Test case 2: Send another set of data and check the output
async def test_case_2(dut):
    """ Test case 2: Send another set of 4 consecutive valid 32-bit data words """

    # New test data to be fed into the DUT (32-bit data)
    test_data = [0xDEADBEEF, 0xCAFEBABE, 0xBAADF00D, 0xFACEFEED]

    # Expected output (concatenation of the input data in order)
    expected_output = concatenate_data(test_data)

    # Apply the input data and check output
    for i in range(4):
        dut._log.info(f"Sending data {hex(test_data[i])}")
        await send_data(dut, test_data[i], 1)  # Send valid data
        await Timer(10, unit="ns")

 

    # Check if the output matches the expected concatenation
    dut._log.info(f"Expected output: {hex(expected_output)}")
   

    assert dut.o_data_out.value == expected_output, f"Output mismatch: Expected {hex(expected_output)}, got {hex(dut.o_data_out.value)}"

    dut._log.info("Test case 2 completed successfully")

async def test_case_3(dut):
    """ Test case 2: Send another set of 4 consecutive valid 32-bit data words """

    # New test data to be fed into the DUT (32-bit data)
    test_data = [0x11111111, 0x22222222, 0x33333333, 0x44444444]

    # Expected output (concatenation of the input data in order)
    expected_output = concatenate_data(test_data)

    # Apply the input data and check output
    for i in range(4):
        dut._log.info(f"Sending data {hex(test_data[i])}")
        await send_data(dut, test_data[i], 1)  # Send valid data
        await Timer(10, unit="ns")

 

    # Check if the output matches the expected concatenation
    dut._log.info(f"Expected output: {hex(expected_output)}")
   

    assert dut.o_data_out.value == expected_output, f"Output mismatch: Expected {hex(expected_output)}, got {hex(dut.o_data_out.value)}"

    dut._log.info("Test case 2 completed successfully")
# Main test function with both test cases
@cocotb.test()
async def test_data_width_converter(dut):
    """ Test data_width_converter with multiple test cases """

    # Start clock with a period of 10 ns (100 MHz)
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Apply reset
    await reset_dut(dut, 20)

    # Run test case 1
    await test_case_1(dut)

    # Apply reset before running the second test case
    #await reset_dut(dut, 20)
@cocotb.test()
async def test_data_width_converter(dut):
    """ Test data_width_converter with multiple test cases """

    # Start clock with a period of 10 ns (100 MHz)
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())



   
    # Run test case 2
    await test_case_2(dut)
@cocotb.test()
async def test_data_width_converter(dut):
    """ Test data_width_converter with multiple test cases """

    # Start clock with a period of 10 ns (100 MHz)
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())



    # Run test case 1
    await reset_dut(dut, 20)
    await test_case_3(dut)