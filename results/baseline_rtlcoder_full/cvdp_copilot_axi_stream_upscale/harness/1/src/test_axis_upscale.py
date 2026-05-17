import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ClockCycles, Timer
import random
import time
import harness_library as hrs_lb

@cocotb.test()
async def test_axis_upscale(dut):
    # Seed the random number generator with the current time or another unique value
    random.seed(time.time())
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 100, unit='ns').start())
    
    
    # Initialize DUT
    print(f'm_axis_data before initialization = {dut.m_axis_data.value}') ####need to remove
    await hrs_lb.dut_init(dut) 
    print(f'm_axis_data after initialization   = {dut.m_axis_data.value}') ####need to remove
    # Apply reset 
    await hrs_lb.reset_dut(dut.resetn, dut)
    await RisingEdge(dut.clk)
    assert dut.m_axis_valid.value == 0, f"[ERROR] s_axis_valid : {dut.m_axis_valid.value}"
    assert dut.m_axis_data.value == 00000000000000000000000000000000, f"[ERROR] m_axis_data : {dut.m_axis_data.value}"
    assert dut.s_axis_ready.value == 0, f"[ERROR] s_axis_ready : {dut.s_axis_ready.value}"

    print(f'reset succesfull') 
    

    await FallingEdge(dut.clk)
    dfmt_enable = 1
    dfmt_type = 1
    dfmt_se =  1
    s_axis_data = 0b000000000000000000000100 
    s_axis_valid = 1
    dut.s_axis_data.value = s_axis_data
    dut.s_axis_valid.value = s_axis_valid
    dut.dfmt_enable.value = dfmt_enable
    dut.dfmt_type.value = dfmt_type
    dut.dfmt_se.value = dfmt_se

    await FallingEdge(dut.clk)

    print(f'm_axis_valid   = {dut.m_axis_valid.value}') ####need to remove
    print(f'm_axis_data   = {dut.m_axis_data.value}') ####need to remove
    assert dut.m_axis_valid.value == s_axis_valid, f"[ERROR] s_axis_valid : {dut.m_axis_valid.value}"

    if(dfmt_enable == 1):
        if(dfmt_type == 1):
            if(dfmt_se == 1):
              assert  dut.m_axis_data.value[23] == ~dut.s_axis_data.value[23], f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"
              assert  dut.m_axis_data.value[31:24] == 8 * str(~dut.s_axis_data.value[23]), f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"
              assert dut.m_axis_data.value[22:0] == dut.s_axis_data.value[22:0], f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"
            else:
                assert dut.m_axis_data.value[23] == ~dut.s_axis_data.value[23], f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"
                assert dut.m_axis_data.value[31:24] == 8 * (0), f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"
                assert dut.m_axis_data.value[22:0] == dut.s_axis_data.value[22:0], f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"
        else:
            if(dfmt_se == 1):
                assert dut.m_axis_data.value[23] == dut.s_axis_data.value[23], f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"
                assert dut.m_axis_data.value[31:24] == 8 * str(~dut.s_axis_data.value[23]), f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"
                assert dut.m_axis_data.value[22:0] == dut.s_axis_data.value[22:0], f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"
            else:
                assert dut.m_axis_data.value[23] == dut.s_axis_data.value[23], f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"
                assert dut.m_axis_data.value[31:24] == 8 * (0), f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"
                assert dut.m_axis_data.value[22:0] == dut.s_axis_data.value[22:0], f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"

    else :    
        assert dut.m_axis_data.value == s_axis_data, f"[ERROR] m_axis_data is not matching to s_axis_data : {dut.m_axis_data.value}"

    m_axis_ready = 1
    dut.m_axis_ready.value = m_axis_ready

    await FallingEdge(dut.clk)

    print(f's_axis_ready   = {dut.s_axis_valid.value}') ####need to remove
    

    print(f'Testing completed succesfully') 
    
    