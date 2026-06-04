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

    localparam [3:0] S0 = 4'd0;
    localparam [3:0] S1 = 4'd1;
    localparam [3:0] S2 = 4'd2;

    logic signed [3:0] target_comb;
    logic signed [3:0] prev_a, prev_b;

    always_comb begin
        case (gate_select)
            2'b00: target_comb = (a == 4'sd1 && b == 4'sd1) ? 4'sd1 : -4'sd1;
            2'b01: target_comb = (a == -4'sd1 && b == -4'sd1) ? -4'sd1 : 4'sd1;
            2'b10: target_comb = (a == 4'sd1 && b == 4'sd1) ? -4'sd1 : 4'sd1;
            2'b11: target_comb = (a == -4'sd1 && b == -4'sd1) ? 4'sd1 : -4'sd1;
            default: target_comb = 4'sd0;
        endcase
    end

    always_comb begin
        case (present_state)
            S0: next_state = (start && (a != 4'sd0 || b != 4'sd0)) ? S1 : S0;
            S1: next_state = S2;
            S2: next_state = (a != prev_a || b != prev_b) ? S1 : S2;
            default: next_state = S0;
        endcase
    end

    always_ff @(posedge clk or negedge rst) begin
        if (!rst) begin
            present_state <= S0;
            w1   <= 4'sd0;
            w2   <= 4'sd0;
            bias <= 4'sd0;
            prev_a <= 4'sd0;
            prev_b <= 4'sd0;
        end else begin
            present_state <= next_state;
            case (present_state)
                S0: begin end
                S1: begin
                    w1   <= w1 + a * target_comb;
                    w2   <= w2 + b * target_comb;
                    bias <= bias + target_comb;
                    prev_a <= a;
                    prev_b <= b;
                end
                S2: begin
                    prev_a <= a;
                    prev_b <= b;
                end
                default: begin end
            endcase
        end
    end

endmodule
