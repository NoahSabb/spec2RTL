module low_pass_filter #(
    parameter int DATA_WIDTH = 16,
    parameter int COEFF_WIDTH = 16,
    parameter int NUM_TAPS = 8,
    parameter int NBW_MULT = DATA_WIDTH + COEFF_WIDTH
)(
    input  logic                                        clk,
    input  logic                                        reset,
    input  logic [DATA_WIDTH*NUM_TAPS-1:0]              data_in,
    input  logic                                        valid_in,
    input  logic [COEFF_WIDTH*NUM_TAPS-1:0]             coeffs,
    output logic [NBW_MULT+$clog2(NUM_TAPS)-1:0]        data_out,
    output logic                                        valid_out
);

    // Internal registered arrays
    logic signed [DATA_WIDTH-1:0]  data_reg  [0:NUM_TAPS-1];
    logic signed [COEFF_WIDTH-1:0] coeff_reg [0:NUM_TAPS-1];

    // Intermediate multiplication results
    logic signed [NBW_MULT-1:0] mult_results [0:NUM_TAPS-1];

    // Summation result
    logic signed [NBW_MULT+$clog2(NUM_TAPS)-1:0] sum_result;

    // Sequential: Register input data and coefficients when valid_in is high
    always_ff @(posedge clk) begin
        if (reset) begin
            for (int i = 0; i < NUM_TAPS; i++) begin
                data_reg[i]  <= '0;
                coeff_reg[i] <= '0;
            end
        end else if (valid_in) begin
            for (int i = 0; i < NUM_TAPS; i++) begin
                data_reg[i]  <= signed'(data_in[i*DATA_WIDTH +: DATA_WIDTH]);
                coeff_reg[i] <= signed'(coeffs[i*COEFF_WIDTH +: COEFF_WIDTH]);
            end
        end
    end

    // Sequential: Register valid_out
    always_ff @(posedge clk) begin
        if (reset) begin
            valid_out <= 1'b0;
        end else begin
            valid_out <= valid_in;
        end
    end

    // Combinational: Element-wise multiplication with reversed coefficients
    // data_reg[i] * coeff_reg[NUM_TAPS-1-i]
    always_comb begin
        for (int i = 0; i < NUM_TAPS; i++) begin
            mult_results[i] = data_reg[i] * coeff_reg[NUM_TAPS-1-i];
        end
    end

    // Combinational: Summation of all multiplication results
    always_comb begin
        sum_result = '0;
        for (int i = 0; i < NUM_TAPS; i++) begin
            sum_result = sum_result + {{($clog2(NUM_TAPS)){mult_results[i][NBW_MULT-1]}}, mult_results[i]};
        end
    end

    // Combinational: Output assignment
    assign data_out = sum_result;

endmodule
