<s> module advanced_decimator_with_adaptive_peak_detection(
    input clk,
    input reset,
    input valid_in,
    input signed [DATA_WIDTH-1:0] data_in,
    output reg valid_out,
    output reg signed [DATA_WIDTH * (N / DEC_FACTOR) - 1:0] data_out,
    output reg signed [DATA_WIDTH-1:0] peak_value
);

parameter N = 8;
parameter DATA_WIDTH = 16;
parameter DEC_FACTOR = 4;

reg signed [DATA_WIDTH-1:0] data_array[(N/DEC_FACTOR)-1:0]; // decimated samples
integer i;
always @ (posedge clk or posedge reset) begin
    if (reset) begin
        valid_out <= 1'b0;
        
        for (i = 0; i < N / DEC_FACTOR; i = i + 1) begin
            data_array[i] <= 'd0;
        end
    end else if (valid_in) begin
        valid_out <= 1'b1;
        for (i = 0; i < N / DEC_FACTOR; i = i + 1) begin
            data_array[i] <= data_in[(i * DATA_WIDTH) +: DATA_WIDTH];
        end
    end else begin
        valid_out <= 1'b0;
    end
end

reg signed [DATA_WIDTH-1:0] max_value = 'd0; // peak value holder
always @ (data_array) begin
    // set the initial value of peak_value to the first sample in decimated data
    peak_value <= data_array[0];
    
    // iterate through all samples and update peak_value if a larger value is found
    for (i = 1; i < N / DEC_FACTOR; i = i + 1) begin
        if (data_array[i] > max_value) begin
            max_value <= data_array[i];
            peak_value <= max_value;
        end
    end
end

// pack the decimated samples into a single bus
always @ (decimated_signals) begin
    for (i = 0; i < N / DEC_FACTOR; i = i + 1) begin
        data_out[(i * DATA_WIDTH) +: DATA_WIDTH] <= decimated_signals[i];
    end
end

endmodule