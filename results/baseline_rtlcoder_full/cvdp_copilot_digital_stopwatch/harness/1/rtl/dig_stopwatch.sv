module dig_stopwatch(
    input clk, // 1Hz clock for 1 second pulse generation
    input reset, // Asynchronous active-high reset signal.
    input start_stop, // Start/stop control that controls if the stopwatch is running or paused.
    output reg [5:0] seconds, // 6-bit counter for seconds (0-59).
    output reg [5:0] minutes,// 6-bit counter for minutes (0-59).
    output reg hour // Represents a one-bit signal that updates to 1 when one hour has passed.
);

parameter CLK_FREQ = 50000000; // Clock frequency in Hz with the default value of 50 MHz.

reg [31:0] clk_divider; // Internal clock divider for counting one pulse per second
always @(posedge clk) begin
    if (reset) begin
        seconds <= 0; // Reset counters to zero if reset occurs
        minutes <= 0;
        hour <= 0;
    end else if (start_stop) begin
        if (seconds == 59) begin
            seconds <= 0;
            if (minutes == 59) begin
                minutes <= 0;
                if (hour) begin
                    hour <= 0;
                end else begin
                    hour <= 1; // Set hour signal to 1 after reaching one hour.
                end
            end else begin
                minutes <= minutes + 1;
            end
        end else begin
            seconds <= seconds + 1; // Increment seconds count
        end
    end
end

always @(posedge clk) begin
    if (reset) begin
        clk_divider <= 0;
    end else if (start_stop) begin
        clk_divider <= clk_divider + 1; // Increment internal clock divider on each rising edge of clk
        
        if (clk_divider == CLK_FREQ/2 - 1) begin // Divide by 2 since clk_divider starts counting from zero
            seconds <= seconds + 1; // Increment seconds count when one full second passes
            
            if (seconds == 59) begin
                seconds <= 0;
                minutes <= minutes + 1; // Increment minutes count when one full hour passes
                
                if (minutes == 59) begin
                    minutes <= 0;
                    hour <= 1; // Set hour signal to 1 after reaching one hour.
                end
            end
        end
    end else if (!start_stop && clk_divider == CLK_FREQ/2 - 1) begin // Resume counting from the exact point where it was paused
        seconds <= seconds + 1; // Increment seconds count when one full second passes
            
            if (seconds == 59) begin
                seconds <= 0;
                minutes <= minutes + 1; // Increment minutes count when one full hour passes
                
                    if (minutes == 59) begin
                        minutes <= 0;
                        hour <= 1; // Set hour signal to 1 after reaching one hour.
                    end
                    // No pause-resume or mid-counting reset logic needed because seconds and minutes counters will continue from where the stopwatch was paused
                end
            end
        end
    end
end

endmodule