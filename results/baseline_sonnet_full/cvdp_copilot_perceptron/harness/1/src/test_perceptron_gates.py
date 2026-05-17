import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random

@cocotb.test()
async def test_perceptron_gates(dut):
    """Testbench for the perceptron_gates module using Cocotb."""

    # Create a 10ns clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset logic
    dut.rst_n.value = 0
    await Timer(10, unit="ns")
    dut.rst_n.value = 1

    # Initialize inputs
    dut.x1.value = 0
    dut.x2.value = 0
    dut.learning_rate.value = 1
    dut.threshold.value = 0
    dut.gate_select.value = 0

    await RisingEdge(dut.rst_n)
    await Timer(10, unit="ns")

    # Helper function for applying stimulus and logging outputs
    async def apply_stimulus(x1, x2, gate_select, duration):
        dut.x1.value = x1
        dut.x2.value = x2
        dut.gate_select.value = gate_select
        await Timer(duration, unit="ns")
        cocotb.log.info(f"gate_select={gate_select}, x1={x1}, x2={x2}, percep_w1={dut.percep_w1.value.signed_integer}, percep_w2={dut.percep_w2.value.signed_integer}, percep_bias={dut.percep_bias.value.signed_integer}, present_addr={bin(int(dut.present_addr.value))}, stop={bin(int(dut.stop.value))}, input_index={bin(int(dut.input_index.value))}, y_in={dut.y_in.value.signed_integer}, y={dut.y.value.signed_integer}, prev_percep_wt_1={dut.prev_percep_wt_1.value.signed_integer}, prev_percep_wt_2={dut.prev_percep_wt_2.value.signed_integer}, prev_percep_bias={dut.prev_percep_bias.value.signed_integer}")

    # Test AND gate targets (gate_select = 2'b00)
    dut.gate_select.value = 0b00
    cocotb.log.info("Start of AND gate Training")
    await apply_stimulus(1, 1, 0b00, 100)
    await apply_stimulus(1, -1, 0b00, 80)
    await apply_stimulus(-1, 1, 0b00, 90)
    await Timer(25, unit="ns")
    await apply_stimulus(-1, -1, 0b00, 95)
    await apply_stimulus(1, 1, 0b00, 25)
    await apply_stimulus(1, -1, 0b00, 30)
    await apply_stimulus(-1, 1, 0b00, 30)
    await apply_stimulus(-1, -1, 0b00, 90)
    await Timer(30, unit="ns")
    cocotb.log.info("End of AND gate Training")

    # Test OR gate targets (gate_select = 2'b01)
    dut.gate_select.value = 0b01
    cocotb.log.info("Start of OR gate Training")
    await apply_stimulus(1, 1, 0b01, 95)
    await Timer(30, unit="ns")
    await apply_stimulus(-1, 1, 0b01, 65)
    await apply_stimulus(1, -1, 0b01, 30)
    await apply_stimulus(-1, -1, 0b01, 60)
    cocotb.log.info("End of OR gate Training")

    # Test NAND gate targets (gate_select = 2'b10)
    dut.gate_select.value = 0b10
    cocotb.log.info("Start of NAND gate Training")
    await apply_stimulus(-1, -1, 0b10, 115)
    await Timer(30, unit="ns")
    await apply_stimulus(-1, 1, 0b10, 80)
    await Timer(30, unit="ns")
    await apply_stimulus(1, -1, 0b10, 65)
    await Timer(10, unit="ns")
    await apply_stimulus(1, 1, 0b10, 70)
    cocotb.log.info("End of NAND gate Training")

    # Test NOR gate targets (gate_select = 2'b11)
    dut.gate_select.value = 0b11
    cocotb.log.info("Start of NOR gate Training")
    await apply_stimulus(-1, -1, 0b11, 410)
    await Timer(20, unit="ns")
    await apply_stimulus(-1, 1, 0b11, 80)
    await Timer(20, unit="ns")
    await apply_stimulus(1, -1, 0b11, 80)
    await Timer(20, unit="ns")
    await apply_stimulus(1, 1, 0b11, 80)
    await Timer(20, unit="ns")
    await apply_stimulus(-1, -1, 0b11, 80)
    await Timer(20, unit="ns")
    await apply_stimulus(-1, 1, 0b11, 80)
    await Timer(20, unit="ns")
    await apply_stimulus(1, -1, 0b11, 80)
    await Timer(20, unit="ns")
    await apply_stimulus(1, 1, 0b11, 70)
    cocotb.log.info("End of NOR gate Training")

    # Randomized test cases
    num_random_cases = 10  # Number of random test cases
    for i in range(num_random_cases):
        random_gate_select = random.randint(0, 3)  # Randomly select gate (0b00 to 0b11)
        random_inputs = [(random.choice([-1, 1]), random.choice([-1, 1])) for _ in range(4)]

        dut.gate_select.value = random_gate_select
        cocotb.log.info(f"Start of Random Test Case {i+1} for gate_select={bin(random_gate_select)}")

        for x1, x2 in random_inputs:
            await apply_stimulus(x1, x2, random_gate_select, 100)
        cocotb.log.info(f"End of Random Test Case {i+1} for gate_select={bin(random_gate_select)}")

    # Stop the test
    cocotb.log.info("Test Completed")

