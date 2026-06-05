import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ClockCycles, Timer
import random
import time
import harness_library as hrs_lb

@cocotb.test()
async def test_perf_counters(dut):
        # Parameters
    CLK_PERIOD = 10  # Clock period in nanoseconds

    # Create a clock on dut.Clk
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD, unit='ns', period_high=(CLK_PERIOD+1)//2 if CLK_PERIOD%2 else CLK_PERIOD//2).start())
    
	# Initialize the DUT signals to default values (usually zero)
    await hrs_lb.dut_init(dut)

    # Apply an asynchronous reset to the DUT; reset is active high
    await hrs_lb.reset_dut(dut.reset, duration_ns=25, active=True)
    # Test sequence variables
    NUM_CYCLES = 50  # Number of clock cycles to test
    count_values = []

    # Start simulation
    dut.sw_req_i.value = 0  # Initial values
    dut.cpu_trig_i.value = 0

    await RisingEdge(dut.clk)  # Synchronize at rising edge of clock

    # Step 1: Test normal counting when sw_req_i is 0 and cpu_trig_i toggles
    for cycle in range(NUM_CYCLES):
        # Randomly toggle the cpu_trig_i
        dut.cpu_trig_i.value = random.randint(0, 1)
        await RisingEdge(dut.clk)  # Wait for the clock edge

        # Log and check count value
        count_values.append(int(dut.p_count_o.value))
        dut._log.info(f"Cycle: {cycle}, CPU Trigger: {dut.cpu_trig_i.value}, Counter Output: {dut.p_count_o.value}")

    # Step 2: Assert `sw_req_i` and check if the count resets to cpu_trig_i value
    dut.sw_req_i.value = 1  # Assert software request
    dut.cpu_trig_i.value = 1  # Set a value for cpu_trig_i

    await RisingEdge(dut.clk)  # Wait for the clock edge
    await Timer(CLK_PERIOD, unit='ns')  # Allow enough time for change

    # Verify that the counter resets to the value of cpu_trig_i
    assert dut.p_count_o.value == 1, f"Error: Counter value {dut.p_count_o.value}, expected 1 when sw_req_i is asserted"

    dut._log.info(f"After sw_req_i assert, Counter Output: {dut.p_count_o.value}")

    # Step 3: Deassert `sw_req_i` and allow normal counting to resume
    dut.sw_req_i.value = 0  # Deassert software request
    for cycle in range(NUM_CYCLES):
        # Randomly toggle the cpu_trig_i
        dut.cpu_trig_i.value = random.randint(0, 1)
        await RisingEdge(dut.clk)  # Wait for the clock edge

        # Log and check count value
        dut._log.info(f"Cycle: {cycle}, CPU Trigger: {dut.cpu_trig_i.value}, Counter Output: {dut.p_count_o.value}")
        count_values.append(int(dut.p_count_o.value))

    # Step 4: Reset and verify count is back to 0
    await hrs_lb.reset_dut(dut.reset, duration_ns=25, active=True)
    await RisingEdge(dut.clk)
    assert dut.p_count_o.value == 0, f"Error: Counter value {dut.p_count_o.value}, expected 0 after reset"
    dut._log.info(f"After reset, Counter Output: {dut.p_count_o.value}")  

@cocotb.test()
async def test_perf_counters_overflow(dut):
    # Parameters
    CLK_PERIOD = 10  # Clock period in nanoseconds
    CNT_W = len(dut.p_count_o)  # Get the width of the counter
    MAX_COUNT = (1 << CNT_W) - 1  # Maximum value the counter can hold based on CNT_W
    print(f"MAX_COUNT = {MAX_COUNT}")
    # Create a clock on dut.clk
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD, unit='ns', period_high=(CLK_PERIOD+1)//2 if CLK_PERIOD%2 else CLK_PERIOD//2).start())

    # Initialize the DUT signals to default values (usually zero)
    await hrs_lb.dut_init(dut)

    # Apply an asynchronous reset to the DUT; reset is active high
    await hrs_lb.reset_dut(dut.reset, duration_ns=25, active=True)

    # Start simulation
    dut.sw_req_i.value = 0  # Allow normal counting
    dut.cpu_trig_i.value = 1  # Trigger the counter on every cycle

    await RisingEdge(dut.clk)  # Synchronize at rising edge of clock

    # Step 1: Drive the counter up to its maximum value (MAX_COUNT)
    for _ in range(MAX_COUNT):
        await RisingEdge(dut.clk)  # Increment the counter
        dut._log.info(f"Current Counter Value: {int(dut.p_count_o.value)}")

    # Step 2: Verify that the next clock cycle causes an overflow (wraparound)
    await RisingEdge(dut.clk)  # One more cycle should cause the overflow
    assert int(dut.p_count_o.value) == 0, f"Error: Counter value {int(dut.p_count_o.value)}, expected 0 after overflow"

    dut._log.info(f"After overflow, Counter Output: {int(dut.p_count_o.value)}")

    # Step 3: Continue counting to ensure correct behavior after overflow
    #for i in range(5):
    i=0
    dut.sw_req_i.value = 1  # Assert software request
    await RisingEdge(dut.clk)
    dut.sw_req_i.value = 0  # Deassert software request        
    expected_value = i + 1
    assert int(dut.p_count_o.value) == expected_value, f"Error: Counter value {int(dut.p_count_o.value)}, expected {expected_value} after overflow"
    dut._log.info(f"Cycle {i+1} after overflow, Counter Output: {int(dut.p_count_o.value)}")
