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

    typedef enum logic [2:0] {
        IDLE               = 3'd0,
        ITEM_SELECTION     = 3'd1,
        PAYMENT_VALIDATION = 3'd2,
        DISPENSING_ITEM    = 3'd3,
        RETURN_CHANGE      = 3'd4,
        RETURN_MONEY       = 3'd5
    } state_t;

    state_t state;

    logic [4:0] coins_accumulated;
    logic [4:0] selected_price;
    logic [2:0] selected_item_id;
    logic [4:0] change_calc;

    logic prev_item_button, prev_cancel;
    logic item_button_rise, cancel_rise;

    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            prev_item_button <= 0;
            prev_cancel <= 0;
        end else begin
            prev_item_button <= item_button;
            prev_cancel <= cancel;
        end
    end

    assign item_button_rise = item_button & ~prev_item_button;
    assign cancel_rise = cancel & ~prev_cancel;

    function automatic [4:0] get_price(input [2:0] item);
        case (item)
            3'd1: get_price = 5'd5;
            3'd2: get_price = 5'd10;
            3'd3: get_price = 5'd15;
            3'd4: get_price = 5'd20;
            default: get_price = 5'd0;
        endcase
    endfunction

    function automatic valid_coin(input [3:0] coin);
        case (coin)
            4'd1, 4'd2, 4'd5, 4'd10: valid_coin = 1;
            default: valid_coin = 0;
        endcase
    endfunction

    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            state             <= IDLE;
            coins_accumulated <= 0;
            selected_price    <= 0;
            selected_item_id  <= 0;
            change_calc       <= 0;
            dispense_item     <= 0;
            return_change     <= 0;
            item_price        <= 0;
            change_amount     <= 0;
            dispense_item_id  <= 0;
            error             <= 0;
            return_money      <= 0;
        end else begin
            // Default: clear one-cycle pulses
            dispense_item    <= 0;
            return_change    <= 0;
            error            <= 0;
            return_money     <= 0;

            case (state)
                IDLE: begin
                    coins_accumulated <= 0;
                    selected_price    <= 0;
                    selected_item_id  <= 0;
                    change_calc       <= 0;
                    change_amount     <= 0;
                    dispense_item_id  <= 0;
                    item_price        <= 0;

                    if (item_button_rise) begin
                        state <= ITEM_SELECTION;
                    end else if (coin_input != 0) begin
                        error <= 1;
                        state <= RETURN_MONEY;
                    end
                end

                ITEM_SELECTION: begin
                    if (cancel_rise) begin
                        error <= 1;
                        state <= RETURN_MONEY;
                    end else if (item_selected != 0) begin
                        if (get_price(item_selected) != 0) begin
                            selected_price   <= get_price(item_selected);
                            selected_item_id <= item_selected;
                            item_price       <= get_price(item_selected);
                            state            <= PAYMENT_VALIDATION;
                        end else begin
                            error <= 1;
                            state <= RETURN_MONEY;
                        end
                    end
                end

                PAYMENT_VALIDATION: begin
                    if (cancel_rise) begin
                        error <= 1;
                        state <= RETURN_MONEY;
                    end else if (coin_input != 0) begin
                        if (valid_coin(coin_input)) begin
                            if ((coins_accumulated + coin_input[4:0]) >= selected_price) begin
                                coins_accumulated <= coins_accumulated + coin_input[4:0];
                                change_calc       <= (coins_accumulated + coin_input[4:0]) - selected_price;
                                state             <= DISPENSING_ITEM;
                            end else begin
                                coins_accumulated <= coins_accumulated + coin_input[4:0];
                            end
                        end else begin
                            error <= 1;
                            state <= RETURN_MONEY;
                        end
                    end
                end

                DISPENSING_ITEM: begin
                    dispense_item    <= 1;
                    dispense_item_id <= selected_item_id;
                    change_amount    <= change_calc;
                    if (change_calc > 0) begin
                        state <= RETURN_CHANGE;
                    end else begin
                        state <= IDLE;
                    end
                end

                RETURN_CHANGE: begin
                    return_change <= 1;
                    change_amount <= change_amount;
                    state         <= IDLE;
                end

                RETURN_MONEY: begin
                    if (coins_accumulated > 0) begin
                        return_money <= 1;
                    end
                    state <= IDLE;
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
