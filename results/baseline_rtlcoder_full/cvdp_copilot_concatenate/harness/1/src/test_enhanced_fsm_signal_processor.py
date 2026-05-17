import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock

def assert_equal(actual, expected, msg=""):
    """Custom assertion with message."""
    assert actual == expected, f"{msg}: Expected {expected}, but got {actual}"

@cocotb.test()
async def test_enhanced_fsm_signal_processor(dut):
    # Setup clock: 10 ns period (100 MHz)
    clock = Clock(dut.i_clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Initialize all inputs
    dut.i_rst_n.value = 0
    dut.i_enable.value = 0
    dut.i_clear.value = 0
    dut.i_ack.value = 0
    dut.i_fault.value = 0
    dut.i_vector_1.value = 0
    dut.i_vector_2.value = 0
    dut.i_vector_3.value = 0
    dut.i_vector_4.value = 0
    dut.i_vector_5.value = 0
    dut.i_vector_6.value = 0

    # Apply asynchronous reset
    await Timer(20, unit="ns")  # Hold reset for 20 ns
    dut.i_rst_n.value = 1
    await RisingEdge(dut.i_clk)
    await Timer(1, unit="ns")

    # Check initial state after reset
    assert_equal(dut.o_fsm_status.value, 0b00, "FSM should be in IDLE after reset")
    assert_equal(dut.o_ready.value, 0, "o_ready should be 0 in IDLE")
    assert_equal(dut.o_error.value, 0, "o_error should be 0 in IDLE")

    # Test IDLE to PROCESS transition
    dut.i_enable.value = 1
    dut.i_vector_1.value = 0b00001
    dut.i_vector_2.value = 0b00010
    dut.i_vector_3.value = 0b00100
    dut.i_vector_4.value = 0b01000
    dut.i_vector_5.value = 0b10000
    dut.i_vector_6.value = 0b11111
    await RisingEdge(dut.i_clk)
    await RisingEdge(dut.i_clk)
    await Timer(1, unit="ns")
    assert_equal(dut.o_fsm_status.value, 0b01, "FSM should transition to PROCESS on i_enable")

    # Test vector processing in PROCESS state
    
    await RisingEdge(dut.i_clk)
    await Timer(1, unit="ns")
    assert_equal(dut.o_vector_1.value, 0b00001000, "o_vector_1 should match MSB of concatenation")
    assert_equal(dut.o_vector_2.value, 0b10001000, "o_vector_2 should match second MSB segment")
    assert_equal(dut.o_vector_3.value, 0b10001000, "o_vector_3 should match third MSB segment")
    assert_equal(dut.o_vector_4.value, 0b01111111, "o_vector_4 should match LSB segment")

    assert_equal(dut.o_fsm_status.value, 0b10, "FSM should transition to READY after processing")
    assert_equal(dut.o_ready.value, 1, "o_ready should be 1 in READY state")

    # Test READY to IDLE transition
    dut.i_ack.value = 1
    await RisingEdge(dut.i_clk)
    await RisingEdge(dut.i_clk)
    await Timer(1, unit="ns")
    dut.i_ack.value = 0
    assert_equal(dut.o_fsm_status.value, 0b00, "FSM should transition to IDLE on i_ack")
    assert_equal(dut.o_ready.value, 0, "o_ready should be 0 in IDLE")

    # Test fault condition from IDLE
    dut.i_fault.value = 1
    await RisingEdge(dut.i_clk)
    await RisingEdge(dut.i_clk)
    await Timer(1, unit="ns")
    assert_equal(dut.o_fsm_status.value, 0b11, "FSM should transition to FAULT on i_fault")
    assert_equal(dut.o_error.value, 1, "o_error should be 1 in FAULT state")

    # Test clearing fault condition
    dut.i_clear.value = 1
    dut.i_fault.value = 0
    dut.i_enable.value = 0
    await RisingEdge(dut.i_clk)
    await RisingEdge(dut.i_clk)
    await Timer(1, unit="ns")
    dut.i_clear.value = 0
    assert_equal(dut.o_fsm_status.value, 0b00, "FSM should transition to IDLE after clearing fault")
    assert_equal(dut.o_error.value, 0, "o_error should be 0 after fault is cleared")

    # Test fault during PROCESS
    dut.i_enable.value = 1
    await RisingEdge(dut.i_clk)
    await RisingEdge(dut.i_clk)
    await Timer(1, unit="ns")
    assert_equal(dut.o_fsm_status.value, 0b01, "FSM should transition to PROCESS on i_enable")
    dut.i_fault.value = 1
    await RisingEdge(dut.i_clk)
    await RisingEdge(dut.i_clk)
    await Timer(1, unit="ns")
    assert_equal(dut.o_fsm_status.value, 0b11, "FSM should transition to FAULT on i_fault in PROCESS")

    # Test all outputs reset in FAULT
    assert_equal(dut.o_vector_1.value, 0, "o_vector_1 should reset in FAULT")
    assert_equal(dut.o_vector_2.value, 0, "o_vector_2 should reset in FAULT")
    assert_equal(dut.o_vector_3.value, 0, "o_vector_3 should reset in FAULT")
    assert_equal(dut.o_vector_4.value, 0, "o_vector_4 should reset in FAULT")
