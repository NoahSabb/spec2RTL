<s> module matrix_multiplier #(
  parameter ROW_A = 4,
  parameter COL_A = 4,
  parameter ROW_B = 4,
  parameter COL_B = 4,
  parameter INPUT_DATA_WIDTH = 8,
  parameter OUTPUT_DATA_WIDTH = INPUT_DATA_WIDTH*COL_A + INPUT_DATA_WIDTH - 1
)(
  input [(ROW_A * COL_A * INPUT_DATA_WIDTH) - 1 : 0] matrix_a,
  input [(ROW_B * COL_B * INPUT_DATA_WIDTH) - 1 : 0] matrix_b,
  output [((ROW_A * COL_B) * OUTPUT_DATA_WIDTH) - 1 : 0] matrix_c
);

  wire [INT_OUTPUT_WIDTH-1:0] temp;
  reg signed [INT_OUTPUT_WIDTH-1:0] c_reg [0:ROW_A-1][0:COL_B-1];
  
  assign temp = matrix_a[((ROW_A * COL_A) - 1):0] * matrix_b[((ROW_B * INPUT_DATA_WIDTH) - 1):0];
  
  always @(*) begin
    for (row_i = 0; row_i < ROW_A; row_i = row_i + 1) begin
      for (col_j = 0; col_j < COL_B; col_j = col_j + 1) begin
        c_reg[row_i][col_j] = temp[((col_j * ROW_A) - 1):(row_i * COL_B)];
      end
    end
  end
  
  assign matrix_c = {c_reg};
  
endmodule