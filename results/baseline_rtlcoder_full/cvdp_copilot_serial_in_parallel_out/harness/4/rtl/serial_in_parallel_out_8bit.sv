```
 module serial_in_parallel_out_8bit (
   input wire clock,
   input wire serial_in,
   output reg [7:0] parallel_out
 );

  always @(posedge clock) begin
    // Shift left by one and insert new LSB
    parallel_out <= {parallel_out[6:0], serial_in};
  end

endmodule