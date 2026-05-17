import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer


@cocotb.test()
async def test_signed_comparator(dut):  # dut will be the object for RTL top.
   

    #magnitude mode

    dut.i_A.value = 0
    dut.i_B.value = 0
    dut.i_enable.value = 0
    dut.i_mode.value = 0
    await Timer(100, unit='ps')
    assert dut.o_greater.value==0, f"output should not be {dut.o_greater.value}"
    assert dut.o_less.value==0, f"output should not be {dut.o_less.value}"
    assert dut.o_equal.value==0, f"output should not be {dut.o_equal.value}"

    dut.i_A.value = 5
    dut.i_B.value = 3
    dut.i_enable.value = 1
    await Timer(100, unit='ps')
    assert dut.o_greater.value==1, f"output should not be {dut.o_greater.value}"
    assert dut.o_less.value==0, f"output should not be {dut.o_less.value}"
    assert dut.o_equal.value==0, f"output should not be {dut.o_equal.value}"

    await Timer(100, unit='ps')
    dut.i_enable.value = 0
    await Timer(300, unit='ns')
    dut.i_A.value = 3
    dut.i_B.value = 5
    dut.i_enable.value = 1
    await Timer(100, unit='ps')
    assert dut.o_greater.value==0, f"output should not be {dut.o_greater.value}"
    assert dut.o_less.value==1, f"output should not be {dut.o_less.value}"
    assert dut.o_equal.value==0, f"output should not be {dut.o_equal.value}"

    await Timer(100, unit='ps')
    dut.i_enable.value = 0
    await Timer(300, unit='ns')
    dut.i_A.value = 5
    dut.i_B.value = 5
    dut.i_enable.value = 1
    await Timer(100, unit='ps')
    assert dut.o_greater.value==0, f"output should not be {dut.o_greater.value}"
    assert dut.o_less.value==0, f"output should not be {dut.o_less.value}"
    assert dut.o_equal.value==1, f"output should not be {dut.o_equal.value}"

    #signed mode_________________________
    await Timer(100, unit='ps')
    dut.i_enable.value = 0
    dut.i_mode.value = 1

    dut.i_A.value = -3
    dut.i_B.value = -5
    dut.i_enable.value = 1
    await Timer(100, unit='ps')
    assert dut.o_greater.value==1, f"output should not be {dut.o_greater.value}"
    assert dut.o_less.value==0, f"output should not be {dut.o_less.value}"
    assert dut.o_equal.value==0, f"output should not be {dut.o_equal.value}"

    await Timer(100, unit='ps')
    dut.i_enable.value = 0
    await Timer(300, unit='ns')
    dut.i_A.value = -5
    dut.i_B.value = -3
    dut.i_enable.value = 1
    await Timer(100, unit='ps')
    assert dut.o_greater.value==0, f"output should not be {dut.o_greater.value}"
    assert dut.o_less.value==1, f"output should not be {dut.o_less.value}"
    assert dut.o_equal.value==0, f"output should not be {dut.o_equal.value}"

    await Timer(100, unit='ps')
    dut.i_enable.value = 0
    await Timer(300, unit='ns')
    dut.i_A.value = -5
    dut.i_B.value = -5
    dut.i_enable.value = 1
    await Timer(100, unit='ps')
    assert dut.o_greater.value==0, f"output should not be {dut.o_greater.value}"
    assert dut.o_less.value==0, f"output should not be {dut.o_less.value}"
    assert dut.o_equal.value==1, f"output should not be {dut.o_equal.value}"


    #___________________
    await Timer(100, unit='ps')
    dut.i_enable.value = 0

    dut.i_A.value = 5
    dut.i_B.value = 3
    dut.i_enable.value = 1
    await Timer(100, unit='ps')
    assert dut.o_greater.value==1, f"output should not be {dut.o_greater.value}"
    assert dut.o_less.value==0, f"output should not be {dut.o_less.value}"
    assert dut.o_equal.value==0, f"output should not be {dut.o_equal.value}"

    await Timer(100, unit='ps')
    dut.i_enable.value = 0
    await Timer(300, unit='ns')
    dut.i_A.value = 3
    dut.i_B.value = 5
    dut.i_enable.value = 1
    await Timer(100, unit='ps')
    assert dut.o_greater.value==0, f"output should not be {dut.o_greater.value}"
    assert dut.o_less.value==1, f"output should not be {dut.o_less.value}"
    assert dut.o_equal.value==0, f"output should not be {dut.o_equal.value}"

    await Timer(100, unit='ps')
    dut.i_enable.value = 0
    await Timer(300, unit='ns')
    dut.i_A.value = 5
    dut.i_B.value = 5
    dut.i_enable.value = 1
    await Timer(100, unit='ps')
    assert dut.o_greater.value==0, f"output should not be {dut.o_greater.value}"
    assert dut.o_less.value==0, f"output should not be {dut.o_less.value}"
    assert dut.o_equal.value==1, f"output should not be {dut.o_equal.value}"



    
    