import cocotb
from cocotb.triggers import Timer
import random
import string

# Helper function to compute expected Caesar cipher result
def caesar_shift(text, shift):
    result = ""
    for char in text:
        if 'A' <= char <= 'Z':
            result += chr(((ord(char) - ord('A') + shift) % 26) + ord('A'))
        elif 'a' <= char <= 'z':
            result += chr(((ord(char) - ord('a') + shift) % 26) + ord('a'))
        else:
            result += char  # Non-alphabetic characters remain unchanged
    return result

@cocotb.test()
async def test_predefined_cases(dut):
    """Test caesar_cipher with predefined cases"""
    # Verify that all signals are available in the DUT
    assert hasattr(dut, "key"), "DUT does not have a 'key' input."
    assert hasattr(dut, "input_char"), "DUT does not have an 'input_char' input."
    assert hasattr(dut, "output_char"), "DUT does not have an 'output_char' output."

    predefined_cases = [
        {"text": "hello", "key": 3, "expected": caesar_shift("hello", 3)},
        {"text": "WORLD", "key": 4, "expected": caesar_shift("WORLD", 4)},
        {"text": "Caesar", "key": 5, "expected": caesar_shift("Caesar", 5)},
        {"text": "Python3!", "key": 2, "expected": caesar_shift("Python3!", 2)},
        {"text": "EdgeCaseZ", "key": 1, "expected": caesar_shift("EdgeCaseZ", 1)},
    ]

    for case in predefined_cases:
        text = case["text"]
        key = case["key"]
        expected = case["expected"]

        dut._log.info(f"Testing Caesar cipher with input '{text}', key = {key}")
        dut.key.value = key  # Assign key to DUT port

        output = ""
        for char in text:
            dut.input_char.value = ord(char)  # Send each character as ASCII value
            await Timer(1, unit="ns")
            output += chr(int(dut.output_char.value))  # Collect each output char

        assert output == expected, f"Failed for input '{text}' with key {key}: expected '{expected}', got '{output}'"
        dut._log.info(f"Passed for input '{text}' with key {key}: output '{output}'")

@cocotb.test()
async def test_boundary_conditions(dut):
    """Test caesar_cipher with boundary conditions"""
    assert hasattr(dut, "key"), "DUT does not have a 'key' input."
    assert hasattr(dut, "input_char"), "DUT does not have an 'input_char' input."
    assert hasattr(dut, "output_char"), "DUT does not have an 'output_char' output."

    boundary_cases = [
        {"text": "Z", "key": 1, "expected": caesar_shift("Z", 1)},   # Wrap-around Z to A
        {"text": "z", "key": 1, "expected": caesar_shift("z", 1)},   # Wrap-around z to a
        {"text": "A", "key": 15, "expected": caesar_shift("A", 15)}, # Adjusted key within range
        {"text": "a", "key": 15, "expected": caesar_shift("a", 15)}, # Adjusted key within range
    ]

    for case in boundary_cases:
        text = case["text"]
        key = case["key"]
        expected = case["expected"]

        dut._log.info(f"Testing boundary condition with input '{text}', key = {key}")
        dut.key.value = key

        output = ""
        for char in text:
            dut.input_char.value = ord(char)
            await Timer(1, unit="ns")
            output += chr(int(dut.output_char.value))

        assert output == expected, f"Failed for input '{text}' with key {key}: expected '{expected}', got '{output}'"
        dut._log.info(f"Passed boundary condition test for input '{text}' with key {key}: output '{output}'")


@cocotb.test()
async def test_random_cases(dut):
    """Test caesar_cipher with random inputs and keys"""
    assert hasattr(dut, "key"), "DUT does not have a 'key' input."
    assert hasattr(dut, "input_char"), "DUT does not have an 'input_char' input."
    assert hasattr(dut, "output_char"), "DUT does not have an 'output_char' output."

    for _ in range(5):
        random_text = ''.join(random.choice(string.ascii_letters) for _ in range(8))  # Random 8-letter text
        random_key = random.randint(0, 15)  # Random key in the 4-bit range
        expected = caesar_shift(random_text, random_key)

        dut._log.info(f"Testing random input '{random_text}', key = {random_key}")
        dut.key.value = random_key

        output = ""
        for char in random_text:
            dut.input_char.value = ord(char)
            await Timer(1, unit="ns")
            output += chr(int(dut.output_char.value))

        assert output == expected, f"Random test failed for input '{random_text}' with key {random_key}: expected '{expected}', got '{output}'"
        dut._log.info(f"Random test passed for input '{random_text}' with key {random_key}: output '{output}'")

@cocotb.test()
async def test_with_numbers_and_symbols(dut):
    """Test caesar_cipher with numbers and symbols to ensure they remain unchanged"""
    assert hasattr(dut, "key"), "DUT does not have a 'key' input."
    assert hasattr(dut, "input_char"), "DUT does not have an 'input_char' input."
    assert hasattr(dut, "output_char"), "DUT does not have an 'output_char' output."

    # Define a test case with numbers and symbols
    text = "Hello123!@#World"
    key = 3
    expected = caesar_shift(text, key)  # Expected result with only alphabetic chars shifted

    dut._log.info(f"Testing Caesar cipher with input '{text}', key = {key} (includes numbers and symbols)")
    dut.key.value = key  # Assign key to DUT port

    output = ""
    for char in text:
        dut.input_char.value = ord(char)  # Send each character as ASCII value
        await Timer(1, unit="ns")
        output += chr(int(dut.output_char.value))  # Collect each output char

    assert output == expected, f"Failed for input '{text}' with key {key}: expected '{expected}', got '{output}'"
    dut._log.info(f"Passed for input '{text}' with key {key}: output '{output}'")
