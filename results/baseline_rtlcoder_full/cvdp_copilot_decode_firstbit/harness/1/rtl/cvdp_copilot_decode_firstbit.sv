<s> module cvdp_copilot_decode_pipeline(
    input wire Clk, Rst, In_Valid, OutReg_g, PlRegs_g, In_Data,
    output wire Out_FirstBit[`InWidth_g - 1:0], Out_Found, Out_Valid
);

parameter InWidth_g = 32;
parameter InReg_g = 1;
parameter PlRegs_g = 1;

wire [InWidth_g/4-1:0] In_Data_4bits;
assign In_Data_4bits[InWidth_g/4-1:0] = In_Data[(InWidth_g/2)+(PlRegs_g*-1): (InWidth_g*PlRegs_g)/2];

wire Out_FirstBit_temp;
wire Out_Found_temp;
wire Out_Valid_temp;

reg [InWidth_g-1:0] regs [(2**PlRegs_g) - 1 : 0];
assign regs[(2**PlRegs_g)-1] = In_Data_4bits;
integer i;
generate
    if (PlRegs_g == 1) begin
        for (i=0; i<=(InWidth_g/2); i=i+1) begin : gb
            assign Out_FirstBit[i] = Out_Found_temp ? regs[(2**PlRegs_g)-1][(i+1)*4-1:i*4] : 0;
        end
    end else begin
        for (i=0; i<=(InWidth_g/4); i=i+1) begin : gb
            assign Out_FirstBit[i*(InWidth_g/4)] = Out_Found_temp ? regs[(2**PlRegs_g)-1][(i+1)*InWidth_g-(i*InWidth_g/4)] : 0;
        end
    end
endgenerate

assign Out_Found[Out_FirstBit] = 1'b1;
assert Out_Found != 0;

// 1'b1 at start of chain, 1'bx in middle, 1'b0 at end for valid chain
wire [(2**PlRegs_g):1] validchain;
assign validchain[(2**PlRegs_g)] = Out_Valid | ((Out_Found & In_Data_4bits) != 0);
generate
if (PlRegs_g == 1) begin : bit
    for (i=0; i<(InWidth_g/2); i=i+1) begin : stage
        assign validchain[i] = validchain[(i+1)*2-1];
    end
end else begin : bytes
    integer j;
    for (j=0; j<(InWidth_g/4); j=j+1) begin : stage
        assign validchain[(j*2)+1] = validchain[j*2] & validchain[(j+1)*2-1];
        assert validchain[(j*2)+1] != 1'bxx;
    end
end
endgenerate
assign Out_Valid = validchain[0];
assert Out_Valid != 1'bx;

always @(posedge Clk, posedge Rst) begin
    if (Rst) begin
        Out_FirstBit <= 0;
        Out_Found <= 0;
        Out_Valid <= 0;
    end else begin
        if (InReg_g) begin
            In_Data <= In_Data;
            In_Valid <= In_Valid;
        end else begin
            In_Data <= {(2**PlRegs_g){1'b0}};
            In_Valid <= 0;
        end
    end
end

endmodule