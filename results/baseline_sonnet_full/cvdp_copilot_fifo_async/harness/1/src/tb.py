import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge
    
# Global Queue
q = []

async def configure_clocks(dut, w_period, r_period):

    # Reset the Clock Configuration
    dut.w_clk.value = 0
    dut.r_clk.value = 0
    await Timer(10, unit="ns")
    
    # Start the clock
    w_clk = cocotb.start_soon(Clock(dut.w_clk, w_period, unit='ns', period_high=(w_period+1)//2 if w_period%2 else w_period//2).start())
    r_clk = cocotb.start_soon(Clock(dut.r_clk, r_period, unit='ns', period_high=(r_period+1)//2 if r_period%2 else r_period//2).start())

    dut._log.info("Clocks initialized.")
    return (w_clk, r_clk)

async def configure_resets(dut):

    # Reset input interface
    dut.w_rst.value  = 1
    dut.r_rst.value  = 1
    dut.w_inc.value  = 0
    dut.r_inc.value  = 0
    dut.w_data.value = 0

    # Reset the DUT
    await Timer(100, unit="ns")
    dut.w_rst.value = 0
    dut.r_rst.value = 0
    dut._log.info("Resets initialized, ready for sequential value tests.")

async def write_data(dut, w_data):

    try:
        await FallingEdge(dut.w_clk)
        dut.w_data.value = w_data
        dut.w_inc.value  = 1
        await FallingEdge(dut.w_clk)
    finally:
        dut._log.info(f"Wrote {hex(w_data)} in w_data bus.")
        dut.w_inc.value  = 0

def read_data(dut, expected_data):

    assert dut.r_data.value  == expected_data, "Wrong domain transitioning"
    dut._log.info(f"Successfully read {hex(expected_data)} and prepared the next read.")

# ----------------------------------------
# - Random Test infrastructure
# ----------------------------------------

async def w_test(dut, tests):

    dut._log.info("Starting w_test thread...")
    
    try:
        width = 2 ** int(dut.DATA_WIDTH.value)
    
        for _ in range(tests):
            w_data = random.randint(0, width - 1)
    
            # Asynchronous start write_func
            if dut.w_full.value == 0:
                await write_data(dut, w_data)
                q.append(w_data)
    
            else:
                dut._log.info(f"FIFO is full, skipping new data write.")
                await FallingEdge(dut.w_clk)
    finally:
        dut._log.info("Finished to execute w_test thread.")

async def r_test(dut, tests):

    dut._log.info("Starting r_test thread...")
    
    try:
        len_q = int(dut.DEPTH.value)
    
        for _ in range(tests):
    
            # Check if contains data to be checked
            if len(q) > 0 and (dut.r_empty.value == 0):
    
                r_data = int(q.pop(0))
                read_data(dut, r_data)
                dut.r_inc.value = 1
    
            else:
                dut._log.info(f"Detected empty FIFO, skipping new data read.")
                dut.r_inc.value = 0
    
            # Synchronize with falling edge
            await FallingEdge(dut.r_clk)
    
    finally:
        dut._log.info("Finished to execute r_test thread.")
        
# ----------------------------------------
# - Basic Test
# ----------------------------------------

@cocotb.test()
async def test_empty(dut):

    w_clk = random.randint(10, 20)
    r_clk = random.randint(10, 20)

    # Configure clocks and resets
    (w_clk, r_clk) = await configure_clocks(dut, w_clk, r_clk)
    await configure_resets(dut)

    len_q = random.randint(2, int(dut.DEPTH.value))
    width = 2 ** int(dut.DATA_WIDTH.value)
    dut._log.info(f"Test Empty Started, executing {len_q} read and writes.")

    assert dut.w_full.value == 0,  "FIFO should not be full. Test just started, no data was driven."
    assert dut.r_empty.value == 1, "FIFO should be empty. Test just started, no data was driven."

    # Synchronize with write clock
    await FallingEdge(dut.w_clk)
    
    try:

        for _ in range(len_q):
            w_data = random.randint(0, width - 1)
            
            dut.w_inc.value  = 1
            dut.w_data.value = w_data
            await FallingEdge(dut.w_clk)

    finally:
        dut._log.info("Finished to write data in FIFO.")

    # Stop driving new data
    dut.w_inc.value = 0

    # Synchronize with read clock
    await FallingEdge(dut.r_clk)
    await FallingEdge(dut.r_clk)
    await FallingEdge(dut.r_clk)
    
    try:
        for _ in range(len_q):
            dut.r_inc.value = 1
            await FallingEdge(dut.r_clk)

    finally:
        dut._log.info("Finished to read data from FIFO.")
    
    # Stop requesting new data
    dut.r_inc.value = 0
    dut.w_inc.value = 0
    
    # Fifo should be empty
    await FallingEdge(dut.r_clk)
    await FallingEdge(dut.r_clk)
    
    assert dut.r_empty.value == 1, "All datas has already been retrieved. FIFO should be empty."

    w_clk.kill()
    r_clk.kill()
    
@cocotb.test()
async def test_basic(dut):

    w_clk = random.randint(10, 20)
    r_clk = random.randint(10, 20)
    
    # Configure clocks and resets
    (w_clk, r_clk) = await configure_clocks(dut, w_clk, r_clk)
    await configure_resets(dut)

    # Asynchronous start write_func
    # cocotb.start_soon(write_data(dut, 0xDEADBEAF))
    await write_data(dut, 0xDEADBEAF)

    # Wait clock transitioning
    for _ in range(2):
        await FallingEdge(dut.r_clk)

    await FallingEdge(dut.r_clk)
    read_data(dut, 0xDEADBEAF)

    w_clk.kill()
    r_clk.kill()

@cocotb.test()
async def test_full(dut):

    w_clk = random.randint(10, 20)
    r_clk = random.randint(10, 20)

    # Configure clocks and resets
    (w_clk, r_clk) = await configure_clocks(dut, w_clk, r_clk)
    await configure_resets(dut)

    len_q = int(dut.DEPTH.value)
    width = 2 ** int(dut.DATA_WIDTH.value)

    assert dut.w_full.value == 0,  "FIFO should not be full. Test just started, no data was driven."
    assert dut.r_empty.value == 1, "FIFO should be empty. Test just started, no data was driven."

    # Synchronize with write clock
    await FallingEdge(dut.w_clk)

    try:
        for _ in range(len_q):
            w_data = random.randint(0, width - 1)
            
            dut.w_inc.value  = 1
            dut.w_data.value = w_data
            await FallingEdge(dut.w_clk)

    finally:
        dut._log.info("Finished to write data into FIFO")

    # FIFO should be full
    await FallingEdge(dut.w_clk)
    assert dut.w_full.value == 1, "FIFO should be full with this amount of data."

    w_clk.kill()
    r_clk.kill()

@cocotb.test()
async def test_random(dut):

    w_clk = random.randint(10, 20)
    r_clk = random.randint(10, 20)

    # Configure clocks and resets
    (w_clk, r_clk) = await configure_clocks(dut, w_clk, r_clk)
    await configure_resets(dut)

    w_task = cocotb.start_soon(w_test(dut, 100))
    r_task = cocotb.start_soon(r_test(dut, 100))

    # Write domain finishes the test.
    for _ in range(100):
        await FallingEdge(dut.w_clk)

    # Succesfully ends the test
    r_task.kill()
    w_task.kill()
    
    w_clk.kill()
    r_clk.kill()
