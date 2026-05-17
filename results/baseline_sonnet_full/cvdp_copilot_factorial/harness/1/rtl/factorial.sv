module factorial (
    input  logic        clk,
    input  logic        arst_n,
    input  logic [4:0]  num_in,
    input  logic        start,
    output logic        busy,
    output logic [63:0] fact,
    output logic        done
);

    // FSM State Encoding
    typedef enum logic [1:0] {
        IDLE = 2'b00,
        BUSY = 2'b01,
        DONE = 2'b10
    } state_t;

    state_t current_state, next_state;

    // Internal registers
    logic [4:0]  counter;
    logic [4:0]  num_reg;
    logic [63:0] result;

    // State register (sequential)
    always_ff @(posedge clk or negedge arst_n) begin
        if (!arst_n) begin
            current_state <= IDLE;
        end else begin
            current_state <= next_state;
        end
    end

    // Datapath registers
    always_ff @(posedge clk or negedge arst_n) begin
        if (!arst_n) begin
            counter  <= 5'd0;
            num_reg  <= 5'd0;
            result   <= 64'd1;
            fact     <= 64'd0;
        end else begin
            case (current_state)
                IDLE: begin
                    if (start) begin
                        num_reg <= num_in;
                        result  <= 64'd1;
                        // Handle factorial of 0 or 1
                        if (num_in == 5'd0 || num_in == 5'd1) begin
                            counter <= 5'd0;
                        end else begin
                            counter <= num_in;
                        end
                    end
                end

                BUSY: begin
                    if (counter > 5'd0) begin
                        result  <= result * counter;
                        counter <= counter - 5'd1;
                    end
                end

                DONE: begin
                    fact    <= result;
                    result  <= 64'd1;
                    counter <= 5'd0;
                    num_reg <= 5'd0;
                end

                default: begin
                    counter <= 5'd0;
                    num_reg <= 5'd0;
                    result  <= 64'd1;
                end
            endcase
        end
    end

    // Next state logic (combinational)
    always_comb begin
        next_state = current_state;
        case (current_state)
            IDLE: begin
                if (start) begin
                    // If input is 0 or 1, factorial is computed immediately (0 cycles)
                    // We still need to go through BUSY for at least the defined behavior
                    // but since num_in=0 or 1 means 0 iterations needed
                    next_state = BUSY;
                end
            end

            BUSY: begin
                // Stay in BUSY until all iterations done (counter reaches 0)
                if (counter == 5'd0) begin
                    next_state = DONE;
                end else begin
                    next_state = BUSY;
                end
            end

            DONE: begin
                next_state = IDLE;
            end

            default: begin
                next_state = IDLE;
            end
        endcase
    end

    // Output logic
    always_comb begin
        busy = 1'b0;
        done = 1'b0;
        case (current_state)
            IDLE: begin
                busy = 1'b0;
                done = 1'b0;
            end
            BUSY: begin
                busy = 1'b1;
                done = 1'b0;
            end
            DONE: begin
                busy = 1'b0;
                done = 1'b1;
            end
            default: begin
                busy = 1'b0;
                done = 1'b0;
            end
        endcase
    end

endmodule
