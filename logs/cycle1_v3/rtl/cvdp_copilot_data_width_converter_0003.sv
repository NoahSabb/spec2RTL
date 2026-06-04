module data_width_converter (
    input wire clk,
    input wire reset,
    input wire [31:0] data_in,
    input wire data_valid,
    output reg [127:0] o_data_out,
    output reg o_data_out_valid
);

    // Internal registers to store the 32-bit inputs
    reg [31:0] buffer [3:0];
    
    // Counter to track the number of valid inputs received
    reg [1:0] count;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            count <= 2'b00;
            o_data_out_valid <= 1'b0;
            o_data_out <= 128'b0;
            buffer[0] <= 32'b0;
            buffer[1] <= 32'b0;
            buffer[2] <= 32'b0;
            buffer[3] <= 32'b0;
        end else begin
            if (data_valid) begin
                if (count == 2'b11) begin
                    // This is the 4th valid input
                    o_data_out <= {buffer[0], buffer[1], buffer[2], data_in};
                    o_data_out_valid <= 1'b1;
                    count <= 2'b00;
                end else begin
                    buffer[count] <= data_in;
                    count <= count + 1;
                    o_data_out_valid <= 1'b0;
                end
            end else begin
                o_data_out_valid <= 1'b0;
            end
        end
    end

endmodule
