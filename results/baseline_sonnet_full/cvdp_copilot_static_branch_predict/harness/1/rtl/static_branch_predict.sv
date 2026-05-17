// Static Branch Predictor Module
// Predicts whether a branch or jump instruction will be taken based on the instruction encoding.

module static_branch_predict (
    input  logic [31:0] fetch_rdata_i,       // Fetched instruction data
    input  logic [31:0] fetch_pc_i,          // Program counter of the fetched instruction
    input  logic        fetch_valid_i,       // Validity of the fetched instruction (active HIGH)

    output logic        predict_branch_taken_o, // Predicted branch taken (active HIGH)
    output logic [31:0] predict_branch_pc_o     // Predicted target address
);

    // Localparams for opcodes
    localparam OPCODE_BRANCH = 7'h63;
    localparam OPCODE_JAL    = 7'h6F;
    localparam OPCODE_JALR   = 7'h67;

    // Alias for the input instruction
    logic [31:0] instr;
    assign instr = fetch_rdata_i;

    // Immediate values
    logic [31:0] imm_j_type;   // Sign-extended immediate for JAL (uncompressed)
    logic [31:0] imm_b_type;   // Sign-extended immediate for Branch (uncompressed)
    logic [31:0] imm_cj_type;  // Sign-extended immediate for compressed jump (C.J/C.JAL)
    logic [31:0] imm_cb_type;  // Sign-extended immediate for compressed branch (C.BEQZ/C.BNEZ)
    logic [31:0] branch_imm;   // Selected immediate based on instruction type

    // Instruction type signals
    logic instr_j;    // Uncompressed JAL or JALR
    logic instr_b;    // Uncompressed branch (BXXX)
    logic instr_cj;   // Compressed jump (C.J / C.JAL) in uncompressed form
    logic instr_cb;   // Compressed branch (C.BEQZ / C.BNEZ) in uncompressed form
    logic instr_b_taken; // Indicates if branch offset is negative (branch predicted taken)

    // -------------------------------------------------------------------------
    // Immediate Extraction and Sign Extension
    // -------------------------------------------------------------------------

    // JAL immediate: {instr[31], instr[19:12], instr[20], instr[30:21], 1'b0}
    assign imm_j_type = {{12{instr[31]}}, instr[19:12], instr[20], instr[30:21], 1'b0};

    // Branch immediate: {instr[31], instr[7], instr[30:25], instr[11:8], 1'b0}
    assign imm_b_type = {{19{instr[31]}}, instr[31], instr[7], instr[30:25], instr[11:8], 1'b0};

    // Compressed jump immediate (C.J/C.JAL converted to uncompressed JAL format)
    // The uncompressed equivalent has the same opcode as JAL (7'h6F)
    // but with a specific encoding in bits [31:7].
    // The immediate is reconstructed from the uncompressed JAL encoding:
    // imm_j_type already handles this since the decompressor produces a JAL-equivalent instruction.
    // For C.J/C.JAL, after decompression, the instruction follows the JAL format.
    // We use imm_j_type for both JAL and C.J/C.JAL.
    assign imm_cj_type = {{12{instr[31]}}, instr[19:12], instr[20], instr[30:21], 1'b0};

    // Compressed branch immediate (C.BEQZ/C.BNEZ converted to uncompressed BXXX format)
    // After decompression, the instruction follows the branch format.
    // We use imm_b_type for both BXXX and C.BEQZ/C.BNEZ.
    assign imm_cb_type = {{19{instr[31]}}, instr[31], instr[7], instr[30:25], instr[11:8], 1'b0};

    // -------------------------------------------------------------------------
    // Instruction Type Decoding
    // -------------------------------------------------------------------------

    // Uncompressed JAL or JALR detection
    // instr_j: opcode is JAL or JALR
    assign instr_j = fetch_valid_i & 
                     ((instr[6:0] == OPCODE_JAL) | (instr[6:0] == OPCODE_JALR));

    // Uncompressed branch detection (BXXX)
    // instr_b: opcode is BRANCH
    // We differentiate from compressed branches by checking that it's not a compressed instruction
    // and that bit[7] pattern matches.
    // For uncompressed branch: opcode = 7'h63, instr[1:0] = 2'b11
    assign instr_b = fetch_valid_i & 
                     (instr[6:0] == OPCODE_BRANCH) &
                     (instr[14] == 1'b0); // func3[2] = 0 means uncompressed (beq, bne, blt, bltu variants)
                                          // Actually, we need a better discriminator

    // -------------------------------------------------------------------------
    // Better discrimination between uncompressed and compressed instructions:
    // 
    // After decompression:
    // - C.J / C.JAL => JAL (opcode 7'h6F), with instr[7] = ~instr_c[15]
    //   - C.J (func3=101, rd=x0): instr[7] = ~0 = 1 -> instr[11:7] = 5'b00001 (rd=x0 but bit7=1?)
    //     Wait, let me re-read the encoding.
    //
    // From the spec, the uncompressed equivalent of C.J/C.JAL:
    // bit[7] = ~instr_c[15]
    // C.J: func3=101 => instr_c[15]=1 => instr[7] = ~1 = 0
    // C.JAL: func3=001 => instr_c[15]=0 => instr[7] = ~0 = 1
    //
    // For standard JAL: rd is in bits[11:7], which could have any value including 0 or 1 in bit[7].
    //
    // The key differentiator for compressed vs uncompressed in their decompressed form:
    // Looking at bits [11:8]:
    // - Compressed jump (C.J/C.JAL decompressed): instr[11:8] = 4'b0000
    // - Standard JAL: instr[11:8] = rd[4:1], which is part of the destination register
    //
    // For compressed branch (C.BEQZ/C.BNEZ decompressed):
    // instr[19:18] = 2'b01 (from the encoding table: bits[19:18] = 2'b01)
    // instr[17:15] = rs1' (3-bit register from compressed encoding, mapped to x8-x15)
    // instr[14:13] = 2'b00
    //
    // For standard branch: 
    // instr[19:15] = rs1 (5-bit register), instr[14:12] = func3
    //
    // The discriminator: 
    // Compressed branch decompressed has instr[14:13] = 2'b00 and instr[19:18] = 2'b01
    // 
    // Let me use the approach: identify compressed instructions by checking specific bit patterns
    // that differ from standard encodings.
    //
    // For C.J/C.JAL (decompressed to JAL):
    //   rd field [11:7]: 
    //     C.JAL: rd = x1 (5'b00001), so instr[11:8] = 4'b0000, instr[7] = 1
    //     C.J:   rd = x0 (5'b00000), so instr[11:8] = 4'b0000, instr[7] = 0
    //   So both C.J and C.JAL have instr[11:8] = 4'b0000
    //   Standard JAL can also have rd=x0 or rd=x1, so instr[11:8] could also be 4'b0000.
    //
    // Actually, looking more carefully at the decompressed C.J/C.JAL encoding:
    // instr[20:12] = {9{instr_c[12]}} which is the sign extension portion
    // This maps to imm[19:11] in the JAL format.
    // 
    // The key insight from the spec is that we should detect compressed vs uncompressed
    // based on the specific bit patterns defined in the decompressed format.
    //
    // For C.BEQZ/C.BNEZ decompressed:
    // - instr[24:20] = 5'b00000 (rs2 = x0)
    // - instr[19:18] = 2'b01
    // This means rs1[4:3] = 2'b01, which forces rs1 to be in range x8-x15.
    // Standard branches can have any rs1, so we can use instr[19:18] = 2'b01 AND 
    // instr[24:20] = 5'b00000 to identify decompressed C.BEQZ/C.BNEZ.
    //
    // For standard BXXX:
    // - rs2 = instr[24:20] can be anything, rs1 = instr[19:15] can be anything
    // - But we need to exclude the case where rs2=0 AND rs1[4:3]=01 (which is decompressed C.BXX)
    //
    // -------------------------------------------------------------------------

    // -------------------------------------------------------------------------
    // Redefine instruction type signals with better discrimination
    // -------------------------------------------------------------------------

    // Compressed jump (C.J / C.JAL) decompressed to JAL format:
    // opcode = 7'h6F AND instr[11:8] = 4'b0000
    // (rd is either x0 for C.J or x1 for C.JAL, both have rd[4:1] = 4'b0000)
    assign instr_cj = fetch_valid_i &
                      (instr[6:0] == OPCODE_JAL) &
                      (instr[11:8] == 4'b0000);

    // Compressed branch (C.BEQZ / C.BNEZ) decompressed to branch format:
    // opcode = 7'h63 AND rs2 = 5'b00000 AND rs1[4:3] = 2'b01
    assign instr_cb = fetch_valid_i &
                      (instr[6:0] == OPCODE_BRANCH) &
                      (instr[24:20] == 5'b00000) &
                      (instr[19:18] == 2'b01);

    // Uncompressed JAL: opcode = 7'h6F AND NOT compressed jump pattern
    // Uncompressed JALR: opcode = 7'h67
    assign instr_j = fetch_valid_i &
                     (((instr[6:0] == OPCODE_JAL) & ~(instr[11:8] == 4'b0000)) |
                      (instr[6:0] == OPCODE_JALR));

    // Uncompressed branch: opcode = 7'h63 AND NOT compressed branch pattern
    assign instr_b = fetch_valid_i &
                     (instr[6:0] == OPCODE_BRANCH) &
                     ~((instr[24:20] == 5'b00000) & (instr[19:18] == 2'b01));

    // -------------------------------------------------------------------------
    // Branch taken prediction
    // For branch instructions, predict taken if the offset is negative (sign bit = 1)
    // -------------------------------------------------------------------------
    // The sign bit for branch immediate is instr[31]
    assign instr_b_taken = instr[31];

    // -------------------------------------------------------------------------
    // Branch immediate selection
    // -------------------------------------------------------------------------
    always_comb begin
        if (instr_j) begin
            branch_imm = imm_j_type;
        end else if (instr_cj) begin
            branch_imm = imm_cj_type;
        end else if (instr_b) begin
            branch_imm = imm_b_type;
        end else if (instr_cb) begin
            branch_imm = imm_cb_type;
        end else begin
            branch_imm = 32'h0;
        end
    end

    // -------------------------------------------------------------------------
    // Output prediction logic
    // -------------------------------------------------------------------------
    assign predict_branch_taken_o = (instr_j | instr_cj) ? 1'b1 :
                                    (instr_b | instr_cb)  ? instr_b_taken :
                                    1'b0;

    assign predict_branch_pc_o = fetch_pc_i + branch_imm;

endmodule
