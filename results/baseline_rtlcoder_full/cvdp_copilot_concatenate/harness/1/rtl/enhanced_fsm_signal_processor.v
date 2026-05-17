<s> module enhanced_fsm_signal_processor (
  input              i_clk,
  input              i_rst_n,
  input              i_enable,
  input              i_clear,
  input              i_ack,
  input              i_fault,
  input [4:0]        i_vector_1,
  input [4:0]        i_vector_2,
  input [4:0]        i_vector_3,
  input [4:0]        i_vector_4,
  input [4:0]        i_vector_5,
  input [4:0]        i_vector_6,
  output reg         o_ready,
  output reg         o_error,
  output reg [1:0]   o_fsm_status,
  output reg [7:0]   o_vector_1,
  output reg [7:0]   o_vector_2,
  output reg [7:0]   o_vector_3,
  output reg [7:0]   o_vector_4
);

  // FSM state encoding
  localparam IDLE = 2'b00;
  localparam PROCESS = 2'b01;
  localparam READY = 2'b10;
  localparam FAULT = 2'b11;
  
  // FSM current state and next state logic
  reg [1:0] state, next_state;
  
  always @ (posedge i_clk, negedge i_rst_n) begin
    if (!i_rst_n) begin
      state <= IDLE;
    end else begin
      state <= next_state;
    end
  end
  
  always @* begin
    case (state)
      IDLE: begin
        next_state = PROCESS;
        o_fsm_status = IDLE;
        if (i_fault) begin
          next_state = FAULT;
        end else if (!i_enable) begin
          next_state = IDLE;
        end
      end
      PROCESS: begin
        next_state = READY;
        o_fsm_status = PROCESS;
        if (i_fault) begin
          next_state = FAULT;
        end else if (!i_enable) begin
          next_state = IDLE;
        end
      end
      READY: begin
        next_state = IDLE;
        o_fsm_status = READY;
        if (i_fault) begin
          next_state = FAULT;
        end else if (!i_enable || i_ack) begin
          next_state = READY;
        end
      end
      FAULT: begin
        o_fsm_status = FAULT;
        if (i_clear && !i_fault) begin
          next_state = IDLE;
        end else begin
          next_state = FAULT;
        end
      end
    endcase
  end
  
  // Output logic
  always @ (posedge i_clk, negedge i_rst_n) begin
    if (!i_rst_n) begin
      o_ready <= 0;
    end else if (state == PROCESS && !i_fault) begin
      // Concatenate input vectors into a single bus
      reg [31:0] concatenated_bus;
      integer i;
      for (i = 0; i < 6; i = i + 1) begin
        concatenated_bus[5*i+4 : 5*i] = i_vector_{i};
        concatenated_bus[31-i] = 1'b1;
      end
      
      // Split the bus into output vectors
      for (i = 0; i < 4; i = i + 1) begin
        if (i == 0) begin
          o_vector_{i} <= concatenated_bus[31:24];
        end else if (i == 1) begin
          o_vector_{i} <= concatenated_bus[23:16];
        end else if (i == 2) begin
          o_vector_{i} <= concatenated_bus[15:8];
        end else if (i == 3) begin
          o_vector_{i} <= concatenated_bus[7:0];
        end
      end
      
      // Set ready flag
      o_ready <= 1;
    end else if (!i_enable || i_fault) begin
      o_ready <= 0;
    end else begin
      o_ready <= 0;
    end
    o_error <= (i_fault && state != FAULT);
    o_vector_1 <= 0;
    o_vector_2 <= 0;
    o_vector_3 <= 0;
    o_vector_4 <= 0;
    if (state == PROCESS && !i_fault) begin
      // Output logic for PROCESS state
      o_vector_1 <= concatenated_bus[31:24];
      o_vector_2 <= concatenated_bus[23:16];
      o_vector_3 <= concatenated_bus[15:8];
      o_vector_4 <= concatenated_bus[7:0];
    end
  end
  
endmodule