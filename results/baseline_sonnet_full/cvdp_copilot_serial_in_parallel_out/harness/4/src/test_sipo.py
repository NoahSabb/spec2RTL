import cocotb
import os
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ClockCycles, Timer, Join
import random

# ----------------------------------------
# - Tests
# ----------------------------------------

##Test 1 with a randomly generated 8-bit value
@cocotb.test()
async def test_sipo_1(dut):
    
    # Start clock thread
    cocotb.start_soon(Clock(dut.clock, 10, unit='ns').start())

    # Generate 8-bit data to be sent serially to SIPO shift register
    reg_data = int((1.0 - random.random()) * 2 ** 8);
    print("reg_data_1 ",bin(reg_data))
    
    for i in range(8):
       
        dut.serial_in.value = ((reg_data << i) & 0x80 ) >> 7
        await FallingEdge(dut.clock)
        
        print("Bit ",i," ",dut.serial_in.value)
        
    print("The parallel out data is ", dut.parallel_out.value)
    assert reg_data == int(dut.parallel_out.value), f"The 8-bit register output doesn't match with the expected value"


##Test 2 with a fixed 8-bit value
@cocotb.test()
async def test_sipo_2(dut):
    
    # Start clock thread
    cocotb.start_soon(Clock(dut.clock, 10, unit='ns').start())

    # 8-bit data to be sent serially to SIPO shift register
    reg_data = int(100)
    print("reg_data_2 ",bin(reg_data))
    
    for i in range(8):
        
        dut.serial_in.value = ((reg_data << i) & 0x80 ) >> 7
        await FallingEdge(dut.clock)
        print("Bit ",i," ",dut.serial_in.value)
        
    print("The parallel out data is ", dut.parallel_out.value)
    assert reg_data == int(dut.parallel_out.value), f"The 8-bit register output doesn't match with the expected value"


##Test 3 with a randomly generated 8-bit value    
@cocotb.test()
async def test_sipo_3(dut):
    
    # Start clock thread
    cocotb.start_soon(Clock(dut.clock, 10, unit='ns').start())

    # Generate 8-bit data to be sent serially to SIPO shift register
    reg_data = int((1.0 - random.random()) * 2 ** 8);
    print("reg_data_3 ",bin(reg_data))
    
    for i in range(8):
        
        dut.serial_in.value = ((reg_data << i) & 0x80 ) >> 7
        await FallingEdge(dut.clock)
        print("Bit ",i," ",dut.serial_in.value)
        
    print("The parallel out data is ", dut.parallel_out.value)
    assert reg_data == int(dut.parallel_out.value), f"The 8-bit register output doesn't match with the expected value"
