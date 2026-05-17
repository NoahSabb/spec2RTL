import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ClockCycles, Timer
import random
import harness_library as hrs_lb

# ----------------------------------------
# - Matrix Multiplication Test
# ----------------------------------------

@cocotb.test()
async def verify_matrix_multiplication(dut):
  """Verify matrix multiplication outputs"""

  # Initialize DUT inputs
  await hrs_lb.dut_init(dut)

  # Apply a small delay
  await Timer(2, unit='ns')

  # Retrieve the rows and columns for matrices
  rows_a = int(dut.ROW_A.value)
  cols_a = int(dut.COL_A.value)
  rows_b = int(dut.ROW_B.value)
  cols_b = int(dut.COL_B.value)
  output_width = int(dut.OUTPUT_DATA_WIDTH.value)

  input_width = int(dut.INPUT_DATA_WIDTH.value)
  input_provided = int(cocotb.plusargs["input_provided"]) # Get the input_provided flag from plusargs
  if input_provided == 1:
    num_inputs = 1 # Single input set provided
  else:
    num_inputs = 10 # Multiple input sets generated dynamically

  # Print matrix dimensions for debugging
  print(f"ROW_A: {rows_a}, COL_A: {cols_a}")
  print(f"ROW_B: {rows_b}, COL_B: {cols_b}")
  print(f"INPUT_DATA_WIDTH: {input_width}")

  for i in range(num_inputs):

    if input_provided == 1:
      # Retrieve matrix_a and matrix_b from plusargs (static input)
      matrix_a_flat = int(cocotb.plusargs["matrix_a"])
      matrix_b_flat = int(cocotb.plusargs["matrix_b"])

      # Convert the flattened matrices back to 2D
      matrix_a = hrs_lb.convert_flat_to_2d(matrix_a_flat, rows_a, cols_a, input_width)
      matrix_b = hrs_lb.convert_flat_to_2d(matrix_b_flat, rows_b, cols_b, input_width)
    else:
      # Dynamically generate matrices (input_provided=0)
      matrix_a = hrs_lb.populate_matrix(rows_a, cols_a, input_width)
      matrix_b = hrs_lb.populate_matrix(rows_b, cols_b, input_width)
      
      # Flatten matrices to pass to the DUT
      matrix_a_flat = hrs_lb.convert_2d_to_flat(matrix_a, input_width)
      matrix_b_flat = hrs_lb.convert_2d_to_flat(matrix_b, input_width)

    # Assign the flattened matrices to DUT inputs
    dut.matrix_a.value = matrix_a_flat
    dut.matrix_b.value = matrix_b_flat

    # Compute the expected result using the reference implementation
    expected_matrix_c = hrs_lb.matrix_multiply(matrix_a, matrix_b)

    # Apply a small delay for DUT to compute the result
    await Timer(2, unit='ns')

    # Read and convert the output matrix from the DUT
    matrix_c_flat = int(dut.matrix_c.value)
    matrix_c = hrs_lb.convert_flat_to_2d(matrix_c_flat, rows_a, cols_b, output_width)

    print(f"Test {i+1} passed")

    # Verify if the output matches the expected result
    assert matrix_c == expected_matrix_c, f"Test {i+1}: Matrix C does not match the expected result: {matrix_c} != {expected_matrix_c}"

    # Apply a small delay (for any final signal propagation)
    await Timer(2, unit='ns')
