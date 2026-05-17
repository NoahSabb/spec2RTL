module encoder_64b66b (
    input  logic        clk_in,
    input  logic        rst_in,
    input  logic [63:0] encoder_data_in,
    input  logic [7:0]  encoder_control_in,
    output logic [65:0] encoder_data_out
);

    always_ff @(posedge clk_in or posedge rst_in) begin
        if (rst_in) begin
            encoder_data_out <= 66'd0;
        end else begin
            if (encoder_control_in == 8'b00000000) begin
                // Pure data encoding: sync header 2'b01 followed by 64-bit data
                encoder_data_out <= {2'b01, encoder_data_in};
            end else begin
                // Control character present: sync header 2'b10 followed by 64'd0
                encoder_data_out <= {2'b10, 64'd0};
            end
        end
    end

endmodule
