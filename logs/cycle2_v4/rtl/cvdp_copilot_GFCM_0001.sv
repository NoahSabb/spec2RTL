module glitch_free_mux (
    input  wire clk1,
    input  wire clk2,
    input  wire sel,
    input  wire rst_n,
    output wire clkout
);

    reg clk1_en_ff, clk2_en_ff;
    reg clk1_en_g, clk2_en_g;

    // FF in clk1 domain
    always @(posedge clk1 or negedge rst_n) begin
        if (!rst_n)
            clk1_en_ff <= 1'b0;
        else
            clk1_en_ff <= ~sel & ~clk2_en_ff;
    end

    // FF in clk2 domain
    always @(posedge clk2 or negedge rst_n) begin
        if (!rst_n)
            clk2_en_ff <= 1'b0;
        else
            clk2_en_ff <= sel & ~clk1_en_ff;
    end

    // Negedge FF for clk1 gating
    always @(negedge clk1 or negedge rst_n) begin
        if (!rst_n)
            clk1_en_g <= 1'b0;
        else
            clk1_en_g <= clk1_en_ff;
    end

    // Negedge FF for clk2 gating
    always @(negedge clk2 or negedge rst_n) begin
        if (!rst_n)
            clk2_en_g <= 1'b0;
        else
            clk2_en_g <= clk2_en_ff;
    end

    assign clkout = (clk1 & clk1_en_g) | (clk2 & clk2_en_g);

endmodule
