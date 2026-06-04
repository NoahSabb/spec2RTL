module digital_dice_roller (
    input wire clk,
    input wire reset,
    input wire button,
    output reg [2:0] dice_value
);

    parameter DICE_MAX = 6;

    // Define states for the FSM
    typedef enum logic {
        IDLE,
        ROLLING
    } state_t;

    // Internal signals
    reg [2:0] counter;
    state_t current_state, next_state;

    // State transition logic (sequential)
    always @(posedge clk or negedge reset) begin
        if (!reset) begin
            current_state <= IDLE;
            dice_value <= 3'b001;
            counter <= 3'b001;
        end else begin
            current_state <= next_state;
            if (current_state == ROLLING) begin
                if (button) begin
                    if (counter == 3'd6)
                        counter <= 3'b001;
                    else
                        counter <= counter + 1;
                end else begin
                    dice_value <= counter;
                end
            end
        end
    end

    // Next state logic (combinational)
    always @(*) begin
        next_state = current_state;
        case (current_state)
            IDLE: begin
                if (button)
                    next_state = ROLLING;
            end
            ROLLING: begin
                if (!button)
                    next_state = IDLE;
            end
        endcase
    end

endmodule
