import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

async def reset_dut(dut):
    """Reset the DUT"""
    dut.i_rstb.value =0
    dut.i_binary_in.value =0

    await FallingEdge(dut.i_clk)
    dut.i_rstb.value = 1
    await RisingEdge(dut.i_clk)

@cocotb.test()
async def test_binary_to_one_hot_decoder_sequential(dut):  # dut will be the object for RTL top.
   # Generate clock
    cocotb.start_soon(Clock(dut.i_clk, 10, unit='ns').start())  # timeperiod= 10ns
    # Reset the DUT
    await reset_dut(dut)

    
    await FallingEdge(dut.i_clk)
    dut.i_binary_in.value = 0
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==1, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 1
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==2, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 2
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==4, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 3
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==8, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 4
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==16, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 5
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==32, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 6
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==64, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 7
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==128, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 8
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==256, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 9
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==512, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 10
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==1024, f"output should not be {dut.o_one_hot_out.value}"
    
    dut.i_binary_in.value = 11
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==2048, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 12
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==4096, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 13
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==8192, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 14
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==16384, f"output should not be {dut.o_one_hot_out.value}"

    dut.i_binary_in.value = 15
    await FallingEdge(dut.i_clk)
    assert dut.o_one_hot_out.value==32768, f"output should not be {dut.o_one_hot_out.value}"





    
    