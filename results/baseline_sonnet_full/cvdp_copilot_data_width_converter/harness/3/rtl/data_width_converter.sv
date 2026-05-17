module data_width_converter (
    input  logic        clk,
    input  logic        reset,
    input  logic [31:0] data_in,
    input  logic        data_valid,
    output logic [127:0] o_data_out,
    output logic        o_data_out_valid
);

    logic [31:0] buffer [0:3];
    logic [1:0]  count;

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            count            <= 2'd0;
            o_data_out       <= 128'd0;
            o_data_out_valid <= 1'b0;
            buffer[0]        <= 32'd0;
            buffer[1]        <= 32'd0;
            buffer[2]        <= 32'd0;
            buffer[3]        <= 32'd0;
        end else begin
            o_data_out_valid <= 1'b0;
            
            if (data_valid) begin
                buffer[count] <= data_in;
                
                if (count == 2'd3) begin
                    o_data_out       <= {buffer[0], buffer[1], buffer[2], data_in};
                    o_data_out_valid <= 1'b1;
                    count            <= 2'd0;
                end else begin
                    count <= count + 2'd1;
                end
            end
        end
    end

endmodule
