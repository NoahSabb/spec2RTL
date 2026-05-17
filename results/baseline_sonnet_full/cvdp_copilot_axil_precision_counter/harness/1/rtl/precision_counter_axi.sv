```systemverilog
module precision_counter_axi #(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 8
)(
    // Clock and Reset
    input  wire                              axi_aclk,
    input  wire                              axi_aresetn,

    // AXI Write Address Channel
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]    axi_awaddr,
    input  wire                              axi_awvalid,
    output reg                               axi_awready,

    // AXI Write Data Channel
    input  wire [C_S_AXI_DATA_WIDTH-1:0]    axi_wdata,
    input  wire [(C_S_AXI_DATA_WIDTH/8)-1:0] axi_wstrb,
    input  wire                              axi_wvalid,
    output reg                               axi_wready,

    // AXI Write Response Channel
    output reg  [1:0]                        axi_bresp,
    output reg                               axi_bvalid,
    input  wire                              axi_bready,

    // AXI Read Address Channel
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]    axi_araddr,
    input  wire                              axi_arvalid,
    output reg                               axi_arready,

    // AXI Read Data Channel
    output reg  [C_S_AXI_DATA_WIDTH-1:0]    axi_rdata,
    output reg  [1:0]                        axi_rresp,
    output reg                               axi_rvalid,
    input  wire                              axi_rready,

    // Control Outputs
    output wire                              axi_ap_done,
    output reg                               irq
);

    // Internal registers
    reg [C_S_AXI_DATA_WIDTH-1:0] slv_reg_ctl;
    reg [C_S_AXI_DATA_WIDTH-1:0] slv_reg_t;
    reg [C_S_AXI_DATA_WIDTH-1:0] slv_reg_v;
    reg [C_S_AXI_DATA_WIDTH-1:0] slv_reg_irq_mask;
    reg [C_S_AXI_DATA_WIDTH-1:0] slv_reg_irq_thresh;

    // Internal signals for write address/data capture
    reg [C_S_AXI_ADDR_WIDTH-1:0] axi_awaddr_reg;
    reg                           aw_en;

    // Address offsets
    localparam ADDR_CTL        = 8'h00;
    localparam ADDR_T          = 8'h10;
    localparam ADDR_V          = 8'h20;
    localparam ADDR_IRQ_MASK   = 8'h24;
    localparam ADDR_IRQ_THRESH = 8'h28;

    // ap_done logic
    assign axi_ap_done = (slv_reg_v == 32'd0) && (slv_reg_ctl[0] == 1'b1);

    // =========================================================================
    // Write Address Channel
    // =========================================================================
    always @(posedge axi_aclk or negedge axi_aresetn) begin
        if (!axi_aresetn) begin
            axi_awready    <= 1'b0;
            axi_awaddr_reg <= {C_S_AXI_ADDR_WIDTH{1'b0}};
            aw_en          <= 1'b1;
        end else begin
            if (~axi_awready && axi_awvalid && axi_wvalid && aw_en) begin
                axi_awready    <= 1'b1;
                axi_awaddr_reg <= axi_awaddr;
                aw_en          <= 1'b0;
            end else if (axi_bvalid && axi_bready) begin
                aw_en          <= 1'b1;
                axi_awready    <= 1'b0;
            end else begin
                axi_awready    <= 1'b0;
            end
        end
    end

    // =========================================================================
    // Write Data Channel
    // =========================================================================
    always @(posedge axi_aclk or negedge axi_aresetn) begin
        if (!axi_aresetn) begin
            axi_wready <= 1'b0;
        end else begin
            if (~axi_wready && axi_wvalid && axi_awvalid && aw_en) begin
                axi_wready <= 1'b1;
            end else begin
                axi_wready <= 1'b0;
            end
        end
    end

    // =========================================================================
    // Register Write Logic
    // =========================================================================
    // Helper function for byte-enable writes
    // We'll do inline byte enable logic

    wire write_en;
    assign write_en = axi_awready && axi_awvalid && axi_wready && axi_wvalid;

    // Determine if the address is valid for write
    wire addr_valid_write;
    assign addr_valid_write = (axi_awaddr_reg == ADDR_CTL)        ||
                               (axi_awaddr_reg == ADDR_T)          ||
                               (axi_awaddr_reg == ADDR_V)          ||
                               (axi_awaddr_reg == ADDR_IRQ_MASK)   ||
                               (axi_awaddr_reg == ADDR_IRQ_THRESH);

    // Write Response Channel
    always @(posedge axi_aclk or negedge axi_aresetn) begin
        if (!axi_aresetn) begin
            axi_bvalid <= 1'b0;
            axi_bresp  <= 2'b00;
        end else begin
            if (write_en && ~axi_bvalid) begin
                axi_bvalid <= 1'b1;
                if (addr_valid_write) begin
                    axi_bresp <= 2'b00; // OKAY
                end else begin
                    axi_bresp <= 2'b10; // SLVERR
                end
            end else if (axi_bready && axi_bvalid) begin
                axi_bvalid <= 1'b0;
                axi_bresp  <= 2'b00;
            end
        end
    end

    // Register write: slv_reg_ctl
    always @(posedge axi_aclk or negedge axi_aresetn) begin
        if (!axi_aresetn) begin
            slv_reg_ctl <= {C_S_AXI_DATA_WIDTH{1'b0}};
        end else begin
            if (write_en && (axi_awaddr_reg == ADDR_CTL)) begin
                // Byte-enable write
                if (axi_wstrb[0]) slv_reg_ctl[7:0]   <= axi_wdata[7:0];
                if (axi_wstrb[1]) slv_reg_ctl[15:8]  <= axi_wdata[15:8];
                if (axi_wstrb[2]) slv_reg_ctl[23:16] <= axi_wdata[23:16];
                if (axi_wstrb[3]) slv_reg_ctl[31:24] <= axi_wdata[31:24];
            end
        end
    end

    // Register write: slv_reg_t (also reset on any write to CTL)
    always @(posedge axi_aclk or negedge axi_aresetn) begin
        if (!axi_aresetn) begin
            slv_reg_t <= {C_S_AXI_DATA_WIDTH{1'b0}};
        end else begin
            if (write_en && (axi_awaddr_reg == ADDR_CTL)) begin
                // Writing to CTL resets slv_reg_t
                slv_reg_t <= {C_S_AXI_DATA_WIDTH{1'b0}};
            end else if (write_en && (axi_awaddr_reg == ADDR_T)) begin
                if (axi_wstrb[0]) slv_reg_t[7:0]   <= axi_wdata[7:0];
                if (axi_wstrb[1]) slv_reg_t[15:8]  <= axi_wdata[15:8];
                if (axi_wstrb[2]) slv_reg_t[23:16] <= axi_wdata[23:16];
                if (axi_wstrb[3]) slv_reg_t[31:24] <= axi_wdata[31:24];
            end else begin
                // Increment elapsed time when countdown is done (v==0) and counter is running
                if (slv_reg_ctl[0] && (slv_reg_v == 32'd0)) begin
                    slv_reg_t <= slv_reg_t + 1;
                end
            end
        end
    end

    // Register write: slv_reg_v (also countdown logic)
    always @(posedge axi_aclk or negedge axi_aresetn) begin
        if (!axi_aresetn) begin
            slv_reg_v <= {C_S_AXI_DATA_WIDTH{1'b0}};
        end else begin
            if (write_en && (axi_awaddr_reg == ADDR_V)) begin
                // Write takes priority
                if (axi_wstrb[0]) slv_reg_v[7:0]   <= axi_wdata[7:0];
                if (axi_wstrb[1]) slv_reg_v[15:8]  <= axi_wdata[15:8];
                if (axi_wstrb[2]) slv_reg_v[23:16] <= axi_wdata[23:16];
                if (axi_wstrb[3]) slv_reg_v[31:24] <= axi_wdata[31:24];
            end else begin
                // Countdown: decrement if running and not zero
                if (slv_reg_ctl[0] && (slv_reg_v != 32'd0)) begin
                    slv_reg_v <= slv_reg_v - 1;
                end
            end
        end
    end

    // Register write: slv_reg_irq_mask
    always @(posedge axi_aclk or negedge axi_aresetn) begin
        if (!axi_aresetn) begin
            slv_reg_irq_mask <= {C_S_AXI_DATA_WIDTH{1'b0}};
        end else begin
            if (write_en && (axi_awaddr_reg == ADDR_IRQ_MASK)) begin
                if (axi_wstrb[0]) slv_reg_irq_mask[7:0]   <= axi_wdata[7:0];
                if (axi_wstrb[1]) slv_reg_irq_mask[15:8]  <= axi_wdata[15:8];
                if (axi_wstrb[2]) slv_reg_irq_mask[23:16] <= axi_wdata[23:16];
                if (axi_wstrb[3]) slv_reg_irq_mask[31:24] <= axi_wdata[31:24];
            end
        end
    end

    // Register write: slv_reg_irq_thresh
    always @(posedge axi_aclk or negedge axi_aresetn) begin
        if (!axi_aresetn) begin
            slv_reg_irq_thresh <= {C_S_AXI_DATA_WIDTH{1'b0}};
        end else begin
            if (write_en && (axi_awaddr_reg == ADDR_IRQ_THRESH)) begin
                if (axi_wstrb[0]) slv_reg_irq_thresh[7:0]   <= axi_wdata[7:0];
                if (axi_wstrb[1]) slv_reg_irq_thresh[15:8]  <= axi_wdata[15:8];
                if (axi_wstrb[2]) slv_reg_irq_thresh[23:16] <= axi_wdata[23:16];
                if (axi_wstrb[3]) slv_reg_irq_thresh[31:24] <= axi_wdata[31:24];
            end
        end
    end

    // =========================================================================
    // IRQ Logic
    // =========================================================================
    always @(posedge axi_aclk or negedge axi_aresetn) begin
        if (!axi_aresetn) begin
            irq <= 1'b0;
        end else begin
            if (slv_reg_ctl[0] &&
                slv_reg_irq_mask[0] &&
                (slv_reg_v == slv_reg_irq_thresh)) begin
                irq <= 1'b1;
            end else begin
                irq <= 1'b0;
            end
        end
    end

    // =========================================================================
    // Read Address Channel
    // =========================================================================
    reg [C_S_AXI_ADDR_WIDTH-1:0] axi_araddr_reg;

    always @(posedge axi_aclk or negedge axi_aresetn) begin
        if (!axi_aresetn) begin
            axi_arready    <= 1'b0;
            axi_araddr_reg <= {C_S_AXI_ADDR_WIDTH{1'b0}};
        end else begin
            if (~axi_arready && axi_arvalid) begin
                axi_arready    <= 1'b1;
                axi_araddr_reg <= axi_araddr;
            end else begin
                axi_arready    <= 1'b0;
            end
        end
    end

    // =========================================================================
    // Read Data Channel
    // =========================================================================
    wire addr_valid_read;
    assign addr_valid_read = (axi_araddr_reg == ADDR_CTL)        ||
                              (axi_araddr_reg == ADDR_T)          ||
                              (axi_araddr_reg == ADDR_V)          ||
                              (axi_araddr_reg == ADDR_IRQ_MASK)   ||
                              (axi_araddr_reg == ADDR_IRQ_THRESH);

    always @(posedge axi_aclk or negedge axi_aresetn) begin
        if (!axi_aresetn) begin
            axi_rvalid <= 1'b0;
            axi_rresp  <= 2'b00;
            axi_rdata  <= {C_S_AXI_DATA_WIDTH{1'b0}};
        end else begin
            if (axi_arready && axi_arvalid && ~axi_rvalid) begin
                axi_rvalid <= 1'b1;
                if (addr_valid_read) begin
                    axi_rresp <= 2'b00; // OKAY
                    case (axi_araddr_reg)
                        ADDR_CTL:        axi_rdata <= slv_reg_ctl;
                        ADDR_T:          axi_rdata <= slv_reg_t;
                        ADDR_V:          axi_rdata <= slv_reg_v;
                        ADDR_IRQ_MASK:   axi_rdata <= slv_reg_irq_mask;
                        ADDR_IRQ_THRESH: axi_rdata <= slv_reg_irq_thresh;
                        default:         axi_rdata <= {C_S_AX