module axis_upscale (
    input wire clk,
    input wire resetn,
    
    input wire dfmt_enable,
    input wire dfmt_type,
    input wire dfmt_se,
    
    input wire s_axis_valid,
    input wire [23:0] s_axis_data,
    input wire m_axis_ready,
    
    output reg s_axis_ready,
    output reg m_axis_valid,
    output reg [31:0] m_axis_data
);

always @(posedge clk) begin
    if (!resetn) begin
        // Synchronous reset behavior
        s_axis_ready <= 1'b0;
        m_axis_valid <= 1'b0;
        m_axis_data <= 32'b0;
    end else begin
        // Normal operation
        s_axis_ready <= m_axis_ready;
        
        if (s_axis_valid) begin
            // Upscale the data based on the control signals
            if (dfmt_enable) begin
                case ({dfmt_se, dfmt_type})
                    2'b00: // No sign extension, MSB not inverted
                        m_axis_data <= {8'b0, s_axis_data};
                    2'b01: // No sign extension, MSB inverted
                        m_axis_data <= {8'b0, ~s_axis_data[23], s_axis_data[22:0]};
                    2'b10: // Sign extension, MSB not inverted
                        m_axis_data <= {{8{s_axis_data[23]}}, s_axis_data};
                    2'b11: // Sign extension, MSB inverted
                        m_axis_data <= {{8{~s_axis_data[23]}}, ~s_axis_data[23], s_axis_data[22:0]};
                endcase
            end else begin
                // No data format modification, just pad with zeros
                m_axis_data <= {8'b0, s_axis_data};
            end
            
            // Drive the master valid signal high
            m_axis_valid <= 1'b1;
        end else begin
            // Hold the master valid signal low if no transaction is happening
            m_axis_valid <= 1'b0;
        end
    end
end

endmodule
