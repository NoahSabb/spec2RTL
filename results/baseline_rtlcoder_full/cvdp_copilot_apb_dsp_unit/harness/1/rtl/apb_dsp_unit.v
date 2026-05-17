<s> module apb_dsp_unit(
    pclk,
    presetn,

    // APB interface
    paddr,
    pselx,
    penable,
    pwrite,
    pwdata,
    pready,
    prdata,
    pslverr,

    // SRAM Interface
    sram_valid
);

parameter WIDTH = 8;
parameter DEPTH = 1024;

input pclk;
input presetn;

input [WIDTH-1:0] pwdata;
output [WIDTH-1:0] prdata;
input paddr, pwrite, pselx, penable;
output pready, pslverr;
input sram_valid;

wire aclk;
assign aclk = pclk;

reg [10:0] r_operand_1;
reg [10:0] r_operand_2;
(* synopsys_dont_merge *) reg [2:0] r_Enable;
(* synopsys_dont_merge *) reg [10:0] r_write_address;
(* synopsys_dont_merge *)reg [WIDTH-1:0] r_write_data;

wire [WIDTH-1:0] prdata = (paddr == 2'h5) ? {8{1'bz}} : {WIDTH{1'b0}};
assign pready = 1'b1;
assign pslverr = (pwrite && (paddr < 4'h6)) ? 1'b0 : 1'b1; // Only addresses from 0x0 to 0x5 are valid. Addresses outside will generate error.

always @(posedge aclk or negedge presetn) begin: reset_behaviour
    if (!presetn) begin
        r_operand_1 <=   {6'b0,2'b0,2'b0,2'b0};
        r_operand_2 <=   {6'b0,2'b0,2'b0,2'b0};
        r_Enable <=      3'b0; // default(0x0): DSP is disabled
        r_write_address <=  11'd0;
        r_write_data <=  {WIDTH{1'b0}};
    end else begin
        if (selx) begin
            if (enable) begin
                if (paddr == 4'h0) begin
                    case(ENA[2:0])
                        3'b000: r_Enable <= 3'b0; // disabled
                        3'b001: r_Enable <= 3'b1; // ADD operation
                        3'b010: r_Enable <= 3'b2; // MULT operation
                        default: r_Enable <= 3'bx; // noop case, should never happen as we've only got three configurations cases to choose from.
                    endcase
                end else if (paddr == 4'h1) begin
                    r_operand_1 <= pwdata;
                end else if (paddr == 4'h2) begin
                    r_operand_2 <= pwdata;
                end else if (pselx && enable && pwrite && ((paddr >= 5'b00010) & (paddr < DEPTH))) begin
                    r_write_address <= paddr - 4'h6 // offset from address (0x6)
                end else if (sram_valid) begin
                    r_write_data <= prdata;
                end else if (pwrite && (paddr == 4'h5)) // write to address 32-bit constant register
                    case(ENA[2:0])
                        3'b000: $display("FAILED");
                        3'b001: prdata <= {{32{1'b0}}, r_operand_1} + r_operand_2; // addition
                        3'b010: prdata <= {{32{1'b0}}, r_operand_1} * r_operand_2; // multiplication
                        default: $display("FAILED");
                    endcase
                    //$write($time, " apb_dsp_unit.v - %n", 'N$i, ENABLED);  // no-op. We just want to see the output in $display.
                end else begin // default/read operations. If paddr is not aligned with configuration registers, we default to reading constant register at 5.
                    case(ENA[2:0])
                        3'b001: prdata <= {{32{r_operand_1}}};
                        3'b010: prdata <= {{32{r_operand_2}}};
                        default: prdata <= {{32{1'b0}}};
                    endcase
                end
            end else begin // DSP is disabled, so reading constant register at address 5 returns undefined.
                          // We return 0s in this case for all DSP modes.
                prdata <= {{32{1'b0}}};
            end
        end
    end
end

endmodule