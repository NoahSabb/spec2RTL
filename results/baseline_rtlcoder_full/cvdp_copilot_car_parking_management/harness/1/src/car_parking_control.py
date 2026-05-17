import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, FallingEdge


TOTAL_SPACES = int(cocotb.plusargs.get("TOTAL_SPACES", 12))

# Helper function to reset DUT
async def reset_dut(dut, duration_ns=20):
    """Reset DUT"""
    dut.reset.value = 1
    await Timer(duration_ns, unit="ns")
    dut.reset.value = 0
    await RisingEdge(dut.clk)

# Helper function to trigger vehicle entry
async def trigger_entry(dut):
    """Simulate vehicle entry"""
    dut.vehicle_entry_sensor.value = 1
    #await RisingEdge(dut.clk)
    await Timer(10, unit="ns")
    dut.vehicle_entry_sensor.value = 0

# Helper function to trigger vehicle exit
async def trigger_exit(dut):
    """Simulate vehicle exit"""
    dut.vehicle_exit_sensor.value = 1
    await Timer(10, unit="ns")
    #await RisingEdge(dut.clk)
    dut.vehicle_exit_sensor.value = 0

def seven_segment_encoding(digit):
    """Returns the seven-segment encoding for a given digit (0-9)"""
    encoding_map = {
        0: 0b1111110,
        1: 0b0110000,
        2: 0b1101101,
        3: 0b1111001,
        4: 0b0110011,
        5: 0b1011011,
        6: 0b1011111,
        7: 0b1110000,
        8: 0b1111111,
        9: 0b1111011,
    }
    return encoding_map.get(digit, 0b0000000)  # Default to blank display

async def validate_seven_segment(dut, available_spaces, count_car):
    """
    Validate seven-segment display outputs for available spaces and count car.
    """
    # Calculate tens and units for available spaces
    available_tens = available_spaces // 10
    available_units = available_spaces % 10

    # Calculate tens and units for count car
    count_tens = count_car // 10
    count_units = count_car % 10

    # Validate seven-segment display for available spaces
    assert int(dut.seven_seg_display_available_tens.value) == seven_segment_encoding(available_tens), \
        f"Available Spaces Tens Mismatch: Expected {bin(seven_segment_encoding(available_tens))}, Got {bin(int(dut.seven_seg_display_available_tens.value))}"
    assert int(dut.seven_seg_display_available_units.value) == seven_segment_encoding(available_units), \
        f"Available Spaces Units Mismatch: Expected {bin(seven_segment_encoding(available_units))}, Got {bin(int(dut.seven_seg_display_available_units.value))}"

    # Validate seven-segment display for count car
    assert int(dut.seven_seg_display_count_tens.value) == seven_segment_encoding(count_tens), \
        f"Count Car Tens Mismatch: Expected {bin(seven_segment_encoding(count_tens))}, Got {bin(int(dut.seven_seg_display_count_tens.value))}"
    assert int(dut.seven_seg_display_count_units.value) == seven_segment_encoding(count_units), \
        f"Count Car Units Mismatch: Expected {bin(seven_segment_encoding(count_units))}, Got {bin(int(dut.seven_seg_display_count_units.value))}"

    dut._log.info("Seven-segment display validated successfully")

# Test case 1: Basic entry
async def test_case_1(dut):
    """Test case 1: Single vehicle entry"""

    dut._log.info("Simulating single vehicle entry")
    await trigger_entry(dut)

    # Wait for state to update
    await Timer(30, unit="ns")
    assert dut.count_car.value == 1, "Count car did not increment as expected"
    assert dut.available_spaces.value == (TOTAL_SPACES - 1), "Available spaces did not decrement as expected"

    # Validate seven-segment display
    await validate_seven_segment(dut, available_spaces=(TOTAL_SPACES - 1), count_car=1)

    #print(hex(int(dut.seven_seg_display_available_tens.value)))
    # Check seven-segment display
    #check_seven_segment(dut, available_spaces=(TOTAL_SPACES - 1), count_car=1)

# Test case 2: Basic exit
async def test_case_2(dut):
    """Test case 2: Single vehicle exit"""

    dut._log.info("Simulating single vehicle exit")
    await trigger_exit(dut)

    # Wait for state to update
    await Timer(20, unit="ns")
    assert dut.count_car.value == 0, "Count car did not decrement as expected"
    assert dut.available_spaces.value == TOTAL_SPACES, "Available spaces did not increment as expected"

    # Validate seven-segment display
    await validate_seven_segment(dut, available_spaces=TOTAL_SPACES, count_car=0)


# Test case 3: Parking full
async def test_case_3(dut):
    """Test case 3: Simulate parking full"""

    dut._log.info("Simulating parking full scenario")
    for _ in range(TOTAL_SPACES):
        await trigger_entry(dut)
        await Timer(20, unit="ns")
        
    # Wait for state to update
    assert dut.led_status.value == 0, "LED status did not indicate parking full"
    assert dut.available_spaces.value == 0, "Available spaces did not reach 0"
    assert dut.count_car.value == TOTAL_SPACES, "Car count did not reach total spaces"

    # Attempt another entry
    await trigger_entry(dut)
    await Timer(20, unit="ns")
    assert dut.count_car.value == TOTAL_SPACES, "Car count should not exceed total spaces"

    # Validate seven-segment display
    await validate_seven_segment(dut, available_spaces=0, count_car=TOTAL_SPACES)

# Test case 4: Reset operation
async def test_case_4(dut):
    """Test case 4: Reset during operation"""

    dut._log.info("Simulating reset during operation")
    await trigger_entry(dut)
    await Timer(20, unit="ns")
    await reset_dut(dut)

    # Validate reset state
    assert dut.count_car.value == 0, "Count car did not reset to 0"
    assert dut.available_spaces.value == TOTAL_SPACES, "Available spaces did not reset to total"

@cocotb.test()
async def test_car_parking_system(dut):
    """Main test function for Car Parking System"""

    # Start clock
    clock = Clock(dut.clk, 10, unit="ns")  # 100 MHz clock
    cocotb.start_soon(clock.start())

    # Initialize signals
    dut.reset.value = 1
    dut.vehicle_exit_sensor.value = 0
    dut.vehicle_entry_sensor.value = 0

    # Apply reset
    await reset_dut(dut, duration_ns=30)
    await Timer(40, unit="ns")
    await reset_dut(dut, duration_ns=30)
    await Timer(40, unit="ns")

    await FallingEdge(dut.clk)
    

    # Run test cases
    await test_case_1(dut)
    await Timer(10, unit="ns")
    await test_case_2(dut)
    await Timer(10, unit="ns")
    await test_case_3(dut)
    await Timer(10, unit="ns")
    await test_case_4(dut)
