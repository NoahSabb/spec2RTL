import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ClockCycles, Timer
import random
import time
import harness_library as hrs_lb
from harness_library import ExReqDriver, dmemIFDriver

# Place holder for coverage

def execute_sb_fn(dut,type_i, wdata, addr_base, addr_offset):
   pass
   #dut._log.info(f"Execute unit request -- type:{hex(type_i)}, write_data = {hex(wdata)}, addr: {hex(addr_base + addr_offset)}")

@cocotb.test()
async def test_load_store_unit(dut): 
   # Start clock
   dut_clock_period = random.randint(2, 20) # starting from 2, t high must be integer! 
   print(f"Clk period is {dut_clock_period}")
   DUT_CLK = Clock(dut.clk, dut_clock_period, 'ns', period_high=(dut_clock_period+1)//2 if dut_clock_period%2 else dut_clock_period//2)
   await cocotb.start(DUT_CLK.start())
   dut.clk._log.info(f"clk STARTED")

   await hrs_lb.dut_init(dut)

   # Apply reset 
   await hrs_lb.reset_dut(dut.rst_n, dut_clock_period)

   for i in range(2):
      await RisingEdge(dut.clk)

   # Ensure  outputs reset value 

   # The Execution Stage Interface is signaled as ready for new requests.
   assert dut.ex_if_ready_o.value == 1, f"The Execution Stage Interface should be signaled as ready for new requests (ex_if_ready_o = 0x1): {dut.ex_if_ready_o.value}"
   
   # No requests are sent to data memory.
   assert dut.dmem_req_o.value == 0, f"ُShould be No requests are sent to data memory (dmem_req_o = 0x0). {dut.dmem_req_o.value}"
   
   # No valid data is provided to the writeback stage.
   assert dut.wb_if_rvalid_o.value == 0, f"Should be No valid data  provided to the writeback stage (wb_if_rvalid_o = 0x0). {dut.wb_if_rvalid_o.value}"

   
   await FallingEdge(dut.clk)
   
   dmemIFDriver(dut,'dmem', dut.clk)
   execute_if_driver = ExReqDriver(dut,'ex_if',dut.clk,execute_sb_fn)

   for i in range(500):
      wdata = random.randint(0, 2**32) # 32 bit word data
      addr_base = random.randint(0,2**6)
      addr_off = random.randint(0,2**6) # Limiting address space to 7 bit (MemoryModel representation limit)
      type = random.randint(0,2) # TYPE: can be 0x0, 0x1, 0x2
      Test_Vec = (type, wdata, addr_base, addr_off)
      # Drive Write operation
      await execute_if_driver.write_req(Test_Vec)
      
      # Read the written value
      await execute_if_driver.read_req(Test_Vec)

    



