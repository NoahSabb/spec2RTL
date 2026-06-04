module piso_8bit (
    input  wire clk,
    input  wire rst,
    output reg  serial_out
);

    reg [7:0] tmp;
    reg [2:0] bit_count;

    always @(posedge clk or negedge rst) begin
        if (!rst) begin
            tmp        <= 8'b0000_0001;
            bit_count  <= 3'd0;
            serial_out <= 1'b0;
        end else begin
            serial_out <= tmp[7 - bit_count];
            bit_count  <= bit_count + 1;
            if (bit_count == 3'd7) begin
                tmp <= tmp + 1;
            end
        end
    end

endmodule
