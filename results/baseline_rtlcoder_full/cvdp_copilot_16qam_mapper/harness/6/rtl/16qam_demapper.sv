<s> module qam16_demapper_interpolated(
    input [(N + N/2)*IN_WIDTH - 1 : 0] I,
    input [(N + N/2)*IN_WIDTH - 1 : 0] Q,
    output reg [N*OUT_WIDTH-1:0] bits,
    output reg error_flag
);

parameter N = 4; // Number of original input symbols (≥ 2 and a multiple of 2)
parameter OUT_WIDTH = 4; // Bit width of each output symbol (fixed at 4)
parameter IN_WIDTH = 3; // Bit width of I/Q components (fixed at 3)

// Internal signals
wire [IN_WIDTH + 1:0] ihat;
wire [IN_WIDTH + 1:0] qhat;
wire [IN_WIDTH + 1:0] idiff;
wire [IN_WIDTH + 1:0] qdiff;
reg [OUT_WIDTH-1:0] b_i_s[15:0]; // b_i for each input symbol
reg [OUT_WIDTH-1:0] b_q_s[15:0]; // b_q for each input symbol

// I-component interpolation
assign ihat = (I[2*i+1]+I[2*(i+1)])>>1;
assign idiff = ihat - I[2*i+1] - I[2*(i+1)];
foreach (integer i, j in r_range(0, N/2)) begin
    if (idiff >> IN_WIDTH == 1'b1) begin
        b_i_s[{i}] <= 4'bx; // set error flag
        error_flag <= 1;
    end else begin
        b_i_s[{i}] <= I[2*i+1:IN_WIDTH] << (2-OUT_WIDTH);
    end
end

// Q-component interpolation
assign qhat = (Q[2*j+1]+Q[2*(j+1)])>>1;
assign qdiff = qhat - Q[2*j+1] - Q[2*(j+1)];
foreach (integer i, j in r_range(0, N/2)) begin
    if (qdiff >> IN_WIDTH == 1'b1) begin
        b_q_s[{i}] <= 4'bx; // set error flag
        error_flag <= 1;
    end else begin
        b_q_s[{j}] <= Q[2*j+1:IN_WIDTH] << (2-OUT_WIDTH);
    end
end

// Output arrangement
always @ (i, j) begin
    bits[4*i +: OUT_WIDTH] = {b_i_s[i], b_q_s[i]} << 1; // MSBs come from I, LSBs from Q
end

// Error flag for interpolated values
always @ (idiff) begin
    if (abs(idiff >> IN_WIDTH) > ERROR_THRESHOLD) begin
        error_flag <= 1;
    end
end

endmodule