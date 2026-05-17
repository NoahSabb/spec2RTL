module sync_pos_neg_edge_detector (
    input i_clk,
    input i_rstb,
    input i_detection_signal,
    output o_positive_edge_detected,
    output o_negative_edge_detected
);

reg positive_edge_last;
reg negative_edge_last;

wire rising_edge = (i_detection_signal & ~positive_edge_last) | (~i_detection_signal & positive_edge_last);
wire falling_edge = (i_detection_signal & ~negative_edge_last) | (~i_detection_signal & negative_edge_last);

assign o_positive_edge_detected = rising_edge;
assign o_negative_edge_detected = falling_edge;

always @(posedge i_clk or negedge i_rstb) begin
    if (!i_rstb) begin
        positive_edge_last <= 0;
        negative_edge_last <= 0;
    end else begin
        positive_edge_last <= rising_edge;
        negative_edge_last <= falling_edge;
    end
end

endmodule