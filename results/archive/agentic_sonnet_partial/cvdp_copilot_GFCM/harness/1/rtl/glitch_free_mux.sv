// rtl/glitch_free_mux.sv
module glitch_free_mux (
    input  wire clk1,
    input  wire clk2,
    input  wire sel,
    input  wire rst_n,
    output wire clkout
);

    // Enable registers - sampled on negative edges to prevent glitches
    // clk1_en controls whether clk1 passes through
    // clk2_en controls whether clk2 passes through
    
    reg clk1_en;
    reg clk2_en;
    
    // clk1_en: deasserted when sel=1 or clk2 is already active
    // Sampled on negedge of clk1 so gating occurs while clk1 is low
    always @(negedge clk1 or negedge rst_n) begin
        if (!rst_n) begin
            clk1_en <= 1'b1;
        end else begin
            clk1_en <= (~sel) & (~clk2_en);
        end
    end
    
    // clk2_en: asserted when sel=1 and clk1 is not active
    // Sampled on negedge of clk2 so gating occurs while clk2 is low
    always @(negedge clk2 or negedge rst_n) begin
        if (!rst_n) begin
            clk2_en <= 1'b0;
        end else begin
            clk2_en <= sel & (~clk1_en);
        end
    end
    
    // Gate the clocks with their respective enable signals
    // AND with the clock itself ensures output is low when disabled
    wire clk1_gated;
    wire clk2_gated;
    
    assign clk1_gated = clk1 & clk1_en;
    assign clk2_gated = clk2 & clk2_en;
    
    // OR the gated clocks to produce the output
    assign clkout = clk1_gated | clk2_gated;

endmodule
