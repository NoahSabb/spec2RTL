# Simple tests for an counter module
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
import random
from collections import deque
from cocotb.triggers import Timer

import threading
import urllib.request

@cocotb.test()
async def test_palindrome_detect(dut):
    NUM_TEST = 100
    # generate a clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.bit_stream.value = 0

    # Reset DUT
    dut.reset.value = 1

    # reset the module, wait 2 rising edges until we release reset
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    
    bit_stream_list = deque(3*[0], 3)
    for n in range(NUM_TEST):
        bit = random.randint(0, 1)
        dut.bit_stream.value = bit
        print("generated bit: "+str(bit))
        if (n>=4):
            print("palindrome",dut.palindrome_detected.value)
            await FallingEdge(dut.clk)
            assert dut.palindrome_detected.value == expected_palind(bit_stream_list), "palindrome result is incorrect: %s != %s" % (str(dut.palindrome_detected.value), expected_palind(bit_stream_list))
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        bit_stream_list.append(bit)
        bit_stream_list.append(bit)
        print("bit stream as input: ",bit_stream_list)
    
def expected_palind (expected_out):
    if (expected_out[0]==expected_out[2]):
        expected_palindrome = 1
    else:
        expected_palindrome = 0
    return expected_palindrome
