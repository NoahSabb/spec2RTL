module restoring_division #(
    parameter WIDTH = 6
)(
    input  logic             clk,
    input  logic             rst,
    input  logic             start,
    input  logic [WIDTH-1:0] dividend,
    input  logic [WIDTH-1:0] divisor,
    output logic [WIDTH-1:0] quotient,
    output logic [WIDTH-1:0] remainder,
    output logic             valid
);

    // Determine number of iterations needed
    // If WIDTH is power of 2, use WIDTH cycles; otherwise WIDTH+1 cycles
    function automatic integer is_power_of_2(input integer n);
        return (n > 0) && ((n & (n - 1)) == 0);
    endfunction

    localparam ITER = is_power_of_2(WIDTH) ? WIDTH : WIDTH + 1;
    localparam CNT_WIDTH = $clog2(ITER + 1);

    // Internal registers
    logic [WIDTH-1:0]   dividend_reg;
    logic [WIDTH-1:0]   divisor_reg;
    logic [WIDTH-1:0]   remainder_reg;
    logic [WIDTH-1:0]   quotient_reg;
    logic [CNT_WIDTH-1:0] count;
    logic               running;

    // Subtraction result (one extra bit for sign detection)
    logic [WIDTH:0]     sub_result;
    logic [WIDTH-1:0]   shifted_remainder;

    always_ff @(posedge clk or negedge rst) begin
        if (!rst) begin
            dividend_reg  <= '0;
            divisor_reg   <= '0;
            remainder_reg <= '0;
            quotient_reg  <= '0;
            quotient      <= '0;
            remainder     <= '0;
            valid         <= 1'b0;
            count         <= '0;
            running       <= 1'b0;
        end else begin
            valid <= 1'b0;

            if (start && !running) begin
                // Initialize
                dividend_reg  <= dividend;
                divisor_reg   <= divisor;
                remainder_reg <= '0;
                quotient_reg  <= '0;
                count         <= '0;
                running       <= 1'b1;
            end else if (running) begin
                if (count < ITER[CNT_WIDTH-1:0]) begin
                    // Shift remainder left and append MSB of dividend_reg
                    shifted_remainder = {remainder_reg[WIDTH-2:0], dividend_reg[WIDTH-1]};
                    // Shift dividend left
                    dividend_reg <= {dividend_reg[WIDTH-2:0], 1'b0};

                    // Subtract divisor
                    sub_result = {1'b0, shifted_remainder} - {1'b0, divisor_reg};

                    if (sub_result[WIDTH] == 1'b0) begin
                        // Result is non-negative, keep it
                        remainder_reg <= sub_result[WIDTH-1:0];
                        quotient_reg  <= {quotient_reg[WIDTH-2:0], 1'b1};
                    end else begin
                        // Result is negative, restore remainder
                        remainder_reg <= shifted_remainder;
                        quotient_reg  <= {quotient_reg[WIDTH-2:0], 1'b0};
                    end

                    count <= count + 1'b1;
                end else begin
                    // Done
                    quotient  <= quotient_reg;
                    remainder <= remainder_reg;
                    valid     <= 1'b1;
                    running   <= 1'b0;
                end
            end
        end
    end

endmodule
