// AXI Stream Data Upsizer
// Upscales 24-bit input data to 32-bit output data
// Supports sign extension and data format selection

module axis_upscale (
    input  wire        clk,
    input  wire        resetn,

    // Data format control signals
    input  wire        dfmt_enable,
    input  wire        dfmt_type,
    input  wire        dfmt_se,

    // AXI Slave Interface
    input  wire        s_axis_valid,
    input  wire [23:0] s_axis_data,
    output wire        s_axis_ready,

    // AXI Master Interface
    output reg         m_axis_valid,
    output reg  [31:0] m_axis_data,
    input  wire        m_axis_ready
);

    // Internal signals for data formatting
    wire        msb_bit;
    wire        extended_bit;
    wire [31:0] formatted_data;

    // Ready signal: slave is ready when master is ready or master is not valid
    assign s_axis_ready = m_axis_ready | ~m_axis_valid;

    // Determine the MSB bit based on dfmt_type
    // dfmt_type = 1: inverted MSB of s_axis_data
    // dfmt_type = 0: MSB of s_axis_data as-is
    assign msb_bit = dfmt_type ? ~s_axis_data[23] : s_axis_data[23];

    // Determine the extension bit based on dfmt_se
    // dfmt_se = 1: extend with the (possibly inverted) MSB bit
    // dfmt_se = 0: extend with zero
    assign extended_bit = dfmt_se ? msb_bit : 1'b0;

    // Format the data based on dfmt_enable
    // dfmt_enable = 1: apply formatting with msb_bit and extended_bit
    // dfmt_enable = 0: zero-extend (8 zeros + 24-bit data)
    assign formatted_data = dfmt_enable ?
        {{8{extended_bit}}, msb_bit, s_axis_data[22:0]} :
        {8'h00, s_axis_data};

    // Pipeline register stage
    always @(posedge clk) begin
        if (!resetn) begin
            m_axis_valid <= 1'b0;
            m_axis_data  <= 32'h0;
        end else begin
            if (s_axis_ready) begin
                m_axis_valid <= s_axis_valid;
                if (s_axis_valid) begin
                    m_axis_data <= formatted_data;
                end
            end
        end
    end

endmodule
