module vending_machine (
    input  logic        clk,
    input  logic        rst,
    input  logic        item_button,
    input  logic [2:0]  item_selected,
    input  logic [3:0]  coin_input,
    input  logic        cancel,
    output logic        dispense_item,
    output logic        return_change,
    output logic [4:0]  item_price,
    output logic [4:0]  change_amount,
    output logic [2:0]  dispense_item_id,
    output logic        error,
    output logic        return_money
);

    // State encoding
    typedef enum logic [2:0] {
        IDLE               = 3'd0,
        ITEM_SELECTION     = 3'd1,
        PAYMENT_VALIDATION = 3'd2,
        DISPENSING_ITEM    = 3'd3,
        RETURN_CHANGE      = 3'd4,
        RETURN_MONEY       = 3'd5
    } state_t;

    state_t current_state, next_state;

    // Internal registers
    logic [4:0] coins_accumulated;
    logic [4:0] item_price_reg;
    logic [2:0] item_id_reg;
    logic [4:0] change_amount_reg;

    // Edge detection for item_button and cancel
    logic item_button_prev;
    logic cancel_prev;
    logic item_button_rise;
    logic cancel_rise;

    // Intermediate signals for next state logic
    logic [4:0] next_coins_accumulated;
    logic [4:0] next_item_price_reg;
    logic [2:0] next_item_id_reg;
    logic [4:0] next_change_amount_reg;

    // Rising edge detection
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            item_button_prev <= 1'b0;
            cancel_prev      <= 1'b0;
        end else begin
            item_button_prev <= item_button;
            cancel_prev      <= cancel;
        end
    end

    assign item_button_rise = item_button & ~item_button_prev;
    assign cancel_rise      = cancel & ~cancel_prev;

    // Item price lookup
    function automatic [4:0] get_item_price(input [2:0] item_id);
        case (item_id)
            3'b001: get_item_price = 5'd5;
            3'b010: get_item_price = 5'd10;
            3'b011: get_item_price = 5'd15;
            3'b100: get_item_price = 5'd20;
            default: get_item_price = 5'd0;
        endcase
    endfunction

    // Coin validity check
    function automatic logic is_valid_coin(input [3:0] coin);
        case (coin)
            4'd1, 4'd2, 4'd5, 4'd10: is_valid_coin = 1'b1;
            default: is_valid_coin = 1'b0;
        endcase
    endfunction

    // State register
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            current_state       <= IDLE;
            coins_accumulated   <= 5'd0;
            item_price_reg      <= 5'd0;
            item_id_reg         <= 3'd0;
            change_amount_reg   <= 5'd0;
        end else begin
            current_state       <= next_state;
            coins_accumulated   <= next_coins_accumulated;
            item_price_reg      <= next_item_price_reg;
            item_id_reg         <= next_item_id_reg;
            change_amount_reg   <= next_change_amount_reg;
        end
    end

    // Next state and output logic
    always_comb begin
        // Default outputs
        dispense_item       = 1'b0;
        return_change       = 1'b0;
        error               = 1'b0;
        return_money        = 1'b0;
        item_price          = item_price_reg;
        change_amount       = change_amount_reg;
        dispense_item_id    = item_id_reg;

        // Default next state values
        next_state              = current_state;
        next_coins_accumulated  = coins_accumulated;
        next_item_price_reg     = item_price_reg;
        next_item_id_reg        = item_id_reg;
        next_change_amount_reg  = change_amount_reg;

        case (current_state)
            IDLE: begin
                item_price       = 5'd0;
                change_amount    = 5'd0;
                dispense_item_id = 3'd0;

                if (item_button_rise) begin
                    next_state = ITEM_SELECTION;
                end else if (coin_input != 4'd0) begin
                    // Inserting coins without item selection
                    error = 1'b1;
                    next_state = RETURN_MONEY;
                end
            end

            ITEM_SELECTION: begin
                if (cancel_rise) begin
                    error = 1'b1;
                    next_state = RETURN_MONEY;
                end else if (item_selected != 3'b000) begin
                    // Item selection detected
                    if (item_selected >= 3'b001 && item_selected <= 3'b100) begin
                        next_item_id_reg    = item_selected;
                        next_item_price_reg = get_item_price(item_selected);
                        item_price          = get_item_price(item_selected);
                        next_state          = PAYMENT_VALIDATION;
                    end else begin
                        error      = 1'b1;
                        next_state = RETURN_MONEY;
                    end
                end
            end

            PAYMENT_VALIDATION: begin
                item_price = item_price_reg;

                if (cancel_rise) begin
                    error = 1'b1;
                    next_state = RETURN_MONEY;
                end else if (coin_input != 4'd0) begin
                    if (is_valid_coin(coin_input)) begin
                        next_coins_accumulated = coins_accumulated + {1'b0, coin_input};
                        if (coins_accumulated + {1'b0, coin_input} >= item_price_reg) begin
                            next_state = DISPENSING_ITEM;
                        end
                    end else begin
                        // Invalid coin
                        error        = 1'b1;
                        return_money = 1'b1;
                        next_state   = IDLE;
                        // Reset internal state
                        next_coins_accumulated = 5'd0;
                        next_item_price_reg    = 5'd0;
                        next_item_id_reg       = 3'd0;
                        next_change_amount_reg = 5'd0;
                    end
                end
            end

            DISPENSING_ITEM: begin
                dispense_item    = 1'b1;
                dispense_item_id = item_id_reg;
                item_price       = item_price_reg;

                if (coins_accumulated > item_price_reg) begin
                    next_change_amount_reg = coins_accumulated - item_price_reg;
                    next_state = RETURN_CHANGE;
                end else begin
                    // No change needed
                    next_state             = IDLE;
                    next_coins_accumulated = 5'd0;
                    next_item_price_reg    = 5'd0;
                    next_item_id_reg       = 3'd0;
                    next_change_amount_reg = 5'd0;
                end
            end

            RETURN_CHANGE: begin
                return_change = 1'b1;
                change_amount = change_amount_reg;
                item_price    = item_price_reg;

                next_state             = IDLE;
                next_coins_accumulated = 5'd0;
                next_item_price_reg    = 5'd0;
                next_item_id_reg       = 3'd0;
                next_change_amount_reg = 5'd0;
            end

            RETURN_MONEY: begin
                if (coins_accumulated > 5'd0) begin
                    return_money = 1'b1;
                end
                next_state             = IDLE;
                next_coins_accumulated = 5'd0;
                next_item_price_reg    = 5'd0;
                next_item_id_reg       = 3'd0;
                next_change_amount_reg = 5'd0;
            end

            default: begin
                next_state = IDLE;
            end
        endcase
    end

endmodule
