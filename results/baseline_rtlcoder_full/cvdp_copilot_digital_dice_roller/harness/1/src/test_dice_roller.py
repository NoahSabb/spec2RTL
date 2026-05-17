
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer
import random

async def reset_dut(dut):
    """Assert the active-low reset signal and release it."""
    dut.reset.value = 0  # Assert reset (active-low)
    await Timer(20, unit="ns")  # Hold reset for 20ns
    dut.reset.value = 1  # Release reset
    await Timer(10, unit="ns")  # Wait for reset release

async def dice_roll_test(dut):
    """Parameterized test for the digital dice roller using DICE_MAX from the RTL design."""

    # Get the maximum dice value directly from the design
    DICE_MAX = int(dut.DICE_MAX.value)

    # Initialize signals
    dut.button.value = 0
    await reset_dut(dut)  # Apply reset at the beginning

    # Test case 1: Normal operation - Button press and release to roll dice
    press_duration = 10  # Duration in mili seconds
    dut._log.info(f"Test Case 1: long Button press, press duration = {press_duration} ms")
    dut.button.value = 1  # Press the button to start rolling
    await Timer(press_duration, unit="ms")  # Hold the button for 10 mili seconds to simulate rolling

    dut.button.value = 0  # Release the button to stop rolling
    await Timer(50, unit="ns")  # Wait for dice to stop

    # Check if dice_value is within valid range
    dice_value = int(dut.dice_value.value)
    assert 1 <= dice_value <= DICE_MAX, f"FAIL: Dice stopped at invalid value: {dice_value}"
    dut._log.info(f"PASS: Dice stopped at valid value: {dice_value} after {press_duration} ms press")

    # Test case 2: Short button press
    press_duration = 10  # Duration in microseconds
    dut._log.info(f"Test Case 2: Short button press, press duration = {press_duration} us")
    dut.button.value = 1  # Press the button to start rolling
    await Timer(press_duration, unit="us")  # Hold the button for a short time

    dut.button.value = 0  # Release the button to stop rolling
    await Timer(50, unit="ns")  # Wait for dice to stop

    # Check if dice_value is within valid range
    dice_value = int(dut.dice_value.value)
    assert 1 <= dice_value <= DICE_MAX, f"FAIL: Dice stopped at invalid value: {dice_value}"
    dut._log.info(f"PASS: Dice stopped at valid value: {dice_value} after {press_duration} us press")

    # Test case 3: Long button press
    press_duration = 200  # Duration in ns
    dut._log.info(f"Test Case 3: Long button press, press duration = {press_duration} ns")
    dut.button.value = 1  # Press the button to start rolling
    await Timer(press_duration, unit="ns")  # Hold the button for a long time

    dut.button.value = 0  # Release the button to stop rolling
    await Timer(50, unit="ns")  # Wait for dice to stop

    # Check if dice_value is within valid range
    dice_value = int(dut.dice_value.value)
    assert 1 <= dice_value <= DICE_MAX, f"FAIL: Dice stopped at invalid value: {dice_value}"
    dut._log.info(f"PASS: Dice stopped at valid value: {dice_value} after {press_duration} ns press")

    # Test case 4: Random button press durations
    for i in range(5):
        press_duration = random.randint(50, 150)  # Random press duration between 50ns and 150ns
        dut._log.info(f"Test Case 4.{i+1}: Random button press, press duration = {press_duration} ns")

        dut.button.value = 1  # Press the button to start rolling
        await Timer(press_duration, unit="ns")  # Hold the button for a random duration

        dut.button.value = 0  # Release the button to stop rolling
        await Timer(50, unit="ns")  # Wait for dice to stop

        # Check if dice_value is within valid range
        dice_value = int(dut.dice_value.value)
        assert 1 <= dice_value <= DICE_MAX, f"FAIL: Dice stopped at invalid value: {dice_value}"
        dut._log.info(f"PASS: Dice stopped at valid value: {dice_value} after {press_duration} ns press")

@cocotb.test()
async def test_dice_roller(dut):
    """Main test for the digital dice roller, using parameterized DICE_MAX from RTL design."""
    # Start the clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await dice_roll_test(dut)

@cocotb.test()
async def test_reset_functionality(dut):
    """Test the reset functionality of the dice roller."""
    # Start the clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    
    # Reset the DUT and check if it resets correctly
    dut._log.info("Test Case 5: Reset functionality")
    await reset_dut(dut)

    # Check that dice_value is reset to 1 after reset
    dice_value = int(dut.dice_value.value)
    assert dice_value == 1, f"FAIL: Dice value did not reset correctly, found: {dice_value}"
    dut._log.info("PASS: Dice value reset correctly to 1 after reset")

    # Test reset during rolling
    dut._log.info("Test Case 6: Asserting reset during rolling")
    dut.button.value = 1  # Press button to start rolling
    await Timer(50, unit="ns")  # Start rolling

    dut.reset.value = 0  # Assert reset (active-low) during roll
    await Timer(20, unit="ns")  # Hold reset for 20ns
    dut.reset.value = 1  # Release reset

    # Check that dice_value is reset to 1 after reset
    dice_value = int(dut.dice_value.value)
    assert dice_value == 1, f"FAIL: Dice value did not reset correctly during rolling, found: {dice_value}"
    dut._log.info("PASS: Dice value reset correctly to 1 during rolling after reset")

@cocotb.test()
async def test_hold_reset_low(dut):
    """Test holding reset low to verify dice_value stays reset."""
    # Start the clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Hold reset low
    dut.reset.value = 0  # Assert reset (active-low)
    dut._log.info("Test Case 7: Holding reset low to verify dice_value stays reset")

    # Wait for a period to verify dice_value remains reset
    await Timer(100, unit="ns")  # Hold reset for 100ns

    # Check that dice_value remains at 1 while reset is low
    dice_value = int(dut.dice_value.value)
    assert dice_value == 1, f"FAIL: Dice value did not remain reset, found: {dice_value}"
    dut._log.info("PASS: Dice value remained at 1 while reset was held low")

    # Release reset
    dut.reset.value = 1
