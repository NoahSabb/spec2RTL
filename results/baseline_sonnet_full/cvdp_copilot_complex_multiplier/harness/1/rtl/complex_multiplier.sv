module complex_multiplier (
    input  logic        clk,
    input  logic        arst_n,
    input  logic signed [15:0] a_real,
    input  logic signed [15:0] a_imag,
    input  logic signed [15:0] b_real,
    input  logic signed [15:0] b_imag,
    output logic signed [31:0] result_real,
    output logic signed [31:0] result_imag
);

    always_ff @(posedge clk or negedge arst_n) begin
        if (!arst_n) begin
            result_real <= 32'sd0;
            result_imag <= 32'sd0;
        end else begin
            result_real <= (a_real * b_real) - (a_imag * b_imag);
            result_imag <= (a_real * b_imag) + (a_imag * b_real);
        end
    end

endmodule
