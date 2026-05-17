import cocotb
from cocotb.triggers import FallingEdge, RisingEdge, Timer
import random

async def dut_init(dut):
    # iterate all the input signals and initialize with 0
    for signal in dut:
        try:
            signal.value = 0
        except Exception:
            pass

async def extract_signed(signal, width, total_elements):
         signed_values = []
         for i in reversed(range(total_elements)):
             # Extract the unsigned value
             unsigned_value = (signal.value.signed_integer >> (width * i)) & ((1 << width) - 1)
             # Convert to signed
             signed_value = unsigned_value - (1 << width) if unsigned_value & (1 << (width - 1)) else unsigned_value
             signed_values.append(signed_value)
         return signed_values

def generate_samples(N):
    # Valid values
    mapped_values = [-3, -1, 1, 3]  # Valid values for mapped symbols
    interp_values = [-3, -2, -1, 0, 1, 2, 3]  # Valid values for interpolated symbols

    # Initialize lists
    I_values = []
    Q_values = []

    # Generate samples dynamically
    for i in range(N // 2):
        I_values.extend([
            random.choice(mapped_values),  # First mapped
            random.choice(interp_values),  # Interpolated
            random.choice(mapped_values)   # Second mapped
        ])
        Q_values.extend([
            random.choice(mapped_values),  # First mapped
            random.choice(interp_values),  # Interpolated
            random.choice(mapped_values)   # Second mapped
        ])

    return I_values, Q_values

def pack_signal(values, width):
    packed_signal = 0
    for i, value in enumerate(reversed(values)):
        # Convert the signed value to unsigned representation
        unsigned_value = value & ((1 << width) - 1)
        # Shift and combine into the packed signal
        packed_signal |= (unsigned_value << (i * width))
    return packed_signal

def map_to_bits_vector(I_values, Q_values, N):
    bits = []  # Initialize an empty list for the bit stream

    for i in range(N):
        # Map I (real component) to MSBs (Most Significant Bits)
        if I_values[i] == -3:
            bits.extend([0, 0])  # MSBs = 00
        elif I_values[i] == -1:
            bits.extend([0, 1])  # MSBs = 01
        elif I_values[i] == 1:
            bits.extend([1, 0])  # MSBs = 10
        elif I_values[i] == 3:
            bits.extend([1, 1])  # MSBs = 11

        # Map Q (imaginary component) to LSBs (Least Significant Bits)
        if Q_values[i] == -3:
            bits.extend([0, 0])  # LSBs = 00
        elif Q_values[i] == -1:
            bits.extend([0, 1])  # LSBs = 01
        elif Q_values[i] == 1:
            bits.extend([1, 0])  # LSBs = 10
        elif Q_values[i] == 3:
            bits.extend([1, 1])  # LSBs = 11

    return bits

