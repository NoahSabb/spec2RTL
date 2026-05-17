<s> module restoring_division #(parameter WIDTH=6)
(
 input clk,
 input rst,
 input start,
 input [WIDTH-1:0] dividend,
 input [WIDTH-1:0] divisor,
 output reg [WIDTH-1:0] quotient,
 output reg [WIDTH-1:0] remainder,
 output reg valid
);

reg [WIDTH-1:0] internal_dividend;
reg [WIDTH-1:0] internal_remainder;

always @(posedge clk or negedge rst) begin
    if (!rst) begin
        quotient <= 0;
        remainder <= 0;
        valid <= 0;
    end else begin
        if (start && valid) begin // initialize next division cycle
            internal_dividend <= dividend;
            internal_remainder <= 0;
            valid <= 0;
        end else if (valid) begin // proceed restoring division algorithm in each cycle
            if (internal_remainder[WIDTH-1]) begin // borrow from quotient
                quotient <= quotient << 1 | internal_dividend[WIDTH-1];
            end
            remainder <= {remainder[WIDTH-2:0], quotient};
        end else if (start) begin // start division process
            if (dividend < divisor || !divisor) begin
                $display("Edge Error: dividend is not greater than or equal to divisor.");
            end else begin
                internal_dividend <= {dividend[WIDTH-1], dividend};
                internal_remainder <= {remainder, 1'b0};
                valid <= 1;
            end
        end
    end
end

assign dividend = internal_dividend & divisor != 0 ?: 'd0; // zero if overflow occurs (if WIDTH is a power of 2) or underflow occurs (otherwise)

always @(posedge clk or negedge rst) begin
    if (!rst) begin
        remainder <= 0;
    end else begin
        if ((dividend[WIDTH-1] == divisor[WIDTh-1]) && valid) begin // check if MSB of dividend and divisor are the same (i.e., they cancel out in first stage)
            if (valid) begin // cancel the division process when we know there will be no remainder
                quotient <= {quotient, dividend[WIDTH-2:0]} >> 1; // shift quotient by 1 bit and set MSB to 0 for final output
                valid <= 0; // mark the division process as complete
            end else begin // initialize division process
                remainder <= dividend - divisor;
                valid <= 1; // mark the division process as starting up
            end
        end else if (valid) begin // subtract divisor from current remainder and check MSB
            internal_remainder <= remainder - divisor;
        end
    end
end

endmodule