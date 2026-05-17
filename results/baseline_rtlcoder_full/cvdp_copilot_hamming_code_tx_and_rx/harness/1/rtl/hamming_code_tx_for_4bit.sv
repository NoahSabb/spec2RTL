Module Name: hamming_code_tx_for_4bit
Version: 0.1
Authors: Yunxiang "Annie" Hu (yan@sandia.gov)
Date Created: 2023-05-09 21:29:12 UTC
SRL #: 68311X_V64E_B12XE/Virtex6-SL FPGA
//---------------------------------------------------------------------------
module hamming_code_tx_for_4bit(
    input [3:0] data_in,        // Original data to be encoded and transmitted
    output reg [7:0] data_out   // 8-bit encoded signal with padded redundant bit (0), 3 parity bits (padded with 1s) and the original input bits.
);

// Encoding module logic
always @* begin
    // Calculate 2 parity bits based on even parity at positions 0, 1, 3 of data_in bits using XOR operation
    data_out[1] = ^data_in;
    data_out[2] = ^{{1'b0, data_in[0], data_in[2]}};
    
    // Preserve the ordering and values of input bits by assigning them directly to the 4 most significant bits in data_out
    data_out[3:0] = {data_in[3:1], 1'b0};
end

// End of module logic
endmodule