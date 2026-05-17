// secure_read_write_bus_interface.v
// Parameterized read/write bus interface with 8-bit configurable key authorization

module secure_read_write_bus_interface #(
    parameter p_configurable_key = 8'hAA,
    parameter p_data_width       = 8,
    parameter p_addr_width       = 8
)(
    input  wire [p_addr_width-1:0] i_addr,
    input  wire [p_data_width-1:0] i_data_in,
    input  wire [7:0]              i_key_in,
    input  wire                    i_read_write_enable,
    input  wire                    i_capture_pulse,
    input  wire                    i_reset_bar,
    output reg  [p_data_width-1:0] o_data_out,
    output reg                     o_error
);

    // Internal memory array: 2^p_addr_width locations, each p_data_width bits wide
    reg [p_data_width-1:0] mem [0:(1<<p_addr_width)-1];

    integer idx;

    always @(posedge i_capture_pulse or negedge i_reset_bar) begin
        if (!i_reset_bar) begin
            // Asynchronous active-low reset: clear outputs and memory
            o_data_out <= {p_data_width{1'b0}};
            o_error    <= 1'b0;
            for (idx = 0; idx < (1<<p_addr_width); idx = idx + 1) begin
                mem[idx] <= {p_data_width{1'b0}};
            end
        end else begin
            if (i_key_in == p_configurable_key[7:0]) begin
                // Authorized access
                o_error <= 1'b0;
                if (i_read_write_enable == 1'b0) begin
                    // Write operation
                    mem[i_addr] <= i_data_in;
                    o_data_out  <= {p_data_width{1'b0}};
                end else begin
                    // Read operation
                    o_data_out <= mem[i_addr];
                end
            end else begin
                // Unauthorized access
                o_error    <= 1'b1;
                o_data_out <= {p_data_width{1'b0}};
            end
        end
    end

endmodule
