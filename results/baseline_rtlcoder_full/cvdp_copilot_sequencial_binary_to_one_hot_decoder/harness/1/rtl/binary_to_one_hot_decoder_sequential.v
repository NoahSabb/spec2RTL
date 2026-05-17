module binary_to_one_hot_decoder_sequencial (
    input [BINARY_WIDTH-1:0] i_binary_in,
    input i_clk,
    input i_rstb,
    output [OUTPUT_WIDTH-1:0] o_one_hot_out
);

parameter BINARY_WIDTH = 5;
parameter OUTPUT_WIDTH = 32;

reg [OUTPUT_WIDTH-1:0] state;

always @(posedge i_clk or negedge i_rstb) begin
    if (~i_rstb) begin
        state <= 0;
    end else begin
        case(i_binary_in)
            2'd0: state <= {OUTPUT_WIDTH{1'b1}} & ~o_one_hot_out[0];
            2'd1: state <= {OUTPUT_WIDTH{1'b1}} & ~o_one_hot_out[1];
            2'd2: state <= {OUTPUT_WIDTH{1'b1}} & ~o_one_hot_out[2];
            2'd3: state <= {OUTPUT_WIDTH{1'b1}} & ~o_one_hot_out[3];
        endcase
        o_one_hot_out <= state;
    end
end

endmodule