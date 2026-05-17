import cocotb
from cocotb.triggers import Timer

# Function to compute the expected output
def expected_outputs(i_A, i_B, i_Cin):
    o_generate = i_A & i_B
    o_propagate = i_A | i_B
    o_Cout = o_generate | (o_propagate & i_Cin)
    return o_generate, o_propagate, o_Cout

@cocotb.test()
async def test_gp_test(dut):
    """Test GP module for all possible input combinations."""
    
    for i_A in range(2):
        for i_B in range(2):
            for i_Cin in range(2):
                
                # Apply the inputs
                dut.i_A.value = i_A
                dut.i_B.value = i_B
                dut.i_Cin.value = i_Cin
                
                # Wait for a short time to simulate signal propagation
                await Timer(2, unit='ns')
                
                # Get the output values from DUT
                o_generate = int(dut.o_generate.value)
                o_propagate = int(dut.o_propagate.value)
                o_Cout = int(dut.o_Cout.value)
                
                # Get the expected values
                expected_generate, expected_propagate, expected_Cout = expected_outputs(i_A, i_B, i_Cin)
                
                # Compare outputs with expected values
                assert o_generate == expected_generate, f"Mismatch for A={i_A}, B={i_B}, Cin={i_Cin}: o_generate={o_generate}, expected={expected_generate}"
                assert o_propagate == expected_propagate, f"Mismatch for A={i_A}, B={i_B}, Cin={i_Cin}: o_propagate={o_propagate}, expected={expected_propagate}"
                assert o_Cout == expected_Cout, f"Mismatch for A={i_A}, B={i_B}, Cin={i_Cin}: o_Cout={o_Cout}, expected={expected_Cout}"
                
                dut._log.info(f"Test passed for A={i_A}, B={i_B}, Cin={i_Cin}.")
