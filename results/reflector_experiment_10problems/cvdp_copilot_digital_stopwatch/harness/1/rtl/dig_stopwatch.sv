module dig_stopwatch #(
    parameter int CLK_FREQ = 50_000_000
) (
    input  logic       clk,
    input  logic       reset,
    input  logic       start_stop,
    output logic [5:0] seconds,
    output logic [5:0] minutes,
    output logic       hour
);

    // Counter max value: CLK_FREQ - 1 cycles to count one second
    localparam int COUNTER_MAX = CLK_FREQ - 1;
    
    // Width calculation for clock divider counter
    localparam int COUNTER_WIDTH = $clog2(CLK_FREQ);

    // Clock divider counter
    logic [COUNTER_WIDTH-1:0] clk_div_count;
    
    // One second pulse - single cycle pulse
    logic one_sec_pulse;

    // Clock divider: counts CLK_FREQ cycles to produce a one-second pulse
    // The counter only advances when start_stop is high
    // The pulse is generated ONLY when start_stop is high AND counter reaches max
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            clk_div_count <= '0;
            one_sec_pulse <= 1'b0;
        end else begin
            // Default: pulse is low
            one_sec_pulse <= 1'b0;
            
            if (start_stop) begin
                if (clk_div_count == COUNTER_WIDTH'(COUNTER_MAX)) begin
                    // Reset divider and generate pulse - only when running
                    clk_div_count <= '0;
                    one_sec_pulse <= 1'b1;
                end else begin
                    clk_div_count <= clk_div_count + 1'b1;
                end
            end
            // When start_stop is low: clk_div_count holds its value (pause behavior)
            // one_sec_pulse remains 0 (already set above)
        end
    end

    // Seconds, minutes, and hour counters
    // Defensive gating: require both one_sec_pulse AND start_stop
    // This prevents stale pulse consumption if start_stop transitions
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            seconds <= 6'd0;
            minutes <= 6'd0;
            hour    <= 1'b0;
        end else begin
            // Only update counters when pulse is valid AND stopwatch is running AND hour limit not reached
            if (one_sec_pulse && start_stop && !hour) begin
                if (seconds == 6'd59) begin
                    seconds <= 6'd0;
                    if (minutes == 6'd59) begin
                        minutes <= 6'd0;
                        hour    <= 1'b1;
                    end else begin
                        minutes <= minutes + 6'd1;
                    end
                end else begin
                    seconds <= seconds + 6'd1;
                end
            end
        end
    end

endmodule
