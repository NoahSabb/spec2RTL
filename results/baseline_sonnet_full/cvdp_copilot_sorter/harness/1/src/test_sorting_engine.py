import cocotb
from cocotb.triggers import RisingEdge, Timer
import random

@cocotb.test()
async def test_sorter_dynamic_latency(dut):
    N = int(dut.N.value)
    WIDTH = int(dut.WIDTH.value)
    clk_period = 10  # ns
    random.seed(0)  # For reproducibility

    async def clock():
        while True:
            dut.clk.value = 0
            await Timer(clk_period/2, unit='ns')
            dut.clk.value = 1
            await Timer(clk_period/2, unit='ns')

    cocotb.start_soon(clock())

    await reset_dut(dut, 5)
    dut.start.value = 0

    async def run_test_case(name, input_array):
        cocotb.log.info(f"Running Test: {name}")
        packed_input = 0
        for idx, val in enumerate(input_array):
            packed_input |= (val << (idx * WIDTH))
        dut.in_data.value = packed_input

        expected_steps = simulate_bubble_sort_steps(input_array, no_early_termination=True) + 2

        await RisingEdge(dut.clk)
        dut.start.value = 1
        await RisingEdge(dut.clk)
        dut.start.value = 0

        cycle_count = 0
        while True:
            await RisingEdge(dut.clk)
            cycle_count += 1
            if dut.done.value == 1:
                break

        out_data_val = int(dut.out_data.value)
        output_array = [ (out_data_val >> (i * WIDTH)) & ((1 << WIDTH) - 1) for i in range(N)]
        expected_output = sorted(input_array)

        assert output_array == expected_output, f"[{name}] Output incorrect. Got: {output_array}, Expected: {expected_output}"
        assert cycle_count == expected_steps, f"[{name}] Latency mismatch. Got {cycle_count}, Expected {expected_steps}"
        cocotb.log.info(f"Test {name} passed.")

    # Corner Cases
    if N == 1:
        await run_test_case("Single Element", [10])

    await run_test_case("Already Sorted", list(range(N)))
    await run_test_case("Reverse Sorted", list(range(N-1, -1, -1)))
    await run_test_case("All Duplicates", [5]*N)
    await run_test_case("All Max Values", [(1 << WIDTH) - 1]*N)
    await run_test_case("All Min Values", [0]*N)
    # Mixed min/max pattern
    await run_test_case("Min-Max Alternating", [0 if i % 2 == 0 else (1 << WIDTH)-1 for i in range(N)])

    # Partial sorted (first half sorted, second half random)
    half_sorted = list(range(N//2)) + [random.randint(0, (1 << WIDTH)-1) for _ in range(N - N//2)]
    await run_test_case("Half Sorted", half_sorted)

    # Stress Testing with multiple random arrays
    # Increase the count for more thorough stress tests
    stress_test_count = 20
    for idx in range(stress_test_count):
        arr = [random.randint(0, (1 << WIDTH)-1) for _ in range(N)]
        await run_test_case(f"Random {idx}", arr)

    cocotb.log.info("All tests completed successfully!")


def simulate_bubble_sort_steps(arr, no_early_termination=False):
    N = len(arr)
    # Given the DUT does no early termination, it always does (N-1)*(N-1) steps.
    # If no_early_termination is True, ignore input and return full passes.
    if no_early_termination:
        return (N)*(N-1)

    # If we were to consider early termination logic, it would go here.
    return (N)*(N-1)


async def reset_dut(dut, duration):
    dut.rst.value = 1
    for _ in range(duration):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
