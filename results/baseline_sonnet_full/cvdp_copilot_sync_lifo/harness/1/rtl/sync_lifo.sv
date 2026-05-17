module sync_lifo #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = 3
) (
    input  logic                  clock,
    input  logic                  reset,
    input  logic                  write_en,
    input  logic                  read_en,
    input  logic [DATA_WIDTH-1:0] data_in,
    output logic                  empty,
    output logic                  full,
    output logic [DATA_WIDTH-1:0] data_out
);

    localparam DEPTH = 2**ADDR_WIDTH;

    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    logic [ADDR_WIDTH:0]   stack_ptr; // One extra bit to detect full/empty

    // Full and empty signals
    assign empty = (stack_ptr == 0);
    assign full  = (stack_ptr == DEPTH);

    integer i;

    always_ff @(posedge clock) begin
        if (reset) begin
            stack_ptr <= 0;
            data_out  <= {DATA_WIDTH{1'b0}};
            for (i = 0; i < DEPTH; i = i + 1) begin
                mem[i] <= {DATA_WIDTH{1'b0}};
            end
        end else begin
            // Write operation
            if (write_en && !full) begin
                mem[stack_ptr] <= data_in;
                stack_ptr <= stack_ptr + 1;
            end

            // Read operation
            if (read_en && !empty) begin
                data_out  <= mem[stack_ptr - 1];
                stack_ptr <= stack_ptr - 1;
            end
        end
    end

endmodule
