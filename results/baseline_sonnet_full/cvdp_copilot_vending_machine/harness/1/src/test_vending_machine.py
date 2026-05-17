import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly , Timer

import harness_library as hrs_lb
import random

# Task to select item
async def select_item(dut, item):
    await RisingEdge(dut.clk)
    dut.item_button.value = 1   
    await RisingEdge(dut.clk)
    dut.item_selected.value = item
    dut.item_button.value = 0
    await RisingEdge(dut.clk)

# Task to insert coins
async def insert_coins(dut, amount):
    dut.coin_input.value = amount
    await RisingEdge(dut.clk)
    dut.coin_input.value = 0
    await RisingEdge(dut.clk)

# Task to simulate cancel button press
async def cancel_purchase(dut):
    dut.cancel.value = 1
    await RisingEdge(dut.clk)
    dut.cancel.value = 0

# Task to check if the item is dispensed and no errors occurred
async def check_dispense(dut, expected_item_id):
    await RisingEdge(dut.clk)
    assert dut.dispense_item.value == 1, f"Expected item to be dispensed!"
    await RisingEdge(dut.clk)
    assert dut.dispense_item_id.value == expected_item_id, f"Dispensed item ID mismatch, got {dut.dispense_item_id.value}, expected {expected_item_id}"
    assert dut.error.value == 0, f"Error signal should not be high!"
    assert dut.return_change.value == 0, "Change should not be returned change in this clock cycle"
    print(f"Dispense_item_id  - {int(dut.dispense_item_id.value)} , Error - {int(dut.error.value)} ")

# Task to check if the correct change is returned
async def check_change(dut, expected_change): 
    if expected_change > 0:
        await RisingEdge(dut.clk)
        assert dut.return_change.value == 1, "Change should be returned"
        print(f"expected_chang amount - {int(expected_change)}")
        print(f"Return change amount - {int(dut.change_amount.value)}")
        assert dut.change_amount.value == expected_change, f"Expected change {expected_change}, but got {dut.change_amount.value}"
    else:
        assert dut.return_change.value == 0, "No change should be returned"
    await RisingEdge(dut.clk)
    assert dut.return_change.value == 0, "Change should not be returned after one cycle"
    assert dut.change_amount.value == 0, f"Expected change {0}, but got {dut.change_amount.value}"

# Task to randomly buy an item with random coins and validate results
async def random_purchase(dut):
    item_id = random.randint(1, 4)
    item_prices = {1: 5, 2: 10, 3: 15, 4: 20}
    expected_price = item_prices[item_id]
    dut._log.info(f"Randomly selecting item {item_id}, expected price: {expected_price}")

    await select_item(dut, item_id)

    # Randomly insert coins until we meet or exceed the price
    total_inserted = 0
    while total_inserted < expected_price:
        coin = random.choice([1, 2, 5, 10])  
        await insert_coins(dut, coin)
        total_inserted += coin
        dut._log.info(f"Inserted coin: {coin}, total so far: {total_inserted}")

    await check_dispense(dut, item_id)
    expected_change = total_inserted - expected_price   

    await check_change(dut, expected_change)
    await Timer(50, unit='ns')

# Task to randomly cancel a purchase
async def random_cancel_purchase(dut):
    item_prices = {1: 5, 2: 10, 3: 15, 4: 20}
    item_id = random.randint(1, 4)
    expected_price = item_prices[item_id]

    dut._log.info(f"Randomly selecting item {item_id} with price {expected_price} and canceling the operation")
    await select_item(dut, item_id)
    dut.coin_input.value = 1
    await RisingEdge(dut.clk)
    dut.coin_input.value = 0
    await RisingEdge(dut.clk)
    dut.coin_input.value = 2
    await RisingEdge(dut.clk) 
    dut.coin_input.value = 0
    await RisingEdge(dut.clk)
    await cancel_purchase(dut)
    await RisingEdge(dut.clk)
    assert dut.error.value == 1, "Error should be high for cancellation"
    await RisingEdge(dut.clk)
    assert dut.return_money.value == 1, "Expected money to be returned after cancellation"
    assert dut.error.value == 0, "Error should not be high for cancellation after clock"
    await RisingEdge(dut.clk)
    assert dut.return_money.value == 0, "when cancle Expected money not be returned after clock"
    await Timer(50, unit='ns')

# Task to simulate invalid item selection
async def invalid_item_selection(dut):
    invalid_item_id = random.choice([0, 6, 5, 7])
    dut._log.info(f"Selecting invalid item ID: {invalid_item_id}")
    await select_item(dut, invalid_item_id)
    dut.coin_input.value = 2
    await RisingEdge(dut.clk)
    dut.coin_input.value = 0
    await RisingEdge(dut.clk)
    assert dut.error.value == 1, "Error should be high for invalid item selection"
    assert dut.dispense_item.value == 0, "No item should be dispensed"
    await insert_coins(dut, 0)
    assert dut.error.value == 0, "Error should not be high for invalid item selection after clock" 
    await Timer(50, unit='ns')

# Task to simulate multiple purchases without resetting the machine
async def multiple_purchases_without_reset(dut):
    for _ in range(3):  
        await random_purchase(dut)
        await RisingEdge(dut.clk) 
    await Timer(50, unit='ns')

# Task to simulate random coin validation
async def random_coin_validation(dut):
    coin = random.choice([1,2,5,7,10]) 
    dut._log.info(f"Inserting random coin value: {coin}")

    await select_item(dut, random.randint(1, 4)) 
    await insert_coins(dut, coin)
    if coin == 7:
        assert dut.error.value == 1, "Expected error for invalid coin input"
    else:
        assert dut.error.value == 0, "Unexpected error for valid coin input"
    await insert_coins(dut, 0)
    await Timer(50, unit='ns')

async def reset_during_transaction(dut):
    await select_item(dut, 3)
    await insert_coins(dut, 5)
    await insert_coins(dut, 0)
    dut._log.info("Resetting the machine during the transaction.")
    dut.rst.value = 1
    dut.item_selected.value = 0
    await Timer(30, unit='ns')

    assert dut.dispense_item.value == 0, "No item should be dispensed after reset"
    assert dut.return_money.value == 0, "No money should be returned after reset"
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    dut._log.info("reset_during_transaction: Machine successfully reset during transaction.")
    await Timer(50, unit='ns')

# Task to simulate inserting coins without selecting an item
async def insert_coins_without_selecting_item(dut):
    cocotb.log.info("Simulating coin insertion without selecting an item")
    await RisingEdge(dut.clk)
    dut.item_button.value = 1   
    dut.item_selected.value = 0
    await RisingEdge(dut.clk)
    dut.item_button.value = 0
    await RisingEdge(dut.clk)
    await insert_coins(dut, 10)

    assert dut.error.value == 1, "Error should be raised when inserting coins without selecting an item"
    await RisingEdge(dut.clk)  
    assert dut.error.value == 0, "Error should  not be raised when inserting coins without selecting an item after a clock"
    assert dut.return_money.value == 1, "Money should be returned when no item is selected"
    await insert_coins(dut, 0)
    await RisingEdge(dut.clk)


    assert dut.dispense_item.value == 0, "No item should be dispensed without item selection"
    assert dut.return_money.value == 0, "Money should not be returned when no item is selected after a clock"
    cocotb.log.info("Simulating coin insertion without selecting an item: Coins returned when no item is selected.")
    await Timer(50, unit='ns')

# Task to cancel after selecting an item
async def cancel_after_selecting_item(dut):
    item_id = 2
    await select_item(dut, item_id)
    dut._log.info(f"Selected item {item_id}")

    dut.cancel.value = 1
    await RisingEdge(dut.clk)
    dut.cancel.value = 0
    await RisingEdge(dut.clk)
    assert dut.error.value == 1, "Expected error signal to be set after cancellation"
    await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    assert dut.error.value == 0, "Expected error signal not be set in cancellation after a clock  "
    await Timer(50, unit='ns')   


# Task to insert coins without selecting an item
async def insert_coins_without_item_button(dut):
    coin = 5
    await RisingEdge(dut.clk) 
    dut.item_selected.value = 0
    await RisingEdge(dut.clk) 
    dut.coin_input.value = coin
    await RisingEdge(dut.clk)
    dut.coin_input.value = 0
    await RisingEdge(dut.clk) 
    assert dut.error.value == 1, "Expected error signal to be set when coins are inserted without item selection"
    dut._log.info(f"Inserted coin: {coin} without selecting an item")
    await RisingEdge(dut.clk)   
    assert dut.return_money.value == 1, "Expected return_money signal to be high when no item selected"
    assert dut.error.value == 0, "Expected error signal not be set when coins are inserted without item selection after a clock"
    dut._log.info("Coins returned successfully when inserted without item selection.")
    await RisingEdge(dut.clk) 
    assert dut.return_money.value == 0, "Expected return_money signal not be high when no item selected after a clock"
    await Timer(50, unit='ns')

# Task to insert an invalid coin during payment validation
async def insert_invalid_coin_during_payment_validation(dut):
    item_id = 1
    await select_item(dut, item_id)
    dut._log.info(f"Selected item {item_id}")
    await insert_coins(dut, 1)
    dut.coin_input.value = 3
    await RisingEdge(dut.clk)   
    dut.coin_input.value = 0 
    await RisingEdge(dut.clk) 
    assert dut.return_money.value == 1, "Expected return_money signal to be high after inserting invalid coin"
    assert dut.error.value == 1, "Expected error signal to be set after inserting invalid coin"
    dut._log.info("Invalid coin insertion handled successfully.")
    await RisingEdge(dut.clk) 

    assert dut.return_money.value == 0, "Expected return_money signal not be high after inserting invalid coin after a clock"
    assert dut.error.value == 0, "Expected error signal not be set after inserting invalid coin after a clock"
    await Timer(50, unit='ns') 


@cocotb.test()
async def test_vending_machine(dut):

    print("start of vending machine")

    # Start the clock with a 10ns time period (100 MHz clock)
    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())

    # Initialize the DUT signals with default 0
    await hrs_lb.dut_init(dut)

    # Reset the DUT rst_n signal
    await hrs_lb.reset_dut(dut.rst, duration_ns=25, active=False)

    await RisingEdge(dut.clk) 

    await random_purchase(dut)

    await random_cancel_purchase(dut)

    await invalid_item_selection(dut)

    await multiple_purchases_without_reset(dut)

    await random_coin_validation(dut)

    await reset_during_transaction(dut)

    await random_purchase(dut)

    await insert_coins_without_selecting_item(dut)

    await cancel_after_selecting_item(dut)

    await insert_coins_without_item_button(dut)

    await insert_invalid_coin_during_payment_validation(dut)
