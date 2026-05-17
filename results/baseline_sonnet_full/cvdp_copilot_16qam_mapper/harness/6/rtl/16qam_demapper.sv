// rtl/16qam_demapper.sv
// QAM16 Demapper with Interpolated Error Detection

module qam16_demapper_interpolated #(
    parameter int N         = 4,
    parameter int OUT_WIDTH = 4,
    parameter int IN_WIDTH  = 3
)(
    input  logic [(N + N/2)*IN_WIDTH-1:0] I,
    input  logic [(N + N/2)*IN_WIDTH-1:0] Q,
    output logic [N*OUT_WIDTH-1:0]        bits,
    output logic                          error_flag
);

    // Error threshold for interpolated value comparison
    localparam int ERROR_THRESHOLD = 1;

    // Total number of samples (mapped + interpolated)
    localparam int TOTAL_SAMPLES = N + N/2;

    // Number of groups (each group: mapped, interpolated, mapped)
    localparam int NUM_GROUPS = N/2;

    // Function to map I or Q component to 2 bits
    function automatic logic [1:0] map_to_bits(input logic signed [IN_WIDTH-1:0] val);
        case (val)
            3'sb101: map_to_bits = 2'b00; // -3
            3'sb111: map_to_bits = 2'b01; // -1
            3'sb001: map_to_bits = 2'b10; //  1
            3'sb011: map_to_bits = 2'b11; //  3
            default: map_to_bits = 2'b00; // default
        endcase
    endfunction

    // Internal arrays for parsed I and Q samples
    logic signed [IN_WIDTH-1:0]   I_samples [0:TOTAL_SAMPLES-1];
    logic signed [IN_WIDTH-1:0]   Q_samples [0:TOTAL_SAMPLES-1];

    // Parse the input vectors into arrays
    // Input is packed: index 0 is at the MSB side
    // I[(TOTAL_SAMPLES-1)*IN_WIDTH +: IN_WIDTH] is sample 0
    // Actually, let's clarify: packed arrays in SV are MSB first
    // So I[TOTAL_SAMPLES*IN_WIDTH-1 : (TOTAL_SAMPLES-1)*IN_WIDTH] = sample 0
    
    integer k;
    always_comb begin
        for (k = 0; k < TOTAL_SAMPLES; k++) begin
            I_samples[k] = signed'(I[(TOTAL_SAMPLES-1-k)*IN_WIDTH +: IN_WIDTH]);
            Q_samples[k] = signed'(Q[(TOTAL_SAMPLES-1-k)*IN_WIDTH +: IN_WIDTH]);
        end
    end

    // Mapped sample indices and interpolated sample indices
    // Pattern: mapped(0), interp(1), mapped(2), mapped(3), interp(4), mapped(5), ...
    // Group g (0-indexed): 
    //   mapped_a  index = g*3
    //   interp    index = g*3 + 1
    //   mapped_b  index = g*3 + 2

    // Storage for error detection
    logic signed [IN_WIDTH:0]   expected_I [0:NUM_GROUPS-1]; // IN_WIDTH+1 bits
    logic signed [IN_WIDTH:0]   expected_Q [0:NUM_GROUPS-1];
    logic signed [IN_WIDTH:0]   diff_I     [0:NUM_GROUPS-1];
    logic signed [IN_WIDTH:0]   diff_Q     [0:NUM_GROUPS-1];
    logic        [IN_WIDTH:0]   abs_diff_I [0:NUM_GROUPS-1];
    logic        [IN_WIDTH:0]   abs_diff_Q [0:NUM_GROUPS-1];
    logic                       group_error[0:NUM_GROUPS-1];

    // Storage for mapped symbols
    // Each group has 2 mapped symbols: mapped_a and mapped_b
    // Total mapped symbols = N
    // Symbol ordering in output: group0_mapped_a, group0_mapped_b, group1_mapped_a, group1_mapped_b, ...
    logic [1:0] I_bits [0:N-1];
    logic [1:0] Q_bits [0:N-1];

    integer g;
    always_comb begin
        error_flag = 1'b0;
        
        for (g = 0; g < NUM_GROUPS; g++) begin
            // Indices
            // mapped_a: g*3, interp: g*3+1, mapped_b: g*3+2
            
            // Expected interpolated value = (mapped_a + mapped_b) / 2
            // Use IN_WIDTH+1 bits for addition
            expected_I[g] = ($signed({I_samples[g*3][IN_WIDTH-1], I_samples[g*3]}) + 
                             $signed({I_samples[g*3+2][IN_WIDTH-1], I_samples[g*3+2]})) >>> 1;
            expected_Q[g] = ($signed({Q_samples[g*3][IN_WIDTH-1], Q_samples[g*3]}) + 
                             $signed({Q_samples[g*3+2][IN_WIDTH-1], Q_samples[g*3+2]})) >>> 1;
            
            // Difference between actual interpolated and expected
            diff_I[g] = $signed({I_samples[g*3+1][IN_WIDTH-1], I_samples[g*3+1]}) - expected_I[g];
            diff_Q[g] = $signed({Q_samples[g*3+1][IN_WIDTH-1], Q_samples[g*3+1]}) - expected_Q[g];
            
            // Absolute difference
            abs_diff_I[g] = diff_I[g][IN_WIDTH] ? (~diff_I[g] + 1'b1) : diff_I[g];
            abs_diff_Q[g] = diff_Q[g][IN_WIDTH] ? (~diff_Q[g] + 1'b1) : diff_Q[g];
            
            // Check if error exceeds threshold
            group_error[g] = (abs_diff_I[g] > ERROR_THRESHOLD) || (abs_diff_Q[g] > ERROR_THRESHOLD);
            
            if (group_error[g])
                error_flag = 1'b1;
            
            // Map mapped_a (index g*3) to bits
            I_bits[g*2]   = map_to_bits(I_samples[g*3]);
            Q_bits[g*2]   = map_to_bits(Q_samples[g*3]);
            
            // Map mapped_b (index g*3+2) to bits
            I_bits[g*2+1] = map_to_bits(I_samples[g*3+2]);
            Q_bits[g*2+1] = map_to_bits(Q_samples[g*3+2]);
        end
        
        // Assemble output bits vector
        // bits[N*OUT_WIDTH-1:0], symbol 0 at MSB
        for (g = 0; g < N; g++) begin
            bits[(N-1-g)*OUT_WIDTH +: OUT_WIDTH] = {I_bits[g], Q_bits[g]};
        end
    end

endmodule
