<s> module hebbian_rule
(
    input wire clk,
    input wire rst,
    input wire start,
    input signed [3:0] a, b,
    output reg signed [3:0] w1, w2, bias,
    output reg [3:0] present_state, next_state,
    output wire [1:0] gate_select
);

parameter State_0 = 4'b0000;
parameter State_1 = 4'b0001;
parameter State_2 = 4'b0010;
parameter State_3 = 4'b0011;
parameter State_6 = 4'b0110;
parameter State_7 = 4'b1000;
parameter State_8 = 4'b1010;
parameter State_9 = 4'b1011;
parameter State_10 = 4'b0000;

reg [3:0] present_state, next_state;
reg [3:0] x1, x2, t1;
reg [3:0] delta_w1, delta_w2, delta_b;

wire gate_0_select;
wire gate_1_select;

always @(posedge clk) begin
    if (rst == 1'b0) begin
        present_state <= State_0 ;
    end else if (start == 1'b1) begin
        present_state <= next_state ;
        next_state <= gate_select[1:0];
    end else begin
        present_state <= next_state ;
    end
     x1 <= a;
     x2 <= b;
     
     if (gate_select == 3'b00) // AND gate training
     begin
         t1 <= x1 & x2;
         delta_w1 <= x1 * t1;
         delta_w2 <= x2 * t1;
         delta_b <= t1;
         w1 <= w1 + delta_w1 ;
         w2 <= w2 + delta_w2 ;
         bias <= bias + delta_b ;
     end
     else if (gate_select == 3'b01) // OR gate training
     begin
         t1 <= x1 | x2;
         delta_w1 <= x1 * t1;
         delta_w2 <= x2 * t1;
         delta_b <= t1;
         w1 <= w1 + delta_w1 ;
         w2 <= w2 + delta_w2 ;
         bias <= bias + delta_b ;
     end
     else if (gate_select == 3'b10) // NAND gate training
     begin
         t1 = ~(x1 & x2);
         delta_w1 = x2 * t1;
         delta_w2 = x2 * t1;
         delta_b = -t1;
         w1 <= w1 + delta_w1 ;
         w2 <= w2 + delta_w2 ;
         bias <= bias + delta_b ;
     end
     else if (gate_select == 3'b11) // NOR gate training
     begin
         t1 = ~(x1 | x2);
         delta_w1 = -dx * t1;
         delta_w2 = -dy * t1;
         delta_b = ~t1;
         w1 <= w1 + delta_w1 ;
         w2 <= w2 + delta_w2 ;
         bias <= bias + delta_b ;
     end
end

endmodule