Module Name: cvdp_prbs_gen (PRBS generator and checker)

Parametrisation:
- `CHECK_MODE` (default: 0): Mode selection. 0 for generator mode, 1 for checker mode.
- `POLY_LENGTH` (default: 31): Length of the polynomial (number of shift register stages in the LFSR).
- `POLY_TAP` (default: 3): Positions of the tap in the shift register that is XORed with bit at `POLY_LENGTH` to generate the feedback bit.
- `WIDTH` (default: 16): Bit width of the data bus. The number of PRBS registers (bits) matches this parameter (POLY_LENGTH+1 bits + WIDTH-1 inputs for checker mode).

Interface:
- Inputs: clk, rst;
  - clk: clock input signal. All operations are synchronized on the rising edge.
  - rst: synchronous reset. When asserted high, resets internal states and outputs to their initial values.
- Outputs: data_out (POLY_LENGTH+1+WIDTH-1 bits);
  - Generator mode: Outputs the generated PRBS pattern with additional MSB indicating the status of the generator
  - Checker mode: outputs 0 when the data input matches the expected PRBS output, otherwise outputs the position (POLY_LENGTH or `POLY_TAP`) that is detected in error.

Internal Behaviour:
- PRBS generator
- Tied input for checker mode

<s> module cvdp_prbs_gen(
    input clk, rst,
    input [WIDTH-1] data_in,
    output reg [POLY_LENGTH+WIDTH-2:0] data_out
);

parameter CHECK_MODE = 0;
parameter POLY_LENGTH = 31;
parameter POLY_TAP = 3;
parameter WIDTH = 16;

reg [POLY_LENGTH+WIDTH-3:0] prbs_reg;
wire feedback, checker;

assign feedback = ^prbs_reg[{POLY_TAP, POLY_LENGTH}];
assign checker = data_in[POLY_LENGTH] ^ data_in[POLY_TAP];

always @(posedge clk) begin
    if (rst) begin
        prbs_reg <= {WIDTH{1'b1}}; // initialize all stages to 1's
        data_out <= {WIDTH{1'b0}}; // reset MSB bit indicating generator status
    end
    else begin
        if(CHECK_MODE) begin // checker mode
            prbs_reg[POLY_LENGTH] <= prbs_reg[POLY_TAP-2:0]; // shift right and insert feedback bit in PRBS registers
            data_out[POLY_LENGTH+WIDTH-3:1] <= {checker, prbs_reg[POLY_LENGTH-1:0]} ^ (POLY_LENGTH ? POLY_TAP : POLY_LENGTH); // generate and compare PRBS bits
        end
        else begin // generator mode
            prbs_reg[POLY_LENGTH] <= {prbs_reg[POLY_LENGTH-1:0], feedback}; // shift right and insert feedback bit in PRBS registers
            data_out[POLY_LENGTH+WIDTH-3:1] <= {prbs_reg[POLY_LENGTH-1:0]} ^ prbs_reg[POLY_TAP]; // generate PRBS bits
            data_out[WIDTH+POLY_LENGTH-2] <= feedback; // set MSB to 1'bx for generator status
        end
    end
end

always @(prbs_reg, POLY_TAP, POLY_LENGTH) begin
    prbs_reg = (POLY_TAP == 0) ? {POLY_LENGTH{1'b0}} :
                (POLY_TAP >= POLY_LENGTH) ? {(POLY_TAP-1){1'b0}}, {POLY_LENGTH-POLY_TAP+1{1'bx}}} :
 module_inst -> data_out[WIDTH+POLY_LENGTH-2:POLY_TAP]; // Tie input for checker mode
end

always @(POLY_TAP) begin
    POLY_TAP = (POLY_TAP < 1) ? 1 : POLY_TAP; // constrain to positive integer
end

endmodule