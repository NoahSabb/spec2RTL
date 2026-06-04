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
    reg [WIDTH-1:0] local_remainder;
    reg [$clog2(WIDTH)+1:0] counter;

    // Determine number of cycles needed
    localparam CYCLES = (WIDTH & (WIDTH-1)) == 0 ? WIDTH : WIDTH + 1;

    // States for state machine
    typedef enum reg [1:0] {
        IDLE,
        SHIFT_SUBTRACT,
        DONE
    } state_t;

    state_t state, next_state;

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
                if (start) begin
                    next_state = SHIFT_SUBTRACT;
                end else begin
                    next_state = IDLE;
                end
            end
            SHIFT_SUBTRACT: begin
                if (counter == CYCLES - 1) begin
                    next_state = IDLE;
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
            quotient        <= '0;
            remainder       <= '0;
            valid           <= 0;
            local_dividend  <= '0;
            local_divisor   <= '0;
            local_quotient  <= '0;
            local_remainder <= '0;
            counter         <= '0;
        end else begin
            case (state)
                IDLE: begin
                    valid <= 0;
                    if (start) begin
                        local_dividend  <= dividend;
                        local_divisor   <= divisor;
                        local_quotient  <= '0;
                        local_remainder <= '0;
                        counter         <= 0;
                    end
                end
                SHIFT_SUBTRACT: begin
                    begin
                        // Shift remainder left by 1, append current MSB of local_dividend
                        reg [WIDTH-1:0] rem_shifted;
                        reg [WIDTH:0]   diff;
                        rem_shifted = {local_remainder[WIDTH-2:0], local_dividend[WIDTH-1]};
                        // Shift local_dividend left
                        local_dividend <= {local_dividend[WIDTH-2:0], 1'b0};
                        // Subtract divisor
                        diff = {1'b0, rem_shifted} - {1'b0, local_divisor};
                        if (diff[WIDTH] == 0) begin
                            // Non-negative result: keep subtraction
                            local_remainder <= diff[WIDTH-1:0];
                            local_quotient  <= {local_quotient[WIDTH-2:0], 1'b1};
                            if (counter == CYCLES - 1) begin
                                quotient  <= {local_quotient[WIDTH-2:0], 1'b1};
                                remainder <= diff[WIDTH-1:0];
                                valid     <= 1;
                            end
                        end else begin
                            // Negative result: restore remainder
                            local_remainder <= rem_shifted;
                            local_quotient  <= {local_quotient[WIDTH-2:0], 1'b0};
                            if (counter == CYCLES - 1) begin
                                quotient  <= {local_quotient[WIDTH-2:0], 1'b0};
                                remainder <= rem_shifted;
                                valid     <= 1;
                            end
                        end
                        counter <= counter + 1;
                    end
                end
                DONE: begin
                    quotient  <= local_quotient;
                    remainder <= local_remainder;
                    valid     <= 1;
                end
                default: begin
                    valid <= 0;
                end
            endcase
        end
    end

endmodule
