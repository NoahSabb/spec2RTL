<s> module nbit_swizzling (
    input [DATA_WIDTH-1:0] data_in,
    input [1:0] sel,
    output reg [DATA_WIDTH-1:0] data_out
);

parameter DATA_WIDTH = 64;

always @(*) begin
    case (sel)
        2'b00: data_out = {data_in[DATA_WIDTH-1], data_in[DATA_WIDTH-2], ..., data_in[0]}; // reverse the entire input
        2'b01: begin // divide into two halves and reverse each half separately
            data_out = 
                {data_in[DATA_WIDTH-1:7], #(16 - DATA_WIDTH) data, data_in[DATA_WIDTH/2-1:0]} + {{8{(DATA_WIDTH % 2 == 1)}}, #(8 * (!(DATA_WIDTH mod 8))) 0};
        end
        2'b10: begin // divide into four equal sizes of bit arrays and reverse each section individually
            data_out = {data_in[3*7-7+DATA_WIDTH-1:3*5], #(16 - 4*8) 0, data_in[2*7-7+DATA_WIDTH-1:2*5]}; // first half
            data_out = {data_out, {2*8{(DATA_WIDTH mod 2 == 1)}} };
            data_out = {data_out, data_in[(3*4+7)-7+DATA_WIDTH-1:(3*4+5)]}; // second half
        end
        2'b11: begin // divide into eight parts and reverse the sections
            data_out = {{8{(DATA_WIDTH mod 8 == 0)}}};
            int i;
            for (i = DATA_WIDTH/8 - 1; i >= 0; --i)
                data_out = {data_out, #(8 * (!!(DATA_WIDTH % 8))) data_in[i*7+3]} + {{4{(DATA_WIDTH mod 2 == 1)}}};
        end
        default: data_out = {data_in, 0}; // do nothing
    endcase
end

endmodule