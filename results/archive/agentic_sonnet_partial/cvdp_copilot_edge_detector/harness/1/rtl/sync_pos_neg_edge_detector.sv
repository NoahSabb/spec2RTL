// File: rtl/sync_pos_neg_edge_detector.sv
// Description: Synchronous positive and negative edge detector module.
//              Detects both rising and falling edges on a glitch-free,
//              debounced input signal and asserts corresponding output
//              signals for exactly one clock cycle per detected edge.

module sync_pos_neg_edge_detector (
    input  logic i_clk,
    input  logic i_rstb,
    input  logic i_detection_signal,
    output logic o_positive_edge_detected,
    output logic o_negative_edge_detected
);

    // Internal register to hold the previous state of the detection signal
    logic signal_prev;

    always_ff @(posedge i_clk or negedge i_rstb) begin
        if (!i_rstb) begin
            // Asynchronous active-low reset: clear all state and outputs
            signal_prev             <= 1'b0;
            o_positive_edge_detected <= 1'b0;
            o_negative_edge_detected <= 1'b0;
        end else begin
            // Update the previous signal register with the current input
            signal_prev <= i_detection_signal;

            // Detect positive edge: current is high, previous was low
            // At this point, signal_prev still holds the value from the
            // prior cycle (before the assignment above takes effect),
            // so the comparison is valid and produces a registered output
            // asserted for exactly one clock cycle.
            o_positive_edge_detected <= i_detection_signal & ~signal_prev;

            // Detect negative edge: current is low, previous was high
            o_negative_edge_detected <= ~i_detection_signal & signal_prev;
        end
    end

endmodule
