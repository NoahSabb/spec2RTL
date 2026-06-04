module microcode_sequencer (
    input wire clk,
    input wire c_n_in,
    input wire c_inc_in,
    input wire r_en,
    input wire cc,
    input wire ien,
    input wire [3:0] d_in,
    input wire [4:0] instr_in,
    input wire oen,

    output wire [3:0] d_out,
    output wire c_n_out,
    output wire c_inc_out,
    output wire full,
    output wire empty
);

parameter MAX_DEPTH = 8;

reg [3:0] d_out_r;
reg c_n_out_r;
reg c_inc_out_r;
reg full_r;
reg empty_r;

reg [3:0] stack_depth;
reg [3:0] pc_reg;
reg [3:0] aux_reg;

assign d_out = d_out_r;
assign c_n_out = c_n_out_r;
assign c_inc_out = c_inc_out_r;
assign full = full_r;
assign empty = empty_r;

// Combinational block for d_out, c_n_out, c_inc_out
always @(*) begin
    case (instr_in)
        5'b00000: begin // PRST
            d_out_r = 4'b0000;
            c_n_out_r = 0;
            c_inc_out_r = 0;
        end
        5'b00001: begin // Fetch PC
            d_out_r = pc_reg;
            c_n_out_r = 0;
            c_inc_out_r = 0;
        end
        5'b00010: begin // Fetch R
            d_out_r = aux_reg;
            c_n_out_r = 0;
            c_inc_out_r = 0;
        end
        5'b00011: begin // Fetch D
            d_out_r = d_in;
            c_n_out_r = 0;
            c_inc_out_r = 0;
        end
        5'b00100: begin // Fetch R + D
            d_out_r = aux_reg + d_in;
            c_n_out_r = 0;
            c_inc_out_r = 0;
        end
        5'b01011: begin // Push PC
            d_out_r = 4'b1000;
            c_n_out_r = 0;
            c_inc_out_r = 0;
        end
        5'b01110: begin // Pop PC
            d_out_r = 4'b0110;
            c_n_out_r = 0;
            c_inc_out_r = 0;
        end
        default: begin
            d_out_r = 4'b0000;
            c_n_out_r = 0;
            c_inc_out_r = 0;
        end
    endcase
end

// Clocked block for PC register
always @(posedge clk) begin
    if (instr_in == 5'b00000) begin // PRST - reset PC
        if (c_inc_in == 1'b1) begin
            pc_reg <= 4'd1;
        end else begin
            pc_reg <= 4'd0;
        end
    end else if (c_inc_in == 1'b1) begin
        pc_reg <= pc_reg + 4'd1;
    end
end

// Clocked block for auxiliary register
// Only update aux_reg when r_en is active low AND the decoder is disabled (ien==1 or cc==1)
// This prevents aux_reg from being overwritten during active instruction execution
always @(posedge clk) begin
    if (r_en == 1'b0 && (ien == 1'b1 || cc == 1'b1)) begin
        aux_reg <= d_in;
    end
end

// Clocked block for stack depth tracking and full/empty flags
always @(posedge clk) begin
    case (instr_in)
        5'b00000: begin // PRST - reset stack
            stack_depth <= 4'd0;
        end
        5'b01011: begin // Push PC - increment stack depth
            if (stack_depth < MAX_DEPTH) begin
                stack_depth <= stack_depth + 4'd1;
            end
        end
        5'b01110: begin // Pop PC - decrement stack depth
            if (stack_depth > 4'd0) begin
                stack_depth <= stack_depth - 4'd1;
            end
        end
        default: begin
            stack_depth <= stack_depth;
        end
    endcase

    // Update full and empty flags synchronously
    if (instr_in == 5'b00000) begin
        empty_r <= 1'b1;
        full_r  <= 1'b0;
    end else if (instr_in == 5'b01011) begin
        // After push
        if (stack_depth + 4'd1 >= MAX_DEPTH) begin
            full_r  <= 1'b1;
        end else begin
            full_r  <= 1'b0;
        end
        if (stack_depth + 4'd1 == 4'd0) begin
            empty_r <= 1'b1;
        end else begin
            empty_r <= 1'b0;
        end
    end else if (instr_in == 5'b01110) begin
        // After pop
        full_r <= 1'b0;
        if (stack_depth == 4'd0 || stack_depth - 4'd1 == 4'd0) begin
            empty_r <= 1'b1;
        end else begin
            empty_r <= 1'b0;
        end
    end else begin
        empty_r <= (stack_depth == 4'd0);
        full_r  <= (stack_depth >= MAX_DEPTH);
    end
end

// Initialize registers
initial begin
    stack_depth = 4'd0;
    pc_reg = 4'd0;
    aux_reg = 4'd0;
    empty_r = 1'b1;
    full_r  = 1'b0;
end

endmodule
