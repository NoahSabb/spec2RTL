// Module: reverse_bits
// Description: Reverses the bits of a 32-bit unsigned input number.
//              The LSB of num_in becomes the MSB of num_out, and so on.

module reverse_bits (
    input  [31:0] num_in,   // 32-bit input number to be reversed
    output [31:0] num_out   // 32-bit bit-reversed output number
);

    // Generate block to assign each bit of num_out to the corresponding
    // reversed bit of num_in
    genvar i;
    generate
        for (i = 0; i < 32; i = i + 1) begin : bit_reverse
            assign num_out[i] = num_in[31 - i];
        end
    endgenerate

endmodule
