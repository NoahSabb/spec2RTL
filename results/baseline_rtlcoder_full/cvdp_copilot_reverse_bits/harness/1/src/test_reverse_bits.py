import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def test_reverse_bits(dut):  # dut refers to the Device Under Test (reverse_bits)
    """
    Test the reverse_bits module with various test cases.
    """

    async def run_test_case(input_val, expected_output):
        """Helper function to apply input, wait, and verify output."""
        dut.num_in.value = input_val
        await Timer(100, unit='ps')  # Wait for outputs to stabilize
        assert dut.num_out.value == expected_output, (
            f"Test failed for input {input_val:#010x}. "
            f"Expected output: {expected_output:#010x}, "
            f"Got: {dut.num_out.value:#010x}"
        )

    # Test Case 1: All zeros
    await run_test_case(0x00000000, 0x00000000)

    # Test Case 2: All ones
    await run_test_case(0xFFFFFFFF, 0xFFFFFFFF)

    # Test Case 3: Single bit set at LSB
    await run_test_case(0x00000001, 0x80000000)

    # Test Case 4: Single bit set at MSB
    await run_test_case(0x80000000, 0x00000001)

    # Test Case 5: Alternating pattern (0xAAAAAAAA)
    await run_test_case(0xAAAAAAAA, 0x55555555)

    # Test Case 6: Alternating pattern (0x55555555)
    await run_test_case(0x55555555, 0xAAAAAAAA)

    # Test Case 7: Incrementing bits (0x12345678)
    await run_test_case(0x12345678, int('{:032b}'.format(0x12345678)[::-1], 2))

    # Test Case 8: Decrementing bits (0x87654321)
    await run_test_case(0x87654321, int('{:032b}'.format(0x87654321)[::-1], 2))

    # Test Case 9: Edge case with one zero surrounded by ones
    await run_test_case(0xFFFFFFFE, 0x7FFFFFFF)

    # Test Case 10: Edge case with one one surrounded by zeros
    await run_test_case(0x00000010, 0x08000000)

    # Test Case 11: Random value (0xCAFEBABE)
    await run_test_case(0xCAFEBABE, int('{:032b}'.format(0xCAFEBABE)[::-1], 2))

    # Test Case 12: Random value (0xDEADBEEF)
    await run_test_case(0xDEADBEEF, int('{:032b}'.format(0xDEADBEEF)[::-1], 2))

    # Test Case 13: Symmetrical value (0x0F0F0F0F)
    await run_test_case(0x0F0F0F0F, 0xF0F0F0F0)

    # Test Case 14: Symmetrical value (0xF0F0F0F0)
    await run_test_case(0xF0F0F0F0, 0x0F0F0F0F)

    # Test Case 15: Middle bit set
    await run_test_case(0x08000000, 0x00000010)

    cocotb.log.info("All test cases passed successfully!")
