import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from cocotb.clock import Clock

# -----------------------------------------------------------------------------
# Helper assertion
# -----------------------------------------------------------------------------
def assert_equal(actual, expected, msg=""):
    """Custom assertion with an optional message."""
    assert actual == expected, f"{msg}: Expected {hex(expected)}, got {hex(actual)}"

# -----------------------------------------------------------------------------
# APB Read/Write Helpers
# -----------------------------------------------------------------------------
async def apb_write(dut, addr, data):
    """Perform a single APB write transaction: Setup + Access phase."""
    # Setup phase
    dut.pselx.value = 1
    dut.pwrite.value = 1
    dut.paddr.value  = addr
    dut.pwdata.value = data
    dut.penable.value = 0
    await RisingEdge(dut.pclk)

    # Access phase
    dut.penable.value = 1
    await RisingEdge(dut.pclk)

    # De-assert
    dut.pselx.value   = 0
    dut.penable.value = 0
    dut.pwrite.value  = 0
    dut.paddr.value   = 0
    dut.pwdata.value  = 0
    await RisingEdge(dut.pclk)

async def apb_read(dut, addr):
    """Perform a single APB read transaction: Setup + Access phase. Returns the read data."""
    # Setup phase
    dut.pselx.value   = 1
    dut.pwrite.value  = 0
    dut.paddr.value   = addr
    dut.penable.value = 0
    await RisingEdge(dut.pclk)

    # Access phase
    dut.penable.value = 1
    await RisingEdge(dut.pclk)
    await Timer(1, unit="ns")  # small delay to allow prdata to settle
    read_data = int(dut.prdata.value)

    # De-assert
    dut.pselx.value   = 0
    dut.penable.value = 0
    dut.paddr.value   = 0
    await RisingEdge(dut.pclk)
    return read_data

# -----------------------------------------------------------------------------
# Actual Test
# -----------------------------------------------------------------------------
@cocotb.test()
async def test_APBGlobalHistoryRegister(dut):
    """Cocotb testbench for APBGlobalHistoryRegister."""

    # Create and start a clock on pclk
    clock = Clock(dut.pclk, 10, unit="ns")  # 100 MHz
    cocotb.start_soon(clock.start())

    # Initialize inputs
    dut.pselx.value   = 0
    dut.penable.value = 0
    dut.pwrite.value  = 0
    dut.pwdata.value  = 0
    dut.paddr.value   = 0
    dut.presetn.value = 1
    dut.history_shift_valid.value = 0
    dut.clk_gate_en.value = 0   # clock gating disabled by default

    # Apply asynchronous reset
    dut.presetn.value = 0
    await Timer(20, unit="ns")  # hold reset low
    dut.presetn.value = 1
    await RisingEdge(dut.pclk)
    await RisingEdge(dut.pclk)

    #--------------------------------------------------------------------------
    # Local constants (addresses)
    # Match these to localparams in RTL if needed
    #--------------------------------------------------------------------------
    ADDR_CTRL_REG     = 0x0
    ADDR_TRAIN_HIS    = 0x1
    ADDR_PREDICT_HIS  = 0x2

    #--------------------------------------------------------------------------
    # 1) Check reset behavior
    #--------------------------------------------------------------------------
    ctrl_reg_val   = await apb_read(dut, ADDR_CTRL_REG)
    train_his_val  = await apb_read(dut, ADDR_TRAIN_HIS)
    predict_his_val= await apb_read(dut, ADDR_PREDICT_HIS)
    await Timer(1, unit="ns")
    assert_equal(ctrl_reg_val,   0x00, "control_register not reset to 0")
    assert_equal(train_his_val,  0x00, "train_history not reset to 0")
    assert_equal(predict_his_val,0x00, "predict_history not reset to 0")

    # Confirm status signals are reset
    assert dut.history_empty.value == 1, "history_empty should be 1 after reset"
    assert dut.history_full.value  == 0, "history_full should be 0 after reset"
    assert dut.interrupt_full.value == 0, "interrupt_full should be 0 after reset"
    assert dut.interrupt_error.value == 0, "interrupt_error should be 0 after reset"

    #--------------------------------------------------------------------------
    # 2) Basic APB Write/Read to control_register
    #--------------------------------------------------------------------------
    # We only use bits [3:0].
    # Bits: predict_valid=1 (LSB), predict_taken=1, train_mispredicted=0, train_taken=1 => 0b1011 = 0x0B
    await apb_write(dut, ADDR_CTRL_REG, 0x0B)
    await Timer(1, unit="ns")
    ctrl_reg_val = await apb_read(dut, ADDR_CTRL_REG)
    await Timer(1, unit="ns")
    # Check only lower 4 bits
    assert_equal(ctrl_reg_val & 0x0F, 0x0B, "control_register readback mismatch")

    #--------------------------------------------------------------------------
    # 3) Basic APB Write/Read to train_history
    #--------------------------------------------------------------------------
    # Bits [6:0] used, bit[7] reserved => if we write 0xAA => that is 10101010 in binary
    # The upper bit [7] is reserved => should read back as 0 => resulting in 0x2A in decimal = 0b0101010
    await apb_write(dut, ADDR_TRAIN_HIS, 0xAA)
    train_his_val = await apb_read(dut, ADDR_TRAIN_HIS)
    # train_his_val[7] should be 0 => so we expect 0x2A if the 7 bits are 1010101 = 0x55 >> but let's see:
    #  0xAA = 10101010 => the top bit is 1 (bit7). That is reserved => read as 0 => real stored bits = 0x2A
    await Timer(1, unit="ns")
    assert_equal(train_his_val, 0x2A, "train_history readback mismatch on reserved bit")

    #--------------------------------------------------------------------------
    # 4) Read predict_history (should still be 0)
    #--------------------------------------------------------------------------
    predict_his_val = await apb_read(dut, ADDR_PREDICT_HIS)
    assert_equal(predict_his_val, 0x00, "predict_history not expected zero before any shifts")

    #--------------------------------------------------------------------------
    # 5) Check error handling (invalid address => PSLVERR => interrupt_error)
    #--------------------------------------------------------------------------
    # Write to an invalid address, e.g., 0x3 or 0x100
    await apb_write(dut, 0x3, 0x55)  # outside valid range 0x0..0x2
    await Timer(1, unit="ns")
    # Wait a cycle to see the effect
    await RisingEdge(dut.pclk)

    # PSLVERR => pslverr, error_flag, interrupt_error should be asserted
    assert dut.pslverr.value == 1, "pslverr not asserted on invalid address"
    assert dut.error_flag.value == 1, "error_flag not asserted on invalid address"
    assert dut.interrupt_error.value == 1, "interrupt_error not asserted on invalid address"

    #--------------------------------------------------------------------------
    # Clear the error by writing a valid address
    # (The design automatically clears PSLVERR next cycle when paddr is valid)
    #--------------------------------------------------------------------------
    await apb_write(dut, ADDR_CTRL_REG, 0x00)
    await Timer(1, unit="ns")
    assert dut.pslverr.value == 0, "pslverr should be cleared after valid transaction"
    assert dut.error_flag.value == 0, "error_flag should be cleared"
    assert dut.interrupt_error.value == 0, "interrupt_error should be cleared"

    #--------------------------------------------------------------------------
    # 6) Test normal shift update on rising edge of history_shift_valid
    #--------------------------------------------------------------------------
    # Let's set control_register => predict_valid=1 (bit0=1), predict_taken=1 (bit1=1)
    await apb_write(dut, ADDR_CTRL_REG, 0x03)  # 0b0011 => mispredict=0, train_taken=0
    await Timer(2, unit="ns")

    # Toggle history_shift_valid
    dut.history_shift_valid.value = 1
    await Timer(2, unit="ns")  # rising edge
    dut.history_shift_valid.value = 0

    # Wait a bit so the GHSR can update (as it's asynchronous).
    await Timer(5, unit="ns")

    # Check updated predict_history
    #   old=0x00 => shift in '1' => LSB=1 => new=0x01
    predict_his_val = await apb_read(dut, ADDR_PREDICT_HIS)
    assert_equal(predict_his_val, 0x01, "predict_history should shift in bit=1 at LSB")

    #--------------------------------------------------------------------------
    # 7) Shift repeatedly to fill up to 0xFF => check history_full and interrupt_full
    #--------------------------------------------------------------------------
    # We'll keep predict_valid=1, predict_taken=1 => each rising edge of history_shift_valid sets LSB=1
    # So repeated shifts should eventually get 0xFF after enough toggles.
    for _ in range(7):
        dut.history_shift_valid.value = 1
        await Timer(2, unit="ns")
        dut.history_shift_valid.value = 0
        await Timer(5, unit="ns")

    predict_his_val = await apb_read(dut, ADDR_PREDICT_HIS)
    assert_equal(predict_his_val, 0xFF, "predict_history not 0xFF after 8 consecutive bits=1")

    assert dut.history_full.value == 1, "history_full should be asserted at 0xFF"
    assert dut.interrupt_full.value == 1, "interrupt_full should be asserted at 0xFF"
    assert dut.history_empty.value == 0, "history_empty should not be set at 0xFF"

    #--------------------------------------------------------------------------
    # 8) Test misprediction handling
    #--------------------------------------------------------------------------
    # Suppose we wrote train_history=0x55 earlier. Let's re-write it to confirm.
    # For example, 0x55 => 0101_0101 => only bits [6:0] are used => 0x55 => 1010101 => plus bit7=0
    await apb_write(dut, ADDR_TRAIN_HIS, 0x55)  # store 0x55 => which effectively 0x55 & 0x7F
    # Then set train_mispredicted=1, train_taken=1 => bits => 0b1100 => predict_valid=0, predict_taken=0
    await apb_write(dut, ADDR_CTRL_REG, 0x0C)
    await Timer(2, unit="ns")

    # Toggle shift valid => misprediction should have highest priority
    dut.history_shift_valid.value = 1
    await Timer(2, unit="ns")
    dut.history_shift_valid.value = 0
    await Timer(5, unit="ns")

    # The GHSR should be restored from train_history[6:0] => which is 0x55 & 0x7F = 0x55 => plus train_taken=1 => => new GHSR=0xAB
    # Explanation: train_history = 0x55 => 0b0101_0101 => ignoring bit7 => it's effectively 1010101 in bits [6:0]
    # => {train_history[6:0], train_taken} => {0x55, 1} => 0x55 << 1 + 1 => 0xAA + 0x01 = 0xAB
    predict_his_val = await apb_read(dut, ADDR_PREDICT_HIS)
    assert_equal(predict_his_val, 0xAB, "predict_history not restored properly on misprediction")

    # Check if full/empty changed
    assert dut.history_full.value == 0, "history_full incorrectly asserted after misprediction restore"
    assert dut.history_empty.value == 0, "history_empty incorrectly asserted after misprediction restore"
    assert dut.interrupt_full.value == 0, "interrupt_full incorrectly asserted"

    #--------------------------------------------------------------------------
    # 9) Priority check: If predict_valid=1 and train_mispredicted=1 together => misprediction wins
    #--------------------------------------------------------------------------
    # Make control_register => predict_valid=1, predict_taken=1, train_mispredicted=1, train_taken=0 => 0b0111 => 0x07
    # So if both are set, we should do the misprediction path.
    # Let's re-store train_history=0x22 => 0b0010_0010 => ignoring bit7 => actually 0x22 => bits [6:0]=0x22
    await apb_write(dut, ADDR_TRAIN_HIS, 0x22)
    await apb_write(dut, ADDR_CTRL_REG, 0x07)
    await Timer(2, unit="ns")

    # Trigger shift
    dut.history_shift_valid.value = 1
    await Timer(2, unit="ns")
    dut.history_shift_valid.value = 0
    await Timer(5, unit="ns")

    # We expect => predict_history = {train_history[6:0], train_taken} => 0x22 << 1 + 0 => 0x44
    # 0x22 => 0010_0010 => ignoring bit7 => it's 0x22 in [6:0]
    # appended train_taken=0 => => 0x44 in decimal
    predict_his_val = await apb_read(dut, ADDR_PREDICT_HIS)
    await Timer(1, unit="ns")
    assert_equal(predict_his_val, 0x44,
                 "Priority fail: misprediction did not override normal predict_valid=1 condition")

    #--------------------------------------------------------------------------
    # 10) Drive predict_history back to 0x00 => check empty/interrupt
    #--------------------------------------------------------------------------
    # We'll do this by writing a misprediction to restore 7 bits=0, plus train_taken=0
    await apb_write(dut, ADDR_TRAIN_HIS, 0x00)
    # train_mispredicted=1, train_taken=0 => 0b0100 => plus predict_valid=0 => 0x04
    await apb_write(dut, ADDR_CTRL_REG, 0x04)
    dut.history_shift_valid.value = 1
    await Timer(2, unit="ns")
    dut.history_shift_valid.value = 0
    await Timer(5, unit="ns")

    predict_his_val = await apb_read(dut, ADDR_PREDICT_HIS)
    assert_equal(predict_his_val, 0x00, "predict_history not reset to 0 via misprediction restore")

    assert dut.history_empty.value == 1, "history_empty not asserted at 0x00"
    assert dut.history_full.value  == 0, "history_full incorrectly asserted at 0x00"

    #--------------------------------------------------------------------------
    # 11) Simple clock gating check
    #--------------------------------------------------------------------------
    # Toggle clk_gate_en => This will effectively 'stop' pclk_gated in the RTL,
    # meaning no register updates. We'll do an APB write, then verify it didn't change.
    dut.clk_gate_en.value = 1
    await RisingEdge(dut.pclk)

    # Attempt to write to ctrl_reg => should NOT update if gating is truly working
    await apb_write(dut, ADDR_CTRL_REG, 0x0F)
    # Read it back
    await FallingEdge(dut.pclk)
    dut.clk_gate_en.value = 0
    reg_val = await apb_read(dut, ADDR_CTRL_REG)
    # Because gating is conceptual in RTL, some synthesis flows might not simulate gating literally,
    # but let's assume it does. If gating is real, the design's internal pclk is off, so no update => remains 0x04
    # (the last value we wrote was 0x04).
    # NOTE: The actual behavior depends on your gate logic. If your gating is purely structural,
    # we might see 0x0F or 0x04. Adjust expectations accordingly.

    # For a realistic test, let's expect no update:
    expected_val = 0x04  
    assert_equal(reg_val, expected_val,
                 "control_register changed despite clock gating")

    # Turn gating back off
    dut.clk_gate_en.value = 0
    await RisingEdge(dut.pclk)
    await RisingEdge(dut.pclk)

    # Write again => now it should succeed
    await apb_write(dut, ADDR_CTRL_REG, 0x0F)
    reg_val = await apb_read(dut, ADDR_CTRL_REG)
    assert_equal(reg_val & 0x0F, 0x0F, "control_register not updated when gating disabled")

    dut._log.info("All APBGlobalHistoryRegister tests completed successfully.")

