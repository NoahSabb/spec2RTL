// rtl/hebb_gates.sv

// Gate target submodule
module gate_target (
    input  logic signed [3:0] a,
    input  logic signed [3:0] b,
    input  logic [1:0] gate_select,
    output logic signed [3:0] target
);
    always_comb begin
        case (gate_select)
            2'b00: begin // AND gate
                if (a == 4'sb0001 && b == 4'sb0001)
                    target = 4'sb0001;
                else
                    target = 4'sbffff; // -1
            end
            2'b01: begin // OR gate
                if (a == 4'sbffff && b == 4'sbffff)
                    target = 4'sbffff; // -1
                else
                    target = 4'sb0001;
            end
            2'b10: begin // NAND gate
                if (a == 4'sb0001 && b == 4'sb0001)
                    target = 4'sbffff; // -1
                else
                    target = 4'sb0001;
            end
            2'b11: begin // NOR gate
                if (a == 4'sbffff && b == 4'sbffff)
                    target = 4'sb0001;
                else
                    target = 4'sbffff; // -1
            end
            default: target = 4'sb0000;
        endcase
    end
endmodule

// Main Hebbian rule module
module hebbian_rule (
    input  logic        clk,
    input  logic        rst,
    input  logic        start,
    input  logic signed [3:0] a,
    input  logic signed [3:0] b,
    input  logic [1:0]  gate_select,
    output logic signed [3:0] w1,
    output logic signed [3:0] w2,
    output logic signed [3:0] bias,
    output logic [3:0]  present_state,
    output logic [3:0]  next_state
);

    // State encoding
    localparam [3:0] 
        State_0  = 4'd0,
        State_1  = 4'd1,
        State_2  = 4'd2,
        State_3  = 4'd3,
        State_4  = 4'd4,
        State_5  = 4'd5,
        State_6  = 4'd6,
        State_7  = 4'd7,
        State_8  = 4'd8,
        State_9  = 4'd9,
        State_10 = 4'd10;

    // Internal registers
    logic signed [3:0] x1, x2;
    logic signed [3:0] target;
    logic signed [3:0] delta_w1, delta_w2, delta_b;
    logic [1:0]        iter; // iteration counter for 4 input combinations
    
    // Training input combinations (bipolar: 1 and -1)
    // Combinations: (1,1), (1,-1), (-1,1), (-1,-1)
    logic signed [3:0] train_a [0:3];
    logic signed [3:0] train_b [0:3];
    
    // Gate target instance
    logic signed [3:0] gt_target;
    logic signed [3:0] gt_a, gt_b;
    
    gate_target gt_inst (
        .a(gt_a),
        .b(gt_b),
        .gate_select(gate_select),
        .target(gt_target)
    );

    // Training vectors
    always_comb begin
        train_a[0] = 4'sb0001;  //  1
        train_a[1] = 4'sb0001;  //  1
        train_a[2] = 4'sbffff;  // -1
        train_a[3] = 4'sbffff;  // -1
        
        train_b[0] = 4'sb0001;  //  1
        train_b[1] = 4'sbffff;  // -1
        train_b[2] = 4'sb0001;  //  1
        train_b[3] = 4'sbffff;  // -1
    end

    // Gate target inputs selection based on iteration
    always_comb begin
        if (present_state == State_2 || present_state == State_3 ||
            present_state == State_4 || present_state == State_5 ||
            present_state == State_6) begin
            gt_a = train_a[iter];
            gt_b = train_b[iter];
        end else begin
            gt_a = a;
            gt_b = b;
        end
    end

    // FSM present state register
    always_ff @(posedge clk or negedge rst) begin
        if (!rst) begin
            present_state <= State_0;
            iter <= 2'd0;
            w1   <= 4'sb0000;
            w2   <= 4'sb0000;
            bias <= 4'sb0000;
            x1   <= 4'sb0000;
            x2   <= 4'sb0000;
            target <= 4'sb0000;
            delta_w1 <= 4'sb0000;
            delta_w2 <= 4'sb0000;
            delta_b  <= 4'sb0000;
        end else begin
            present_state <= next_state;
            
            case (present_state)
                State_0: begin
                    // Initialize weights and bias
                    w1   <= 4'sb0000;
                    w2   <= 4'sb0000;
                    bias <= 4'sb0000;
                    iter <= 2'd0;
                end
                
                State_1: begin
                    // Capture inputs for current iteration
                    x1 <= train_a[iter];
                    x2 <= train_b[iter];
                end
                
                State_2: begin
                    // Compute target using gate_target module
                    target <= gt_target;
                end
                
                State_3: begin
                    // Additional target assignment step
                    target <= gt_target;
                end
                
                State_4: begin
                    target <= gt_target;
                end
                
                State_5: begin
                    target <= gt_target;
                end
                
                State_6: begin
                    target <= gt_target;
                end
                
                State_7: begin
                    // Compute deltas
                    delta_w1 <= x1 * target;
                    delta_w2 <= x2 * target;
                    delta_b  <= target;
                end
                
                State_8: begin
                    // Update weights and bias
                    w1   <= w1 + delta_w1;
                    w2   <= w2 + delta_w2;
                    bias <= bias + delta_b;
                end
                
                State_9: begin
                    // Increment iteration counter
                    iter <= iter + 2'd1;
                end
                
                State_10: begin
                    // Training complete, stay or reset
                    iter <= 2'd0;
                end
                
                default: begin
                    // do nothing
                end
            endcase
        end
    end

    // Next state logic (Moore FSM)
    always_comb begin
        case (present_state)
            State_0: begin
                if (start)
                    next_state = State_1;
                else
                    next_state = State_0;
            end
            
            State_1: begin
                next_state = State_2;
            end
            
            State_2: begin
                next_state = State_3;
            end
            
            State_3: begin
                next_state = State_4;
            end
            
            State_4: begin
                next_state = State_5;
            end
            
            State_5: begin
                next_state = State_6;
            end
            
            State_6: begin
                next_state = State_7;
            end
            
            State_7: begin
                next_state = State_8;
            end
            
            State_8: begin
                next_state = State_9;
            end
            
            State_9: begin
                // Check if we've processed all 4 input combinations
                if (iter == 2'd3)
                    next_state = State_10;
                else
                    next_state = State_1;
            end
            
            State_10: begin
                next_state = State_0;
            end
            
            default: begin
                next_state = State_0;
            end
        endcase
    end

endmodule
