module glitch_free_mux (
    input wire clk1,
    input wire clk2,
    input wire sel,
    input wire rst_n,
    output wire clkout
);

    // Internal enable signals for clk1 and clk2
    reg clk1_en;
    reg clk2_en;

    // Synchronize sel signal to both clk1 and clk2 domains
    reg sel_sync_clk1;
    reg sel_sync_clk2;

    // Two-flop synchronizer second stages
    reg sel_sync_clk1_ff2;
    reg sel_sync_clk2_ff2;

    // Synchronize sel to clk1 domain (posedge)
    always @(posedge clk1 or negedge rst_n) begin
        if (!rst_n) begin
            sel_sync_clk1 <= 0;
        end else begin
            sel_sync_clk1 <= sel;
        end
    end

    // Capture sel_sync_clk1 on negedge clk1 for use in clk1_en logic
    always @(negedge clk1 or negedge rst_n) begin
        if (!rst_n) begin
            sel_sync_clk1_ff2 <= 0;
        end else begin
            sel_sync_clk1_ff2 <= sel_sync_clk1;
        end
    end

    // Synchronize sel to clk2 domain (posedge)
    always @(posedge clk2 or negedge rst_n) begin
        if (!rst_n) begin
            sel_sync_clk2 <= 0;
        end else begin
            sel_sync_clk2 <= sel;
        end
    end

    // Capture sel_sync_clk2 on negedge clk2 for use in clk2_en logic
    always @(negedge clk2 or negedge rst_n) begin
        if (!rst_n) begin
            sel_sync_clk2_ff2 <= 0;
        end else begin
            sel_sync_clk2_ff2 <= sel_sync_clk2;
        end
    end

    // Generate enable signal for clk1 (on negedge to avoid glitches)
    always @(negedge clk1 or negedge rst_n) begin
        if (!rst_n) begin
            clk1_en <= 1;
        end else begin
            if (sel_sync_clk1_ff2) begin
                clk1_en <= 0;
            end else begin
                clk1_en <= !clk2_en;
            end
        end
    end

    // Generate enable signal for clk2 (on negedge to avoid glitches)
    always @(negedge clk2 or negedge rst_n) begin
        if (!rst_n) begin
            clk2_en <= 0;
        end else begin
            if (!sel_sync_clk2_ff2) begin
                clk2_en <= 0;
            end else begin
                clk2_en <= !clk1_en;
            end
        end
    end

    // Generate clkout as combinational AND-OR of gated clocks
    assign clkout = (clk1 & clk1_en) | (clk2 & clk2_en);

endmodule
