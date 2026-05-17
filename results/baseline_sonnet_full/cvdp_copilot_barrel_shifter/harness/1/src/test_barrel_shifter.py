import cocotb
import os
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ClockCycles, Timer, Join
import random

# ----------------------------------------
# - Tests
# ----------------------------------------

@cocotb.test()
async def test_barrel_1(dut):
      
    dut.data_in.value = int((1.0 - random.random()) * 2 ** 8);   
    dut.shift_bits.value = 0b011    
    dut.left_right.value = 0b1;
    
    await Timer(10, unit="ns")
    print("data_in ",str(dut.data_in.value))
    print("shift_bits ",str(dut.shift_bits.value))
    print("left_right",str(dut.left_right.value))
    print("data_out ",str(dut.data_out.value))
    
    shift_result = (int(dut.data_in.value) << int(dut.shift_bits.value)) & 0xFF
    print((shift_result))
    if (dut.data_out.value == shift_result):
        print("Left shift process is successful")
    assert dut.data_out.value == shift_result, f"Computed and DUT outputs of barrel shifter are not correct"
 
@cocotb.test()
async def test_barrel_2(dut):
      
    # Assert seed and wait
    dut.data_in.value = int((1.0 - random.random()) * 2 ** 8);
    dut.shift_bits.value = 0b111    
    dut.left_right.value = 0b0;        
    
    await Timer(10, unit="ns")
    print("data_in ",str(dut.data_in.value))
    print("shift_bits ",str(dut.shift_bits.value))
    print("left_right",str(dut.left_right.value))
    print("data_out ",str(dut.data_out.value))
    shift_result = (int(dut.data_in.value) >> int(dut.shift_bits.value)) & 0xFF
    print((shift_result))
    if (dut.data_out.value == shift_result):
        print("Right shift process is successful");
    assert dut.data_out.value == shift_result, f"Computed and DUT outputs of barrel shifter are not correct"
 

@cocotb.test()
async def test_barrel_3(dut):
      
    # Assert seed and wait
    dut.data_in.value = int((1.0 - random.random()) * 2 ** 8);
    dut.shift_bits.value = 0b000
    dut.left_right.value = 0b1;

    await Timer(10, unit="ns")
    print("data_in ",str(dut.data_in.value))
    print("shift_bits ",str(dut.shift_bits.value))
    print("left_right",str(dut.left_right.value))
    print("data_out ",str(dut.data_out.value))
    shift_result = (int(dut.data_in.value) << int(dut.shift_bits.value)) & 0xFF
    print((shift_result))
    if (dut.data_out.value == shift_result):
        print("Left shift process is successful")
    assert dut.data_out.value == shift_result, f"Computed and DUT outputs of barrel shifter are not correct"



