module glitch_free_mux (
    input  wire clk1,
    input  wire clk2,
    input  wire sel,
    input  wire rst_n,
    output wire clkout
);

    reg clk1_en;
    reg clk2_en;

    // clk1_en: update on positive edge of clk1
    always @(posedge clk1 or negedge rst_n) begin
        if (!rst_n)
            clk1_en <= 1'b1;
        else
            clk1_en <= (~sel) & (~clk2_en);
    end

    // clk2_en: update on positive edge of clk2
    always @(posedge clk2 or negedge rst_n) begin
        if (!rst_n)
            clk2_en <= 1'b0;
        else
            clk2_en <= sel & (~clk1_en);
    end

    // Gate the clocks and OR them together
    assign clkout = (clk1 & clk1_en) | (clk2 & clk2_en);

endmodule
