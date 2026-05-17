module piso_8bit(clk, rst, serial_out);

input clk;
input rst;
output reg serial_out;

reg [7:0] tmp;

always @(posedge clk or negedge rst) begin
    if (~rst) begin // Asynchronous active LOW reset
        tmp <= 8'b0000_0001;
        serial_out <= 1'b0;
    end
    else begin
        if (tmp == 8'b1111_1111) // Increment the value after every 8th clock cycle
            tmp <= 8'b0000_0000;
        else
            tmp <= tmp + 8'h1; // Increment the value by one when 3 bits are transmitted
         serial_out <= (!tmp[7]) ? 1'b1 : 1'b0;
    end
end

endmodule