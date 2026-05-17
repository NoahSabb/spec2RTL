module palindrome_detect #( 
parameter N=3
) (
input clk,
input reset,
input bit_stream,
output palindrome_detected
);

// Shift register to store the last N bits
reg [N-1:0] shift_reg;

// Shift in the new bit at every clock cycle
always @(posedge clk) begin
    if (reset) begin
        shift_reg <= {N{1'b0}};
    end else begin
        shift_reg <= {shift_reg[N-2:0], bit_stream};
    end
end

// Check if the current N-bit window is a palindrome
// A 3-bit palindrome: bit[2] == bit[0] (middle bit can be anything)
// shift_reg[N-1] is the oldest bit, shift_reg[0] is the newest bit
reg palindrome_reg;

always @(posedge clk) begin
    if (reset) begin
        palindrome_reg <= 1'b0;
    end else begin
        // Check palindrome condition for N=3: first bit equals last bit
        // After shift, shift_reg = {old[N-2:0], bit_stream}
        // We need to check the window after the new bit is shifted in
        // The window will be: {shift_reg[N-2:0], bit_stream}
        // For N=3: window[2]=shift_reg[1], window[1]=shift_reg[0], window[0]=bit_stream
        // Palindrome if window[2] == window[0], i.e., shift_reg[1] == bit_stream
        palindrome_reg <= (shift_reg[N-2] == bit_stream);
    end
end

assign palindrome_detected = palindrome_reg;

endmodule
