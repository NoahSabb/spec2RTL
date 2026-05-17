<s> module gf_multiplier(
    input [3:0] A,
    input [3:0] B,
    output reg [3:0] result
);

reg [3:0] multiplicand;
reg [4:0] irreducible_poly = 5'b10011; // Irreducible polynomial

always @ (A or B) begin
    // Initialize multiplicand and result
    multiplicand <= A;
    result <= 4'b0000;
    
    // Multiplication process
    for (int i = 0; i < 4; i = i + 1) begin
        if (B[i] == 1) begin
            // XOR with multiplicand and shift
            result <= result ^ multiplicand;
            multiplicand <= multiplicand << 1;
            
            // Polynomial reduction if MSB of multiplicand is 1 after shifting
            if (multiplicand[4] == 1) begin
                multiplicand <= multiplicand ^ irreducible_poly;
            end
        end else begin
            // No operation
            multiplicand <= multiplicand << 1;
            
            // Polynomial reduction if MSB of multiplicand is 1 after shifting
            if (multiplicand[4] == 1) begin
                multiplicand <= multiplicand ^ irreducible_poly;
            end
        end
    end
end

endmodule