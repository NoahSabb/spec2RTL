module digital_dice_roller (
    input wire clk,
    input wire reset_n,
    input wire button,
    output reg [2:0] dice_value
);

    // Define states for the FSM
    typedef enum logic {
        IDLE,
        ROLLING
    } state_t;

    // Internal signals
    reg [2:0] counter;
    state_t current_state, next_state;

    // State transition logic
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            current_state <= IDLE;
            dice_value <= 3'b001; // Reset dice value to 1
            counter <= 3'b001;   // Start counter at 1
        end else begin
            current_state <= next_state;
            if (current_state == ROLLING) begin
                if (button) begin
                    // Increment counter while rolling
                    if (counter == 3'b110)
                        counter <= 3'b001;
                    else
                        counter <= counter + 1;
                end else begin
                    // Button released, capture the final value
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
                if (button) begin
                    next_state = ROLLING;
                end
            end
            ROLLING: begin
                if (!button) begin
                    next_state = IDLE;
                end
            end
        endcase
    end

endmodule
