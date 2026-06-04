module cvdp_copilot_apb_gpio #(
    parameter int GPIO_WIDTH = 8
) (
    // Inputs
    input logic pclk,
    input logic preset_n,
    input logic psel,
    input logic [7:2] paddr,
    input logic penable,
    input logic pwrite,
    input logic [31:0] pwdata,
    input logic [GPIO_WIDTH-1:0] gpio_in,

    // Outputs
    output logic [31:0] prdata,
    output logic pready,
    output logic pslverr,
    output logic [GPIO_WIDTH-1:0] gpio_out,
    output logic [GPIO_WIDTH-1:0] gpio_enable,
    output logic [GPIO_WIDTH-1:0] gpio_int,
    output logic comb_int
);

    // Internal Registers
    logic [GPIO_WIDTH-1:0] reg_in_sync1;
    logic [GPIO_WIDTH-1:0] reg_in_sync2;
    logic [GPIO_WIDTH-1:0] reg_out;
    logic [GPIO_WIDTH-1:0] reg_enable;
    logic [GPIO_WIDTH-1:0] reg_int_enable;
    logic [GPIO_WIDTH-1:0] reg_int_type;
    logic [GPIO_WIDTH-1:0] reg_int_polarity;
    logic [GPIO_WIDTH-1:0] reg_int_state;

    // Synchronize gpio_in with pclk using two-stage flip-flops
    always_ff @(posedge pclk or negedge preset_n) begin
        if (!preset_n) begin
            reg_in_sync1 <= '0;
            reg_in_sync2 <= '0;
        end else begin
            reg_in_sync1 <= gpio_in;
            reg_in_sync2 <= reg_in_sync1;
        end
    end

    // Interrupt Logic
    logic [GPIO_WIDTH-1:0] int_edge_pos;
    logic [GPIO_WIDTH-1:0] int_edge_neg;
    logic [GPIO_WIDTH-1:0] int_level_high;
    logic [GPIO_WIDTH-1:0] int_level_low;

    // reg_in_sync1 is the most recently sampled value (new)
    // reg_in_sync2 is the previous value (old)
    // Rising edge = new high AND old low
    // Falling edge = new low AND old high
    assign int_edge_pos = reg_in_sync1 & ~reg_in_sync2;
    assign int_edge_neg = reg_in_sync2 & ~reg_in_sync1;

    // Detect high and low levels
    assign int_level_high = reg_in_sync2;
    assign int_level_low = ~reg_in_sync2 & {GPIO_WIDTH{1'b1}};

    // Registered edge-detect interrupt state register
    always_ff @(posedge pclk or negedge preset_n) begin
        if (!preset_n) begin
            reg_int_state <= '0;
            reg_out <= '0;
            reg_enable <= '0;
            reg_int_enable <= '0;
            reg_int_type <= '0;
            reg_int_polarity <= '0;
        end else begin
            // APB Write Logic
            if (psel && penable && pwrite) begin
                case (paddr)
                    6'h00: ; // Read-only, no write
                    6'h01: reg_out <= pwdata[GPIO_WIDTH-1:0];
                    6'h02: reg_enable <= pwdata[GPIO_WIDTH-1:0];
                    6'h03: reg_int_enable <= pwdata[GPIO_WIDTH-1:0];
                    6'h04: reg_int_type <= pwdata[GPIO_WIDTH-1:0];
                    6'h05: reg_int_polarity <= pwdata[GPIO_WIDTH-1:0];
                    6'h06: begin
                        // Write-1-to-clear interrupt state
                        reg_int_state <= reg_int_state & ~pwdata[GPIO_WIDTH-1:0];
                    end
                    default: ; // Undefined address, no write
                endcase
            end

            // Capture edge interrupts into reg_int_state
            for (int i = 0; i < GPIO_WIDTH; i++) begin
                if (reg_int_enable[i] && reg_int_type[i]) begin // Edge-sensitive
                    if (reg_int_polarity[i]) begin // polarity=1: falling edge (active-low)
                        if (int_edge_neg[i]) begin
                            reg_int_state[i] <= 1'b1;
                        end
                    end else begin // polarity=0: rising edge (active-high)
                        if (int_edge_pos[i]) begin
                            reg_int_state[i] <= 1'b1;
                        end
                    end
                end else if (reg_int_type[i] == 1'b0) begin
                    // Level-sensitive: don't accumulate in reg_int_state
                    reg_int_state[i] <= 1'b0;
                end
            end

            // Handle write-1-to-clear with priority over edge set
            if (psel && penable && pwrite && paddr == 6'h06) begin
                for (int i = 0; i < GPIO_WIDTH; i++) begin
                    if (pwdata[i]) begin
                        // Clear takes priority
                        reg_int_state[i] <= 1'b0;
                    end
                end
            end
        end
    end

    // Generate individual interrupt signals
    always_comb begin
        gpio_int = '0;
        for (int i = 0; i < GPIO_WIDTH; i++) begin
            if (reg_int_enable[i]) begin
                if (reg_int_type[i]) begin // Edge-sensitive: use registered state
                    gpio_int[i] = reg_int_state[i];
                end else begin // Level-sensitive: use combinational signals
                    if (reg_int_polarity[i]) begin // polarity=1: active-low, fires when pin is LOW
                        gpio_int[i] = int_level_low[i];
                    end else begin // polarity=0: active-high, fires when pin is HIGH
                        gpio_int[i] = int_level_high[i];
                    end
                end
            end
        end
    end

    // APB Read Logic
    always_comb begin
        prdata = '0;
        case (paddr)
            6'h00: prdata[GPIO_WIDTH-1:0] = reg_in_sync2;      // GPIO Input Data
            6'h01: prdata[GPIO_WIDTH-1:0] = reg_out;            // GPIO Output Data
            6'h02: prdata[GPIO_WIDTH-1:0] = reg_enable;         // GPIO Output Enable
            6'h03: prdata[GPIO_WIDTH-1:0] = reg_int_enable;     // GPIO Interrupt Enable
            6'h04: prdata[GPIO_WIDTH-1:0] = reg_int_type;       // GPIO Interrupt Type
            6'h05: prdata[GPIO_WIDTH-1:0] = reg_int_polarity;   // GPIO Interrupt Polarity
            6'h06: prdata[GPIO_WIDTH-1:0] = reg_int_state;      // GPIO Interrupt State
            default: prdata = '0; // Undefined address, read 0
        endcase
    end

    // GPIO Output Control
    assign gpio_out = reg_out;
    assign gpio_enable = reg_enable;

    // Combined Interrupt Signal
    assign comb_int = |gpio_int;

    // APB Ready and Error Signals
    assign pready = 1'b1; // Always ready
    assign pslverr = 1'b0; // No error

endmodule
