module gate_target (
    input  logic [1:0] gate_select,
    input  logic [3:0] a,
    input  logic [3:0] b,
    output logic [3:0] target
);

    always_comb begin
        case (gate_select)
            2'b00: // AND gate
                target = (a == 4'b0001 && b == 4'b0001) ? 4'b0001 : 4'b1111;
            2'b01: // OR gate
                target = (a == 4'b0001 || b == 4'b0001) ? 4'b0001 : 4'b1111;
            2'b10: // NAND gate
                target = (a != 4'b0001 || b != 4'b0001) ? 4'b0001 : 4'b1111;
            2'b11: // NOR gate
                target = (a != 4'b0001 && b != 4'b0001) ? 4'b0001 : 4'b1111;
            default:
                target = 4'b1111;
        endcase
    end

endmodule

module hebb_gates (
    input  logic        clk,
    input  logic        rst,
    input  logic        start,
    input  logic signed [3:0] a,
    input  logic signed [3:0] b,
    input  logic [1:0]  gate_select,
    output logic signed [3:0] w1,
    output logic signed [3:0] w2,
    output logic signed [3:0] bias,
    output logic [3:0]  present_state,
    output logic [3:0]  next_state
);

    // State parameters
    localparam [3:0] State_0  = 4'd0;
    localparam [3:0] State_1  = 4'd1;
    localparam [3:0] State_2  = 4'd2;
    localparam [3:0] State_3  = 4'd3;
    localparam [3:0] State_4  = 4'd4;
    localparam [3:0] State_5  = 4'd5;
    localparam [3:0] State_6  = 4'd6;
    localparam [3:0] State_7  = 4'd7;
    localparam [3:0] State_8  = 4'd8;
    localparam [3:0] State_9  = 4'd9;
    localparam [3:0] State_10 = 4'd10;

    // Internal registers
    logic signed [3:0] x1, x2;
    logic signed [3:0] target;
    logic signed [3:0] delta_w1, delta_w2, delta_b;
    logic [3:0] iter;

    // Gate target instantiation
    gate_target gt_inst (
        .gate_select(gate_select),
        .a(x1),
        .b(x2),
        .target(target)
    );

    // Sequential block
    always_ff @(posedge clk or negedge rst) begin
        if (!rst) begin
            present_state <= State_0;
            iter          <= 4'd0;
            w1            <= 4'd0;
            w2            <= 4'd0;
            bias          <= 4'd0;
            x1            <= 4'd0;
            x2            <= 4'd0;
            delta_w1      <= 4'd0;
            delta_w2      <= 4'd0;
            delta_b       <= 4'd0;
        end else begin
            present_state <= next_state;
            case (present_state)
                State_1: begin
                    x1 <= a;
                    x2 <= b;
                end
                State_7: begin
                    delta_w1 <= x1 * target;
                    delta_w2 <= x2 * target;
                    delta_b  <= target;
                end
                State_8: begin
                    w1   <= w1   + delta_w1;
                    w2   <= w2   + delta_w2;
                    bias <= bias + delta_b;
                end
                State_9: begin
                    if (iter < 4'd3)
                        iter <= iter + 4'd1;
                    else
                        iter <= 4'd0;
                end
                default: begin end
            endcase
        end
    end

    // Combinational next-state block
    always_comb begin
        next_state = present_state;
        case (present_state)
            State_0: begin
                if (start)
                    next_state = State_1;
                else
                    next_state = State_0;
            end
            State_1: next_state = State_7;
            State_2: next_state = State_3;
            State_3: next_state = State_4;
            State_4: next_state = State_5;
            State_5: next_state = State_6;
            State_6: next_state = State_7;
            State_7: next_state = State_8;
            State_8: next_state = State_9;
            State_9: begin
                if (iter < 4'd3)
                    next_state = State_1;
                else
                    next_state = State_0;
            end
            State_10: next_state = State_0;
            default:  next_state = State_0;
        endcase
    end

endmodule
