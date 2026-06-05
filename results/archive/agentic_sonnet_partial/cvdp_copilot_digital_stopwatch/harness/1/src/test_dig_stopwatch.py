import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge,FallingEdge, Timer
import random

import harness_library as hrs_lb

async def wait_for_seconds(dut, num_seconds):
    # Wait for a specified number of seconds.
    for _ in range(num_seconds):
        await RisingEdge(dut.one_sec_pulse)
        print(f"Current Time - Hours: {int(dut.hour.value)}, Minutes: {int(dut.minutes.value)}, Seconds: {int(dut.seconds.value)}")

async def check_rollover_conditions(dut, num_seconds):
    # Check the rollover of seconds, minutes, and hours.
    for _ in range(num_seconds):
        await RisingEdge(dut.one_sec_pulse)
        print(f"Rollover Current Time - Hour: {int(dut.hour.value)}, Minutes: {int(dut.minutes.value)}, Seconds: {int(dut.seconds.value)}")

        # Check for seconds rollover
        if int(dut.seconds.value) == 59 and int(dut.minutes.value) < 59:
            await RisingEdge(dut.clk)
            assert int(dut.seconds.value) == 0, "Error: Seconds did not reset to 0 after reaching 59."
            assert int(dut.minutes.value) > 0, "Error: Minutes did not increment after seconds rollover."

        # Check for minutes rollover
        if int(dut.minutes.value) == 59 and int(dut.seconds.value) == 59:
            await RisingEdge(dut.clk)
            assert int(dut.seconds.value) == 0, "Error: Seconds did not reset to 0 after reaching 59."
            assert int(dut.minutes.value) == 0, "Error: Minutes did not reset to 0 after reaching 59."
            assert int(dut.hour.value) == 1, "Error: Hour did not increment after minutes rollover."

        # Check for hours rollover from max value back to zero
        if int(dut.hour.value) == 1 and int(dut.minutes.value) == 0 and int(dut.seconds.value) == 0 and dut.start_stop.value:
            await RisingEdge(dut.clk)
            assert int(dut.hour.value) == 1, "Error: Hour did not reset to 0 after reaching 1."
            assert int(dut.minutes.value) == 0 and int(dut.seconds.value) == 0, "Minutes and seconds did not reset to 0 at hour rollover."

async def check_pause_and_resume(dut):
    # Test that the stopwatch pauses and resumes correctly.
    dut.start_stop.value = 1
    await wait_for_seconds(dut, 10)
    
    # Pause the stopwatch
    dut.start_stop.value = 0
    await RisingEdge(dut.clk)
    
    paused_seconds = int(dut.seconds.value)
    for _ in range(20):
        await RisingEdge(dut.clk)
    
    
    # Wait to ensure the stopwatch remains paused
    await RisingEdge(dut.clk)  # Instead of Timer, ensure clock cycle sync
    assert int(dut.seconds.value) == paused_seconds, "Error: Stopwatch did not pause correctly."

    # Resume the stopwatch and check it continues counting from the same value
    dut.start_stop.value = 1
    await wait_for_seconds(dut, 20)
    assert int(dut.seconds.value) == paused_seconds + 19, "Error: Stopwatch did not resume correctly."

async def pause_at_random_second(dut):
    dut.start_stop.value = 1
    tb_counter = 0  
    clk_freq = int(dut.CLK_FREQ.value)
    counter_max = clk_freq - 1 

    # Generate a random number of clock cycles to count before pausing
    random_pause_duration = random.randint(1, counter_max - 1)

    # Run until reaching the random_pause_duration and keep track with tb_counter
    for _ in range(random_pause_duration):
        await RisingEdge(dut.clk)
        tb_counter += 1

    # Pause the stopwatch
    dut.start_stop.value = 0
    await RisingEdge(dut.clk)
    paused_seconds = int(dut.seconds.value)

    # Ensure the stopwatch remains paused by monitoring tb_counter and checking the seconds in the DUT
    for _ in range(100):
        await RisingEdge(dut.clk)
        assert int(dut.seconds.value) == paused_seconds, "Error: Stopwatch did not remain paused as expected."

    # Resume the stopwatch and continue tracking
    await RisingEdge(dut.clk)
    dut.start_stop.value = 1

    remaining_ticks = counter_max - tb_counter  # Calculate the remaining ticks to reach one second
    for _ in range((remaining_ticks + 1)):
         await RisingEdge(dut.clk)

    # Verify stopwatch has advanced after the remaining ticks complete
    await RisingEdge(dut.clk)
    assert int(dut.seconds.value) == paused_seconds + 1, f"Stopwatch did not resume correctly from paused second. Expected: {paused_seconds + 1}, Got: {dut.seconds.value}"

async def pause_at_random_minute(dut):

    dut.start_stop.value = 1
    await wait_for_seconds(dut, 50)

    # Pause the stopwatch
    dut.start_stop.value = 0
    await RisingEdge(dut.clk)
    paused_minutes = 0

    # Ensure the stopwatch remains paused
    for _ in range(3600):
        await RisingEdge(dut.clk)
        assert int(dut.minutes.value) == paused_minutes, "Error: Stopwatch did not remain paused as expected."

    # Resume the stopwatch and allow remaining ticks to complete a full minutes
    dut.start_stop.value = 1
    await wait_for_seconds(dut, 10)

    # Confirm the stopwatch has moved to the next minute after resuming
    await RisingEdge(dut.clk)
    expected_minutes = paused_minutes + 1
    assert int(dut.minutes.value) == expected_minutes, f"Stopwatch did not resume correctly from paused minute. Expected: {expected_minutes}, Got: {dut.minutes.value}"

@cocotb.test()
async def test_dig_stopwatch(dut):
    clk_freq = int(dut.CLK_FREQ.value)

    PERIOD = int(1_000_000_000 / clk_freq)  # Calculate clock period in ns
    cocotb.start_soon(Clock(dut.clk, PERIOD // 2, unit='ns', period_high=(PERIOD // 2+1)//2).start())
    
    await hrs_lb.dut_init(dut)
    await hrs_lb.reset_dut(dut.reset, duration_ns=PERIOD, active=False)

    assert dut.seconds.value == 0, f"Initial seconds is not 0! Got: {dut.seconds.value}"
    assert dut.minutes.value == 0, f"Initial minutes is not 0! Got: {dut.minutes.value}"
    assert dut.hour.value == 0, f"Initial hours is not 0! Got: {dut.hour.value}"

    await RisingEdge(dut.clk)

    # Start the stopwatch
    dut.start_stop.value = 1
    await RisingEdge(dut.clk)

    initial_seconds = int(dut.seconds.value)
    await wait_for_seconds(dut, 10)
    assert int(dut.seconds.value) == initial_seconds + 9, f"Seconds did not increment correctly. Current seconds: {dut.seconds.value}"

    # Stop the stopwatch  
    dut.start_stop.value = 0
    await RisingEdge(dut.clk)
    stopped_seconds = int(dut.seconds.value)

    await RisingEdge(dut.clk)
    assert int(dut.seconds.value) == stopped_seconds, "Stopwatch did not stop as expected."

    # Start the stopwatch again
    dut.start_stop.value = 1
    await RisingEdge(dut.clk)

    await check_pause_and_resume(dut)

    await check_rollover_conditions(dut, 3600)  # Testing rollovers for 1 hour
    
    dut.start_stop.value = 0

    dut.reset.value = 1
    await RisingEdge(dut.clk)

    assert dut.seconds.value == 0, f"Reset failed for seconds! Got: {dut.seconds.value}"
    assert dut.minutes.value == 0, f"Reset failed for minutes! Got: {dut.minutes.value}"
    assert dut.hour.value == 0, f"Reset failed for hours! Got: {dut.hour.value}"
    await RisingEdge(dut.clk)

    dut.reset.value = 0
    await pause_at_random_second(dut)
    await RisingEdge(dut.clk)

    dut.reset.value = 1
    await RisingEdge(dut.clk)
    dut.reset.value = 0

    await pause_at_random_minute(dut)
    await RisingEdge(dut.clk)
    
