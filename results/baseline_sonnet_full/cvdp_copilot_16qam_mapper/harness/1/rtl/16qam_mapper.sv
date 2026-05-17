// rtl/16qam_mapper.sv
// QAM16 Mapper with Interpolation

module qam16_mapper_interpolated #(
    parameter int N         = 4,  // Number of input symbols (>= 2, multiple of 2)
    parameter int IN_WIDTH  = 4,  // Bit width of each input symbol (fixed at 4)
    parameter int OUT_WIDTH = 3   // Bit width of output components (fixed at 3)
) (
    input  logic [N*IN_WIDTH-1:0]          bits,
    output logic [(N+N/2)*OUT_WIDTH-1:0]   I,
    output logic [(N+N/2)*OUT_WIDTH-1:0]   Q
);

    // Total output symbols: N mapped + N/2 interpolated = N + N/2
    localparam int TOTAL_OUT = N + N/2;

    // Mapped I and Q arrays (signed, OUT_WIDTH bits each)
    logic signed [OUT_WIDTH-1:0] mapped_I [N];
    logic signed [OUT_WIDTH-1:0] mapped_Q [N];

    // Interpolated I and Q (need 1 extra bit for addition)
    logic signed [OUT_WIDTH:0] interp_I [N/2];
    logic signed [OUT_WIDTH:0] interp_Q [N/2];

    // Function to map 2 bits to QAM16 component value
    function automatic logic signed [OUT_WIDTH-1:0] map_bits(input logic [1:0] b);
        case (b)
            2'b00: map_bits = -3;
            2'b01: map_bits = -1;
            2'b10: map_bits =  1;
            2'b11: map_bits =  3;
            default: map_bits = 0;
        endcase
    endfunction

    // Map input bits to I and Q components
    always_comb begin
        for (int i = 0; i < N; i++) begin
            // Extract the i-th symbol (N*IN_WIDTH-1 downto 0, symbol 0 is MSB group)
            // Symbol i occupies bits [(N-1-i)*IN_WIDTH +: IN_WIDTH]
            automatic logic [IN_WIDTH-1:0] sym;
            sym = bits[(N-1-i)*IN_WIDTH +: IN_WIDTH];
            // MSBs [IN_WIDTH-1 : IN_WIDTH-2] -> I component
            mapped_I[i] = map_bits(sym[IN_WIDTH-1:IN_WIDTH-2]);
            // LSBs [1:0] -> Q component
            mapped_Q[i] = map_bits(sym[1:0]);
        end
    end

    // Compute interpolated values for each pair of consecutive symbols
    always_comb begin
        for (int p = 0; p < N/2; p++) begin
            // Symbols at indices 2*p and 2*p+1
            interp_I[p] = ({{1{mapped_I[2*p][OUT_WIDTH-1]}}, mapped_I[2*p]} + 
                           {{1{mapped_I[2*p+1][OUT_WIDTH-1]}}, mapped_I[2*p+1]}) >>> 1;
            interp_Q[p] = ({{1{mapped_Q[2*p][OUT_WIDTH-1]}}, mapped_Q[2*p]} + 
                           {{1{mapped_Q[2*p+1][OUT_WIDTH-1]}}, mapped_Q[2*p+1]}) >>> 1;
        end
    end

    // Arrange output: for each pair (sym[2*p], interp[p], sym[2*p+1])
    // Output index in packed array:
    //   TOTAL_OUT symbols, each OUT_WIDTH bits
    //   Output slot 0 is MSB (highest bits)
    //
    // For pair p (0-indexed):
    //   - slot 3*p+0: mapped_I/Q[2*p]
    //   - slot 3*p+1: interp_I/Q[p]  (truncated to OUT_WIDTH)
    //   - slot 3*p+2: mapped_I/Q[2*p+1]
    always_comb begin
        I = '0;
        Q = '0;
        for (int p = 0; p < N/2; p++) begin
            // Slot index for first mapped symbol of pair p
            automatic int slot0 = 3*p;
            automatic int slot1 = 3*p + 1;
            automatic int slot2 = 3*p + 2;

            // Pack into output: slot 0 is at top (MSB side)
            // Slot k occupies bits [(TOTAL_OUT-1-k)*OUT_WIDTH +: OUT_WIDTH]
            I[(TOTAL_OUT-1-slot0)*OUT_WIDTH +: OUT_WIDTH] = mapped_I[2*p];
            I[(TOTAL_OUT-1-slot1)*OUT_WIDTH +: OUT_WIDTH] = interp_I[p][OUT_WIDTH-1:0];
            I[(TOTAL_OUT-1-slot2)*OUT_WIDTH +: OUT_WIDTH] = mapped_I[2*p+1];

            Q[(TOTAL_OUT-1-slot0)*OUT_WIDTH +: OUT_WIDTH] = mapped_Q[2*p];
            Q[(TOTAL_OUT-1-slot1)*OUT_WIDTH +: OUT_WIDTH] = interp_Q[p][OUT_WIDTH-1:0];
            Q[(TOTAL_OUT-1-slot2)*OUT_WIDTH +: OUT_WIDTH] = mapped_Q[2*p+1];
        end
    end

endmodule
