import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random

# Helper function to calculate expected encoded bits based on generator polynomials
def expected_bits(data_in, shift_reg):
    g1 = data_in ^ shift_reg[0] ^ shift_reg[1]  # Generator g1 = 111
    g2 = data_in ^ shift_reg[1]                 # Generator g2 = 101
    return g1, g2

@cocotb.test()
async def test_reset(dut):
    """Test reset functionality."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())  # Start the clock

    # Apply reset
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)  # Wait for a few clock cycles
    dut.rst.value = 0

    # Check if the shift register and encoded bits are properly reset
    assert dut.shift_reg.value == 0, f"Shift register is not reset properly: {dut.shift_reg.value}"
    assert dut.encoded_bit1.value == 0, f"Encoded bit1 is not reset properly: {dut.encoded_bit1.value}"
    assert dut.encoded_bit2.value == 0, f"Encoded bit2 is not reset properly: {dut.encoded_bit2.value}"

@cocotb.test()
async def test_convolutional_encoding(dut):
    """Test the convolutional encoding logic for a sequence of data."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())  # Start the clock

    # Reset the DUT
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0

    # Initialize shift register
    shift_reg = [0, 0]  # Initial state of the shift register (2-bit for K-1)

    # Apply a sequence of data and check the encoded output
    test_data = [1, 0, 1, 1, 0, 0]  # Test input sequence
    for i, bit_in in enumerate(test_data):
        dut.data_in.value = bit_in

        # Wait for a clock edge and then a short delay to allow signal propagation
        await RisingEdge(dut.clk)
        await Timer(2, unit="ns")  # Small delay to ensure signals stabilize

        # Calculate the expected encoded bits
        expected_bit1, expected_bit2 = expected_bits(bit_in, shift_reg)

        # Debug print for shift register and expected vs actual encoded bits
        print(f"Cycle {i + 1}: Input bit: {bit_in}, Shift register: {shift_reg}")
        print(f"Expected encoded bits: bit1={expected_bit1}, bit2={expected_bit2}")
        print(f"Actual encoded bits: bit1={int(dut.encoded_bit1.value)}, bit2={int(dut.encoded_bit2.value)}")

        # Check the encoded bits after allowing for signal stabilization
        assert dut.encoded_bit1.value == expected_bit1, f"Encoded bit1 mismatch at cycle {i + 1}: got {dut.encoded_bit1.value}, expected {expected_bit1}"
        assert dut.encoded_bit2.value == expected_bit2, f"Encoded bit2 mismatch at cycle {i + 1}: got {dut.encoded_bit2.value}, expected {expected_bit2}"

        # Update the shift register (LIFO shift)
        shift_reg = [bit_in] + shift_reg[:-1]

@cocotb.test()
async def test_random_data(dut):
    """Test convolutional encoding with random input data."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())  # Start the clock

    # Reset the DUT
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0

    # Initialize shift register
    shift_reg = [0, 0]  # Initial state of the shift register

    # Apply a random sequence of data and check the encoded output
    for i in range(10):
        bit_in = random.randint(0, 1)
        dut.data_in.value = bit_in

        # Wait for a clock edge and then a short delay to allow signal propagation
        await RisingEdge(dut.clk)
        await Timer(2, unit="ns")  # Small delay to ensure signals stabilize

        # Calculate the expected encoded bits
        expected_bit1, expected_bit2 = expected_bits(bit_in, shift_reg)

        # Debug print for shift register and expected vs actual encoded bits
        print(f"Cycle {i + 1}: Input bit: {bit_in}, Shift register: {shift_reg}")
        print(f"Expected encoded bits: bit1={expected_bit1}, bit2={expected_bit2}")
        print(f"Actual encoded bits: bit1={int(dut.encoded_bit1.value)}, bit2={int(dut.encoded_bit2.value)}")

        # Check the encoded bits after allowing for signal stabilization
        assert dut.encoded_bit1.value == expected_bit1, f"Encoded bit1 mismatch at cycle {i + 1}: got {dut.encoded_bit1.value}, expected {expected_bit1}"
        assert dut.encoded_bit2.value == expected_bit2, f"Encoded bit2 mismatch at cycle {i + 1}: got {dut.encoded_bit2.value}, expected {expected_bit2}"

        # Update the shift register
        shift_reg = [bit_in] + shift_reg[:-1]
