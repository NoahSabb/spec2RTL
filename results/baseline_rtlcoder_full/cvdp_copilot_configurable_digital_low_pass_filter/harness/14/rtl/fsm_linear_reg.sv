---
<s> module fsm_linear_reg(
  input clk,
  input reset,
  input start,
  input signed [DATA_WIDTH-1:0] x_in,
  input signed [DATA_WIDTH-1:0] w_in,
  input signed [DATA_WIDTH-1:0] b_in,
  output reg signed [2*DATA_WIDTH-1:0] result1,
  output reg signed [DATA_WIDTH:0] result2,
  output reg done
);

// SystemVerilog state machine
localparam IDLE = 2'b00;
localparam COMPUTE = 2'b01;
localparam DONE = 2'b10;
reg [1:0] state_next;
always @ (posedge clk, posedge reset)
begin
  if(reset) begin
    state_next <= IDLE;
    result1 <= {DATA_WIDTH{1'b0}};
    result2 <= {DATA_WIDTH+1{1'b0}};
    done <= 1'b0;
  end else begin
    case(state_next)
      IDLE:
        if(start == 1'b1) begin
          state_next <= COMPUTE;
          result1 <= {w_in*x_in, DATA_WIDTH{1'b0}};
          result2 <= {b_in, x_in[DATA_WIDTH-3:0]};
        end else begin
          state_next <= IDLE;
          result2 <= {DATA_WIDTH+1{1'b0}};
        end
      COMPUTE:
        if(result1 != 2*DATA_WIDTH) begin
          state_next <= DONE;
          done <= 1'b1;
        end else begin
          state_next <= COMPUTE;
          done <= 1'b0;
        end
      default:
        state_next <= IDLE;
    endcase
  end
end

endmodule