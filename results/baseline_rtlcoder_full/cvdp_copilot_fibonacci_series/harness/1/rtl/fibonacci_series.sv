<s> module fibonacci_series(
    input clk,
    input rst,
    output reg [32-1:0] fib_out,
    output reg overflow_flag
);

reg [31:0] RegA;
reg [31:0] RegB;
wire [31:0] next_fib;

assign next_fib = RegA + RegB;

always @(posedge clk) begin
    if (rst) begin
        RegA <= 0;
        RegB <= 1;
        fib_out <= 0;
        overflow_flag <= 0;
    end else begin
        RegA <= RegB;
        RegB <= next_fib;
        
        if (next_fib[32] == 1) begin
            overflow_detected <= 1;
            fib_out <= RegB;
            overflow_flag <= 1;
        end else begin
            overflow_detected <= 0;
            fib_out <= RegB;
            overflow_flag <= 0;
        end
    end
end

initial begin
    fib_out <= 0;
    overflow_flag <= 0;
end

endmodule