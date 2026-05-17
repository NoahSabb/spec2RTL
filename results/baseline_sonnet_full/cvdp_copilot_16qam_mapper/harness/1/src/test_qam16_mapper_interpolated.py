import cocotb
from cocotb.triggers import Timer
import random
import harness_library as hrs_lb


@cocotb.test()
async def test_qam16_mapper_interpolated(dut):
    """Test the 16-QAM mapper with interpolation."""

    # Parameters from the DUT
    N = int(dut.N.value)
    IN_WIDTH = int(dut.IN_WIDTH.value)
    OUT_WIDTH = int(dut.OUT_WIDTH.value)

    # Debug mode
    debug = 0

    # Number of random test iterations
    num_random_iterations = 98  # Adjust to complement the explicit cases for 100 total tests

    # Explicit test cases to ensure edge coverage
    test_cases = [
        [0] * N,             # All zeros
        [(1 << IN_WIDTH) - 1] * N  # All maximum values (e.g., 15 for IN_WIDTH=4)
    ]

    # Add random test cases
    for _ in range(num_random_iterations):
        test_cases.append([random.randint(0, (1 << IN_WIDTH) - 1) for _ in range(N)])

    # Iterate through all test cases
    for test_num, bits in enumerate(test_cases):
        # Flatten the bits into a single input vector
        bits_concat = sum((b << (i * IN_WIDTH)) for i, b in enumerate(reversed(bits)))

        # Apply the input to the DUT
        dut.bits.value = bits_concat

        # Wait for 10 ns (1 clock cycle duration)
        await Timer(10, unit='ns')

        # Extract the mapped I/Q values for validation
        mapped_I = []
        mapped_Q = []
        for b in bits:
            mapped_I.append({0b00: -3, 0b01: -1, 0b10: 1, 0b11: 3}[b >> 2])
            mapped_Q.append({0b00: -3, 0b01: -1, 0b10: 1, 0b11: 3}[b & 0b11])

        # Calculate interpolated I/Q values and build the expected output vectors
        expected_I = []
        expected_Q = []
        for i in range(N // 2):
            expected_I.extend([
                mapped_I[2 * i],
                (mapped_I[2 * i] + mapped_I[2 * i + 1]) // 2,
                mapped_I[2 * i + 1]
            ])
            expected_Q.extend([
                mapped_Q[2 * i],
                (mapped_Q[2 * i] + mapped_Q[2 * i + 1]) // 2,
                mapped_Q[2 * i + 1]
            ])

        # Use the helper function to extract DUT outputs
        dut_I = await hrs_lb.extract_signed(dut.I, OUT_WIDTH, N + N // 2)
        dut_Q = await hrs_lb.extract_signed(dut.Q, OUT_WIDTH, N + N // 2)

        # Assertions
        assert dut_I == expected_I, f"Test {test_num}: I mismatch: DUT={dut_I}, Expected={expected_I}"
        assert dut_Q == expected_Q, f"Test {test_num}: Q mismatch: DUT={dut_Q}, Expected={expected_Q}"

        if debug:
            cocotb.log.info(f"[DEBUG] Test {test_num}")
            cocotb.log.info(f"[DEBUG] Input bits: {bits}")
            cocotb.log.info(f"[DEBUG] Mapped I: {mapped_I}")
            cocotb.log.info(f"[DEBUG] Mapped Q: {mapped_Q}")
            cocotb.log.info(f"[DEBUG] DUT I: {dut_I}")
            cocotb.log.info(f"[DEBUG] DUT Q: {dut_Q}")
            cocotb.log.info(f"[DEBUG] Expected I: {expected_I}")
            cocotb.log.info(f"[DEBUG] Expected Q: {expected_Q}")

    cocotb.log.info(f"All {len(test_cases)} tests passed successfully.")
