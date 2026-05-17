import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import harness_library as hrs_lb

@cocotb.test()
async def test_perfect_squares_generator(dut):
    """Cocotb test for perfect squares generator"""

    # Initialize variables
    error_count = 0
    cycle_count = 0
    n = 2
    expected_sqr = n * n
    max_cycle_count = 100000
    CLK_PERIOD = 10  # Clock period in nanoseconds
    # Create a clock on dut.Clk
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD, unit='ns', period_high=(CLK_PERIOD+1)//2 if CLK_PERIOD%2 else CLK_PERIOD//2).start())
    
	# Initialize the DUT signals to default values (usually zero)
    await hrs_lb.dut_init(dut)

    # Apply an asynchronous reset to the DUT; reset is active high
    await hrs_lb.reset_dut(dut.reset, duration_ns=25, active=True)

    # Open a log file
    fd = open("perfect_squares_output.txt", "w")

    # Run simulation loop
    while cycle_count < max_cycle_count:
        await RisingEdge(dut.clk)
        cycle_count += 1

        # Capture and verify output
        actual_sqr_o = int(dut.sqr_o.value)
        
        if dut.reset.value:
            # Reset condition: reset n and expected square
            n = 2
            expected_sqr = n * n
        else:
            # Handle expected_sqr overflow
            if expected_sqr > 0xFFFFFFFF:
                expected_sqr = 0xFFFFFFFF  # Saturate expected square value

            # Check output against expected value
            if actual_sqr_o != (expected_sqr & 0xFFFFFFFF):
                if actual_sqr_o == 0xFFFFFFFF and expected_sqr == 0xFFFFFFFF:
                    fd.write(f"Cycle {cycle_count}: Output saturated at 0xFFFFFFFF due to overflow.\n")
                else:
                    fd.write(f"Cycle {cycle_count}: ERROR - Expected sqr_o = {expected_sqr & 0xFFFFFFFF:X}, "
                             f"but got {actual_sqr_o:X}\n")
                    error_count += 1
            else:
                fd.write(f"Cycle {cycle_count}: sqr_o = {actual_sqr_o:X} (Correct)\n")

            # Update n and compute the next expected square
            n += 1
            expected_sqr = n * n

        # Check for saturation to end simulation early
        if actual_sqr_o == 0xFFFFFFFF and expected_sqr == 0xFFFFFFFF:
            fd.write(f"Cycle {cycle_count}: Output has saturated. Ending simulation.\n")
            break

    # Final pass/fail report
    if error_count == 0:
        fd.write("TEST PASSED: No errors detected.\n")
    else:
        fd.write(f"TEST FAILED: {error_count} error(s) detected.\n")

    # Close the log file
    fd.close()
