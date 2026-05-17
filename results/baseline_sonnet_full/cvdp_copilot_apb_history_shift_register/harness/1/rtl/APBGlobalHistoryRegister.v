// rtl/APBGlobalHistoryRegister.v

module APBGlobalHistoryRegister (
    // Clock & Reset
    input  wire       pclk,
    input  wire       presetn,

    // APB Signals
    input  wire [9:0] paddr,
    input  wire       pselx,
    input  wire       penable,
    input  wire       pwrite,
    input  wire [7:0] pwdata,
    output reg        pready,
    output reg  [7:0] prdata,
    output reg        pslverr,

    // History Shift Interface
    input  wire       history_shift_valid,

    // Clock Gating Enable
    input  wire       clk_gate_en,

    // Status & Interrupt Signals
    output wire       history_full,
    output wire       history_empty,
    output wire       error_flag,
    output wire       interrupt_full,
    output wire       interrupt_error
);

    // -------------------------------------------------------------------------
    // Internal Registers
    // -------------------------------------------------------------------------
    reg [7:0] control_register;  // Address 0x0
    reg [7:0] train_history;     // Address 0x1 (only [6:0] used)
    reg [7:0] predict_history;   // Address 0x2 (read-only via APB)

    // -------------------------------------------------------------------------
    // Clock Gating
    // -------------------------------------------------------------------------
    reg  clk_gate_en_latched;
    wire gated_clk;

    // Latch clk_gate_en on negative edge of pclk to avoid glitches
    always @(negedge pclk or negedge presetn) begin
        if (!presetn)
            clk_gate_en_latched <= 1'b0;
        else
            clk_gate_en_latched <= clk_gate_en;
    end

    // Gate the clock: when clk_gate_en_latched is high, gate pclk
    assign gated_clk = pclk & (~clk_gate_en_latched);

    // -------------------------------------------------------------------------
    // APB State Machine
    // -------------------------------------------------------------------------
    localparam IDLE        = 2'b00;
    localparam WRITE_STATE = 2'b01;
    localparam READ_STATE  = 2'b10;

    reg [1:0] apb_state;
    reg       error_flag_reg;

    // APB FSM - uses gated_clk
    always @(posedge gated_clk or negedge presetn) begin
        if (!presetn) begin
            apb_state        <= IDLE;
            pready           <= 1'b0;
            prdata           <= 8'b0;
            pslverr          <= 1'b0;
            control_register <= 8'b0;
            train_history    <= 8'b0;
            error_flag_reg   <= 1'b0;
        end else begin
            case (apb_state)
                IDLE: begin
                    pready  <= 1'b0;
                    pslverr <= 1'b0;
                    prdata  <= 8'b0;
                    error_flag_reg <= 1'b0;
                    if (pselx && !penable) begin
                        if (pwrite)
                            apb_state <= WRITE_STATE;
                        else
                            apb_state <= READ_STATE;
                    end
                end

                WRITE_STATE: begin
                    pready <= 1'b1;
                    if (pselx && penable && pwrite) begin
                        case (paddr)
                            10'h0: begin
                                control_register <= pwdata;
                                pslverr          <= 1'b0;
                                error_flag_reg   <= 1'b0;
                            end
                            10'h1: begin
                                train_history  <= pwdata;
                                pslverr        <= 1'b0;
                                error_flag_reg <= 1'b0;
                            end
                            10'h2: begin
                                // predict_history is read-only; treat as error
                                pslverr        <= 1'b1;
                                error_flag_reg <= 1'b1;
                            end
                            default: begin
                                pslverr        <= 1'b1;
                                error_flag_reg <= 1'b1;
                            end
                        endcase
                    end
                    apb_state <= IDLE;
                end

                READ_STATE: begin
                    pready <= 1'b1;
                    if (pselx && penable && !pwrite) begin
                        case (paddr)
                            10'h0: begin
                                // Reserved bits [7:4] read as 0
                                prdata         <= {4'b0, control_register[3:0]};
                                pslverr        <= 1'b0;
                                error_flag_reg <= 1'b0;
                            end
                            10'h1: begin
                                // Reserved bit [7] reads as 0
                                prdata         <= {1'b0, train_history[6:0]};
                                pslverr        <= 1'b0;
                                error_flag_reg <= 1'b0;
                            end
                            10'h2: begin
                                prdata         <= predict_history;
                                pslverr        <= 1'b0;
                                error_flag_reg <= 1'b0;
                            end
                            default: begin
                                prdata         <= 8'b0;
                                pslverr        <= 1'b1;
                                error_flag_reg <= 1'b1;
                            end
                        endcase
                    end
                    apb_state <= IDLE;
                end

                default: begin
                    apb_state <= IDLE;
                end
            endcase
        end
    end

    // -------------------------------------------------------------------------
    // Prediction History Update Logic
    // Triggered on rising edge of history_shift_valid (asynchronous to pclk)
    // -------------------------------------------------------------------------
    wire       predict_valid     = control_register[0];
    wire       predict_taken     = control_register[1];
    wire       train_mispredicted = control_register[2];
    wire       train_taken       = control_register[3];

    always @(posedge history_shift_valid or negedge presetn) begin
        if (!presetn) begin
            predict_history <= 8'b0;
        end else begin
            if (train_mispredicted) begin
                // Misprediction: restore history with actual outcome
                // {train_history[6:0], train_taken}
                predict_history <= {train_history[6:0], train_taken};
            end else if (predict_valid) begin
                // Normal update: shift in predicted direction at LSB
                predict_history <= {predict_history[6:0], predict_taken};
            end
            // If neither, no update
        end
    end

    // -------------------------------------------------------------------------
    // Status & Interrupt Signals
    // -------------------------------------------------------------------------
    assign history_full    = (predict_history == 8'hFF);
    assign history_empty   = (predict_history == 8'h00);
    assign error_flag      = error_flag_reg;
    assign interrupt_full  = history_full;
    assign interrupt_error = error_flag;

endmodule
