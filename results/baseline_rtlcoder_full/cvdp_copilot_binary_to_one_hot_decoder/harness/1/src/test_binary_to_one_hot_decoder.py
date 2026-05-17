import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer


@cocotb.test()
async def test_binary_to_one_hot_decoder(dut):  # dut will be the object for RTL top.
   

    dut.binary_in.value = 0
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==1, f"output should not be {dut.one_hot_out.value}"
    
    dut.binary_in.value = 1
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==2, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 2
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==4, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 3
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==8, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 4
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==16, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 5
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==32, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 6
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==64, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 7
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==128, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 8
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==256, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 9
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==512, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 10
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==1024, f"output should not be {dut.one_hot_out.value}"
    
    dut.binary_in.value = 11
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==2048, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 12
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==4096, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 13
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==8192, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 14
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==16384, f"output should not be {dut.one_hot_out.value}"

    dut.binary_in.value = 15
    await Timer(100, unit='ps')
    assert dut.one_hot_out.value==32768, f"output should not be {dut.one_hot_out.value}"





    
    