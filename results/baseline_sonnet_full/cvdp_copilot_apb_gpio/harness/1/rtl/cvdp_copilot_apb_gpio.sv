// =============================================================================
// Module: cvdp_copilot_apb_gpio
// Description: APB-compatible GPIO module with configurable width,
//              bidirectional control, interrupt generation, and synchronization.
// =============================================================================

module cvdp_copilot_apb_gpio #(
    parameter int GPIO_WIDTH = 8
) (
    // APB Interface
    input  logic                    pclk,
    input  logic                    preset_n,
    input  logic                    psel,
    input  logic [7:2]              paddr,
    input  logic                    penable,
    input  logic                    pwrite,
    input  logic [31:0]             pwdata,
    output logic [31:0]             prdata,
    output logic                    pready,
    output logic                    pslverr,

    // GPIO Interface
    input  logic [GPIO_WIDTH-1:0]   gpio_in,
    output logic [GPIO_WIDTH-1:0]   gpio_out,
    output logic [GPIO_WIDTH-1:0]   gpio_enable,
    output logic [GPIO_WIDTH-1:0]   gpio_int,
    output logic                    comb_int
);

    // =========================================================================
    // Register Map Address Definitions
    // =========================================================================
    localparam logic [7:2] ADDR_GPIO_IN       = 6'h00; // 0x00 >> 2 = 0
    localparam logic [7:2] ADDR_GPIO_OUT      = 6'h01; // 0x04 >> 2 = 1
    localparam logic [7:2] ADDR_GPIO_OE       = 6'h02; // 0x08 >> 2 = 2
    localparam logic [7:2] ADDR_GPIO_INT_EN   = 6'h03; // 0x0C >> 2 = 3
    localparam logic [7:2] ADDR_GPIO_INT_TYPE = 6'h04; // 0x10 >> 2 = 4
    localparam logic [7:2] ADDR_GPIO_INT_POL  = 6'h05; // 0x14 >> 2 = 5
    localparam logic [7:2] ADDR_GPIO_INT_STAT = 6'h06; // 0x18 >> 2 = 6

    // =========================================================================
    // Internal Registers
    // =========================================================================
    logic [GPIO_WIDTH-1:0] reg_out;        // GPIO Output Data Register
    logic [GPIO_WIDTH-1:0] reg_oe;         // GPIO Output Enable Register
    logic [GPIO_WIDTH-1:0] reg_int_en;     // GPIO Interrupt Enable Register
    logic [GPIO_WIDTH-1:0] reg_int_type;   // GPIO Interrupt Type Register (1=edge, 0=level)
    logic [GPIO_WIDTH-1:0] reg_int_pol;    // GPIO Interrupt Polarity Register (1=active-high/rising, 0=active-low/falling)
    logic [GPIO_WIDTH-1:0] reg_int_stat;   // GPIO Interrupt Status Register (read-only, internally driven)

    // =========================================================================
    // Two-Stage Synchronizer for gpio_in
    // =========================================================================
    logic [GPIO_WIDTH-1:0] gpio_sync_stage1;
    logic [GPIO_WIDTH-1:0] gpio_sync_stage2;
    logic [GPIO_WIDTH-1:0] gpio_sync_prev;  // Previous synchronized value for edge detection

    always_ff @(posedge pclk or negedge preset_n) begin
        if (!preset_n) begin
            gpio_sync_stage1 <= '0;
            gpio_sync_stage2 <= '0;
            gpio_sync_prev   <= '0;
        end else begin
            gpio_sync_stage1 <= gpio_in;
            gpio_sync_stage2 <= gpio_sync_stage1;
            gpio_sync_prev   <= gpio_sync_stage2;
        end
    end

    // =========================================================================
    // APB Write Logic
    // =========================================================================
    logic apb_write_en;
    assign apb_write_en = psel & penable & pwrite;

    always_ff @(posedge pclk or negedge preset_n) begin
        if (!preset_n) begin
            reg_out      <= '0;
            reg_oe       <= '0;
            reg_int_en   <= '0;
            reg_int_type <= '0;
            reg_int_pol  <= '0;
        end else if (apb_write_en) begin
            case (paddr)
                ADDR_GPIO_OUT:      reg_out      <= pwdata[GPIO_WIDTH-1:0];
                ADDR_GPIO_OE:       reg_oe       <= pwdata[GPIO_WIDTH-1:0];
                ADDR_GPIO_INT_EN:   reg_int_en   <= pwdata[GPIO_WIDTH-1:0];
                ADDR_GPIO_INT_TYPE: reg_int_type <= pwdata[GPIO_WIDTH-1:0];
                ADDR_GPIO_INT_POL:  reg_int_pol  <= pwdata[GPIO_WIDTH-1:0];
                default: begin
                    // No effect for undefined addresses
                end
            endcase
        end
    end

    // =========================================================================
    // APB Read Logic
    // =========================================================================
    logic apb_read_en;
    assign apb_read_en = psel & ~pwrite;

    always_ff @(posedge pclk or negedge preset_n) begin
        if (!preset_n) begin
            prdata <= 32'h0;
        end else if (apb_read_en) begin
            case (paddr)
                ADDR_GPIO_IN:       prdata <= {{(32-GPIO_WIDTH){1'b0}}, gpio_sync_stage2};
                ADDR_GPIO_OUT:      prdata <= {{(32-GPIO_WIDTH){1'b0}}, reg_out};
                ADDR_GPIO_OE:       prdata <= {{(32-GPIO_WIDTH){1'b0}}, reg_oe};
                ADDR_GPIO_INT_EN:   prdata <= {{(32-GPIO_WIDTH){1'b0}}, reg_int_en};
                ADDR_GPIO_INT_TYPE: prdata <= {{(32-GPIO_WIDTH){1'b0}}, reg_int_type};
                ADDR_GPIO_INT_POL:  prdata <= {{(32-GPIO_WIDTH){1'b0}}, reg_int_pol};
                ADDR_GPIO_INT_STAT: prdata <= {{(32-GPIO_WIDTH){1'b0}}, reg_int_stat};
                default:            prdata <= 32'h0;
            endcase
        end else begin
            prdata <= 32'h0;
        end
    end

    // =========================================================================
    // APB Fixed Signals
    // =========================================================================
    assign pready  = 1'b1;
    assign pslverr = 1'b0;

    // =========================================================================
    // GPIO Output Assignments
    // =========================================================================
    assign gpio_out    = reg_out;
    assign gpio_enable = reg_oe;

    // =========================================================================
    // Interrupt Logic
    // =========================================================================
    // Edge detection signals
    logic [GPIO_WIDTH-1:0] rising_edge_det;
    logic [GPIO_WIDTH-1:0] falling_edge_det;

    // Detect rising and falling edges on synchronized GPIO input
    assign rising_edge_det  = gpio_sync_stage2 & ~gpio_sync_prev;
    assign falling_edge_det = ~gpio_sync_stage2 & gpio_sync_prev;

    // Compute raw interrupt signals (before enable masking)
    // reg_int_type:  1 = edge-sensitive, 0 = level-sensitive
    // reg_int_pol:   1 = active-high (rising edge), 0 = active-low (falling edge)
    logic [GPIO_WIDTH-1:0] raw_int;

    genvar i;
    generate
        for (i = 0; i < GPIO_WIDTH; i++) begin : gen_raw_int
            always_comb begin
                if (reg_int_type[i]) begin
                    // Edge-sensitive
                    if (reg_int_pol[i]) begin
                        // Rising edge
                        raw_int[i] = rising_edge_det[i];
                    end else begin
                        // Falling edge
                        raw_int[i] = falling_edge_det[i];
                    end
                end else begin
                    // Level-sensitive
                    if (reg_int_pol[i]) begin
                        // Active-high level
                        raw_int[i] = gpio_sync_stage2[i];
                    end else begin
                        // Active-low level
                        raw_int[i] = ~gpio_sync_stage2[i];
                    end
                end
            end
        end
    endgenerate

    // Interrupt Status Register - captures edge interrupts; level interrupts are continuous
    // For edge-sensitive: latch and hold until cleared (sticky)
    // For level-sensitive: reflect current state
    always_ff @(posedge pclk or negedge preset_n) begin
        if (!preset_n) begin
            reg_int_stat <= '0;
        end else begin
            for (int j = 0; j < GPIO_WIDTH; j++) begin
                if (reg_int_type[j]) begin
                    // Edge-sensitive: set on edge, clear when interrupt is disabled or on read-clear
                    // For simplicity, set on edge detect; clear when interrupt enable is deasserted
                    if (raw_int[j] & reg_int_en[j]) begin
                        reg_int_stat[j] <= 1'b1;
                    end else if (!reg_int_en[j]) begin
                        reg_int_stat[j] <= 1'b0;
                    end
                end else begin
                    // Level-sensitive: continuously reflect state
                    reg_int_stat[j] <= raw_int[j] & reg_int_en[j];
                end
            end
        end
    end

    // Individual interrupt signals (masked by enable)
    always_comb begin
        for (int k = 0; k < GPIO_WIDTH; k++) begin
            if (reg_int_type[k]) begin
                // Edge-sensitive: driven by status register
                gpio_int[k] = reg_int_stat[k] & reg_int_en[k];
            end else begin
                // Level-sensitive: driven by raw signal masked by enable
                gpio_int[k] = raw_int[k] & reg_int_en[k];
            end
        end
    end

    // Combined interrupt: logical OR of all individual interrupts
    assign comb_int = |gpio_int;

endmodule
