module nbit_swizzling #(
    parameter integer DATA_WIDTH = 64
) (
    input  logic [DATA_WIDTH-1:0] data_in,
    input  logic [1:0]            sel,
    output logic [DATA_WIDTH-1:0] data_out
);

    logic [DATA_WIDTH-1:0] reversed_full;
    logic [DATA_WIDTH-1:0] reversed_half;
    logic [DATA_WIDTH-1:0] reversed_quarter;
    logic [DATA_WIDTH-1:0] reversed_eighth;

    genvar i;

    // sel=0: reverse entire word
    generate
        for (i = 0; i < DATA_WIDTH; i = i + 1) begin : gen_full
            assign reversed_full[i] = data_in[DATA_WIDTH-1-i];
        end
    endgenerate

    // sel=1: reverse each half independently
    // Section s (0=lower half, 1=upper half), base = s*(DATA_WIDTH/2)
    // data_out[base+k] = data_in[base + (DATA_WIDTH/2-1-k)]
    generate
        genvar s1, k1;
        for (s1 = 0; s1 < 2; s1 = s1 + 1) begin : gen_half_sec
            for (k1 = 0; k1 < DATA_WIDTH/2; k1 = k1 + 1) begin : gen_half_bit
                assign reversed_half[s1*(DATA_WIDTH/2) + k1] = data_in[s1*(DATA_WIDTH/2) + (DATA_WIDTH/2 - 1 - k1)];
            end
        end
    endgenerate

    // sel=2: reverse each quarter independently
    generate
        genvar s2, k2;
        for (s2 = 0; s2 < 4; s2 = s2 + 1) begin : gen_quarter_sec
            for (k2 = 0; k2 < DATA_WIDTH/4; k2 = k2 + 1) begin : gen_quarter_bit
                assign reversed_quarter[s2*(DATA_WIDTH/4) + k2] = data_in[s2*(DATA_WIDTH/4) + (DATA_WIDTH/4 - 1 - k2)];
            end
        end
    endgenerate

    // sel=3: reverse each eighth independently
    generate
        genvar s3, k3;
        for (s3 = 0; s3 < 8; s3 = s3 + 1) begin : gen_eighth_sec
            for (k3 = 0; k3 < DATA_WIDTH/8; k3 = k3 + 1) begin : gen_eighth_bit
                assign reversed_eighth[s3*(DATA_WIDTH/8) + k3] = data_in[s3*(DATA_WIDTH/8) + (DATA_WIDTH/8 - 1 - k3)];
            end
        end
    endgenerate

    always_comb begin
        case (sel)
            2'b00: data_out = reversed_full;
            2'b01: data_out = reversed_half;
            2'b10: data_out = reversed_quarter;
            2'b11: data_out = reversed_eighth;
            default: data_out = data_in;
        endcase
    end

endmodule
