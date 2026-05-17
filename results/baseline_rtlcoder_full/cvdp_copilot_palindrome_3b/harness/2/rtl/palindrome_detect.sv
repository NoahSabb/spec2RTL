<s> module PalindromeDetect (
    input clk,
    input reset,
    input bit_stream,
    output reg palindrome_detected
);
  parameter N = 3; //determine the length of the palindrome
  
  reg [N-1:0] shift_reg; //buffer to store last N bits
  
  always @ (posedge clk) begin
    if(reset) begin
      shift_reg <= 0;
      palindrome_detected <= 0;
    end else begin
      shift_reg <= {shift_reg[N-2:0], bit_stream}; //shift the last N-1 bits and add the current bit
      if(shift_reg == {shift_reg[N-1], shift_reg[N-1:0]}) begin //check if the last N bits are equal to its reverse
        palindrome_detected <= 1;
      end else begin
        palindrome_detected <= 0;
      end
    end
  end
endmodule