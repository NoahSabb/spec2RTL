import cocotb
import os
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ClockCycles, Timer, Join
import random

# ----------------------------------------
# - Tests
# ----------------------------------------

async def assert_reset (dut):
    
    dut.rst.value = 0
    for i in range(2):
        await FallingEdge(dut.clk)
    dut.rst.value = 1

@cocotb.test()
async def test_piso_1(dut):

    # Start clock thread
    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())
    await assert_reset(dut)
    
    data_1 = list()
    data_2 = list()
    data_3 = list()
    
    for i in range(32):
        await FallingEdge(dut.clk)
        if (i < 8):
            data_1.append(int(dut.serial_out.value))
            print("Serial out ",dut.serial_out.value)
        if (i >= 8 and i < 16):
            data_2.append(int(dut.serial_out.value))
            print("Serial out ",dut.serial_out.value)
        if (i >= 24 and i < 32):
            data_3.append(int(dut.serial_out.value))
            print("Serial out ",dut.serial_out.value)
            
    print(data_1)
    assert data_1 == [0,0,0,0,0,0,0,1], f"Serial data sequence is not correct"

    print(data_2)
    assert data_2 == [0,0,0,0,0,0,1,0], f"Serial data sequence is not correct"

    print(data_3)
    assert data_3 == [0,0,0,0,0,1,0,0], f"Serial data sequence is not correct"


@cocotb.test()
async def test_piso_2(dut):

    # Start clock thread
    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())
    await assert_reset(dut)

    data = list()
    
    for i in range(16):
        await FallingEdge(dut.clk)
        if (i >= 8 and i < 16):
            data.append(int(dut.serial_out.value))
            print("Serial out ",i,dut.serial_out.value)
            
    print(data)
    assert data == [0,0,0,0,0,0,1,0], f"Serial data sequence is not correct"


@cocotb.test()
async def test_piso_3(dut):

    # Start clock thread
    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())
    await assert_reset(dut)
    
    data = list()
    
    for i in range(32):
        await FallingEdge(dut.clk)
        if (i > 23 and i < 32):
            data.append(int(dut.serial_out.value))
            print("Serial out ",dut.serial_out.value)
        
    print(data)
    assert data == [0,0,0,0,0,1,0,0], f"Serial data sequence is not correct"


@cocotb.test()
async def test_piso_4(dut):
    #print("stimulus script : register_size test_piso_2",int(dut.register_size.value))
    # Start clock thread
    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())
    await assert_reset(dut)
    
    data   = list()
    data_1 = list()
    data_2 = list()
    
    for i in range((2 ** 8 + 1) * 8):
        
        await FallingEdge(dut.clk)
        if (i < 8): #checking the first sequence 0000_0001 after 8 clock cycles
            data.append(int(dut.serial_out.value))
            print("Serial out ",i,dut.serial_out.value)
        if (i >= ((2 ** 8 - 1) * 8) and i < ((2 ** 8 + 0) * 8)): #checking the sequence 0000_0000 after rollout
            data_1.append(int(dut.serial_out.value))
            print("Serial out ",i,dut.serial_out.value)
        if (i >= ((2 ** 8 + 0) * 8) and i < ((2 ** 8 + 1) * 8)): #checking the sequence 0000_0001 after rollout
            data_2.append(int(dut.serial_out.value))
            print("Serial out ",i,dut.serial_out.value)
            
    print("Initial 8-bit sequence", data)
    print("First   8-bit sequence 0000_0000 after rollout",data_1)
    print("Second  8-bit sequence 0000_0001 after rollout",data_2)
    
    tmp = [0] * 30
    tmp_1 = tmp.extend([1,0])
    
    assert data_1 == [0,0,0,0,0,0,0,0], f"Sequences are not same. Rollout is not happening properly"
    assert data == data_2, f"Sequences are not same. Rollout is not happening properly"

async def piso_loop (dut, _range) -> None:
    
    tmp = 1
    for i in range(_range):
        index = (i % 8)
        await FallingEdge(dut.clk)
        assert int(dut.serial_out.value) == (tmp >> ( 7 - index )) % 2
        tmp += 1 if index == 7 else 0

@cocotb.test()
async def test_reset (dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())
    await assert_reset(dut)

    # Check output interface
    assert int(dut.serial_out.value) == 0, "serial_out value didn't reset properly"

    # Check internal signals reset
    await piso_loop(dut, 4 * 8 - 2)
    print("Done first loop test...")
    
    # Trigger reset inside test
    dut.rst.value = 0
    await FallingEdge(dut.clk)
    dut.rst.value = 1

    print("Done mid test reset application...")
    await piso_loop(dut, 8 * 8)
