// rtl/hill_cipher.sv

module hill_cipher (
    input  logic        clk,
    input  logic        reset,
    input  logic        start,
    input  logic [14:0] plaintext,
    input  logic [44:0] key,
    output logic [14:0] ciphertext,
    output logic        done
);

    // FSM States
    typedef enum logic [1:0] {
        IDLE    = 2'b00,
        COMPUTE = 2'b01,
        OUTPUT  = 2'b10
    } state_t;

    state_t state, next_state;

    // Key matrix elements
    logic [4:0] K00, K01, K02;
    logic [4:0] K10, K11, K12;
    logic [4:0] K20, K21, K22;

    // Plaintext vector elements
    logic [4:0] P0, P1, P2;

    // Intermediate ciphertext values (wider to handle multiplication)
    logic [14:0] C0_raw, C1_raw, C2_raw;
    logic [4:0]  C0, C1, C2;

    // Internal registers
    logic [14:0] plaintext_reg;
    logic [44:0] key_reg;

    // Cycle counter for latency
    logic [1:0] cycle_count;

    // Extract key elements
    assign K00 = key_reg[44:40];
    assign K01 = key_reg[39:35];
    assign K02 = key_reg[34:30];
    assign K10 = key_reg[29:25];
    assign K11 = key_reg[24:20];
    assign K12 = key_reg[19:15];
    assign K20 = key_reg[14:10];
    assign K21 = key_reg[9:5];
    assign K22 = key_reg[4:0];

    // Extract plaintext elements
    assign P0 = plaintext_reg[14:10];
    assign P1 = plaintext_reg[9:5];
    assign P2 = plaintext_reg[4:0];

    // Matrix multiplication
    assign C0_raw = (K00 * P0) + (K01 * P1) + (K02 * P2);
    assign C1_raw = (K10 * P0) + (K11 * P1) + (K12 * P2);
    assign C2_raw = (K20 * P0) + (K21 * P1) + (K22 * P2);

    // Modulo 26
    assign C0 = C0_raw % 26;
    assign C1 = C1_raw % 26;
    assign C2 = C2_raw % 26;

    // FSM - State register
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            state       <= IDLE;
            cycle_count <= 2'b00;
            plaintext_reg <= 15'b0;
            key_reg       <= 45'b0;
            ciphertext    <= 15'b0;
            done          <= 1'b0;
        end else begin
            case (state)
                IDLE: begin
                    done <= 1'b0;
                    if (start) begin
                        plaintext_reg <= plaintext;
                        key_reg       <= key;
                        cycle_count   <= 2'b00;
                        state         <= COMPUTE;
                    end
                end

                COMPUTE: begin
                    if (cycle_count == 2'b01) begin
                        state       <= OUTPUT;
                        cycle_count <= 2'b00;
                    end else begin
                        cycle_count <= cycle_count + 1'b1;
                    end
                end

                OUTPUT: begin
                    ciphertext <= {C0, C1, C2};
                    done       <= 1'b1;
                    state      <= IDLE;
                end

                default: begin
                    state <= IDLE;
                end
            endcase
        end
    end

endmodule
