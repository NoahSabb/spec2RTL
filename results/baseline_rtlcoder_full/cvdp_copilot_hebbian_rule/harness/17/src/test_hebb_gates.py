import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random

@cocotb.test()
async def test_hebb_gates(dut):
    """Test the hebb_gates module with different gate selections and inputs."""

    # Create a 10ns clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset logic
    dut.rst.value = 0
    await Timer(10, unit="ns")
    dut.rst.value = 1

    # Initialize inputs
    dut.start.value = 0
    dut.a.value = 0
    dut.b.value = 0
    dut.gate_select.value = 0

    await RisingEdge(dut.rst)
    await Timer(10, unit="ns")

    # Helper function for applying stimulus and logging outputs
    async def apply_stimulus(a, b, gate_select, duration):
        dut.a.value = a
        dut.b.value = b
        dut.gate_select.value = gate_select
        await Timer(duration, unit="ns")
        cocotb.log.info(f"gate_select={gate_select}, a={a}, b={b}, w1={dut.w1.value.signed_integer}, w2={dut.w2.value.signed_integer}, bias={dut.bias.value.signed_integer}, state={bin(int(dut.present_state.value))}")

    # Test AND gate targets (gate_select = 2'b00)
    dut.gate_select.value = 0b00
    dut.start.value = 1
    cocotb.log.info("Start of AND gate Training")

    await apply_stimulus(1, 1, 0b00, 60)
    await apply_stimulus(1, -1, 0b00, 60)
    await apply_stimulus(-1, 1, 0b00, 60)
    await apply_stimulus(-1, -1, 0b00, 70)
    assert dut.w1.value.signed_integer == 2, f"Expected w1=1, but got {dut.w1.value.signed_integer}"
    assert dut.w2.value.signed_integer == 2, f"Expected w2=1, but got {dut.w2.value.signed_integer}"
    assert dut.bias.value.signed_integer == -2, f"Expected bias=-1, but got {dut.bias.value.signed_integer}"
    cocotb.log.info("End of AND gate Training")

    # Test OR gate targets (gate_select = 2'b01)
    dut.gate_select.value = 0b01
    cocotb.log.info("Start of OR gate Training")

    await apply_stimulus(1, 1, 0b01, 70)
    await apply_stimulus(-1, 1, 0b01, 60)
    await apply_stimulus(1, -1, 0b01, 60)
    await apply_stimulus(-1, -1, 0b01, 70)
    assert dut.w1.value.signed_integer == 2, f"Expected w1=1, but got {dut.w1.value.signed_integer}"
    assert dut.w2.value.signed_integer == 2, f"Expected w2=1, but got {dut.w2.value.signed_integer}"
    assert dut.bias.value.signed_integer == 2, f"Expected bias=-1, but got {dut.bias.value.signed_integer}"
    cocotb.log.info("End of OR gate Training")

    # Test NAND gate targets (gate_select = 2'b10)
    dut.gate_select.value = 0b10
    cocotb.log.info("Start of NAND gate Training")

    await apply_stimulus(-1, -1, 0b10, 70)
    await apply_stimulus(-1, 1, 0b10, 60)
    await apply_stimulus(1, -1, 0b10, 60)
    await apply_stimulus(1, 1, 0b10, 70)
    assert dut.w1.value.signed_integer == -2, f"Expected w1=1, but got {dut.w1.value.signed_integer}"
    assert dut.w2.value.signed_integer == -2, f"Expected w2=1, but got {dut.w2.value.signed_integer}"
    assert dut.bias.value.signed_integer == 2, f"Expected bias=-1, but got {dut.bias.value.signed_integer}"
    cocotb.log.info("End of NAND gate Training")

    # Test NOR gate targets (gate_select = 2'b11)
    dut.gate_select.value = 0b11
    cocotb.log.info("Start of NOR gate Training")

    await apply_stimulus(-1, -1, 0b11, 70)
    await apply_stimulus(-1, 1, 0b11, 60)
    await apply_stimulus(1, -1, 0b11, 60)
    await apply_stimulus(1, 1, 0b11, 70)
    assert dut.w1.value.signed_integer == -2, f"Expected w1=1, but got {dut.w1.value.signed_integer}"
    assert dut.w2.value.signed_integer == -2, f"Expected w2=1, but got {dut.w2.value.signed_integer}"
    assert dut.bias.value.signed_integer == -2, f"Expected bias=-1, but got {dut.bias.value.signed_integer}"
    cocotb.log.info("End of NOR gate Training")

    # Randomized test cases
    num_random_cases = 10  # Number of random test cases
    for i in range(num_random_cases):
        random_gate_select = random.randint(0, 3)  # Randomly select gate (0b00 to 0b11)
        random_inputs = [(random.choice([-1, 1]), random.choice([-1, 1])) for _ in range(4)]

        dut.gate_select.value = random_gate_select
        dut.start.value = 1
        cocotb.log.info(f"Start of Random Test Case {i+1} for gate_select={bin(random_gate_select)}")

        for a, b in random_inputs:
            await apply_stimulus(a, b, random_gate_select, 65)
        cocotb.log.info(f"End of Random Test Case {i+1} for gate_select={bin(random_gate_select)}")
    # Stop the test
    dut.start.value = 0
    cocotb.log.info("Test Completed")
