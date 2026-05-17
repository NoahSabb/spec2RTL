module fifo_async #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH      = 16
) (
    // Write domain
    input  logic                  w_clk,
    input  logic                  w_rst,
    input  logic                  w_inc,
    input  logic [DATA_WIDTH-1:0] w_data,
    output logic                  w_full,

    // Read domain
    input  logic                  r_clk,
    input  logic                  r_rst,
    input  logic                  r_inc,
    output logic                  r_empty,
    output logic [DATA_WIDTH-1:0] r_data
);

    // Address width (log2 of DEPTH)
    localparam ADDR_WIDTH = $clog2(DEPTH);
    // Pointer width has one extra bit for overflow detection
    localparam PTR_WIDTH  = ADDR_WIDTH + 1;

    // Memory
    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    // Write pointer (binary and Gray)
    logic [PTR_WIDTH-1:0] w_ptr_bin;
    logic [PTR_WIDTH-1:0] w_ptr_gray;
    logic [PTR_WIDTH-1:0] w_ptr_bin_next;
    logic [PTR_WIDTH-1:0] w_ptr_gray_next;

    // Read pointer (binary and Gray)
    logic [PTR_WIDTH-1:0] r_ptr_bin;
    logic [PTR_WIDTH-1:0] r_ptr_gray;
    logic [PTR_WIDTH-1:0] r_ptr_bin_next;
    logic [PTR_WIDTH-1:0] r_ptr_gray_next;

    // Synchronized pointers (2FF synchronizers)
    // Read pointer synchronized into write clock domain
    logic [PTR_WIDTH-1:0] r_ptr_gray_sync1_w;
    logic [PTR_WIDTH-1:0] r_ptr_gray_sync2_w;
    // Write pointer synchronized into read clock domain
    logic [PTR_WIDTH-1:0] w_ptr_gray_sync1_r;
    logic [PTR_WIDTH-1:0] w_ptr_gray_sync2_r;

    // -------------------------------------------------------------------------
    // Write pointer logic
    // -------------------------------------------------------------------------
    always_ff @(posedge w_clk or posedge w_rst) begin
        if (w_rst) begin
            w_ptr_bin  <= '0;
            w_ptr_gray <= '0;
        end else begin
            w_ptr_bin  <= w_ptr_bin_next;
            w_ptr_gray <= w_ptr_gray_next;
        end
    end

    assign w_ptr_bin_next  = (w_inc && !w_full) ? (w_ptr_bin + 1'b1) : w_ptr_bin;
    assign w_ptr_gray_next = (w_ptr_bin_next >> 1) ^ w_ptr_bin_next;

    // -------------------------------------------------------------------------
    // Read pointer logic
    // -------------------------------------------------------------------------
    always_ff @(posedge r_clk or posedge r_rst) begin
        if (r_rst) begin
            r_ptr_bin  <= '0;
            r_ptr_gray <= '0;
        end else begin
            r_ptr_bin  <= r_ptr_bin_next;
            r_ptr_gray <= r_ptr_gray_next;
        end
    end

    assign r_ptr_bin_next  = (r_inc && !r_empty) ? (r_ptr_bin + 1'b1) : r_ptr_bin;
    assign r_ptr_gray_next = (r_ptr_bin_next >> 1) ^ r_ptr_bin_next;

    // -------------------------------------------------------------------------
    // Memory write
    // -------------------------------------------------------------------------
    always_ff @(posedge w_clk) begin
        if (w_inc && !w_full) begin
            mem[w_ptr_bin[ADDR_WIDTH-1:0]] <= w_data;
        end
    end

    // -------------------------------------------------------------------------
    // Memory read (asynchronous)
    // -------------------------------------------------------------------------
    assign r_data = mem[r_ptr_bin[ADDR_WIDTH-1:0]];

    // -------------------------------------------------------------------------
    // Synchronize read pointer into write clock domain (2FF)
    // -------------------------------------------------------------------------
    always_ff @(posedge w_clk or posedge w_rst) begin
        if (w_rst) begin
            r_ptr_gray_sync1_w <= '0;
            r_ptr_gray_sync2_w <= '0;
        end else begin
            r_ptr_gray_sync1_w <= r_ptr_gray;
            r_ptr_gray_sync2_w <= r_ptr_gray_sync1_w;
        end
    end

    // -------------------------------------------------------------------------
    // Synchronize write pointer into read clock domain (2FF)
    // -------------------------------------------------------------------------
    always_ff @(posedge r_clk or posedge r_rst) begin
        if (r_rst) begin
            w_ptr_gray_sync1_r <= '0;
            w_ptr_gray_sync2_r <= '0;
        end else begin
            w_ptr_gray_sync1_r <= w_ptr_gray;
            w_ptr_gray_sync2_r <= w_ptr_gray_sync1_r;
        end
    end

    // -------------------------------------------------------------------------
    // Full flag generation (write clock domain)
    // Full when MSBs differ and all other bits are equal
    // -------------------------------------------------------------------------
    assign w_full = (w_ptr_gray[PTR_WIDTH-1]   != r_ptr_gray_sync2_w[PTR_WIDTH-1]) &&
                    (w_ptr_gray[PTR_WIDTH-2]   != r_ptr_gray_sync2_w[PTR_WIDTH-2]) &&
                    (w_ptr_gray[PTR_WIDTH-3:0] == r_ptr_gray_sync2_w[PTR_WIDTH-3:0]);

    // -------------------------------------------------------------------------
    // Empty flag generation (read clock domain)
    // Empty when write and read pointers are exactly the same
    // -------------------------------------------------------------------------
    assign r_empty = (r_ptr_gray == w_ptr_gray_sync2_r);

endmodule
