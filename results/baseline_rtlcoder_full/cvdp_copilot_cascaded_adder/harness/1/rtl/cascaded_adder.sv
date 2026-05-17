<s> module cascaded_adder (
    input wire clk,
    input wire reset_n = 0,
    input wire i_valid,
    input wire [15 : 0] i_data [(`IN_DATA_NS * `IN_DATA_WIDTH) - 1 : 0],
    output reg o_valid,
    output reg [`IN_DATA_WIDTH + $clog2(`IN_DATA_NS) - 1 : 0] o_data
);

parameter IN_DATA_WIDTH = 16;
parameter IN_DATA_NS = 4;

reg [(`IN_DATA_WIDTH + $clog2(`IN_DATA_NS) - 1) - 1 : 0] sum;

always @(posedge clk or negedge reset_n) begin
    if (~reset_n) begin
        o_valid <= 0;
        sum <= 0;
    end else begin
        if (i_valid && sum == {IN_DATA_NS{1'b0}}) begin // reset cascade sum to zero after a data set is received
            for (integer i = 1; i <= IN_DATA_NS; i = i + 1) begin
                sum[IN_DATA_WIDTH:i] <= i_data[(i-1)*(IN_DATA_WIDTH):i*(`IN_DATA_WS-1)];
            end
            o_valid <= 1;
        end
    end
end

assign o_data = sum[(IN_DATA_WIDTH+$clog2(`IN_DATA_NS)) - 1 : `clog2(`IN_DATA_NS)];

endmodule