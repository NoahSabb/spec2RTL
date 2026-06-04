module sync_lifo #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = 3
)(
    input  wire                  clock,
    input  wire                  reset,
    input  wire                  write_en,
    input  wire                  read_en,
    input  wire [DATA_WIDTH-1:0] data_in,
    output reg                   empty,
    output reg                   full,
    output reg  [DATA_WIDTH-1:0] data_out
);

    localparam DEPTH = 2**ADDR_WIDTH;

    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    reg [ADDR_WIDTH:0]   sp;

    integer i;

    always @(posedge clock) begin
        if (reset) begin
            sp       <= 0;
            empty    <= 1;
            full     <= 0;
            data_out <= 0;
            for (i = 0; i < DEPTH; i = i + 1) begin
                mem[i] <= 0;
            end
        end else begin
            if (write_en && !full) begin
                mem[sp] <= data_in;
                sp      <= sp + 1;
                empty   <= 0;
                full    <= (sp + 1 == DEPTH);
            end else if (read_en && !empty) begin
                data_out <= mem[sp - 1];
                sp       <= sp - 1;
                full     <= 0;
                empty    <= (sp - 1 == 0);
            end
        end
    end

endmodule
