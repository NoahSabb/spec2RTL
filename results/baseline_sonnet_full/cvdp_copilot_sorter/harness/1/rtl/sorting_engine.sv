module sorting_engine #(
    parameter int N     = 8,
    parameter int WIDTH = 8
)(
    input  logic                  clk,
    input  logic                  rst,
    input  logic                  start,
    input  logic [N*WIDTH-1:0]    in_data,
    output logic                  done,
    output logic [N*WIDTH-1:0]    out_data
);

    // State encoding
    typedef enum logic [1:0] {
        IDLE    = 2'b00,
        SORTING = 2'b01,
        DONE    = 2'b10
    } state_t;

    state_t state, next_state;

    // Internal array
    logic [WIDTH-1:0] arr [0:N-1];

    // Counters
    // Total passes = N*(N-1), each pass does one comparison
    // We need a counter to track which comparison we're on
    // Total comparisons = N*(N-1)
    // Index into the "flat" list of comparisons
    // For bubble sort: pass p (0 to N-2), compare index i (0 to N-2-p)
    // But we're doing N*(N-1) total passes (comparisons)
    
    // Counter for total steps: N*(N-1) steps
    localparam int TOTAL_STEPS = N * (N - 1);
    localparam int CNT_WIDTH   = $clog2(TOTAL_STEPS + 1);

    logic [CNT_WIDTH-1:0] step_cnt;

    // For each step, we need to know which pair to compare
    // We'll use pass and index counters
    // pass: 0 to N-2, index: 0 to N-2-pass
    // But we do exactly N*(N-1) steps total (not early termination)
    // Let's track pass_cnt and idx_cnt
    
    localparam int PASS_CNT_WIDTH = $clog2(N);
    localparam int IDX_CNT_WIDTH  = $clog2(N);

    logic [PASS_CNT_WIDTH-1:0] pass_cnt;
    logic [IDX_CNT_WIDTH-1:0]  idx_cnt;

    // Temporary for swap
    logic [WIDTH-1:0] temp;

    integer k;

    // State register
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            state    <= IDLE;
            done     <= 1'b0;
            step_cnt <= '0;
            pass_cnt <= '0;
            idx_cnt  <= '0;
        end else begin
            state <= next_state;

            case (state)
                IDLE: begin
                    done     <= 1'b0;
                    step_cnt <= '0;
                    pass_cnt <= '0;
                    idx_cnt  <= '0;
                    if (start) begin
                        // Load input data into internal array
                        for (k = 0; k < N; k++) begin
                            arr[k] <= in_data[k*WIDTH +: WIDTH];
                        end
                    end
                end

                SORTING: begin
                    done <= 1'b0;
                    // Perform one comparison/swap per cycle
                    // Current comparison: arr[idx_cnt] vs arr[idx_cnt+1]
                    if (arr[idx_cnt] > arr[idx_cnt + 1]) begin
                        // Swap
                        arr[idx_cnt]     <= arr[idx_cnt + 1];
                        arr[idx_cnt + 1] <= arr[idx_cnt];
                    end

                    // Advance counters
                    step_cnt <= step_cnt + 1'b1;

                    // Advance idx_cnt and pass_cnt
                    // In a standard bubble sort pass p, we go from idx=0 to idx=N-2-p
                    // When idx_cnt reaches N-2-pass_cnt, move to next pass
                    if (idx_cnt >= (N - 2 - pass_cnt)) begin
                        idx_cnt  <= '0;
                        pass_cnt <= pass_cnt + 1'b1;
                    end else begin
                        idx_cnt <= idx_cnt + 1'b1;
                    end
                end

                DONE: begin
                    done <= 1'b1;
                    // Write sorted array to output
                    for (k = 0; k < N; k++) begin
                        out_data[k*WIDTH +: WIDTH] <= arr[k];
                    end
                end

                default: begin
                    done <= 1'b0;
                end
            endcase
        end
    end

    // Next state logic
    always_comb begin
        next_state = state;
        case (state)
            IDLE: begin
                if (start)
                    next_state = SORTING;
                else
                    next_state = IDLE;
            end

            SORTING: begin
                // Done after N*(N-1) steps
                if (step_cnt == (TOTAL_STEPS - 1))
                    next_state = DONE;
                else
                    next_state = SORTING;
            end

            DONE: begin
                // done is pulsed for 1 cycle, go back to IDLE
                next_state = IDLE;
            end

            default: next_state = IDLE;
        endcase
    end

endmodule
