import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock
import random
import harness_library as hrs_lb

@cocotb.test()
async def test_apb_controller_with_delay(dut):

    # Create a clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Apply reset and check values after reset
    await hrs_lb.async_reset_dut(dut)

    # Read the number of iterations from the environment variable, default to 5
    num_iterations = 5

    # Perform selections for the specified number of iterations
    for _ in range(num_iterations):

        # Randomize addresses and data for events A, B, and C
        dut.addr_a_i.value = random.randint(0x10000000, 0x1FFFFFFF)
        dut.data_a_i.value = random.randint(0, 0xFFFFFFFF)

        dut.addr_b_i.value = random.randint(0x20000000, 0x2FFFFFFF)
        dut.data_b_i.value = random.randint(0, 0xFFFFFFFF)

        dut.addr_c_i.value = random.randint(0x30000000, 0x3FFFFFFF)
        dut.data_c_i.value = random.randint(0, 0xFFFFFFFF)

        # Add a small delay to allow values to propagate
        await Timer(1, unit="ns")

        # Define select signals and addresses/data
        select_signals = [
            (dut.select_a_i, int(dut.addr_a_i.value), int(dut.data_a_i.value)),
            (dut.select_b_i, int(dut.addr_b_i.value), int(dut.data_b_i.value)),
            (dut.select_c_i, int(dut.addr_c_i.value), int(dut.data_c_i.value))
        ]

        # Randomly choose a select signal along with corresponding address and data
        select_signal, expected_addr, expected_data = random.choice(select_signals)

        # Run the APB transaction with the selected signal and expected values
        await hrs_lb.run_apb_test_with_delay(dut, select_signal, expected_addr, expected_data)

@cocotb.test()
async def test_apb_controller_without_delay(dut):

    # Create a clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Apply reset and check values after reset
    await hrs_lb.async_reset_dut(dut)

    # Read the number of iterations from the environment variable, default to 5
    num_iterations = 4

    # Perform selections for the specified number of iterations
    for _ in range(num_iterations):

        # Randomize addresses and data for events A, B, and C
        dut.addr_a_i.value = random.randint(0x10000000, 0x1FFFFFFF)
        dut.data_a_i.value = random.randint(0, 0xFFFFFFFF)

        dut.addr_b_i.value = random.randint(0x20000000, 0x2FFFFFFF)
        dut.data_b_i.value = random.randint(0, 0xFFFFFFFF)

        dut.addr_c_i.value = random.randint(0x30000000, 0x3FFFFFFF)
        dut.data_c_i.value = random.randint(0, 0xFFFFFFFF)

        # Add a small delay to allow values to propagate
        await Timer(1, unit="ns")

        # Define select signals and addresses/data
        select_signals = [
            (dut.select_a_i, int(dut.addr_a_i.value), int(dut.data_a_i.value)),
            (dut.select_b_i, int(dut.addr_b_i.value), int(dut.data_b_i.value)),
            (dut.select_c_i, int(dut.addr_c_i.value), int(dut.data_c_i.value))
        ]

        # Randomly choose a select signal along with corresponding address and data
        select_signal, expected_addr, expected_data = random.choice(select_signals)

        # Run the APB transaction with the selected signal and expected values
        await hrs_lb.run_apb_test_without_delay(dut, select_signal, expected_addr, expected_data)        
@cocotb.test()
async def test_apb_controller_with_timeout(dut):

    # Create a clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Apply reset and check values after reset
    await hrs_lb.async_reset_dut(dut)

    # Read the number of iterations from the environment variable, default to 5
    num_iterations = 1

    # Perform selections for the specified number of iterations
    for _ in range(num_iterations):

        # Randomize addresses and data for events A, B, and C
        dut.addr_a_i.value = random.randint(0x10000000, 0x1FFFFFFF)
        dut.data_a_i.value = random.randint(0, 0xFFFFFFFF)

        dut.addr_b_i.value = random.randint(0x20000000, 0x2FFFFFFF)
        dut.data_b_i.value = random.randint(0, 0xFFFFFFFF)

        dut.addr_c_i.value = random.randint(0x30000000, 0x3FFFFFFF)
        dut.data_c_i.value = random.randint(0, 0xFFFFFFFF)

        # Add a small delay to allow values to propagate
        await Timer(1, unit="ns")

        # Define select signals and addresses/data
        select_signals = [
            (dut.select_a_i, int(dut.addr_a_i.value), int(dut.data_a_i.value)),
            (dut.select_b_i, int(dut.addr_b_i.value), int(dut.data_b_i.value)),
            (dut.select_c_i, int(dut.addr_c_i.value), int(dut.data_c_i.value))
        ]

        # Randomly choose a select signal along with corresponding address and data
        select_signal, expected_addr, expected_data = random.choice(select_signals)

        # Run the APB transaction with the selected signal and expected values
        await hrs_lb.test_timeout(dut, select_signal, expected_addr, expected_data) 


@cocotb.test()
async def test_apb_controller_priority_all_events(dut):
    """
    Test the priority handling of the APB controller for simultaneous events A, B, and C.
    """

    # Create a clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Apply reset and check values after reset
    await hrs_lb.async_reset_dut(dut)

    # Set randomized addresses and data for events A, B, and C
    dut.addr_a_i.value = random.randint(0x10000000, 0x1FFFFFFF)
    dut.data_a_i.value = random.randint(0, 0xFFFFFFFF)
    dut.addr_b_i.value = random.randint(0x20000000, 0x2FFFFFFF)
    dut.data_b_i.value = random.randint(0, 0xFFFFFFFF)
    dut.addr_c_i.value = random.randint(0x30000000, 0x3FFFFFFF)
    dut.data_c_i.value = random.randint(0, 0xFFFFFFFF)
    # Add a small delay to allow values to propagate
    await Timer(1, unit="ns")

    # Check priority for Event A
    await hrs_lb.check_priority(
        dut,
        [dut.select_a_i, dut.select_b_i, dut.select_c_i],
        int(dut.addr_a_i.value),
        int(dut.data_a_i.value),
        "Event A Priority Test"
    )

    # Check priority for Event B (disable Event A)
    await hrs_lb.check_priority(
        dut,
        [dut.select_b_i, dut.select_c_i],
        int(dut.addr_b_i.value),
        int(dut.data_b_i.value),
        "Event B Priority Test"
    )

    # Check priority for Event C (disable Events A and B)
    await hrs_lb.check_priority(
        dut,
        [dut.select_c_i],
        int(dut.addr_c_i.value),
        int(dut.data_c_i.value),
        "Event C Priority Test"
    )
