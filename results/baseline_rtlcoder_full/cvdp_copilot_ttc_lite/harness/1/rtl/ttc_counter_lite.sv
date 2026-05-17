<s> module ttc_counter_lite (
    input clk,
    input reset,
    input [3:0] axi_addr,
    input [31:0] axi_wdata,
    output [31:0] axi_rdata,
    input axi_write_en,
    input axi_read_en,
    output reg interrupt,
    output reg [15:0] count,
    input interrupt_clear
);

reg [15:0] match_value;
reg [15:0] reload_value;
reg enable = 0;
reg interval_mode = 0;
reg interrupt_enable = 0;
wire match_flag;

// Counter Registers
reg [15:0] counter_match_count = 0;
reg [15:0] counter_reload_count = 0;
always @(posedge clk, posedge reset) begin
    if (reset) begin
        count <= 0;
        counter_match_count <= 0;
        counter_reload_count <= 0;
        interrupt <= 0;
        match_flag <= 0;
    end else begin
        if (enable) begin
            count <= count + 1;
            if (interval_mode) begin
                if (match_flag) begin
                    count <= counter_reload_count;
                end
            end else begin
                if (count == match_value[15:0]) begin
                    count <= match_value[15:0];
                end
            end
        end else begin
            count <= 0;
        end
    end
end

// Match Detection Logic
wire edge;
assign edge = (&count) & (!match_flag);
always @(posedge clk, posedge reset) begin
    if (reset) begin
        match_flag <= 0;
    end else begin
        if (edge && count == match_value[15:0]) begin
            match_flag <= 1;
        end
        if (interval_mode && match_flag) begin
            counter_match_count <= counter_match_count + 1;
            if (counter_match_count == reload_value) begin
                match_flag <= 0;
                counter_reload_count <= reload_value;
            end else begin
                count <= count + 1;
                interrupt <= interrupt && interrupt_enable;
            end
        end
    end
end

// Interrupt Generation Logic
always @(posedge clk, posedge reset) begin
    if (reset) begin
        interrupt <= 0;
    end else begin
        interrupt <= interrupt_clear ? 0 : (match_flag && interrupt_enable);
    end
end

// AXI-Lite Register Read and Write Logic
always @(posedge clk, posedge reset) begin
    if (reset) begin
        axi_rdata <= {4'bx, match_value[7:0], 16'h0000};
    end else begin
        if (axi_read_en && axi_addr == 4'hf) begin
            case (axi_addr)
                4'h0: axi_rdata <= count[15:0];
                4'h1: axi_rdata <= match_value[7:0];
                4'h2: axi_rdata <= reload_value[15:0];
                4'h3: axi_rdata <= {1'b1, enable, interval_mode, interrupt_enable}; // this bit should probably be changed to just signal interrupt -JT
                4'h4: axi_rdata <= interrupt ? 32'h0000FFFF : 32'h00000000;
            endcase
        end else begin
            case (axi_addr)
                4'h0: count[15:0] <= axi_wdata[7:0];
                4'h1: match_value[7:0] <= axi_wdata[7:0];
                4'h2: reload_value[15:0] <= axi_wdata[15:0];
                4'h3: {enable, interval_mode, interrupt_enable} <= axi_wdata[6:2];
            endcase
        end
    end
end

endmodule