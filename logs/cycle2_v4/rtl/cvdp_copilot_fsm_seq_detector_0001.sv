module fsm_seq_detector (
    input  bit   clk_in,
    input  logic rst_in,
    input  logic seq_in,
    output logic seq_detected
);

    typedef enum logic [2:0] {
        S0 = 3'd0,
        S1 = 3'd1,
        S2 = 3'd2,
        S3 = 3'd3,
        S4 = 3'd4,
        S5 = 3'd5,
        S6 = 3'd6,
        S7 = 3'd7
    } state_t;

    state_t cur_state, next_state;
    logic seq_detected_w;

    // Sequential: state register
    always @(posedge clk_in or posedge rst_in) begin
        if (rst_in) begin
            cur_state    <= S0;
            seq_detected <= 1'b0;
        end else begin
            cur_state    <= next_state;
            seq_detected <= seq_detected_w;
        end
    end

    // Combinational: next state and output logic
    // Sequence: 1 0 1 1 0 0 0 1
    always_comb begin
        next_state     = S0;
        seq_detected_w = 1'b0;

        case (cur_state)
            S0: begin
                if (seq_in == 1'b1) next_state = S1;
                else                next_state = S0;
            end
            S1: begin // received: 1
                if (seq_in == 1'b0) next_state = S2;
                else                next_state = S1; // '1' restarts at S1
            end
            S2: begin // received: 10
                if (seq_in == 1'b1) next_state = S3;
                else                next_state = S0;
            end
            S3: begin // received: 101
                if (seq_in == 1'b1) next_state = S4;
                else                next_state = S2; // '0': "1010" -> "10" prefix
            end
            S4: begin // received: 1011
                if (seq_in == 1'b0) next_state = S5;
                else                next_state = S1; // '1': restart, last '1' counts
            end
            S5: begin // received: 10110
                if (seq_in == 1'b0) next_state = S6;
                else                next_state = S3; // '1': "101101" -> "101" prefix
            end
            S6: begin // received: 101100
                if (seq_in == 1'b0) next_state = S7;
                else                next_state = S1; // '1': "1011001" -> "1" prefix
            end
            S7: begin // received: 1011000
                if (seq_in == 1'b1) begin
                    next_state     = S1; // overlap: last '1' is prefix
                    seq_detected_w = 1'b1;
                end else begin
                    next_state = S0;
                end
            end
            default: begin
                next_state     = S0;
                seq_detected_w = 1'b0;
            end
        endcase
    end

endmodule
