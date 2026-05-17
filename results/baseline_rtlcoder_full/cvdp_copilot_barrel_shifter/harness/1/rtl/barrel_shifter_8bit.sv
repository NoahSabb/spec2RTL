Generate it and submit!
module barrel_shifter_8bit(input [7:0] data_in, input [2:0] shift_bits, input left_right, output [7:0] data_out);
    assign data_out = left_right ? (data_in << shift_bits) : (data_in >> shift_bits);
endmodule