module morse_encoder (
    input  logic [7:0] ascii_in,
    output logic [9:0] morse_out,
    output logic [3:0] morse_length
);

    always_comb begin
        case (ascii_in)
            8'h41: begin morse_out = 10'b01;    morse_length = 4'd2; end
            8'h42: begin morse_out = 10'b1000;  morse_length = 4'd4; end
            8'h43: begin morse_out = 10'b1010;  morse_length = 4'd4; end
            8'h44: begin morse_out = 10'b100;   morse_length = 4'd3; end
            8'h45: begin morse_out = 10'b0;     morse_length = 4'd1; end
            8'h46: begin morse_out = 10'b0010;  morse_length = 4'd4; end
            8'h47: begin morse_out = 10'b110;   morse_length = 4'd3; end
            8'h48: begin morse_out = 10'b0000;  morse_length = 4'd4; end
            8'h49: begin morse_out = 10'b00;    morse_length = 4'd2; end
            8'h4A: begin morse_out = 10'b0111;  morse_length = 4'd4; end
            8'h4B: begin morse_out = 10'b101;   morse_length = 4'd3; end
            8'h4C: begin morse_out = 10'b0100;  morse_length = 4'd4; end
            8'h4D: begin morse_out = 10'b11;    morse_length = 4'd2; end
            8'h4E: begin morse_out = 10'b10;    morse_length = 4'd2; end
            8'h4F: begin morse_out = 10'b111;   morse_length = 4'd3; end
            8'h50: begin morse_out = 10'b0110;  morse_length = 4'd4; end
            8'h51: begin morse_out = 10'b1101;  morse_length = 4'd4; end
            8'h52: begin morse_out = 10'b010;   morse_length = 4'd3; end
            8'h53: begin morse_out = 10'b000;   morse_length = 4'd3; end
            8'h54: begin morse_out = 10'b1;     morse_length = 4'd1; end
            8'h55: begin morse_out = 10'b001;   morse_length = 4'd3; end
            8'h56: begin morse_out = 10'b0001;  morse_length = 4'd4; end
            8'h57: begin morse_out = 10'b011;   morse_length = 4'd3; end
            8'h58: begin morse_out = 10'b1001;  morse_length = 4'd4; end
            8'h59: begin morse_out = 10'b1011;  morse_length = 4'd4; end
            8'h5A: begin morse_out = 10'b1100;  morse_length = 4'd4; end
            8'h30: begin morse_out = 10'b11111; morse_length = 4'd5; end
            8'h31: begin morse_out = 10'b01111; morse_length = 4'd5; end
            8'h32: begin morse_out = 10'b00111; morse_length = 4'd5; end
            8'h33: begin morse_out = 10'b00011; morse_length = 4'd5; end
            8'h34: begin morse_out = 10'b00001; morse_length = 4'd5; end
            8'h35: begin morse_out = 10'b00000; morse_length = 4'd5; end
            8'h36: begin morse_out = 10'b10000; morse_length = 4'd5; end
            8'h37: begin morse_out = 10'b11000; morse_length = 4'd5; end
            8'h38: begin morse_out = 10'b11100; morse_length = 4'd5; end
            8'h39: begin morse_out = 10'b11110; morse_length = 4'd5; end
            default: begin morse_out = 10'b0;   morse_length = 4'd0; end
        endcase
    end

endmodule
