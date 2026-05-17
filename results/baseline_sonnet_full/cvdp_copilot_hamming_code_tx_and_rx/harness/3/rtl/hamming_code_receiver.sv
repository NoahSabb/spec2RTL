module hamming_code_receiver (
    input  logic [7:0] data_in,
    output logic [3:0] data_out
);

    logic c1, c2, c3;
    logic [7:0] corrected;

    // Even parity checks
    assign c3 = data_in[1] ^ data_in[3] ^ data_in[5] ^ data_in[7];
    assign c2 = data_in[2] ^ data_in[3] ^ data_in[6] ^ data_in[7];
    assign c1 = data_in[4] ^ data_in[5] ^ data_in[6] ^ data_in[7];

    // Error correction
    always_comb begin
        corrected = data_in;
        if ({c1, c2, c3} != 3'b000) begin
            corrected[{c1, c2, c3}] = ~data_in[{c1, c2, c3}];
        end
    end

    // Output assignment: data bits are at positions 7, 6, 5, 3
    assign data_out = {corrected[7], corrected[6], corrected[5], corrected[3]};

endmodule
