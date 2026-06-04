module hamming_code_receiver (
    input  logic [7:0] data_in,
    output logic [3:0] data_out
);

    // Internal signals for syndrome calculation
    logic c1, c2, c3;
    logic [2:0] syndrome;

    // Calculate syndrome bits
    assign c1 = data_in[4] ^ data_in[5] ^ data_in[6] ^ data_in[7]; // Parity bit 3
    assign c2 = data_in[2] ^ data_in[3] ^ data_in[6] ^ data_in[7]; // Parity bit 2
    assign c3 = data_in[1] ^ data_in[3] ^ data_in[5] ^ data_in[7]; // Parity bit 1

    // Combine syndrome bits into a single 3-bit value
    assign syndrome = {c1, c2, c3};

    // Corrected data signal
    logic [7:0] corrected_data;

    // Correct the error if detected
    always_comb begin
        case (syndrome)
            3'b000: corrected_data = data_in; // No error
            3'b001: corrected_data = data_in ^ 8'b00000010; // Error in data_in[1]
            3'b010: corrected_data = data_in ^ 8'b00000100; // Error in data_in[2]
            3'b011: corrected_data = data_in ^ 8'b00001000; // Error in data_in[3]
            3'b100: corrected_data = data_in ^ 8'b00010000; // Error in data_in[4]
            3'b101: corrected_data = data_in ^ 8'b00100000; // Error in data_in[5]
            3'b110: corrected_data = data_in ^ 8'b01000000; // Error in data_in[6]
            3'b111: corrected_data = data_in ^ 8'b10000000; // Error in data_in[7]
        endcase
    end

    // Assign corrected data bits to output
    assign data_out = {corrected_data[7], corrected_data[6], corrected_data[5], corrected_data[3]};

endmodule
