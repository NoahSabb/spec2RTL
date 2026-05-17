<s> module vending_machine(
    input clk,
    input rst,
    input item_button,
    input [2:0] item_selected,
    input [3:0] coin_input,
    input cancel,
    output reg dispense_item,
    output reg return_change,
    output reg [4:0] item_price,
    output reg [4:0] change_amount,
    output reg [2:0] dispense_item_id,
    output reg error,
    output reg return_money);

parameter IDLE = 3'd0;
parameter ITEM_SELECTION = 3'd1;
parameter PAYMENT_VALIDATION = 3'd2;
parameter DISPENSING_ITEM = 3'd3;
parameter RETURN_CHANGE = 3'd4;
parameter RETURN_MONEY = 3'd5;

reg [1:0] state;
reg [3:0] coins_accumulated;

always @(posedge clk, posedge rst) begin
    if (rst) begin
        state <= IDLE;
        coins_accumulated <= 4'd0;
        dispense_item <= 1'b0;
        return_change <= 1'b0;
        item_price <= 5'd0;
        change_amount <= 5'd0;
        dispense_item_id <= 3'd0;
        error <= 1'b0;
        return_money <= 1'b0;
    end else begin
        case (state)
            IDLE: begin
                if (item_button) begin
                    state <= ITEM_SELECTION;
                end else if (coin_input != 4'd0) begin
                    error <= 1'b1;
                    return_money <= 1'b1;
                    state <= RETURN_MONEY;
                end
            end
            
            ITEM_SELECTION: begin
                case (item_selected)
                    3'b001: item_price <= 5'd10;
                    3'b010: item_price <= 5'd20;
                    3'b100: item_price <= 5'd40;
                endcase
                state <= PAYMENT_VALIDATION;
            end
            
            PAYMENT_VALIDATION: begin
                case (coin_input)
                    4'd1: coins_accumulated <= coins_accumulated + 1;
                    4'd2: coins_accumulated <= coins_accumulated + 2;
                    4'd5: coins_accumulated <= coins_accumulated + 5;
                    4'd10: coins_accumulated <= coins_accumulated + 10;
                endcase
                if (coins_accumulated >= item_price) begin
                    state <= DISPENSING_ITEM;
                end else if (cancel) begin
                    error <= 1'b1;
                    return_money <= 1'b1;
                    state <= RETURN_MONEY;
                end
            end
            
            DISPENSING_ITEM: begin
                dispense_item <= 1'b1;
                if (coins_accumulated - item_price > 4'd0) begin
                    change_amount <= coins_accumulated - item_price;
                    state <= RETURN_CHANGE;
                end else begin
                    state <= IDLE;
                end
            end
            
            RETURN_CHANGE: begin
                return_change <= 1'b1;
                coins_accumulated <= 4'd0;
                state <= IDLE;
            end
            
            RETURN_MONEY: begin
                return_money <= 1'b1;
                coins_accumulated <= 4'd0;
                state <= IDLE;
            end
        endcase
    end
end

initial begin
    state = IDLE;
    coins_accumulated = 4'd0;
    dispense_item = 1'b0;
    return_change = 1'b0;
    item_price = 5'd0;
    change_amount = 5'd0;
    dispense_item_id = 3'd0;
    error = 1'b0;
    return_money = 1'b0;
end

endmodule