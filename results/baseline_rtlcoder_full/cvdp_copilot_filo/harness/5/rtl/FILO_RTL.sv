module FILO_RTL (
  input clk,
  input reset,
  input push,
  input pop,
  input [`DATA_WIDTH-1:`DATA_WIDTH] data_in,
  output reg [`DATA_WIDTH-1:`DATA_WIDTH] data_out,
  output reg full,
  output reg empty
);

parameter DATA_WIDTH = 8;
parameter FILO_DEPTH = 16;

// Internal state variables
reg [`DATA_WIDTH-1:`DATA_WIDTH] mem [0:FILO_DEPTH-1]; // memory buffer
reg [$clog2(FILO_DEPTH)-1:0] top; // current top of the stack pointer

always @ (posedge clk) begin
  if (reset) begin
    // reset operation
    top <= 0;
    full <= 0;
    empty <= 1;
  end else begin
    if (push && !full) begin
      mem[top] <= data_in;
      top <= top + 1;
      if (top == FILO_DEPTH) begin
        full <= 1;
      end
      empty <= 0;
    end

    if (pop && !empty) begin
      data_out <= mem[top-1];
      top <= top - 1;
      if (top == 0) begin
        empty <= 1;
      end
      full <= 0;
    end
  end
end

endmodule