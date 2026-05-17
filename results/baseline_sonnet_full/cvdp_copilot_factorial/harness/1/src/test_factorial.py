import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.regression import TestFactory
import random


# Function to calculate the expected factorial value
def reference_factorial(num):
  if num == 0 or num == 1:
    return 1
  fact = 1
  for i in range(2, num + 1):
    fact *= i
  return fact

async def initialize_dut(dut):
  cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
  dut.arst_n.value = 0
  # dut.num_in.value = 0
  await RisingEdge(dut.clk)
  dut.arst_n.value = 1
  await RisingEdge(dut.clk)

@cocotb.test()
async def test_factorial(dut):
  match = 0
  mismatch = 0
  await initialize_dut(dut)
  
  # Randomize the number of test cases
  NUM_TESTS = 100  # Max number of tests to run
  test_count = 0   # Number of random test casesi
  # for i in range(NUM_TESTS+1):
  while (test_count<NUM_TESTS):
    # Randomize input value (8-bit input)
    random_input = random.randint(0, 15)  # Limiting to 12 due to large factorial values
    
    # Apply input to DUT
    if (dut.busy.value!=1 and dut.start.value!=1):
      dut.num_in.value = random_input
      dut.start.value  = 1
      expected_fact = reference_factorial(random_input)
    else:
      dut.num_in.value = 0
      dut.start.value  = 0

    await RisingEdge(dut.clk)
    
    # Get the DUT result
    if (dut.done.value==1):
      actual_fact = dut.fact.value
    
      if (actual_fact == expected_fact):
        print(f"Test {test_count} Passed: result = {int(actual_fact)} matches reference {expected_fact}")
        match = match+1
      else:
        print(f"Test {test_count} Failed: result = {int(actual_fact)} do not matches reference {expected_fact}")
        mismatch = mismatch+1
      test_count = test_count+1

  if (mismatch==0):
    print(f"All {NUM_TESTS} test cases PASSED successfully.")
  else: 
    print(f"Matched: {match} , Mismatched {mismatch} - TEST FAILED.")
