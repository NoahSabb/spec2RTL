import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock

def assert_equal(actual, expected, msg=""):
    """Custom assertion with message."""
    assert actual == expected, f"{msg}: Expected {expected}, but got {actual}"

# Helper function to perform an APB write
async def apb_write(dut, addr, data):
    """Perform a single APB write transaction: Setup + Access phase."""
    # Setup phase
    dut.pselx.value = 1
    dut.pwrite.value = 1
    dut.paddr.value = addr
    dut.pwdata.value = data
    dut.penable.value = 0
    await RisingEdge(dut.pclk)

    # Access phase
    dut.penable.value = 1
    await RisingEdge(dut.pclk)

    # De-assert
    dut.pselx.value = 0
    dut.penable.value = 0
    dut.pwrite.value = 0
    dut.paddr.value = 0
    dut.pwdata.value = 0
    await RisingEdge(dut.pclk)

# Helper function to perform an APB read
async def apb_read(dut, addr):
    """Perform a single APB read transaction: Setup + Access phase. Returns the read data."""
    # Setup phase
    dut.pselx.value = 1
    dut.pwrite.value = 0
    dut.paddr.value = addr
    dut.penable.value = 0
    await RisingEdge(dut.pclk)

    # Access phase
    dut.penable.value = 1
    await RisingEdge(dut.pclk)
    await Timer(1, unit="ns")
    read_data = int(dut.prdata.value)

    # De-assert
    dut.pselx.value = 0
    dut.penable.value = 0
    dut.paddr.value = 0
    await RisingEdge(dut.pclk)

    return read_data

@cocotb.test()
async def test_apb_dsp_unit(dut):
    """Testbench for the APB DSP Unit."""

    # Create a clock
    clock = Clock(dut.pclk, 10, unit="ns")  # 100 MHz
    cocotb.start_soon(clock.start())

    # Initially drive inputs to known values
    dut.pselx.value = 0
    dut.penable.value = 0
    dut.pwrite.value = 0
    dut.pwdata.value = 0
    dut.paddr.value = 0
    dut.presetn.value = 1

    # Apply asynchronous reset
    dut.presetn.value = 0
    await Timer(20, unit="ns")  # hold reset low
    dut.presetn.value = 1
    await RisingEdge(dut.pclk)
    await RisingEdge(dut.pclk)

    #--------------------------------------------------------------------------
    # Constants / Addresses (matching localparams in RTL)
    #--------------------------------------------------------------------------
    ADDR_OPERAND1   = 0x0
    ADDR_OPERAND2   = 0x1
    ADDR_ENABLE     = 0x2
    ADDR_WRITE_ADDR = 0x3
    ADDR_WRITE_DATA = 0x4
    ADDR_RESULT     = 0x5

    MODE_DISABLED   = 0x0
    MODE_ADD        = 0x1
    MODE_MULT       = 0x2
    MODE_WRITE      = 0x3

    #--------------------------------------------------------------------------
    # 1. Check Reset Values
    #--------------------------------------------------------------------------
    # The RTL should have reset all registers to 0. Let's confirm.
    op1 = await apb_read(dut, ADDR_OPERAND1)
    assert_equal(op1, 0, "After reset, r_operand_1 should be 0")

    op2 = await apb_read(dut, ADDR_OPERAND2)
    assert_equal(op2, 0, "After reset, r_operand_2 should be 0")

    enable = await apb_read(dut, ADDR_ENABLE)
    assert_equal(enable, 0, "After reset, r_enable should be 0")

    write_addr = await apb_read(dut, ADDR_WRITE_ADDR)
    assert_equal(write_addr, 0, "After reset, r_write_address should be 0")

    write_data = await apb_read(dut, ADDR_WRITE_DATA)
    assert_equal(write_data, 0, "After reset, r_write_data should be 0")

    #--------------------------------------------------------------------------
    # 2. Write Mode Test
    #--------------------------------------------------------------------------
    # We'll write a value into memory (e.g., at address 100).
    TEST_MEM_ADDR = 100
    TEST_MEM_DATA = 0x55
    dut.sram_valid.value = 0
    # Set up the DSP for write mode
    await apb_write(dut, ADDR_ENABLE, MODE_WRITE)        # r_enable = 3
    await apb_write(dut, ADDR_WRITE_ADDR, TEST_MEM_ADDR) # r_write_address = 100
    await apb_write(dut, ADDR_WRITE_DATA, TEST_MEM_DATA) # r_write_data = 0x55

    # Now read back the memory at address 100 to confirm
    dut.sram_valid.value = 1
    await Timer(10, unit="ns")
    dut.sram_valid.value = 0

    read_val = await apb_read(dut, TEST_MEM_ADDR)
    assert_equal(read_val, TEST_MEM_DATA, f"Memory at address {TEST_MEM_ADDR} should hold 0x55")

    #--------------------------------------------------------------------------
    # 3. Addition Mode Test
    #--------------------------------------------------------------------------
    # Let's store two different values in memory for addition. We'll use addresses 10 and 11.
    await apb_write(dut, ADDR_WRITE_ADDR, 10)   # memory[10] = 0xA0
    await apb_write(dut, ADDR_WRITE_DATA, 0xA0)
    dut.sram_valid.value = 1
    await Timer(10, unit="ns")
    dut.sram_valid.value = 0
    await apb_write(dut, ADDR_WRITE_ADDR, 11)   # memory[11] = 0x05
    await apb_write(dut, ADDR_WRITE_DATA, 0x05)
    dut.sram_valid.value = 1
    await Timer(10, unit="ns")
    dut.sram_valid.value = 0

    # Switch to addition mode
    await apb_write(dut, ADDR_ENABLE, MODE_ADD)
    # Set the operand addresses
    await apb_write(dut, ADDR_OPERAND1, 10)  # r_operand_1 = 10
    await apb_write(dut, ADDR_OPERAND2, 11)  # r_operand_2 = 11

    # Wait a cycle or two to let the DSP perform the operation
    await RisingEdge(dut.pclk)
    await RisingEdge(dut.pclk)

    # Read the result from address 0x5
    result_val = await apb_read(dut, ADDR_RESULT)
    expected_sum = 0xA0 + 0x05
    assert_equal(result_val, expected_sum & 0xFF,
                 "Addition result should be 0xA5 (lowest 8 bits if overflow)")

    #--------------------------------------------------------------------------
    # 4. Multiplication Mode Test
    #--------------------------------------------------------------------------
    # Let's store two different values in memory for multiplication. We'll reuse addresses 10 and 11.
    await apb_write(dut, ADDR_ENABLE, MODE_WRITE)        # r_enable = 3
    await apb_write(dut, ADDR_WRITE_ADDR, 10)   # memory[10] = 0x02
    await apb_write(dut, ADDR_WRITE_DATA, 0x02)
    dut.sram_valid.value = 1
    await Timer(10, unit="ns")
    dut.sram_valid.value = 0
    await apb_write(dut, ADDR_WRITE_ADDR, 11)   # memory[11] = 0x03
    await apb_write(dut, ADDR_WRITE_DATA, 0x03)
    dut.sram_valid.value = 1
    await Timer(10, unit="ns")
    dut.sram_valid.value = 0

    # Switch to multiplication mode
    await apb_write(dut, ADDR_ENABLE, MODE_MULT)

    # Operands remain 10 and 11
    await RisingEdge(dut.pclk)
    await RisingEdge(dut.pclk)

    # Read the result
    result_val = await apb_read(dut, ADDR_RESULT)
    expected_mult = 0x02 * 0x03
    assert_equal(result_val, expected_mult & 0xFF,
                 "Multiplication result should be 6")

    
    #--------------------------------------------------------------------------
    # 6. Conclusion
    #--------------------------------------------------------------------------
    dut._log.info("APB DSP Unit test completed successfully.")
