module cascaded_adder #(
    parameter IN_DATA_WIDTH = 16,
    parameter IN_DATA_NS    = 4
) (
    input  logic                                              clk,
    input  logic                                              rst_n,
    input  logic                                              i_valid,
    input  logic [IN_DATA_WIDTH * IN_DATA_NS - 1 : 0]        i_data,
    output logic                                              o_valid,
    output logic [(IN_DATA_WIDTH + $clog2(IN_DATA_NS)) - 1 : 0] o_data
);

    localparam OUT_DATA_WIDTH = IN_DATA_WIDTH + $clog2(IN_DATA_NS);

    // Registered input data and valid
    logic [IN_DATA_WIDTH * IN_DATA_NS - 1 : 0] r_data;
    logic                                       r_valid;

    // Stage 1: Register inputs
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_data  <= '0;
            r_valid <= 1'b0;
        end else begin
            r_valid <= i_valid;
            if (i_valid) begin
                r_data <= i_data;
            end
        end
    end

    // Cascaded addition using combinational logic on registered data
    logic [OUT_DATA_WIDTH - 1 : 0] cascade_sum [0 : IN_DATA_NS - 1];

    genvar i;
    generate
        for (i = 0; i < IN_DATA_NS; i++) begin : gen_cascade
            if (i == 0) begin
                assign cascade_sum[0] = {{($clog2(IN_DATA_NS)){1'b0}}, r_data[IN_DATA_WIDTH - 1 : 0]};
            end else begin
                assign cascade_sum[i] = cascade_sum[i-1] + {{($clog2(IN_DATA_NS)){1'b0}}, r_data[i * IN_DATA_WIDTH +: IN_DATA_WIDTH]};
            end
        end
    endgenerate

    // Stage 2: Register output
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            o_data  <= '0;
            o_valid <= 1'b0;
        end else begin
            o_valid <= r_valid;
            if (r_valid) begin
                o_data <= cascade_sum[IN_DATA_NS - 1];
            end
        end
    end

endmodule
