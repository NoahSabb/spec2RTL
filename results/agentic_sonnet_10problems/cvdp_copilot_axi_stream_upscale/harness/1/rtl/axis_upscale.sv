// rtl/axis_upscale.sv

module axis_upscale (
    input  wire         clk,
    input  wire         resetn,

    input  wire         dfmt_enable,
    input  wire         dfmt_type,
    input  wire         dfmt_se,

    input  wire         s_axis_valid,
    input  wire [23:0]  s_axis_data,
    input  wire         m_axis_ready,

    output wire         s_axis_ready,
    output wire         m_axis_valid,
    output wire [31:0]  m_axis_data
);

    // Internal registered signals
    reg         m_axis_valid_reg;
    reg [31:0]  m_axis_data_reg;
    reg         s_axis_ready_reg;

    // Data format logic - combinational
    wire        fill_bit;
    wire [7:0]  fill_byte;
    wire [31:0] upscaled_data;

    // Determine the fill bit based on dfmt signals
    // dfmt_enable=0: fill with 0
    // dfmt_enable=1, dfmt_se=0: fill with 0
    // dfmt_enable=1, dfmt_se=1, dfmt_type=0: fill with s_axis_data[23] (MSB)
    // dfmt_enable=1, dfmt_se=1, dfmt_type=1: fill with ~s_axis_data[23] (inverted MSB)

    assign fill_bit = dfmt_enable & dfmt_se & (dfmt_type ? ~s_axis_data[23] : s_axis_data[23]);

    // The upper byte fill
    assign fill_byte = {8{fill_bit}};

    // For bit[23] of output when dfmt_enable is active:
    // dfmt_type=1: inverted MSB of slave goes to m_axis_data[23]
    // dfmt_type=0: MSB of slave goes to m_axis_data[23]
    // When dfmt_enable=0: just concatenate zeros with data
    wire msb_bit;
    assign msb_bit = dfmt_enable ? (dfmt_type ? ~s_axis_data[23] : s_axis_data[23]) : s_axis_data[23];

    // Construct the 32-bit output data
    // [31:24] = fill_byte (sign extension or zero)
    // [23]    = msb_bit (potentially inverted MSB)
    // [22:0]  = s_axis_data[22:0]
    assign upscaled_data = dfmt_enable ? 
                           {fill_byte, msb_bit, s_axis_data[22:0]} :
                           {8'b0, s_axis_data};

    // Pipeline register and handshaking
    // s_axis_ready is registered, initialized to 0
    // It follows m_axis_ready (downstream readiness)
    always @(posedge clk) begin
        if (!resetn) begin
            m_axis_valid_reg <= 1'b0;
            m_axis_data_reg  <= 32'b0;
            s_axis_ready_reg <= 1'b0;
        end else begin
            // Update s_axis_ready: reflects m_axis_ready for next cycle
            s_axis_ready_reg <= m_axis_ready;

            // Pipeline data when handshake occurs
            if (s_axis_ready_reg & s_axis_valid) begin
                m_axis_valid_reg <= 1'b1;
                m_axis_data_reg  <= upscaled_data;
            end else if (m_axis_ready) begin
                // Downstream consumed the data, no new data coming in
                m_axis_valid_reg <= 1'b0;
            end
        end
    end

    // Output assignments
    assign s_axis_ready = s_axis_ready_reg;
    assign m_axis_valid = m_axis_valid_reg;
    assign m_axis_data  = m_axis_data_reg;

endmodule
