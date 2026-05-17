Do not include module definition statement (module glitch_free_mux( 
      input clk1,
      input clk2,
      input sel,
      input rst_n,
      output reg clkout)) in your response.

 module glitch_free_mux( 
   input clk1,
   input clk2,
   input sel,
   input rst_n,
   output reg clkout);

   reg [1:0] clk_sel;
   assign clk_sel = {sel, ~sel};
   
   always @(posedge clk1 or posedge clk2) begin
      if (~rst_n)
        clkout <= 0;
      else if (clk_sel == 2'b01 && ~clkout) begin
         clkout <= sel ? clk2 : clk1;
      end
      else if (clk_sel == 2'b10 && ~clkout) begin
         clkout <= sel ? ~clk2 : sel ? clk1 : clkout;
      end
   end
   
endmodule