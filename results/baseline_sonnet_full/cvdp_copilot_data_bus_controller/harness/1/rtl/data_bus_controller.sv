module data_bus_controller #(
  parameter AFINITY = 0
  )(
  input         clk      ,
  input         rst_n    ,

  output        m0_read  ,
  input         m0_valid ,
  input [31:0]  m0_data  ,

  output        m1_read  ,
  input         m1_valid ,
  input [31:0]  m1_data  ,

  input         s_read   ,
  output        s_valid  ,
  output [31:0] s_data 
);

  // Internal registered outputs
  reg        s_valid_reg;
  reg [31:0] s_data_reg;

  // Combinational logic to determine which master wins
  // and drive slave outputs
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      s_valid_reg <= 1'b0;
      s_data_reg  <= 32'd0;
    end else begin
      // Both masters valid at the same cycle - use AFINITY
      if (m0_valid && m1_valid) begin
        if (AFINITY == 0) begin
          // m0 wins
          if (s_read) begin
            s_valid_reg <= 1'b1;
            s_data_reg  <= m0_data;
          end else begin
            s_valid_reg <= 1'b0;
            s_data_reg  <= 32'd0;
          end
        end else begin
          // m1 wins
          if (s_read) begin
            s_valid_reg <= 1'b1;
            s_data_reg  <= m1_data;
          end else begin
            s_valid_reg <= 1'b0;
            s_data_reg  <= 32'd0;
          end
        end
      end
      // Only m0 valid
      else if (m0_valid && !m1_valid) begin
        if (s_read) begin
          s_valid_reg <= 1'b1;
          s_data_reg  <= m0_data;
        end else begin
          s_valid_reg <= 1'b0;
          s_data_reg  <= 32'd0;
        end
      end
      // Only m1 valid
      else if (!m0_valid && m1_valid) begin
        if (s_read) begin
          s_valid_reg <= 1'b1;
          s_data_reg  <= m1_data;
        end else begin
          s_valid_reg <= 1'b0;
          s_data_reg  <= 32'd0;
        end
      end
      // Neither valid
      else begin
        s_valid_reg <= 1'b0;
        s_data_reg  <= 32'd0;
      end
    end
  end

  // Slave outputs
  assign s_valid = s_valid_reg;
  assign s_data  = s_data_reg;

  // Master ready signals depend on slave ready
  // m0 is ready when slave is ready and m0 is the selected master (or only master)
  // m1 is ready when slave is ready and m1 is the selected master (or only master)
  assign m0_read = s_read && (
                    (m0_valid && !m1_valid) ||
                    (m0_valid &&  m1_valid && (AFINITY == 0))
                  );

  assign m1_read = s_read && (
                    (!m0_valid && m1_valid) ||
                    ( m0_valid && m1_valid && (AFINITY == 1))
                  );

endmodule
