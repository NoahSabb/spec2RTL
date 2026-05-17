module data_width_converter (
    input clk, reset,
    input [31:0] data_in,
    input data_valid,
    output reg [127:0] o_data_out,
    output reg o_data_out_valid
);

// Internal registers
reg [3:0] count;
reg [127:0] buffer;

always @(posedge clk) begin
    if (reset) begin
        // Reset all internal registers and buffers
        count <= 4'd0;
        buffer <= 128'd0;
        o_data_out_valid <= 1'b0;
    end else begin
        if (data_valid) begin
            // Increment counter
            if (count < 3) count <= count + 1;
            else count <= 4'd0;
            
            // Populate buffer
            case (count)
                4'd0: buffer <= {data_in, buffer[127:32]};
                4'd1: buffer <= {data_in, buffer[127:32], data_in};
                4'd2: buffer <= {data_in, buffer[127:32], data_in, data_in};
                4'd3: buffer <= {buffer[95:0], data_in, buffer[127:96]};
            endcase
            
            // Set output valid flag
            if (count == 4) o_data_out_valid <= 1'b1;
        end else begin
            o_data_out_valid <= 1'b0;
        end
        
        o_data_out <= buffer;
    end
end

endmodule