import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ClockCycles, Timer
import random
import harness_library as hrs_lb

# ----------------------------------------
# - Tests
# ----------------------------------------

@cocotb.test()
async def test_penc(dut):

    encoder_in = int(cocotb.plusargs["encoder_in"])
    
    print("input value =", bin(encoder_in))

    await hrs_lb.dut_init(dut)
    
    # print(dir(dut))
    dut['in'].value = encoder_in 
    await Timer(10, unit="ns")

    # print(dut['in'].value)
    msb_1_bit_num = hrs_lb.highbit_number(encoder_in, msb=True, length=8)
    # print(f"msb_1_bit_num = {msb_1_bit_num}")

    # ----------------------------------------
    # - Check No Operation
    # ----------------------------------------
    # print(f"encoder input = {encoder_in}, highest bit number is {msb_1_bit_num} and output is {dut.out.value}")
    if dut['in'].value.is_resolvable and dut.out.value.is_resolvable:
        assert (dut.out.value == msb_1_bit_num), f"encoder input = {encoder_in} binary is {bin(encoder_in)}, highest bit number is {msb_1_bit_num} and output is {dut.out.value}"
    else:
        raise Exception("Error, input and output are not resolveable")
