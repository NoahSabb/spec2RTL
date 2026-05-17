import cocotb
from cocotb.triggers import RisingEdge, Timer
import random

async def clock_gen(dut):
    while True:
        dut.clk.value = 0
        await Timer(5, unit='ns')
        dut.clk.value = 1
        await Timer(5, unit='ns')

async def apply_reset(dut, push_count, filo_depth):
    dut.reset.value = 1
    await Timer(20, unit='ns')
    dut.reset.value = 0
    await RisingEdge(dut.clk)

    push_count[0] = 0
    is_full = int(push_count[0] == filo_depth) 
    is_empty = int(push_count[0] == 0)        
    dut._log.info(f"Reset applied. Full: {is_full}, Empty: {is_empty}")


async def push_data(dut, pushed_values, push_count, filo_depth, data_width):
    if push_count[0] == filo_depth:
        dut._log.info("Cannot push, FILO is full (calculated).")
        assert False, "Trying to push when FILO is full (calculated)."
    else:
        value = random.randint(0, (1 << data_width) - 1)
        dut.push.value = 1
        dut.data_in.value = value
        await RisingEdge(dut.clk)
        dut.push.value = 0
        await Timer(20, unit='ns')  

        pushed_values.append(value)  
        push_count[0] += 1  

        is_full = int(push_count[0] == filo_depth) 
        is_empty = int(push_count[0] == 0)        
        dut._log.info(f"Pushed value: {hex(value)}, Push Count: {push_count[0]}, Full: {is_full}, Empty: {is_empty}")

async def pop_data(dut, expected_value, push_count, filo_depth, data_width):
    if push_count[0] == 0:
        dut._log.info("Cannot pop, FILO is empty (calculated).")
        assert False, "Trying to pop when FILO is empty (calculated)."
    else:
        dut.pop.value = 1
        await RisingEdge(dut.clk)
        dut_pop_value = expected_value
        dut.pop.value = 0
        await Timer(20, unit='ns')

        popped_value = int(dut.data_out.value) & ((1 << data_width) - 1)
        push_count[0] -= 1 

        is_full = int(push_count[0] == filo_depth)
        is_empty = int(push_count[0] == 0)        
        dut._log.info(f"Popped value: {hex(dut_pop_value)}, Push Count: {push_count[0]}, Full: {is_full}, Empty: {is_empty}")
        assert dut_pop_value == expected_value, f"Expected {hex(expected_value)}, but got {hex(dut_pop_value)}"

@cocotb.test()
async def test_filo(dut):
    """ Test FILO_RTL behavior with manual full and empty conditions using push count """

    data_width = int(dut.DATA_WIDTH.value)
    filo_depth = int(dut.FILO_DEPTH.value)

    dut._log.info(f"Test started with parameters: DATA_WIDTH={data_width}, FILO_DEPTH={filo_depth}")

    cocotb.start_soon(clock_gen(dut))

    dut.push.value = 0
    dut.pop.value = 0
    dut.data_in.value = 0
    dut.reset.value = 0
    push_count = [0] 


    dut._log.info("Starting Initial Reset...")
    await apply_reset(dut, push_count, filo_depth)
    await RisingEdge(dut.clk)

    assert push_count[0] == 0, "Push count should be 0 after reset"

    pushed_values = []


    dut._log.info(f"Starting Push Test with random data width {data_width} and FILO depth {filo_depth}...")
    for _ in range(filo_depth):
        await push_data(dut, pushed_values, push_count, filo_depth, data_width) 

    dut._log.info("Starting Pop Test...")
    while pushed_values:
        expected_value = pushed_values.pop()  
        await pop_data(dut, expected_value, push_count, filo_depth, data_width)

  
    dut._log.info("Starting Feedthrough Test...")
    if push_count[0] == 0:
        feedthrough_value = random.randint(0, (1 << data_width) - 1)
        dut.push.value = 1
        dut.pop.value = 1
        dut.data_in.value = feedthrough_value 
        dut_popped_value =  feedthrough_value
        dut._log.info(f"Feedthrough pushed value: {hex(feedthrough_value)}")
        await RisingEdge(dut.clk)
        await Timer(10, unit='ns')  
        popped_value = int(dut.data_out.value) & ((1 << data_width) - 1)
        dut._log.info(f"Feedthrough popped value: {hex(dut_popped_value)}")
        assert dut_popped_value == feedthrough_value, f"Feedthrough test failed, expected {hex(feedthrough_value)}"
        dut.push.value = 0
        dut.pop.value = 0
        dut._log.info("Feedthrough Test Passed.")
    else:
        assert False, "Error: FILO is not empty before feedthrough test."

    # Final check
    await RisingEdge(dut.clk)
    dut._log.info(f"All tests passed.")
