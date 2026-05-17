import cocotb
from cocotb.triggers import Timer, RisingEdge, FallingEdge
import random

async def async_reset_dut(dut):

    dut.reset_n.value = 1
    await FallingEdge(dut.clk)
    dut.reset_n.value = 0
    await Timer(2, unit="ns")  # Small delay
    assert dut.apb_psel_o.value == 0, "APB select should be 0 at a reset"
    assert dut.apb_penable_o.value == 0, "APB enable should be 0 at a reset" 
    assert dut.apb_pwrite_o.value == 0, "APB write signal should be 0 at a reset" 
    assert dut.apb_paddr_o.value == 0, f"APB address should be 0 at a reset"
    assert dut.apb_pwdata_o.value == 0, f"APB data should be 0 at a reset"  
    await RisingEdge(dut.clk)
    dut.reset_n.value = 1
    await RisingEdge(dut.clk)

async def run_apb_test_with_delay(dut, select_signal, expected_addr, expected_data):

    # Apply stimulus for the selected signal
    select_signal.value = 1
    dut.apb_pready_i.value = 0  # Initially APB is not ready

    # Wait for a few clock cycles to simulate state transitions
    await RisingEdge(dut.clk)
    select_signal.value = 0 

    # latency count
    latency_sel = 0
    while (dut.apb_psel_o.value == 0) and (dut.apb_pwrite_o.value == 0):
        await RisingEdge(dut.clk)
        latency_sel += 1

    # SETUP state checks
    assert latency_sel == 1, f"Latency from `apb_psel_o` should be 1 cycle, but got {latency_sel}"    
    assert dut.apb_psel_o.value == 1, "APB select signal should be high in SETUP state"
    assert dut.apb_penable_o.value == 0, "APB enable signal should be deasserted in ACCESS state"
    assert dut.apb_pwrite_o.value == 1, "APB write signal should be high in SETUP state"
    assert dut.apb_paddr_o.value == expected_addr, f"APB address should be {hex(expected_addr)} in SETUP state"
    assert dut.apb_pwdata_o.value == expected_data, f"APB data should be {hex(expected_data)} in SETUP state"
 
    # latency count
    latency_enable = 0
    while dut.apb_penable_o.value == 0:
        await RisingEdge(dut.clk)
        latency_enable += 1

    # ACCESS state checks
    # Validate that `apb_penable_o` is asserted exactly 1 clock cycle after `apb_psel_o`
    await RisingEdge(dut.clk)
    assert latency_enable == 1, f"Latency from `apb_psel_o` to `apb_penable_o` should be 1 cycle, but got {latency_enable}"
    assert dut.apb_penable_o.value == 1, "APB enable signal should be high in ACCESS state"
    assert dut.apb_psel_o.value == 1, "APB select signal should be stable in ACCESS state"
    assert dut.apb_pwrite_o.value == 1, "APB write signal should be stable in ACCESS state"
    assert dut.apb_paddr_o.value == expected_addr, f"APB address should be {hex(expected_addr)} in ACCESS state"
    assert dut.apb_pwdata_o.value == expected_data, f"APB data should be {hex(expected_data)} in ACCESS state"
    
    # Simulate some delay before APB becomes ready
    delay_cycles = random.randint(2, 5)
    for _ in range(delay_cycles):
        await RisingEdge(dut.clk)
    
    # Simulate APB becoming ready
    dut.apb_pready_i.value = 1
    await RisingEdge(dut.clk)
    dut.apb_pready_i.value = 0  # Deasserting ready

    latency_rdy = 0
    while dut.apb_penable_o.value == 1:
        await RisingEdge(dut.clk)
        latency_rdy += 1  

    # Check if APB signals are deasserted after the transaction
    assert latency_rdy == 1, f"Latency from `apb_pready_i` to `apb_sel_o` and `apb_penable_o` should be 1 cycle, but got {latency_rdy}"
    assert dut.apb_psel_o.value == 0, "APB select should be deasserted after ACCESS"
    assert dut.apb_penable_o.value == 0, "APB enable should be deasserted after ACCESS" 
    assert dut.apb_pwrite_o.value == 0, "APB write signal should be deasserted after ACCESS state" 
    assert dut.apb_paddr_o.value == 0, f"APB address should be 0 after ACCESS"
    assert dut.apb_pwdata_o.value == 0, f"APB data should be 0 after ACCESS"     

async def run_apb_test_without_delay(dut, select_signal, expected_addr, expected_data):

    # Apply stimulus for the selected signal
    select_signal.value = 1
    dut.apb_pready_i.value = 0  # Initially APB is not ready

    # Wait for a 1 clock cycles to simulate state transitions
    await RisingEdge(dut.clk)
    select_signal.value = 0 

    # latency count
    latency_sel = 0
    while (dut.apb_psel_o.value == 0) and (dut.apb_pwrite_o.value == 0):
        await RisingEdge(dut.clk)
        latency_sel += 1
    dut.apb_pready_i.value = 1  # Asserting ready signal
    # SETUP state checks
    assert latency_sel == 1, f"Latency from `apb_psel_o` should be 1 cycle, but got {latency_sel}"    
    assert dut.apb_psel_o.value == 1, "APB select signal should be high in SETUP state"
    assert dut.apb_penable_o.value == 0, "APB enable signal should be deasserted in ACCESS state"
    assert dut.apb_pwrite_o.value == 1, "APB write signal should be high in SETUP state"
    assert dut.apb_paddr_o.value == expected_addr, f"APB address should be {hex(expected_addr)} in SETUP state"
    assert dut.apb_pwdata_o.value == expected_data, f"APB data should be {hex(expected_data)} in SETUP state"       

    # ACCESS state checks
    await RisingEdge(dut.clk)
    assert dut.apb_psel_o.value == 1, "APB select signal should be asserted in ACCESS state"
    assert dut.apb_penable_o.value == 1, "APB enable signal should be asserted in ACCESS state"
    assert dut.apb_pwrite_o.value == 1, "APB write signal should be high in SETUP state"
    assert dut.apb_paddr_o.value == expected_addr, f"APB address should be {hex(expected_addr)} in SETUP state"
    assert dut.apb_pwdata_o.value == expected_data, f"APB data should be {hex(expected_data)} in SETUP state"       

    
    dut.apb_pready_i.value = 0  # Deasserting ready signal
    latency_rdy = 0
    while dut.apb_penable_o.value == 1:
        await RisingEdge(dut.clk)
        latency_rdy += 1 

    # Check if APB signals are deasserted after the transaction
    assert latency_rdy == 1, f"Latency from `apb_pready_i` to `apb_sel_o` and `apb_penable_o` should be 1 cycle, but got {latency_rdy}"
    assert dut.apb_psel_o.value == 0, "APB select should be deasserted after ACCESS"
    assert dut.apb_penable_o.value == 0, "APB enable should be deasserted after ACCESS" 
    assert dut.apb_pwrite_o.value == 0, "APB write signal should be deasserted after ACCESS state"   
    assert dut.apb_paddr_o.value == 0, f"APB address should be 0 after ACCESS"
    assert dut.apb_pwdata_o.value == 0, f"APB data should be 0 after ACCESS" 

async def test_timeout(dut, select_signal, expected_addr, expected_data):

    # Apply stimulus for the selected signal
    select_signal.value = 1
    dut.apb_pready_i.value = 0  # Initially APB is not ready

    # Wait for a few clock cycles to simulate state transitions
    await RisingEdge(dut.clk)
    select_signal.value = 0 

    # latency count
    latency_sel = 0
    while (dut.apb_psel_o.value == 0) and (dut.apb_pwrite_o.value == 0):
        await RisingEdge(dut.clk)
        latency_sel += 1

    # SETUP state checks
    assert latency_sel == 1, f"Latency from `apb_psel_o` should be 1 cycle, but got {latency_sel}"    
    assert dut.apb_psel_o.value == 1, "APB select signal should be high in SETUP state"
    assert dut.apb_penable_o.value == 0, "APB enable signal should be deasserted in ACCESS state"
    assert dut.apb_pwrite_o.value == 1, "APB write signal should be high in SETUP state"
    assert dut.apb_paddr_o.value == expected_addr, f"APB address should be {hex(expected_addr)} in SETUP state"
    assert dut.apb_pwdata_o.value == expected_data, f"APB data should be {hex(expected_data)} in SETUP state"
 
    # latency count
    latency_enable = 0
    while dut.apb_penable_o.value == 0:
        await RisingEdge(dut.clk)
        latency_enable += 1

    # ACCESS state checks
    # Validate that `apb_penable_o` is asserted exactly 1 clock cycle after `apb_psel_o`
    await RisingEdge(dut.clk)
    assert latency_enable == 1, f"Latency from `apb_psel_o` to `apb_penable_o` should be 1 cycle, but got {latency_enable}"
    assert dut.apb_penable_o.value == 1, "APB enable signal should be high in ACCESS state"
    assert dut.apb_psel_o.value == 1, "APB select signal should be stable in ACCESS state"
    assert dut.apb_pwrite_o.value == 1, "APB write signal should be stable in ACCESS state"
    assert dut.apb_paddr_o.value == expected_addr, f"APB address should be {hex(expected_addr)} in ACCESS state"
    assert dut.apb_pwdata_o.value == expected_data, f"APB data should be {hex(expected_data)} in ACCESS state"
    
    # Wait for the timeout period 
    latency_disable = 0
    while dut.apb_penable_o.value == 1:
        await RisingEdge(dut.clk)
        latency_disable += 1

    # Check if the controller has returned to IDLE after timeout
    assert latency_disable == 15, f"Design should return to IDLE after 15 cycles, but it happened after {latency_disable} cycles"
    assert dut.apb_psel_o.value == 0, "APB select should be deasserted after ACCESS"
    assert dut.apb_penable_o.value == 0, "APB enable should be deasserted after ACCESS" 
    assert dut.apb_pwrite_o.value == 0, "APB write signal should be deasserted after ACCESS state"   
    assert dut.apb_paddr_o.value == 0, f"APB address should be 0 after ACCESS"
    assert dut.apb_pwdata_o.value == 0, f"APB data should be 0 after ACCESS" 

async def check_priority(dut, select_signals, expected_addr, expected_data, description):
    await RisingEdge(dut.clk)
    # Apply select signals simultaneously
    for signal in select_signals:
        signal.value = 1

    # Wait for one clock cycle to propagate select signals
    await RisingEdge(dut.clk)

    # Deassert all select signals
    for signal in select_signals:
        signal.value = 0

    while (dut.apb_psel_o.value == 0) and (dut.apb_pwrite_o.value == 0):
        await RisingEdge(dut.clk)

    dut.apb_pready_i.value = 1
    await RisingEdge(dut.clk)
    dut.apb_pready_i.value = 0
    # Verify the selected address and data
    assert dut.apb_paddr_o.value == expected_addr, (
        f"{description}: Expected address {hex(expected_addr)}, "
        f"but got {hex(int(dut.apb_paddr_o.value))}"
    )
    assert dut.apb_pwdata_o.value == expected_data, (
        f"{description}: Expected data {hex(expected_data)}, "
        f"but got {hex(int(dut.apb_pwdata_o.value))}"
    )
    await RisingEdge(dut.clk)
