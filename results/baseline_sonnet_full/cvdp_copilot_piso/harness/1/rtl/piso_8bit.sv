module piso_8bit (
    input  logic clk,
    input  logic rst,
    output logic serial_out
);

    logic [7:0] tmp;
    logic [2:0] bit_count;

    always_ff @(posedge clk or negedge rst) begin
        if (!rst) begin
            tmp        <= 8'b0000_0001;
            bit_count  <= 3'd0;
            serial_out <= 1'b0;
        end else begin
            // Output the current MSB bit of tmp
            serial_out <= tmp[7 - bit_count];

            if (bit_count == 3'd7) begin
                // After transmitting all 8 bits, increment tmp
                tmp       <= tmp + 1'b1;
                bit_count <= 3'd0;
            end else begin
                bit_count <= bit_count + 1'b1;
            end
        end
    end

endmodule
