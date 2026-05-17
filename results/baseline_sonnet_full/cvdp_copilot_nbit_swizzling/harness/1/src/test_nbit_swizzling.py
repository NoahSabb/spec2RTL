
import cocotb
from cocotb.triggers import Timer
import random

# Function to generate random data based on DATA_WIDTH

# Testbench function to test different scenarios
@cocotb.test()
async def test_nbit_sizling(dut):
    """ Test the nbit_sizling module """
    data_wd = int(dut.DATA_WIDTH.value)
    for i in range(20):
        # Generate random input data and selection signal
        data_in = random.randint(0,(2**data_wd)-1)
        sel = random.randint(0,3)  # sel is 2-bit wide, so choose between 0 to 3
        print(f"DATA_WIDTH ={data_wd}")
        # Apply inputs to the DUT
        dut.data_in.value = data_in
        dut.sel.value = sel
        
        await Timer(10, unit='ns')

        
        # Run the actual result calculation in Python for comparison
        expected_data_out = reverse_data(data_in, sel, data_wd)
        print(f"Checking operation for sel={sel}:: data_in = {int(dut.data_in.value)},data_in = {(dut.data_in.value)},, expected_data_out = {expected_data_out}, data_out = {int(dut.data_out.value)}")
        print(f"Checking operation in binary for sel={sel}:: data_in_bin = {dut.data_in.value}, expected_data_out = {bin(expected_data_out)}, data_out = {dut.data_out.value}")
       
        # Compare the DUT's output with expected value
        assert dut.data_out.value == expected_data_out, f"Test failed with data_in={data_in}, sel={sel}, expected={expected_data_out}, but got={dut.data_out.value}"

# Helper function to perform the data reversal based on sel
def reverse_data(data_in, sel, data_wd):
    data_in_bits = f'{data_in:0{data_wd}b}'  # Convert input to binary string of size DATA_WIDTH
    if sel == 0:
        # Reverse entire data
        return int(data_in_bits[::-1], 2)
    elif sel == 1:
        # Reverse two halves
        half_width = data_wd // 2
        first_half = data_in_bits[:half_width][::-1]
        second_half = data_in_bits[half_width:][::-1]
        return int(first_half + second_half, 2)
    elif sel == 2:
        # Reverse four sets
        quarter_width = data_wd // 4
        first_set = data_in_bits[:quarter_width][::-1]
        second_set = data_in_bits[quarter_width:2*quarter_width][::-1]
        third_set = data_in_bits[2*quarter_width:3*quarter_width][::-1]
        fourth_set = data_in_bits[3*quarter_width:][::-1]
        return int(first_set + second_set + third_set + fourth_set, 2)
    elif sel == 3:
        # Reverse eight sets
        eighth_width = data_wd // 8
        sets = [data_in_bits[i*eighth_width:(i+1)*eighth_width][::-1] for i in range(8)]
        return int(''.join(sets), 2)
    else:
        return data_in  # Default, just return the input data as-is


