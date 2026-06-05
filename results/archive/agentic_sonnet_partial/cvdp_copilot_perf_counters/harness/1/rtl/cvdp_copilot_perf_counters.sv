module cvdp_copilot_perf_counters #(
    parameter int CNT_W = 8
) (
    input  logic             clk,
    input  logic             reset,
    input  logic             sw_req_i,
    input  logic             cpu_trig_i,
    output logic [CNT_W-1:0] p_count_o
);

    logic [CNT_W-1:0] count_q;
    logic             do_reset_next;

    // Counter logic: increment on trigger, reset after software read
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            count_q <= '0;
        end else if (do_reset_next) begin
            // After software read, reset counter; still capture new trigger in same cycle
            if (cpu_trig_i) begin
                count_q <= {{(CNT_W-1){1'b0}}, 1'b1};
            end else begin
                count_q <= '0;
            end
        end else begin
            if (cpu_trig_i) begin
                count_q <= count_q + 1'b1;
            end
        end
    end

    // Track whether software read occurred last cycle to trigger reset
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            do_reset_next <= 1'b0;
        end else begin
            do_reset_next <= sw_req_i;
        end
    end

    // Output: only expose count when software requests it
    always_comb begin
        if (sw_req_i) begin
            p_count_o = count_q;
        end else begin
            p_count_o = '0;
        end
    end

endmodule
