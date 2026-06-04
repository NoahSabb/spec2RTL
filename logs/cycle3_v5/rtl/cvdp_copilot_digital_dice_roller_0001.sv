module digital_dice_roller (
    input  wire       clk,
    input  wire       reset,
    input  wire       button,
    output reg  [2:0] dice_value
);

    // FSM states
    localparam IDLE    = 1'b0;
    localparam ROLLING = 1'b1;

    reg state;
    reg [2:0] counter;

    // FSM and counter logic
    always @(posedge clk or negedge reset) begin
        if (!reset) begin
            state      <= IDLE;
            counter    <= 3'd1;
            dice_value <= 3'd0;
        end else begin
            case (state)
                IDLE: begin
                    if (button) begin
                        state   <= ROLLING;
                        counter <= 3'd1;
                    end
                end
                ROLLING: begin
                    if (!button) begin
                        state      <= IDLE;
                        dice_value <= counter;
                    end else begin
                        if (counter == 3'd6)
                            counter <= 3'd1;
                        else
                            counter <= counter + 3'd1;
                    end
                end
                default: begin
                    state   <= IDLE;
                    counter <= 3'd1;
                end
            endcase
        end
    end

endmodule
