// Performance Counter Module
// Counts events triggered by CPU pipeline and supports software-controlled read and reset

module cvdp_copilot_perf_counters #(
    parameter CNT_W = 32  // Parameterizable counter width
) (
    input  logic             clk,
    input  logic             reset,
    input  logic             sw_req_i,
    input  logic             cpu_trig_i,
    output logic [CNT_W-1:0] p_count_o
);

    // Internal counter register
    logic [CNT_W-1:0] count_q;

    // Counter logic: increment on cpu_trig_i, reset to zero after sw_req_i read
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            count_q <= {CNT_W{1'b0}};
        end else if (sw_req_i) begin
            // After software reads the counter, reset to zero next cycle
            // But if cpu_trig_i is also active at same time, start from 1
            if (cpu_trig_i) begin
                count_q <= {{(CNT_W-1){1'b0}}, 1'b1};
            end else begin
                count_q <= {CNT_W{1'b0}};
            end
        end else if (cpu_trig_i) begin
            // Increment counter on trigger event
            count_q <= count_q + {{(CNT_W-1){1'b0}}, 1'b1};
        end
    end

    // Output logic: only output counter value when software read request is active
    always_comb begin
        if (sw_req_i) begin
            p_count_o = count_q;
        end else begin
            p_count_o = {CNT_W{1'b0}};
        end
    end

endmodule
