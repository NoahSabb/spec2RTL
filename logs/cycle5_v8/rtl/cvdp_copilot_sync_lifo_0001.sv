module sync_lifo #(
    parameter int DATA_WIDTH = 8,
    parameter int ADDR_WIDTH = 3
) (
    input logic clock,
    input logic reset,
    input logic write_en,
    input logic read_en,
    input logic [DATA_WIDTH-1:0] data_in,

    output logic empty,
    output logic full,
    output logic [DATA_WIDTH-1:0] data_out
);

    // Calculate the depth of the LIFO
    localparam int DEPTH = DATA_WIDTH;

    // Memory array to store the data
    logic [DATA_WIDTH-1:0] mem [DEPTH-1:0];

    // Stack pointer - points to next empty location
    logic [$clog2(DEPTH):0] write_ptr;

    // Internal signal for data output
    logic [DATA_WIDTH-1:0] current_data_out;

    // Full and Empty Flags
    assign full  = (write_ptr == DEPTH);
    assign empty = (write_ptr == '0);

    // Output Assignment
    assign data_out = current_data_out;

    // Combined Write (Push) and Read (Pop) Logic in a single always_ff block
    always_ff @(posedge clock) begin
        if (!reset) begin
            write_ptr <= '0;
            current_data_out <= '0;
            for (int i = 0; i < DEPTH; i++) begin
                mem[i] <= '0;
            end
        end else if (write_en && !full && read_en && !empty) begin
            // Simultaneous read and write: overwrite top of stack, pointer unchanged
            mem[write_ptr[$clog2(DEPTH)-1:0] - 1] <= data_in;
            current_data_out <= mem[write_ptr[$clog2(DEPTH)-1:0] - 1];
            // write_ptr stays the same
        end else if (write_en && !full) begin
            mem[write_ptr[$clog2(DEPTH)-1:0]] <= data_in;
            write_ptr <= write_ptr + 1;
        end else if (read_en && !empty) begin
            current_data_out <= mem[write_ptr[$clog2(DEPTH)-1:0] - 1];
            write_ptr <= write_ptr - 1;
        end
    end

endmodule
