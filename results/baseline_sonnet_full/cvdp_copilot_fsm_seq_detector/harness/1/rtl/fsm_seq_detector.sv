// rtl/fsm_seq_detector.sv
// FSM Sequence Detector for sequence "10110001"

module fsm_seq_detector (
    input  bit     clk_in,
    input  logic   rst_in,
    input  logic   seq_in,
    output logic   seq_detected
);

    // State type definition
    typedef enum logic [2:0] {
        S0 = 3'b000,  // Initial state, waiting for '1'
        S1 = 3'b001,  // Received '1'
        S2 = 3'b010,  // Received '10'
        S3 = 3'b011,  // Received '101'
        S4 = 3'b100,  // Received '1011'
        S5 = 3'b101,  // Received '10110'
        S6 = 3'b110,  // Received '101100'
        S7 = 3'b111   // Received '1011000'
    } state_t;

    state_t cur_state, next_state;
    logic   seq_detected_w;

    // Sequential block: state register and output register
    always_ff @(posedge clk_in or posedge rst_in) begin
        if (rst_in) begin
            cur_state    <= S0;
            seq_detected <= 1'b0;
        end else begin
            cur_state    <= next_state;
            seq_detected <= seq_detected_w;
        end
    end

    // Combinational block: next state logic and output logic
    // Sequence to detect: 1 0 1 1 0 0 0 1
    //                     S0->S1->S2->S3->S4->S5->S6->S7->detect
    always_comb begin
        // Default values
        next_state     = S0;
        seq_detected_w = 1'b0;

        case (cur_state)
            S0: begin
                // Waiting for first bit '1'
                if (seq_in == 1'b1)
                    next_state = S1;
                else
                    next_state = S0;
            end

            S1: begin
                // Received '1', waiting for '0'
                if (seq_in == 1'b0)
                    next_state = S2;
                else
                    next_state = S1; // '1' again, stay at S1
            end

            S2: begin
                // Received '10', waiting for '1'
                if (seq_in == 1'b1)
                    next_state = S3;
                else
                    next_state = S0; // '0', go back to S0
            end

            S3: begin
                // Received '101', waiting for '1'
                if (seq_in == 1'b1)
                    next_state = S4;
                else
                    next_state = S2; // '0', received '10' suffix, go to S2
            end

            S4: begin
                // Received '1011', waiting for '0'
                if (seq_in == 1'b0)
                    next_state = S5;
                else
                    next_state = S1; // '1', only last '1' counts, go to S1
            end

            S5: begin
                // Received '10110', waiting for '0'
                if (seq_in == 1'b0)
                    next_state = S6;
                else
                    next_state = S3; // '1', received '101' suffix, go to S3
            end

            S6: begin
                // Received '101100', waiting for '0'
                if (seq_in == 1'b0)
                    next_state = S7;
                else
                    next_state = S3; // '1', received '101' suffix, go to S3
            end

            S7: begin
                // Received '1011000', waiting for '1'
                if (seq_in == 1'b1) begin
                    next_state     = S1;  // Sequence detected! Last '1' can be start of new sequence
                    seq_detected_w = 1'b1;
                end else begin
                    next_state = S0; // '0', no overlap possible, go to S0
                end
            end

            default: begin
                next_state     = S0;
                seq_detected_w = 1'b0;
            end
        endcase
    end

endmodule
