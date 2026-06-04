module dig_stopwatch #(
    parameter CLK_FREQ = 50000000 // Default clock frequency in Hz
)(
    input wire clk,          // Input clock signal
    input wire reset,        // Asynchronous active-high reset signal
    input wire start_stop,   // Start/stop control signal
    
    output reg [5:0] seconds, // 6-bit counter for seconds (0-59)
    output reg [5:0] minutes, // 6-bit counter for minutes (0-59)
    output reg hour           // One-bit signal indicating one hour has passed
);

    // Internal signals
    reg [31:0] clk_div_counter; // Clock divider counter
    reg one_sec_pulse;           // One-second pulse signal

    // Clock divider to generate a one-second pulse
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            clk_div_counter <= 0;
            one_sec_pulse <= 0;
        end else begin
            if (start_stop) begin
                if (clk_div_counter == CLK_FREQ - 1) begin
                    clk_div_counter <= 0;
                    one_sec_pulse <= 1;
                end else begin
                    clk_div_counter <= clk_div_counter + 1;
                    one_sec_pulse <= 0;
                end
            end else begin
                one_sec_pulse <= 0;
                // clk_div_counter holds its value
            end
        end
    end

    // Stopwatch logic
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            seconds <= 0;
            minutes <= 0;
            hour <= 0;
        end else if (one_sec_pulse && start_stop && !hour) begin
            if (seconds == 59) begin
                seconds <= 0;
                if (minutes == 59) begin
                    minutes <= 0;
                    hour <= 1; // Set hour to 1 after reaching one hour
                end else begin
                    minutes <= minutes + 1;
                end
            end else begin
                seconds <= seconds + 1;
            end
        end
    end

endmodule
