module gate_target (
    input  logic [1:0] gate_select,
    input  logic signed [3:0] a,
    input  logic signed [3:0] b,
    output logic signed [3:0] target
);
    always_comb begin
        case (gate_select)
            2'b00: target = (a == 4'sb0001 && b == 4'sb0001) ? 4'sb0001 : 4'sb1111;
            2'b01: target = (a == 4'sb0001 || b == 4'sb0001) ? 4'sb0001 : 4'sb1111;
            2'b10: target = (a != 4'sb0001 || b != 4'sb0001) ? 4'sb0001 : 4'sb1111;
            2'b11: target = (a != 4'sb0001 && b != 4'sb0001) ? 4'sb0001 : 4'sb1111;
            default: target = 4'sb1111;
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

    parameter State_0  = 4'd0;
    parameter State_1  = 4'd1;
    parameter State_2  = 4'd2;
    parameter State_3  = 4'd3;
    parameter State_4  = 4'd4;
    parameter State_5  = 4'd5;
    parameter State_6  = 4'd6;
    parameter State_7  = 4'd7;
    parameter State_8  = 4'd8;
    parameter State_9  = 4'd9;
    parameter State_10 = 4'd10;

    logic signed [3:0] x1, x2;
    logic signed [3:0] target_out;
    logic signed [3:0] w1_next, w2_next, bias_next;
    logic signed [3:0] x1_next, x2_next;
    logic training_done;

    gate_target gt_inst (
        .gate_select(gate_select),
        .a(x1),
        .b(x2),
        .target(target_out)
    );

    // Sequential block
    always_ff @(posedge clk or negedge rst) begin
        if (!rst) begin
            present_state <= State_0;
            w1            <= 4'sb0000;
            w2            <= 4'sb0000;
            bias          <= 4'sb0000;
            x1            <= 4'sb0000;
            x2            <= 4'sb0000;
            training_done <= 1'b0;
        end else begin
            present_state <= next_state;
            w1            <= w1_next;
            w2            <= w2_next;
            bias          <= bias_next;
            x1            <= x1_next;
            x2            <= x2_next;

            if (present_state == State_10) begin
                training_done <= 1'b1;
            end else if (present_state == State_0 && start && !training_done) begin
                training_done <= 1'b0;
            end else if (present_state == State_1) begin
                training_done <= 1'b0;
            end else if (present_state == State_0 && !start) begin
                training_done <= 1'b0;
            end
        end
    end

    // Combinational next-state and output logic
    always_comb begin
        // Defaults
        next_state = present_state;
        w1_next    = w1;
        w2_next    = w2;
        bias_next  = bias;
        x1_next    = x1;
        x2_next    = x2;

        case (present_state)
            State_0: begin
                if (start && !training_done) begin
                    next_state = State_1;
                end else begin
                    next_state = State_0;
                end
            end

            State_1: begin
                // Capture inputs into x1, x2
                x1_next    = a;
                x2_next    = b;
                next_state = State_2;
            end

            State_2: begin
                next_state = State_7;
            end

            State_3: begin
                next_state = State_7;
            end

            State_4: begin
                next_state = State_7;
            end

            State_5: begin
                next_state = State_7;
            end

            State_6: begin
                next_state = State_7;
            end

            State_7: begin
                // Compute deltas and update weights/bias directly
                w1_next    = w1 + (x1 * target_out);
                w2_next    = w2 + (x2 * target_out);
                bias_next  = bias + target_out;
                next_state = State_8;
            end

            State_8: begin
                next_state = State_9;
            end

            State_9: begin
                next_state = State_10;
            end

            State_10: begin
                next_state = State_0;
            end

            default: begin
                next_state = State_0;
            end
        endcase
    end

endmodule
