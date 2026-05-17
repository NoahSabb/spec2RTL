# Filename: test_hill_cipher.py

import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from cocotb.clock import Clock
import random

def mod26(value):
    """Modulo 26 operation."""
    return value % 26

def mod64(value):
    """Modulo 32 operation."""
    return value % 64

@cocotb.test()
async def hill_cipher_test(dut):
    """Test the hill_cipher module with various inputs to cover all corner cases."""

    # Generate clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Reset the DUT
    dut.reset.value = 1
    dut.start.value = 0
    dut.plaintext.value = 0
    dut.key.value = 0
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await RisingEdge(dut.clk)

    # Define test cases with categories
    test_cases = [
        # Normal case
        {
            'category': 'Normal Case',
            'plaintext': 0b000010000100001,  # 'A', 'B', 'C' (assuming 'A' = 0, 'B' = 1, etc.)
            'key': 0b000010000100001000010000100001000010000100001,
            'expected_ciphertext': None  # Will compute below
        },
        # Maximum values
        {
            'category': 'Maximum Values',
            'plaintext': 0b110101101011010,  # Max plaintext `Z`, `Z`, `Z`
            'key': 0b111111111111111111111111111111111111111111111,
            'expected_ciphertext': None
        },
        # Minimum values
        {
            'category': 'Minimum Values',
            'plaintext': 0b000000000000000,
            'key': 0b000000000000000000000000000000000000000000000,
            'expected_ciphertext': None
        },
        # Edge case for modulo operation
        {
            'category': 'Edge Case: Modulo Operation',
            'plaintext': 0b001100011000110,  # 12, 12, 12
            'key': 0b001100011000110001100011000110001100011000110,  # 12s
            'expected_ciphertext': None
        },
        # Random values
        {
            'category': 'Random Case',
            'plaintext':  int(f"{random.randint(0, 0x19)}{random.randint(0, 0x19)}"),
            'key': random.randint(0, 0x1FFFFFFFFFF),
            'expected_ciphertext': None
        },
        # Another random case
        {
            'category': 'Random Case',
            'plaintext': int(f"{random.randint(0, 0x19)}{random.randint(0, 0x19)}"),
            'key': random.randint(0, 0x1FFFFFFFFFF),
            'expected_ciphertext': None
        },
    ]

    # Helper function to split bits into 5-bit chunks
    def split_bits(value, num_chunks, chunk_size):
        chunks = []
        for i in range(num_chunks):
            chunks.append((value >> ((num_chunks - 1 - i) * chunk_size)) & ((1 << chunk_size) - 1))
        return chunks

    # Run test cases
    for idx, case in enumerate(test_cases):
        dut._log.info(f"Running Test Case {idx+1}: {case['category']}")

        # Apply inputs
        dut.plaintext.value = case['plaintext']
        dut.key.value = case['key']
        await FallingEdge(dut.clk)
        dut.start.value = 1
        await RisingEdge(dut.clk)
        dut.start.value = 0

        # Wait for done signal
        while dut.done.value != 1:
            await RisingEdge(dut.clk)

        # Display input values in logs
        dut._log.info(f"Test Case {idx+1} Inputs:")
        dut._log.info(f"  Category: {case['category']}")
        dut._log.info(f"  Plaintext (binary): {bin(case['plaintext'])}")
        dut._log.info(f"  Plaintext (decimal): {int(case['plaintext'])}")
        dut._log.info(f"  Key (binary): {bin(case['key'])}")
        dut._log.info(f"  Key (decimal): {int(case['key'])}")

        # Compute expected ciphertext in Python
        P = split_bits(int(case['plaintext']), 3, 5)  # [P0, P1, P2]
        K = split_bits(int(case['key']), 9, 5)        # [K00, K01, ..., K22]

        # Reshape K into 3x3 matrix
        K_matrix = [K[0:3], K[3:6], K[6:9]]

        # Matrix multiplication
        C = []
        for i in range(3):
            temp = 0
            for j in range(3):
                temp += mod26(K_matrix[i][j] * P[j])
            temp = mod64(temp)
            C.append(mod26(temp))

        # Expected ciphertext
        expected_ciphertext = (C[0] << 10) | (C[1] << 5) | C[2]

        # Display expected ciphertext
        dut._log.info(f"  Expected Ciphertext (binary): {bin(expected_ciphertext)}")
        dut._log.info(f"  Expected Ciphertext (decimal): {expected_ciphertext}")

        # Check the output
        actual_ciphertext = int(dut.ciphertext.value)
        dut._log.info(f"  Actual Ciphertext (binary): {bin(actual_ciphertext)}")
        dut._log.info(f"  Actual Ciphertext (decimal): {actual_ciphertext}")

        assert actual_ciphertext == expected_ciphertext, (
            f"Test Case {idx+1} ({case['category']}) failed: "
            f"Expected {expected_ciphertext}, got {actual_ciphertext}"
        )

        # Reset the DUT between test cases
        dut.reset.value = 1
        await RisingEdge(dut.clk)
        dut.reset.value = 0
        await RisingEdge(dut.clk)

    dut._log.info("All test cases passed!")


@cocotb.test()
async def hill_cipher_clock_latency_test(dut):
    """Test the clock latency from start signal to done signal."""

    # Generate clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Reset the DUT
    dut.reset.value = 1
    await RisingEdge(dut.clk)
    dut.reset.value = 0

    # Apply a simple input
    dut.plaintext.value = 0b000010000100001  # Example plaintext
    dut.key.value = 0b000010000100001000010000100001000010000100001  # Example key

    # Assert start signal and measure latency
    await FallingEdge(dut.clk)
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    latency = 0
    while dut.done.value != 1:
        await RisingEdge(dut.clk)
        latency += 1

    # Log the latency
    dut._log.info(f"Clock Latency: {latency} clock cycles")
    assert latency == 3, "Clock latency should be equal to 3."
