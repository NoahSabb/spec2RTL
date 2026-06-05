
from cocotb.triggers import FallingEdge, RisingEdge, Timer
import random

async def reset_dut(rst, dut):
    # Restart Interface
    await FallingEdge(dut.clk)
    rst.value = 0
    await FallingEdge(dut.clk)
    rst.value = 1
    await FallingEdge(dut.clk)
    rst._log.debug("Reset complete")

async def enable_dut(enable, duration_ns = 10):
    # Restart Interface
    enable.value = 0
    await Timer(duration_ns, unit="ns")
    enable.value = 1
    await Timer(duration_ns, unit='ns')
    enable._log.debug("enable complete")


async def dut_init(dut):
    # iterate all the input signals and initialize with 0
    for signal in dut:
        try:
            signal.value = 0
        except Exception:
            pass

async def calculate_moving_average(data_queue, current_sum, new_data, window):
    if len(data_queue) < window:
        data_queue.append(new_data)
        current_sum += new_data
    else:
        oldest_data = data_queue.pop(0)
        current_sum += new_data - oldest_data
        data_queue.append(new_data)

    expected_avg = current_sum // window
    
    return expected_avg, current_sum

