import cocotb
from cocotb.triggers import Timer
import harness_library as hrs_lb

@cocotb.test()
async def test_qam16_demapper_interpolated(dut):
    # Parameters from the DUT
    N = int(dut.N.value)  # Number of mapped symbols
    IN_WIDTH = int(dut.IN_WIDTH.value)
    threshold = int(dut.ERROR_THRESHOLD.value)

    # Debug mode
    debug = 0

    I_values, Q_values = hrs_lb.generate_samples(N)
    mapped_indices = []
    for i in range(N // 2):
        mapped_indices.extend([3 * i, 3 * i + 2])  # First mapped and second mapped
    
    # Indices for interpolated values
    interp_indices = [3 * i + 1 for i in range(N // 2)]  # Interpolated indices are always the middle (3*i + 1)
    # Extract mapped values
    mapped_I = [I_values[idx] for idx in mapped_indices]
    mapped_Q = [Q_values[idx] for idx in mapped_indices]    

    # Extract interpolated values
    interp_I = [I_values[idx] for idx in interp_indices]
    interp_Q = [Q_values[idx] for idx in interp_indices]
    
    error_flag = 0
    for i in range(len(interp_I)):
           # Calculate averages of mapped pairs
           avg_I = (mapped_I[2 * i] + mapped_I[2 * i + 1]) / 2
           avg_Q = (mapped_Q[2 * i] + mapped_Q[2 * i + 1]) / 2
           cocotb.log.info(f'avg I= {avg_I}')
           cocotb.log.info(f'avg Q= {avg_Q}')
           # Compare with interpolated values
           if abs(avg_I - interp_I[i]) > threshold or abs(avg_Q - interp_Q[i]) > threshold:
               error_flag = 1

    bit_vec = hrs_lb.map_to_bits_vector(mapped_I, mapped_Q, N)
    bit_stream ="".join(str(bit) for bit in bit_vec)
    packed_I = hrs_lb.pack_signal(I_values, IN_WIDTH)
    packed_Q = hrs_lb.pack_signal(Q_values, IN_WIDTH)    
    dut.I.value = packed_I
    dut.Q.value = packed_Q

    await Timer(1, unit="ns")
    assert dut.bits.value == bit_stream
    assert dut.error_flag.value == error_flag

    if debug:
      cocotb.log.info(f"I_values: {I_values}")
      cocotb.log.info(f"Q_values: {Q_values}")
      cocotb.log.info(f"interp_I: {interp_I}")
      cocotb.log.info(f"interp_Q: {interp_Q}")
      cocotb.log.info(f'error flag     = {error_flag}')
      cocotb.log.info(f'error_flag dut = {dut.error_flag.value}')          
      cocotb.log.info(f"Packed I: {bin(packed_I)}")
      cocotb.log.info(f"Packed Q: {bin(packed_Q)}")    
      cocotb.log.info(f"DUT I_values: {dut.I.value}")
      cocotb.log.info(f"DUT Q_values: {dut.Q.value}")
      cocotb.log.info(f'bits dut = {dut.bits.value}')
      cocotb.log.info(f'bit model = {(bit_stream)}')
