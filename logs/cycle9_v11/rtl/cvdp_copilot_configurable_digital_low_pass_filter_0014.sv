module fsm_linear_reg #(
    parameter integer DATA_WIDTH = 16
) (
    input  wire                             clk,
    input  wire                             reset,
    input  wire                             start,
    input  wire signed [DATA_WIDTH-1:0]     x_in,
    input  wire signed [DATA_WIDTH-1:0]     w_in,
    input  wire signed [DATA_WIDTH-1:0]     b_in,
    output reg  signed [2*DATA_WIDTH-1:0]   result1,
    output reg  signed [DATA_WIDTH:0]       result2,
    output reg                              done
);

    // Define states
    localparam [1:0] IDLE    = 2'b00;
    localparam [1:0] COMPUTE = 2'b01;
    localparam [1:0] DONE    = 2'b10;

    // State registers
    reg [1:0] current_state, next_state;

    // Intermediate results
    wire signed [2*DATA_WIDTH-1:0] product;
    wire signed [2*DATA_WIDTH-1:0] weighted_sum;
    wire signed [DATA_WIDTH-1:0]   x_shifted;
    wire signed [DATA_WIDTH:0]     bias_adjusted_input;

    // Combinational logic for weighted sum and bias-adjusted input
    assign product              = $signed(w_in) * $signed(x_in);
    assign weighted_sum         = $signed(product) >>> 1;
    assign x_shifted            = $signed(x_in) >>> 2;
    assign bias_adjusted_input  = $signed({{1{b_in[DATA_WIDTH-1]}}, b_in}) + $signed({{1{x_shifted[DATA_WIDTH-1]}}, x_shifted});

    // State transition logic (sequential)
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            current_state <= IDLE;
        end else begin
            current_state <= next_state;
        end
    end

    // Next state logic (combinational)
    always @(*) begin
        case (current_state)
            IDLE: begin
                if (start)
                    next_state = COMPUTE;
                else
                    next_state = IDLE;
            end
            COMPUTE: begin
                next_state = DONE;
            end
            DONE: begin
                next_state = IDLE;
            end
            default: begin
                next_state = IDLE;
            end
        endcase
    end

    // Output logic (sequential)
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            result1 <= {(2*DATA_WIDTH){1'b0}};
            result2 <= {(DATA_WIDTH+1){1'b0}};
            done    <= 1'b0;
        end else begin
            case (current_state)
                IDLE: begin
                    result1 <= {(2*DATA_WIDTH){1'b0}};
                    result2 <= {(DATA_WIDTH+1){1'b0}};
                    done    <= 1'b0;
                end
                COMPUTE: begin
                    result1 <= weighted_sum;
                    result2 <= bias_adjusted_input;
                    done    <= 1'b0;
                end
                DONE: begin
                    result1 <= result1;
                    result2 <= result2;
                    done    <= 1'b1;
                end
                default: begin
                    result1 <= {(2*DATA_WIDTH){1'b0}};
                    result2 <= {(DATA_WIDTH+1){1'b0}};
                    done    <= 1'b0;
                end
            endcase
        end
    end

endmodule
