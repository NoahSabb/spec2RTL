import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
import harness_library as hrs_lb
import random

# ----------------------------------------
# - Test Advanced Decimator with Adaptive Peak Detection
# ----------------------------------------

@cocotb.test()
async def test_advanced_decimator_with_adaptive_peak_detection_0(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())

    # Debug mode
    debug = 0

    # Retrieve parameters from the DUT
    DATA_WIDTH = int(dut.DATA_WIDTH.value)
    DEC_FACTOR = int(dut.DEC_FACTOR.value)
    N = int(dut.N.value)

    # Initialize DUT
    await hrs_lb.dut_init(dut)

    # Apply reset
    await hrs_lb.reset_dut(dut.reset)

    # Test parameters
    num_samples = 10  # Number of sets of input data to test
    max_value = (1 << (DATA_WIDTH - 1)) - 1  # Max positive value for signed DATA_WIDTH
    min_value = -(1 << (DATA_WIDTH - 1))    # Min negative value for signed DATA_WIDTH

    for test_case in range(num_samples):
        # Generate random input values for the decimator
        input_values = [random.randint(min_value, max_value) for _ in range(N)]
        packed_signal = await hrs_lb.pack_signal(input_values, DATA_WIDTH)
        
        dec_model = []
        input_values = input_values[::-1]
        for i in range(N // DEC_FACTOR):
            dec_model.append(input_values[i * DEC_FACTOR])
        dec_model = dec_model[::-1]
        peak_model = max(dec_model)

        valid_in = random.randint(0,1)
        # Apply input to DUT
        dut.data_in.value = packed_signal
        dut.valid_in.value = valid_in

        if debug:
            cocotb.log.info(f"[DEBUG] Test Case {test_case + 1}")
            cocotb.log.info(f"[DEBUG] Input Values: {input_values}")
            cocotb.log.info(f"[DEBUG] Packed Signal: {packed_signal:#0{N * DATA_WIDTH // 4 + 2}x}")
            

        # Wait for one clock cycle
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)

        # Retrieve outputs
        output_data = await hrs_lb.extract_signed(dut.data_out, DATA_WIDTH, N//DEC_FACTOR)
        peak_value = dut.peak_value.value.signed_integer

        # Debug output
        if debug:
            for i in range(N):
               cocotb.log.info(f"[DEBUG] In data 2D: {dut.data_vec_in.value[i].signed_integer}")
            cocotb.log.info(f"[DEBUG] Output Data: {output_data}")
            cocotb.log.info(f"[DEBUG] Model Data: {dec_model}")
            cocotb.log.info(f"[DEBUG] Peak Value: {peak_value}")
            cocotb.log.info(f"[DEBUG] Model Peak: {peak_model}")

        # Assertions (replace with specific checks for your DUT logic)
        assert dut.valid_out.value == valid_in, f"[ERROR] DUT did not assert valid_out on Test Case {test_case + 1}"
        if valid_in == 1:
          assert output_data == dec_model, f"[ERROR] DUT output data does not match model output data on Test Case {test_case + 1}"
          assert peak_value == peak_model, f"[ERROR] DUT peak value does not match model peak value on Test Case {test_case + 1}"
            