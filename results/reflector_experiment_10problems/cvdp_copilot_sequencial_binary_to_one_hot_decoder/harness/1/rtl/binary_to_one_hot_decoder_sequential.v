module binary_to_one_hot_decoder_sequential #(
    parameter BINARY_WIDTH = 5,
    parameter OUTPUT_WIDTH = 32
)(
    input  wire                    i_clk,
    input  wire                    i_rstb,
    input  wire [BINARY_WIDTH-1:0] i_binary_in,
    output reg  [OUTPUT_WIDTH-1:0] o_one_hot_out
);

    always @(posedge i_clk or negedge i_rstb) begin
        if (!i_rstb) begin
            o_one_hot_out <= {OUTPUT_WIDTH{1'b0}};
        end else begin
            o_one_hot_out <= ({{OUTPUT_WIDTH-1{1'b0}}, 1'b1} << i_binary_in);
        end
    end

endmodule
