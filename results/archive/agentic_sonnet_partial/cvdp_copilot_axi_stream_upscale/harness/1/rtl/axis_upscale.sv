// AXI Stream Data Upsizer: 24-bit to 32-bit
// File: rtl/axis_upscale.sv

module axis_upscale (
    input  wire        clk,
    input  wire        resetn,

    // Data format control signals
    input  wire        dfmt_enable,
    input  wire        dfmt_type,
    input  wire        dfmt_se,

    // AXI Stream Slave Interface
    input  wire        s_axis_valid,
    input  wire [23:0] s_axis_data,
    output wire        s_axis_ready,

    // AXI Stream Master Interface
    output reg         m_axis_valid,
    output reg  [31:0] m_axis_data,
    input  wire        m_axis_ready
);

    // -------------------------------------------------------------------------
    // Combinational: compute the 8 fill bits that go into [31:24]
    // and bit [23] override when dfmt_type is used.
    // -------------------------------------------------------------------------

    // The MSB of slave data (bit 23)
    wire s_msb = s_axis_data[23];

    // The fill bit for the upper 8 bits [31:24]:
    //   - dfmt_enable = 0 : fill with 0
    //   - dfmt_enable = 1, dfmt_se = 0 : fill with 0
    //   - dfmt_enable = 1, dfmt_se = 1, dfmt_type = 0 : fill with s_msb
    //   - dfmt_enable = 1, dfmt_se = 1, dfmt_type = 1 : fill with ~s_msb
    wire fill_bit;
    assign fill_bit = dfmt_enable & dfmt_se & (dfmt_type ? ~s_msb : s_msb);

    // Bit [23] of m_axis_data:
    //   - dfmt_enable = 0 : pass s_axis_data[23] as-is
    //   - dfmt_enable = 1, dfmt_type = 0 : pass s_axis_data[23] as-is
    //   - dfmt_enable = 1, dfmt_type = 1 : invert s_axis_data[23]
    wire bit23;
    assign bit23 = (dfmt_enable & dfmt_type) ? ~s_msb : s_msb;

    // Full 32-bit combined word before registering
    wire [31:0] data_in;
    assign data_in = {
        {8{fill_bit}},   // bits [31:24]
        bit23,           // bit  [23]
        s_axis_data[22:0] // bits [22:0]
    };

    // -------------------------------------------------------------------------
    // Handshake / flow control
    // The module has a single pipeline register stage.
    // s_axis_ready is asserted when the pipeline register is empty OR
    // when the downstream is ready to accept data (so we can pass through).
    // -------------------------------------------------------------------------

    // Simple single-stage pipeline:
    // We accept slave data when:
    //   - there is no valid data in the register yet, OR
    //   - master is consuming the data this cycle
    wire reg_empty   = ~m_axis_valid;
    wire downstream_consuming = m_axis_valid & m_axis_ready;

    assign s_axis_ready = reg_empty | downstream_consuming;

    // -------------------------------------------------------------------------
    // Pipeline register
    // -------------------------------------------------------------------------
    always @(posedge clk) begin
        if (!resetn) begin
            m_axis_valid <= 1'b0;
            m_axis_data  <= 32'h0000_0000;
        end else begin
            if (s_axis_valid & s_axis_ready) begin
                // Load new data from slave
                m_axis_valid <= 1'b1;
                m_axis_data  <= data_in;
            end else if (downstream_consuming) begin
                // Data consumed by master, no new data available
                m_axis_valid <= 1'b0;
                m_axis_data  <= 32'h0000_0000;
            end
            // Otherwise hold current state
        end
    end

endmodule
