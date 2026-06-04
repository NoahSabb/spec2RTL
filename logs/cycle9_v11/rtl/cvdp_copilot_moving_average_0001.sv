module moving_average (
    input  wire        clk,
    input  wire        reset,
    input  wire [11:0] data_in,
    output reg  [11:0] data_out
);

    localparam DEPTH      = 8;
    localparam ADDR_WIDTH = 3;
    localparam SUM_WIDTH  = 15;

    reg [ADDR_WIDTH-1:0] write_ptr;
    reg [SUM_WIDTH-1:0]  sum;
    reg [11:0]           buffer [DEPTH-1:0];

    integer i;

    always @(posedge clk) begin
        if (reset) begin
            for (i = 0; i < DEPTH; i = i + 1) begin
                buffer[i] <= 12'b0;
            end
            write_ptr <= 3'b0;
            sum       <= 15'b0;
            data_out  <= 12'b0;
        end else begin
            // Compute new sum: subtract oldest (slot being overwritten), add new sample
            // next_sum is a local variable computed combinatorially within the always block
            begin : compute
                reg [SUM_WIDTH-1:0] next_sum;
                next_sum  = sum - buffer[write_ptr] + data_in;
                buffer[write_ptr] <= data_in;
                write_ptr <= write_ptr + 1;
                sum       <= next_sum;
                data_out  <= next_sum[SUM_WIDTH-1:3];
            end
        end
    end

endmodule
