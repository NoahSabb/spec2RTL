module convolutional_encoder (
    input  logic clk,
    input  logic rst,
    input  logic data_in,
    output logic encoded_bit1,
    output logic encoded_bit2
);

    // Shift register to hold previous bits (constraint length K=3, so 2 memory bits)
    logic [1:0] shift_reg;

    // Update shift register on clock edge
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            shift_reg    <= 2'b00;
            encoded_bit1 <= 1'b0;
            encoded_bit2 <= 1'b0;
        end else begin
            // Shift register: shift_reg[1] holds bit from 2 clocks ago,
            // shift_reg[0] holds bit from 1 clock ago
            shift_reg[1] <= shift_reg[0];
            shift_reg[0] <= data_in;

            // g1 = "111" => x^2 + x + 1 => XOR of data_in, shift_reg[0], shift_reg[1]
            encoded_bit1 <= data_in ^ shift_reg[0] ^ shift_reg[1];

            // g2 = "101" => x^2 + 1 => XOR of data_in and shift_reg[1]
            encoded_bit2 <= data_in ^ shift_reg[1];
        end
    end

endmodule
