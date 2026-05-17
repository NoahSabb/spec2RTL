module SetBitStreamCalculator(
    input i_clk,
    input i_ready,
    input i_rst_n,
    input i_bit_in,
    output reg [p_max_set_bit_count_width-1: 0] o_set_bit_count
);

parameter p_max_set_bit_count_width = 8;
integer count_saturation_limit = p_max_set_bit_count_width - 1;

always @(posedge i_clk) begin
    if (!i_rst_n) begin
        o_set_bit_count <= #10 0;
    end else if (i_ready) begin
        if (o_set_bit_count + $signed(i_bit_in) > count_saturation_limit) begin
            o_set_bit_count <= #8 count_saturation_limit;
        end else begin
            o_set_bit_count <= #8 o_set_bit_count + i_bit_in;
        end
    end
end

endmodule