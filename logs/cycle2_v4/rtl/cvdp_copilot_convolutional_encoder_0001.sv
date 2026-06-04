module convolutional_encoder (
    input wire clk,
    input wire rst,
    input wire data_in,
    output reg encoded_bit1,
    output reg encoded_bit2
);

    reg [1:0] shift_reg;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            shift_reg <= 2'b00;
            encoded_bit1 <= 1'b0;
            encoded_bit2 <= 1'b0;
        end else begin
            // g1 = 111: data_in XOR shift_reg[0] XOR shift_reg[1]
            encoded_bit1 <= data_in ^ shift_reg[0] ^ shift_reg[1];
            // g2 = 101: data_in XOR shift_reg[1]
            encoded_bit2 <= data_in ^ shift_reg[1];
            // Shift register update
            shift_reg <= {shift_reg[0], data_in};
        end
    end

endmodule
