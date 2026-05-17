module moving_average (
    input  wire        clk,
    input  wire        reset,
    input  wire [11:0] data_in,
    output reg  [11:0] data_out
);

    // Memory buffer to store last 8 samples
    reg [11:0] buffer [0:7];
    
    // Index to track current position in circular buffer
    reg [2:0] index;
    
    // Sum register - needs enough bits to hold sum of 8 12-bit values
    // Max sum = 8 * 4095 = 32760, needs 15 bits
    reg [14:0] sum;
    
    integer i;
    
    always @(posedge clk) begin
        if (reset) begin
            // Clear all buffer entries
            for (i = 0; i < 8; i = i + 1) begin
                buffer[i] <= 12'b0;
            end
            index   <= 3'b0;
            sum     <= 15'b0;
            data_out <= 12'b0;
        end else begin
            // Update sum: subtract old value at current index, add new value
            sum <= sum - buffer[index] + data_in;
            
            // Store new sample in buffer at current index
            buffer[index] <= data_in;
            
            // Advance index (wraps around 0-7)
            index <= index + 1;
            
            // Output is sum divided by 8 (right shift by 3)
            data_out <= (sum - buffer[index] + data_in) >> 3;
        end
    end

endmodule
