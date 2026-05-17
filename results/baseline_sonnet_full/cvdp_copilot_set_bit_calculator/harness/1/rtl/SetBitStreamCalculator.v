// rtl/SetBitStreamCalculator.v

module SetBitStreamCalculator #(
    parameter p_max_set_bit_count_width = 8
)(
    input  wire i_bit_in,
    input  wire i_clk,
    input  wire i_ready,
    input  wire i_rst_n,
    output reg  [p_max_set_bit_count_width-1:0] o_set_bit_count
);

    // Maximum saturation value
    localparam MAX_COUNT = {p_max_set_bit_count_width{1'b1}};

    // Register to hold previous value of i_ready for edge detection
    reg r_ready_prev;

    always @(posedge i_clk or negedge i_rst_n) begin
        if (!i_rst_n) begin
            o_set_bit_count <= {p_max_set_bit_count_width{1'b0}};
            r_ready_prev    <= 1'b0;
        end else begin
            // Update previous ready
            r_ready_prev <= i_ready;

            // Detect rising edge of i_ready: reset count
            if (i_ready && !r_ready_prev) begin
                // Rising edge of i_ready: reset count, ignore first bit
                o_set_bit_count <= {p_max_set_bit_count_width{1'b0}};
            end else if (i_ready && r_ready_prev) begin
                // i_ready is high and was high previously: count i_bit_in
                if (i_bit_in) begin
                    if (o_set_bit_count == MAX_COUNT) begin
                        // Saturate
                        o_set_bit_count <= MAX_COUNT;
                    end else begin
                        o_set_bit_count <= o_set_bit_count + 1'b1;
                    end
                end
            end
            // If i_ready is low, retain current count
        end
    end

endmodule
