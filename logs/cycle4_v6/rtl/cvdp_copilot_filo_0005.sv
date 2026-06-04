module FILO_RTL #(
    parameter DATA_WIDTH = 8,
    parameter FILO_DEPTH = 16
)(
    input wire clk,
    input wire reset,
    input wire push,
    input wire pop,
    input wire [DATA_WIDTH-1:0] data_in,
    output reg [DATA_WIDTH-1:0] data_out,
    output reg full,
    output reg empty
);

    // Internal storage for the FILO buffer
    reg [DATA_WIDTH-1:0] buffer [FILO_DEPTH-1:0];
    
    // Pointer to the top of the FILO
    reg [$clog2(FILO_DEPTH):0] top;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            top <= 0;
            full <= 0;
            empty <= 1;
            data_out <= {DATA_WIDTH{1'b0}};
        end else begin
            // Handle feedthrough scenario: buffer is empty, both push and pop asserted
            if (push && pop && empty) begin
                data_out <= data_in;
                // top remains 0, empty remains 1, full remains 0
            end else if (push && pop && !empty) begin
                // Simultaneous push and pop when not empty:
                // Pop the current top, then push new data at same location
                // Net effect: top stays the same, data_out gets old top value
                data_out <= buffer[top - 1];
                buffer[top - 1] <= data_in;
                // top, full, empty flags remain unchanged
            end else begin
                if (push && !full) begin
                    buffer[top] <= data_in;
                    top <= top + 1;
                    empty <= 0;
                    if (top + 1 == FILO_DEPTH)
                        full <= 1;
                end
                if (pop && !empty) begin
                    data_out <= buffer[top - 1];
                    top <= top - 1;
                    full <= 0;
                    if (top - 1 == 0)
                        empty <= 1;
                end
            end
        end
    end

endmodule
