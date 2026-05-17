module binary_to_one_hot_decoder #(
    parameter BINARY_WIDTH = 5,
    parameter OUTPUT_WIDTH = 32
)(
    input  [BINARY_WIDTH-1:0] binary_in,
    output [OUTPUT_WIDTH-1:0] one_hot_out
);

    assign one_hot_out = (binary_in < OUTPUT_WIDTH) ? ({{(OUTPUT_WIDTH-1){1'b0}}, 1'b1} << binary_in) : {OUTPUT_WIDTH{1'b0}};

endmodule
