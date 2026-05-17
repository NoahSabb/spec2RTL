module morse_encoder(
    input [7:0] ascii_in,
    output reg [9:0] morse_out,
    output reg [3:0] morse_length
);

always @* begin
    case(ascii_in) // Direct Mapping for Morse Code Encoding
        8'h41: begin morse_out = 10'b01; morse_length = 2; end
        8'h42: morse_out = 10'b1000; morse_length = 4;
        8'h43: morse_out = 10'b1010; morse_length = 4;
        8'h44: morse_out = 10'b100; morse_length = 3;
        8'h45: begin morse_out = 10'b0; morse_length = 1; end
        8'h46: morse_out = 10'b0010; morse_length = 4;
        8'h47: morse_out = 10'b110; morse_length = 3;
        8'h48: morse_out = 10'b0000; morse_length = 4;
        8'h49: begin morse_out = 10'b00; morse_length = 2; end
        8'h4A: morse_out = 10'b0111; morse_length = 4;
        8'h4B: morse_out = 10'b101; morse_length = 3;
        8'h4C: morse_out = 10'b0100; morse_length = 4;
        8'h4D: begin morse_out = 10'b11; morse_length = 2; end
        8'h4E: morse_out = 10'b10; morse_length = 3;
        8'h4F: morse_out = 10'b111; morse_length = 3;
        8'h50: morse_out = 10'b0110; morse_length = 4;
        8'h51: morse_out = 10'b0111; morse_length = 4;
        8'h52: morse_out = 10'b010; morse_length = 3;
        8'h53: begin morse_out = 10'b000; morse_length = 3; end
        8'h54: morse_out = 10'b001; morse_length = 4;
        8'h55: morse_out = 10'b011; morse_length = 4;
        8'h56: morse_out = 10'b00001; morse_length = 4;
        8'h57: morse_out = 10'b011; morse_length = 3;
        8'h58: morse_out = 10'b1101; morse_length = 4;
        8'h59: morse_out = 10'b1011; morse_length = 4;
        8'h5A: morse_out = 10'b1100; morse_length = 4;
        default: begin morse_out = 10'b0; morse_length = 0; end
    endcase
end

always @* begin
    if(ascii_in >= `ASCII '0') begin // ASCII to Morse Code mapping for digits 0-9
        case(ascii_in - `ASCII '0' + 2)
            3: morse_out = 10'b10000;
            4: morse_out = 10'b01111;
            5: morse_out = 10'b00111;
            6: morse_out = 10'b01000;
        endcase
    end else begin // Default case - Morse code is reset to zeros
        morse_out = 10'b0;
    end
end

always @* begin
    morse_length = ascii_in >= `ASCII 'A' && ascii_in <= `ASCII 'Z' ? 4 : ascii_in >= `ASCII '0' && ascii_in <= `ASCII '9' ? 5 : morse_length;
end

endmodule