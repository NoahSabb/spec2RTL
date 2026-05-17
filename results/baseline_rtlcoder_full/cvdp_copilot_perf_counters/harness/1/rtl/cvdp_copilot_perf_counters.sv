module cvdp_copilot_perf_counters #(
    parameter CNT_W = 12
) (
    input clk, // Clock signal
    input reset, // Active-high reset signal
    input sw_req_i, // Software request signal
    input cpu_trig_i, // CPU trigger signal
    output reg [CNT_W-1:0] p_count_o // Performance counter output
);

reg [CNT_W-1:0] count_q; // Performance counter value
wire trig_int = ~cpu_trig_i & ~sw_req_i & ~reset; // Trigger condition

always @(posedge clk or posedge reset) begin
    if (reset) begin
        count_q <= 0;
    end else if (trig_int) begin
        count_q <= count_q + 1'b1;
    end
end

assign p_count_o = sw_req_i ? count_q : {(CNT_W){1'b0}}; // Output counter value based on read request

endmodule