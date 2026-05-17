import cocotb
from cocotb.triggers import Timer
import random

# Dictionary of ASCII characters to expected Morse code (binary) and length
ascii_to_morse = {
    'A': (0b01, 2),       # .-
    'B': (0b1000, 4),     # -...
    'C': (0b1010, 4),     # -.-.
    'D': (0b100, 3),      # -..
    'E': (0b0, 1),        # .
    'F': (0b0010, 4),     # ..-.
    'G': (0b110, 3),      # --.
    'H': (0b0000, 4),     # ....
    'I': (0b00, 2),       # ..
    'J': (0b0111, 4),     # .---
    'K': (0b101, 3),      # -.-
    'L': (0b0100, 4),     # .-..
    'M': (0b11, 2),       # --
    'N': (0b10, 2),       # -.
    'O': (0b111, 3),      # ---
    'P': (0b0110, 4),     # .--.
    'Q': (0b1101, 4),     # --.-
    'R': (0b010, 3),      # .-.
    'S': (0b000, 3),      # ...
    'T': (0b1, 1),        # -
    'U': (0b001, 3),      # ..-
    'V': (0b0001, 4),     # ...-
    'W': (0b011, 3),      # .--
    'X': (0b1001, 4),     # -..-
    'Y': (0b1011, 4),     # -.--
    'Z': (0b1100, 4),     # --..
    '0': (0b11111, 5),    # -----
    '1': (0b01111, 5),    # .----
    '2': (0b00111, 5),    # ..---
    '3': (0b00011, 5),    # ...--
    '4': (0b00001, 5),    # ....-
    '5': (0b00000, 5),    # .....
    '6': (0b10000, 5),    # -....
    '7': (0b11000, 5),    # --...
    '8': (0b11100, 5),    # ---..
    '9': (0b11110, 5),    # ----.
}

@cocotb.test()
async def test_random_ascii_inputs(dut):
    """Test the morse_encoder module with random ASCII inputs."""
    num_tests = 256  # Number of random tests to run
    ascii_range = (65, 90)  # ASCII range for 'A' to 'Z'

    for _ in range(num_tests):
        random_ascii = random.randint(*ascii_range)  # Generate a random ASCII value within the range
        ascii_char = chr(random_ascii)  # Convert ASCII value to character

        # Check if the character is in the predefined Morse code dictionary
        if ascii_char in ascii_to_morse:
            expected_morse, expected_length = ascii_to_morse[ascii_char]
            dut.ascii_in.value = random_ascii
            await Timer(1, unit='ns')
            assert int(dut.morse_out.value) == expected_morse, f"Test failed for {ascii_char}: Expected Morse {bin(expected_morse)}, got {bin(int(dut.morse_out.value))}"
            assert int(dut.morse_length.value) == expected_length, f"Test failed for {ascii_char}: Expected length {expected_length}, got {int(dut.morse_length.value)}"
        else:
            print(f"Skipping {ascii_char}, not in Morse code dictionary.")

@cocotb.test()
async def test_specific_chars(dut):
    """Test specific characters as originally planned."""
    for ascii_char, (expected_morse, expected_length) in ascii_to_morse.items():
        dut.ascii_in.value = ord(ascii_char)
        await Timer(1, unit='ns')
        assert int(dut.morse_out.value) == expected_morse, f"Test failed for {ascii_char}: Expected Morse {bin(expected_morse)}, got {bin(int(dut.morse_out.value))}"
        assert int(dut.morse_length.value) == expected_length, f"Test failed for {ascii_char}: Expected length {expected_length}, got {int(dut.morse_length.value)}"

@cocotb.test()
async def test_random_numeric_inputs(dut):
    """Test the morse_encoder module with random numeric inputs."""
    num_tests = 256  # Number of random tests to run
    numeric_range = (48, 57)  # ASCII range for '0' to '9'

    for _ in range(num_tests):
        random_ascii = random.randint(*numeric_range)  # Generate a random ASCII value within the numeric range
        ascii_char = chr(random_ascii)  # Convert ASCII value to character

        expected_morse, expected_length = ascii_to_morse[ascii_char]
        dut.ascii_in.value = random_ascii
        await Timer(1, unit='ns')
        morse_out = int(dut.morse_out.value)
        morse_length = int(dut.morse_length.value)

        assert morse_out == expected_morse and morse_length == expected_length, \
            f"Test failed for numeric {ascii_char}: Expected Morse {bin(expected_morse)}, got {bin(morse_out)}; Expected length {expected_length}, got {morse_length}"
