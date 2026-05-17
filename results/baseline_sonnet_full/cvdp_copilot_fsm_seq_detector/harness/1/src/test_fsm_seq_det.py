import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ClockCycles, Timer
import test_runner
import json
import os


async def init_dut(dut):
    dut.rst_in.value     = 1
    dut.seq_in.value    = 0

    await RisingEdge(dut.clk_in)



@cocotb.test()
async def test_basic(dut):
    cocotb.start_soon(Clock(dut.clk_in, 10, unit='ns').start())
    await init_dut(dut)

    # Retrieve test_sequence and expected_output from environment variables
    test_sequence = json.loads(os.getenv("TEST_SEQUENCE"))
    expected_output = json.loads(os.getenv("EXPECTED_OUTPUT"))

    # ----------------------------------------
    # - Check No Operation
    # ----------------------------------------

    await RisingEdge(dut.clk_in)
    await RisingEdge(dut.clk_in)  # Wait until 2 clocks to de-assert reset
    dut.rst_in.value = 0
    await RisingEdge(dut.clk_in)  

    # Apply the test sequence with seq_in updated for only one clock cycle
    for i in range(len(test_sequence)):
        await RisingEdge(dut.clk_in)
        dut.seq_in.value = test_sequence[i]
        dut._log.info(f"Input: {dut.seq_in.value}, Decoded Output: {dut.seq_detected.value}, test_sequence: {test_sequence[i]}")
        await FallingEdge(dut.clk_in)
        assert dut.seq_detected.value == expected_output[i], f"Error at step {i}"
