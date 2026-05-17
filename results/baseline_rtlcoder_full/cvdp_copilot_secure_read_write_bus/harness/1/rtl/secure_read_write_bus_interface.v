<s> module secure_read_write_bus_interface #
    (
        parameter integer p_configurable_key = 8'hAA,
        parameter integer p_data_width = 8,
        parameter integer p_addr_width = 8
    )
    (
        input [p_addr_width-1:0] i_addr,
        input [p_data_width-1:0] i_data_in,
        input [7:0] i_key_in,
        input i_read_write_enable,
        input i_capture_pulse,
        input i_reset_bar,
        output reg [p_data_width-1:0] o_data_out,
        output reg o_error
    );

  always @(posedge i_capture_pulse or negedge i_reset_bar) begin
      if (~i_reset_bar) begin
          o_data_out <= 0;
          o_error <= 1'b0;
      end else begin
          if (i_read_write_enable == 1 && i_key_in == p_configurable_key) begin
              o_data_out <= #1 data_mem[i_addr];
              o_error <= 1'b0;
          end else begin
              o_data_out <= 0;
              o_error <= 1'b1;
          end
      end
  end

endmodule