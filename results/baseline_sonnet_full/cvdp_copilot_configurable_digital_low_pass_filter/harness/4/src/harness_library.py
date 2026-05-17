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

# Reset the DUT (design under test)
async def reset_dut(reset_n, duration_ns=10):
    reset_n.value = 1
    await Timer(duration_ns, unit="ns")
    reset_n.value = 0
    await Timer(duration_ns, unit='ns')
    reset_n._log.debug("Reset complete")   

async def extract_signed(signal, width, total_elements):
         signed_values = []
         for i in reversed(range(total_elements)):
             # Extract the unsigned value
             unsigned_value = (signal.value.signed_integer >> (width * i)) & ((1 << width) - 1)
             # Convert to signed
             signed_value = unsigned_value - (1 << width) if unsigned_value & (1 << (width - 1)) else unsigned_value
             signed_values.append(signed_value)
         return signed_values

async def pack_signal(values, width):
    packed_signal = 0
    for i, value in enumerate(reversed(values)):
        # Convert the signed value to unsigned representation
        unsigned_value = value & ((1 << width) - 1)
        # Shift and combine into the packed signal
        packed_signal |= (unsigned_value << (i * width))
    return packed_signal    