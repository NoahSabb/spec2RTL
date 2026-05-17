```systemverilog
// rtl/microcode_sequencer.sv

// ============================================================
// Stack Pointer Submodule
// ============================================================
module stack_pointer (
    input  logic       clk,
    input  logic       rst,
    input  logic       push,
    input  logic       pop,
    output logic [4:0] stack_addr,
    output logic       full,
    output logic       empty
);
    logic [4:0] sp_reg;

    assign stack_addr = sp_reg;
    assign full  = (sp_reg == 5'd16);
    assign empty = (sp_reg == 5'd0);

    always_ff @(posedge clk) begin
        if (rst) begin
            sp_reg <= 5'b00000;
        end else if (push && !full) begin
            sp_reg <= sp_reg + 5'd1;
        end else if (pop && !empty) begin
            sp_reg <= sp_reg - 5'd1;
        end
    end
endmodule

// ============================================================
// Stack RAM Submodule
// ============================================================
module stack_ram (
    input  logic       clk,
    input  logic [4:0] stack_addr,
    input  logic [3:0] stack_data_in,
    input  logic       stack_we,
    input  logic       stack_re,
    output logic [3:0] stack_data_out
);
    logic [3:0] mem [0:31];

    always_ff @(posedge clk) begin
        if (stack_we) begin
            mem[stack_addr] <= stack_data_in;
        end
        if (stack_re) begin
            stack_data_out <= mem[stack_addr];
        end
    end
endmodule

// ============================================================
// Stack Data Mux Submodule
// ============================================================
module stack_data_mux (
    input  logic [3:0] data_in,
    input  logic [3:0] pc_in,
    input  logic       stack_mux_sel,
    output logic [3:0] stack_mux_out
);
    // stack_mux_sel == 1: data_in selected
    // stack_mux_sel == 0: pc_in selected
    assign stack_mux_out = stack_mux_sel ? data_in : pc_in;
endmodule

// ============================================================
// LIFO Stack Module
// ============================================================
module lifo_stack (
    input  logic       clk,
    input  logic [3:0] stack_data1_in,
    input  logic [3:0] stack_data2_in,
    input  logic       stack_reset,
    input  logic       stack_push,
    input  logic       stack_pop,
    input  logic       stack_mux_sel,
    input  logic       stack_we,
    input  logic       stack_re,
    output logic [3:0] stack_data_out,
    output logic       full_o,
    output logic       empty_o
);
    logic [4:0] stack_addr;
    logic [3:0] mux_out;

    stack_data_mux u_stack_mux (
        .data_in      (stack_data1_in),
        .pc_in        (stack_data2_in),
        .stack_mux_sel(stack_mux_sel),
        .stack_mux_out(mux_out)
    );

    stack_pointer u_sp (
        .clk       (clk),
        .rst       (stack_reset),
        .push      (stack_push),
        .pop       (stack_pop),
        .stack_addr(stack_addr),
        .full      (full_o),
        .empty     (empty_o)
    );

    stack_ram u_sram (
        .clk           (clk),
        .stack_addr    (stack_addr),
        .stack_data_in (mux_out),
        .stack_we      (stack_we),
        .stack_re      (stack_re),
        .stack_data_out(stack_data_out)
    );
endmodule

// ============================================================
// PC Mux Submodule
// ============================================================
module pc_mux (
    input  logic [3:0] full_adder_data,
    input  logic [3:0] pc_data,
    input  logic       pc_mux_sel,
    output logic [3:0] pc_mux_out
);
    // pc_mux_sel == 1: full_adder_data selected
    // pc_mux_sel == 0: pc_data selected
    assign pc_mux_out = pc_mux_sel ? full_adder_data : pc_data;
endmodule

// ============================================================
// PC Incrementer Submodule
// ============================================================
module pc_incrementer (
    input  logic       pc_c_in,
    input  logic       inc,
    input  logic [3:0] pc_data_in,
    output logic [3:0] pc_inc_out,
    output logic       pc_c_out
);
    logic [4:0] sum;
    always_comb begin
        if (inc) begin
            sum = {1'b0, pc_data_in} + {4'b0000, pc_c_in};
        end else begin
            sum = {1'b0, pc_data_in};
        end
        pc_inc_out = sum[3:0];
        pc_c_out   = sum[4];
    end
endmodule

// ============================================================
// PC Register Submodule
// ============================================================
module pc_reg (
    input  logic       clk,
    input  logic [3:0] pc_data_in,
    output logic [3:0] pc_data_out
);
    always_ff @(posedge clk) begin
        pc_data_out <= pc_data_in;
    end
endmodule

// ============================================================
// Program Counter Module
// ============================================================
module program_counter (
    input  logic       clk,
    input  logic [3:0] full_adder_data_i,
    input  logic       pc_c_in,
    input  logic       inc,
    input  logic       pc_mux_sel,
    output logic [3:0] pc_out,
    output logic       pc_c_out
);
    logic [3:0] mux_out;
    logic [3:0] inc_out;
    logic [3:0] reg_out;

    pc_mux u_pc_mux (
        .full_adder_data(full_adder_data_i),
        .pc_data        (reg_out),
        .pc_mux_sel     (pc_mux_sel),
        .pc_mux_out     (mux_out)
    );

    pc_incrementer u_pc_inc (
        .pc_c_in    (pc_c_in),
        .inc        (inc),
        .pc_data_in (mux_out),
        .pc_inc_out (inc_out),
        .pc_c_out   (pc_c_out)
    );

    pc_reg u_pc_reg (
        .clk        (clk),
        .pc_data_in (inc_out),
        .pc_data_out(reg_out)
    );

    assign pc_out = reg_out;
endmodule

// ============================================================
// Aux Reg Mux Submodule
// ============================================================
module aux_reg_mux (
    input  logic [3:0] reg1_in,
    input  logic [3:0] reg2_in,
    input  logic       rsel,
    input  logic       re,
    output logic [3:0] reg_mux_out
);
    logic sel;
    // sel = rsel AND ~re
    assign sel = rsel & (~re);
    // sel == 1: reg1_in selected
    // sel == 0: reg2_in selected
    assign reg_mux_out = sel ? reg1_in : reg2_in;
endmodule

// ============================================================
// Aux Register Submodule
// ============================================================
module aux_reg (
    input  logic       clk,
    input  logic [3:0] reg_in,
    input  logic       rce,
    input  logic       re,
    output logic [3:0] reg_out
);
    logic enable;
    // enable = rce OR ~re
    assign enable = rce | (~re);

    always_ff @(posedge clk) begin
        if (enable) begin
            reg_out <= reg_in;
        end
    end
endmodule

// ============================================================
// A Mux Submodule
// ============================================================
module a_mux (
    input  logic [3:0] register_data,
    input  logic [3:0] data_in,
    input  logic [1:0] a_mux_sel,
    output logic [3:0] a_mux_out
);
    always_comb begin
        case (a_mux_sel)
            2'b00:   a_mux_out = data_in;
            2'b01:   a_mux_out = register_data;
            2'b10:   a_mux_out = 4'b0000;
            default: a_mux_out = 4'b0000;
        endcase
    end
endmodule

// ============================================================
// B Mux Submodule
// ============================================================
module b_mux (
    input  logic [3:0] register_data,
    input  logic [3:0] stack_data,
    input  logic [3:0] pc_data,
    input  logic [1:0] b_mux_sel,
    output logic [3:0] b_mux_out
);
    always_comb begin
        case (b_mux_sel)
            2'b00:   b_mux_out = pc_data;
            2'b01:   b_mux_out = stack_data;
            2'b10:   b_mux_out = 4'b0000;
            2'b11:   b_mux_out = register_data;
            default: b_mux_out = 4'b0000;
        endcase
    end
endmodule

// ============================================================
// Full Adder Submodule (4-bit ripple carry)
// ============================================================
module full_adder (
    input  logic [3:0] a_in,
    input  logic [3:0] b_in,
    input  logic       c_in,
    input  logic       cen,
    output logic [3:0] c_out
);
    logic [4:0] sum;
    always_comb begin
        if (cen) begin
            sum = {1'b0, a_in} + {1'b0, b_in} + {4'b0000, c_in};
        end else begin
            sum = {1'b0, a_in} + {1'b0, b_in};
        end
        c_out = sum[3:0];
    end
endmodule

// ============================================================
// Microcode Arithmetic Module
// ============================================================
module microcode_arithmetic (
    input  logic       clk,
    input  logic [3:0] fa_in,
    input  logic [3:0] d_in,
    input  logic [3:0] stack_data_in,
    input  logic [3:0] pc_data_in,
    input  logic       reg_en,
    input  logic       oen,
    input  logic       rce,
    input  logic       cen,
    input  logic [1:0] a_mux_sel,
    input  logic [1:0] b_mux_sel,
    input  logic       arith_cin,
    input  logic       oe,
    output logic       arith_cout,
    output logic [3:0] d_out
);
    logic [3:0] reg_mux_out;
    logic [3:0] reg_out;
    logic [3:0] a_out;
    logic [3:0] b_out;
    logic [3:0] fa_out;
    logic [4:0] fa_sum;

    aux_reg_mux u_aux_reg_mux (
        .reg1_in    (fa_in),
        .reg2_in    (d_in),
        .rsel       (rce),
        .re         (reg_en),
        .reg_mux_out(reg_mux_out)
    );

    aux_reg u_aux_reg (
        .clk    (clk),
        .reg_in (reg_mux_out),
        .rce    (rce),
        .re     (reg_en),
        .reg_out(reg_out)
    );

    a_mux u_a_mux (
        .register_data(reg_out),
        .data_in      (d_in),
        .a_mux_sel    (a_mux_sel),
        .a_mux_out    (a_out)
    );

    b_mux u_b_mux (
        .register_data(reg_out),
        .stack_data   (stack_data_in),
        .pc_data      (pc_data_in),
        .b_mux_sel    (b_mux_sel),
        .b_mux_out    (b_out)
    );

    // Ripple carry adder with carry enable
    always_comb begin
        if (cen) begin
            fa_sum = {1'b0, a_out} + {1'b0, b_out} + {4'b0000, arith_cin};
        end else begin
            fa_sum = {1'b0, a_out} + {1'b0, b_out};
        end
        fa_out     = fa_sum[3:0];
        arith_cout = fa_sum[4];
    end

    // Output gating: oe ACTIVE HIGH, oen ACTIVE LOW
    assign d_out = (oe && !oen) ? fa_out : 4'bz;

endmodule

// ============================================================
// Result Register Module
// ============================================================
module result_register (
    input  logic       clk,
    input  logic [3:0] data_in,
    input  logic       out_ce,
    output logic [3:0] data_out
);
    always_ff @(posedge clk) begin
        if (out_ce) begin
            data_out <= data_in;
        end
    end
endmodule

// ============================================================
// Instruction Decoder Module
// ============================================================
module instruction_decoder (
    input  logic [4:0] instr_in,
    input  logic       cc_in,
    input  logic       instr_en,
    output logic       cen,
    output logic       rst,
    output logic       oen,
    output logic       inc,
    output logic       rsel,
    output logic       rce,
    output logic       pc_mux_sel,
    output logic [1:0] a_mux_sel,
    output logic [1:0] b_mux_sel,
    output logic       push,
    output logic       pop,
    output logic       src_sel,
    output logic       stack_we,
    output logic       stack_re,
    output logic       out_ce
);
    always_comb begin
        // Default values
        cen        = 1'b0;
        rst        = 1'b0;
        oen        = 1'b0;
        inc        = 1'b0;
        rsel       = 1'b0;
        rce        = 1'b0;
        pc_mux_sel = 1'b0;
        a_mux_sel  = 2'b10; // default: 4'b0000
        b_mux_sel  = 2'b10; // default: 4'b0000
        push       = 1'b0;
        pop        = 1'b0;
        src_sel    = 1'b0;
        stack