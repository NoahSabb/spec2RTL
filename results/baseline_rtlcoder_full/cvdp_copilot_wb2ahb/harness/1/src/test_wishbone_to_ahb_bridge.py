import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer
import harness_library as hrs_lb
@cocotb.test()
async def test_wishbone_to_ahb_bridge(dut):
    """Testbench for Wishbone-to-AHB Bridge"""

    # Clock generation
    cocotb.start_soon(Clock(dut.clk_i, 10, unit="ns").start())
    cocotb.start_soon(Clock(dut.hclk, 10, unit="ns").start())

    # Initialize inputs
    dut.rst_i.value = 1
    dut.cyc_i.value = 0
    dut.stb_i.value = 0
    dut.sel_i.value = 0b1111
    dut.we_i.value = 0
    dut.addr_i.value = 0
    dut.data_i.value = 0
    dut.hreset_n.value = 0
    dut.hrdata.value = 0
    dut.hresp.value = 0b00
    dut.hready.value = 1

    # Reset pulse
    await Timer(20, unit="ns")
    dut.rst_i.value = 0
    dut.hreset_n.value = 1
    await Timer(20, unit="ns")
    dut.rst_i.value = 1

    # Test 1: Write operation
    await RisingEdge(dut.clk_i)
    dut.cyc_i.value = 1
    dut.stb_i.value = 1
    dut.we_i.value = 1
    dut.addr_i.value = 0x10000000
    dut.data_i.value = 0xDEADBEEF

    await RisingEdge(dut.hclk)
    dut.hready.value = 0  # Simulate wait state
    await RisingEdge(dut.hclk)
    dut.hready.value = 1  # Simulate transfer completion

    # Check AHB outputs for write
    assert dut.hwrite.value == 1, f"ERROR: hwrite should be 1, got {dut.hwrite.value}"
    assert dut.haddr.value == 0x10000000, f"ERROR: haddr should be 0x10000000, got {hex(dut.haddr.value)}"
    assert dut.hwdata.value == 0xDEADBEEF, f"ERROR: hwdata should be 0xDEADBEEF, got {hex(dut.hwdata.value)}"
    dut._log.info(f"[CHECK] AHB outputs for write correctly set: dut.hwdata.value = {int(dut.hwdata.value)}, dut.hwrite.value = {int(dut.hwrite.value)}, dut.haddr.value = {int(dut.haddr.value)}")

    cocotb.log.info("PASS: Write operation successful")

    await RisingEdge(dut.clk_i)
    dut.stb_i.value = 0
    dut.cyc_i.value = 0

    # Test 2: Read operation
    await RisingEdge(dut.clk_i)
    dut.cyc_i.value = 1
    dut.stb_i.value = 1
    dut.we_i.value = 0
    dut.addr_i.value = 0x20000000
    dut.hrdata.value = 0xCAFEBABE  # AHB slave data

    await RisingEdge(dut.hclk)
    dut.hready.value = 0  # Simulate wait state
    await RisingEdge(dut.hclk)
    dut.hready.value = 1  # Simulate transfer completion

    # Check Wishbone outputs for read
    assert dut.data_o.value == 0xCAFEBABE, f"ERROR: data_o should be 0xCAFEBABE, got {hex(dut.data_o.value)}"
    dut._log.info(f"[CHECK] Wishbone outputs for read correctly set: dut.data_o.value = {int(dut.data_o.value)}")

    cocotb.log.info("PASS: Read operation successful")

    await RisingEdge(dut.clk_i)
    dut.stb_i.value = 0
    dut.cyc_i.value = 0

    cocotb.log.info("Test complete")
