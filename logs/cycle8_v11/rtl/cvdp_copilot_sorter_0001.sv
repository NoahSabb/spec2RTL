module sorting_engine #(
    parameter N     = 8,
    parameter WIDTH = 8
)(
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  start,
    input  wire [N*WIDTH-1:0]    in_data,
    output reg                   done,
    output reg  [N*WIDTH-1:0]    out_data
);

    integer i;
    reg [WIDTH-1:0] data_reg [0:N-1];
    reg [$clog2(N*N+4)-1:0] step;

    // Derived index j = (step-1) % (N-1)
    wire [$clog2(N+1)-1:0] j;
    assign j = (N > 1) ? ((step - 1) % (N-1)) : 0;

    localparam IDLE    = 1'd0;
    localparam SORTING = 1'd1;

    reg state, next_state;

    // Total steps
    localparam TOTAL_STEPS = N * (N - 1);

    // Next state logic
    always @(*) begin
        next_state = state;
        case (state)
            IDLE: begin
                if (start)
                    next_state = SORTING;
            end
            SORTING: begin
                if (step == TOTAL_STEPS)
                    next_state = IDLE;
            end
        endcase
    end

    // FSM state register and done signal
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state <= IDLE;
            done  <= 0;
        end else begin
            state <= next_state;
            if (state == SORTING && step == TOTAL_STEPS)
                done <= 1;
            else
                done <= 0;
        end
    end

    // Data and step register
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            step <= 0;
            for (i = 0; i < N; i = i + 1)
                data_reg[i] <= 0;
        end else begin
            case (state)
                IDLE: begin
                    if (start) begin
                        for (i = 0; i < N; i = i + 1)
                            data_reg[i] <= in_data[i*WIDTH +: WIDTH];
                        step <= 1;
                    end
                end
                SORTING: begin
                    // Perform compare-swap on positions j and j+1
                    // j = (step-1) % (N-1)
                    if (step <= TOTAL_STEPS) begin
                        if (data_reg[j] > data_reg[j+1]) begin
                            data_reg[j]   <= data_reg[j+1];
                            data_reg[j+1] <= data_reg[j];
                        end
                    end
                    step <= step + 1;
                    // Write out_data on the last step
                    if (step == TOTAL_STEPS) begin
                        for (i = 0; i < N; i = i + 1) begin
                            if (i == j) begin
                                if (data_reg[j] > data_reg[j+1])
                                    out_data[i*WIDTH +: WIDTH] <= data_reg[j+1];
                                else
                                    out_data[i*WIDTH +: WIDTH] <= data_reg[i];
                            end else if (i == j + 1) begin
                                if (data_reg[j] > data_reg[j+1])
                                    out_data[i*WIDTH +: WIDTH] <= data_reg[j];
                                else
                                    out_data[i*WIDTH +: WIDTH] <= data_reg[i];
                            end else begin
                                out_data[i*WIDTH +: WIDTH] <= data_reg[i];
                            end
                        end
                    end
                end
            endcase
        end
    end

endmodule
