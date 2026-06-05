import cocotb
from cocotb.triggers import Timer,  RisingEdge, ReadOnly
import random

#@cocotb.coroutine
async def phase_shifted_clock(signal, period, phase_shift, unit="ns"):
    """Generates a clock with a phase shift."""
    signal.value = 0 
    # Timer doesn't accept zero offset
    if phase_shift > 0:
        await Timer(phase_shift, unit=unit)
    while True:
        await Timer(period // 2, unit=unit)
        signal.value = ~ signal.value

async def check_glitch_free_transition(dut):
    dut._log.info(f"SEL EDGE")
    await ReadOnly()
    if dut.sel.value == 0:
        dut._log.info(f"SEL 1->0")
        #Glitch condition
        await RisingEdge(dut.clk2)
        dut._log.info(f"CLK2 POSEEDGE")
        await ReadOnly()
        # Assert clkout is no longer follwing clk2 by the first edge of clk2 after sel deassertion
        assert dut.clkout.value == 0, f"Glitch detected, clkout is {dut.clkout.value}"
        await RisingEdge(dut.clk1)
        dut._log.info(f"CLK1 POSEEDGE")

    elif dut.sel.value == 1:
        dut._log.info(f"SEL 0->1")
        await RisingEdge(dut.clk1)
        dut._log.info(f"CLK1 POSEEDGE")
        await ReadOnly()
        # Assert clkout is no longer follwing clk1 by the first edge of clk2 after sel assertion
        assert dut.clkout.value == 0, f"Glitch detected, clkout is {dut.clkout.value}"
        await RisingEdge(dut.clk2)
        dut._log.info(f"CLK2 POSEEDGE")
    await ReadOnly()

def random_clock_select(dut):
    # List of clock signals
    clocks = [dut.clk1, dut.clk2]
    # Randomly choose between clk1 and clk2
    selected_clk = random.choice(clocks)
    return selected_clk