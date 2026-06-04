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
    logic [4:0] coins_acc;
    logic [4:0] price_reg;
    logic [2:0] item_id_reg;
    logic prev_item_button;
    logic prev_cancel;
    logic item_button_rise;
    logic cancel_rise;

    assign item_button_rise = item_button & ~prev_item_button;
    assign cancel_rise      = cancel & ~prev_cancel;

    function automatic logic [4:0] get_price(input logic [2:0] id);
        case (id)
            3'd1: get_price = 5'd5;
            3'd2: get_price = 5'd10;
            3'd3: get_price = 5'd15;
            3'd4: get_price = 5'd20;
            default: get_price = 5'd0;
        endcase
    endfunction

    function automatic logic valid_coin(input logic [3:0] c);
        case (c)
            4'd1, 4'd2, 4'd5, 4'd10: valid_coin = 1'b1;
            default: valid_coin = 1'b0;
        endcase
    endfunction

    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            state            <= IDLE;
            coins_acc        <= 0;
            price_reg        <= 0;
            item_id_reg      <= 0;
            prev_item_button <= 0;
            prev_cancel      <= 0;
            dispense_item    <= 0;
            return_change    <= 0;
            item_price       <= 0;
            change_amount    <= 0;
            dispense_item_id <= 0;
            error            <= 0;
            return_money     <= 0;
        end else begin
            prev_item_button <= item_button;
            prev_cancel      <= cancel;
            // Default outputs
            dispense_item    <= 0;
            return_change    <= 0;
            error            <= 0;
            return_money     <= 0;

            case (state)
                IDLE: begin
                    item_price       <= 0;
                    change_amount    <= 0;
                    dispense_item_id <= 0;
                    coins_acc        <= 0;
                    price_reg        <= 0;
                    item_id_reg      <= 0;
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
                        logic [4:0] p;
                        p = get_price(item_selected);
                        if (p == 0) begin
                            error <= 1;
                            state <= RETURN_MONEY;
                        end else begin
                            price_reg        <= p;
                            item_price       <= p;
                            item_id_reg      <= item_selected;
                            dispense_item_id <= item_selected;
                            state            <= PAYMENT_VALIDATION;
                        end
                    end
                end

                PAYMENT_VALIDATION: begin
                    if (cancel_rise) begin
                        error <= 1;
                        state <= RETURN_MONEY;
                    end else if (coin_input != 0) begin
                        if (!valid_coin(coin_input)) begin
                            error        <= 1;
                            return_money <= 1;
                            coins_acc    <= 0;
                            state        <= IDLE;
                        end else begin
                            logic [4:0] new_acc;
                            new_acc = coins_acc + coin_input;
                            if (new_acc >= price_reg) begin
                                coins_acc <= new_acc;
                                state     <= DISPENSING_ITEM;
                            end else begin
                                coins_acc <= new_acc;
                            end
                        end
                    end
                end

                DISPENSING_ITEM: begin
                    dispense_item <= 1;
                    // dispense_item_id already set in ITEM_SELECTION, keep it
                    if (coins_acc > price_reg) begin
                        change_amount <= coins_acc - price_reg;
                        state         <= RETURN_CHANGE;
                    end else begin
                        change_amount <= 0;
                        item_price    <= 0;
                        coins_acc     <= 0;
                        price_reg     <= 0;
                        item_id_reg   <= 0;
                        // Do NOT clear dispense_item_id here so testbench can read it next cycle
                        state         <= IDLE;
                    end
                end

                RETURN_CHANGE: begin
                    return_change    <= 1;
                    // change_amount already set in DISPENSING_ITEM
                    item_price       <= 0;
                    dispense_item_id <= 0;
                    coins_acc        <= 0;
                    price_reg        <= 0;
                    item_id_reg      <= 0;
                    state            <= IDLE;
                end

                RETURN_MONEY: begin
                    if (coins_acc > 0) begin
                        return_money <= 1;
                    end
                    coins_acc        <= 0;
                    price_reg        <= 0;
                    item_id_reg      <= 0;
                    item_price       <= 0;
                    change_amount    <= 0;
                    dispense_item_id <= 0;
                    state            <= IDLE;
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
