module cvdp_prbs_gen #(
    parameter int CHECK_MODE = 0,   // 0 for generator mode, 1 for checker mode
    parameter int POLY_LENGTH = 31, // Length of the polynomial
    parameter int POLY_TAP = 3,     // Tap position for XOR feedback
    parameter int WIDTH = 16        // Width of data_in and data_out
) (
    input wire clk,                 // Clock input
    input wire rst,                 // Active high synchronous reset
    input wire [WIDTH-1:0] data_in, // Input data bus
    output reg [WIDTH-1:0] data_out // Output data bus
);

    // Internal PRBS register
    reg [POLY_LENGTH-1:0] prbs_reg;

    // Multi-step LFSR implementation
    always @(posedge clk) begin
        if (rst) begin
            prbs_reg <= {POLY_LENGTH{1'b1}};
            data_out <= {WIDTH{1'b1}};
        end else begin
            // Declare local variables for multi-step LFSR
            reg [POLY_LENGTH-1:0] prbs_arr [0:WIDTH];
            reg xor_a;
            reg [WIDTH-1:0] result;
            integer i;

            // Initialize prbs_arr[0] with current prbs_reg
            prbs_arr[0] = prbs_reg;

            // Compute WIDTH steps of the LFSR
            // Python model uses MSB-first indexing:
            // prbs[i][poly_tap-1] corresponds to bit [POLY_LENGTH-POLY_TAP] in RTL (MSB=index 0 in Python)
            // prbs[i][poly_length-1] corresponds to bit [0] in RTL (LSB=last element in Python)
            // Python shift: [xor_a] + prbs[i][0:poly_length-1] => prepend xor_a, drop last => shift left, insert at MSB
            for (i = 0; i < WIDTH; i = i + 1) begin
                xor_a = prbs_arr[i][POLY_LENGTH-POLY_TAP] ^ prbs_arr[i][0];
                prbs_arr[i+1] = {xor_a, prbs_arr[i][POLY_LENGTH-1:1]};
                result[i] = xor_a;
            end

            // Update prbs_reg with final LFSR state
            prbs_reg <= prbs_arr[WIDTH];

            // Assign output based on mode
            if (CHECK_MODE == 0) begin
                data_out <= result;
            end else begin
                data_out <= result ^ data_in;
            end
        end
    end

endmodule
