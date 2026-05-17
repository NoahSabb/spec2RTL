<s> module unpack_one_hot(
    input sign,
    input size,
    input [2:0] one_hot_selector,
    input [255:0] source_reg,
    output [511:0] destination_reg
);

integer i;

always @(*) begin
  case (one_hot_selector)
    3'b001 : for (i = 0; i < 256; i = i + 8) begin
                if (sign)
                  destination_reg[i/8:i+7] <= $signed(source_reg[i    :i+7]);
                else
                  destination_reg[i/8:i+7] <= source_reg[i    :i+7];
             end
    3'b010 : for (i = 0; i < 256; i = i + 4) begin
                if (sign)
                  destination_reg[(i/8)*8 +: 8] <= $signed(source_reg[i*2-1:i*2+1]);
                else
                  destination_reg[(i/8)*8 +: 8] <= source_reg[i*2-1:i*2+1];
             end
    3'b100 : if (size) begin
                for (i = 0; i < 64; i = i + 8) begin
                  if (sign)
                    destination_reg[i/8:i+7] <= $signed(source_reg[i   :i+15]);
                  else
                    destination_reg[i/8:i+7] <= source_reg[i   :i+15];
                end
              end
              else begin
                for (i = 0; i < 256; i = i + 4) begin
                  if (sign)
                    destination_reg[(i/8)*8 +: 8] <= $signed(source_reg[i*2-1:i*2+1]);
                  else
                    destination_reg[(i/8)*8 +: 8] <= source_reg[i*2-1:i*2+1];
                end
              end
     default : destination_reg <= source_reg;
  endcase
end

endmodule