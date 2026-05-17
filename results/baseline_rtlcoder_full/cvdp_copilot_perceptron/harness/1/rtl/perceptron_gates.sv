module gate_target (
    input [1:0] gate_select,
    output reg o_1,
    output reg o_2,
    output reg o_3,
    output reg o_4
);

   always @ (gate_select) begin
      case(gate_select)
         2'd0 : begin // AND GATE
                  o_1 = {4'd1, -4'd1, -4'd1};
                  o_2 = {4'd1, 4'd1, 4'd1};
      end
         2'd1 : begin // OR GATE
                  o_1 = {-4'd1, 4'd1, 4'd1, 4'd1};
      end
         2'd2 : begin // NAND GATE
                  o_1 = {4'd1, 4'd1, 4'd1, -4'd1};
      end
         2'd3 : begin // NOR GATE
                  o_1 = {-4'd1, -4'd1, -4'd1,-4'd1};
      end
         default: begin
                    o_1 = 0;
                end
      endcase
   end
endmodule

module perceptron_gates (
    input clk,
    input rst_n,
    input [3:0] x1,
    input [3:0] x2,
    input signed [3:0] threshold,
    input learning_rate,
    output reg signed [3:0] percep_w1,
    output reg signed [3:0] percep_w2,
    output reg signed [3:0] percep_bias,
    output reg [3:0] present_addr,
    output reg stop,
    output reg [2:0] input_index,
    output reg [3:0] y_in,
    output reg [3:0] y
);

parameter INITIALIZED = 4'b1001;
parameter MICROCODE_SIZE = 5'd6;

reg [MICROCODE_SIZE-1:0] microcode;
reg [2:0] gate_target;
wire [3:0] o1,o2,o3,o4;
wire signed [7:0] yt;
wire signed [7:0] yyt;
wire signed [7:0] yn;
wire signed [3:0] wt1_upd, wt2_upd, bias_upd;
wire signed [3:0] percep_w1_update, percep_w2_update, percep_bias_update;
reg [4'b31:0] counter;
reg [MICROCODE_SIZE-1:0] next_microcode;
reg stop_tmp, rst_n_r;
wire done, start;

assign y = yyt[7:0];
assign y_in = {4'b0, yt[7:3]};

assign o1 = gate_target[0] ? o1 : 4'd1;
assign o2 = gate_target[1] ? o2 : 4'b0;
assign o3 = gate_target[2] ? o3 : 4'b0;
assign o4 = gate_target[3] ? o4 : 4'b0;

assign gate_target = {x2[3], x1};

wire xor_y = |yt[7:6]; // y is a treshold crossed???

gate_target inst(.gate_select(gate_target), .o_1(o1),  .o_2(o2));
gate_target inst2(.gate_select(gate_target), .o_3(o3), .o_4(o4));

assign yyt = {xor_y, 3'b0, threshold[7:6], threshold};
assign yn = yt + {5'd0, o1, o2, o3}*learning_rate;

micrcode inst (
    .clk(clk),
    .rst_n(rst_n_r),
    .present_addr(present_addr),
    .next_microcode(next_microcode),
    .counter(counter),
    .start(start),
    .done(done) // Done is low when micro-op is done.
);

always @ (posedge clk) begin
    rst_n_r <= rst_n;
    if (!rst_n)
        present_addr <= 0;
    start <= present_addr == next_microcode;
end

always @ (*) begin
    case(present_addr[2:1])
        2'd0 : counter = INITIALIZED;
        2'b10, 2'b11 : counter = 3'd7;
        default : counter = 3'd5;
    endcase
end

always @ (*) begin
    case(present_addr[1:0])
        2'b0x : microcode = percep_w1_update | (percep_bias_update ? {1'b1, 4'b0} : {5'd0} )<<3; // wt1 upd, bias update
        2'b1x : begin
              if(percep_bias_update)
                  microcode = (learning_rate > 0 ? percep_bias_update : {5'd0})<<3 | wt2_upd|(learning_rate > 0 ? 1'b1 : 1'b0); // bias update, wt2 upd
                                                                                                                else
                 microcode = percep_w2_update <<3 ;// wt2 update, only if percep_bias_update is not set...
           end
        2'b13 : microcode = (learning_rate > 0 ? percep_w1_update : {5'd0})<<2; // Wt, only if y[7] is xor.
                                                                                            // Note : bias upd & wt2 upd was tested but fails !!!
        2'b14 : microcode = (learning_rate > 0 ? percep_w1_update : {5'd0})<<3 ; // Wt, only if y[7:6] is 2'b0x
                                                                            // Note : bias upd & wt1_upd was tested but fails !!!
        2'b15 : microcode = (learning_rate > 0 ? percep_w1_update : {5'd0})<<4 ; // Wit, only if y[7:6] is 2'b1x (so xor_y was 0)
                                                                             // Note : bias upd & wt1_upd was tested but fails !!!
        2'b16 : microcode = {6{learning_rate}};// Initial, Only when perceptron got fully trained...
        default : microcode = ~128 ? {3'd0, y[7], -1} : 4'bx; // 4'b? to mark op as done.
    endcase
end

assign done = next_microcode == present_addr && present_addr != microcode;
assign percep_w1_update = (microcode[3:0] == present_addr[2:0]) ? (5'd0) : ((present_addr[2:1] == 2'b0x) ? {4'b1, o1, -o1} : {4'b1, 4'b0}) <<3;
assign percep_w2_update = (microcode[7:4] == present_addr[2:0]) ? (~4'd0) : ((present_addr[2:1] == 2'b1x || present_addr[2:1] == 2'b13) ? {4'b1, xor_y, ~xor_y} << 3 : (microcode[7:4][0] ? (present_addr[2:1] == 2'b0x ? {3'd0, o2} : {{~o3}, o2}) : o3) <<3 });
module percep_bias_upd (
    input clk,
    input rst_n,
    output reg signed [1:0] stopped
);
    assign yt = {percep_w1, percep_w2};
    sub_module inst(.clk(clk), .rst_n(rst_n), .yt(yt), .yn(y), .threshold(threshold));
    always @ (posedge clk) begin
        if (!rst_n)
            percep_bias <= 4'd1;
        else if (!(~|present_addr)) // Perceptron got fully trained, Stop.
            percep_bias <= 4'd0;    
    end
endmodule

module sub_module (
    input clk, 
    input rst_n, 
    output reg signed [7:0] yt, 
    output reg signed [7:0] y, 
    input signed [7:0] threshold
);
    always @ (posedge clk) begin
        if (!rst_n) begin
            yt <= 8'b1111_1111; // Initial state. Percepton will not be trained...
        end
        else if ({xor_y, o1} > {xor_y, threshold})
            yt <= 8'b1111_1110; // First layer of gates
    end
endmodule