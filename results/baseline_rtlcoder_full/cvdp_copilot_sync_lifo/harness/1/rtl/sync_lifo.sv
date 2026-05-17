Module sync_lifo (
   input clock,
   input reset,
   input write_en,
   input read_en,
   input [DATA_WIDTH-1:0] data_in,
   output reg empty,
   output reg full,
   output reg [DATA_WIDTH-1:0] data_out
);

   parameter DATA_WIDTH = 8;
   parameter ADDR_WIDTH = 3;

   reg [DATA_WIDTH-1:0] mem [(2**ADDR_WIDTH)-1:0]; // memory array with size = 2^ADDR_WIDTH
   reg [ADDR_WIDTH-1:0] ptr = 'd0; //ptr is used to store data that need to be pushed up or popped down on the LIFO.

   // write operation
   always @(posedge clock) begin
     if (reset) begin
         mem = 'b0;
         ptr <= 0;
         empty <= 1'b1;
         full <= 1'b0;
      end else if (!full && write_en) begin
          mem[ptr] <= data_in; // simply push it up or pop down according to whether the control signal is asserted
          ptr <= ptr + 1;
          full <= (ptr == 2**ADDR_WIDTH) ? 1'b1 : 1'b0;
      end
      empty <= ~full;
   end

   // read operation
   always @(posedge clock) begin
     if (reset) begin
         data_out <= 'b0;
         ptr <= 0;
     end else if (!empty && read_en) begin
         data_out <= mem[ptr]; // simply pop it down or push it up according to whether the control signal is asserted.
         ptr <= ptr - 1;
         empty <= (ptr == 0) ? 1'b1 : 1'b0;
     end else begin
        data_out = #1 data_out;
     end
   end
endmodule