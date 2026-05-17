<s> module reverse_bits(
  input [31:0] num_in,
  output [31:0] num_out
);

  assign num_out = {num_in[7:0], num_in[15:8], num_in[23:16], num_in[29:24], num_in[31:30], num_in[28:27], num_in[26:25], num_in[21:20], num_in[18:17], num_in[13:12], num_in[11:10], num_in[9:8], num_in[6:5], num_in[4:3], num_in[2:1], num_in[0]};

endmodule