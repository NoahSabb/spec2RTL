module dig_stopwatch #(
    parameter int CLK_FREQ = 50_000_000
)(
    input  logic        clk,
    input  logic        reset,
    input  logic        start_stop,
    output logic [5:0]  seconds,
    output logic [5:0]  minutes,
    output logic        hour
);

    // Clock divider counter
    // We need to count CLK_FREQ cycles to produce a one-second pulse
    // Counter goes from 0 to CLK_FREQ-1
    localparam int COUNTER_MAX = CLK_FREQ - 1;
    
    // Determine the width needed for the counter
    localparam int COUNTER_WIDTH = $clog2(CLK_FREQ);
    
    logic [COUNTER_WIDTH-1:0] clk_div_counter;
    logic one_sec_pulse;
    
    // Clock divider: counts input clock cycles, produces pulse when one second elapses
    // The counter pauses when start_stop is low (stopwatch is paused)
    // But we need to hold partial progress when paused
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            clk_div_counter <= '0;
            one_sec_pulse   <= 1'b0;
        end else begin
            one_sec_pulse <= 1'b0; // default: pulse is low
            if (start_stop) begin
                if (hour) begin
                    // Stopwatch has reached one hour, hold state
                    clk_div_counter <= '0;
                end else begin
                    if (clk_div_counter == COUNTER_MAX[COUNTER_WIDTH-1:0]) begin
                        clk_div_counter <= '0;
                        one_sec_pulse   <= 1'b1;
                    end else begin
                        clk_div_counter <= clk_div_counter + 1'b1;
                    end
                end
            end
            // When start_stop is low, hold clk_div_counter (partial progress preserved)
        end
    end
    
    // Seconds, minutes, hour counters
    // Update on the rising edge of one_sec_pulse (which is a single clk-period pulse)
    // Since one_sec_pulse is already synchronized to clk edges, we just check it
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            seconds <= 6'd0;
            minutes <= 6'd0;
            hour    <= 1'b0;
        end else begin
            if (one_sec_pulse && !hour) begin
                if (seconds == 6'd59) begin
                    seconds <= 6'd0;
                    if (minutes == 6'd59) begin
                        minutes <= 6'd0;
                        hour    <= 1'b1;
                    end else begin
                        minutes <= minutes + 1'b1;
                    end
                end else begin
                    seconds <= seconds + 1'b1;
                end
            end
        end
    end

endmodule
