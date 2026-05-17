```SystemVerilog
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

  reg [31:0] s_data_reg;
  wire m0_ready, m1_ready;

  assign m0_ready = s_read && !m1_ready;
  assign m1_ready = s_read && !m0_ready;

  always @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
      s_data_reg <= 32'b0;
      m0_ready <= 1'b0;
      m1_ready <= 1'b0;
    end else begin
      if(AFINITY == 0) begin
        m0_ready <= 1'b0;
        m1_ready <= (m1_valid && !s_read);
      end else begin
        m0_ready <= (m0_valid && !s_read);
        m1_ready <= 1'b0;
      end
    end
  end

  assign s_data = s_data_reg;
  assign s_valid = (m0_valid || m1_valid) && s_read;

  always @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
      s_data_reg <= 32'b0;
    end else if((m0_valid && m0_ready) || (m1_valid && m1_ready)) begin
      s_data_reg <= (m0_valid && m0_ready) ? m0_data : m1_data;
    end
  end

endmodule