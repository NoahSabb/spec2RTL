module fibonacci_series (
    input  logic        clk,
    input  logic        rst,
    output logic [31:0] fib_out,
    output logic        overflow_flag
);

    logic [31:0] RegA;
    logic [31:0] RegB;
    logic [32:0] next_fib;
    logic        overflow_detected;

    // Combinatorial block to compute next Fibonacci number
    always_comb begin
        next_fib = {1'b0, RegA} + {1'b0, RegB};
    end

    // Sequential block for state updates
    always_ff @(posedge clk) begin
        if (rst) begin
            RegA           <= 32'd0;
            RegB           <= 32'd1;
            fib_out        <= 32'd0;
            overflow_flag  <= 1'b0;
            overflow_detected <= 1'b0;
        end else begin
            if (overflow_detected) begin
                // One cycle after overflow detected: set flag, restart sequence
                overflow_flag     <= 1'b1;
                overflow_detected <= 1'b0;
                RegA              <= 32'd0;
                RegB              <= 32'd1;
                fib_out           <= 32'd0;
            end else begin
                overflow_flag <= 1'b0;
                if (next_fib[32]) begin
                    // Overflow detected this cycle: output RegB, set overflow_detected
                    fib_out           <= RegB;
                    overflow_detected <= 1'b1;
                end else begin
                    // Normal operation: shift registers and update output
                    RegA    <= RegB;
                    RegB    <= next_fib[31:0];
                    fib_out <= RegB;
                end
            end
        end
    end

endmodule
