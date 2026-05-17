module dig_stopwatch #(
    parameter int CLK_FREQ = 50_000_000
) (
    input  logic        clk,
    input  logic        reset,
    input  logic        start_stop,
    output logic [5:0]  seconds,
    output logic [5:0]  minutes,
    output logic        hour
);

    // Calculate the number of bits needed to hold CLK_FREQ-1
    localparam int COUNTER_WIDTH = $clog2(CLK_FREQ);

    // Store COUNTER_MAX as a properly-sized localparam to avoid width mismatch
    localparam logic [COUNTER_WIDTH-1:0] COUNTER_MAX = CLK_FREQ - 1;

    // Internal clock divider counter
    logic [COUNTER_WIDTH-1:0] clk_div_counter;

    // One-second pulse signal
    logic one_sec_pulse;

    // -------------------------------------------------------------------------
    // Clock Divider: counts from 0 to CLK_FREQ-1, then pulses for one cycle
    // -------------------------------------------------------------------------
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            clk_div_counter <= '0;
        end else if (start_stop) begin
            if (clk_div_counter == COUNTER_MAX) begin
                clk_div_counter <= '0;
            end else begin
                clk_div_counter <= clk_div_counter + 1'b1;
            end
        end
        // When start_stop is low (paused), hold clk_div_counter at current value
    end

    // Generate one-second pulse: high for exactly one clk period
    assign one_sec_pulse = (start_stop && (clk_div_counter == COUNTER_MAX));

    // -------------------------------------------------------------------------
    // Seconds, Minutes, and Hour counters
    // -------------------------------------------------------------------------
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            seconds <= 6'd0;
            minutes <= 6'd0;
            hour    <= 1'b0;
        end else if (one_sec_pulse) begin
            // Only count if we haven't reached one hour
            if (!hour) begin
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
            // If hour == 1, hold at 1 hour, 0 minutes, 0 seconds (no further counting)
        end
    end

endmodule
