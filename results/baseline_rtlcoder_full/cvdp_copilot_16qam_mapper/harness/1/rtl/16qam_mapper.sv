<s> module qam16_mapper_interpolated(
    input [N*IN_WIDTH-1:0] bits,
    output [(N+N/2)*OUT_WIDTH-1:0] I,
    output [(N+N/2)*OUT_WIDTH-1:0] Q
);

parameter N = 4; // Number of input symbols (fixed at 8 for QAM8 but needs to be a multiple of 2)
parameter IN_WIDTH = 4; // Width of each input bit (fixed at 4 for QAM16)
parameter OUT_WIDTH = 3; // Width of the output components (also fixed at 3 for signed integers since the mapping only involves a set of four distinct values)

wire [IN_WIDTH-1:0] i_msb;
wire [IN_WIDTH-1:0] q_msb;
wire [IN_WIDTH-1:0] i_lsb;
wire [IN_WIDTH-1:0] q_lsb;

assign {i_msb, q_msb, i_lsb, q_lsb} = bits[N + $clog2(N):0]; // Extract input symbols
assign I[(N/2):0] = (i_msb[1:0])*2 - 1; // Map MSBs to I
assign Q[(N/2):0] = (q_lsb[1:0])*2 - 1; // Map LSBs to Q

wire [OUT_WIDTH-1:0] i_ip;
wire [OUT_WIDTH-1:0] q_ip;

integer index = 1; // Counter for interpolated values
assign I[(N+N/2)] = i_msb + i_lsb; // First mapped symbol goes alone
assign Q[(N+N/2)] = q_msb + q_lsb; // Add first two input symbols

// Compute interpolation for remaining output values. Output pattern is:
// (mapped1, interpolated1, mapped2)
// where we always keep the MSB and LSB from each symbol to avoid bias

always @*
begin
    // Interpolate between adjacent input symbols
    if(N >= 6) begin
        assign i_ip = I[(N+N/2)] + (i_msb + q_lsb - {I[(N+N/2)*4+index], Q[(N+N/2)*4+index]});
        index <= index + 1;
           
        if(index <= N-3) begin
            assign q_ip = I[(N+N/2)] + (i_msb + q_lsb - {I[(N+N/2)*4+index], Q[(N+N/2)*4+index]});
            index <= index + 1;
        end
    else if(N == 4) begin
        assign i_ip = I[(N+N/2)] + (i_msb - q_lsb);
        
        if($signed(i_ip[OUT_WIDTH-1]) < $signed(i_msb[IN_WIDTH-1])) begin
            assign Q[(N+N/2)] = (q_msb >= 0) ? 2 : -2; // Assign the maximal interpolated value
        end
        
        index <= N;
    end
         
end

assign I[(N+N/2)*4-1:(N+N/2)] = i_ip;
assign Q[(N+N/2)*4-1:(N+N/2)] = q_ip;

endmodule