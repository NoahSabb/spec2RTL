module gcd_top #(parameter WIDTH = 4)(
    input  logic             clk, rst,
    input  logic [WIDTH-1:0] A, B,
    input  logic             go,
    output logic [WIDTH-1:0] OUT,
    output logic             done
);
    logic [1:0] controlpath_state;
    logic       equal, greater_than;

    gcd_controlpath #(.WIDTH(WIDTH)) controlpath (
        .clk(clk), .rst(rst), .go(go), .equal(equal), .greater_than(greater_than),
        .controlpath_state(controlpath_state), .done(done));

    gcd_datapath #(.WIDTH(WIDTH)) datapath (
        .clk(clk), .rst(rst), .A(A), .B(B),
        .controlpath_state(controlpath_state),
        .OUT(OUT), .equal(equal), .greater_than(greater_than));
endmodule

module gcd_controlpath #(parameter WIDTH = 4)(
    input  logic       clk, rst, go, equal, greater_than,
    output logic [1:0] controlpath_state,
    output logic       done
);
    localparam IDLE=2'b00, DONE=2'b01, A_GT_B=2'b10, B_GT_A=2'b11;
    logic [1:0] current_state, next_state;

    always_comb begin
        case (current_state)
            IDLE:   next_state = go ? (equal ? DONE : (greater_than ? A_GT_B : B_GT_A)) : IDLE;
            DONE:   next_state = IDLE;
            A_GT_B: next_state = equal ? DONE : (greater_than ? A_GT_B : B_GT_A);
            B_GT_A: next_state = equal ? DONE : (greater_than ? A_GT_B : B_GT_A);
            default: next_state = IDLE;
        endcase
    end

    always_ff @(posedge clk) begin
        if (rst) begin
            current_state <= IDLE;
            done <= 1'b0;
        end else begin
            current_state <= next_state;
            done <= (next_state == DONE);
        end
    end

    assign controlpath_state = current_state;
endmodule

module gcd_datapath #(parameter WIDTH = 4)(
    input  logic             clk, rst,
    input  logic [WIDTH-1:0] A, B,
    input  logic [1:0]       controlpath_state,
    output logic [WIDTH-1:0] OUT,
    output logic             equal, greater_than
);
    logic [WIDTH-1:0] A_ff, B_ff;

    assign equal        = (A_ff == B_ff);
    assign greater_than = (A_ff  > B_ff);
    assign OUT = A_ff;

    always_ff @(posedge clk) begin
        if (rst) begin
            A_ff <= '0;
            B_ff <= '0;
        end else case (controlpath_state)
            2'b00: begin A_ff <= A;    B_ff <= B;    end  // IDLE: pre-load inputs
            2'b01: begin A_ff <= A_ff; B_ff <= B_ff; end  // DONE: hold
            2'b10: begin A_ff <= A_ff - B_ff; B_ff <= B_ff; end  // A > B
            2'b11: begin A_ff <= A_ff; B_ff <= B_ff - A_ff; end  // B > A
            default: begin A_ff <= A_ff; B_ff <= B_ff; end
        endcase
    end
endmodule
