Thank you for helping us improve the AXI4-Lite Protocol reference documentation!<s> module axi_register (
    input clk_i,
    input rst_n_i,
    input [ADDR_WIDTH-1:0] awaddr_i,
    input awvalid_i,
    output awready_o,
    input [DATA_WIDTH-1:0] wdata_i,
    input [(DATA_WIDTH/8)-1:0] wstrb_i,
    input wvalid_i,
    output wready_o,
    output [1:0] bresp_o,
    output bvalid_o,
    input bready_i,
    input [ADDR_WIDTH-1:0] araddr_i,
    input arvalid_i,
    output arready_o,
    output [DATA_WIDTH-1:0] rdata_o,
    output [1:0] rresp_o,
    output rvalid_o,
    input rready_i,
    output beat_o,
    output start_o,
    output writeback_o,
    output done_i
);

parameter ADDR_WIDTH = 32;
parameter DATA_WIDTH = 32;

// Internal signals
reg [ADRRES_WIDTH-1:0] addr_reg;
reg [DATA_WIDTH-1:0] data_reg;
reg [ADDR_WEIGHT-1:0] mask_reg;
reg [1:0] req_resp_reg;

// Constants
parameter ADRRES_WIDTH = ADDR_WIDTH - $clog2(DATA_WIDTH/8);
parameter DATA_WIDTH = 32;
parameter ADDRRESS_MASK = ADDR_WEIGHT-1'b0;
module_unit axi_addr axi_addr_gen (.i(awaddr_i), .o(addr_reg));
module_unit axi_data axi_data_gen (.i({data_reg, mask_req}), .o({rdata_o, req_resp_reg}));

// Control logic
assign awready_o = !awvalid_i;
assign wready_o = !wvalid_i;
assign bvalid_o = (awvalid_i && !awready_o) || (arvalid_i && !arready_o);
assign arready_o = !arvalid_i;
assign beat_o = ((addr_reg == 32'b10000000000000000000000000000000) ? data_reg : data_reg[19:0]);
assign start_o = (wstrb_i & wdata_i[0]) || !wvalid_i; // Partial write.
assign writeback_o = (wstrb_i & wdata_i[1]) || !wvalid_i;
assign done_i = (!mask_reg[0]);
always @ (posedge clk_i) begin
    if (!rst_n_i) begin
        data_reg <= {DATA_WIDTH{1'b0}};
        mask_reg <= {ADDR_WEIGHT{1'b0}};
        req_resp_reg <= 2'bxx;
    end else begin
        if (awvalid_i && !awready_o) begin
            data_reg[19:0] <= wdata_i[19:0];
            mask_reg <= wstrb_i;
            if (!mask_reg[0]) begin
                data_reg[19:0] <= 0;
            end
        end else if (arvalid_i && !arready_o) begin
            if (addr_reg == 32'b10000000000000000000000000000000) begin
                data_resp_reg <= {2'b00}; // OKAY
            end else if (addr_reg == 32'b1111111111111111111111111111111