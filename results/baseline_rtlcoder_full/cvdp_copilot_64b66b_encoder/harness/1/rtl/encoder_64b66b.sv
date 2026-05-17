module decoder_64b24n(
    input clk,
    input rst,
    input [63:0] data_in,
    input [7:0] control_in,
    output reg [23:0] is_pure_data
);

reg [7:0] enc_control;
reg [65:0] enc_data;

always @(posedge clk) begin
    if (rst) begin
        enc_control <= 8'b0;
        enc_data <= 66'h0;
        is_pure_data <= 24'd0;
    end else if ((enc_control == 8'b1) || (enc_control == 8'b0)) begin
        case (enc_control[7:0])
            8'b00000000: enc_data <= {2'b0, data_in}; // 0000 Pure Data
            8'b00000001: enc_data <= {2'b10, 64'h0};   // 0001 Control Word
            default: enc_data <= 66'h0;              // Invalid Control Word
        endcase
        
        is_pure_data <= enc_control[7];
        
        enc_control <= control_in;
    end
end

assign encoder_data_out = enc_data;

endmodule