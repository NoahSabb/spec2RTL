import cocotb
from cocotb.triggers import  Timer, RisingEdge, FallingEdge
from cocotb.clock import Clock
import harness_library as util
import random

@cocotb.test()
async def test_glitch_free_mux(dut):
    # Generate two random period clock signals
    clk1_period = random.randint(5, 20) # CLK1 with random clk period 
    await cocotb.start(util.phase_shifted_clock(dut.clk1, clk1_period, 0, "ns"))
    dut._log.info(f"clk1 STARTED, period: {clk1_period}, phase: 0")

    clk2_period = random.randint(1, 10) * clk1_period # clk2 is sync to clk1
    clk2_phase = random.randint(0, clk2_period//2)
    await cocotb.start(util.phase_shifted_clock(dut.clk2,clk2_period,clk2_phase, "ns"))
    dut._log.info(f"clk2 STARTED, period: {clk2_period}, phase: {clk2_phase}")

    # DUT RESET 
    dut.rst_n.value = 0 
    await Timer(random.randint(1, 30), unit="ns") # Assert reset for random time 
    dut.rst_n.value = 1
    dut._log.info(f"DUT IS OUT OF RESET") 
    
    # Excercise sel signal with random assertion/deassertion time
    dut.sel.value = 0 ; 
    await Timer(20, unit="ns")


    # Randomly choose which clk sel will be driven by.
    sel_sync_clock = util.random_clock_select(dut)
    #cocotb.start_soon(util.verification_check(dut))
    for i in range(50):
        await RisingEdge(sel_sync_clock)
        await FallingEdge(sel_sync_clock)
        dut.sel.value = ~ dut.sel.value
        
        # After sel change
        # 1. Wait one clock cycle to avoid glitches 
        # 2. Start the second clock on the next posedge, meanwhile clkout should be zero
        await util.check_glitch_free_transition(dut)
        

        sel_time =  random.randint(50, 500)
        for _ in range (sel_time):
            if  dut.sel.value == 0 :
                assert dut.clkout.value == dut.clk1.value, f"clkout isn't follwing clk1"
            else:
                assert dut.clkout.value == dut.clk2.value, f"clkout isn't follwing clk2"
            await Timer(1, unit="ns")


