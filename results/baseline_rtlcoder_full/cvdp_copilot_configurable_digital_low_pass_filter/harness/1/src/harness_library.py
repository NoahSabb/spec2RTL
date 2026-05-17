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