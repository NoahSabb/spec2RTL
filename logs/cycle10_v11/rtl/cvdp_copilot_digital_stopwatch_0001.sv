module dig_stopwatch #(
    parameter integer CLK_FREQ = 50_000_000
) (
    input  wire        clk,
    input  wire        reset,
    input  wire        start_stop,
    output reg  [5:0]  seconds,
    output reg  [5:0]  minutes,
    output reg         hour,
    output reg         one_sec_pulse
);

    // Internal clock divider counter
    reg [31:0] clk_div_counter;

    // Clock divider counter logic and one_sec_pulse generation
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            clk_div_counter <= 0;
            one_sec_pulse   <= 0;
        end else if (start_stop) begin
            if (clk_div_counter == CLK_FREQ - 1) begin
                clk_div_counter <= 0;
                one_sec_pulse   <= 1;
            end else begin
                clk_div_counter <= clk_div_counter + 1;
                one_sec_pulse   <= 0;
            end
        end else begin
            // When start_stop == 0, freeze counter and clear pulse
            one_sec_pulse <= 0;
        end
    end

    // Stopwatch seconds/minutes/hour logic
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            seconds <= 0;
            minutes <= 0;
            hour    <= 0;
        end else if (one_sec_pulse) begin
            if (seconds == 59) begin
                seconds <= 0;
                if (minutes == 59) begin
                    minutes <= 0;
                    hour    <= 1;
                end else begin
                    minutes <= minutes + 1;
                end
            end else begin
                seconds <= seconds + 1;
            end
        end
    end

endmodule
