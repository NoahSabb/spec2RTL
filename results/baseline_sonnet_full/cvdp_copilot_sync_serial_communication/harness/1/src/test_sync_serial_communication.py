import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge,FallingEdge,Timer
import harness_library as hrs_lb
import random


sel_value = [1,2,3,4]


# Main test for sync_communication top module
@cocotb.test()
async def test_sync_communication(dut):
    #data_wd = int(dut.DATA_WIDTH.value)                                    # Get the data width from the DUT (Device Under Test)
    # Start the clock with a 10ns time period

    sel = random.choice(sel_value)

    if sel == 1:
        range_value = 8
        data_in = random.randint(0, 127)
    elif sel == 2:
        range_value = 16
        data_in = random.randint(0,4196)
    elif sel == 3:
        range_value = 32
        data_in = random.randint(0,18192)
    elif sel == 4:
        range_value = 64
        data_in = random.randint(0,154097)

    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())

    # Initialize the DUT signals with default 0
    await hrs_lb.dut_init(dut)

    # Reset the DUT rst_n signal
    await hrs_lb.reset_dut(dut.reset_n, duration_ns=25, active=False)

    # Ensure all control signals are low initially before starting the test
    dut.sel.value = 0
    dut.data_in.value = 0

    # Main test loop to validate both PISO and SIPO functionality
    for _ in range(sel):
        await drive_byte(dut,sel,range_value,data_in)
        await hrs_lb.reset_dut(dut.reset_n, duration_ns=25, active=False)

        
async def drive_byte(dut,sel,range_value,data_in):
    """Drive a byte of data to the DUT"""
    await RisingEdge(dut.clk)
    dut.data_in.value = data_in  # Assign a random byte (0-127)
    dut._log.info(f" data_in = {int(dut.data_in.value)}, sel = {dut.sel.value}")
    for i in range(range_value):
        dut.sel.value  = sel
        #dut._log.info(f" data_in = {int(dut.data_in.value)}, sel = {dut.sel.value}")
        await RisingEdge(dut.clk)
    await RisingEdge(dut.done)
    await RisingEdge(dut.clk)
    dut._log.info(f" data_in = {int(dut.data_in.value)}, sel = {dut.sel.value}, data_out = {int(dut.data_out.value)}, done = {dut.done.value}")

    expected_data_out = dut.data_in.value
    dut._log.info(f" data_in = {int(dut.data_in.value)}, expected_data_out = {int(expected_data_out)}, data_out = {int(dut.data_out.value)}")

    assert int(dut.data_out.value) == expected_data_out, f"Test failed: Expected {expected_data_out}, got {int(dut.data_out.value)}"
