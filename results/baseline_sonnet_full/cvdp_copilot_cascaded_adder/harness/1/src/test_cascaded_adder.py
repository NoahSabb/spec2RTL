import cocotb
from cocotb.triggers import  Timer, RisingEdge, ReadOnly, FallingEdge
from cocotb.clock import Clock
import harness_library as util
import random

@cocotb.test()
async def cascaded_adder(dut):
    # Generate two random period clock signals
    clock_period_ns = 10  # For example, 10ns clock period
    cocotb.start_soon(Clock(dut.clk, clock_period_ns, unit='ns', period_high=(clock_period_ns+1)//2 if clock_period_ns%2 else clock_period_ns//2).start())
    dut._log.info(f"DUT_CLK STARTED")
    await util.dut_init(dut)
    # DUT RESET 
    dut.rst_n.value = 1
    await Timer(5, unit="ns")

    dut.rst_n.value = 0 
    await ReadOnly()
    # for async reset, right after reset assertion design should be held in reset
    assert dut.o_valid.value == 0, f"Valid output should be driven low"
    assert dut.o_data.value == 0 , f"Output should be driven low"  
    await Timer(30, unit="ns")
    dut.rst_n.value = 1
    dut._log.info(f"DUT IS OUT OF RESET") 
    
    IN_DATA_WIDTH = int(dut.IN_DATA_WIDTH.value)
    IN_DATA_NS = int(dut.IN_DATA_NS.value)
    
    ## Direct test for overflow
    for i in range(5):
        stimulus= util.random_stim_generator(IN_DATA_NS, IN_DATA_WIDTH, "DIRECT_MAX")
        input_data = stimulus[0]
        golden_output = stimulus[1]
        await RisingEdge(dut.clk)
        dut.i_data.value = input_data
        dut.i_valid.value = 1
        await RisingEdge(dut.clk)
        dut.i_valid.value = 0

        latency = 0
        while (dut.o_valid.value != 1):
            await RisingEdge(dut.clk)
            latency = latency + 1

        assert latency == 2, f"Valid output should have latency of 2 clk cycles"
        assert dut.o_data.value == golden_output , f"Output doesn't match golden output: dut_output {hex(dut.o_data.value)}, Expected output {hex(golden_output)}"  
  

    for i in range(50):
        stimulus= util.random_stim_generator(IN_DATA_NS, IN_DATA_WIDTH, "RANDOM")
        input_data = stimulus[0]
        golden_output = stimulus[1]
        await RisingEdge(dut.clk)
        dut.i_data.value = input_data
        dut.i_valid.value = 1 
        await RisingEdge(dut.clk)
        dut.i_valid.value = 0 
        
        latency = 0 
        while (dut.o_valid.value != 1):
            await RisingEdge(dut.clk)
            latency = latency + 1
       
        assert latency == 2, f"Valid output should have latency of 2 clk cycles"
        assert dut.o_data.value == golden_output , f"Output doesn't match golden output: dut_output {hex(dut.o_data.value)}, Expected output {hex(golden_output)}"  

## Direct test for valid streaming 
    outputs_list = []        
    for i in range(50):
        # first two cycles only append
        if i <2 :
            stimulus= util.random_stim_generator(IN_DATA_NS, IN_DATA_WIDTH, "RANDOM")
            input_data = stimulus[0]
            golden_output = stimulus[1]
            outputs_list.append(golden_output)
            await RisingEdge(dut.clk)
            await RisingEdge(dut.clk)
            dut.i_data.value = input_data
            dut.i_valid.value = 1  
            assert dut.o_valid.value == 0, "During initial 2 cycles, o_valid should be zero"
        else: # append and pop 
            stimulus= util.random_stim_generator(IN_DATA_NS, IN_DATA_WIDTH, "RANDOM")
            input_data = stimulus[0]
            golden_output = stimulus[1]
            outputs_list.append(golden_output)
            await RisingEdge(dut.clk)
            await RisingEdge(dut.clk)
            dut.i_data.value = input_data
            dut.i_valid.value = 1
            expected_result =  outputs_list.pop(0)
            dut_output = int (dut.o_data.value)
            
            await ReadOnly()
            assert dut.o_valid.value == 1, f"Valid output should have latency of 2 clk cycles"
            assert dut_output == expected_result , f"Output doesn't match golden output: dut_output {hex(dut_output)}, Expected output {hex(expected_result)}"
    await FallingEdge(dut.clk)
    dut.rst_n.value = 0
    await ReadOnly()
    assert dut.o_valid.value == 0, "During reset, o_valid should be zero"
    assert dut.o_data.value == 0, "During reset, o_data should be zero"
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
