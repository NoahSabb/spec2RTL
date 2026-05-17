import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.clock import Clock

# Helper function to generate expected PRBS sequence
def generate_prbs(seed, poly_length, poly_tap, width, num_cycles):
    prbs_reg = [int(x) for x in f'{seed:0{poly_length}b}']
    prbs_out = []

    for _ in range(num_cycles):
        prbs_xor_a = []
        prbs = [prbs_reg]  # Initialize prbs[0] with the current PRBS register

        # Loop through each bit of the output width
        for i in range(width):
            # Perform XOR operation between specified tap and last stage of PRBS
            xor_a = prbs[i][poly_tap - 1] ^ prbs[i][poly_length - 1]
            prbs_xor_a.append(xor_a)

            # Shift the LFSR and insert the new XOR result to generate next state
            prbs_next = [xor_a] + prbs[i][0:poly_length - 1]
            prbs.append(prbs_next)

        # Collect the XOR result as the output for this cycle
        prbs_out.append(int(''.join(map(str, prbs_xor_a[::-1])), 2))

        # Update the PRBS register with the last stage (prbs[width])
        prbs_reg = prbs[width]

    return prbs_out

# Testbench for PRBS Generator and Checker
@cocotb.test()
async def test_prbs_gen(dut):
    # Initialize and start the clock signal with a 10 ns period
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Test Parameters
    #width       = int(dut.WIDTH.value)
    check_mode  = int(dut.CHECK_MODE.value)  # Select mode: generator or checker
    poly_length = int(dut.POLY_LENGTH.value)  # Length of the polynomial
    poly_tap    = int(dut.POLY_TAP.value)     # Tap position in the polynomial
    width       = int(dut.WIDTH.value)        # Width of the PRBS output
    num_cycles  = 100  # Number of cycles to run the test
    #print ("Parameters: CHECK_MODE: " ,check_mode, ", POLY_LENGTH: " ,poly_length, ", POLY_TAP: " ,poly_tap, ", WIDTH: ",width)

    # Seed value for PRBS generation (all bits set to 1 initially)
    seed = int('1' * poly_length, 2)

    if check_mode == 0:  # Generator mode
        # Reset the DUT (Device Under Test)
        dut.rst.value = 1
        dut.data_in.value = 0  # Initialize data_in to 0
        await ClockCycles(dut.clk, 5)  # Wait for 5 clock cycles

        # When rst is high, set expected PRBS output to all 1's
        expected_prbs = [int('1' * width, 2)]

        # Check the PRBS output during reset
        await RisingEdge(dut.clk)  # Wait for a rising edge of the clock
        prbs_out = int(dut.data_out.value)  # Capture the output from the DUT
        assert prbs_out == expected_prbs[0], f"During reset: Expected {expected_prbs[0]:0{width}b}, Got {prbs_out:0{width}b}"

        # Release the reset and enable PRBS generation
        dut.rst.value = 0  # Release reset

        # Generate expected PRBS sequence after reset is released
        expected_prbs = generate_prbs(seed, poly_length, poly_tap, width, num_cycles)

        await RisingEdge(dut.clk)  # Wait for a rising edge of the clock so that the reset is driven low

        # Check the PRBS output after reset is released
        for cycle in range(num_cycles):
            await RisingEdge(dut.clk)  # Wait for each clock cycle

            # Extract the generated PRBS output from the DUT
            prbs_out = int(dut.data_out.value)

            # Compare the DUT output with the expected PRBS sequence
            assert prbs_out == expected_prbs[cycle], f"Mismatch at cycle {cycle}: Expected {expected_prbs[cycle]:0{width}b}, Got {prbs_out:0{width}b}"

    elif check_mode == 1:  # Checker mode
        # Reset the DUT (Device Under Test)
        dut.rst.value = 1
        dut.data_in.value = 0  # Initialize data_in to 0
        await ClockCycles(dut.clk, 5)  # Wait for 5 clock cycles

        # Release the reset and enable PRBS checking
        dut.rst.value = 0  # Release reset

        # Generate expected PRBS sequence to feed into data_in
        prbs_sequence = generate_prbs(seed, poly_length, poly_tap, width, num_cycles)

        # Initialize error flag
        error_flag = 0

        # Wait for a rising edge of the clock to ensure reset is low
        #await RisingEdge(dut.clk)

        # Send the PRBS sequence to the DUT via data_in
        for cycle in range(num_cycles):
            # Apply PRBS data_in
            dut.data_in.value = prbs_sequence[cycle]

            # Wait for a clock cycle
            await RisingEdge(dut.clk)

            # Read the error flag from data_out (assuming data_out is the error indicator)
            error_flag = int(dut.data_out.value)

            if(cycle>0):
            # Check that error_flag is 0 (no error)
                assert error_flag == 0, f"No error expected, but error detected at cycle {cycle}"

        # Introduce an error in the data_in
        error_cycle = num_cycles // 2  # Introduce error at the middle of the sequence
        dut.data_in.value = prbs_sequence[error_cycle] ^ 0x1  # Flip one bit to introduce error

        # Wait for a clock cycle
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)

        # Read the error flag after introducing the error
        error_flag = int(dut.data_out.value)

        # Check that error_flag is 1 (error detected)
        assert error_flag >0, f"Error expected, but no error detected at cycle {error_cycle}"
