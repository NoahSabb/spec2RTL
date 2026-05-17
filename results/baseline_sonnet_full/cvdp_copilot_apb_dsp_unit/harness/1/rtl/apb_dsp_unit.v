// rtl/apb_dsp_unit.v

module apb_dsp_unit (
    input wire        pclk,
    input wire        presetn,
    input wire [9:0]  paddr,
    input wire        pselx,
    input wire        penable,
    input wire        pwrite,
    input wire [7:0]  pwdata,
    output reg        pready,
    output reg [7:0]  prdata,
    output reg        pslverr,
    output reg        sram_valid
);

    // FSM States
    localparam IDLE        = 2'b00;
    localparam WRITE_STATE = 2'b01;
    localparam READ_STATE  = 2'b10;

    reg [1:0] state, next_state;

    // Internal Registers
    reg [7:0] r_operand_1;
    reg [7:0] r_operand_2;
    reg [7:0] r_Enable;
    reg [7:0] r_write_address;
    reg [7:0] r_write_data;
    reg [7:0] r_result;

    // SRAM: 1KB = 1024 bytes
    reg [7:0] sram [0:1023];

    // Operand values read from SRAM
    wire [7:0] op1_data;
    wire [7:0] op2_data;
    assign op1_data = sram[r_operand_1];
    assign op2_data = sram[r_operand_2];

    // FSM: State Register
    always @(posedge pclk or negedge presetn) begin
        if (!presetn)
            state <= IDLE;
        else
            state <= next_state;
    end

    // FSM: Next State Logic
    always @(*) begin
        next_state = IDLE;
        case (state)
            IDLE: begin
                if (pselx && !penable) begin
                    if (pwrite)
                        next_state = WRITE_STATE;
                    else
                        next_state = READ_STATE;
                end else begin
                    next_state = IDLE;
                end
            end
            WRITE_STATE: next_state = IDLE;
            READ_STATE:  next_state = IDLE;
            default:     next_state = IDLE;
        endcase
    end

    // FSM: Output / Register Update Logic
    always @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            pready         <= 1'b0;
            prdata         <= 8'h00;
            pslverr        <= 1'b0;
            sram_valid     <= 1'b0;
            r_operand_1    <= 8'h00;
            r_operand_2    <= 8'h00;
            r_Enable       <= 8'h00;
            r_write_address<= 8'h00;
            r_write_data   <= 8'h00;
            r_result       <= 8'h00;
        end else begin
            // Default outputs each cycle
            pready     <= 1'b0;
            pslverr    <= 1'b0;
            prdata     <= 8'h00;
            sram_valid <= 1'b0;

            case (state)
                IDLE: begin
                    // Nothing to do; wait for transaction
                end

                WRITE_STATE: begin
                    pready <= 1'b1;
                    case (paddr)
                        10'h000: r_operand_1    <= pwdata;
                        10'h001: r_operand_2    <= pwdata;
                        10'h002: begin
                            r_Enable <= pwdata;
                        end
                        10'h003: r_write_address <= pwdata;
                        10'h004: r_write_data    <= pwdata;
                        default: pslverr <= 1'b1;
                    endcase
                end

                READ_STATE: begin
                    pready <= 1'b1;
                    case (paddr)
                        10'h000: prdata <= r_operand_1;
                        10'h001: prdata <= r_operand_2;
                        10'h002: prdata <= r_Enable;
                        10'h003: prdata <= r_write_address;
                        10'h004: prdata <= r_write_data;
                        10'h005: prdata <= r_result;
                        default: pslverr <= 1'b1;
                    endcase
                end

                default: begin
                    // Do nothing
                end
            endcase

            // Compute result based on r_Enable
            case (r_Enable)
                8'h01: begin
                    // Addition mode
                    r_result <= op1_data + op2_data;
                    sram[10'h005] <= op1_data + op2_data;
                end
                8'h02: begin
                    // Multiplication mode
                    r_result <= op1_data * op2_data;
                    sram[10'h005] <= op1_data * op2_data;
                end
                8'h03: begin
                    // Data Writing mode
                    sram_valid <= 1'b1;
                    sram[r_write_address] <= r_write_data;
                end
                default: begin
                    // Disabled or unknown
                end
            endcase
        end
    end

endmodule
