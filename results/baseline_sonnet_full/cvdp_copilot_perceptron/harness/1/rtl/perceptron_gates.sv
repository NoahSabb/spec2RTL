// rtl/perceptron_gates.sv

module gate_target (
    input  logic [1:0] gate_select,
    output logic signed [3:0] o_1, o_2, o_3, o_4
);
    always_comb begin
        case (gate_select)
            2'b00: begin // AND Gate
                o_1 = 4'sd1;
                o_2 = -4'sd1;
                o_3 = -4'sd1;
                o_4 = -4'sd1;
            end
            2'b01: begin // OR Gate
                o_1 = 4'sd1;
                o_2 = 4'sd1;
                o_3 = 4'sd1;
                o_4 = -4'sd1;
            end
            2'b10: begin // NAND Gate
                o_1 = 4'sd1;
                o_2 = 4'sd1;
                o_3 = 4'sd1;
                o_4 = -4'sd1;
            end
            2'b11: begin // NOR Gate
                o_1 = 4'sd1;
                o_2 = -4'sd1;
                o_3 = -4'sd1;
                o_4 = -4'sd1;
            end
            default: begin
                o_1 = 4'sd0;
                o_2 = 4'sd0;
                o_3 = 4'sd0;
                o_4 = 4'sd0;
            end
        endcase
    end
endmodule


module perceptron_gates (
    input  logic        clk,
    input  logic        rst_n,
    input  logic signed [3:0] x1,
    input  logic signed [3:0] x2,
    input  logic        learning_rate,
    input  logic signed [3:0] threshold,
    input  logic [1:0]  gate_select,
    
    output logic signed [3:0] percep_w1,
    output logic signed [3:0] percep_w2,
    output logic signed [3:0] percep_bias,
    output logic [3:0]        present_addr,
    output logic              stop,
    output logic [2:0]        input_index,
    output logic signed [3:0] y_in,
    output logic signed [3:0] y,
    output logic signed [3:0] prev_percep_wt_1,
    output logic signed [3:0] prev_percep_wt_2,
    output logic signed [3:0] prev_percep_bias
);

    // Microcode ROM: 6 instructions
    // Each instruction is just an address/action identifier
    // We'll define actions as parameters
    localparam ACTION_INIT        = 4'd0;
    localparam ACTION_COMPUTE     = 4'd1;
    localparam ACTION_SELECT_TGT  = 4'd2;
    localparam ACTION_UPDATE      = 4'd3;
    localparam ACTION_CHECK_CONV  = 4'd4;
    localparam ACTION_NEXT_EPOCH  = 4'd5;

    // Microcode ROM: sequence of 6 actions
    logic [3:0] microcode_rom [0:5];
    initial begin
        microcode_rom[0] = ACTION_INIT;
        microcode_rom[1] = ACTION_COMPUTE;
        microcode_rom[2] = ACTION_SELECT_TGT;
        microcode_rom[3] = ACTION_UPDATE;
        microcode_rom[4] = ACTION_CHECK_CONV;
        microcode_rom[5] = ACTION_NEXT_EPOCH;
    end

    // Gate target outputs
    logic signed [3:0] t1, t2, t3, t4;
    gate_target u_gate_target (
        .gate_select(gate_select),
        .o_1(t1),
        .o_2(t2),
        .o_3(t3),
        .o_4(t4)
    );

    // Internal registers
    logic signed [3:0] target;
    logic signed [3:0] wt1_update, wt2_update, bias_update;
    logic signed [3:0] percep_wt1, percep_wt2, percep_b;
    logic signed [7:0] y_in_full;
    
    // Address register
    logic [3:0] addr_reg;
    logic [3:0] current_action;
    
    assign present_addr = addr_reg;
    assign current_action = microcode_rom[addr_reg];

    // Sequential address update
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            addr_reg <= 4'd0;
        end else begin
            if (!stop) begin
                if (addr_reg == 4'd5)
                    addr_reg <= 4'd1; // After NEXT_EPOCH, go back to COMPUTE
                else
                    addr_reg <= addr_reg + 4'd1;
            end
        end
    end

    // Main datapath
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            percep_w1        <= 4'sd0;
            percep_w2        <= 4'sd0;
            percep_bias      <= 4'sd0;
            percep_wt1       <= 4'sd0;
            percep_wt2       <= 4'sd0;
            percep_b         <= 4'sd0;
            y_in             <= 4'sd0;
            y                <= 4'sd0;
            target           <= 4'sd0;
            wt1_update       <= 4'sd0;
            wt2_update       <= 4'sd0;
            bias_update      <= 4'sd0;
            prev_percep_wt_1 <= 4'sd0;
            prev_percep_wt_2 <= 4'sd0;
            prev_percep_bias <= 4'sd0;
            input_index      <= 3'd0;
            stop             <= 1'b0;
        end else begin
            if (!stop) begin
                case (current_action)
                    ACTION_INIT: begin
                        // Initialize weights and bias to zero
                        percep_w1        <= 4'sd0;
                        percep_w2        <= 4'sd0;
                        percep_bias      <= 4'sd0;
                        percep_wt1       <= 4'sd0;
                        percep_wt2       <= 4'sd0;
                        percep_b         <= 4'sd0;
                        wt1_update       <= 4'sd0;
                        wt2_update       <= 4'sd0;
                        bias_update      <= 4'sd0;
                        prev_percep_wt_1 <= 4'sd0;
                        prev_percep_wt_2 <= 4'sd0;
                        prev_percep_bias <= 4'sd0;
                        input_index      <= 3'd0;
                        y_in             <= 4'sd0;
                        y                <= 4'sd0;
                        target           <= 4'sd0;
                    end
                    
                    ACTION_COMPUTE: begin
                        // Compute y_in = bias + x1*w1 + x2*w2
                        y_in_full = {{4{percep_w1[3]}}, percep_w1} + 
                                    (x1 * percep_w1) + 
                                    (x2 * percep_w2) + 
                                    {{4{percep_bias[3]}}, percep_bias};
                        // Simplified: y_in = bias + x1*w1 + x2*w2
                        y_in <= percep_bias + (x1 * percep_w1) + (x2 * percep_w2);
                        
                        // Compute y based on threshold
                        begin
                            logic signed [3:0] computed_yin;
                            computed_yin = percep_bias + (x1 * percep_w1) + (x2 * percep_w2);
                            if (computed_yin > threshold)
                                y <= 4'sd1;
                            else if (computed_yin < -threshold)
                                y <= -4'sd1;
                            else
                                y <= 4'sd0;
                        end
                    end
                    
                    ACTION_SELECT_TGT: begin
                        // Select target based on input_index and gate_select
                        case (input_index)
                            3'd0: target <= t1;
                            3'd1: target <= t2;
                            3'd2: target <= t3;
                            3'd3: target <= t4;
                            default: target <= 4'sd0;
                        endcase
                    end
                    
                    ACTION_UPDATE: begin
                        // Update weights and bias if y != target
                        if (y != target) begin
                            wt1_update  <= learning_rate ? x1 * target : 4'sd0;
                            wt2_update  <= learning_rate ? x2 * target : 4'sd0;
                            bias_update <= learning_rate ? target : 4'sd0;
                        end else begin
                            wt1_update  <= 4'sd0;
                            wt2_update  <= 4'sd0;
                            bias_update <= 4'sd0;
                        end
                        
                        // Apply updates
                        begin
                            logic signed [3:0] wu1, wu2, bu;
                            if (y != target) begin
                                wu1 = learning_rate ? x1 * target : 4'sd0;
                                wu2 = learning_rate ? x2 * target : 4'sd0;
                                bu  = learning_rate ? target : 4'sd0;
                            end else begin
                                wu1 = 4'sd0;
                                wu2 = 4'sd0;
                                bu  = 4'sd0;
                            end
                            percep_w1   <= percep_w1   + wu1;
                            percep_w2   <= percep_w2   + wu2;
                            percep_bias <= percep_bias + bu;
                        end
                    end
                    
                    ACTION_CHECK_CONV: begin
                        // Check convergence: compare current updates with previous
                        if ((wt1_update == prev_percep_wt_1) &&
                            (wt2_update == prev_percep_wt_2) &&
                            (bias_update == prev_percep_bias)) begin
                            // Check if we've gone through all inputs
                            if (input_index == 3'd3) begin
                                stop <= 1'b1;
                            end
                        end else begin
                            // Not converged, update previous values
                            prev_percep_wt_1 <= wt1_update;
                            prev_percep_wt_2 <= wt2_update;
                            prev_percep_bias <= bias_update;
                        end
                    end
                    
                    ACTION_NEXT_EPOCH: begin
                        // Increment input index and prepare for next iteration
                        if (input_index == 3'd3) begin
                            input_index <= 3'd0;
                            // Reset previous updates for new epoch tracking
                            prev_percep_wt_1 <= 4'sd0;
                            prev_percep_wt_2 <= 4'sd0;
                            prev_percep_bias <= 4'sd0;
                        end else begin
                            input_index <= input_index + 3'd1;
                        end
                    end
                    
                    default: begin
                        // Do nothing
                    end
                endcase
            end
        end
    end

endmodule
