module fibonacci_series (
    input  logic        clk,
    input  logic        rst,
    output logic [31:0] fib_out,
    output logic        overflow_flag
);

    logic [31:0] RegA, RegB;
    logic [32:0] next_fib;
    logic        overflow_detected;

    always_ff @(posedge clk) begin
        if (rst) begin
            RegA             <= 32'd0;
            RegB             <= 32'd1;
            fib_out          <= 32'd0;
            overflow_flag    <= 1'b0;
            overflow_detected <= 1'b0;
        end else begin
            if (overflow_detected) begin
                // One cycle after overflow detection: set flag, propagate last value, restart
                overflow_flag    <= 1'b1;
                fib_out          <= 32'd0;
                RegA             <= 32'd0;
                RegB             <= 32'd1;
                overflow_detected <= 1'b0;
            end else begin
                next_fib = {1'b0, RegA} + {1'b0, RegB};

                if (next_fib[32]) begin
                    // Overflow detected: propagate RegB to output, set overflow_detected
                    fib_out          <= RegB;
                    overflow_detected <= 1'b1;
                    overflow_flag    <= 1'b0;
                    // Keep RegA and RegB as they are until reset next cycle
                    RegA             <= RegA;
                    RegB             <= RegB;
                end else begin
                    overflow_flag    <= 1'b0;
                    fib_out          <= RegB;
                    RegA             <= RegB;
                    RegB             <= next_fib[31:0];
                    overflow_detected <= 1'b0;
                end
            end
        end
    end

endmodule
