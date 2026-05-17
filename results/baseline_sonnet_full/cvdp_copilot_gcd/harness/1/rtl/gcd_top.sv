// GCD Control Path Module
module gcd_controlpath #(
    parameter WIDTH = 4
)(
    input  logic        clk,
    input  logic        rst,
    input  logic        go,
    input  logic        equal,
    input  logic        greater_than,
    output logic [1:0]  controlpath_state,
    output logic        done
);

    // State encoding
    localparam S0 = 2'b00; // IDLE
    localparam S1 = 2'b01; // DONE
    localparam S2 = 2'b10; // A > B
    localparam S3 = 2'b11; // B > A

    logic [1:0] state, next_state;

    // State register
    always_ff @(posedge clk) begin
        if (rst) begin
            state <= S0;
        end else begin
            state <= next_state;
        end
    end

    // Next state logic
    always_comb begin
        case (state)
            S0: begin
                if (go) begin
                    if (equal)
                        next_state = S1;
                    else if (greater_than)
                        next_state = S2;
                    else
                        next_state = S3;
                end else begin
                    next_state = S0;
                end
            end
            S1: begin
                next_state = S0;
            end
            S2: begin
                if (equal)
                    next_state = S1;
                else if (greater_than)
                    next_state = S2;
                else
                    next_state = S3;
            end
            S3: begin
                if (equal)
                    next_state = S1;
                else if (greater_than)
                    next_state = S2;
                else
                    next_state = S3;
            end
            default: begin
                next_state = S0;
            end
        endcase
    end

    // Output logic - synchronized to positive edge of clock
    always_ff @(posedge clk) begin
        if (rst) begin
            controlpath_state <= S0;
            done              <= 1'b0;
        end else begin
            controlpath_state <= next_state;
            done              <= (next_state == S1) ? 1'b1 : 1'b0;
        end
    end

endmodule


// GCD Datapath Module
module gcd_datapath #(
    parameter WIDTH = 4
)(
    input  logic              clk,
    input  logic              rst,
    input  logic [WIDTH-1:0]  A,
    input  logic [WIDTH-1:0]  B,
    input  logic [1:0]        controlpath_state,
    output logic [WIDTH-1:0]  OUT,
    output logic              equal,
    output logic              greater_than
);

    // State encoding (matching controlpath)
    localparam S0 = 2'b00;
    localparam S1 = 2'b01;
    localparam S2 = 2'b10;
    localparam S3 = 2'b11;

    logic [WIDTH-1:0] A_ff, B_ff;

    // Comparison logic
    // In S0 state, use input A and B directly
    // In other states, use registered A_ff and B_ff
    always_comb begin
        if (controlpath_state == S0) begin
            equal        = (A == B);
            greater_than = (A > B);
        end else begin
            equal        = (A_ff == B_ff);
            greater_than = (A_ff > B_ff);
        end
    end

    // Datapath register updates and output
    always_ff @(posedge clk) begin
        if (rst) begin
            A_ff <= '0;
            B_ff <= '0;
            OUT  <= '0;
        end else begin
            case (controlpath_state)
                S0: begin
                    // Latch inputs when in IDLE (go will have been asserted)
                    A_ff <= A;
                    B_ff <= B;
                end
                S1: begin
                    // Computation complete, output the GCD
                    OUT <= A_ff;
                end
                S2: begin
                    // A > B: subtract B from A
                    A_ff <= A_ff - B_ff;
                end
                S3: begin
                    // B > A: subtract A from B
                    B_ff <= B_ff - A_ff;
                end
                default: begin
                    A_ff <= A_ff;
                    B_ff <= B_ff;
                end
            endcase
        end
    end

endmodule


// GCD Top Module
module gcd_top #(
    parameter WIDTH = 4
)(
    input  logic              clk,
    input  logic              rst,
    input  logic [WIDTH-1:0]  A,
    input  logic [WIDTH-1:0]  B,
    input  logic              go,
    output logic [WIDTH-1:0]  OUT,
    output logic              done
);

    logic [1:0] controlpath_state;
    logic       equal;
    logic       greater_than;

    // Instantiate control path
    gcd_controlpath #(
        .WIDTH(WIDTH)
    ) u_controlpath (
        .clk               (clk),
        .rst               (rst),
        .go                (go),
        .equal             (equal),
        .greater_than      (greater_than),
        .controlpath_state (controlpath_state),
        .done              (done)
    );

    // Instantiate datapath
    gcd_datapath #(
        .WIDTH(WIDTH)
    ) u_datapath (
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
