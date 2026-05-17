or immediately on reset

<s> module bcd_counter(
    input clk,
    input rst,
    output reg [3:0] ms_hr,
    output reg [3:0] ls_hr,
    output reg [3:0] ms_min,
    output reg [3:0] ls_min,
    output reg [3:0] ms_sec,
    output reg [3:0] ls_sec
);

    // Initial values at reset—all 6 counters begin at zero
    initial begin
        ms_hr = 4'b0;
        ls_hr = 4'b0;
        ms_min = 4'b0;
        ls_min = 4'b0;
        ms_sec = 4'b0;
        ls_sec = 4'b0;
    end

    // Counter logic - 3 tiers:
    // 1. seconds counter only increments in most significant digit if least significant digit is full and overflowed
    // 2. minutes counter increment logic flows up to most significant digit from last non-overflowed digit
    // 3. hours counter works the same but uses minute digits instead of second digits
    always @ (posedge clk or posedge rst) begin
        if (rst) begin
            ms_hr <= 4'b0;
            ls_hr <= 4'b0;
            ms_min <= 4'b0;
            ls_min <= 4'b0;
            ms_sec <= 4'b0;
            ls_sec <= 4'b0;
        end else begin
            // Increment seconds counter only if there is a carry chain from least significant digit - cascades to most significant digit ONLY on overflow
            if (ls_sec == 4'b9) begin
                ms_sec <= ms_sec + 1;
                ls_sec <= 4'b0;
                // Increment minutes counter only if there was an increment to seconds counter - cascades to most significant digit ONLY on overflow
                if (ms_sec == 4'b5 && ls_sec == 4'b9) begin
                    ms_min <= ms_min + 1;
                    ls_min <= 'bx;
                    
                    // Increment hours counter only if there was an increment to minutes counter - cascades to most significant digit ONLY on overflow
                    if (ms_min == 4'b59 && ms_sec == 4'b6) begin
                        ms_hr <= ms_hr + 1;
                        ls_hr <= 'bx;
                        
                        // Reset all counters and cascade on overflow - 23:59:59
                        if (ms_hr == 4'b2) begin
                            ms_hr <= 4'b0;
                            ls_hr <= 'bx;
                            ms_min <= 4'b0;
                            ls_min <= 'bx;
                            ms_sec <= 4'b0;
                            ls_sec <= 'bx;
                        end
                    end
                end
            end else begin
                // No carry chain - reset least significant digit
                ls_sec <= 4'b0;
            end
        end
    end
endmodule