import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

async def reset_dut(dut):
    """Reset the DUT"""
    dut.i_rstb.value =0
    dut.i_detection_signal.value =0

    await FallingEdge(dut.i_clk)
    dut.i_rstb.value = 1
    await RisingEdge(dut.i_clk)

# async def edge(dut, initial_value, final_value):
#     """EDGE CREATION"""
#     dut.i_detection_signal.value = initial_value
#     await RisingEdge(dut.i_clk)
#     dut.i_detection_signal.value = final_value


@cocotb.test()
async def test_sync_pos_neg_edge_detector(dut):  # dut will be the object for RTL top.
    # Generate clock
    cocotb.start_soon(Clock(dut.i_clk, 10, unit='ns').start())  # timeperiod= 10ns
    # Reset the DUT
    await reset_dut(dut)

    
    await RisingEdge(dut.i_clk)
    dut.i_detection_signal.value = 1
    await RisingEdge(dut.i_clk)
    await FallingEdge(dut.i_clk)
    assert dut.o_positive_edge_detected.value==1, f"output should be 1 not {dut.o_positive_edge_detected.value}"
    await RisingEdge(dut.i_clk)
    dut.i_detection_signal.value = 0
    await FallingEdge(dut.i_clk)
    assert dut.o_positive_edge_detected.value==0, f"output should be 1 not {dut.o_positive_edge_detected.value}"
    await FallingEdge(dut.i_clk)
    assert dut.o_negative_edge_detected.value==1, f"output should be 1 not {dut.o_negative_edge_detected.value}"
    await FallingEdge(dut.i_clk)
    assert dut.o_negative_edge_detected.value==0, f"output should be 0 not {dut.o_negative_edge_detected.value}"


   