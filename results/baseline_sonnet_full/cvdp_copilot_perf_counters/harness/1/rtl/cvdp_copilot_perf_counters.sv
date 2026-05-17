// Performance Counter Module
// Counts events triggered by CPU pipeline and has software-controlled reset

module cvdp_copilot_perf_counters #(
    parameter CNT_W = 32  // Counter width, parameterizable
) (
    input  logic             clk,        // Clock signal
    input  logic             reset,      // Active-high asynchronous reset
    input  logic             sw_req_i,   // Software request signal
    input  logic             cpu_trig_i, // CPU trigger signal
    output logic [CNT_W-1:0] p_count_o   // Performance counter output
);

    // Internal counter register
    logic [CNT_W-1:0] count_q;

    // Counter logic: increment on cpu_trig_i, reset after sw_req_i read
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            count_q <= {CNT_W{1'b0}};
        end else if (sw_req_i) begin
            // After software reads, reset counter to zero
            // But if cpu_trig_i is also active at the same time,
            // we still reset (read takes priority for reset, but count starts fresh)
            if (cpu_trig_i) begin
                count_q <= {{(CNT_W-1){1'b0}}, 1'b1};
            end else begin
                count_q <= {CNT_W{1'b0}};
            end
        end else if (cpu_trig_i) begin
            count_q <= count_q + {{(CNT_W-1){1'b0}}, 1'b1};
        end
    end

    // Output logic: only output counter value when software requests it
    // Otherwise output zero
    always_comb begin
        if (sw_req_i) begin
            p_count_o = count_q;
        end else begin
            p_count_o = {CNT_W{1'b0}};
        end
    end

endmodule
