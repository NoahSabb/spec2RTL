import os
import json
from cocotb_tools.runner import get_runner
import pytest

verilog_sources = os.getenv("VERILOG_SOURCES").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")
wave            = os.getenv("WAVE")

def runner(test_sequence=None, expected_output=None):
    runner = get_runner(sim)

    # Set environment variables for test_sequence and expected_output
    os.environ["TEST_SEQUENCE"] = json.dumps(test_sequence)
    os.environ["EXPECTED_OUTPUT"] = json.dumps(expected_output)

    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        always=True,
        clean=True,
        verbose=True,
        timescale=("1ns", "1ns"),
        log_file="sim.log")
    runner.test(hdl_toplevel=toplevel, test_module=module, waves=True)

# Test: Detection of the Sequence at the Start
def test_detection_at_start():
    test_sequence = [1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1]  # Sequence at the start
    expected_output = [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]  # Detected at position 9
    runner(test_sequence=test_sequence, expected_output=expected_output)

# Test: Detection of the Sequence at the End
def test_detection_at_end():
    test_sequence = [0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1]  # Sequence at the end
    expected_output = [0] * 10 + [0, 0, 0, 1]  # Detected at the last position
    runner(test_sequence=test_sequence, expected_output=expected_output)

# Test: Multiple Occurrences of the Sequence
def test_multiple_occurrences():
    test_sequence = [1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1]
    expected_output = [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1]  # Two detections
    runner(test_sequence=test_sequence, expected_output=expected_output)

# Test: Sequence with Noise Before and After
def test_noise_before_after():
    test_sequence = [0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0]  # Noise before and after
    expected_output = [0] * 13 + [0, 1, 0]  # Detection happens at index 14 (1-clock delay)
    runner(test_sequence=test_sequence, expected_output=expected_output)

# Test: Sequence with Overlapping 2 sequences
def test_seq_overlapping():
    test_sequence = [1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0]  # Overlapping case
    expected_output = [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0]  # Two detections
    runner(test_sequence=test_sequence, expected_output=expected_output)
