module hill_cipher (
    input wire clk,
    input wire reset,
    input wire start,
    input wire [14:0] plaintext,
    input wire [44:0] key,
    output reg [14:0] ciphertext,
    output reg done
);

    // Define states for the FSM
    typedef enum reg [1:0] {
        IDLE,
        COMPUTE,
        DONE
    } state_t;

    state_t state, next_state;

    // Intermediate registers for matrix multiplication
    wire [4:0] p0, p1, p2;
    wire [4:0] k00, k01, k02, k10, k11, k12, k20, k21, k22;
    reg [14:0] sum0, sum1, sum2;

    // Continuous assignments for plaintext and key elements
    assign p0 = plaintext[14:10];
    assign p1 = plaintext[9:5];
    assign p2 = plaintext[4:0];

    assign k00 = key[44:40];
    assign k01 = key[39:35];
    assign k02 = key[34:30];
    assign k10 = key[29:25];
    assign k11 = key[24:20];
    assign k12 = key[19:15];
    assign k20 = key[14:10];
    assign k21 = key[9:5];
    assign k22 = key[4:0];

    // Modulo wires
    wire [14:0] mod0, mod1, mod2;
    assign mod0 = sum0 % 26;
    assign mod1 = sum1 % 26;
    assign mod2 = sum2 % 26;

    // FSM state transition logic
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            state <= IDLE;
            done <= 0;
            ciphertext <= 15'b0;
            sum0 <= 0;
            sum1 <= 0;
            sum2 <= 0;
        end else begin
            state <= next_state;
            case (state)
                IDLE: begin
                    done <= 0;
                    sum0 <= 0;
                    sum1 <= 0;
                    sum2 <= 0;
                end
                COMPUTE: begin
                    done <= 0;
                    sum0 <= (k00 * p0) + (k01 * p1) + (k02 * p2);
                    sum1 <= (k10 * p0) + (k11 * p1) + (k12 * p2);
                    sum2 <= (k20 * p0) + (k21 * p1) + (k22 * p2);
                end
                DONE: begin
                    ciphertext <= {mod0[4:0], mod1[4:0], mod2[4:0]};
                    done <= 1;
                end
                default: begin
                    done <= 0;
                end
            endcase
        end
    end

    // FSM next state logic
    always @(*) begin
        case (state)
            IDLE: begin
                if (start)
                    next_state = COMPUTE;
                else
                    next_state = IDLE;
            end
            COMPUTE: next_state = DONE;
            DONE: next_state = IDLE;
            default: next_state = IDLE;
        endcase
    end

endmodule
