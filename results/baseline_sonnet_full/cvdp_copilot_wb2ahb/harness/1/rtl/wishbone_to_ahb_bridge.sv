// rtl/wishbone_to_ahb_bridge.sv
// Wishbone to AHB Bridge Module

module wishbone_to_ahb_bridge (
    // Wishbone Master Interface
    input  logic        clk_i,
    input  logic        rst_i,       // Active-low reset
    input  logic        cyc_i,
    input  logic        stb_i,
    input  logic [3:0]  sel_i,
    input  logic        we_i,
    input  logic [31:0] addr_i,
    input  logic [31:0] data_i,

    // AHB Slave Interface (inputs from AHB slave)
    input  logic        hclk,
    input  logic        hreset_n,    // Active-low reset
    input  logic [31:0] hrdata,
    input  logic [1:0]  hresp,
    input  logic        hready,

    // Wishbone Outputs
    output logic [31:0] data_o,
    output logic        ack_o,

    // AHB Outputs
    output logic [1:0]  htrans,
    output logic [2:0]  hsize,
    output logic [2:0]  hburst,
    output logic        hwrite,
    output logic [31:0] haddr,
    output logic [31:0] hwdata
);

    // AHB Transfer Types
    localparam HTRANS_IDLE   = 2'b00;
    localparam HTRANS_BUSY   = 2'b01;
    localparam HTRANS_NONSEQ = 2'b10;
    localparam HTRANS_SEQ    = 2'b11;

    // AHB Burst Types
    localparam HBURST_SINGLE = 3'b000;

    // AHB Size Types
    localparam HSIZE_BYTE     = 3'b000;
    localparam HSIZE_HALFWORD = 3'b001;
    localparam HSIZE_WORD     = 3'b010;

    // FSM States
    typedef enum logic [2:0] {
        IDLE        = 3'b000,
        ADDR_PHASE  = 3'b001,
        DATA_PHASE  = 3'b010,
        ACK_PHASE   = 3'b011,
        WAIT_READY  = 3'b100
    } state_t;

    state_t current_state, next_state;

    // Internal registers
    logic [31:0] haddr_reg;
    logic [2:0]  hsize_reg;
    logic        hwrite_reg;
    logic [31:0] hwdata_reg;
    logic [1:0]  htrans_reg;
    logic [31:0] data_o_reg;
    logic        ack_o_reg;

    // Function to determine transfer size from sel_i
    function automatic logic [2:0] get_hsize;
        input logic [3:0] sel;
        case (sel)
            4'b0001, 4'b0010, 4'b0100, 4'b1000: get_hsize = HSIZE_BYTE;
            4'b0011, 4'b1100:                    get_hsize = HSIZE_HALFWORD;
            4'b1111:                             get_hsize = HSIZE_WORD;
            default:                             get_hsize = HSIZE_WORD;
        endcase
    endfunction

    // Function to fix address based on sel_i
    function automatic logic [31:0] fix_addr;
        input logic [31:0] addr;
        input logic [3:0]  sel;
        case (sel)
            4'b0001: fix_addr = {addr[31:2], 2'b00};
            4'b0010: fix_addr = {addr[31:2], 2'b01};
            4'b0100: fix_addr = {addr[31:2], 2'b10};
            4'b1000: fix_addr = {addr[31:2], 2'b11};
            4'b0011: fix_addr = {addr[31:2], 2'b00};
            4'b1100: fix_addr = {addr[31:2], 2'b10};
            4'b1111: fix_addr = {addr[31:2], 2'b00};
            default: fix_addr = {addr[31:2], 2'b00};
        endcase
    endfunction

    // Endian conversion for write data based on sel_i
    function automatic logic [31:0] convert_write_data;
        input logic [31:0] data;
        input logic [3:0]  sel;
        case (sel)
            4'b0001: convert_write_data = {24'b0, data[7:0]};
            4'b0010: convert_write_data = {16'b0, data[7:0], 8'b0};
            4'b0100: convert_write_data = {8'b0, data[7:0], 16'b0};
            4'b1000: convert_write_data = {data[7:0], 24'b0};
            4'b0011: convert_write_data = {16'b0, data[15:0]};
            4'b1100: convert_write_data = {data[15:0], 16'b0};
            4'b1111: convert_write_data = data;
            default: convert_write_data = data;
        endcase
    endfunction

    // Endian conversion for read data based on sel_i
    function automatic logic [31:0] convert_read_data;
        input logic [31:0] data;
        input logic [3:0]  sel;
        case (sel)
            4'b0001: convert_read_data = {24'b0, data[7:0]};
            4'b0010: convert_read_data = {24'b0, data[15:8]};
            4'b0100: convert_read_data = {24'b0, data[23:16]};
            4'b1000: convert_read_data = {24'b0, data[31:24]};
            4'b0011: convert_read_data = {16'b0, data[15:0]};
            4'b1100: convert_read_data = {16'b0, data[31:16]};
            4'b1111: convert_read_data = data;
            default: convert_read_data = data;
        endcase
    endfunction

    // Registered sel for data phase
    logic [3:0] sel_reg;
    logic [31:0] data_i_reg;

    // Reset condition (both resets must be high for operation)
    wire reset_active = ~rst_i | ~hreset_n;

    // FSM sequential logic
    always_ff @(posedge hclk or negedge hreset_n or negedge rst_i) begin
        if (~hreset_n || ~rst_i) begin
            current_state <= IDLE;
            haddr_reg     <= 32'b0;
            hsize_reg     <= HSIZE_WORD;
            hwrite_reg    <= 1'b0;
            hwdata_reg    <= 32'b0;
            htrans_reg    <= HTRANS_IDLE;
            data_o_reg    <= 32'b0;
            ack_o_reg     <= 1'b0;
            sel_reg       <= 4'b0;
            data_i_reg    <= 32'b0;
        end else begin
            current_state <= next_state;
            ack_o_reg     <= 1'b0;

            case (current_state)
                IDLE: begin
                    if (cyc_i && stb_i) begin
                        // Capture transaction attributes
                        haddr_reg  <= fix_addr(addr_i, sel_i);
                        hsize_reg  <= get_hsize(sel_i);
                        hwrite_reg <= we_i;
                        hwdata_reg <= convert_write_data(data_i, sel_i);
                        htrans_reg <= HTRANS_NONSEQ;
                        sel_reg    <= sel_i;
                        data_i_reg <= data_i;
                    end else begin
                        htrans_reg <= HTRANS_IDLE;
                    end
                end

                ADDR_PHASE: begin
                    if (hready) begin
                        htrans_reg <= HTRANS_IDLE;
                        hwdata_reg <= convert_write_data(data_i_reg, sel_reg);
                    end
                end

                DATA_PHASE: begin
                    if (hready) begin
                        if (!hwrite_reg) begin
                            data_o_reg <= convert_read_data(hrdata, sel_reg);
                        end
                        ack_o_reg <= 1'b1;
                    end
                end

                WAIT_READY: begin
                    if (hready) begin
                        if (!hwrite_reg) begin
                            data_o_reg <= convert_read_data(hrdata, sel_reg);
                        end
                        ack_o_reg <= 1'b1;
                    end
                end

                ACK_PHASE: begin
                    ack_o_reg  <= 1'b0;
                    htrans_reg <= HTRANS_IDLE;
                    // Check for back-to-back transaction
                    if (cyc_i && stb_i) begin
                        haddr_reg  <= fix_addr(addr_i, sel_i);
                        hsize_reg  <= get_hsize(sel_i);
                        hwrite_reg <= we_i;
                        hwdata_reg <= convert_write_data(data_i, sel_i);
                        htrans_reg <= HTRANS_NONSEQ;
                        sel_reg    <= sel_i;
                        data_i_reg <= data_i;
                    end
                end

                default: begin
                    htrans_reg <= HTRANS_IDLE;
                end
            endcase
        end
    end

    // FSM next state logic
    always_comb begin
        next_state = current_state;
        case (current_state)
            IDLE: begin
                if (cyc_i && stb_i) begin
                    next_state = ADDR_PHASE;
                end else begin
                    next_state = IDLE;
                end
            end

            ADDR_PHASE: begin
                if (hready) begin
                    next_state = DATA_PHASE;
                end else begin
                    next_state = WAIT_READY;
                end
            end

            WAIT_READY: begin
                if (hready) begin
                    next_state = ACK_PHASE;
                end else begin
                    next_state = WAIT_READY;
                end
            end

            DATA_PHASE: begin
                if (hready) begin
                    next_state = ACK_PHASE;
                end else begin
                    next_state = WAIT_READY;
                end
            end

            ACK_PHASE: begin
                if (cyc_i && stb_i) begin
                    next_state = ADDR_PHASE;
                end else begin
                    next_state = IDLE;
                end
            end

            default: next_state = IDLE;
        endcase
    end

    // Output assignments
    assign htrans = htrans_reg;
    assign hsize  = hsize_reg;
    assign hburst = HBURST_SINGLE;
    assign hwrite = hwrite_reg;
    assign haddr  = haddr_reg;
    assign hwdata = hwdata_reg;
    assign data_o = data_o_reg;
    assign ack_o  = ack_o_reg;

endmodule
