module factorial_computation (
    input clk,
    input arst_n,
    input [4:0] num_in,
    input start,
    output reg busy,
    output reg [63:0] fact,
    output reg done
);
    
    // Define State Enum for FSM
    typedef enum {
        Idle,
        Bussy,
        Done
    } state_t;
    
    // Define FSM Signals and Regs
    reg [2:0] state;
    parameter Idle = 3'd0;
    parameter Bussy = 3'd1;
    parameter Done = 3'd2;
    
    always @ (posedge clk or negedge arst_n) begin
        if (!arst_n) begin
            state <= Idle;
            busy <= 0;
            fact <= 1;
            done <= 0;
            fact <= 1;
        end else begin
            case (state)
                Idle: begin
                    if (start == 1 && num_in < 32) begin
                        state <= Bussy;
                        busy <= 1;
                    end
                end
                Bussy: begin
                    fact <= fact * (num_in+1);
                    num_in = num_in - 1;
                    if (num_in == 0) begin
                        state <= Done;
                        busy <= 0;
                        done <= 1;
                    end else begin
                        fact <= fact * (num_in+1);
                        num_in = num_in - 1;
                    end
                end
                Done: begin
                    done <= 0;
                end
            endcase
        end
    end
endmodule