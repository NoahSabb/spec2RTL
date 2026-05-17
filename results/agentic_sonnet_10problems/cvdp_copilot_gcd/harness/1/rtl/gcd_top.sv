// rtl/gcd_top.sv

// =============================================================================
// GCD Control Path Module
// =============================================================================
module gcd_controlpath (
    input  logic        clk,
    input  logic        rst,
    input  logic        go,
    input  logic        equal,
    input  logic        greater_than,
    output logic [1:0]  controlpath_state,
    output logic        done
);

    // FSM State Encoding
    localparam logic [1:0] S0 = 2'b00; // IDLE
    localparam logic [1:0] S1 = 2'b01; // DONE
    localparam logic [1:0] S2 = 2'b10; // A > B
    localparam logic [1:0] S3 = 2'b11; // B > A

    logic [1:0] state_reg, state_next;

    // State register - synchronous with reset
    always_ff @(posedge clk) begin
        if (rst)
            state_reg <= S0;
        else
            state_reg <= state_next;
    end

    // Next state logic (combinational)
    always_comb begin
        case (state_reg)
            S0: begin
                if (go) begin
                    if (equal)
                        state_next = S1;
                    else if (greater_than)
                        state_next = S2;
                    else
                        state_next = S3;
                end else begin
                    state_next = S0;
                end
            end
            S1: begin
                state_next = S0;
            end
            S2: begin
                if (equal)
                    state_next = S1;
                else if (greater_than)
                    state_next = S2;
                else
                    state_next = S3;
            end
            S3: begin
                if (equal)
                    state_next = S1;
                else if (greater_than)
                    state_next = S2;
                else
                    state_next = S3;
            end
            default: begin
                state_next = S0;
            end
        endcase
    end

    // Output logic - registered outputs
    always_ff @(posedge clk) begin
        if (rst) begin
            controlpath_state <= S0;
            done              <= 1'b0;
        end else begin
            controlpath_state <= state_next;
            done              <= (state_next == S1) ? 1'b1 : 1'b0;
        end
    end

endmodule


// =============================================================================
// GCD Datapath Module
// =============================================================================
module gcd_datapath #(
    parameter int WIDTH = 4
) (
    input  logic              clk,
    input  logic              rst,
    input  logic [WIDTH-1:0]  A,
    input  logic [WIDTH-1:0]  B,
    input  logic [1:0]        controlpath_state,
    output logic [WIDTH-1:0]  OUT,
    output logic              equal,
    output logic              greater_than
);

    // FSM State Encoding (matches controlpath)
    localparam logic [1:0] S0 = 2'b00; // IDLE
    localparam logic [1:0] S1 = 2'b01; // DONE
    localparam logic [1:0] S2 = 2'b10; // A > B
    localparam logic [1:0] S3 = 2'b11; // B > A

    logic [WIDTH-1:0] A_ff, B_ff;

    // Internal registers for A and B
    always_ff @(posedge clk) begin
        if (rst) begin
            A_ff <= '0;
            B_ff <= '0;
        end else begin
            case (controlpath_state)
                S0: begin
                    // Latch inputs when in IDLE state
                    A_ff <= A;
                    B_ff <= B;
                end
                S1: begin
                    // Hold values in DONE state
                    A_ff <= A_ff;
                    B_ff <= B_ff;
                end
                S2: begin
                    // A > B: subtract B from A
                    A_ff <= A_ff - B_ff;
                    B_ff <= B_ff;
                end
                S3: begin
                    // B > A: subtract A from B
                    A_ff <= A_ff;
                    B_ff <= B_ff - A_ff;
                end
                default: begin
                    A_ff <= A_ff;
                    B_ff <= B_ff;
                end
            endcase
        end
    end

    // Combinational comparison signals
    always_comb begin
        if (controlpath_state == S0) begin
            equal        = (A == B);
            greater_than = (A > B);
        end else begin
            equal        = (A_ff == B_ff);
            greater_than = (A_ff > B_ff);
        end
    end

    // Output register - capture GCD when in S1 (DONE) state
    always_ff @(posedge clk) begin
        if (rst) begin
            OUT <= '0;
        end else begin
            if (controlpath_state == S1) begin
                OUT <= A_ff;
            end
        end
    end

endmodule


// =============================================================================
// GCD Top Module
// =============================================================================
module gcd_top #(
    parameter int WIDTH = 4
) (
    input  logic              clk,
    input  logic              rst,
    input  logic [WIDTH-1:0]  A,
    input  logic [WIDTH-1:0]  B,
    input  logic              go,
    output logic [WIDTH-1:0]  OUT,
    output logic              done
);

    // Internal signals connecting controlpath and datapath
    logic [1:0] controlpath_state;
    logic       equal;
    logic       greater_than;

    // Instantiate Control Path
    gcd_controlpath u_gcd_controlpath (
        .clk               (clk),
        .rst               (rst),
        .go                (go),
        .equal             (equal),
        .greater_than      (greater_than),
        .controlpath_state (controlpath_state),
        .done              (done)
    );

    // Instantiate Datapath
    gcd_datapath #(
        .WIDTH (WIDTH)
    ) u_gcd_datapath (
        .clk               (clk),
        .rst               (rst),
        .A                 (A),
        .B                 (B),
        .controlpath_state (controlpath_state),
        .OUT               (OUT),
        .equal             (equal),
        .greater_than      (greater_than)
    );

endmodule
