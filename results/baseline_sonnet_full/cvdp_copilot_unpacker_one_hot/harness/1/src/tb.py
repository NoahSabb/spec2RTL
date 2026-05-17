import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_unpack_one_hot(dut):
    """Cocotb testbench for unpack_one_hot with scoring for test cases"""

    # Initialize the score
    total_score = 0
    max_score = 6  # Total number of test cases provided

    # Test Case 1: One-Hot Selector = 1, sign = 0
    dut.sign.value = 0
    dut.size.value = 0
    dut.one_hot_selector.value = 1
    dut.source_reg.value = int(
        "3fa8c1d7e4926b73f1d4a9872ebc5609f4ac7b01e9d2f34c8a5b0f6789dc1234", 16
    )
    expected = int(
        "01000000010001000001000101000101000000000101010100010100000101010100000001000001010100010101000000000001000001000000010100010000", 16
    )
    await Timer(2, unit="ns")
    if dut.destination_reg.value == expected:
        total_score += 1

    # Test Case 2: One-Hot Selector = 1, sign = 1
    dut.sign.value = 1
    dut.size.value = 0
    dut.one_hot_selector.value = 1
    dut.source_reg.value = int(
        "3fa8c1d7e4926b73f1d4a9872ebc5609f4ac7b01e9d2f34c8a5b0f6789dc1234", 16
    )
    expected = int(
        "ff000000ff00ff0000ff00ffff00ffff00000000ffffffff00ffff0000ffffffff000000ff0000ffffff00ffffff0000000000ff0000ff000000ffff00ff0000", 16
    )
    await Timer(2, unit="ns")
    if dut.destination_reg.value == expected:
        total_score += 1

    # Test Case 3: One-Hot Selector = 2, sign = 0
    dut.sign.value = 0
    dut.size.value = 0
    dut.one_hot_selector.value = 2
    dut.source_reg.value = int(
        "3fa8c1d7e4926b73f1d4a9872ebc5609f4ac7b01e9d2f34c8a5b0f6789dc1234", 16
    )
    expected = int(
        "03030100020203000103020300000001030202010301000203030003010003000200020201010203000003030102010302000201030103000001000200030100", 16
    )
    await Timer(2, unit="ns")
    if dut.destination_reg.value == expected:
        total_score += 1

    # Test Case 4: One-Hot Selector = 2, sign = 1
    dut.sign.value = 1
    dut.size.value = 0
    dut.one_hot_selector.value = 2
    dut.source_reg.value = int(
        "3fa8c1d7e4926b73f1d4a9872ebc5609f4ac7b01e9d2f34c8a5b0f6789dc1234", 16
    )
    expected = int(
        "ffff0100fefeff0001fffeff00000001fffefe01ff0100feffff00ff0100ff00fe00fefe0101feff0000ffff01fe01fffe00fe01ff01ff00000100fe00ff0100", 16
    )
    await Timer(2, unit="ns")
    if dut.destination_reg.value == expected:
        total_score += 1

    # Test Case 5: One-Hot Selector = 4, sign = 0, size = 1
    dut.sign.value = 0
    dut.size.value = 1
    dut.one_hot_selector.value = 4
    dut.source_reg.value = int(
        "3fa8c1d7e4926b73f1d4a9872ebc5609f4ac7b01e9d2f34c8a5b0f6789dc1234", 16
    )
    expected = int(
        "003f00a800c100d700e40092006b007300f100d400a90087002e00bc0056000900f400ac007b000100e900d200f3004c008a005b000f0067008900dc00120034", 16
    )
    await Timer(2, unit="ns")
    if dut.destination_reg.value == expected:
        total_score += 1

    # Test Case 6: One-Hot Selector = 3 (pass-through mode)
    dut.sign.value = 0
    dut.size.value = 0
    dut.one_hot_selector.value = 3
    dut.source_reg.value = int(
        "3fa8c1d7e4926b73f1d4a9872ebc5609f4ac7b01e9d2f34c8a5b0f6789dc1234", 16
    )
    expected = int(
        "00000000000000000000000000000000000000000000000000000000000000003fa8c1d7e4926b73f1d4a9872ebc5609f4ac7b01e9d2f34c8a5b0f6789dc1234", 16
    )
    await Timer(2, unit="ns")
    if dut.destination_reg.value == expected:
        total_score += 1

    # Final Score Check
    if total_score == max_score:
        dut._log.info(f"All tests passed! Total Score: {total_score}/{max_score}")
    else:
        dut._log.error(f"Some tests failed. Total Score: {total_score}/{max_score}")

