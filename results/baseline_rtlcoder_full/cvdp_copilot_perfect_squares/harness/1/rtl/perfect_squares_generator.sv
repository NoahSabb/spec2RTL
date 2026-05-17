module perfect_squares_generator(
    input clk,
    input reset,
    output reg [31:0] sqr_o
);

reg [31:0] count;

always @(posedge clk or negedge reset) begin
    if (!reset) begin
        count <= 1;
        sqr_o <= 1;
    end else if (count == 32'hFFFFFFFF) begin
        count <= 0;
        sqr_o <= 0;
    end else if (sqr_o >= count*count) begin
        count <= count + 1;
    end else begin
        sqr_o <= sqr_o + 1;
    end
end

endmodule