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
    logic [31:0] internal_fib_out;
    logic        internal_overflow_flag;

    // Combinational next Fibonacci calculation
    always_comb begin
        next_fib = {1'b0, RegA} + {1'b0, RegB};
    end

    // Sequential logic with asynchronous reset
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            RegA                  <= 32'd0;
            RegB                  <= 32'd1;
            internal_fib_out      <= 32'd0;
            internal_overflow_flag <= 1'b0;
            overflow_detected     <= 1'b0;
        end else begin
            if (overflow_detected) begin
                // One cycle after overflow: set flag, show last fib, then restart
                internal_overflow_flag <= 1'b1;
                internal_fib_out       <= 32'd0;
                RegA                   <= 32'd0;
                RegB                   <= 32'd1;
                overflow_detected      <= 1'b0;
            end else begin
                if (next_fib[32]) begin
                    // Overflow detected: propagate RegB to output, set overflow_detected
                    internal_fib_out      <= RegB;
                    overflow_detected     <= 1'b1;
                    internal_overflow_flag <= 1'b0;
                    // Keep RegA and RegB for one more cycle
                    RegA <= RegA;
                    RegB <= RegB;
                end else begin
                    // Normal Fibonacci update
                    internal_fib_out       <= RegB;
                    internal_overflow_flag <= 1'b0;
                    overflow_detected      <= 1'b0;
                    RegA                   <= RegB;
                    RegB                   <= next_fib[31:0];
                end
            end
        end
    end

    // Asynchronous reset override for outputs
    assign fib_out       = rst ? 32'd0 : internal_fib_out;
    assign overflow_flag = rst ? 1'b0  : internal_overflow_flag;

endmodule
