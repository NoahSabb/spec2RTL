<s> module moving_average(
    input clk,
    input reset,
    input [11 : 0] data_in,
    output reg [11 : 0] data_out
);

    // Declare internal registers here
    reg [11:0] sum;
    reg [4:0] count;
    reg [11:0] buffer [7:0];

    always @(posedge clk) begin
        if (reset) begin
            // Reset behavior
            sum <= 0;
            count <= 0;
            for (int i = 0; i < 8; i++) begin
                buffer[i] <= 0;
            end
            data_out <= 0;
        end else begin
            // Check if a new sample is available
            buffer[count] <= data_in;
            sum <= sum + data_in - (count > 0 ? buffer[count - 1] : 0);
            count <= count + 1;
            
            // Update output
            if (count < 8) begin
                data_out <= {(8 - count){1'b0}} * ((8 - count) / {(sum == 0) ? 1 : sum})
                          + (count > 0 ? buffer[count - 1] : 0);
            end else if (count > 7) begin
                data_out <= ((count - 7 > 0) ? 0 : sum / {(sum == 0) ? 1 : 7});
            end
        end
    end
endmodule