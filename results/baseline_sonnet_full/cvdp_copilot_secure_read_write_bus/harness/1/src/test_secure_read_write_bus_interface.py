import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

async def reset_dut(dut):
    """Reset the DUT"""
    dut.i_reset_bar.value =0
    dut.i_addr.value =0
    dut.i_data_in.value =0
    dut.i_key_in.value =0
    dut.i_read_write_enable.value =0
    dut.i_capture_pulse.value =0

    await FallingEdge(dut.i_capture_pulse)
    dut.i_reset_bar.value = 1
    await RisingEdge(dut.i_capture_pulse)


@cocotb.test()
async def test_secure_read_write_bus_interface(dut):  # dut will be the object for RTL top.
   

    cocotb.start_soon(Clock(dut.i_capture_pulse, 10, unit='ns').start())  # timeperiod= 10ns
    # Reset the DUT
    await reset_dut(dut)

    
    await FallingEdge(dut.i_capture_pulse)  #writing addr 1 with data 1, with correct key.
    dut.i_addr.value =1
    dut.i_data_in.value =1
    dut.i_key_in.value =170
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) #writing addr 2 with data 2, with correct key.
    assert dut.o_error.value==0, f"output should not be {dut.o_error.value}"
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =2
    dut.i_data_in.value =2
    dut.i_key_in.value =170
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) #reading addr 1 with correct key.
    assert dut.o_error.value==0, f"output should not be {dut.o_error.value}"
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =1
    dut.i_data_in.value =0
    dut.i_key_in.value =170
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion of addr 1.reading addr 2 with correct key.
    assert dut.o_data_out.value==1, f"output should not be {dut.o_data_out.value}"
    assert dut.o_error.value==0, f"output should not be {dut.o_error.value}"
    dut.i_addr.value =2
    dut.i_data_in.value =0
    dut.i_key_in.value =170
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion of addr 2.reading addr 2 with incorrect key.
    assert dut.o_data_out.value==2, f"output should not be {dut.o_data_out.value}"
    assert dut.o_error.value==0, f"output should not be {dut.o_error.value}"
    dut.i_addr.value =2
    dut.i_data_in.value =0
    dut.i_key_in.value =172
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion of addr 2. #writing addr 1 with data 4, with incorrect key.
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    assert dut.o_error.value==1, f"output should not be {dut.o_error.value}"
    dut.i_addr.value =1
    dut.i_data_in.value =4
    dut.i_key_in.value =173
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) #reading add 1, with correct key.
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    assert dut.o_error.value==1, f"output should not be {dut.o_error.value}"
    dut.i_addr.value =1
    dut.i_data_in.value =0
    dut.i_key_in.value =170
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion of addr 1. data should not change.reading addr 2 with correct key.
    assert dut.o_data_out.value==1, f"output should not be {dut.o_data_out.value}"
    assert dut.o_error.value==0, f"output should not be {dut.o_error.value}"