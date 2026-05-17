module perfect_squares_generator (
    input  logic        clk,
    input  logic        reset,
    output logic [31:0] sqr_o
);

    logic [31:0] counter;
    logic [63:0] next_square;

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            counter <= 32'd1;
            sqr_o   <= 32'd1;
        end else begin
            next_square = (counter + 1) * (counter + 1);
            if (next_square > 64'hFFFFFFFF) begin
                sqr_o <= 32'hFFFFFFFF;
            end else begin
                sqr_o <= next_square[31:0];
            end
            counter <= counter + 1;
        end
    end

endmodule
