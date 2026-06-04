module cvdp_copilot_perf_counters #(
    parameter CNT_W = 8  // Parameterizable counter width
) (
    input wire clk,          // Clock signal
    input wire reset,        // Active-high reset signal
    input wire sw_req_i,     // Software request signal
    input wire cpu_trig_i,   // CPU trigger signal
    output reg [CNT_W-1:0] p_count_o // Performance counter output
);

    reg [CNT_W-1:0] count_q; // Internal register to hold the counter value

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            count_q <= '0;  // Asynchronous reset sets counter to zero
        end else begin
            if (sw_req_i) begin
                count_q <= cpu_trig_i ? 1 : '0;  // reset on read; if trig also active, start at 1
            end else if (cpu_trig_i) begin
                count_q <= count_q + 1;  // Increment counter on CPU trigger
            end
        end
    end

    always @(*) begin
        if (sw_req_i)
            p_count_o = count_q;
        else
            p_count_o = '0;
    end

endmodule
