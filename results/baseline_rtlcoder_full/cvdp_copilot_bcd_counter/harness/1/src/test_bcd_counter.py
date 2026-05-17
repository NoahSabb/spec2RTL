import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import harness_library as hrs_lb  

@cocotb.test()
async def test_bcd_counter(dut):
    """
    Test the BCD counter simulating a 24-hour clock with a 1 Hz frequency.
    Ensures that the counter correctly handles the transition through midnight.
    """

    # Start a 1 Hz clock with a 1 second period (1,000,000,000 nanoseconds)
    clock = Clock(dut.clk, 1_000_000_000, unit='ns')
    cocotb.start_soon(clock.start())

    # Apply reset using a custom function from the harness library
    # Reset is active low and lasts for 500,000,000 ns (500 seconds)
    await hrs_lb.reset_dut(dut.rst, duration_ns=500000000, active=False)

    # Wait for the first rising edge of the clock after reset
    await RisingEdge(dut.clk)

    # Function to simulate the passage of time based on hours, minutes, and seconds
    async def pass_time(hours, minutes, seconds):
        total_seconds = hours * 3600 + minutes * 60 + seconds
        # Advance the clock by one rising edge per second for the total number of seconds
        for _ in range(total_seconds):
            await RisingEdge(dut.clk)

    # Simulate the time until one second before midnight
    await pass_time(23, 59, 59)

    # Await the rising edge that represents the passing of the final second of the day
    await RisingEdge(dut.clk)

    # Output the state of the clock at midnight (expected to be reset to 00:00:00)
    print(f"Midnight transition: Hours = {dut.ms_hr.value}{dut.ls_hr.value}, " + \
          f"Minutes = {dut.ms_min.value}{dut.ls_min.value}, Seconds = {dut.ms_sec.value}{dut.ls_sec.value}")

    # Verify that the counter has reset to 00:00:00
    assert int(dut.ms_hr) == 0 and int(dut.ls_hr) == 0, "24-hour reset failed"
    assert int(dut.ms_min) == 0 and int(dut.ls_min) == 0, "24-hour reset failed"
    assert int(dut.ms_sec) == 0 and int(dut.ls_sec) == 0, "24-hour reset failed"

    # Pass some more time to ensure stability and correctness after the midnight reset
    await pass_time(10, 10, 10)  # Simulate additional time after midnight

    # Print the new time after additional 10 hours, 10 minutes, and 10 seconds
    print(f"Post-midnight check: Hours = {dut.ms_hr.value}{dut.ls_hr.value}, " + \
          f"Minutes = {dut.ms_min.value}{dut.ls_min.value}, Seconds = {dut.ms_sec.value}{dut.ls_sec.value}")

    # Assert the correctness of time after 10 hours, 10 minutes, and 10 seconds
    assert int(dut.ms_hr) == 1 and int(dut.ls_hr) == 0, "Counter incorrect for hours after reset"
    assert int(dut.ms_min) == 1 and int(dut.ls_min) == 0, "Counter incorrect for minutes after reset"
    assert int(dut.ms_sec) == 1 and int(dut.ls_sec) == 0, "Counter incorrect for seconds after reset"








