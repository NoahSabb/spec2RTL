module morse_encoder (
    input  wire [7:0]  ascii_in,
    output wire [9:0]  morse_out,
    output wire [3:0]  morse_length
);

    reg [9:0] morse_out_r;
    reg [3:0] morse_length_r;

    assign morse_out    = morse_out_r;
    assign morse_length = morse_length_r;

    always @(*) begin
        case (ascii_in)
            8'h41: begin morse_out_r = 10'd1;  morse_length_r = 4'd2; end // A .-
            8'h42: begin morse_out_r = 10'd8;  morse_length_r = 4'd4; end // B -...
            8'h43: begin morse_out_r = 10'd10; morse_length_r = 4'd4; end // C -.-.
            8'h44: begin morse_out_r = 10'd4;  morse_length_r = 4'd3; end // D -..
            8'h45: begin morse_out_r = 10'd0;  morse_length_r = 4'd1; end // E .
            8'h46: begin morse_out_r = 10'd2;  morse_length_r = 4'd4; end // F ..-.
            8'h47: begin morse_out_r = 10'd6;  morse_length_r = 4'd3; end // G --.
            8'h48: begin morse_out_r = 10'd0;  morse_length_r = 4'd4; end // H ....
            8'h49: begin morse_out_r = 10'd0;  morse_length_r = 4'd2; end // I ..
            8'h4A: begin morse_out_r = 10'd7;  morse_length_r = 4'd4; end // J .---
            8'h4B: begin morse_out_r = 10'd5;  morse_length_r = 4'd3; end // K -.-
            8'h4C: begin morse_out_r = 10'd4;  morse_length_r = 4'd4; end // L .-..
            8'h4D: begin morse_out_r = 10'd3;  morse_length_r = 4'd2; end // M --
            8'h4E: begin morse_out_r = 10'd2;  morse_length_r = 4'd2; end // N -.
            8'h4F: begin morse_out_r = 10'd7;  morse_length_r = 4'd3; end // O ---
            8'h50: begin morse_out_r = 10'd6;  morse_length_r = 4'd4; end // P .--.
            8'h51: begin morse_out_r = 10'd13; morse_length_r = 4'd4; end // Q --.-
            8'h52: begin morse_out_r = 10'd2;  morse_length_r = 4'd3; end // R .-.
            8'h53: begin morse_out_r = 10'd0;  morse_length_r = 4'd3; end // S ...
            8'h54: begin morse_out_r = 10'd1;  morse_length_r = 4'd1; end // T -
            8'h55: begin morse_out_r = 10'd1;  morse_length_r = 4'd3; end // U ..-
            8'h56: begin morse_out_r = 10'd1;  morse_length_r = 4'd4; end // V ...-
            8'h57: begin morse_out_r = 10'd3;  morse_length_r = 4'd3; end // W .--
            8'h58: begin morse_out_r = 10'd9;  morse_length_r = 4'd4; end // X -..-
            8'h59: begin morse_out_r = 10'd11; morse_length_r = 4'd4; end // Y -.--
            8'h5A: begin morse_out_r = 10'd12; morse_length_r = 4'd4; end // Z --..
            8'h30: begin morse_out_r = 10'd31; morse_length_r = 4'd5; end // 0 -----
            8'h31: begin morse_out_r = 10'd15; morse_length_r = 4'd5; end // 1 .----
            8'h32: begin morse_out_r = 10'd7;  morse_length_r = 4'd5; end // 2 ..---
            8'h33: begin morse_out_r = 10'd3;  morse_length_r = 4'd5; end // 3 ...--
            8'h34: begin morse_out_r = 10'd1;  morse_length_r = 4'd5; end // 4 ....-
            8'h35: begin morse_out_r = 10'd0;  morse_length_r = 4'd5; end // 5 .....
            8'h36: begin morse_out_r = 10'd16; morse_length_r = 4'd5; end // 6 -....
            8'h37: begin morse_out_r = 10'd24; morse_length_r = 4'd5; end // 7 --...
            8'h38: begin morse_out_r = 10'd28; morse_length_r = 4'd5; end // 8 ---..
            8'h39: begin morse_out_r = 10'd30; morse_length_r = 4'd5; end // 9 ----.
            default: begin morse_out_r = 10'd0; morse_length_r = 4'd0; end
        endcase
    end

endmodule
