module matrix_multiplier #(
    parameter ROW_A          = 4,
    parameter COL_A          = 4,
    parameter ROW_B          = 4,
    parameter COL_B          = 4,
    parameter INPUT_DATA_WIDTH  = 8,
    parameter OUTPUT_DATA_WIDTH = INPUT_DATA_WIDTH * 2 + $clog2(COL_A)
) (
    input  logic [(ROW_A * COL_A * INPUT_DATA_WIDTH) - 1 : 0] matrix_a,
    input  logic [(ROW_B * COL_B * INPUT_DATA_WIDTH) - 1 : 0] matrix_b,
    output logic [(ROW_A * COL_B * OUTPUT_DATA_WIDTH) - 1 : 0] matrix_c
);

    // Internal arrays for unpacked representation
    logic [INPUT_DATA_WIDTH-1:0]  a [0:ROW_A-1][0:COL_A-1];
    logic [INPUT_DATA_WIDTH-1:0]  b [0:ROW_B-1][0:COL_B-1];
    logic [OUTPUT_DATA_WIDTH-1:0] c [0:ROW_A-1][0:COL_B-1];

    // Unpack matrix_a from flattened input
    // matrix_a = {a[ROW_A-1][COL_A-1], ..., a[0][0]}
    // Element a[row][col] is at index (row * COL_A + col)
    always_comb begin
        for (int row = 0; row < ROW_A; row++) begin
            for (int col = 0; col < COL_A; col++) begin
                a[row][col] = matrix_a[(row * COL_A + col) * INPUT_DATA_WIDTH +: INPUT_DATA_WIDTH];
            end
        end
    end

    // Unpack matrix_b from flattened input
    // matrix_b = {b[ROW_B-1][COL_B-1], ..., b[0][0]}
    // Element b[row][col] is at index (row * COL_B + col)
    always_comb begin
        for (int row = 0; row < ROW_B; row++) begin
            for (int col = 0; col < COL_B; col++) begin
                b[row][col] = matrix_b[(row * COL_B + col) * INPUT_DATA_WIDTH +: INPUT_DATA_WIDTH];
            end
        end
    end

    // Compute matrix multiplication c = a * b
    always_comb begin
        for (int i = 0; i < ROW_A; i++) begin
            for (int j = 0; j < COL_B; j++) begin
                c[i][j] = '0;
                for (int k = 0; k < COL_A; k++) begin
                    c[i][j] = c[i][j] + (OUTPUT_DATA_WIDTH)'(a[i][k]) * (OUTPUT_DATA_WIDTH)'(b[k][j]);
                end
            end
        end
    end

    // Pack output matrix_c into flattened output
    // matrix_c = {c[ROW_A-1][COL_B-1], ..., c[0][0]}
    // Element c[row][col] is at index (row * COL_B + col)
    always_comb begin
        for (int row = 0; row < ROW_A; row++) begin
            for (int col = 0; col < COL_B; col++) begin
                matrix_c[(row * COL_B + col) * OUTPUT_DATA_WIDTH +: OUTPUT_DATA_WIDTH] = c[row][col];
            end
        end
    end

endmodule
