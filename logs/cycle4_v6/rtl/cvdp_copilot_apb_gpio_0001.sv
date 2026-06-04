module cvdp_copilot_apb_gpio #(
    parameter GPIO_WIDTH = 8
) (
    input  logic                    pclk,
    input  logic                    preset_n,
    input  logic                    psel,
    input  logic [7:2]              paddr,
    input  logic                    penable,
    input  logic                    pwrite,
    input  logic [31:0]             pwdata,
    input  logic [GPIO_WIDTH-1:0]   gpio_in,
    
    output logic [31:0]             prdata,
    output logic                    pready,
    output logic                    pslverr,
    output logic [GPIO_WIDTH-1:0]   gpio_out,
    output logic [GPIO_WIDTH-1:0]   gpio_enable,
    output logic [GPIO_WIDTH-1:0]   gpio_int,
    output logic                    comb_int
);

    // APB fixed outputs
    assign pready  = 1'b1;
    assign pslverr = 1'b0;

    // Register definitions
    logic [GPIO_WIDTH-1:0] reg_din_sync;   // 0x00 - synchronized input
    logic [GPIO_WIDTH-1:0] reg_dout;       // 0x04 - output data
    logic [GPIO_WIDTH-1:0] reg_dout_en;    // 0x08 - output enable
    logic [GPIO_WIDTH-1:0] reg_int_en;     // 0x0C - interrupt enable
    logic [GPIO_WIDTH-1:0] reg_int_type;   // 0x10 - interrupt type (1=level, 0=edge)
    logic [GPIO_WIDTH-1:0] reg_int_pol;    // 0x14 - interrupt polarity (1=active-high/falling, 0=active-low/rising)
    logic [GPIO_WIDTH-1:0] reg_int_state;  // 0x18 - interrupt state (edge-sensitive sticky bits)

    // Two-stage synchronizer
    logic [GPIO_WIDTH-1:0] sync_stage1;
    logic [GPIO_WIDTH-1:0] sync_stage2;
    logic [GPIO_WIDTH-1:0] sync_prev;     // previous synchronized value for edge detection

    // APB write enable
    logic apb_write_en;
    assign apb_write_en = psel & penable & pwrite;

    // APB read enable  
    logic apb_read_en;
    assign apb_read_en = psel & ~pwrite;

    // Address decode (word address)
    logic [5:0] word_addr;
    assign word_addr = paddr[7:2];

    // APB write to interrupt state register (write-1-to-clear)
    logic apb_write_to_int_state;
    assign apb_write_to_int_state = apb_write_en & (word_addr == 6'h06);

    // Two-stage synchronizer
    always_ff @(posedge pclk or negedge preset_n) begin
        if (!preset_n) begin
            sync_stage1 <= '0;
            sync_stage2 <= '0;
            sync_prev   <= '0;
        end else begin
            sync_stage1 <= gpio_in;
            sync_stage2 <= sync_stage1;
            sync_prev   <= sync_stage2;
        end
    end

    assign reg_din_sync = sync_stage2;

    // Edge detection
    logic [GPIO_WIDTH-1:0] rising_edge_det;
    logic [GPIO_WIDTH-1:0] falling_edge_det;
    
    assign rising_edge_det  = sync_stage2 & ~sync_prev;
    assign falling_edge_det = ~sync_stage2 & sync_prev;

    // Register write logic
    always_ff @(posedge pclk or negedge preset_n) begin
        if (!preset_n) begin
            reg_dout      <= '0;
            reg_dout_en   <= '0;
            reg_int_en    <= '0;
            reg_int_type  <= '0;
            reg_int_pol   <= '0;
            reg_int_state <= '0;
        end else begin
            // Edge-sensitive interrupt state update logic (sticky, clear on write-1)
            for (int i = 0; i < GPIO_WIDTH; i++) begin
                if (!reg_int_type[i]) begin
                    // Edge sensitive (reg_int_type[i] = 0)
                    // reg_int_pol[i] = 0 -> rising edge
                    // reg_int_pol[i] = 1 -> falling edge
                    if (!reg_int_pol[i]) begin
                        // Rising edge (polarity=0 means active-low/rising)
                        reg_int_state[i] <= (reg_int_state[i] | rising_edge_det[i]) & 
                                            ~(apb_write_to_int_state & pwdata[i]);
                    end else begin
                        // Falling edge (polarity=1 means active-high/falling)
                        reg_int_state[i] <= (reg_int_state[i] | falling_edge_det[i]) & 
                                            ~(apb_write_to_int_state & pwdata[i]);
                    end
                end else begin
                    // Level sensitive - clear the sticky bit (level is handled combinatorially)
                    reg_int_state[i] <= 1'b0;
                end
            end

            // APB write operations
            if (apb_write_en) begin
                case (word_addr)
                    6'h01: reg_dout     <= pwdata[GPIO_WIDTH-1:0];
                    6'h02: reg_dout_en  <= pwdata[GPIO_WIDTH-1:0];
                    6'h03: reg_int_en   <= pwdata[GPIO_WIDTH-1:0];
                    6'h04: reg_int_type <= pwdata[GPIO_WIDTH-1:0];
                    6'h05: reg_int_pol  <= pwdata[GPIO_WIDTH-1:0];
                    // 0x00 is read-only (gpio input)
                    // 0x06 is handled inline in the per-bit logic above (write-1-to-clear for edge mode)
                    default: ;
                endcase
            end
        end
    end

    // Combinational level-sensitive interrupt signal
    logic [GPIO_WIDTH-1:0] level_int_comb;
    always_comb begin
        for (int i = 0; i < GPIO_WIDTH; i++) begin
            if (reg_int_type[i]) begin
                // Level sensitive
                // reg_int_pol[i] = 1 -> active-high (fires when input is high)
                // reg_int_pol[i] = 0 -> active-low (fires when input is low)
                level_int_comb[i] = reg_int_pol[i] ? sync_stage2[i] : ~sync_stage2[i];
            end else begin
                level_int_comb[i] = 1'b0;
            end
        end
    end

    // Combined interrupt state: edge-sensitive uses sticky reg_int_state, level uses combinatorial
    logic [GPIO_WIDTH-1:0] int_state_combined;
    assign int_state_combined = reg_int_state | level_int_comb;

    // APB read logic
    always_comb begin
        prdata = 32'h0;
        if (apb_read_en) begin
            case (word_addr)
                6'h00: prdata = {{(32-GPIO_WIDTH){1'b0}}, reg_din_sync};
                6'h01: prdata = {{(32-GPIO_WIDTH){1'b0}}, reg_dout};
                6'h02: prdata = {{(32-GPIO_WIDTH){1'b0}}, reg_dout_en};
                6'h03: prdata = {{(32-GPIO_WIDTH){1'b0}}, reg_int_en};
                6'h04: prdata = {{(32-GPIO_WIDTH){1'b0}}, reg_int_type};
                6'h05: prdata = {{(32-GPIO_WIDTH){1'b0}}, reg_int_pol};
                6'h06: prdata = {{(32-GPIO_WIDTH){1'b0}}, int_state_combined};
                default: prdata = 32'h0;
            endcase
        end
    end

    // GPIO outputs
    assign gpio_out    = reg_dout;
    assign gpio_enable = reg_dout_en;

    // Interrupt outputs
    assign gpio_int = int_state_combined & reg_int_en;
    assign comb_int = |gpio_int;

endmodule
