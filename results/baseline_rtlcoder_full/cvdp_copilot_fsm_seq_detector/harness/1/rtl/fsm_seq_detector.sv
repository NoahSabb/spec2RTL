module fsm_seq_detector (
    input clk_in, // Input clock signal with 50% duty cycle
    input rst_in, // Asynchronous active-high reset signal
    input seq_in, // Serial input signal
    output reg seq_detected // Asserted high for one clock cycle when the sequence is detected, otherwise remains at low.
);

// Define state types and possible values. Use bit to represent
// clock signals for precise edge detection.
typedef bit clk_t;
type logic [2:0] state_t = {seq_detected, next_state}; // State encoding scheme

// Sequence to detect
parameter seq = 8'b10110001;

// State register
reg clk;
always @(posedge clk_in or posedge rst_in) begin
    if (rst_in) begin
        clk <= 1'b0; // S0
    end else begin
        clk <= #1 ~clk; // Update clock on rising edge
    end
end

// Next state logic
always @(*) begin
    logic [2:0] next_state = state_t[2:0];
    case (state)
        3'b000: next_state = (seq_in == seq[0]) ? 3'b001 : 3'b000; // S0
        3'b001: next_state = (seq_in == seq[1]) ? 3'b010 : 3'b000; // S1
        3'b010: next_state = (seq_in == seq[2]) ? 3'b100 : 3'b000; // S2
        3'b100: next_state = (seq_in == seq[3]) ? 3'b110 : 3'b000; // S3
        3'b110: next_state = (seq_in == seq[4]) ? 3'b101 : 3'b000; // S4
        3'b101: next_state = (seq_in == seq[5]) ? 3'b011 : 3'b000; // S5
        3'b011: next_state = (seq_in == seq[6]) ? 3'b100 : 3'b000; // S6
        3'b100: next_state = (seq_in == seq[7]) ? 3'b101 : 3'b000; // S7
        default: next_state = 3'b000; // Default state
    endcase
end

// Output logic
always @(*) begin
    logic [2:0] seq_detected_w;
    case (state)
        3'b101: seq_detected_w = 4'hF; // Only assert once
        default: seq_detected_w = 4'h0;
    endcase
end
always @(posedge clk or posedge rst_in) begin
    if (rst_in) begin
        seq_detected <= 1'b0; // Clear output register on reset
    end else begin
        seq_detected <= #1 seq_detected_w[3]; // Synchronize output with clock
    end
end

endmodule