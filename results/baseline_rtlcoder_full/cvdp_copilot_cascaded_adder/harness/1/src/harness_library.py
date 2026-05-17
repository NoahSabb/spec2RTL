import cocotb
from cocotb.triggers import  Timer, RisingEdge, FallingEdge, Edge, ReadOnly
from cocotb.clock import Clock
from enum import Enum
import random


async def dut_init(dut):
    # iterate all the input signals and initialize with 0
    for signal in dut:
        if signal._type == "GPI_NET":
            signal.value = 0

def random_stim_generator(IN_DATA_NS, IN_DATA_WIDTH, StimType):
    golden_output = 0 
    input_1d = 0 
    for _ in range (IN_DATA_NS):
        if StimType == "RANDOM":
            random_value = random.randint(0, (1 << IN_DATA_WIDTH) - 1)
        elif StimType == "DIRECT_MAX":
            random_value = (1 << IN_DATA_WIDTH) - 1
        elif StimType == "DIRECT_MIN":
            random_value = 0    
        golden_output = golden_output + random_value 
        input_1d = (input_1d << IN_DATA_WIDTH) | random_value
    
    return (input_1d, golden_output)