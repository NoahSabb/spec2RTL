import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb.regression import TestFactory
import random

# Constants for the affinity parameter
AFINITY_0 = 0

async def reset_dut(dut):
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

async def drive_master_transaction(dut, master, valid, data):
    """Drives a transaction on the specified master interface."""
    if master == 0:
        dut.m0_valid.value = valid
        dut.m0_data.value = data
    elif master == 1:
        dut.m1_valid.value = valid
        dut.m1_data.value = data
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

async def drive_both_master_transaction(dut, valid, data0, data1):
    """Drives a transaction on the specified master interface."""
    dut.m0_valid.value = valid
    dut.m0_data.value = data0
    dut.m1_valid.value = valid
    dut.m1_data.value = data1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

async def release_master(dut, master):
    """Releases the transaction on the specified master interface."""
    if master == 0:
        dut.m0_valid.value = 0
    elif master == 1:
        dut.m1_valid.value = 0
    await RisingEdge(dut.clk)

async def monitor_slave_transaction(dut, expected_data):
    """Monitors and checks if the transaction on the slave interface is as expected."""
    await FallingEdge(dut.clk)
    if dut.s_valid.value and dut.s_ready.value:
        assert dut.s_data.value == expected_data, f"Expected data {hex(expected_data)}, but got {hex(int(dut.s_data.value))}"
        cocotb.log.info(f"Transaction successful: Received data {dut.s_data.value}")

async def test_transaction(dut, affinity):
    NUM_TEST = 1000
    """Main test coroutine that applies different transaction scenarios to the DUT."""
    # AFINITY = dut.AFINITY.value  # Set the affinity parameter
    for x in range(NUM_TEST):
        AFINITY_TEST = random.choice([True, False])
        if AFINITY_TEST == True:
            print("AFINITY_TEST")
            data0      = random.randint(0,0xFFFF_FFFF)
            data1      = random.randint(0,0xFFFF_FFFF)
            dut.s_ready.value = 1
            await drive_both_master_transaction(dut, 1, data0=data0, data1=data1)

            if affinity == AFINITY_0:
                await monitor_slave_transaction(dut, expected_data=data0)
            else:
                await monitor_slave_transaction(dut, expected_data=data1)
            await release_master(dut, 0)
            await release_master(dut, 1)

        else:
            master_num = random.randint(0, 1) 
            data       = random.randint(0,0xFFFF_FFFF)
            # master_num = 0
            dut.s_ready.value = 1
            await drive_master_transaction(dut, master_num, valid=1, data=data)
            await monitor_slave_transaction(dut, expected_data=data)
            await release_master(dut, master_num)

@cocotb.test()
async def test_data_bus_controller(dut):
    AFINITY = dut.AFINITY.value
    # Generate the clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    # Run the test with AFINITY set to 0
    dut._log.info("Testing with Random AFINITY")
    await test_transaction(dut, AFINITY)