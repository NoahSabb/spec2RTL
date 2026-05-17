from cocotb.triggers import FallingEdge, RisingEdge, Timer
import random
import os

async def reset_dut(reset_n, duration_ns=10):
  """
  Reset the DUT by setting the reset signal low for a specified duration
  and then setting it high again.
  
  Args:
    reset_n: The reset signal (active low).
    duration_ns: The time in nanoseconds for which the reset signal is held low.
  """
  reset_n.value = 0  # Set reset to active low
  await Timer(duration_ns, unit="ns")  # Wait for the specified duration
  reset_n.value = 1  # Deactivate reset (set it high)
  await Timer(duration_ns, unit='ns')  # Wait for the reset to stabilize
  reset_n._log.debug("Reset complete")

# Function to initialize DUT inputs to 0
async def dut_init(dut):
  """
  Initialize all input signals of the DUT to 0.
  
  Args:
    dut: The Design Under Test.
  """
  for signal in dut:
      try:
          signal.value = 0
      except Exception:
          pass

# Save VCD waveform files after the test is run
def save_vcd(wave: bool, toplevel: str, new_name: str):
  """
  Save the VCD (waveform) file if waveform generation is enabled.
  
  Args:
    wave: Boolean flag to indicate whether to save waveforms.
    toplevel: The top-level module name.
    new_name: The new name for the saved VCD file.
  """
  if wave:
    os.makedirs("vcd", exist_ok=True)  # Create the vcd folder if it doesn't exist
    os.rename(f'./sim_build/{toplevel}.fst', f'./vcd/{new_name}.fst')  # Rename and move the VCD file
    print(f"FST info: Moved /code/rundir/sim_build/{toplevel}.fst to /code/rundir/vcd/{new_name}.fst")

# Helper function to convert a 2D matrix into a flattened integer
def convert_2d_to_flat(array_2d, width):
  """
  Convert a 2D matrix into a flattened integer for passing as a plusarg to the simulator.
  
  Args:
    array_2d: The 2D matrix (list of lists).
    width: The bit-width of each element.
      
  Returns:
    An integer representing the flattened matrix.
  """
  flat_var = []
  for row in array_2d:
    for element in row:
      flat_var.append(element)

  result = 0
  for i, value in enumerate(flat_var):
    result |= (value << (i * width))  # Shift and OR to pack the bits
  return result

# Helper function to multiply two matrices (reference implementation)
def matrix_multiply(a, b):
  """
  Multiply two 2D matrices and return the result.
  
  Args:
    a: The first matrix.
    b: The second matrix.
  
  Returns:
    The resulting matrix after multiplication.
  """
  assert len(a[0]) == len(b), "Matrix dimensions are incompatible for multiplication"  # Ensure correct dimensions
  result = [[0 for _ in range(len(b[0]))] for _ in range(len(a))]
  for i in range(len(a)):
    for j in range(len(b[0])):
      for k in range(len(b)):
        result[i][j] += a[i][k] * b[k][j]  # Element-wise multiplication and summation
  return result

# Helper function to convert a flattened integer back into a 2D matrix
def convert_flat_to_2d(flat_var, rows, cols, width):
  """
  Convert a flattened integer back into a 2D matrix.
  
  Args:
    flat_var: The flattened integer representing the matrix.
    rows: The number of rows in the matrix.
    cols: The number of columns in the matrix.
    width: The bit-width of each element.
      
  Returns:
    A 2D list (matrix) reconstructed from the flattened integer.
  """
  array_2d = []
  for i in range(rows):
    row = []
    for j in range(cols):
      row.append((flat_var >> (width * (i * cols + j))) & ((1 << width) - 1))  # Extract bits for each element
    array_2d.append(row)
  return array_2d

# Helper function to print a matrix in a readable format
def print_matrix(name, matrix):
  """
  Print the contents of a matrix with a label.
  
  Args:
    name: The label for the matrix.
    matrix: The 2D matrix to print.
  """
  print(f"Matrix {name}:")
  for row in matrix:
    print(row)
  print()

# Helper function to populate a matrix with random values
def populate_matrix(rows, cols, width):
  """
  Populate a 2D matrix with random integer values.
  
  Args:
    rows: Number of rows in the matrix.
    cols: Number of columns in the matrix.
    width: The bit-width of each element (values will be within this bit range).
      
  Returns:
    A randomly populated 2D matrix.
  """
  matrix = []
  for i in range(rows):
    row = []
    for j in range(cols):
      row.append(random.randint(0, (2**width)-1))  # Generate random numbers within bit-width
    matrix.append(row)
  return matrix
