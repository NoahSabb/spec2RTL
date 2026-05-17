import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

async def reset_dut(dut):
    """Reset the DUT"""
    dut.i_rst_n.value =0
    dut.i_addr.value =0
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =0
    dut.i_capture_pulse.value =0

    await FallingEdge(dut.i_capture_pulse)
    dut.i_rst_n.value = 1
    await RisingEdge(dut.i_capture_pulse)


@cocotb.test()
async def test_secure_read_write_register_bank(dut):  # dut will be the object for RTL top.
   

    cocotb.start_soon(Clock(dut.i_capture_pulse, 10, unit='ns').start())  # timeperiod= 10ns
    # Reset the DUT
    await reset_dut(dut)

    
    await FallingEdge(dut.i_capture_pulse)  #stage one unlock
    dut.i_addr.value =0
    dut.i_data_in.value =171
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) #stage two unlock
    dut.i_addr.value =1
    dut.i_data_in.value =205
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) #unlocked, at address 2, data 2 witten
    dut.i_addr.value =2
    dut.i_data_in.value =2
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) # at address 3, data 3 witte
    dut.i_addr.value =3
    dut.i_data_in.value =3
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) #read at address 2
    dut.i_addr.value =2
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion at address 2, and read at address 3
    assert dut.o_data_out.value==2, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =3
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion at address 3, and locks the bank
    assert dut.o_data_out.value==3, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =0
    dut.i_data_in.value =170
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) #locked, reading at address 2. 
    dut.i_addr.value =2
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion at address 2 locked, and read at address 3
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =3
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion at address 3 locked, and step 1 of unlock
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =0
    dut.i_data_in.value =171
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) #read at address 2, locked
    dut.i_addr.value =2
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion at address 2 locked, and read at address 3
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =3
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion at address 3 locked, and step 2 of unlock
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =1
    dut.i_data_in.value =205
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) # read address 2, locked. unlock series broken.
    dut.i_addr.value =2
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion at address 2 locked, and read at address 3
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =3
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion at address 3 locked, and step 2 of unlock
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =0
    dut.i_data_in.value =171
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) #stage two unlock
    dut.i_addr.value =1
    dut.i_data_in.value =205
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) #unlocked, read at address 2.
    dut.i_addr.value =2
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion at address 2, and read at address 0
    assert dut.o_data_out.value==2, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =0
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion at address 0, and read at address 1
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =1
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion at address 1, and incorrect unlock 1
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    dut.i_addr.value =0
    dut.i_data_in.value =170
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) #in correct stage two unlock
    dut.i_addr.value =1
    dut.i_data_in.value =200
    dut.i_read_write_enable.value =0
    await FallingEdge(dut.i_capture_pulse) #locked, read at address 2.
    dut.i_addr.value =2
    dut.i_data_in.value =0
    dut.i_read_write_enable.value =1
    await FallingEdge(dut.i_capture_pulse) #assertion at address 2
    assert dut.o_data_out.value==0, f"output should not be {dut.o_data_out.value}"
    