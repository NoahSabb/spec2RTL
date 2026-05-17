module fsm_linear_reg #(
    parameter DATA_WIDTH = 16
)(
    input  logic                        clk,
    input  logic                        reset,
    input  logic                        start,
    input  logic signed [DATA_WIDTH-1:0] x_in,
    input  logic signed [DATA_WIDTH-1:0] w_in,
    input  logic signed [DATA_WIDTH-1:0] b_in,
    output logic signed [2*DATA_WIDTH-1:0] result1,
    output logic signed [DATA_WIDTH:0]     result2,
    output logic                           done
);

    // State encoding
    typedef enum logic [1:0] {
        IDLE    = 2'b00,
        COMPUTE = 2'b01,
        DONE    = 2'b10
    } state_t;

    state_t current_state, next_state;

    // Internal computation signals
    logic signed [2*DATA_WIDTH-1:0] result1_next;
    logic signed [DATA_WIDTH:0]     result2_next;

    // State register (synchronous with async reset)
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            current_state <= IDLE;
        end else begin
            current_state <= next_state;
        end
    end

    // Next state logic
    always_comb begin
        case (current_state)
            IDLE:    next_state = start ? COMPUTE : IDLE;
            COMPUTE: next_state = DONE;
            DONE:    next_state = IDLE;
            default: next_state = IDLE;
        endcase
    end

    // Combinational computation
    always_comb begin
        // result1 = w_in * x_in >>> 1
        result1_next = ({{DATA_WIDTH{w_in[DATA_WIDTH-1]}}, w_in} * {{DATA_WIDTH{x_in[DATA_WIDTH-1]}}, x_in}) >>> 1;
        // result2 = b_in + (x_in >>> 2)
        result2_next = {{1{b_in[DATA_WIDTH-1]}}, b_in} + {{1{x_in[DATA_WIDTH-1]}}, x_in} >>> 2;
    end

    // Output registers
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            result1 <= '0;
            result2 <= '0;
            done    <= 1'b0;
        end else begin
            case (current_state)
                IDLE: begin
                    result1 <= '0;
                    result2 <= '0;
                    done    <= 1'b0;
                end
                COMPUTE: begin
                    result1 <= result1_next;
                    result2 <= result2_next;
                    done    <= 1'b0;
                end
                DONE: begin
                    done <= 1'b1;
                end
                default: begin
                    result1 <= '0;
                    result2 <= '0;
                    done    <= 1'b0;
                end
            endcase
        end
    end

endmodule
