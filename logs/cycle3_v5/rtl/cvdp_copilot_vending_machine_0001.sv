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
    reg [4:0] latched_price;
    reg [2:0] latched_item_id;
    reg item_button_r, cancel_r;

    // Item prices (combinational)
    always @(*) begin
        case (item_selected)
            3'b001: selected_item_price = 5'd10;
            3'b010: selected_item_price = 5'd15;
            3'b011: selected_item_price = 5'd20;
            3'b100: selected_item_price = 5'd25;
            default: selected_item_price = 5'd0;
        endcase
    end

    // State transition and output logic
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
            latched_price <= 5'd0;
            latched_item_id <= 3'b0;
        end else begin
            current_state <= next_state;
            // Default: clear one-cycle signals
            dispense_item <= 1'b0;
            return_change <= 1'b0;
            error <= 1'b0;
            return_money <= 1'b0;

            // Coin accumulation: accumulate when in PAYMENT_VALIDATION and coin is valid
            if (current_state == PAYMENT_VALIDATION) begin
                if (coin_input == 4'd1 || coin_input == 4'd2 || coin_input == 4'd5 || coin_input == 4'd10) begin
                    coins_accumulated <= coins_accumulated + coin_input;
                end
            end

            case (current_state)
                IDLE: begin
                    if (next_state == IDLE) begin
                        coins_accumulated <= 5'd0;
                        item_price <= 5'd0;
                        change_amount <= 5'd0;
                        latched_price <= 5'd0;
                        latched_item_id <= 3'b0;
                    end
                    // If transitioning to RETURN_MONEY due to coin insertion without item selection
                    if (next_state == RETURN_MONEY) begin
                        error <= 1'b1;
                    end
                end
                ITEM_SELECTION: begin
                    if (next_state == PAYMENT_VALIDATION) begin
                        // Latch the price and item ID when transitioning to PAYMENT_VALIDATION
                        latched_price <= selected_item_price;
                        latched_item_id <= item_selected;
                        dispense_item_id <= item_selected;
                        item_price <= selected_item_price;
                        coins_accumulated <= 5'd0;
                    end else if (next_state == RETURN_MONEY) begin
                        error <= 1'b1;
                    end
                end
                PAYMENT_VALIDATION: begin
                    if (next_state == RETURN_MONEY) begin
                        error <= 1'b1;
                        // Return money for invalid coin or cancel
                        if (coins_accumulated > 5'd0) begin
                            return_money <= 1'b1;
                        end
                    end else if (next_state == DISPENSING_ITEM) begin
                        // coins_accumulated will be updated above with the coin_input
                        // We need to store the final accumulated amount
                        // The coin accumulation block above handles this
                    end
                end
                DISPENSING_ITEM: begin
                    dispense_item <= 1'b1;
                    // At this point coins_accumulated already has all coins including last one
                    if (coins_accumulated > latched_price) begin
                        change_amount <= coins_accumulated - latched_price;
                    end else begin
                        change_amount <= 5'd0;
                    end
                    if (next_state == IDLE) begin
                        // No change needed
                    end
                end
                RETURN_CHANGE: begin
                    return_change <= 1'b1;
                    if (next_state == IDLE) begin
                        coins_accumulated <= 5'd0;
                        item_price <= 5'd0;
                        change_amount <= 5'd0;
                        latched_price <= 5'd0;
                        latched_item_id <= 3'b0;
                    end
                end
                RETURN_MONEY: begin
                    if (coins_accumulated > 5'd0) begin
                        return_money <= 1'b1;
                    end
                    if (next_state == IDLE) begin
                        coins_accumulated <= 5'd0;
                        item_price <= 5'd0;
                        change_amount <= 5'd0;
                        latched_price <= 5'd0;
                        latched_item_id <= 3'b0;
                    end
                end
            endcase
        end
    end

    // Next state logic
    always @(*) begin
        next_state = current_state;
        case (current_state)
            IDLE: begin
                if (item_button && !item_button_r) begin
                    next_state = ITEM_SELECTION;
                end else if (coin_input != 4'd0) begin
                    next_state = RETURN_MONEY;
                end
            end
            ITEM_SELECTION: begin
                if (cancel && !cancel_r) begin
                    next_state = RETURN_MONEY;
                end else if (item_selected >= 3'b001 && item_selected <= 3'b100) begin
                    next_state = PAYMENT_VALIDATION;
                end else if (item_selected != 3'b000) begin
                    next_state = RETURN_MONEY;
                end
            end
            PAYMENT_VALIDATION: begin
                if (cancel && !cancel_r) begin
                    next_state = RETURN_MONEY;
                end else if (coin_input != 4'd0 && !(coin_input == 4'd1 || coin_input == 4'd2 || coin_input == 4'd5 || coin_input == 4'd10)) begin
                    next_state = RETURN_MONEY;
                end else if ((coin_input == 4'd1 || coin_input == 4'd2 || coin_input == 4'd5 || coin_input == 4'd10) &&
                             (coins_accumulated + coin_input) >= latched_price) begin
                    next_state = DISPENSING_ITEM;
                end
            end
            DISPENSING_ITEM: begin
                if (coins_accumulated > latched_price) begin
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
