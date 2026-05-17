import os
from cocotb_tools.runner import get_runner
import random
import pytest
from datetime import datetime  # Import datetime for timestamp
import harness_library as hrs_lb

# Fetch environment variables
verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")
wave            = bool(os.getenv("WAVE"))

# The main runner function to trigger matrix multiplication tests
# This function prepares the simulation environment, sets parameters, and runs the test
def runner(ROW_A: int=4, COL_A: int=4, ROW_B: int=4, COL_B: int=4, INPUT_DATA_WIDTH: int=8,matrix_a: int=0, matrix_b: int=0, input_provided: int=0):
  # Define simulation parameters
  parameter = {
    "ROW_A": ROW_A,
    "COL_A": COL_A,
    "ROW_B": ROW_B,
    "COL_B": COL_B,
    "INPUT_DATA_WIDTH": INPUT_DATA_WIDTH,
  }

  # Prepare plusargs, which are passed to the DUT
  plusargs = [
    f'+input_provided={input_provided}',
    f'+matrix_a={hrs_lb.convert_2d_to_flat(matrix_a, INPUT_DATA_WIDTH)}',
    f'+matrix_b={hrs_lb.convert_2d_to_flat(matrix_b, INPUT_DATA_WIDTH)}'
  ]

  # Set up the runner for the simulator
  runner = get_runner(sim)
  runner.build(
    sources=verilog_sources,
    hdl_toplevel=toplevel,
    # Arguments
    parameters=parameter,
    always=True,
    clean=True,
    verbose=True,
    timescale=("1ns", "1ns"),
    log_file="sim.log")
  runner.test(hdl_toplevel=toplevel, test_module=module, waves=wave, plusargs=plusargs)

  # Save the VCD (waveform) after running the test with a unique timestamp
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Unique timestamp
  test_name = f"{toplevel}_ROW_A_{ROW_A}_COL_A_{COL_A}_ROW_B_{ROW_B}_COL_B_{COL_B}_WIDTH_{INPUT_DATA_WIDTH}_{timestamp}"
  # hrs_lb.save_vcd(wave, toplevel, test_name)


# Basic Matrix Multiplication Tests (static values)
# Parametrized tests for static matrix multiplication cases
@pytest.mark.parametrize("ROW_A, COL_A, ROW_B, COL_B, INPUT_DATA_WIDTH, matrix_a, matrix_b", [
  # Basic 2x2 test
  (2, 2, 2, 2, 8, [[1,  2], [ 3,  4]], [[ 5,  6], [ 7,  8]]),
  (2, 2, 2, 2, 8, [[9, 10], [11, 12]], [[13, 14], [15, 16]]),
  (2, 2, 2, 2, 8, [[0,  0], [ 1,  1]], [[ 1,  1], [ 1,  1]]),
  # Basic 3x3 test
  (3, 3, 3, 3, 8, [[1, 2, 3], [4, 5, 6], [7, 8,  9]], [[9, 8,  7], [ 6, 5, 4], [3, 2, 1]]),
  (3, 3, 3, 3, 8, [[2, 3, 4], [5, 6, 7], [8, 9, 10]], [[1, 2,  3], [ 4, 5, 6], [7, 8, 9]]),
  (3, 3, 3, 3, 8, [[0, 1, 1], [1, 0, 0], [1, 1,  1]], [[7, 5, 14], [14, 2, 2], [3, 3, 3]]),
  # Basic 4x4 test
  (4, 4, 4, 4, 8, [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 0]], [[1, 1, 1, 1], [2, 2, 2, 2], [3, 3, 3, 3], [4, 4, 4, 4]]),
  (4, 4, 4, 4, 8, [[1, 0, 0, 1], [0, 1, 1, 0], [1,  0,  1,  1], [ 1,  1,  1, 1]], [[1, 1, 1, 1], [1, 0, 1, 1], [0, 1, 0, 1], [1, 1, 0, 0]]),
  (4, 4, 4, 4, 8, [[2, 2, 2, 2], [2, 2, 2, 2], [2,  2,  2,  2], [ 2,  2,  2, 2]], [[3, 3, 3, 3], [3, 3, 3, 3], [3, 3, 3, 3], [3, 3, 3, 3]]),
  # Identity Matrix test
  (2, 2, 2, 2, 8, [[1,  2], [ 3,  4]], [[ 1,  0], [ 0,  1]]),
  (3, 3, 3, 3, 8, [[1, 2, 3], [4, 5, 6], [7, 8,  9]], [[1, 0, 0], [0, 1, 0], [0, 0, 1]]),
  (4, 4, 4, 4, 8, [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 0]], [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]),
  # Zero Matrix test
  (2, 2, 2, 2, 8, [[1, 2], [3, 4]], [[0, 0], [0, 0]]),
  (3, 3, 3, 3, 8, [[0, 0, 0], [0, 0, 0], [0, 0, 0]], [[0, 0, 0], [0, 0, 0], [0, 0, 0]]),
  (4, 4, 4, 4, 8, [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 0]], [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]),
  # Max Value Overflow test
  (2, 2, 2, 2, 4, [[15, 15], [15, 15]], [[15, 15], [15, 15]]),
  (2, 2, 2, 2, 8, [[255, 255], [255, 255]], [[255, 255], [255, 255]]),
  (2, 2, 2, 2, 16, [[65535, 65535], [65535, 65535]], [[65535, 65535], [65535, 65535]]),
  # Single Element test
  (1, 1, 1, 1, 8, [[  5]], [[ 10]]),
  (1, 1, 1, 1, 8, [[255]], [[  1]]),
  (1, 1, 1, 1, 8, [[  1]], [[255]]),
  # Non-square test
  (2, 3, 3, 2, 8, [[2, 4, 6], [1, 3, 5]], [[7, 8], [9, 10], [11, 12]]),
  (3, 4, 4, 2, 8, [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], [[1, 2], [3, 4], [5, 6], [7, 8]]),
  (4, 3, 3, 5, 8, [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]], [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10], [11, 12, 13, 14, 15]]),
])
def test_matrix_multiplication(ROW_A, COL_A, ROW_B, COL_B, INPUT_DATA_WIDTH, matrix_a, matrix_b):
  # Run the test with input_provided=1, meaning static input matrices are passed
  runner(ROW_A=ROW_A, COL_A=COL_A, ROW_B=ROW_B, COL_B=COL_B, INPUT_DATA_WIDTH=INPUT_DATA_WIDTH, matrix_a=matrix_a, matrix_b=matrix_b, input_provided=1)


# Random Matrix Multiplication Tests
# Generate random matrix dimensions and values, and run the test
@pytest.mark.parametrize("random_test", range(10))
def test_random_matrix_multiplication(random_test):
  # Generate random dimensions for the matrices
  ROW_A = random.randint(1, 8)
  COL_A = random.randint(1, 8)
  ROW_B = COL_A  # To make matrix multiplication valid
  COL_B = random.randint(1, 8)
  INPUT_DATA_WIDTH = random.randint(1, 16)

  # Populate the matrices with random values
  matrix_a = hrs_lb.populate_matrix(ROW_A, COL_A, INPUT_DATA_WIDTH)
  matrix_b = hrs_lb.populate_matrix(ROW_B, COL_B, INPUT_DATA_WIDTH)

  # Run the test with input_provided=1, meaning input matrices are passed  
  runner(ROW_A=ROW_A, COL_A=COL_A, ROW_B=ROW_B, COL_B=COL_B, INPUT_DATA_WIDTH=INPUT_DATA_WIDTH, matrix_a=matrix_a, matrix_b=matrix_b, input_provided=1)

# Input Stream Matrix Multiplication Tests (Test with multiple set of inputs)
# These tests will run with input_provided=0, meaning matrices are generated on the fly
@pytest.mark.parametrize("ROW_A, COL_A, ROW_B, COL_B, INPUT_DATA_WIDTH", [
  # Basic 2x2 test without inputs
  (2, 2, 2, 2, 8),
  # Basic 3x3 test without inputs
  (3, 3, 3, 3, 8),
])
def test_matrix_multiplication_without_inputs(ROW_A, COL_A, ROW_B, COL_B, INPUT_DATA_WIDTH):
  # Run the test with input_provided=0, meaning matrices will be generated dynamically
  runner(ROW_A=ROW_A, COL_A=COL_A, ROW_B=ROW_B, COL_B=COL_B, INPUT_DATA_WIDTH=INPUT_DATA_WIDTH, matrix_a=[], matrix_b=[], input_provided=0)