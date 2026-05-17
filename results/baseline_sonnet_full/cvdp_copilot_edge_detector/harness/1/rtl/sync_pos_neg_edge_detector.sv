module sync_pos_neg_edge_detector (
    input  logic i_clk,
    input  logic i_rstb,
    input  logic i_detection_signal,
    output logic o_positive_edge_detected,
    output logic o_negative_edge_detected
);

    logic detection_signal_prev;

    always_ff @(posedge i_clk or negedge i_rstb) begin
        if (!i_rstb) begin
            detection_signal_prev    <= 1'b0;
        end else begin
            detection_signal_prev    <= i_detection_signal;
        end
    end

    assign o_positive_edge_detected = i_detection_signal & ~detection_signal_prev;
    assign o_negative_edge_detected = ~i_detection_signal & detection_signal_prev;

endmodule
