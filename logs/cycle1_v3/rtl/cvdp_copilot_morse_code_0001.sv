module morse_encoder (
    input  wire [7:0] ascii_in,
    output reg [9:0] morse_out,
    output reg [3:0] morse_length
);

always @(*) begin
    case (ascii_in)
        8'h41: {morse_out, morse_length} = {10'b0000000001, 4'd2}; // A .- = 01
        8'h42: {morse_out, morse_length} = {10'b0000001000, 4'd4}; // B -... = 1000
        8'h43: {morse_out, morse_length} = {10'b0000001010, 4'd4}; // C -.-. = 1010
        8'h44: {morse_out, morse_length} = {10'b0000000100, 4'd3}; // D -.. = 100
        8'h45: {morse_out, morse_length} = {10'b0000000000, 4'd1}; // E . = 0
        8'h46: {morse_out, morse_length} = {10'b0000000010, 4'd4}; // F ..-. = 0010
        8'h47: {morse_out, morse_length} = {10'b0000000110, 4'd3}; // G --. = 110
        8'h48: {morse_out, morse_length} = {10'b0000000000, 4'd4}; // H .... = 0000
        8'h49: {morse_out, morse_length} = {10'b0000000000, 4'd2}; // I .. = 00
        8'h4A: {morse_out, morse_length} = {10'b0000000111, 4'd4}; // J .--- = 0111
        8'h4B: {morse_out, morse_length} = {10'b0000000101, 4'd3}; // K -.- = 101
        8'h4C: {morse_out, morse_length} = {10'b0000000100, 4'd4}; // L .-.. = 0100
        8'h4D: {morse_out, morse_length} = {10'b0000000011, 4'd2}; // M -- = 11
        8'h4E: {morse_out, morse_length} = {10'b0000000010, 4'd2}; // N -. = 10
        8'h4F: {morse_out, morse_length} = {10'b0000000111, 4'd3}; // O --- = 111
        8'h50: {morse_out, morse_length} = {10'b0000000110, 4'd4}; // P .--. = 0110
        8'h51: {morse_out, morse_length} = {10'b0000001101, 4'd4}; // Q --.- = 1101
        8'h52: {morse_out, morse_length} = {10'b0000000010, 4'd3}; // R .-. = 010
        8'h53: {morse_out, morse_length} = {10'b0000000000, 4'd3}; // S ... = 000
        8'h54: {morse_out, morse_length} = {10'b0000000001, 4'd1}; // T - = 1
        8'h55: {morse_out, morse_length} = {10'b0000000001, 4'd3}; // U ..- = 001
        8'h56: {morse_out, morse_length} = {10'b0000000001, 4'd4}; // V ...- = 0001
        8'h57: {morse_out, morse_length} = {10'b0000000011, 4'd3}; // W .-- = 011
        8'h58: {morse_out, morse_length} = {10'b0000001001, 4'd4}; // X -..- = 1001
        8'h59: {morse_out, morse_length} = {10'b0000001011, 4'd4}; // Y -.-- = 1011
        8'h5A: {morse_out, morse_length} = {10'b0000001100, 4'd4}; // Z --.. = 1100
        8'h30: {morse_out, morse_length} = {10'b0000011111, 4'd5}; // 0 ----- = 11111
        8'h31: {morse_out, morse_length} = {10'b0000001111, 4'd5}; // 1 .---- = 01111
        8'h32: {morse_out, morse_length} = {10'b0000000111, 4'd5}; // 2 ..--- = 00111
        8'h33: {morse_out, morse_length} = {10'b0000000011, 4'd5}; // 3 ...-- = 00011
        8'h34: {morse_out, morse_length} = {10'b0000000001, 4'd5}; // 4 ....- = 00001
        8'h35: {morse_out, morse_length} = {10'b0000000000, 4'd5}; // 5 ..... = 00000
        8'h36: {morse_out, morse_length} = {10'b0000010000, 4'd5}; // 6 -.... = 10000
        8'h37: {morse_out, morse_length} = {10'b0000011000, 4'd5}; // 7 --... = 11000
        8'h38: {morse_out, morse_length} = {10'b0000011100, 4'd5}; // 8 ---.. = 11100
        8'h39: {morse_out, morse_length} = {10'b0000011110, 4'd5}; // 9 ----. = 11110
        default: {morse_out, morse_length} = {10'b0000000000, 4'd0}; // Unsupported
    endcase
end

endmodule
