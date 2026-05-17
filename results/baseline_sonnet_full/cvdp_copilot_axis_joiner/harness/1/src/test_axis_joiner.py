import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ClockCycles, Timer
import random
import time
import harness_library as hrs_lb

@cocotb.test()
async def test_axis_joiner(dut):
    # Seed the random number generator with the current time or another unique value
    random.seed(time.time())
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 5, unit='ns', period_high=3).start())
    
    await hrs_lb.dut_init(dut)
    


    await FallingEdge(dut.clk)
    dut.rst.value = 0
    await FallingEdge(dut.clk)
    dut.rst.value = 1
    await FallingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    assert dut.m_axis_tdata.value == 0, f"[ERROR] m_axis_tdata value is : {dut.m_axis_tdata.value}"
    print(f'reset successful ')

    dut.m_axis_tready.value = 1
 
    
    await FallingEdge(dut.clk)
    dut.s_axis_tdata_1.value = 0xff
    dut.s_axis_tvalid_1.value = 1
    dut.s_axis_tlast_1.value = 0
    await FallingEdge(dut.clk)
    dut.s_axis_tdata_1.value = 0xf0
    dut.s_axis_tvalid_1.value = 1
    dut.s_axis_tlast_1.value = 0
    assert dut.m_axis_tdata.value == 0xff, f"[ERROR] m_axis_tdata value is : {dut.m_axis_tdata.value}"
    assert dut.m_axis_tvalid.value == 1, f"[ERROR] m_axis_tvalid value is : {dut.m_axis_tvalid.value}"
    assert dut.m_axis_tlast.value == 0, f"[ERROR] m_axis_tlast value is : {dut.m_axis_tlast.value}"
    assert dut.m_axis_tuser.value == 0x1, f"[ERROR] m_axis_tuser value is : {dut.m_axis_tuser.value}"
    

    await FallingEdge(dut.clk)
    dut.s_axis_tdata_1.value = 0xfa
    dut.s_axis_tvalid_1.value = 1
    dut.s_axis_tlast_1.value = 1
    assert dut.m_axis_tdata.value == 0xf0, f"[ERROR] m_axis_tdata value is : {dut.m_axis_tdata.value}"
    assert dut.m_axis_tvalid.value == 1, f"[ERROR] m_axis_tvalid value is : {dut.m_axis_tvalid.value}"
    assert dut.m_axis_tlast.value == 0, f"[ERROR] m_axis_tlast value is : {dut.m_axis_tlast.value}"
    assert dut.m_axis_tuser.value == 0x1, f"[ERROR] m_axis_tuser value is : {dut.m_axis_tuser.value}"
    await RisingEdge(dut.clk)
    assert dut.m_axis_tdata.value == 0xfa, f"[ERROR] m_axis_tdata value is : {dut.m_axis_tdata.value}"
    assert dut.m_axis_tvalid.value == 1, f"[ERROR] m_axis_tvalid value is : {dut.m_axis_tvalid.value}"
    assert dut.m_axis_tlast.value == 1, f"[ERROR] m_axis_tlast value is : {dut.m_axis_tlast.value}"
    assert dut.m_axis_tuser.value == 0x1, f"[ERROR] m_axis_tuser value is : {dut.m_axis_tuser.value}"

    print(f'successfully received data from stream 1 with correct tag id in m_axis_tuser channel  ')

    await FallingEdge(dut.clk)
    dut.s_axis_tvalid_1.value = 0
    await FallingEdge(dut.clk)
    await FallingEdge(dut.clk)
    
    await FallingEdge(dut.clk)
    dut.s_axis_tdata_2.value = 0xff
    dut.s_axis_tvalid_2.value = 1
    dut.s_axis_tlast_2.value = 0
    await FallingEdge(dut.clk)
    dut.s_axis_tdata_2.value = 0xf0
    dut.s_axis_tvalid_2.value = 1
    dut.s_axis_tlast_2.value = 0
    assert dut.m_axis_tdata.value == 0xff, f"[ERROR] m_axis_tdata value is : {dut.m_axis_tdata.value}"
    assert dut.m_axis_tvalid.value == 1, f"[ERROR] m_axis_tvalid value is : {dut.m_axis_tvalid.value}"
    assert dut.m_axis_tlast.value == 0, f"[ERROR] m_axis_tlast value is : {dut.m_axis_tlast.value}"
    assert dut.m_axis_tuser.value == 0x2, f"[ERROR] m_axis_tuser value is : {dut.m_axis_tuser.value}"

    await FallingEdge(dut.clk)
    dut.s_axis_tdata_2.value = 0xfa
    dut.s_axis_tvalid_2.value = 1
    dut.s_axis_tlast_2.value = 1
    assert dut.m_axis_tdata.value == 0xf0, f"[ERROR] m_axis_tdata value is : {dut.m_axis_tdata.value}"
    assert dut.m_axis_tvalid.value == 1, f"[ERROR] m_axis_tvalid value is : {dut.m_axis_tvalid.value}"
    assert dut.m_axis_tlast.value == 0, f"[ERROR] m_axis_tlast value is : {dut.m_axis_tlast.value}"
    assert dut.m_axis_tuser.value == 0x2, f"[ERROR] m_axis_tuser value is : {dut.m_axis_tuser.value}"
    await RisingEdge(dut.clk)
    assert dut.m_axis_tdata.value == 0xfa, f"[ERROR] m_axis_tdata value is : {dut.m_axis_tdata.value}"
    assert dut.m_axis_tvalid.value == 1, f"[ERROR] m_axis_tvalid value is : {dut.m_axis_tvalid.value}"
    assert dut.m_axis_tlast.value == 1, f"[ERROR] m_axis_tlast value is : {dut.m_axis_tlast.value}"
    assert dut.m_axis_tuser.value == 0x2, f"[ERROR] m_axis_tuser value is : {dut.m_axis_tuser.value}"

    print(f'successfully received data from stream 2 with correct tag id in m_axis_tuser channel  ')

    await FallingEdge(dut.clk)
    dut.s_axis_tvalid_2.value = 0
    await FallingEdge(dut.clk)
    await FallingEdge(dut.clk)

    await FallingEdge(dut.clk)
    dut.s_axis_tdata_3.value = 0xff
    dut.s_axis_tvalid_3.value = 1
    dut.s_axis_tlast_3.value = 0
    await FallingEdge(dut.clk)
    dut.s_axis_tdata_3.value = 0xf0
    dut.s_axis_tvalid_3.value = 1
    dut.s_axis_tlast_3.value = 0
    assert dut.m_axis_tdata.value == 0xff, f"[ERROR] m_axis_tdata value is : {dut.m_axis_tdata.value}"
    assert dut.m_axis_tvalid.value == 1, f"[ERROR] m_axis_tvalid value is : {dut.m_axis_tvalid.value}"
    assert dut.m_axis_tlast.value == 0, f"[ERROR] m_axis_tlast value is : {dut.m_axis_tlast.value}"
    assert dut.m_axis_tuser.value == 0x3, f"[ERROR] m_axis_tuser value is : {dut.m_axis_tuser.value}"

    await FallingEdge(dut.clk)
    dut.s_axis_tdata_3.value = 0xfa
    dut.s_axis_tvalid_3.value = 1
    dut.s_axis_tlast_3.value = 1
    assert dut.m_axis_tdata.value == 0xf0, f"[ERROR] m_axis_tdata value is : {dut.m_axis_tdata.value}"
    assert dut.m_axis_tvalid.value == 1, f"[ERROR] m_axis_tvalid value is : {dut.m_axis_tvalid.value}"
    assert dut.m_axis_tlast.value == 0, f"[ERROR] m_axis_tlast value is : {dut.m_axis_tlast.value}"
    assert dut.m_axis_tuser.value == 0x3, f"[ERROR] m_axis_tuser value is : {dut.m_axis_tuser.value}"
    await RisingEdge(dut.clk)
    assert dut.m_axis_tdata.value == 0xfa, f"[ERROR] m_axis_tdata value is : {dut.m_axis_tdata.value}"
    assert dut.m_axis_tvalid.value == 1, f"[ERROR] m_axis_tvalid value is : {dut.m_axis_tvalid.value}"
    assert dut.m_axis_tlast.value == 1, f"[ERROR] m_axis_tlast value is : {dut.m_axis_tlast.value}"
    assert dut.m_axis_tuser.value == 0x3, f"[ERROR] m_axis_tuser value is : {dut.m_axis_tuser.value}"

    print(f'successfully received data from stream 3 with correct tag id in m_axis_tuser channel  ')

   
    print(f' tested successfully')
    