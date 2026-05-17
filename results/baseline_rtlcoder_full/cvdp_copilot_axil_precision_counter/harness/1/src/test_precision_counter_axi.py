import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly , Timer

import harness_library as hrs_lb
import random

# Function to initialize the DUT
async def initialize_dut(dut):
    dut.axi_awvalid.value = 0
    dut.axi_wvalid.value = 0
    dut.axi_arvalid.value = 0
    dut.axi_bready.value = 0
    dut.axi_rready.value = 0
    dut.axi_awaddr.value = 0
    dut.axi_wdata.value = 0
    dut.axi_wstrb.value = 0
    dut.axi_araddr.value = 0

# Function to reset the DUT
async def reset_dut(reset_signal, duration_ns=25, active=True):
    reset_signal.value = 0 if active else 1
    await Timer(duration_ns, unit="ns")
    reset_signal.value = 1 if active else 0
    await Timer(duration_ns, unit="ns")

# AXI write transaction helper function
async def axi_write(dut, address, data, strb=0xF):
    dut.axi_awaddr.value = address
    dut.axi_wdata.value = data
    dut.axi_awvalid.value = 1
    dut.axi_wvalid.value = 1
    dut.axi_wstrb.value = strb
    await RisingEdge(dut.axi_aclk)

    while not (dut.axi_awready.value and dut.axi_wready.value):
        await RisingEdge(dut.axi_aclk)

    await RisingEdge(dut.axi_aclk)
    dut.axi_awvalid.value = 0
    dut.axi_wvalid.value = 0

    dut.axi_bready.value = 1
    await RisingEdge(dut.axi_aclk)
    dut.axi_bready.value = 0

# AXI read transaction helper function
async def axi_read(dut, address):
    dut.axi_araddr.value = address
    dut.axi_arvalid.value = 1
    dut.axi_rready.value = 1

    while not dut.axi_arready.value:
        await RisingEdge(dut.axi_aclk)

    await RisingEdge(dut.axi_aclk)
    await RisingEdge(dut.axi_aclk)

    dut.axi_arvalid.value = 0

    while not dut.axi_rvalid.value:
        await RisingEdge(dut.axi_aclk)

    await RisingEdge(dut.axi_aclk)
    dut.axi_rready.value = 0

# Function to check output values
async def check_output(dut, address, expected_value, description):
    await axi_read(dut, address)
    assert int(dut.axi_rdata.value) == expected_value, f"{description}: Expected {expected_value}, got {int(dut.axi_rdata.value)}"

# Function to test random countdown values
async def test_random_countdown(dut,DATA_WIDTH):
    for _ in range(10):
        strb = (1 << (DATA_WIDTH // 8)) - 1
        random_value = random.randint(0, (1 << DATA_WIDTH) - 1)
        await axi_write(dut, 0x20, random_value,strb)
        await axi_read(dut, 0x20)
        _ctr = int(dut.axi_rdata.value)
        assert random_value - 10 <= _ctr <= random_value - 1, f"Random countdown value {random_value}: got {_ctr}"


# Function to test IRQ output
async def test_irq_output(dut,DATA_WIDTH):
    strb = (1 << (DATA_WIDTH // 8)) - 1
    await axi_write(dut, 0x24, 0x1,strb)  # Enable IRQ
    await RisingEdge(dut.axi_aclk)
    await axi_write(dut, 0x28, 0x5,strb)  # Write to threshold register
    await RisingEdge(dut.axi_aclk)
    await axi_write(dut, 0x20, 0x5,strb)  # Write to countdown value
    await RisingEdge(dut.axi_aclk)
    await axi_write(dut, 0x00, 0x1,strb)  # Start the counter
    await RisingEdge(dut.axi_aclk)

    # Check IRQ output
    if dut.irq.value:
        dut._log.info("[PASS] IRQ triggered successfully.")
    else:
        dut._log.error("[FAIL] IRQ not triggered.")

# Function to test additional reads
async def test_additional_reads(dut):
    await axi_read(dut, 0x20)  # Read counter value register
    await RisingEdge(dut.axi_aclk)

    await axi_read(dut, 0x04)  # Read dummy register
    dut._log.info("Reading from dummy register 0x04")
    await RisingEdge(dut.axi_aclk)

    await axi_read(dut, 0x08)  # Read another dummy register
    dut._log.info("Reading from dummy register 0x08")
    await RisingEdge(dut.axi_aclk)

    await axi_read(dut, 0x50)  # Attempt to read invalid register
    dut._log.info(" Invalid register 0x50 read .")
    await RisingEdge(dut.axi_aclk)

# Function to test reset behavior
async def test_reset_behavior(dut):
    await axi_write(dut, 0x00, 0x1)  # Start the counter
    random_value = random.randint(1, 100)
    await axi_write(dut, 0x20, random_value)  # Set countdown value

    await reset_dut(dut.axi_aresetn)

    # Verify all registers reset to default values
    await check_output(dut, 0x00, 0x0, "Control register after reset")
    await check_output(dut, 0x20, 0x0, "Countdown value after reset")
    await check_output(dut, 0x10, 0x0, "Elapsed time register after reset")

@cocotb.test()
async def test_precision_counter_axi(dut):
    ADDR_WIDTH = int(dut.C_S_AXI_ADDR_WIDTH.value)
    DATA_WIDTH = int(dut.C_S_AXI_DATA_WIDTH.value)
    # Start the clock with a 10ns time period (100 MHz clock)
    cocotb.start_soon(Clock(dut.axi_aclk, 10, unit='ns').start())

    # Initialize the DUT signals with default 0
    await hrs_lb.dut_init(dut)

    # Reset the DUT rst_n signal
    await hrs_lb.reset_dut(dut.axi_aresetn, duration_ns=25, active=True)

    await RisingEdge(dut.axi_aclk) 

     # Test case 1: Write to the control register and verify
    strb = (1 << (DATA_WIDTH // 8)) - 1
    await axi_write(dut, 0x00, 0x1,strb)  # Start the counter
    await check_output(dut, 0x00, 0x1, "Control register value mismatch")
    await RisingEdge(dut.axi_aclk) 

    # Test case 2: Set countdown value and verify
    random_value = random.randint(0, (1 << DATA_WIDTH) - 1)
    await axi_write(dut, 0x20, random_value,strb)  # Set countdown value to 100
    await axi_read(dut, 0x20)
    _ctr = int(dut.axi_rdata.value)
    assert random_value - 10 <= _ctr <= random_value - 1, f"Countdown value mismatch: wrote {random_value}, read {_ctr}"
    await RisingEdge(dut.axi_aclk) 

    # Test case 3: Verify interrupt mask functionality
    random_value = random.randint(0, (1 << DATA_WIDTH) - 1)
    await axi_write(dut, 0x24, random_value,strb)  # Enable interrupt
    await check_output(dut, 0x24, random_value, "Interrupt mask mismatch")
    
    # Test case 4: Verify Write to address 0x28
    random_value = random.randint(0, (1 << DATA_WIDTH) - 1)
    await axi_write(dut, 0x28, random_value,strb)
    await check_output(dut, 0x28, random_value, f"Write to address 0x28 with value {random_value}")

    # Test case 4: Countdown functionality and interrupt generation
    for i in range(10):
        await RisingEdge(dut.axi_aclk)

    await axi_read(dut, 0x10)
    _elapsed = int(dut.axi_rdata.value)
    assert 1 <= _elapsed <= 20, f"Elapsed time mismatch: got {_elapsed}"
    # Test case 5: Additional register reads
    await test_additional_reads(dut)

    # Test case 6: IRQ output checking
    await test_irq_output(dut,DATA_WIDTH)

    # Corner case 2: Test random countdown values
    await test_random_countdown(dut,DATA_WIDTH)

    # Corner case 3: Test reset behavior
    await test_reset_behavior(dut)

    dut._log.info("All test cases, including corner cases, passed.")   