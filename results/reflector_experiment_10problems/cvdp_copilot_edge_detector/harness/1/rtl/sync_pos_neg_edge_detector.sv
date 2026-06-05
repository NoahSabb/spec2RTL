// File: rtl/sync_pos_neg_edge_detector.sv
// Description: Synchronous positive and negative edge detector module
// Detects both rising and falling edges on a glitch-free, debounced input signal
// Each detection output is asserted for exactly one clock cycle

module sync_pos_neg_edge_detector (
    input  logic i_clk,                    // Clock signal (active on rising edge)
    input  logic i_rstb,                   // Asynchronous reset (active low)
    input  logic i_detection_signal,       // Glitch-free, debounced input signal

    output logic o_positive_edge_detected, // Asserted for one cycle on rising edge
    output logic o_negative_edge_detected  // Asserted for one cycle on falling edge
);

    // Internal register to store the previous state of the detection signal
    logic r_detection_signal_prev;

    // Sequential logic: capture the previous state of the input signal
    // with asynchronous reset
    always_ff @(posedge i_clk or negedge i_rstb) begin
        if (!i_rstb) begin
            r_detection_signal_prev <= 1'b0;
        end else begin
            r_detection_signal_prev <= i_detection_signal;
        end
    end

    // Sequential logic: register the edge detection outputs
    // This ensures outputs are asserted for exactly one clock cycle
    // and makes timing more robust
    always_ff @(posedge i_clk or negedge i_rstb) begin
        if (!i_rstb) begin
            o_positive_edge_detected <= 1'b0;
            o_negative_edge_detected <= 1'b0;
        end else begin
            // Positive edge: current is high, previous was low
            o_positive_edge_detected <= i_detection_signal & ~r_detection_signal_prev;
            // Negative edge: current is low, previous was high
            o_negative_edge_detected <= ~i_detection_signal & r_detection_signal_prev;
        end
    end

endmodule
