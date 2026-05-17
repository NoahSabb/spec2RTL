<s> module hamming_code_receiver(
    input [7:0] data_in,
    output reg [3:0] data_out
);

wire [2:0] c;
assign c[0] = ^data_in[1]^data_in[3]^data_in[5]^data_in[7];
assign c[1] = ^data_in[2]^data_in[3]^data_in[6]^data_in[7];
assign c[2] = ^data_in[4]^data_in[5]^data_in[6]^data_in[7];

always @* begin
    if (c != 3'b000) begin
        casez(c)
            3'b001: data_out <= {3'bxxx, ~data_in[1], data_in[2:0]};
            3'b010: data_out <= {3'bxxxx, data_in[6:4]} ^~^ data_in[7];
            3'b011: data_out <= {3'bxxxx, ~data_in[2], ~data_in[3]};
            3'b100: data_out <= {3'bxxxx, ~data_in[4], ~data_in[5]};
            default: data_out <= {3'bxxxxx, 3'bzzz, 3'bzzz}; // Invalid error pattern
        endcase
    end else begin
        data_out <= data_in[7:4];
    end
end

endmodule