// Glitch-Free Clock Multiplexer
// When sel=0, clkout = clk1; when sel=1, clkout = clk2
// Glitch-free switching using enable flops on negative edges

module glitch_free_mux (
    input  wire clk1,
    input  wire clk2,
    input  wire rst_n,
    input  wire sel,
    output wire clkout
);

    reg clk1_en_reg;
    reg clk2_en_reg;

    // clk1 enable logic:
    // Captured on negative edge of clk1
    // Enable clk1 when sel=0 and clk2 is not enabled
    // Disable clk1 when sel=1
    always @(negedge clk1 or negedge rst_n) begin
        if (!rst_n) begin
            clk1_en_reg <= 1'b1; // default to clk1 after reset
        end else begin
            clk1_en_reg <= (~sel) & (~clk2_en_reg);
        end
    end

    // clk2 enable logic:
    // Captured on negative edge of clk2
    // Enable clk2 when sel=1 and clk1 is not enabled
    // Disable clk2 when sel=0
    always @(negedge clk2 or negedge rst_n) begin
        if (!rst_n) begin
            clk2_en_reg <= 1'b0;
        end else begin
            clk2_en_reg <= sel & (~clk1_en_reg);
        end
    end

    // Gate the clocks using AND gates
    // clk1_gated is active only when clk1_en_reg is high
    // clk2_gated is active only when clk2_en_reg is high
    // The output is the OR of the two gated clocks

    wire clk1_gated;
    wire clk2_gated;

    assign clk1_gated = clk1 & clk1_en_reg;
    assign clk2_gated = clk2 & clk2_en_reg;

    assign clkout = clk1_gated | clk2_gated;

endmodule
