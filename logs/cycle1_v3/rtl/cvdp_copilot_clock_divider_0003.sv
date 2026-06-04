module clock_divider (
    input wire clk,       // Primary clock input
    input wire rst_n,     // Active-low asynchronous reset
    input wire [1:0] sel, // Selection input for clock division factor
    output reg clk_out    // Divided clock output
);

    // Internal counter to track clock cycles
    reg [3:0] counter;

    // Internal signal to hold the next state of clk_out
    reg next_clk_out;

    // Clock division factors
    localparam DIV_BY_2 = 2'd0;
    localparam DIV_BY_4 = 2'd1;
    localparam DIV_BY_8 = 2'd2;

    // Combinational logic to determine the next state of clk_out
    always @(*) begin
        case (sel)
            DIV_BY_2: begin
                next_clk_out = ~clk_out;
            end
            DIV_BY_4: begin
                if (counter[0] == 1'b1) begin
                    next_clk_out = ~clk_out;
                end else begin
                    next_clk_out = clk_out;
                end
            end
            DIV_BY_8: begin
                if (counter[1:0] == 2'b11) begin
                    next_clk_out = ~clk_out;
                end else begin
                    next_clk_out = clk_out;
                end
            end
            default: begin
                next_clk_out = 1'b0; // Hold clk_out at 0 for invalid sel values
            end
        endcase
    end

    // Sequential logic to update clk_out and counter
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            clk_out <= 1'b0;
            counter <= 4'd0;
        end else begin
            clk_out <= next_clk_out;
            counter <= counter + 1;
        end
    end

endmodule
