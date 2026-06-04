module ttc_counter_lite (
    input wire clk,
    input wire reset,
    input wire [3:0] axi_addr,
    input wire [31:0] axi_wdata,
    input wire axi_write_en,
    input wire axi_read_en,
    output wire [31:0] axi_rdata,
    output reg interrupt
);

    // Registers
    reg [15:0] count;
    reg [15:0] match_value;
    reg [15:0] reload_value;
    reg enable;
    reg interval_mode;
    reg interrupt_enable;
    reg match_flag;

    // Internal signals
    wire match_detected;

    // Register map addresses
    localparam COUNT_REG_ADDR = 4'h0;
    localparam MATCH_REG_ADDR = 4'h1;
    localparam RELOAD_REG_ADDR = 4'h2;
    localparam CONTROL_REG_ADDR = 4'h3;
    localparam STATUS_REG_ADDR = 4'h4;

    // Match detection logic
    assign match_detected = (count == match_value);

    // Counter logic
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            count <= 16'h0;
            match_flag <= 1'b0;
        end else if (enable) begin
            if (match_detected) begin
                if (interval_mode) begin
                    count <= reload_value;
                    match_flag <= 1'b1;
                end else begin
                    count <= match_value;
                    match_flag <= 1'b1;
                end
            end else begin
                count <= count + 1;
            end
        end
    end

    // Interrupt generation
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            interrupt <= 1'b0;
        end else begin
            if (axi_write_en && axi_addr == STATUS_REG_ADDR) begin
                interrupt <= 1'b0;
            end else if (match_flag && interrupt_enable) begin
                interrupt <= 1'b1;
            end
        end
    end

    // AXI-Lite read operation (combinational)
    reg [31:0] axi_rdata_reg;
    assign axi_rdata = axi_rdata_reg;

    always @(*) begin
        case (axi_addr)
            COUNT_REG_ADDR:   axi_rdata_reg = {16'h0, count};
            MATCH_REG_ADDR:   axi_rdata_reg = {16'h0, match_value};
            RELOAD_REG_ADDR:  axi_rdata_reg = {16'h0, reload_value};
            CONTROL_REG_ADDR: axi_rdata_reg = {29'h0, interrupt_enable, interval_mode, enable};
            STATUS_REG_ADDR:  axi_rdata_reg = {31'h0, match_flag};
            default:          axi_rdata_reg = 32'h0;
        endcase
    end

    // AXI-Lite write operation
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            match_value <= 16'h0;
            reload_value <= 16'h0;
            enable <= 1'b0;
            interval_mode <= 1'b0;
            interrupt_enable <= 1'b0;
        end else if (axi_write_en) begin
            case (axi_addr)
                MATCH_REG_ADDR: match_value <= axi_wdata[15:0];
                RELOAD_REG_ADDR: reload_value <= axi_wdata[15:0];
                CONTROL_REG_ADDR: begin
                    enable <= axi_wdata[0];
                    interval_mode <= axi_wdata[1];
                    interrupt_enable <= axi_wdata[2];
                end
                STATUS_REG_ADDR: begin
                    // Writing to status register clears the interrupt flag
                    match_flag <= 1'b0;
                end
            endcase
        end
    end

endmodule
