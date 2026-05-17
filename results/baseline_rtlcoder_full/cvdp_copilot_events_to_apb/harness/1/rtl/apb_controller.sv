module apb_controller (
  input clk,
  input reset_n,
  input select_a_i,
  input select_b_i,
  input select_c_i,
  input [31:0] addr_a_i,
  input [31:0] data_a_i,
  input [31:0] addr_b_i,
  input [31:0] data_b_i,
  input [31:0] addr_c_i,
  input [31:0] data_c_i,
  output reg apb_psel_o,
  output reg apb_penable_o,
  output reg apb_pwrite_o,
  output reg [31:0] apb_paddr_o,
  output reg [31:0] apb_pwdata_o,
  input apb_pready_i
);

  // Internal signals
  reg [1:0] state;
  reg [31:0] timeout;
  
  always @(posedge clk, negedge reset_n) begin
    if (~reset_n) begin
      state <= 2'b00; // IDLE
      apb_psel_o <= 0;
      apb_penable_o <= 0;
      apb_pwrite_o <= 0;
      apb_paddr_o <= 0;
      apb_pwdata_o <= 0;
      timeout <= 4'b0; // Reset timeout counter.
    end else begin
      case (state)
        2'b00: // IDLE state
          if ({select_a_i, select_b_i, select_c_i} != 3'b0) begin
            if ({select_a_i, select_b_i, select_c_i} == 3'b10) begin
              // Only Event A is active
              apb_psel_o <= 1;
              apb_paddr_o <= addr_a_i;
              apb_pwdata_o <= data_a_i;
            end
            else if ({select_a_i, select_b_i, select_c_i} == 3'b01) begin
              // Only Event B is active
              apb_psel_o <= 1;
              apb_paddr_o <= addr_b_i;
              apb_pwdata_o <= data_b_i;
            end
            else if ({select_a_i, select_b_i, select_c_i} == 3'b00) begin
              // Only Event C is active
              apb_psel_o <= 1;
              apb_paddr_o <= addr_c_i;
              apb_pwdata_o <= data_c_i;
            end
            state <= 2'b01; // SETUP State
          end // if select signal asserted
        2'b01: // SETUP state
          begin
            apb_penable_o <= 1;
            state <= 2'b10; // ACCESS State
          end
        2'b10: // ACCESS State
          if (apb_pready_i) begin
            apb_psel_o <= 0;
            apb_penable_o <= 0;
            timeout <= 4'b0; // Reset timeout counter.
            if ({select_a_i, select_b_i, select_c_i} != 3'b0) begin
              state <= 2'b00; // IDLE State
            end
          end else if (timeout < 4'hF) begin
            timeout <= timeout + 1;
            apb_penable_o <= 1;
          end else begin
            apb_psel_o <= 0;
            apb_penable_o <= 0;
            state <= 2'b00; // IDLE State
          end // if (apb_pready_i || timeout == 4'hF)
        default: state <= 2'b00; // Default to IDLE.
      endcase
    end
  end
endmodule