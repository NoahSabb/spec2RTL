module wishbone_to_ahb_bridge (
    // Wishbone Inputs
    input wire clk_i,
    input wire rst_i,
    input wire cyc_i,
    input wire stb_i,
    input wire [3:0] sel_i,
    input wire we_i,
    input wire [31:0] addr_i,
    input wire [31:0] data_i,

    // Wishbone Outputs
    output wire [31:0] data_o,
    output reg ack_o,

    // AHB Inputs
    input wire hclk,
    input wire hreset_n,
    input wire [31:0] hrdata,
    input wire [1:0] hresp,
    input wire hready,

    // AHB Outputs
    output wire [1:0] htrans,
    output wire [2:0] hsize,
    output wire [2:0] hburst,
    output wire hwrite,
    output wire [31:0] haddr,
    output wire [31:0] hwdata
);

    // States for the FSM
    typedef enum logic [1:0] {
        IDLE,
        ACTIVE
    } state_t;

    state_t state, next_state;

    // Internal registers to hold transaction attributes
    reg [31:0] addr_reg;
    reg [31:0] data_reg;
    reg [3:0] sel_reg;
    reg we_reg;

    // Endian conversion function
    function [31:0] endian_convert(input [31:0] data, input [3:0] sel);
        case (sel)
            4'b0001: return {24'b0, data[7:0]};
            4'b0010: return {16'b0, data[15:8], 8'b0};
            4'b0100: return {8'b0, data[23:16], 16'b0};
            4'b1000: return {data[31:24], 24'b0};
            4'b0011: return {16'b0, data[15:0]};
            4'b0110: return {8'b0, data[23:8], 8'b0};
            4'b1100: return {data[31:16], 16'b0};
            4'b0101: return {24'b0, data[15:8], 8'b0};
            4'b1010: return {16'b0, data[23:16], 8'b0};
            4'b1001: return {8'b0, data[31:24], 16'b0};
            4'b1110: return {data[31:16], 16'b0};
            4'b1101: return {data[31:24], 24'b0};
            4'b1011: return {data[31:24], 24'b0};
            4'b0111: return {24'b0, data[23:0]};
            4'b1111: return data;
            default: return 32'b0;
        endcase
    endfunction

    // Determine the size of the transfer based on sel (combinatorial)
    function [2:0] get_size(input [3:0] sel);
        case (sel)
            4'b0001, 4'b0010, 4'b0100, 4'b1000: return 3'b000; // Byte
            4'b0011, 4'b0110, 4'b1100, 4'b1010, 4'b1001, 4'b0111: return 3'b001; // Halfword
            4'b1110, 4'b1101, 4'b1011, 4'b1111: return 3'b010; // Word
            default: return 3'b000;
        endcase
    endfunction

    // State machine to manage transaction phases
    always_ff @(posedge hclk or negedge hreset_n) begin
        if (!hreset_n) begin
            state <= IDLE;
        end else begin
            state <= next_state;
        end
    end

    always_comb begin
        next_state = state;
        case (state)
            IDLE: begin
                if (cyc_i && stb_i) begin
                    next_state = ACTIVE;
                end
            end
            ACTIVE: begin
                if (hready) begin
                    next_state = IDLE;
                end
            end
            default: next_state = IDLE;
        endcase
    end

    // Combinational AHB address-phase outputs
    assign htrans = (state == IDLE && cyc_i && stb_i) ? 2'b10 :
                    (state == ACTIVE && !hready)       ? 2'b10 :
                    2'b00;

    assign haddr  = (state == IDLE && cyc_i && stb_i) ? addr_i :
                    (state == ACTIVE)                  ? addr_reg :
                    32'b0;

    assign hwrite = (state == IDLE && cyc_i && stb_i) ? we_i :
                    (state == ACTIVE && !hready)       ? we_reg :
                    1'b0;

    assign hsize  = (state == IDLE && cyc_i && stb_i) ? get_size(sel_i) :
                    (state == ACTIVE)                  ? get_size(sel_reg) :
                    3'b000;

    assign hburst = 3'b000; // Always SINGLE

    assign hwdata = (state == IDLE && cyc_i && stb_i) ? endian_convert(data_i, sel_i) :
                    (state == ACTIVE)                  ? endian_convert(data_reg, sel_reg) :
                    32'b0;

    // Always pass through hrdata directly
    assign data_o = hrdata;

    // Registered block: only captures internal regs and ack_o
    always_ff @(posedge hclk or negedge hreset_n) begin
        if (!hreset_n) begin
            ack_o    <= 1'b0;
            addr_reg <= 32'b0;
            data_reg <= 32'b0;
            sel_reg  <= 4'b0;
            we_reg   <= 1'b0;
        end else begin
            case (state)
                IDLE: begin
                    ack_o <= 1'b0;
                    if (cyc_i && stb_i) begin
                        addr_reg <= addr_i;
                        data_reg <= data_i;
                        sel_reg  <= sel_i;
                        we_reg   <= we_i;
                    end
                end

                ACTIVE: begin
                    if (hready) begin
                        ack_o  <= 1'b1;
                    end else begin
                        ack_o  <= 1'b0;
                    end
                end

                default: begin
                    ack_o <= 1'b0;
                end
            endcase
        end
    end

endmodule
