module vending_machine (
    input wire clk,
    input wire rst,
    input wire item_button,
    input wire [2:0] item_selected,
    input wire [3:0] coin_input,
    input wire cancel,

    output reg dispense_item,
    output reg return_change,
    output reg [4:0] item_price,
    output reg [4:0] change_amount,
    output reg [2:0] dispense_item_id,
    output reg error,
    output reg return_money
);

    // Define states
    typedef enum logic [2:0] {
        IDLE = 3'b000,
        ITEM_SELECTION = 3'b001,
        PAYMENT_VALIDATION = 3'b010,
        DISPENSING_ITEM = 3'b011,
        RETURN_CHANGE = 3'b100,
        RETURN_MONEY = 3'b101
    } state_t;

    // Internal registers
    state_t current_state, next_state;
    reg [4:0] coins_accumulated;
    reg [4:0] selected_item_price;
    reg item_button_r, cancel_r;
    reg next_is_error;

    // Wire for valid coin check
    wire coin_valid = (coin_input == 4'd1 || coin_input == 4'd2 || coin_input == 4'd5 || coin_input == 4'd10);
    wire [4:0] coins_after = coins_accumulated + coin_input;

    // Item prices
    always @(*) begin
        case (item_selected)
            3'b001: selected_item_price = 5'd5;   // Item 1 price
            3'b010: selected_item_price = 5'd10;  // Item 2 price
            3'b011: selected_item_price = 5'd15;  // Item 3 price
            3'b100: selected_item_price = 5'd20;  // Item 4 price
            default: selected_item_price = 5'd0;   // Invalid item
        endcase
    end

    // Next state logic (purely combinational, no output assignments)
    always @(*) begin
        next_state = current_state;
        next_is_error = 1'b0;
        case (current_state)
            IDLE: begin
                if (item_button && !item_button_r) begin
                    next_state = ITEM_SELECTION;
                end else if (coin_input != 4'd0) begin
                    next_state = RETURN_MONEY;
                    next_is_error = 1'b1;
                end
            end
            ITEM_SELECTION: begin
                if (cancel && !cancel_r) begin
                    next_state = RETURN_MONEY;
                    next_is_error = 1'b1;
                end else if (item_selected != 3'b000 && item_selected <= 3'b100) begin
                    next_state = PAYMENT_VALIDATION;
                end else if (item_selected != 3'b000) begin
                    next_state = RETURN_MONEY;
                    next_is_error = 1'b1;
                end
            end
            PAYMENT_VALIDATION: begin
                if (cancel && !cancel_r) begin
                    next_state = RETURN_MONEY;
                    next_is_error = 1'b1;
                end else if (coin_input != 4'd0 && !coin_valid) begin
                    next_state = RETURN_MONEY;
                    next_is_error = 1'b1;
                end else if (coin_input != 4'd0 && coin_valid && coins_after >= item_price) begin
                    next_state = DISPENSING_ITEM;
                end else if (coin_input == 4'd0 && coins_accumulated >= item_price && coins_accumulated > 0) begin
                    next_state = DISPENSING_ITEM;
                end
            end
            DISPENSING_ITEM: begin
                if (change_amount > 0) begin
                    next_state = RETURN_CHANGE;
                end else begin
                    next_state = IDLE;
                end
            end
            RETURN_CHANGE: begin
                next_state = IDLE;
            end
            RETURN_MONEY: begin
                next_state = IDLE;
            end
            default: next_state = IDLE;
        endcase
    end

    // State transition and output logic (clocked)
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            current_state <= IDLE;
            coins_accumulated <= 5'd0;
            item_price <= 5'd0;
            change_amount <= 5'd0;
            dispense_item <= 1'b0;
            return_change <= 1'b0;
            dispense_item_id <= 3'b0;
            error <= 1'b0;
            return_money <= 1'b0;
        end else begin
            // Default: clear one-cycle signals
            dispense_item <= 1'b0;
            return_change <= 1'b0;
            error <= 1'b0;
            return_money <= 1'b0;

            // Accumulate coins when in PAYMENT_VALIDATION, regardless of next_state
            if (current_state == PAYMENT_VALIDATION) begin
                if (coin_valid && coin_input != 4'd0) begin
                    coins_accumulated <= coins_accumulated + coin_input;
                end
            end

            current_state <= next_state;

            case (next_state)
                IDLE: begin
                    coins_accumulated <= 5'd0;
                    item_price <= 5'd0;
                    change_amount <= 5'd0;
                end
                ITEM_SELECTION: begin
                    coins_accumulated <= 5'd0;
                end
                PAYMENT_VALIDATION: begin
                    // Set item price when transitioning into payment validation
                    if (current_state == ITEM_SELECTION) begin
                        item_price <= selected_item_price;
                        dispense_item_id <= item_selected;
                    end
                    // Coin accumulation is handled above unconditionally
                end
                DISPENSING_ITEM: begin
                    dispense_item <= 1'b1;
                    // Calculate change: if transitioning from PAYMENT_VALIDATION,
                    // coins_accumulated will be updated by the unconditional block above
                    // but since both are in the same always block, we need to use coins_after
                    if (current_state == PAYMENT_VALIDATION) begin
                        if (coin_valid && coin_input != 4'd0) begin
                            if (coins_after > item_price) begin
                                change_amount <= coins_after - item_price;
                            end else begin
                                change_amount <= 5'd0;
                            end
                        end else begin
                            if (coins_accumulated > item_price) begin
                                change_amount <= coins_accumulated - item_price;
                            end else begin
                                change_amount <= 5'd0;
                            end
                        end
                    end else begin
                        if (coins_accumulated > item_price) begin
                            change_amount <= coins_accumulated - item_price;
                        end else begin
                            change_amount <= 5'd0;
                        end
                    end
                end
                RETURN_CHANGE: begin
                    return_change <= 1'b1;
                end
                RETURN_MONEY: begin
                    error <= 1'b1;
                    if (coins_accumulated > 0) begin
                        return_money <= 1'b1;
                    end
                end
            endcase
        end
    end

    // Register previous values of item_button and cancel for edge detection
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            item_button_r <= 1'b0;
            cancel_r <= 1'b0;
        end else begin
            item_button_r <= item_button;
            cancel_r <= cancel;
        end
    end

endmodule
