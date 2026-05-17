// Module: cvdp_prbs_gen
// Description: PRBS Generator and Checker module
// Supports both generator mode (CHECK_MODE=0) and checker mode (CHECK_MODE=1)

module cvdp_prbs_gen #(
    parameter integer CHECK_MODE  = 0,   // 0: Generator, 1: Checker
    parameter integer POLY_LENGTH = 31,  // Length of polynomial (LFSR stages)
    parameter integer POLY_TAP    = 3,   // Tap position for feedback XOR
    parameter integer WIDTH       = 16   // Data bus width
) (
    input  logic             clk,
    input  logic             rst,
    input  logic [WIDTH-1:0] data_in,
    output logic [WIDTH-1:0] data_out
);

    // PRBS shift register
    logic [POLY_LENGTH-1:0] prbs_reg;
    
    // Combinational signals for next state computation
    logic [POLY_LENGTH-1:0] prbs_next [0:WIDTH];
    logic [WIDTH-1:0]       data_out_comb;
    logic                   feedback_bit;

    // Initialize prbs_next[0] to current prbs_reg
    // Then compute WIDTH iterations

    integer i;

    always_comb begin
        // Start with current register state
        prbs_next[0] = prbs_reg;
        
        for (i = 0; i < WIDTH; i = i + 1) begin
            // Feedback bit: XOR of bit at POLY_LENGTH-1 (MSB, position POLY_LENGTH)
            // and bit at POLY_TAP-1 (position POLY_TAP)
            feedback_bit = prbs_next[i][POLY_LENGTH-1] ^ prbs_next[i][POLY_TAP-1];
            
            // Shift register: shift right (towards LSB), insert feedback at MSB
            prbs_next[i+1] = {feedback_bit, prbs_next[i][POLY_LENGTH-1:1]};
            
            if (CHECK_MODE == 0) begin
                // Generator mode: output is the feedback bit (new MSB)
                data_out_comb[i] = feedback_bit;
            end else begin
                // Checker mode: compare input bit with expected PRBS bit
                // Expected bit is the same feedback_bit as in generator mode
                data_out_comb[i] = data_in[i] ^ feedback_bit;
            end
        end
    end

    // Sequential logic
    always_ff @(posedge clk) begin
        if (rst) begin
            prbs_reg  <= {POLY_LENGTH{1'b1}};
            data_out  <= {WIDTH{1'b1}};
        end else begin
            prbs_reg  <= prbs_next[WIDTH];
            data_out  <= data_out_comb;
        end
    end

endmodule
