// ttc_counter_lite.sv
// Lightweight Timer/Counter with AXI-Lite register interface

module ttc_counter_lite (
    input  logic        clk,
    input  logic        reset,
    input  logic [3:0]  axi_addr,
    input  logic [31:0] axi_wdata,
    input  logic        axi_write_en,
    input  logic        axi_read_en,
    output logic [31:0] axi_rdata,
    output logic        interrupt
);

    // Internal registers
    logic [15:0] count;
    logic [15:0] match_value;
    logic [15:0] reload_value;
    logic        enable;
    logic        interval_mode;
    logic        interrupt_enable;
    logic        match_flag;
    logic        interrupt_status;

    // Address definitions
    localparam ADDR_COUNT   = 4'h0;
    localparam ADDR_MATCH   = 4'h1;
    localparam ADDR_RELOAD  = 4'h2;
    localparam ADDR_CTRL    = 4'h3;
    localparam ADDR_STATUS  = 4'h4;

    // Write logic
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            match_value      <= 16'hFFFF;
            reload_value     <= 16'h0000;
            enable           <= 1'b0;
            interval_mode    <= 1'b0;
            interrupt_enable <= 1'b0;
        end else if (axi_write_en) begin
            case (axi_addr)
                ADDR_MATCH: begin
                    match_value <= axi_wdata[15:0];
                end
                ADDR_RELOAD: begin
                    reload_value <= axi_wdata[15:0];
                end
                ADDR_CTRL: begin
                    enable           <= axi_wdata[0];
                    interval_mode    <= axi_wdata[1];
                    interrupt_enable <= axi_wdata[2];
                end
                default: begin
                    // No action for other addresses
                end
            endcase
        end
    end

    // Counter logic
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            count      <= 16'h0000;
            match_flag <= 1'b0;
        end else begin
            if (enable) begin
                if (count == match_value) begin
                    match_flag <= 1'b1;
                    if (interval_mode) begin
                        count <= reload_value;
                    end else begin
                        count <= count; // Hold at match value
                    end
                end else begin
                    match_flag <= 1'b0;
                    count      <= count + 16'h1;
                end
            end else begin
                match_flag <= 1'b0;
            end
        end
    end

    // Interrupt status logic
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            interrupt_status <= 1'b0;
        end else begin
            // Clear interrupt when status register is written
            if (axi_write_en && (axi_addr == ADDR_STATUS)) begin
                interrupt_status <= 1'b0;
            end else if (match_flag && interrupt_enable) begin
                interrupt_status <= 1'b1;
            end
        end
    end

    // Interrupt output
    assign interrupt = interrupt_status & interrupt_enable;

    // Read logic
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            axi_rdata <= 32'h0000_0000;
        end else if (axi_read_en) begin
            case (axi_addr)
                ADDR_COUNT: begin
                    axi_rdata <= {16'h0000, count};
                end
                ADDR_MATCH: begin
                    axi_rdata <= {16'h0000, match_value};
                end
                ADDR_RELOAD: begin
                    axi_rdata <= {16'h0000, reload_value};
                end
                ADDR_CTRL: begin
                    axi_rdata <= {29'h0000_0000, interrupt_enable, interval_mode, enable};
                end
                ADDR_STATUS: begin
                    axi_rdata <= {31'h0000_0000, interrupt_status};
                end
                default: begin
                    axi_rdata <= 32'h0000_0000;
                end
            endcase
        end else begin
            axi_rdata <= 32'h0000_0000;
        end
    end

endmodule
