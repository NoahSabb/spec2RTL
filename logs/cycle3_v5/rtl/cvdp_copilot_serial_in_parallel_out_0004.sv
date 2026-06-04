module serial_in_parallel_out_8bit (
    input wire clock,          // Clock signal
    input wire rst_n,        // Active-low reset signal
    input wire serial_in,    // Serial input bit
    output reg [7:0] parallel_out  // Parallel output register
);

always @(posedge clock or negedge rst_n) begin
    if (!rst_n) begin
        // Asynchronous active-low reset
        parallel_out <= 8'b0000_0000;
    end else begin
        // Shift the register left and insert the new serial bit at the LSB
        parallel_out <= {parallel_out[6:0], serial_in};
    end
end

endmodule
