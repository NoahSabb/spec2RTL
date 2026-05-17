module clock_divider (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [1:0]  sel,
    output logic        clk_out
);

    // Internal counter - 3 bits to support divide by 8
    logic [2:0] counter;
    
    // Toggle signal for clock output
    logic clk_div2;
    logic clk_div4;
    logic clk_div8;
    
    // Counter logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            counter <= 3'b000;
        end else begin
            counter <= counter + 1'b1;
        end
    end
    
    // Generate divided clocks from counter bits
    // counter[0] toggles every cycle -> divide by 2
    // counter[1] toggles every 2 cycles -> divide by 4
    // counter[2] toggles every 4 cycles -> divide by 8
    assign clk_div2 = counter[0];
    assign clk_div4 = counter[1];
    assign clk_div8 = counter[2];
    
    // Output mux based on sel
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            clk_out <= 1'b0;
        end else begin
            case (sel)
                2'b00: clk_out <= clk_div2;
                2'b01: clk_out <= clk_div4;
                2'b10: clk_out <= clk_div8;
                default: clk_out <= 1'b0;
            endcase
        end
    end

endmodule
