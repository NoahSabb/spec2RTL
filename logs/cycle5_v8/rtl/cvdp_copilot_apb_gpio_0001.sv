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

    // Interrupt Logic (combinational)
    logic [GPIO_WIDTH-1:0] int_edge_pos;
    logic [GPIO_WIDTH-1:0] int_edge_neg;
    logic [GPIO_WIDTH-1:0] int_level_high;
    logic [GPIO_WIDTH-1:0] int_level_low;

    // Detect rising and falling edges (combinational)
    // reg_in_sync1 is the current (new) value, reg_in_sync2 is the previous (old) value
    assign int_edge_pos  = reg_in_sync1 & ~reg_in_sync2;
    assign int_edge_neg  = ~reg_in_sync1 & reg_in_sync2;

    // Detect high and low levels using current synchronized value
    assign int_level_high = reg_in_sync1;
    assign int_level_low  = ~reg_in_sync1;

    // Generate individual interrupt signals
    always_comb begin
        gpio_int = '0;
        for (int i = 0; i < GPIO_WIDTH; i++) begin
            if (reg_int_enable[i]) begin
                if (reg_int_type[i]) begin // Level-sensitive
                    if (reg_int_polarity[i]) begin // Active-high
                        gpio_int[i] = int_level_high[i];
                    end else begin // Active-low
                        gpio_int[i] = int_level_low[i];
                    end
                end else begin // Edge-sensitive
                    if (reg_int_polarity[i]) begin // Rising edge
                        gpio_int[i] = int_edge_pos[i];
                    end else begin // Falling edge
                        gpio_int[i] = int_edge_neg[i];
                    end
                end
            end
        end
    end

    // APB Write Logic
    always_ff @(posedge pclk or negedge preset_n) begin
        if (!preset_n) begin
            reg_out          <= '0;
            reg_enable       <= '0;
            reg_int_enable   <= '0;
            reg_int_type     <= '0;
            reg_int_polarity <= '0;
            reg_int_state    <= '0;
        end else begin
            // Update interrupt state per-bit with sticky logic for edge-sensitive
            for (int i = 0; i < GPIO_WIDTH; i++) begin
                if (reg_int_type[i]) begin
                    // Level-sensitive: continuously mirror gpio_int
                    reg_int_state[i] <= gpio_int[i];
                end else begin
                    // Edge-sensitive: latch on assertion, clear on write-to-clear
                    if (psel && penable && pwrite && (paddr[7:2] == 6'h06)) begin
                        // Write-to-clear: clear bits where pwdata bit is set
                        reg_int_state[i] <= reg_int_state[i] & ~pwdata[i];
                    end else if (gpio_int[i]) begin
                        reg_int_state[i] <= 1'b1;
                    end
                    // else hold current value
                end
            end

            if (psel && penable && pwrite) begin
                case (paddr[7:2])
                    6'h00: ; // Read-only, no write
                    6'h01: reg_out <= pwdata[GPIO_WIDTH-1:0];
                    6'h02: reg_enable <= pwdata[GPIO_WIDTH-1:0];
                    6'h03: reg_int_enable <= pwdata[GPIO_WIDTH-1:0];
                    6'h04: reg_int_type <= pwdata[GPIO_WIDTH-1:0];
                    6'h05: reg_int_polarity <= pwdata[GPIO_WIDTH-1:0];
                    6'h06: ; // Handled above (write-to-clear for edge-sensitive bits)
                    default: ; // Undefined address, no write
                endcase
            end
        end
    end

    // APB Read Logic
    always_comb begin
        prdata = '0;
        case (paddr[7:2])
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
    assign gpio_out    = reg_out;
    assign gpio_enable = reg_enable;

    // Combined Interrupt Signal
    assign comb_int = |gpio_int;

    // APB Ready and Error Signals
    assign pready  = 1'b1; // Always ready
    assign pslverr = 1'b0; // No error

endmodule
