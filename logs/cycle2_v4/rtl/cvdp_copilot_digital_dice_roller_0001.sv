module digital_dice_roller (
    input wire clk,
    input wire reset_n,
    input wire button,
    output reg [2:0] dice_value
);

    // FSM states
    parameter IDLE    = 1'b0;
    parameter ROLLING = 1'b1;
    
    reg state;
    reg [2:0] counter;
    
    // FSM and counter logic
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state      <= IDLE;
            counter    <= 3'd1;
            dice_value <= 3'd1;
        end else begin
            case (state)
                IDLE: begin
                    dice_value <= counter;
                    if (button) begin
                        state <= ROLLING;
                    end
                end
                
                ROLLING: begin
                    if (button) begin
                        // Continue rolling
                        if (counter >= 3'd6)
                            counter <= 3'd1;
                        else
                            counter <= counter + 3'd1;
                    end else begin
                        // Button released, go to IDLE and latch value
                        state      <= IDLE;
                        dice_value <= counter;
                    end
                end
                
                default: begin
                    state <= IDLE;
                end
            endcase
        end
    end

endmodule
