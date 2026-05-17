module rst_ff(input clk, rst_n, output reg out);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out <= 1'b0;
        end else begin
            out <= #1 ~out;
        end
    end
endmodule

// This clock divider uses an FSM. The state encoding is as follows:
//  00: Counter at '0'.
//  01: Counter at '2', first counter period finished.
//  10: Counter at '4', second counter period finished.
//  11: Counter at '8' (or 7, depending on the division factor), third counter period finished.
// In a real system, one would typically use two counters (one for dividing by two and one for dividing by four/eight) instead. The FSM is made more complex in this case because it has to wait for the next rising edge of the input clock, but it could be much simpler otherwise.
module clock_divider(input clk, input rst_n, input [1:0] sel, output reg clk_out);
    localparam IDLE = 2'b00;
    localparam COUNT8_FINISHED = 2'b11;
    reg [2:0] state;
    
    reg [3:0] count;
    wire clk_divided = (count == 4'd7) ? ~count[3] : 1'b0;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            count <= 4'd0;
            clk_out <= 1'b0;
        end else begin
            // State machine
            case (state)
                IDLE:
                    if (sel == 2'b00)
                        state <= COUNT8_FINISHED;
                COUNT8_FINISHED:
                    begin
                        if (sel == 2'b10) // Divide by 4
                            state <= IDLE;
                        else if (sel == 2'b10) // Divide by 8
                            state <= {cnt[3], cnt[2:0]};
                    end
            endcase
            
            if (sel != IDLE) begin
                count <= (count + 4'd1) % 5;
                clk_out <= clk_divided;
            end else begin
                count <= 4'd0;
                clk_out <= 1'b0;
            end
        end
    end
endmodule