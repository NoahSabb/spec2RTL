import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
import harness_library as hrs_lb
import random

# ----------------------------------------
# - Test FSM Linear Regression
# ----------------------------------------

@cocotb.test()
async def test_fsm_linear_reg(dut):
    """Test the FSM Linear Regression module with edge cases and random data."""

    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())

    # Debug mode
    debug = 0

    # Retrieve parameters from the DUT
    DATA_WIDTH = int(dut.DATA_WIDTH.value)
    model = hrs_lb.FSMLinearReg(DATA_WIDTH)
    # Initialize DUT
    await hrs_lb.dut_init(dut)

    # Apply reset
    await hrs_lb.reset_dut(dut.reset)
    model.reset()
    await RisingEdge(dut.clk)

    # Calculate min and max values for input data
    data_min = int(-2**(DATA_WIDTH - 1))  # Minimum signed value
    data_max = int((2**(DATA_WIDTH - 1)) - 1)  # Maximum signed value
    #random.seed(10)

    # Simulation configurations
    num_random_iterations = 10


    # ----------------------------------------
    # Test 1: Min and Max values for inputs
    # ----------------------------------------
    edge_case_inputs = [
        (data_min, data_min, data_min),  # All inputs at minimum
        (data_max, data_max, data_max),  # All inputs at maximum
        (data_min, data_max, data_min),  # Mixed min and max
        (data_max, data_min, data_max)   # Mixed max and min
    ]

    # Generate random test cases and append to edge cases
    for _ in range(num_random_iterations):
        random_x = random.randint(data_min, data_max)
        random_w = random.randint(data_min, data_max)
        random_b = random.randint(data_min, data_max)
        edge_case_inputs.append((random_x, random_w, random_b))

    reset_cycle = random.randint(0, len(edge_case_inputs) - 2)
    cocotb.log.warning(f'Reset will be applied at cycle = {reset_cycle+1}')

    # Run all test cases (edge cases + random cases)
    for i, (x_in_val, w_in_val, b_in_val) in enumerate(edge_case_inputs):
        start_signal = random.randint(0,1)
        
        # Apply stimulus to DUT
        dut.start.value = start_signal
        dut.x_in.value = x_in_val
        dut.w_in.value = w_in_val
        dut.b_in.value = b_in_val        
        if i == reset_cycle:
            cocotb.log.info(f"[INFO] Applying reset at cycle {i+1}")
            await hrs_lb.reset_dut(dut.reset)
            result1 = dut.result1.value.signed_integer
            result2 = dut.result2.value.signed_integer
            done    = int(dut.done.value)
            model_res = model.print_outputs()
            model_out = model.get_outputs()
    
            # Log the DUT outputs
            if debug:
               cocotb.log.info(f"  result1 = {result1}")
               cocotb.log.info(f"  result2 = {result2}")
               cocotb.log.info(f"  done    = {done}")            
            model.reset()
            await RisingEdge(dut.clk)
            model.step(start=start_signal, x_in=x_in_val, w_in=w_in_val, b_in=b_in_val)
            model.step(start=start_signal, x_in=x_in_val, w_in=w_in_val, b_in=b_in_val)


        model.step(start=start_signal, x_in=x_in_val, w_in=w_in_val, b_in=b_in_val)

        # Log the applied inputs
        if debug:
            cocotb.log.info(f"[INFO] Test Case {i+1}")
            cocotb.log.info(f"  x_in   = {x_in_val}")
            cocotb.log.info(f"  w_in   = {w_in_val}")
            cocotb.log.info(f"  b_in   = {b_in_val}")
            cocotb.log.info(f"  start  = {start_signal}")
            cocotb.log.info(f"   STATE = {int(dut.next_state.value)}")
            cocotb.log.info(f"   STATE = {int(dut.current_state.value)}")

        # Wait for one clock cycle
        await RisingEdge(dut.clk)

        # Read outputs
        result1 = dut.result1.value.signed_integer
        result2 = dut.result2.value.signed_integer
        done    = int(dut.done.value)
        model_res = model.print_outputs()
        model_out = model.get_outputs()

        # Log the DUT outputs
        if debug:
            cocotb.log.info(f"  result1 = {result1}")
            cocotb.log.info(f"  result2 = {result2}")
            cocotb.log.info(f"  done    = {done}")
            cocotb.log.info(f"MODEL = {model_res} ")

        assert result1 == model_out[0]
        assert result2 == model_out[1]
        assert done    == model_out[2]
