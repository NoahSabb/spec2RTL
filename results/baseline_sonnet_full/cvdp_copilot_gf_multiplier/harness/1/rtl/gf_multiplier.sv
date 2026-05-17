module gf_multiplier (
    input  logic [3:0] A,
    input  logic [3:0] B,
    output logic [3:0] result
);

    always_comb begin
        logic [4:0] multiplicand;
        logic [3:0] res;
        
        res = 4'b0000;
        multiplicand = {1'b0, A};
        
        // Iteration for each bit of B
        // Bit 0
        if (B[0]) begin
            res = res ^ multiplicand[3:0];
        end
        // Shift multiplicand left by 1
        multiplicand = {multiplicand[3:0], 1'b0};
        // Check MSB (bit 4) for polynomial reduction
        if (multiplicand[4]) begin
            multiplicand = multiplicand ^ 5'b10011;
        end
        
        // Bit 1
        if (B[1]) begin
            res = res ^ multiplicand[3:0];
        end
        // Shift multiplicand left by 1
        multiplicand = {multiplicand[3:0], 1'b0};
        if (multiplicand[4]) begin
            multiplicand = multiplicand ^ 5'b10011;
        end
        
        // Bit 2
        if (B[2]) begin
            res = res ^ multiplicand[3:0];
        end
        // Shift multiplicand left by 1
        multiplicand = {multiplicand[3:0], 1'b0};
        if (multiplicand[4]) begin
            multiplicand = multiplicand ^ 5'b10011;
        end
        
        // Bit 3
        if (B[3]) begin
            res = res ^ multiplicand[3:0];
        end
        // Shift multiplicand left by 1 (not needed after last iteration but kept for consistency)
        multiplicand = {multiplicand[3:0], 1'b0};
        if (multiplicand[4]) begin
            multiplicand = multiplicand ^ 5'b10011;
        end
        
        result = res;
    end

endmodule
