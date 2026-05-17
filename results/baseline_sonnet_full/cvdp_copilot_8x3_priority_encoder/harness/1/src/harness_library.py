
from cocotb.triggers import FallingEdge, RisingEdge, Timer
import random

async def reset_dut(reset_n, duration_ns = 10):
    # Restart Interface
    reset_n.value = 0
    await Timer(duration_ns, unit="ns")
    reset_n.value = 1
    await Timer(duration_ns, unit='ns')
    reset_n._log.debug("Reset complete")

async def duty_cycle(pwm_signal, clock, period):
    # 0-> time_period, 1-> high_time, 2-> low_time = full_time = high_time
    pwm = {"time_period": period, "on_time": 0, "off_time": 0}
    pwm_signal._log.debug("Pulse started")
    for i in range(period):
        if pwm_signal.value == 1:
            pwm["on_time"] += 1
        await RisingEdge(clock)

    pwm["off_time"] = pwm["time_period"] - pwm["on_time"]
    pwm_signal._log.debug("Time period completed")
    return pwm

async def dut_init(dut):
    # iterate all the input signals and initialize with 0
    for signal in dut:
        try:
            signal.value = 0
        except Exception:
            pass


def highbit_number(number: int, length=8, msb=True) -> int:
    str_num = bin(number)[2:].zfill(length)
    print(str_num)    
    if '1' not in str_num:
        return 0  # Return 0 if the number has no '1' bits
    
    if msb:
        return length - str_num.index('1') - 1
    else:
        return str_num[::-1].index('1')
