module restoring_division #(
    parameter WIDTH = 6
) (
    input wire clk,
    input wire rst,
    input wire start,
    input wire [WIDTH-1:0] dividend,
    input wire [WIDTH-1:0] divisor,
    output reg [WIDTH-1:0] quotient,
    output reg [WIDTH-1:0] remainder,
    output reg valid
);

    // Internal registers
    reg [WIDTH-1:0] local_dividend;
    reg [WIDTH-1:0] local_divisor;
    reg [WIDTH-1:0] local_quotient;
    reg [WIDTH-1:0] partial_rem;
    reg [$clog2(WIDTH)+1:0] counter;

    // States for state machine
    typedef enum reg [1:0] {
        IDLE,
        SHIFT_SUBTRACT,
        DONE
    } state_t;

    state_t state, next_state;

    // Intermediate wires
    wire [WIDTH-1:0] shifted_rem;
    wire [WIDTH-1:0] local_dividend_next;
    wire [WIDTH:0] diff;

    assign shifted_rem = {partial_rem[WIDTH-2:0], local_dividend[WIDTH-1]};
    assign local_dividend_next = {local_dividend[WIDTH-2:0], 1'b0};
    assign diff = {1'b0, shifted_rem} - {1'b0, local_divisor};

    // State machine logic
    always_ff @(posedge clk or negedge rst) begin
        if (!rst) begin
            state <= IDLE;
        end else begin
            state <= next_state;
        end
    end

    // Next state logic
    always_comb begin
        case (state)
            IDLE: begin
                if (start && !valid) begin
                    next_state = SHIFT_SUBTRACT;
                end else begin
                    next_state = IDLE;
                end
            end
            SHIFT_SUBTRACT: begin
                if (counter == WIDTH) begin
                    next_state = DONE;
                end else begin
                    next_state = SHIFT_SUBTRACT;
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

    // Main logic
    always_ff @(posedge clk or negedge rst) begin
        if (!rst) begin
            quotient <= '0;
            remainder <= '0;
            valid <= 0;
            local_dividend <= '0;
            local_divisor <= '0;
            local_quotient <= '0;
            partial_rem <= '0;
            counter <= '0;
        end else begin
            // Clear valid after one clock cycle
            if (valid) begin
                valid <= 0;
            end

            case (state)
                IDLE: begin
                    if (start && !valid) begin
                        local_dividend <= dividend;
                        local_divisor <= divisor;
                        local_quotient <= '0;
                        partial_rem <= '0;
                        counter <= 0;
                    end
                end
                SHIFT_SUBTRACT: begin
                    if (counter < WIDTH) begin
                        // diff[WIDTH] is the sign bit (1 = negative)
                        if (diff[WIDTH] == 1'b0) begin
                            // Non-negative: subtraction successful
                            partial_rem <= diff[WIDTH-1:0];
                            local_quotient <= {local_quotient[WIDTH-2:0], 1'b1};
                        end else begin
                            // Negative: restore
                            partial_rem <= shifted_rem;
                            local_quotient <= {local_quotient[WIDTH-2:0], 1'b0};
                        end
                        local_dividend <= local_dividend_next;
                        counter <= counter + 1;
                    end
                end
                DONE: begin
                    quotient <= local_quotient;
                    remainder <= partial_rem;
                    valid <= 1;
                end
                default: begin
                end
            endcase
        end
    end

endmodule
