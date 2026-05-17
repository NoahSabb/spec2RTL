module complex_multiplier (
    input clk,
    input arst_n,
    input [15:0] a_real,
    input [15:0] a_imag,
    input [15:0] b_real,
    input [15:0] b_imag,
    output reg [31:0] result_real,
    output reg [31:0] result_imag
);

reg [15:0] a, b;
reg [31:0] ac, bc, ad, bd;
reg [31:0] real_part, imaginary_part;

always @(posedge clk or negedge arst_n) begin
    if (~arst_n) begin
        result_real <= 0;
        result_imag <= 0;
    end else begin
        a <= a_real;
        b <= b_real;
        
        ac <= a * b_real;
        bc <= a_imag * b;
        ad <= b_imag * a;
        bd <= b_real * a_imag;
        
        real_part <= ac - bc;
        imaginary_part <= ad + bd;
        
        result_real <= real_part;
        result_imag <= imaginary_part;
    end
end

endmodule