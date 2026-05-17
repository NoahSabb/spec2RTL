<s> module static_branch_predict(
    input [31:0] fetch_rdata_i,
    input [31:0] fetch_pc_i,
    input fetch_valid_i,
    input [4:0] register_addr_i,
    output reg predict_branch_taken_o,
    output reg [31:0] predict_branch_pc_o
);

// Immediate storage registers
reg [31:0] imm_j_type;
reg [31:0] imm_b_type;
reg [31:0] imm_cj_type;
reg [31:0] imm_cb_type;

// Internal signals (output is always active-high)
wire instr_j       = fetch_rdata_i[31:26] == 7'h6F; // JAL or JALR?
wire instr_cj      = fetch_rdata_i[31:26] == 7'h67;
wire instr_cb      = fetch_rdata_i[31:26] == 7'h63;
wire instr_b       = ~instr_cj & ~instr_j; // uncompressed branch?
wire instr_b_taken = fetch_rdata_i[15];   // negative offset => taken branch?

reg [31:0] branch_imm;

assign predict_branch_pc_o = (instr_cj) ? imm_cj_type : instructed_branch_imm + predict_branch_pc_o;
assign predict_branch_taken_o = (instr_cj) ? 1'b1 : ((instr_b) ? instr_b_taken : 0);
 module static_branch_predict(
    input [31:0] fetch_rdata_i,
    input [31:0] fetch_pc_i,
    input fetch_valid_i,
    input [4:0] register_addr_i,
    output reg predict_branch_taken_o,
    output reg [31:0] predict_branch_pc_o
);

// Compute immediate (offsets can be negative)!
always @(*) begin
    case ({fetch_rdata_i[28], fetch_rdata_i}) // Opcode+Func3
        7'h63: imm_cb_type = {{19{fetch_rdata_i[12]}}, fetch_rdata_i[12:1]}; // C.Bxx, sign-extends 12 bits to 32
        7'h6F: imm_j_type = {fetch_pc_i[4], fetch_rdata_i[15:0], fetch_rdata_i[31:16]}; // JAL, pc+u32
        7'h67: imm_cj_type = {fetch_pc_i[4], fetch_rdata_i[15:0], fetch_rdata_i[31:16]}; // C.J, pc+u32
        default: begin // uncompressed branch (Bxx) or immediate load
            case (fetch_rdata_i[31:4]) // Opcode+Func7
                4'b0000: imm_b_type = {{19{8'hFF}}, fetch_pc_i, fetch_rdata_i}; // Bxx
                6'h110_: imm_b_type = {fetch_pc_i, fetch_rdata_i, 4'd0}; // ILWM.Bxx
                6'h11x_: begin // ILWHM.Bxx
                   case (fetch_op[2])
                        3'b000: imm_b_type = {fetch_pc_i, fetch_rdata_i, 14'h0004};
                        3'b001: imm_b_type = {fetch_pc_i, fetch_rdata_i, 12'hF0FF};
                        3'b010: imm_b_type = {fetch_pc_i, fetch_op[6], fetch_rdata_i[4:0]};
                        3'b011: begin // SLL$imm
                            case (fetch_op[4])
                                2'h0: imm_b_type = {17{fetch_pc_i[0]}, fetch_rdata_i, fetch_op[5], 4'd0};
                                2'h1: imm_b_type = {6'h80, fetch_rdata_i, fetch_op[5], fetch_pc_i};  // SLLV$imm
                                2'h2: imm_b_type = fetch_rdata_i + fetch_pc_i[7:0];
                                default: imm_b_type = {6'h80, fetch_op[5], fetch_rdata_i}; // SLLV$imm
                            endcase
                        end
                        3'b100: begin // SLT$imm
                            case (fetch_op[6])
                                4'b1000: imm_b_type = {24'h7_FFFFFF, fetch_rdata_i}; // SLT$A
                                4'b0100: begin
                                    if (fetch_op[5] == 1) // Destination register
                                        imm_b_type = {32'h87_FFFFFF, fetch_rdata_i};
                                    else
                                        imm_b_type = {32'h07_FFFFFF, fetch_op[5], fetch_rdata_i}; // SLT$R
                                end
                                default: $error("Unsupported SLT immediate form");
                            endcase
                        end
                        3'b101: imm_b_type = {6'h80, fetch_op[5], fetch_rdata_i[5], fetch_pc_i}; // SRL$imm
                        3'b110: imm_b_type = {fetch_pc_i, fetch_rdata_i};  // ADDI.Bxx
                        default: $error("Unsupported Branch Opcode"); // XXX handle ADDA/SUBA/SLLA/SLTA/SRA$imm?
                    endcase
                end
                default: begin // Other branches - or invalid instruction!
                    predict_branch_taken_o <= 1;
                    imm_b_type = {24'h0, fetch_rdata_i};
                end
            endcase
        end
    endcase
end

// Assign input to output. This is necessary for tools that have trouble with blocking assignments.
assign predict_branch_pc_o = (instr_cj) ? imm_cj_type : instructed_branch_imm + fetch_pc_i;
assign branch_imm = (instr_b) ? imm_b_type : (instr_j) ? (7'h100 * fetch_rdata_i[6] + 4'd12 - fetch_pc_i) : imm_cb_type; // Uncompressed JALR, Compressed JAL?
assign predict_branch_taken_o = (instr_cj) ? 1'b0 : ((instr_b_taken) ? 1 : ((fetch_rdata_i[31] - fetch_pc_i [2]) & fetch_rdata_i[35]));
endmodule