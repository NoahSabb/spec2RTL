module dig_stopwatch #(
    parameter CLK_FREQ = 50000000
)(
    input  logic       clk,
    input  logic       reset,
    input  logic       start_stop,
    output logic [5:0] seconds,
    output logic [5:0] minutes,
    output logic       hour
);

    // Internal signals
    logic [$clog2(CLK_FREQ)-1:0] clk_div_counter;
    logic one_sec_pulse;

    // Combinational one_sec_pulse
    assign one_sec_pulse = start_stop && !hour && (clk_div_counter == CLK_FREQ - 1);

    // Clock divider: counts CLK_FREQ cycles to produce a one-second pulse
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            clk_div_counter <= '0;
        end else begin
            if (start_stop && !hour) begin
                if (clk_div_counter == CLK_FREQ - 1) begin
                    clk_div_counter <= '0;
                end else begin
                    clk_div_counter <= clk_div_counter + 1'b1;
                end
            end
            // When paused, hold clk_div_counter to preserve partial second
        end
    end

    // Seconds, minutes, hour counters
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            seconds <= 6'd0;
            minutes <= 6'd0;
            hour    <= 1'b0;
        end else begin
            if (one_sec_pulse) begin
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
