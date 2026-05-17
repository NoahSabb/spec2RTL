import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random

@cocotb.test()
async def test_decode_firstbit(dut):
    """Testbench for olo_base_decode_firstbit module."""

    # Parameters
    CLK_PERIOD = 10  # Clock period in nanoseconds

    # Create a clock on dut.Clk
    cocotb.start_soon(Clock(dut.Clk, CLK_PERIOD, unit='ns', period_high=(CLK_PERIOD+1)//2 if CLK_PERIOD%2 else CLK_PERIOD//2).start())

    # Initialize inputs
    dut.Rst.value = 1
    dut.In_Data.value = 0
    dut.In_Valid.value = 0

    # Wait for a few clock cycles
    await Timer(CLK_PERIOD * 5, unit='ns')
    dut.Rst.value = 0

    # Define test vectors
    test_vectors = [
        0x00000000,  # No bits set
        0x00000001,  # First bit set
        0x00000002,  # Second bit set
        0x80000000,  # Last bit set
        0x00010000,  # Middle bit set
        0xFFFFFFFF,  # All bits set
        0xFFFFFFFE,  # All but first bit set
        0x7FFFFFFF,  # All but last bit set
        0x00008000,  # Random bit set
        0x00000008,  # Another random bit set
        0xAAAAAAAA,  # Alternating bits starting with '1'
        0x55555555,  # Alternating bits starting with '0'
        0x0000FFFF,  # Lower half bits set
        0xFFFF0000,  # Upper half bits set
        0x00000010,  # Single bit set at position 4
        0x00020000,  # Single bit set at position 17
        0x00000004,  # Single bit set at position 2
        0x40000000,  # Single bit set at position 30
        0x00800000,  # Single bit set at position 23
        0x00400000,  # Single bit set at position 22
        0x00000400,  # Single bit set at position 10
    ]

    # Apply predefined test vectors
    for data_in in test_vectors:
        await apply_test_vector(dut, data_in, CLK_PERIOD)

    # Apply random test vectors
    for _ in range(20):  # Increased from 10 to 20 random tests
        random_data = random.getrandbits(len(dut.In_Data))
        await apply_test_vector(dut, random_data, CLK_PERIOD)

async def apply_test_vector(dut, data_in, CLK_PERIOD):
    """Apply a single test vector to the DUT."""

    # Apply input data and valid signal
    dut.In_Data.value = data_in
    dut.In_Valid.value = 1

    await RisingEdge(dut.Clk)
    dut.In_Valid.value = 0

    # Wait for the output to become valid
    while True:
        await RisingEdge(dut.Clk)
        if dut.Out_Valid.value:
            break

    # Read output values
    out_firstbit = int(dut.Out_FirstBit.value)
    out_found = int(dut.Out_Found.value)

    # Calculate expected results
    expected_index = find_first_set_bit(data_in)
    expected_found = 1 if expected_index != -1 else 0

    # Compare DUT output with expected values
    if out_found != expected_found:
        dut._log.error(f"Out_Found mismatch: Input={hex(data_in)}, Expected {expected_found}, Got {out_found}")
        raise AssertionError("Out_Found signal mismatch")

    if expected_found:
        if out_firstbit != expected_index:
            dut._log.error(f"Out_FirstBit mismatch: Input={hex(data_in)}, Expected Index={expected_index}, Got {out_firstbit}")
            raise AssertionError("Out_FirstBit signal mismatch")
        else:
            dut._log.info(f"PASS: Input={hex(data_in)}, Expected Index={expected_index}, Output Index={out_firstbit}")
    else:
        dut._log.info(f"PASS: Input={hex(data_in)}, No bits set as expected")

def find_first_set_bit(data_in):
    """Find the index of the first set bit in data_in."""
    for idx in range(data_in.bit_length()):
        if (data_in >> idx) & 1:
            return idx
    return -1  # Return -1 if no bits are set

# Pytest wrapper
import os
from cocotb_tools.runner import get_runner
import pytest
import pickle


@pytest.mark.parametrize("in_width_g", [8, 16, 32])
@pytest.mark.parametrize("output_format_g", [0, 1])
def test_decode_firstbit_runner(in_width_g, output_format_g):
    """Pytest wrapper to run the cocotb test with different parameters."""

    dut_path = os.path.abspath("cvdp_copilot_decode_firstbit.v")
    
    # Define the module name (this file without extension)
    module_name = os.path.splitext(os.path.basename(__file__))[0]
    
    sim_build = os.path.abspath(f"sim_build_{in_width_g}_{output_format_g}")
    
    parameters = {}
    parameters['InWidth_g'] = in_width_g
    parameters['OutputFormat_g'] = output_format_g

    # Convert parameters to dictionary required by cocotb-test
    extra_env = {f'PARAM_{k}': str(v) for k, v in parameters.items()}

    runner = get_runner(sim)
    runner.build(
        verilog_sources=[dut_path],
        toplevel="cvdp_copilot_decode_firstbit",
        module=module_name,  # Name of the Python test module (without .py)
        parameters=parameters,
        sim_build=sim_build,
        extra_env=extra_env,
    )
    runner.test(hdl_toplevel=toplevel, test_module=module, waves=True)