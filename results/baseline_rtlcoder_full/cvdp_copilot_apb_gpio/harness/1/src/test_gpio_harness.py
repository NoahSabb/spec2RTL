import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock
import logging

# Constants
APB_ADDRESSES = {
    'DATA_IN': 0x00,       # Address 0x00 >> 2 = 0x00
    'DATA_OUT': 0x01,      # Address 0x04 >> 2 = 0x01
    'DATA_OUT_EN': 0x02,   # Address 0x08 >> 2 = 0x02
    'INT_ENABLE': 0x03,    # Address 0x0C >> 2 = 0x03
    'INT_TYPE': 0x04,      # Address 0x10 >> 2 = 0x04
    'INT_POLARITY': 0x05,  # Address 0x14 >> 2 = 0x05
    'INT_STATE': 0x06      # Address 0x18 >> 2 = 0x06
}

async def apb_write(dut, address, data):
    """Perform an APB write transaction"""
    # Set APB write signals
    dut.psel.value = 1
    dut.paddr.value = address  # Word address
    dut.pwrite.value = 1
    dut.pwdata.value = data
    dut.penable.value = 0

    # Wait for posedge pclk
    await RisingEdge(dut.pclk)

    # Enable transfer
    dut.penable.value = 1
    await RisingEdge(dut.pclk)

    # De-assert psel and penable
    dut.psel.value = 0
    dut.penable.value = 0

async def apb_read(dut, address):
    """Perform an APB read transaction and return the read data"""
    # Set APB read signals
    dut.psel.value = 1
    dut.paddr.value = address  # Word address
    dut.pwrite.value = 0
    dut.penable.value = 0

    # Wait for posedge pclk
    await RisingEdge(dut.pclk)

    # Enable transfer
    dut.penable.value = 1
    await RisingEdge(dut.pclk)

    # Read prdata
    read_data = int(dut.prdata.value)

    # De-assert psel and penable
    dut.psel.value = 0
    dut.penable.value = 0

    return read_data

def check_condition(condition, fail_msg, pass_msg, test_failures):
    """Helper function to log test results"""
    if not condition:
        logging.getLogger().error(fail_msg)
        test_failures.append(fail_msg)
    else:
        logging.getLogger().info(pass_msg)

@cocotb.test()
async def test1_write_read_data_output(dut):
    """Test 1: Write and Read Data Output Register (reg_dout)"""

    logger = dut._log
    logger.setLevel(logging.INFO)
    logger.info("Test 1: Write and Read Data Output Register")

    # Retrieve GPIO_WIDTH from DUT parameters
    GPIO_WIDTH = int(dut.GPIO_WIDTH.value)

    # Start the clock
    cocotb.start_soon(Clock(dut.pclk, 20, unit="ns").start())

    # Reset
    dut.preset_n.value = 0
    await Timer(50, unit='ns')  # Hold reset low for 50 ns
    dut.preset_n.value = 1

    # Wait for reset deassertion
    await RisingEdge(dut.pclk)

    # Perform APB write to DATA_OUT
    write_data = 0xA5A5A5A5  # Write a pattern
    write_data_masked = write_data & ((1 << GPIO_WIDTH) - 1)
    await apb_write(dut, APB_ADDRESSES['DATA_OUT'], write_data_masked)

    # Perform APB read from DATA_OUT
    read_data = await apb_read(dut, APB_ADDRESSES['DATA_OUT'])
    expected_data = write_data_masked
    actual_data = read_data

    # Check Data Output Register
    check_condition(
        actual_data == expected_data,
        f"FAIL: Data Output Register mismatch. Expected: 0x{expected_data:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_data:0{(GPIO_WIDTH + 3) // 4}X}",
        f"PASS: Data Output Register value: 0x{actual_data:0{(GPIO_WIDTH + 3) // 4}X}",
        []
    )

@cocotb.test()
async def test2_write_read_output_enable(dut):
    """Test 2: Write and Read Output Enable Register (reg_dout_en)"""

    logger = dut._log
    logger.setLevel(logging.INFO)
    logger.info("Test 2: Write and Read Output Enable Register")

    # Retrieve GPIO_WIDTH from DUT parameters
    GPIO_WIDTH = int(dut.GPIO_WIDTH.value)

    # Start the clock
    cocotb.start_soon(Clock(dut.pclk, 20, unit="ns").start())

    # Reset
    dut.preset_n.value = 0
    await Timer(50, unit='ns')  # Hold reset low for 50 ns
    dut.preset_n.value = 1

    # Initialize list to collect failures
    test_failures = []

    # Perform APB write to DATA_OUT
    write_data = 0xA5A5A5A5  # Write a pattern
    write_data_masked = write_data & ((1 << GPIO_WIDTH) - 1)
    await apb_write(dut, APB_ADDRESSES['DATA_OUT'], write_data_masked)

    # Perform APB write to DATA_OUT_EN
    write_en = (1 << GPIO_WIDTH) - 1  # Enable all GPIOs based on GPIO_WIDTH
    await apb_write(dut, APB_ADDRESSES['DATA_OUT_EN'], write_en)

    # Perform APB read from DATA_OUT_EN
    read_data = await apb_read(dut, APB_ADDRESSES['DATA_OUT_EN'])
    expected_en = write_en
    actual_en = read_data

    # Check Output Enable Register
    check_condition(
        actual_en == expected_en,
        f"FAIL: Output Enable Register mismatch. Expected: 0x{expected_en:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_en:0{(GPIO_WIDTH + 3) // 4}X}",
        f"PASS: Output Enable Register value: 0x{actual_en:0{(GPIO_WIDTH + 3) // 4}X}",
        test_failures
    )

    # Verify GPIO Outputs and Enables
    gpio_out = int(dut.gpio_out.value)
    gpio_enable = int(dut.gpio_enable.value)
    expected_gpio_out = write_data_masked
    expected_gpio_enable = write_en

    check_condition(
        gpio_out == expected_gpio_out,
        f"FAIL: GPIO Output mismatch. Expected: 0x{expected_gpio_out:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{gpio_out:0{(GPIO_WIDTH + 3) // 4}X}",
        f"PASS: GPIO Output matches expected value: 0x{gpio_out:0{(GPIO_WIDTH + 3) // 4}X}",
        test_failures
    )

    check_condition(
        gpio_enable == expected_gpio_enable,
        f"FAIL: GPIO Enable mismatch. Expected: 0x{expected_gpio_enable:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{gpio_enable:0{(GPIO_WIDTH + 3) // 4}X}",
        f"PASS: GPIO Enable matches expected value: 0x{gpio_enable:0{(GPIO_WIDTH + 3) // 4}X}",
        test_failures
    )

    # Report failures if any
    if test_failures:
        failure_message = "\n".join(test_failures)
        logger.error(f"Test 2 completed with failures:\n{failure_message}")
        assert False, f"Some test cases failed. Check the log for details:\n{failure_message}"
    else:
        logger.info("Test 2 completed successfully")

@cocotb.test()
async def test3_gpio_input_synchronization(dut):
    """Test 3: Test GPIO Input Synchronization"""

    logger = dut._log
    logger.setLevel(logging.INFO)
    logger.info("Test 3: GPIO Input Synchronization")

    # Retrieve GPIO_WIDTH from DUT parameters
    GPIO_WIDTH = int(dut.GPIO_WIDTH.value)

    # Start the clock
    cocotb.start_soon(Clock(dut.pclk, 20, unit="ns").start())

    # Reset
    dut.preset_n.value = 0
    await Timer(50, unit='ns')  # Hold reset low for 50 ns
    dut.preset_n.value = 1

    # Initialize list to collect failures
    test_failures = []

    # Perform APB write to DATA_OUT and DATA_OUT_EN
    write_data = (0xA5A5A5A5 >> (32 - GPIO_WIDTH))  # Adjust based on GPIO_WIDTH
    write_en = (1 << GPIO_WIDTH) - 1
    await apb_write(dut, APB_ADDRESSES['DATA_OUT'], write_data)
    await apb_write(dut, APB_ADDRESSES['DATA_OUT_EN'], write_en)

    # Change GPIO inputs
    gpio_input = 0x3C
    gpio_input_masked = gpio_input & ((1 << GPIO_WIDTH) - 1)
    dut.gpio_in.value = gpio_input_masked
    for _ in range(3):
        await RisingEdge(dut.pclk)  # Wait for synchronization

    # Perform APB read from DATA_IN
    read_data = await apb_read(dut, APB_ADDRESSES['DATA_IN'])
    expected_data = gpio_input_masked
    actual_data = read_data

    # Check GPIO Input Data
    check_condition(
        actual_data == expected_data,
        f"FAIL: GPIO Input Data mismatch. Expected: 0x{expected_data:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_data:0{(GPIO_WIDTH + 3) // 4}X}",
        f"PASS: GPIO Input Data value: 0x{actual_data:0{(GPIO_WIDTH + 3) // 4}X}",
        test_failures
    )

    # Report failures if any
    if test_failures:
        failure_message = "\n".join(test_failures)
        logger.error(f"Test 3 completed with failures:\n{failure_message}")
        assert False, f"Some test cases failed. Check the log for details:\n{failure_message}"
    else:
        logger.info("Test 3 completed successfully")

@cocotb.test()
async def test4_configure_level_triggered_interrupts(dut):
    """Test 4: Configure Level-Triggered Interrupts (Positive Polarity)"""

    logger = dut._log
    logger.setLevel(logging.INFO)
    logger.info("Test 4: Configure Level-Triggered Interrupts (Positive Polarity)")

    # Retrieve GPIO_WIDTH from DUT parameters
    GPIO_WIDTH = int(dut.GPIO_WIDTH.value)

    # Start the clock
    cocotb.start_soon(Clock(dut.pclk, 20, unit="ns").start())

    # Reset
    dut.preset_n.value = 0
    await Timer(50, unit='ns')  # Hold reset low for 50 ns
    dut.preset_n.value = 1

    # Initialize list to collect failures
    test_failures = []

    # Perform APB writes to set up GPIO and Interrupts
    write_data = (0xA5A5A5A5 >> (32 - GPIO_WIDTH))
    write_en = (1 << GPIO_WIDTH) - 1
    await apb_write(dut, APB_ADDRESSES['DATA_OUT'], write_data)
    await apb_write(dut, APB_ADDRESSES['DATA_OUT_EN'], write_en)
    await apb_write(dut, APB_ADDRESSES['INT_TYPE'], 0x00)       # Level-triggered
    await apb_write(dut, APB_ADDRESSES['INT_POLARITY'], 0x00)   # Active High
    await apb_write(dut, APB_ADDRESSES['INT_ENABLE'], write_en) # Enable all interrupts

    # Generate GPIO Input to Trigger Interrupts
    gpio_input = 0x55
    gpio_input_masked = gpio_input & ((1 << GPIO_WIDTH) - 1)
    dut.gpio_in.value = gpio_input_masked
    for _ in range(3):
        await RisingEdge(dut.pclk)  # Wait for synchronization and interrupt update

    # Perform APB read from INT_STATE
    read_data = await apb_read(dut, APB_ADDRESSES['INT_STATE'])
    expected_int_state = gpio_input_masked
    actual_int_state = read_data

    # Check Interrupt State Register
    check_condition(
        actual_int_state == expected_int_state,
        f"FAIL: Interrupt State Register mismatch (Level-Triggered). Expected: 0x{expected_int_state:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_int_state:0{(GPIO_WIDTH + 3) // 4}X}",
        f"PASS: Interrupt State Register value: 0x{actual_int_state:0{(GPIO_WIDTH + 3) // 4}X}",
        test_failures
    )

    # Check Combined Interrupt Signal
    comb_int = int(dut.comb_int.value)
    expected_comb_int = 1 if expected_int_state != 0 else 0
    check_condition(
        comb_int == expected_comb_int,
        f"FAIL: Combined Interrupt Signal should be {'high' if expected_comb_int else 'low'}. Got: {comb_int}",
        f"PASS: Combined Interrupt Signal is {'high' if comb_int else 'low'} as expected",
        test_failures
    )

    # Report failures if any
    if test_failures:
        failure_message = "\n".join(test_failures)
        logger.error(f"Test 4 completed with failures:\n{failure_message}")
        assert False, f"Some test cases failed. Check the log for details:\n{failure_message}"
    else:
        logger.info("Test 4 completed successfully")

@cocotb.test()
async def test5_clear_level_triggered_interrupts(dut):
    """Test 5: Clear Level-Triggered Interrupts by Changing Input"""

    logger = dut._log
    logger.setLevel(logging.INFO)
    logger.info("Test 5: Clear Level-Triggered Interrupts by Changing Input")

    # Retrieve GPIO_WIDTH from DUT parameters
    GPIO_WIDTH = int(dut.GPIO_WIDTH.value)

    # Start the clock
    cocotb.start_soon(Clock(dut.pclk, 20, unit="ns").start())

    # Reset
    dut.preset_n.value = 0
    await Timer(50, unit='ns')  # Hold reset low for 50 ns
    dut.preset_n.value = 1

    # Initialize list to collect failures
    test_failures = []

    # Perform APB writes to set up GPIO and Interrupts
    write_data = (0xA5A5A5A5 >> (32 - GPIO_WIDTH))
    write_en = (1 << GPIO_WIDTH) - 1
    await apb_write(dut, APB_ADDRESSES['DATA_OUT'], write_data)
    await apb_write(dut, APB_ADDRESSES['DATA_OUT_EN'], write_en)
    await apb_write(dut, APB_ADDRESSES['INT_TYPE'], 0x00)       # Level-triggered
    await apb_write(dut, APB_ADDRESSES['INT_POLARITY'], 0x00)   # Active High
    await apb_write(dut, APB_ADDRESSES['INT_ENABLE'], write_en) # Enable all interrupts

    # Generate GPIO Input to Trigger Interrupts
    gpio_input = 0x55
    gpio_input_masked = gpio_input & ((1 << GPIO_WIDTH) - 1)
    dut.gpio_in.value = gpio_input_masked
    for _ in range(3):
        await RisingEdge(dut.pclk)  # Wait for synchronization and interrupt update

    # Clear interrupts by changing GPIO inputs
    gpio_input_clear = 0x00
    gpio_input_clear_masked = gpio_input_clear & ((1 << GPIO_WIDTH) - 1)
    dut.gpio_in.value = gpio_input_clear_masked
    for _ in range(3):
        await RisingEdge(dut.pclk)  # Wait for synchronization

    # Perform APB read from INT_STATE
    read_data = await apb_read(dut, APB_ADDRESSES['INT_STATE'])
    expected_int_state = gpio_input_clear_masked
    actual_int_state = read_data

    # Check Interrupt State Register
    check_condition(
        actual_int_state == expected_int_state,
        f"FAIL: Level-triggered interrupts not cleared. Expected: 0x{expected_int_state:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_int_state:0{(GPIO_WIDTH + 3) // 4}X}",
        "PASS: Level-triggered interrupts cleared successfully",
        test_failures
    )

    # Verify Combined Interrupt Signal is Low
    comb_int = int(dut.comb_int.value)
    expected_comb_int = 1 if expected_int_state != 0 else 0
    check_condition(
        comb_int == expected_comb_int,
        f"FAIL: Combined Interrupt Signal should be {'high' if expected_comb_int else 'low'}. Got: {comb_int}",
        f"PASS: Combined Interrupt Signal is {'high' if comb_int else 'low'} as expected",
        test_failures
    )

    # Report failures if any
    if test_failures:
        failure_message = "\n".join(test_failures)
        logger.error(f"Test 5 completed with failures:\n{failure_message}")
        assert False, f"Some test cases failed. Check the log for details:\n{failure_message}"
    else:
        logger.info("Test 5 completed successfully")

@cocotb.test()
async def test6_configure_edge_triggered_interrupts(dut):
    """Test 6: Configure Edge-Triggered Interrupts (Negative Polarity)"""

    logger = dut._log
    logger.setLevel(logging.INFO)
    logger.info("Test 6: Configure Edge-Triggered Interrupts (Negative Polarity)")

    # Retrieve GPIO_WIDTH from DUT parameters
    GPIO_WIDTH = int(dut.GPIO_WIDTH.value)

    # Start the clock
    cocotb.start_soon(Clock(dut.pclk, 20, unit="ns").start())

    # Reset
    dut.preset_n.value = 0
    await Timer(50, unit='ns')  # Hold reset low for 50 ns
    dut.preset_n.value = 1

    # Initialize list to collect failures
    test_failures = []

    # Perform APB writes to set up GPIO and Interrupts
    write_data = (0xFFFF >> (32 - GPIO_WIDTH))  # For GPIO_WIDTH=16, 0xFFFF
    write_en = (1 << GPIO_WIDTH) - 1
    await apb_write(dut, APB_ADDRESSES['DATA_OUT'], write_data)
    await apb_write(dut, APB_ADDRESSES['DATA_OUT_EN'], write_en)
    await apb_write(dut, APB_ADDRESSES['INT_TYPE'], (1 << GPIO_WIDTH) - 1)       # Edge-triggered
    await apb_write(dut, APB_ADDRESSES['INT_POLARITY'], (1 << GPIO_WIDTH) - 1)   # Active Low
    await apb_write(dut, APB_ADDRESSES['INT_ENABLE'], write_en)                  # Enable all interrupts
    await apb_write(dut, APB_ADDRESSES['INT_STATE'], (1 << GPIO_WIDTH) - 1)       # Clear any pending interrupts

    # Generate Falling Edge on GPIO Inputs (Active Low Polarity)
    initial_gpio = (1 << GPIO_WIDTH) - 1  # All high
    gpio_falling = 0xAAAA & ((1 << GPIO_WIDTH) - 1)  # Example pattern with falling edges
    dut.gpio_in.value = initial_gpio
    for _ in range(3):
        await RisingEdge(dut.pclk)

    # Generate Falling Edges
    dut.gpio_in.value = gpio_falling
    for _ in range(3):
        await RisingEdge(dut.pclk)

    # Calculate expected interrupts: bits that transitioned from 1 to 0
    transitions = initial_gpio ^ gpio_falling
    expected_int_state = transitions & ((1 << GPIO_WIDTH) - 1)

    # Perform APB read from INT_STATE
    read_data = await apb_read(dut, APB_ADDRESSES['INT_STATE'])
    actual_int_state = read_data

    # Check Interrupt State Register
    check_condition(
        actual_int_state == expected_int_state,
        f"FAIL: Interrupt State Register mismatch (Edge-Triggered). Expected: 0x{expected_int_state:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_int_state:0{(GPIO_WIDTH + 3) // 4}X}",
        f"PASS: Interrupt State Register value: 0x{actual_int_state:0{(GPIO_WIDTH + 3) // 4}X}",
        test_failures
    )

    # Clear Edge-Triggered Interrupts
    await apb_write(dut, APB_ADDRESSES['INT_STATE'], (1 << GPIO_WIDTH) - 1)  # Clear all interrupts
    await RisingEdge(dut.pclk)

    # Perform APB read from INT_STATE
    read_data = await apb_read(dut, APB_ADDRESSES['INT_STATE'])
    expected_int_state_cleared = 0x00
    actual_int_state_cleared = read_data & ((1 << GPIO_WIDTH) - 1)

    # Check Interrupt State Register after clearing
    check_condition(
        actual_int_state_cleared == expected_int_state_cleared,
        f"FAIL: Edge-triggered interrupts not cleared. Expected: 0x{expected_int_state_cleared:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_int_state_cleared:0{(GPIO_WIDTH + 3) // 4}X}",
        "PASS: Edge-triggered interrupts cleared successfully",
        test_failures
    )

    # Report failures if any
    if test_failures:
        failure_message = "\n".join(test_failures)
        logger.error(f"Test 6 completed with failures:\n{failure_message}")
        assert False, f"Some test cases failed. Check the log for details:\n{failure_message}"
    else:
        logger.info("Test 6 completed successfully")

@cocotb.test()
async def test7_mask_interrupts(dut):
    """Test 7: Mask Interrupts Using Interrupt Enable Register"""

    logger = dut._log
    logger.setLevel(logging.INFO)
    logger.info("Test 7: Mask Interrupts Using Interrupt Enable Register")

    # Retrieve GPIO_WIDTH from DUT parameters
    GPIO_WIDTH = int(dut.GPIO_WIDTH.value)

    # Start the clock
    cocotb.start_soon(Clock(dut.pclk, 20, unit="ns").start())

    # Reset
    dut.preset_n.value = 0
    await Timer(50, unit='ns')  # Hold reset low for 50 ns
    dut.preset_n.value = 1

    # Initialize list to collect failures
    test_failures = []

    # Perform APB writes to set up GPIO and Interrupts
    write_data = (0xFFFF >> (32 - GPIO_WIDTH))  # For GPIO_WIDTH=16, 0xFFFF
    write_en = (1 << GPIO_WIDTH) - 1
    await apb_write(dut, APB_ADDRESSES['DATA_OUT'], write_data)
    await apb_write(dut, APB_ADDRESSES['DATA_OUT_EN'], write_en)
    await apb_write(dut, APB_ADDRESSES['INT_ENABLE'], 0x0F)     # Enable lower 4 interrupts
    await apb_write(dut, APB_ADDRESSES['INT_TYPE'], 0x00)       # Level-triggered
    await apb_write(dut, APB_ADDRESSES['INT_POLARITY'], 0x00)   # Active High

    # Clear any pending interrupts
    await apb_write(dut, APB_ADDRESSES['INT_STATE'], (1 << GPIO_WIDTH) - 1)
    await RisingEdge(dut.pclk)

    # Generate Edge on GPIO Inputs
    dut.gpio_in.value = 0x00  # All inputs low
    for _ in range(3):
        await RisingEdge(dut.pclk)

    dut.gpio_in.value = 0xFF  # All inputs high (should generate edges on all bits)
    for _ in range(3):
        await RisingEdge(dut.pclk)

    # Expected interrupts only on lower 4 bits
    expected_int_state = 0x0F & ((1 << GPIO_WIDTH) - 1)
    read_data = await apb_read(dut, APB_ADDRESSES['INT_STATE'])
    actual_int_state = read_data & ((1 << GPIO_WIDTH) - 1)

    # Check Interrupt State Register
    check_condition(
        actual_int_state == expected_int_state,
        f"FAIL: Interrupts not masked correctly. Expected: 0x{expected_int_state:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_int_state:0{(GPIO_WIDTH + 3) // 4}X}",
        f"PASS: Interrupts masked correctly, Interrupt State: 0x{actual_int_state:0{(GPIO_WIDTH + 3) // 4}X}",
        test_failures
    )

    # Verify Combined Interrupt Signal
    comb_int = int(dut.comb_int.value)
    expected_comb_int = 1 if expected_int_state != 0 else 0
    check_condition(
        comb_int == expected_comb_int,
        f"FAIL: Combined Interrupt Signal should be {'high' if expected_comb_int else 'low'}. Got: {comb_int}",
        f"PASS: Combined Interrupt Signal is {'high' if comb_int else 'low'} as expected",
        test_failures
    )

    # Perform APB writes to further test masking
    # Reconfigure Interrupt Polarity to Active High (already active high, but for completeness)
    await apb_write(dut, APB_ADDRESSES['INT_POLARITY'], 0x00)
    await RisingEdge(dut.pclk)

    # Generate edges again
    dut.gpio_in.value = 0x00
    for _ in range(3):
        await RisingEdge(dut.pclk)
    dut.gpio_in.value = 0xFF
    for _ in range(3):
        await RisingEdge(dut.pclk)

    # Expected interrupts still only on lower 4 bits
    read_data = await apb_read(dut, APB_ADDRESSES['INT_STATE'])
    actual_int_state = read_data & ((1 << GPIO_WIDTH) - 1)

    # Check Interrupt State Register again
    check_condition(
        actual_int_state == expected_int_state,
        f"FAIL: Interrupts not masked correctly after re-triggering. Expected: 0x{expected_int_state:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_int_state:0{(GPIO_WIDTH + 3) // 4}X}",
        f"PASS: Interrupts masked correctly after re-triggering, Interrupt State: 0x{actual_int_state:0{(GPIO_WIDTH + 3) // 4}X}",
        test_failures
    )

    # Report failures if any
    if test_failures:
        failure_message = "\n".join(test_failures)
        logger.error(f"Test 7 completed with failures:\n{failure_message}")
        assert False, f"Some test cases failed. Check the log for details:\n{failure_message}"
    else:
        logger.info("Test 7 completed successfully")

@cocotb.test()
async def test8_invalid_address_access(dut):
    """Test 8: Attempt to Access Invalid Address"""

    logger = dut._log
    logger.setLevel(logging.INFO)
    logger.info("Test 8: Attempt to Access Invalid Address")

    # Retrieve GPIO_WIDTH from DUT parameters
    GPIO_WIDTH = int(dut.GPIO_WIDTH.value)

    # Start the clock
    cocotb.start_soon(Clock(dut.pclk, 20, unit="ns").start())

    # Reset
    dut.preset_n.value = 0
    await Timer(50, unit='ns')  # Hold reset low for 50 ns
    dut.preset_n.value = 1

    # Initialize list to collect failures
    test_failures = []

    # Attempt to write to an invalid address (e.g., 0x3F)
    invalid_address = 0x3F
    write_data = 0xDEADBEEF
    await apb_write(dut, invalid_address, write_data)

    # Attempt to read from the invalid address
    read_data = await apb_read(dut, invalid_address)
    expected_data = 0x00

    # Check that invalid address returns zero
    check_condition(
        read_data == expected_data,
        f"FAIL: Invalid address should return zero data. Expected: 0x{expected_data:08X}, Got: 0x{read_data:08X}",
        "PASS: Invalid address access returned zero as expected",
        test_failures
    )

    # Report failures if any
    if test_failures:
        failure_message = "\n".join(test_failures)
        logger.error(f"Test 8 completed with failures:\n{failure_message}")
        assert False, f"Some test cases failed. Check the log for details:\n{failure_message}"
    else:
        logger.info("Test 8 completed successfully")

@cocotb.test()
async def test9_multiple_simultaneous_interrupts(dut):
    """Test 9: Multiple Interrupts Occurring Simultaneously"""

    logger = dut._log
    logger.setLevel(logging.INFO)
    logger.info("Test 9: Multiple Interrupts Occurring Simultaneously")

    # Retrieve GPIO_WIDTH from DUT parameters
    GPIO_WIDTH = int(dut.GPIO_WIDTH.value)

    # Start the clock
    cocotb.start_soon(Clock(dut.pclk, 20, unit="ns").start())

    # Reset
    dut.preset_n.value = 0
    await Timer(50, unit='ns')  # Hold reset low for 50 ns
    dut.preset_n.value = 1

    # Initialize list to collect failures
    test_failures = []

    # Perform APB writes to set up GPIO and Interrupts
    write_data = 0x0000  # Initialize gpio_out to 0x0000
    write_en = (1 << GPIO_WIDTH) - 1
    await apb_write(dut, APB_ADDRESSES['DATA_OUT'], write_data)
    await apb_write(dut, APB_ADDRESSES['DATA_OUT_EN'], write_en)
    await apb_write(dut, APB_ADDRESSES['INT_ENABLE'], write_en)       # Enable all interrupts
    await apb_write(dut, APB_ADDRESSES['INT_TYPE'], 0xFF)           # Edge-triggered
    await apb_write(dut, APB_ADDRESSES['INT_POLARITY'], 0x00)       # Active High
    await apb_write(dut, APB_ADDRESSES['INT_STATE'], (1 << GPIO_WIDTH) - 1)  # Clear any pending interrupts

    # Generate multiple simultaneous interrupts
    dut.gpio_in.value = 0x00  # Initial state
    for _ in range(3):
        await RisingEdge(dut.pclk)

    # Change multiple bits simultaneously
    gpio_change = 0xF0 | 0x0F  # Example pattern: upper and lower 4 bits change
    gpio_change_masked = gpio_change & ((1 << GPIO_WIDTH) - 1)
    dut.gpio_in.value = gpio_change_masked
    for _ in range(3):
        await RisingEdge(dut.pclk)

    # Calculate expected interrupts: bits that transitioned from 0 to 1
    # Since polarity is active high and edge-triggered, rising edges trigger interrupts
    transitions = gpio_change_masked
    expected_int_state = transitions

    # Perform APB read from INT_STATE
    read_data = await apb_read(dut, APB_ADDRESSES['INT_STATE'])
    actual_int_state = read_data

    # Check Interrupt State Register
    check_condition(
        actual_int_state == expected_int_state,
        f"FAIL: Not all interrupts captured. Expected: 0x{expected_int_state:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_int_state:0{(GPIO_WIDTH + 3) // 4}X}",
        "PASS: All interrupts captured successfully",
        test_failures
    )

    # Report failures if any
    if test_failures:
        failure_message = "\n".join(test_failures)
        logger.error(f"Test 9 completed with failures:\n{failure_message}")
        assert False, f"Some test cases failed. Check the log for details:\n{failure_message}"
    else:
        logger.info("Test 9 completed successfully")

@cocotb.test()
async def test10_reset_conditions(dut):
    """Test 10: Reset Conditions"""

    logger = dut._log
    logger.setLevel(logging.INFO)
    logger.info("Test 10: Reset Conditions")

    # Retrieve GPIO_WIDTH from DUT parameters
    GPIO_WIDTH = int(dut.GPIO_WIDTH.value)

    # Start the clock
    cocotb.start_soon(Clock(dut.pclk, 20, unit="ns").start())

    # Reset
    dut.preset_n.value = 0
    await Timer(50, unit='ns')  # Hold reset low for 50 ns
    dut.preset_n.value = 1

    # Initialize list to collect failures
    test_failures = []

    # Perform APB writes to set up GPIO and Interrupts before reset
    write_data = (0xA5A5A5A5 >> (32 - GPIO_WIDTH))
    write_en = (1 << GPIO_WIDTH) - 1
    await apb_write(dut, APB_ADDRESSES['DATA_OUT'], write_data)
    await apb_write(dut, APB_ADDRESSES['DATA_OUT_EN'], write_en)
    await apb_write(dut, APB_ADDRESSES['INT_ENABLE'], write_en)       # Enable all interrupts
    await apb_write(dut, APB_ADDRESSES['INT_STATE'], (1 << GPIO_WIDTH) - 1)  # Clear any pending interrupts

    # Assert reset
    dut.preset_n.value = 0
    for _ in range(2):
        await RisingEdge(dut.pclk)

    # Deassert reset
    dut.preset_n.value = 1
    for _ in range(2):
        await RisingEdge(dut.pclk)

    # Perform APB reads to verify reset
    # Data Output Register
    read_data = await apb_read(dut, APB_ADDRESSES['DATA_OUT'])
    expected_data = 0x00
    actual_data = read_data & ((1 << GPIO_WIDTH) - 1)
    check_condition(
        actual_data == expected_data,
        f"FAIL: Data Output Register not reset. Expected: 0x{expected_data:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_data:0{(GPIO_WIDTH + 3) // 4}X}",
        "PASS: Data Output Register reset correctly",
        test_failures
    )

    # Output Enable Register
    read_data = await apb_read(dut, APB_ADDRESSES['DATA_OUT_EN'])
    expected_en = 0x00
    actual_en = read_data & ((1 << GPIO_WIDTH) - 1)
    check_condition(
        actual_en == expected_en,
        f"FAIL: Output Enable Register not reset. Expected: 0x{expected_en:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_en:0{(GPIO_WIDTH + 3) // 4}X}",
        "PASS: Output Enable Register reset correctly",
        test_failures
    )

    # Interrupt Enable Register
    read_data = await apb_read(dut, APB_ADDRESSES['INT_ENABLE'])
    expected_en = 0x00
    actual_en = read_data & ((1 << GPIO_WIDTH) - 1)
    check_condition(
        actual_en == expected_en,
        f"FAIL: Interrupt Enable Register not reset. Expected: 0x{expected_en:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_en:0{(GPIO_WIDTH + 3) // 4}X}",
        "PASS: Interrupt Enable Register reset correctly",
        test_failures
    )

    # Interrupt State Register
    read_data = await apb_read(dut, APB_ADDRESSES['INT_STATE'])
    expected_int_state = 0x00
    actual_int_state = read_data & ((1 << GPIO_WIDTH) - 1)
    check_condition(
        actual_int_state == expected_int_state,
        f"FAIL: Interrupt State Register not reset. Expected: 0x{expected_int_state:0{(GPIO_WIDTH + 3) // 4}X}, "
        f"Got: 0x{actual_int_state:0{(GPIO_WIDTH + 3) // 4}X}",
        "PASS: Interrupt State Register reset correctly",
        test_failures
    )

    # Report failures if any
    if test_failures:
        failure_message = "\n".join(test_failures)
        logger.error(f"Test 10 completed with failures:\n{failure_message}")
        assert False, f"Some test cases failed. Check the log for details:\n{failure_message}"
    else:
        logger.info("PASS: All registers reset correctly")
        logger.info("Test 10 completed successfully")
