import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ClockCycles, Timer
import random
import time
import harness_library as hrs_lb

@cocotb.test()
async def test_moving_average(dut):
    """Test the functionality of the moving average module."""
    
    # Start the clock with a 2ns period
    cocotb.start_soon(Clock(dut.clk, 2, unit='ns').start())

    # Define parameters for the data width and the window size
    width = 12   # Data width is 12 bits
    window = 8   # The moving average window size is 8

    # Log the test parameters
    print(f"[INFO] WIDTH = {width}, WINDOW_SIZE = {window}")
    
    # Initialize the DUT (Design Under Test)
    await hrs_lb.dut_init(dut)
    dut.data_in.value = 0

    # Apply reset 
    await hrs_lb.reset_dut(dut.reset)
    
    # Wait for a couple of cycles to stabilize
    for i in range(2):
        await RisingEdge(dut.clk)
    
    # Ensure all outputs are zero
    assert dut.data_out.value == 0, f"[ERROR] data_out is not zero after reset: {dut.data_out.value}"

    # Initialize variables for tracking the sum of the moving average and input data queue
    current_sum = 0
    data_queue = []
    previous_expected_avg = None  # Variable to hold the previous cycle's expected average

    # Randomize the total number of test cycles (between 20 to 50)
    cycle_num = random.randint(20, 50)
    # Determine the cycle at which a reset will be applied (halfway through the total test)
    reset_cycle = cycle_num // 2
    print(f"[INFO] Total cycles = {cycle_num}, Reset will be applied at cycle {reset_cycle}")
    
    # Loop through the cycles and apply random input data to the DUT
    for cycle in range(cycle_num):
        # Generate a random input value (based on the defined data width)
        data_in = random.randint(0, 2**width-1)
        dut.data_in.value = data_in  # Apply the input value to the DUT
        await RisingEdge(dut.clk)

        # Apply reset halfway through the test
        if cycle == reset_cycle:
            print(f"[INFO] Applying reset at cycle {cycle}")
            # Apply reset to the DUT and reset output
            #await RisingEdge(dut.clk)
            dut.reset.value = 1
            await RisingEdge(dut.clk)
            await RisingEdge(dut.clk)
            assert dut.data_out.value == 0, f"[ERROR] data_out is not zero after reset: {dut.data_out.value}"
            # Reset the sum and the data queue
            current_sum = 0
            data_queue = []
            previous_expected_avg = None  # Clear previous average
            
            # Wait for 2 cycles after reset to allow stabilization
            for i in range(2):
                await RisingEdge(dut.clk)
            dut.reset.value = 0  # Release reset
            print("[INFO] Starting fresh operation after reset")

            # Continue applying random inputs and checking output after reset
            for post_cycle in range(cycle_num - reset_cycle):
                # Generate new random input after reset
                data_in = random.randint(0, 2**width-1)
                dut.data_in.value = data_in
                await RisingEdge(dut.clk)

                # Calculate the expected moving average using a helper function
                expected_avg, current_sum = await hrs_lb.calculate_moving_average(
                    data_queue, current_sum, data_in, window
                )
                
                # Read the DUT output and compare it with the expected average
                actual_avg = int(dut.data_out.value)
                if previous_expected_avg is not None:
                    assert actual_avg == previous_expected_avg, \
                        f"[ERROR] Mismatch at post-reset cycle {post_cycle}: Expected {previous_expected_avg}, got {actual_avg}"
                    
                    # Log debugging information for each cycle
                    dut._log.info(f"[DEBUG] Post-reset Cycle {post_cycle}/{cycle_num - reset_cycle}: DUT average = {actual_avg}")
                    dut._log.info(f"[DEBUG] Post-reset Cycle {post_cycle}/{cycle_num - reset_cycle}: Testbench average = {previous_expected_avg}")

                # Update the previous expected average for the next comparison
                previous_expected_avg = expected_avg

            # Exit after completing post-reset cycles
            break

        # Calculate the expected moving average for the current cycle
        expected_avg, current_sum = await hrs_lb.calculate_moving_average(
            data_queue, current_sum, data_in, window
        )
        
        # Read the DUT output and compare it with the expected average
        actual_avg = int(dut.data_out.value)
        if previous_expected_avg is not None:
            assert actual_avg == previous_expected_avg, \
                f"[ERROR] Mismatch at cycle {cycle}: Expected {previous_expected_avg}, got {actual_avg}"
            
            # Log debugging information for each cycle
            dut._log.info(f"[DEBUG] Cycle {cycle}/{cycle_num}: DUT average = {actual_avg}")
            dut._log.info(f"[DEBUG] Cycle {cycle}/{cycle_num}: Testbench average = {previous_expected_avg}")

        # Update the previous expected average
        previous_expected_avg = expected_avg

    # Wait for a few stabilization cycles before ending the test
    for i in range(2):
        await RisingEdge(dut.clk)
    
    # Test completed successfully
    print("[INFO] Test 'test_moving_average' completed successfully.")
