// First-Bit Decoder RTL Module
// Returns the index of the lowest bit set in a vector

module cvdp_copilot_decode_firstbit #(
    parameter int InWidth_g = 32,
    parameter int InReg_g   = 1,
    parameter int OutReg_g  = 1,
    parameter int PlRegs_g  = 1
) (
    input  logic                          Clk,
    input  logic                          Rst,
    input  logic [InWidth_g-1:0]          In_Data,
    input  logic                          In_Valid,
    output logic [$clog2(InWidth_g)-1:0]  Out_FirstBit,
    output logic                          Out_Found,
    output logic                          Out_Valid
);

    // Local parameters
    localparam int BinBits_c   = $clog2(InWidth_g);
    // Round up to nearest power of two
    localparam int PowTwoWidth_c = 2**BinBits_c;

    // -------------------------------------------------------------------------
    // Input Register Stage
    // -------------------------------------------------------------------------
    logic [InWidth_g-1:0] data_in;
    logic                 valid_in;

    generate
        if (InReg_g == 1) begin : gen_in_reg
            always_ff @(posedge Clk or posedge Rst) begin
                if (Rst) begin
                    data_in  <= '0;
                    valid_in <= 1'b0;
                end else begin
                    data_in  <= In_Data;
                    valid_in <= In_Valid;
                end
            end
        end else begin : gen_no_in_reg
            assign data_in  = In_Data;
            assign valid_in = In_Valid;
        end
    endgenerate

    // -------------------------------------------------------------------------
    // Pad input to nearest power of two (set extra bits to 0 so they won't
    // be detected as first set bit)
    // -------------------------------------------------------------------------
    logic [PowTwoWidth_c-1:0] data_padded;
    always_comb begin
        data_padded = '0;
        data_padded[InWidth_g-1:0] = data_in;
    end

    // -------------------------------------------------------------------------
    // Pipeline stages for first-bit detection
    //
    // The detection is split across (PlRegs_g + 1) stages.
    // Each stage handles a portion of the bits.
    //
    // Strategy:
    //   We use a tree-based approach. At each pipeline stage we look at groups
    //   of bits and determine the lowest set bit index, propagating partial
    //   results through the pipeline.
    //
    // For simplicity and correctness across all PlRegs_g values, we implement
    // the following approach:
    //   - Stage 0 through PlRegs_g: we carry along a "remaining mask" and
    //     an "accumulated index" and "found" flag.
    //   - At each registered stage boundary, we resolve some of the bits.
    //
    // Simpler approach: compute the full first-bit result combinatorially,
    // then pipe the valid signal through PlRegs_g registers.
    // The combinatorial result is registered at the output if OutReg_g=1.
    // -------------------------------------------------------------------------

    // Combinatorial first-bit detection on padded data
    logic [BinBits_c-1:0] firstbit_comb;
    logic                  found_comb;

    always_comb begin
        firstbit_comb = '0;
        found_comb    = 1'b0;
        for (int i = PowTwoWidth_c-1; i >= 0; i--) begin
            if (i < InWidth_g && data_padded[i]) begin
                firstbit_comb = BinBits_c'(i);
                found_comb    = 1'b1;
            end
        end
    end

    // Pipeline registers for data (firstbit and found) and valid
    // We have PlRegs_g pipeline stages between input and output register
    // Total latency = InReg_g + PlRegs_g + OutReg_g cycles

    // Pipeline arrays
    logic [BinBits_c-1:0] pl_firstbit [0:PlRegs_g];
    logic                  pl_found    [0:PlRegs_g];
    logic                  pl_valid    [0:PlRegs_g];

    // Stage 0 is directly from combinatorial logic (uses registered input if InReg_g=1)
    assign pl_firstbit[0] = firstbit_comb;
    assign pl_found[0]    = found_comb;
    assign pl_valid[0]    = valid_in;

    // Pipeline stages 1 through PlRegs_g
    generate
        for (genvar s = 1; s <= PlRegs_g; s++) begin : gen_pl_stages
            always_ff @(posedge Clk or posedge Rst) begin
                if (Rst) begin
                    pl_firstbit[s] <= '0;
                    pl_found[s]    <= 1'b0;
                    pl_valid[s]    <= 1'b0;
                end else begin
                    pl_firstbit[s] <= pl_firstbit[s-1];
                    pl_found[s]    <= pl_found[s-1];
                    pl_valid[s]    <= pl_valid[s-1];
                end
            end
        end
    endgenerate

    // -------------------------------------------------------------------------
    // Output Register Stage
    // -------------------------------------------------------------------------
    generate
        if (OutReg_g == 1) begin : gen_out_reg
            always_ff @(posedge Clk or posedge Rst) begin
                if (Rst) begin
                    Out_FirstBit <= '0;
                    Out_Found    <= 1'b0;
                    Out_Valid    <= 1'b0;
                end else begin
                    Out_FirstBit <= pl_firstbit[PlRegs_g];
                    Out_Found    <= pl_found[PlRegs_g];
                    Out_Valid    <= pl_valid[PlRegs_g];
                end
            end
        end else begin : gen_no_out_reg
            assign Out_FirstBit = pl_firstbit[PlRegs_g];
            assign Out_Found    = pl_found[PlRegs_g];
            assign Out_Valid    = pl_valid[PlRegs_g];
        end
    endgenerate

endmodule
