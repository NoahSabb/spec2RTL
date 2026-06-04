module fibonacci_series (
    input wire clk,
    input wire rst,
    output reg [31:0] fib_out,
    output reg overflow_flag
);

    // Registers to store the two preceding Fibonacci numbers
    reg [31:0] RegA;
    reg [31:0] RegB;

    // Wire to store the next Fibonacci number (combinational)
    wire [32:0] next_fib;

    // Continuous assignment for combinational computation
    assign next_fib = RegA + RegB;

    // Internal flag to detect overflow
    reg overflow_detected;

    // Sequential logic to update Fibonacci numbers and handle overflow
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            // Reset state
            RegA <= 32'b0;
            RegB <= 32'b1;
            fib_out <= 32'b0;
            overflow_flag <= 1'b0;
            overflow_detected <= 1'b0;
        end else begin
            // Check if overflow was detected in the previous cycle
            if (overflow_detected) begin
                // Set overflow flag and reset the sequence
                overflow_flag <= 1'b1;
                RegA <= 32'b0;
                RegB <= 32'b1;
                fib_out <= 32'b0;
                overflow_detected <= 1'b0;
            end else begin
                // Check for overflow
                if (next_fib[32]) begin
                    // Overflow detected, set the internal flag
                    overflow_detected <= 1'b1;
                    // Output the last valid Fibonacci number
                    fib_out <= RegB;
                end else begin
                    // No overflow, update the registers and output
                    RegA <= RegB;
                    RegB <= next_fib[31:0];
                    fib_out <= RegB;
                    overflow_flag <= 1'b0;
                end
            end
        end
    end

endmodule
