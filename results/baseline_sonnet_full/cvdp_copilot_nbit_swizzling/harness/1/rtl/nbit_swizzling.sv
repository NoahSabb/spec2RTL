module nbit_swizzling #(
    parameter DATA_WIDTH = 64
) (
    input  logic [DATA_WIDTH-1:0] data_in,
    input  logic [1:0]            sel,
    output logic [DATA_WIDTH-1:0] data_out
);

    // Local parameters for segment sizes
    localparam HALF_WIDTH    = DATA_WIDTH / 2;
    localparam QUARTER_WIDTH = DATA_WIDTH / 4;
    localparam EIGHTH_WIDTH  = DATA_WIDTH / 8;

    // Function to reverse bits of a given width
    function automatic logic [DATA_WIDTH-1:0] reverse_bits;
        input logic [DATA_WIDTH-1:0] in_data;
        input integer                width;
        input integer                offset;
        integer i;
        begin
            reverse_bits = in_data;
            for (i = 0; i < width; i++) begin
                reverse_bits[offset + i] = in_data[offset + width - 1 - i];
            end
        end
    endfunction

    always_comb begin
        case (sel)
            2'b00: begin
                // Reverse entire input
                integer i;
                for (i = 0; i < DATA_WIDTH; i++) begin
                    data_out[i] = data_in[DATA_WIDTH-1-i];
                end
            end
            2'b01: begin
                // Divide into 2 halves and reverse each half separately
                integer i;
                for (i = 0; i < HALF_WIDTH; i++) begin
                    data_out[i]             = data_in[HALF_WIDTH-1-i];
                    data_out[HALF_WIDTH+i]  = data_in[DATA_WIDTH-1-i];
                end
            end
            2'b10: begin
                // Divide into 4 quarters and reverse each quarter separately
                integer i;
                for (i = 0; i < QUARTER_WIDTH; i++) begin
                    data_out[i]                      = data_in[QUARTER_WIDTH-1-i];
                    data_out[QUARTER_WIDTH+i]        = data_in[2*QUARTER_WIDTH-1-i];
                    data_out[2*QUARTER_WIDTH+i]      = data_in[3*QUARTER_WIDTH-1-i];
                    data_out[3*QUARTER_WIDTH+i]      = data_in[4*QUARTER_WIDTH-1-i];
                end
            end
            2'b11: begin
                // Divide into 8 sections and reverse each section separately
                integer i;
                for (i = 0; i < EIGHTH_WIDTH; i++) begin
                    data_out[i]                = data_in[EIGHTH_WIDTH-1-i];
                    data_out[EIGHTH_WIDTH+i]   = data_in[2*EIGHTH_WIDTH-1-i];
                    data_out[2*EIGHTH_WIDTH+i] = data_in[3*EIGHTH_WIDTH-1-i];
                    data_out[3*EIGHTH_WIDTH+i] = data_in[4*EIGHTH_WIDTH-1-i];
                    data_out[4*EIGHTH_WIDTH+i] = data_in[5*EIGHTH_WIDTH-1-i];
                    data_out[5*EIGHTH_WIDTH+i] = data_in[6*EIGHTH_WIDTH-1-i];
                    data_out[6*EIGHTH_WIDTH+i] = data_in[7*EIGHTH_WIDTH-1-i];
                    data_out[7*EIGHTH_WIDTH+i] = data_in[8*EIGHTH_WIDTH-1-i];
                end
            end
            default: begin
                data_out = data_in;
            end
        endcase
    end

endmodule
