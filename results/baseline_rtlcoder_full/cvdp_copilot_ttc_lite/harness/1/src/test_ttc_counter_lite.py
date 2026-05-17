import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock
import harness_library as hrs_lb

@cocotb.test()
async def test_ttc_counter_lite(dut):
    """
    Cocotb-based testbench for the ttc_counter_lite module.
    """
    # Generate clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Initialize the DUT signals (e.g., reset all values to default 0)
    await hrs_lb.dut_init(dut)

    # Reset the DUT
    dut.reset.value = 1
    await Timer(20, unit="ns")
    dut.reset.value = 0
    await RisingEdge(dut.clk)

    # Helper function to write to AXI
    async def axi_write(addr, data):
        dut.axi_addr.value = addr
        dut.axi_wdata.value = data
        dut.axi_write_en.value = 1
        await RisingEdge(dut.clk)
        dut.axi_write_en.value = 0
        await RisingEdge(dut.clk)

    # Helper function to read from AXI
    async def axi_read(addr):
        dut.axi_addr.value = addr
        dut.axi_read_en.value = 1
        await RisingEdge(dut.clk)
        dut.axi_read_en.value = 0
        await RisingEdge(dut.clk)
        read_value = int(dut.axi_rdata.value)
        print(f"[READ] Address: {addr}, Data: {read_value}")
        return read_value

    # Write match value
    await axi_write(0x1, 0x14)  # Set match value to 20
    assert int(dut.match_value.value) == 0x14, "[ERROR] Match value not set correctly"
    dut._log.info(f"[CHECK] Match value correctly set: {int(dut.match_value.value)}")

    # Write reload value
    await axi_write(0x2, 0xA)  # Set reload value to 10
    assert int(dut.reload_value.value) == 0xA, "[ERROR] Reload value not set correctly"
    dut._log.info(f"[CHECK] Reload value correctly set: {int(dut.reload_value.value)}")

    # Configure control register
    await axi_write(0x3, 0x7)  # Enable = 1, Interval mode = 1, Interrupt enable = 1
    assert dut.enable.value == 1, "[ERROR] Control register enable not set"
    assert dut.interval_mode.value == 1, "[ERROR] Interval mode not set"
    assert dut.interrupt_enable.value == 1, "[ERROR] Interrupt enable not set"
    dut._log.info(f"[CHECK] Control register configured correctly: Enable={dut.enable.value}, Interval Mode={dut.interval_mode.value}, Interrupt Enable={dut.interrupt_enable.value}")

    # Observe counting
    await Timer(200, unit="ns")
    count = int(dut.count.value)
    reload_value = int(dut.reload_value.value)
    match_value = int(dut.match_value.value)
    assert reload_value <= count <= match_value, f"[ERROR] Counter value {count} is out of range [{reload_value}, {match_value}]"
    dut._log.info(f"[CHECK] Counter is running within range: {count}, Reload Value: {reload_value}, Match Value: {match_value}")

    # Read counter value
    count_val = await axi_read(0x0)  # Read counter value
    assert count_val == int(dut.count.value), f"[ERROR] Counter value mismatch: read {count_val}, expected {int(dut.count.value)}"
    dut._log.info(f"[INFO] Counter value read: {count_val}")

    # Wait for interrupt
    await Timer(50, unit="ns")
    assert dut.interrupt.value == 1, "[ERROR] Interrupt not asserted"
    dut._log.info(f"[CHECK] Interrupt asserted at match: {dut.interrupt.value}")
    # Check interrupt status
    interrupt_status = await axi_read(0x4)
    assert interrupt_status == dut.interrupt.value, "[ERROR] Interrupt status mismatch"
    dut._log.info("[CHECK] Interrupt status matches expected value")

    # Clear interrupt
    await axi_write(0x4, 0x0)  # Clear interrupt
    assert dut.interrupt.value == 0, "[ERROR] Interrupt not cleared"
    dut._log.info(f"[CHECK] Interrupt cleared successfully: {dut.interrupt.value}")

    dut._log.info("[INFO] Simulation completed")

