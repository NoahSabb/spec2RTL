import cocotb
from cocotb.triggers import Timer, RisingEdge
import random

# Constants for 640x480 VGA with 25 MHz clock
CLOCK_PERIOD_NS = 40
H_ACTIVE_PIXELS = 640
H_FRONT_PORCH = 16
H_SYNC_PULSE = 96
H_BACK_PORCH = 48

V_ACTIVE_LINES = 480
V_FRONT_PORCH = 10
V_SYNC_PULSE = 2
V_BACK_PORCH = 33

@cocotb.test()
async def test_vga_controller(dut):
    """VGA Controller Test with Phase Tracking, limited to 1 frame, with input stimulus."""

    # Start clock generator
    cocotb.start_soon(clock_gen(dut, CLOCK_PERIOD_NS))

    # Apply reset
    dut.reset.value = 1
    await Timer(100, unit="ns")
    dut.reset.value = 0
    dut._log.info("Reset released")

    # Initialize counters
    cycle_count = 0
    line_count = 0

    # Define input changes
    color_patterns = [
        0b11100011,  # Red high, blue high
        0b00011100,  # Green high
        0b11111111,  # White color
        0b00000000   # Black color
    ]

    # Apply a new color pattern at the start of the frame
    new_color = random.choice(color_patterns)
    dut.color_in.value = new_color
    dut._log.info(f"Color pattern applied at frame start: {bin(new_color)}")

    # Track exactly one complete frame
    while line_count < V_ACTIVE_LINES + V_FRONT_PORCH + V_SYNC_PULSE + V_BACK_PORCH:
        await RisingEdge(dut.clock)

        # Track Horizontal Phases
        if cycle_count == 0:
            dut._log.info("Horizontal Phase: Active Region started.")
        elif cycle_count == H_ACTIVE_PIXELS:
            dut._log.info("Horizontal Phase: Front Porch started.")
        elif cycle_count == H_ACTIVE_PIXELS + H_FRONT_PORCH:
            dut._log.info("Horizontal Phase: Sync Pulse started.")
        elif cycle_count == H_ACTIVE_PIXELS + H_FRONT_PORCH + H_SYNC_PULSE:
            dut._log.info("Horizontal Phase: Back Porch started.")

        # Check for end of horizontal line
        if cycle_count == H_ACTIVE_PIXELS + H_FRONT_PORCH + H_SYNC_PULSE + H_BACK_PORCH - 1:
            dut._log.info("Horizontal Line completed.")
            cycle_count = 0  # Reset cycle count for next line
            line_count += 1  # Increment line count

            # Track Vertical Phases
            if line_count == 0:
                dut._log.info("Vertical Phase: Active Region started.")
            elif line_count == V_ACTIVE_LINES:
                dut._log.info("Vertical Phase: Front Porch started.")
            elif line_count == V_ACTIVE_LINES + V_FRONT_PORCH:
                dut._log.info("Vertical Phase: Sync Pulse started.")
            elif line_count == V_ACTIVE_LINES + V_FRONT_PORCH + V_SYNC_PULSE:
                dut._log.info("Vertical Phase: Back Porch started.")

            # Check for end of frame
            if line_count == V_ACTIVE_LINES + V_FRONT_PORCH + V_SYNC_PULSE + V_BACK_PORCH:
                dut._log.info("One Vertical Frame completed.")
                break  # Stop after one frame

        else:
            # Increment horizontal cycle count
            cycle_count += 1

    # End the test successfully after 1 frame
    return  # test passed


async def clock_gen(dut, period_ns):
    """Clock generation"""
    while True:
        dut.clock.value = 0
        await Timer(period_ns / 2, unit="ns")
        dut.clock.value = 1
        await Timer(period_ns / 2, unit="ns")

