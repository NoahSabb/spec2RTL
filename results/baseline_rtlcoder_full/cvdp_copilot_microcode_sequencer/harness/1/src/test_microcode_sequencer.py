import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge , Timer
import random


@cocotb.test()
async def test_microcode_sequencer(dut):
    """Testbench for microcode_sequencer"""

    # Create a clock with a period of 20 ns (50 MHz)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Initialize all inputs
    dut.instr_in.value = 0
    dut.c_n_in.value = 0
    dut.c_inc_in.value = 0
    dut.r_en.value = 0
    dut.cc.value = 0
    dut.ien.value = 0
    dut.d_in.value = 0
    dut.oen.value = 0

    # Reset DUT
    dut._log.info("Resetting DUT...")
    await Timer(3, unit="ns")  # Wait for reset to propagate
    dut._log.info("Reset complete.")

    # Allow signals to settle
    await Timer(20, unit="ns")

    # Utility function to safely read signal values
    def safe_read(signal):
        """Safely read a signal, handling unknown ('X') values."""
        try:
            return int(signal.value)
        except ValueError:
            dut._log.warning(f"Signal {signal._name} has an unknown value ('X'). Defaulting to 0.")
            return 0

    async def test_push_pc_instruction(dut):
        """Testbench for Push PC Instruction"""
        dut._log.info(f"Push_PC_instruction")
        # Start a clock with a period of 20 ns
        cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

        # Initialize inputs
        dut.instr_in.value = 0
        dut.c_n_in.value = 0
        dut.c_inc_in.value = 0
        dut.r_en.value = 0
        dut.cc.value = 0
        dut.ien.value = 0
        dut.d_in.value = 0
        dut.oen.value = 0

        # Reset DUT
        await Timer(9, unit="ns")

        # Apply Push PC Instruction inputs
        dut.instr_in.value = 0b01011
        dut.c_n_in.value = 0
        dut.c_inc_in.value = 0
        dut.r_en.value = 0
        dut.cc.value = 0
        dut.ien.value = 0
        dut.d_in.value = 0
        dut.oen.value = 0

        # Wait for the DUT to process the inputs
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        
        # Assertions
        expected_d_out = 0b01000  # Update based on expected PC value
        actual_d_out = safe_read(dut.d_out)
        assert actual_d_out == expected_d_out, f"Push PC Instruction failed: Expected {expected_d_out}, got {actual_d_out}"

        dut._log.info("Push PC Instruction test passed.")
    
    async def test_pop_pc_instruction(dut):
        """Testbench for Pop PC Instruction"""
        dut._log.info(f"Pop_PC_instruction")
        # Start a clock with a period of 20 ns
        cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

        # Initialize inputs
        dut.instr_in.value = 0
        dut.c_n_in.value = 0
        dut.c_inc_in.value = 0
        dut.r_en.value = 0
        dut.cc.value = 0
        dut.ien.value = 0
        dut.d_in.value = 0
        dut.oen.value = 0

        # Reset DUT
        await Timer(15, unit="ns")

        # Apply Pop PC Instruction inputs
        dut.instr_in.value = 0b01110
        dut.c_n_in.value = 0
        dut.c_inc_in.value = 0
        dut.r_en.value = 0
        dut.cc.value = 0
        dut.ien.value = 0
        dut.d_in.value = 0
        dut.oen.value = 0

        # Wait for the DUT to process the inputs
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        
        # Assertions
        expected_d_out = 0b01000  # Update based on expected PC value
        actual_d_out = safe_read(dut.d_out)
        assert actual_d_out == expected_d_out, f"Push PC Instruction failed: Expected {expected_d_out}, got {actual_d_out}"

        dut._log.info("Pop PC Instruction test passed.")

    # Test Task equivalent
    async def run_test_case(
        test_instr,          # Instruction input
        test_carry_in,       # Carry input
        test_carry_inc,      # Carry increment input
        test_reg_en,         # Register enable
        test_cond_code,      # Condition code
        test_instr_en,       # Instruction enable
        test_data_in,        # Data input
        test_output_en,      # Output enable
        expected_d_out,      # Expected data output
        expected_c_n_out,    # Expected carry out (full adder)
        expected_c_inc_out,  # Expected carry increment out
        expected_full,       # Expected full condition
        expected_empty,      # Expected empty condition
        case_name            # Name of the test case
    ):
        # Apply inputs
        dut.instr_in.value = test_instr
        dut.c_n_in.value = test_carry_in
        dut.c_inc_in.value = test_carry_inc
        dut.r_en.value = test_reg_en
        dut.cc.value = test_cond_code
        dut.ien.value = test_instr_en
        dut.d_in.value = test_data_in
        dut.oen.value = test_output_en

        # Wait for two clock cycles to allow the DUT to settle
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)

        # Log inputs, internal signals, and outputs
        dut._log.info(f"Running test case: {case_name}")
        dut._log.info(f"Inputs: instr_in = {int(dut.instr_in.value)}, c_n_in = {dut.c_n_in.value}, "
                      f"c_inc_in = {dut.c_inc_in.value}, r_en = {dut.r_en.value}, cc = {dut.cc.value}, "
                      f"ien = {dut.ien.value}, d_in = {int(dut.d_in.value)}, oen = {dut.oen.value}")
        dut._log.info(f"Expected: d_out = {expected_d_out}, c_n_out = {expected_c_n_out}, "
                      f"c_inc_out = {expected_c_inc_out}, full = {expected_full}, empty = {expected_empty}")
        dut._log.info(f"Actual: d_out = {int(dut.d_out.value)}, c_n_out = {dut.c_n_out.value}, "
                      f"c_inc_out = {dut.c_inc_out.value}, full = {dut.full.value}, empty = {dut.empty.value}")

        # Assertions
        assert int(dut.d_out.value) == expected_d_out, f"{case_name} - d_out mismatch"
        assert dut.c_n_out.value == expected_c_n_out, f"{case_name} - c_n_out mismatch"
        assert dut.c_inc_out.value == expected_c_inc_out, f"{case_name} - c_inc_out mismatch"
        assert dut.full.value == expected_full, f"{case_name} - full mismatch"
        assert dut.empty.value == expected_empty, f"{case_name} - empty mismatch"

    # Run fixed test cases
    await run_test_case(0b00000, 0, 0, 0, 0, 0, 0b0000, 0, 0b0000, 0, 0, 0, 1, "Reset Instruction")
    await run_test_case(0b00001, 0, 1, 0, 0, 0, 0b0000, 0, 0b0001, 0, 0, 0, 1, "Fetch PC Instruction 1")
    await run_test_case(0b00001, 0, 0, 0, 0, 0, 0b0000, 0, 0b0010, 0, 0, 0, 1, "Fetch PC Instruction 2")
    await run_test_case(0b00010, 0, 1, 0, 0, 0, 0b1010, 0, 0b1010, 0, 0, 0, 1, "Fetch R Instruction")
    await run_test_case(0b00011, 0, 1, 0, 0, 0, 0b1011, 0, 0b1011, 0, 0, 0, 1, "Fetch D Instruction")
    await run_test_case(0b00100, 1, 1, 0, 0, 0, 0b0011, 0, 0b0111, 0, 0, 0, 1, "Fetch R+D Instruction")
    await test_push_pc_instruction(dut)
    await test_push_pc_instruction(dut) 
    await test_pop_pc_instruction(dut)
    await test_pop_pc_instruction(dut)
    # Add randomized test case
    for i in range(2):  # Run 2 randomized test cases
        random_instr = 0  # Reset Instruction
        random_carry_in = 0
        random_carry_inc = 0
        random_reg_en = 0
        random_cond_code = 0
        random_instr_en = 0
        random_data_in = random.randint(0, 15)  # Random 4-bit data input
        random_output_en = 0

        # Determine expected values based on DUT behavior
        expected_d_out = 0  # Example behavior, adjust as per DUT logic
        expected_c_n_out = 0  # Adjust based on DUT
        expected_c_inc_out = 0  # Adjust based on DUT
        expected_full = 0  # Adjust based on DUT
        expected_empty = 1  # Adjust based on DUT

        await run_test_case(
            random_instr,
            random_carry_in,
            random_carry_inc,
            random_reg_en,
            random_cond_code,
            random_instr_en,
            random_data_in,
            random_output_en,
            expected_d_out,
            expected_c_n_out,
            expected_c_inc_out,
            expected_full,
            expected_empty,
            f"Random Test Case {i+1}"
        )

    dut._log.info("All test cases, including randomized tests, completed successfully.")

