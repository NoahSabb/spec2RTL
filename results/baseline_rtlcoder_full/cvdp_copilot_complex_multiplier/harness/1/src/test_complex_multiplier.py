import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
import random

def reference_complex_multiplier(a_real, a_imag, b_real, b_imag):
    result_real = (a_real * b_real) - (a_imag * b_imag)
    result_imag = (a_real * b_imag) + (a_imag * b_real)
    return result_real, result_imag

async def initialize_dut(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.arst_n.value = 0
    await RisingEdge(dut.clk)
    dut.arst_n.value = 1
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_complex_multiplier(dut):
    await initialize_dut(dut)
    match = 0
    mismatch = 0

    NUM_TESTS = 1000
    # MIN_INPUT_VAL = 1
    MAX_INPUT_VAL = 0xFF

    for i in range(NUM_TESTS+1): # The result of Nth test is available in N+1 cycle.
        
        a_real = random.randint(-MAX_INPUT_VAL, MAX_INPUT_VAL)
        a_imag = random.randint(-MAX_INPUT_VAL, MAX_INPUT_VAL)
        b_real = random.randint(-MAX_INPUT_VAL, MAX_INPUT_VAL)
        b_imag = random.randint(-MAX_INPUT_VAL, MAX_INPUT_VAL)

        dut.a_real.value = a_real
        dut.a_imag.value = a_imag
        dut.b_real.value = b_real
        dut.b_imag.value = b_imag

        expected_real, expected_imag = reference_complex_multiplier(a_real, a_imag, b_real, b_imag)

        await RisingEdge(dut.clk)
        a_real = random.randint(-MAX_INPUT_VAL, MAX_INPUT_VAL)
        a_imag = random.randint(-MAX_INPUT_VAL, MAX_INPUT_VAL)
        b_real = random.randint(-MAX_INPUT_VAL, MAX_INPUT_VAL)
        b_imag = random.randint(-MAX_INPUT_VAL, MAX_INPUT_VAL)

        dut.a_real.value = a_real
        dut.a_imag.value = a_imag
        dut.b_real.value = b_real
        dut.b_imag.value = b_imag
        await RisingEdge(dut.clk)


        actual_real = dut.result_real.value.signed_integer
        actual_imag = dut.result_imag.value.signed_integer

        if ((actual_real == expected_real) and (actual_imag == expected_imag)):
            print(f"Test {i} Passed: result = ({actual_real} + {actual_imag}j) matches reference ({expected_real} + {expected_imag}j)")
            match = match+1
        else:
            print(f"Test {i} Failed: result = ({actual_real} + {actual_imag}j) matches reference ({expected_real} + {expected_imag}j)")
            mismatch = mismatch+1

    if (mismatch==0):
        print(f"All {NUM_TESTS} test cases PASSED successfully.")
    else: 
        print(f"Matched: {match} , Mismatched {mismatch} - TEST FAILED.")
