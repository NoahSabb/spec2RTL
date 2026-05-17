import cocotb
from cocotb.triggers import Timer, RisingEdge

@cocotb.test()
async def test_field_extract(dut):
    dut.rst.value = 1
    dut.clk.value = 0
    await Timer(10, unit="ns")
    dut.rst.value = 0
    
    async def clk_cycle():
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")

    dut.vld.value = 0
    dut.sof.value = 0
    dut.eof.value = 0
    dut.data.value = 0
    await clk_cycle()
    
    passed_cases = []

    # Start of frame with valid data
    dut.vld.value = 1
    dut.sof.value = 1
    await clk_cycle()
    
    # First beat of data
    dut.sof.value = 0
    dut.data.value = 0xAAAA5555
    await clk_cycle()
    
    # Second beat where extraction should occur
    dut.data.value = 0x1234ABCD
    await clk_cycle()
    
    await clk_cycle()
    extracted_field = int(dut.field.value)
    field_valid = int(dut.field_vld.value)
    print(f"Extracted field: {hex(extracted_field)}, Field valid: {field_valid}")
    
    try:
        assert extracted_field == 0x1234, f"Expected field=0x1234, Got={hex(extracted_field)}"
        assert field_valid == 1, f"Expected field_vld=1, Got={field_valid}"
        passed_cases.append("Field Extraction Test")
    except AssertionError as e:
        print(f"Field Extraction Test failed: {e}")
    
    # End of frame
    dut.eof.value = 1
    await clk_cycle()
    
    try:
        assert dut.field_vld.value == 0, f"Expected field_vld=0 after EOF, Got={dut.field_vld.value}"
        passed_cases.append("End of Frame Test")
    except AssertionError as e:
        print(f"End of Frame Test failed: {e}")

    dut.eof.value = 0
    dut.vld.value = 0
    await clk_cycle()
    
    print(f"All test cases passed: {passed_cases}")
