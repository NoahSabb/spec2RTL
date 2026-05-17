module digital_dice_roller (
    input  logic       clk,
    input  logic       reset_n,
    input  logic       button,
    output logic [2:0] dice_value
);

    // FSM State Encoding
    typedef enum logic [1:0] {
        IDLE    = 2'b00,
        ROLLING = 2'b01
    } state_t;

    state_t current_state, next_state;

    // Internal counter register
    logic [2:0] counter;

    // State register (sequential)
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            current_state <= IDLE;
        end else begin
            current_state <= next_state;
        end
    end

    // Next state logic (combinational)
    always_comb begin
        case (current_state)
            IDLE: begin
                if (button)
                    next_state = ROLLING;
                else
                    next_state = IDLE;
            end
            ROLLING: begin
                if (!button)
                    next_state = IDLE;
                else
                    next_state = ROLLING;
            end
            default: next_state = IDLE;
        endcase
    end

    // Counter logic (sequential)
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            counter <= 3'd1;
        end else begin
            if (current_state == ROLLING) begin
                if (counter >= 3'd6)
                    counter <= 3'd1;
                else
                    counter <= counter + 3'd1;
            end
        end
    end

    // Output logic (sequential)
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            dice_value <= 3'd0;
        end else begin
            if (current_state == ROLLING) begin
                dice_value <= counter;
            end
            // In IDLE state, dice_value holds its last value
        end
    end

endmodule
