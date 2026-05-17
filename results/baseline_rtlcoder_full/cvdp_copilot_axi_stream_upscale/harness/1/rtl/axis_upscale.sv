module axis_upscaler(clocks, input_clk_en, input_dff, output_clk_en, output_rdata);
  input clocks;
  input input_clk_en;
  input input_dff;
  output output_clk_en;
  outreg [31:0] output_rdata[0:2];
  reg [31:0] qc[0:7][1:0];
  parameter [7:5] AXI_STATUS = 8'h100;
  parameter CLK_ENA = 1'b0;
  parameter DFFENA = 1'b1;
  localparam RSTN = 1'b0;
  
  always @ (posedge clocks or negedge RSTN) begin
      if (!RSTN) begin
          output_rdata <= 'bz;
          qc[0] <= 32'h0;
      end
      else if(input_clk_en) begin
          output_rdata[1:0] <= {qc[1][1], qc[1][0]};
          output_rdata[2:0] <= {qc[7][1], qc[7][0], qc[6][1]};    // AXI-ID [4:3]

       // generate q = {p, d(p)...d(p)} sequence
          if (input_dff) begin
              qc[0] <= output_rdata;
              qc[6] <= qc[8];            // dff[0]: rdata
              qc[7][1:0] <= qc[6][31:0]; // copy MSB into AXI-ID [4:3]
              qc[1][1:0] <= {qc[2][30:0], qc[0][31]};  // inverted AXI-ID[30:0] = AXI-ID[30:0]
          end            
      end
  end
  
  assign output_clk_en = CLK_ENA;
endmodule