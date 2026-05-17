import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
import harness_library as hrs_lb
import random

# ----------------------------------------
# - Test Low Pass Filter
# ----------------------------------------

@cocotb.test()
async def test_low_pass_filter(dut):
    """Test the Low Pass Filter module with edge cases and random data."""

    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())

    # Debug mode
    debug = 0

    # Retrieve parameters from the DUT
    DATA_WIDTH = int(dut.DATA_WIDTH.value)
    COEFF_WIDTH = int(dut.COEFF_WIDTH.value)
    NUM_TAPS = int(dut.NUM_TAPS.value)

    # Initialize DUT
    await hrs_lb.dut_init(dut)

    # Apply reset and enable
    await hrs_lb.reset_dut(dut.reset)

    # Calculate min and max values for data and coefficients
    data_min = int(-2**DATA_WIDTH / 2)
    data_max = int((2**DATA_WIDTH / 2) - 1)
    coeff_min = int(-2**COEFF_WIDTH / 2)
    coeff_max = int((2**COEFF_WIDTH / 2) - 1)

    # Number of random test iterations
    num_random_iterations = 98  # Adjust to complement explicit cases for 100 total tests

    # Explicit test cases to ensure edge coverage
    test_cases = [
        ([0] * NUM_TAPS, [0] * NUM_TAPS),  # All zeros
        ([data_max] * NUM_TAPS, [coeff_max] * NUM_TAPS),  # All maximum values
        ([data_min] * NUM_TAPS, [coeff_min] * NUM_TAPS),  # All minimum values
    ]

    # Add random test cases
    for _ in range(num_random_iterations):
        data_in = [random.randint(data_min, data_max) for _ in range(NUM_TAPS)]
        coeffs = [random.randint(coeff_min, coeff_max) for _ in range(NUM_TAPS)]
        test_cases.append((data_in, coeffs))

    # Iterate through all test cases
    for test_num, (data_in, coeffs) in enumerate(test_cases):
        #cocotb.log.info(f"[INFO] Test Case {test_num + 1}")

        # Flatten input data and coefficients into a single concatenated value
        data_in_concat = int(''.join(format(x & ((1 << DATA_WIDTH) - 1), f'0{DATA_WIDTH}b') for x in data_in), 2)
        coeffs_concat = int(''.join(format(x & ((1 << COEFF_WIDTH) - 1), f'0{COEFF_WIDTH}b') for x in coeffs), 2)

        valid_in = 1 if test_num < 3 else random.randint(0, 1)  # Valid always high for edge cases

        # Apply inputs to the DUT
        dut.data_in.value = data_in_concat
        dut.coeffs.value = coeffs_concat
        dut.valid_in.value = valid_in

        for _ in range(2):  # Wait for computation to propagate
            await RisingEdge(dut.clk)

        if valid_in:
            # Calculate expected output
            expected_output = sum(d * c for d, c in zip(data_in, coeffs[::-1]))

            # Read the output from the DUT
            data_out = dut.data_out.value.signed_integer

            # Assertions
            assert data_out == expected_output, f"Test {test_num + 1}: Output mismatch: {data_out} != {expected_output}"
            assert dut.valid_out.value == valid_in, f"Test {test_num + 1}: Valid mismatch: {dut.valid_out.value} != {valid_in}"

            # Debug logging
            if debug:
                cocotb.log.info(f"[DEBUG] Test {test_num + 1}")
                cocotb.log.info(f"[DEBUG] Data_in = {data_in}")
                cocotb.log.info(f"[DEBUG] Coeffs = {coeffs}")
                cocotb.log.info(f"[DEBUG] Data_out = {data_out}, Expected = {expected_output}")
                cocotb.log.info(f"[DEBUG] Valid_out = {dut.valid_out.value}, Valid_in = {valid_in}")

        # Deactivate valid_in for the next iteration
        dut.valid_in.value = 0

    cocotb.log.info(f"All {len(test_cases)} tests passed successfully.")
