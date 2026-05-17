// -----------------------------------------------------------------------------
// Module: signed_unsigned_comparator
// Description: A fully parameterized combinational comparator that supports
//              two comparison modes:
//              - Signed Mode   (i_mode = 1): Interprets inputs as signed integers
//              - Magnitude Mode (i_mode = 0): Ignores sign bit, treats as unsigned
//
// Parameters:
//   WIDTH : Bit-width of the input operands (default: 5)
//
// Inputs:
//   i_A      : WIDTH-bit input operand A
//   i_B      : WIDTH-bit input operand B
//   i_enable : Enable signal (active high); when low, all outputs are deasserted
//   i_mode   : Mode select; high = signed mode, low = magnitude mode
//
// Outputs:
//   o_greater : High when i_A > i_B (and i_enable is high)
//   o_less    : High when i_A < i_B (and i_enable is high)
//   o_equal   : High when i_A == i_B (and i_enable is high)
// -----------------------------------------------------------------------------

module signed_unsigned_comparator #(
    parameter int WIDTH = 5
)(
    input  logic [WIDTH-1:0] i_A,
    input  logic [WIDTH-1:0] i_B,
    input  logic             i_enable,
    input  logic             i_mode,
    output logic             o_greater,
    output logic             o_less,
    output logic             o_equal
);

    // Internal signals for signed and unsigned interpretations
    logic signed   [WIDTH-1:0] A_signed;
    logic signed   [WIDTH-1:0] B_signed;
    logic unsigned [WIDTH-2:0] A_magnitude;
    logic unsigned [WIDTH-2:0] B_magnitude;

    // Assign signed views of the inputs
    assign A_signed   = $signed(i_A);
    assign B_signed   = $signed(i_B);

    // Magnitude: strip the MSB (sign bit) and compare remaining bits
    assign A_magnitude = i_A[WIDTH-2:0];
    assign B_magnitude = i_B[WIDTH-2:0];

    // Combinational comparison logic
    always_comb begin
        // Default: all outputs deasserted
        o_greater = 1'b0;
        o_less    = 1'b0;
        o_equal   = 1'b0;

        if (i_enable) begin
            if (i_mode) begin
                // -----------------------------------------------
                // Signed Mode: MSB is the sign bit
                // -----------------------------------------------
                if (A_signed > B_signed) begin
                    o_greater = 1'b1;
                    o_less    = 1'b0;
                    o_equal   = 1'b0;
                end else if (A_signed < B_signed) begin
                    o_greater = 1'b0;
                    o_less    = 1'b1;
                    o_equal   = 1'b0;
                end else begin
                    // A_signed == B_signed
                    o_greater = 1'b0;
                    o_less    = 1'b0;
                    o_equal   = 1'b1;
                end
            end else begin
                // -----------------------------------------------
                // Magnitude Mode: ignore the sign bit (MSB),
                // compare only the lower (WIDTH-1) bits
                // -----------------------------------------------
                if (A_magnitude > B_magnitude) begin
                    o_greater = 1'b1;
                    o_less    = 1'b0;
                    o_equal   = 1'b0;
                end else if (A_magnitude < B_magnitude) begin
                    o_greater = 1'b0;
                    o_less    = 1'b1;
                    o_equal   = 1'b0;
                end else begin
                    // A_magnitude == B_magnitude
                    o_greater = 1'b0;
                    o_less    = 1'b0;
                    o_equal   = 1'b1;
                end
            end
        end
        // When i_enable is low, outputs remain 0 (default)
    end

endmodule
