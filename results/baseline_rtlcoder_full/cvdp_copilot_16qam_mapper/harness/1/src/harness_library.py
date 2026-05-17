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