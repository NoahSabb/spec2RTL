import cocotb
from cocotb.triggers import FallingEdge, RisingEdge, Timer
import random

async def dut_init(dut):
    # iterate all the input signals and initialize with 0
    for signal in dut:
        try:
            signal.value = 0
        except Exception:
            pass

# Reset the DUT (design under test)
async def reset_dut(reset_n, duration_ns=10):
    reset_n.value = 1
    await Timer(duration_ns, unit="ns")
    reset_n.value = 0
    await Timer(duration_ns, unit='ns')
    reset_n._log.debug("Reset complete")   

class FSMLinearReg:
    """
    A Python implementation of FSM logic that mimics the behavior of fsm_linear_reg module.
    """

    # FSM States
    IDLE = 0
    COMPUTE = 1
    DONE = 2

    def __init__(self, data_width=16):
        self.DATA_WIDTH = data_width
        self.reset()

    def reset(self):
        """
        Resets the FSM to the IDLE state and clears all outputs and registers.
        """
        self.current_state = self.IDLE
        self.result1 = 0       # Output for combinational logic 1
        self.result2 = 0       # Output for combinational logic 2
        self.done = 0          # Completion flag
        self.compute1 = 0      # Internal signal for logic 1
        self.compute2 = 0      # Internal signal for logic 2
        self.output_buffer = {  # Buffer to introduce delay
            "result1": 0,
            "result2": 0,
            "done": 0
        }

    def next_state_logic(self, start):
        """
        Determines the next state based on the current state and start signal.
        """
        if self.current_state == self.IDLE:
            self.next_state = self.COMPUTE if start else self.IDLE
        elif self.current_state == self.COMPUTE:
            self.next_state = self.DONE
        elif self.current_state == self.DONE:
            self.next_state = self.IDLE
        else:
            self.next_state = self.IDLE

    def combinational_logic(self, x_in, w_in, b_in):
        """
        Perform the two combinational logic operations.
        Logic 1: (w_in * x_in) >> 1
        Logic 2: b_in + (x_in >> 2)
        """
        self.compute1 = (w_in * x_in) >> 1  # Weighted sum shifted right by 1
        self.compute2 = b_in + (x_in >> 2)  # Add bias to input shifted right by 2

    def fsm_output_logic(self):
        """
        Updates outputs based on the current state and introduces delay in outputs.
        """
        # Update outputs with a cycle of delay using the buffer
        self.result1 = self.output_buffer["result1"]
        self.result2 = self.output_buffer["result2"]
        self.done = self.output_buffer["done"]

        if self.current_state == self.COMPUTE:
            self.output_buffer["result1"] = self.compute1
            self.output_buffer["result2"] = self.compute2
            self.output_buffer["done"] = 0
        elif self.current_state == self.DONE:
            self.output_buffer["done"] = 1
        else:
            self.output_buffer["result1"] = 0
            self.output_buffer["result2"] = 0
            self.output_buffer["done"] = 0

    def step(self, start, x_in, w_in, b_in):
        """
        Simulate one clock cycle of the FSM.
        """
        # Determine the next state
        self.next_state_logic(start)

        # Combinational logic
        #if self.current_state == self.COMPUTE:
        self.combinational_logic(x_in, w_in, b_in)

        # Update outputs
        self.fsm_output_logic()

        # Move to the next state
        self.current_state = self.next_state

    def print_outputs(self):
        """
        Returns the outputs of the FSM after the delay cycle.
        """
        return {
            "result1": self.result1,
            "result2": self.result2,
            "done": self.done
        }
    def get_outputs(self):
      return [self.result1,self.result2,self.done]

