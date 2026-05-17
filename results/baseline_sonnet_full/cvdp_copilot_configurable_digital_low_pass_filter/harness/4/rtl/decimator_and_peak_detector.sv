module advanced_decimator_with_adaptive_peak_detection #(
    parameter int N          = 8,
    parameter int DATA_WIDTH = 16,
    parameter int DEC_FACTOR = 4
)(
    input  logic                              clk,
    input  logic                              reset,
    input  logic                              valid_in,
    input  logic [DATA_WIDTH*N-1:0]           data_in,
    output logic                              valid_out,
    output logic [DATA_WIDTH*(N/DEC_FACTOR)-1:0] data_out,
    output logic [DATA_WIDTH-1:0]             peak_value
);

    localparam int DEC_N = N / DEC_FACTOR;

    // Registered input data
    logic [DATA_WIDTH*N-1:0] data_reg;

    // Unpacked input samples
    logic signed [DATA_WIDTH-1:0] samples [0:N-1];

    // Decimated samples
    logic signed [DATA_WIDTH-1:0] dec_samples [0:DEC_N-1];

    // 1) Input Data Registering
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            data_reg <= '0;
        end else begin
            data_reg <= data_in;
        end
    end

    // 2) Input Unpacking (combinational)
    // data_in is packed as {sample[0], sample[1], ..., sample[N-1]}
    // where sample[0] occupies the most significant bits
    always_comb begin
        for (int i = 0; i < N; i++) begin
            samples[i] = signed'(data_reg[(N-1-i)*DATA_WIDTH +: DATA_WIDTH]);
        end
    end

    // 3) Decimation (combinational)
    // Select every DEC_FACTOR-th sample starting from index 0
    always_comb begin
        for (int i = 0; i < DEC_N; i++) begin
            dec_samples[i] = samples[i * DEC_FACTOR];
        end
    end

    // 4) Peak Detection (combinational)
    always_comb begin
        peak_value = dec_samples[0];
        for (int i = 1; i < DEC_N; i++) begin
            if (dec_samples[i] > signed'(peak_value)) begin
                peak_value = dec_samples[i];
            end
        end
    end

    // 5) Output Packing (combinational)
    always_comb begin
        for (int i = 0; i < DEC_N; i++) begin
            data_out[(DEC_N-1-i)*DATA_WIDTH +: DATA_WIDTH] = dec_samples[i];
        end
    end

    // 6) Validation Control (sequential)
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            valid_out <= 1'b0;
        end else begin
            valid_out <= valid_in;
        end
    end

endmodule
