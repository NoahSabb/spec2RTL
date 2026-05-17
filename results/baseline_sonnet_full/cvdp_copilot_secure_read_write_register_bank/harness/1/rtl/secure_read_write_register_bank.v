// rtl/secure_read_write_register_bank.v

module secure_read_write_register_bank #(
    parameter p_address_width  = 8,
    parameter p_data_width     = 8,
    parameter p_unlock_code_0  = 8'hAB,
    parameter p_unlock_code_1  = 8'hCD
)(
    input  wire [p_address_width-1:0] i_addr,
    input  wire [p_data_width-1:0]    i_data_in,
    input  wire                        i_read_write_enable,
    input  wire                        i_capture_pulse,
    input  wire                        i_rst_n,
    output reg  [p_data_width-1:0]    o_data_out
);

    // Register bank memory
    // Total addressable space = 2^p_address_width
    localparam MEM_DEPTH = (1 << p_address_width);

    reg [p_data_width-1:0] mem [0:MEM_DEPTH-1];

    // Unlock state machine states
    // State 0: Locked, waiting for unlock code 0 at address 0
    // State 1: Got code 0 at address 0, waiting for code 1 at address 1
    // State 2: Unlocked
    localparam STATE_LOCKED       = 2'b00;
    localparam STATE_GOT_CODE_0   = 2'b01;
    localparam STATE_UNLOCKED     = 2'b10;

    reg [1:0] unlock_state;

    integer i;

    always @(posedge i_capture_pulse or negedge i_rst_n) begin
        if (!i_rst_n) begin
            // Asynchronous reset
            unlock_state <= STATE_LOCKED;
            o_data_out   <= {p_data_width{1'b0}};
            // Optionally clear memory on reset - not specified, so leave as is
        end else begin
            // Default output
            o_data_out <= {p_data_width{1'b0}};

            if (!i_read_write_enable) begin
                // Write operation
                case (i_addr)
                    {{(p_address_width-1){1'b0}}, 1'b0}: begin
                        // Address 0 write
                        // Write to memory[0]
                        mem[0] <= i_data_in;
                        // Check unlock code 0
                        if (i_data_in == p_unlock_code_0[p_data_width-1:0]) begin
                            unlock_state <= STATE_GOT_CODE_0;
                        end else begin
                            // Wrong code, lock
                            unlock_state <= STATE_LOCKED;
                        end
                        o_data_out <= {p_data_width{1'b0}};
                    end

                    {{(p_address_width-1){1'b0}}, 1'b1}: begin
                        // Address 1 write
                        // Write to memory[1]
                        mem[1] <= i_data_in;
                        // Check unlock sequence
                        if (unlock_state == STATE_GOT_CODE_0 && i_data_in == p_unlock_code_1[p_data_width-1:0]) begin
                            unlock_state <= STATE_UNLOCKED;
                        end else begin
                            // Wrong code or wrong sequence, lock
                            unlock_state <= STATE_LOCKED;
                        end
                        o_data_out <= {p_data_width{1'b0}};
                    end

                    default: begin
                        // Other addresses
                        if (unlock_state == STATE_UNLOCKED) begin
                            mem[i_addr] <= i_data_in;
                        end
                        // If locked, do not write, output stays 0
                        o_data_out <= {p_data_width{1'b0}};
                    end
                endcase
            end else begin
                // Read operation
                case (i_addr)
                    {{(p_address_width-1){1'b0}}, 1'b0}: begin
                        // Address 0 is write-only, cannot be read
                        o_data_out <= {p_data_width{1'b0}};
                    end

                    {{(p_address_width-1){1'b0}}, 1'b1}: begin
                        // Address 1 is write-only, cannot be read
                        o_data_out <= {p_data_width{1'b0}};
                    end

                    default: begin
                        if (unlock_state == STATE_UNLOCKED) begin
                            o_data_out <= mem[i_addr];
                        end else begin
                            // Locked: output 0
                            o_data_out <= {p_data_width{1'b0}};
                        end
                    end
                endcase
            end
        end
    end

endmodule
