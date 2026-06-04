module axis_upscale (
    input  wire        clk,
    input  wire        resetn,
    input  wire        dfmt_enable,
    input  wire        dfmt_type,
    input  wire        dfmt_se,
    input  wire        s_axis_valid,
    input  wire [23:0] s_axis_data,
    input  wire        m_axis_ready,
    output wire        s_axis_ready,
    output reg         m_axis_valid,
    output reg  [31:0] m_axis_data
);

    wire        sign_bit;
    wire        fill_bit;
    wire [31:0] data_out;

    // Determine the sign/fill bit
    assign sign_bit = dfmt_type ? ~s_axis_data[23] : s_axis_data[23];
    assign fill_bit = (dfmt_enable && dfmt_se) ? sign_bit : 1'b0;

    // Build output data
    assign data_out = dfmt_enable ? {{8{fill_bit}}, s_axis_data} : {8'b0, s_axis_data};

    // Ready when downstream is ready
    assign s_axis_ready = m_axis_ready;

    always @(posedge clk) begin
        if (!resetn) begin
            m_axis_valid <= 1'b0;
            m_axis_data  <= 32'b0;
        end else begin
            m_axis_valid <= s_axis_valid;
            m_axis_data  <= data_out;
        end
    end

endmodule
