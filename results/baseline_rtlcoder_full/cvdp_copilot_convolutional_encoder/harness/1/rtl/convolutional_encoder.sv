module convolutional_encoder (
    input clk,
    input rst,
    input data_in,
    output reg encoded_bit1,
    output reg encoded_bit2
);

reg [1:0] reg_input;
reg [3:0] shift_register = 4'b0000;

always @(posedge clk or posedge rst) begin
    if (rst) begin
        shift_register <= 4'b0000;
        encoded_bit1 <= 1'b0;
        encoded_bit2 <= 1'b0;
        reg_input <= 2'b00;
    end else begin
        shift_register <= {shift_register[2:0], data_in};
        
        reg_input <= {reg_input[0], shift_register[1]};
        
        case ({reg_input})
            2'b00: encoded_bit1 <= 1'b0;
            2'b01: encoded_bit1 <= 1'b1;
            2'b10: encoded_bit1 <= 1'b0;
            2'b11: encoded_bit1 <= 1'b1;
        endcase
        
        case ({reg_input})
            2'b01, 2'b10: encoded_bit2 <= 1'b1;
        endcase
    end
end

endmodule