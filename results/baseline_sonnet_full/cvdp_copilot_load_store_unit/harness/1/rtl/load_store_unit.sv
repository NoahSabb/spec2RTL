module load_store_unit (
    // Clock and Reset
    input  logic        clk,
    input  logic        rst_n,

    // Data-Cache Interface
    output logic        dmem_req_o,
    input  logic        dmem_gnt_i,
    output logic [31:0] dmem_req_addr_o,
    output logic        dmem_req_we_o,
    output logic [3:0]  dmem_req_be_o,
    output logic [31:0] dmem_req_wdata_o,
    input  logic        dmem_rvalid_i,
    input  logic [31:0] dmem_rsp_rdata_i,

    // Execution Stage Interface
    input  logic        ex_if_req_i,
    input  logic        ex_if_we_i,
    input  logic [1:0]  ex_if_type_i,
    input  logic [31:0] ex_if_wdata_i,
    input  logic [31:0] ex_if_addr_base_i,
    input  logic [31:0] ex_if_addr_offset_i,
    output logic        ex_if_ready_o,

    // Writeback Interface
    output logic [31:0] wb_if_rdata_o,
    output logic        wb_if_rvalid_o
);

    // Internal state machine
    typedef enum logic [2:0] {
        IDLE        = 3'b000,
        MEM_REQ     = 3'b001,
        WAIT_GNT    = 3'b010,
        WAIT_RVALID = 3'b011,
        COMPLETE    = 3'b100
    } state_t;

    state_t state, next_state;

    // Registered signals
    logic        req_we_r;
    logic [1:0]  req_type_r;
    logic [31:0] req_addr_r;
    logic [31:0] req_wdata_r;
    logic [3:0]  req_be_r;

    // Combinational signals
    logic [31:0] eff_addr;
    logic [1:0]  addr_lsb;
    logic [3:0]  byte_enable;
    logic        misaligned;
    logic        accepted;

    // Effective address calculation
    assign eff_addr = ex_if_addr_base_i + ex_if_addr_offset_i;
    assign addr_lsb = eff_addr[1:0];

    // Byte enable and misalignment detection
    always_comb begin
        byte_enable = 4'b0000;
        misaligned  = 1'b0;

        case (ex_if_type_i)
            2'b00: begin // Byte access
                case (addr_lsb)
                    2'b00: byte_enable = 4'b0001;
                    2'b01: byte_enable = 4'b0010;
                    2'b10: byte_enable = 4'b0100;
                    2'b11: byte_enable = 4'b1000;
                    default: byte_enable = 4'b0000;
                endcase
                misaligned = 1'b0;
            end
            2'b01: begin // Halfword access
                if (addr_lsb == 2'b00) begin
                    byte_enable = 4'b0011;
                    misaligned  = 1'b0;
                end else if (addr_lsb == 2'b10) begin
                    byte_enable = 4'b1100;
                    misaligned  = 1'b0;
                end else begin
                    byte_enable = 4'b0000;
                    misaligned  = 1'b1;
                end
            end
            2'b10: begin // Word access
                if (addr_lsb == 2'b00) begin
                    byte_enable = 4'b1111;
                    misaligned  = 1'b0;
                end else begin
                    byte_enable = 4'b0000;
                    misaligned  = 1'b1;
                end
            end
            default: begin
                byte_enable = 4'b0000;
                misaligned  = 1'b1;
            end
        endcase
    end

    // Request accepted when LSU is ready, request is asserted, and not misaligned
    assign accepted = ex_if_ready_o & ex_if_req_i & ~misaligned;

    // State register
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
        end else begin
            state <= next_state;
        end
    end

    // Next state logic
    always_comb begin
        next_state = state;
        case (state)
            IDLE: begin
                if (accepted) begin
                    next_state = MEM_REQ;
                end
            end
            MEM_REQ: begin
                // dmem_req_o is asserted, wait for grant
                if (dmem_gnt_i) begin
                    if (req_we_r) begin
                        // Store: complete after grant
                        next_state = COMPLETE;
                    end else begin
                        // Load: wait for rvalid
                        next_state = WAIT_RVALID;
                    end
                end else begin
                    next_state = WAIT_GNT;
                end
            end
            WAIT_GNT: begin
                if (dmem_gnt_i) begin
                    if (req_we_r) begin
                        next_state = COMPLETE;
                    end else begin
                        next_state = WAIT_RVALID;
                    end
                end
            end
            WAIT_RVALID: begin
                if (dmem_rvalid_i) begin
                    next_state = COMPLETE;
                end
            end
            COMPLETE: begin
                next_state = IDLE;
            end
            default: next_state = IDLE;
        endcase
    end

    // Registered control signals for memory request
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            req_we_r    <= 1'b0;
            req_type_r  <= 2'b00;
            req_addr_r  <= 32'b0;
            req_wdata_r <= 32'b0;
            req_be_r    <= 4'b0;
        end else begin
            if (accepted) begin
                req_we_r    <= ex_if_we_i;
                req_type_r  <= ex_if_type_i;
                req_addr_r  <= eff_addr;
                req_wdata_r <= ex_if_wdata_i;
                req_be_r    <= byte_enable;
            end
        end
    end

    // dmem_req_o: asserted in MEM_REQ and WAIT_GNT states
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dmem_req_o       <= 1'b0;
            dmem_req_we_o    <= 1'b0;
            dmem_req_addr_o  <= 32'b0;
            dmem_req_be_o    <= 4'b0;
            dmem_req_wdata_o <= 32'b0;
        end else begin
            case (state)
                IDLE: begin
                    if (accepted) begin
                        // Will transition to MEM_REQ, setup memory signals
                        dmem_req_o       <= 1'b1;
                        dmem_req_we_o    <= ex_if_we_i;
                        dmem_req_addr_o  <= eff_addr;
                        dmem_req_be_o    <= byte_enable;
                        dmem_req_wdata_o <= ex_if_wdata_i;
                    end else begin
                        dmem_req_o       <= 1'b0;
                        dmem_req_we_o    <= 1'b0;
                        dmem_req_addr_o  <= 32'b0;
                        dmem_req_be_o    <= 4'b0;
                        dmem_req_wdata_o <= 32'b0;
                    end
                end
                MEM_REQ: begin
                    if (dmem_gnt_i) begin
                        // Deassert request after grant
                        dmem_req_o       <= 1'b0;
                        dmem_req_we_o    <= 1'b0;
                        dmem_req_addr_o  <= 32'b0;
                        dmem_req_be_o    <= 4'b0;
                        dmem_req_wdata_o <= 32'b0;
                    end
                    // else keep signals asserted
                end
                WAIT_GNT: begin
                    if (dmem_gnt_i) begin
                        dmem_req_o       <= 1'b0;
                        dmem_req_we_o    <= 1'b0;
                        dmem_req_addr_o  <= 32'b0;
                        dmem_req_be_o    <= 4'b0;
                        dmem_req_wdata_o <= 32'b0;
                    end
                    // else keep signals asserted
                end
                WAIT_RVALID: begin
                    // Already cleared, keep cleared
                    dmem_req_o       <= 1'b0;
                    dmem_req_we_o    <= 1'b0;
                    dmem_req_addr_o  <= 32'b0;
                    dmem_req_be_o    <= 4'b0;
                    dmem_req_wdata_o <= 32'b0;
                end
                COMPLETE: begin
                    dmem_req_o       <= 1'b0;
                    dmem_req_we_o    <= 1'b0;
                    dmem_req_addr_o  <= 32'b0;
                    dmem_req_be_o    <= 4'b0;
                    dmem_req_wdata_o <= 32'b0;
                end
                default: begin
                    dmem_req_o       <= 1'b0;
                    dmem_req_we_o    <= 1'b0;
                    dmem_req_addr_o  <= 32'b0;
                    dmem_req_be_o    <= 4'b0;
                    dmem_req_wdata_o <= 32'b0;
                end
            endcase
        end
    end

    // ex_if_ready_o: asserted in IDLE and COMPLETE states
    // Deasserted with one-cycle latency after accepting a request
    // Re-asserted with one-cycle latency after transaction completes
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ex_if_ready_o <= 1'b1;
        end else begin
            case (state)
                IDLE: begin
                    if (accepted) begin
                        ex_if_ready_o <= 1'b0;
                    end else begin
                        ex_if_ready_o <= 1'b1;
                    end
                end
                MEM_REQ: begin
                    ex_if_ready_o <= 1'b0;
                end
                WAIT_GNT: begin
                    ex_if_ready_o <= 1'b0;
                end
                WAIT_RVALID: begin
                    ex_if_ready_o <= 1'b0;
                end
                COMPLETE: begin
                    // Re-assert ready after complete (one cycle latency)
                    ex_if_ready_o <= 1'b1;
                end
                default: begin
                    ex_if_ready_o <= 1'b1;
                end
            endcase
        end
    end

    // Writeback interface
    // wb_if_rvalid_o asserted one cycle after dmem_rvalid_i
    // wb_if_rdata_o updated one cycle after dmem_rvalid_i, maintained until next load
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wb_if_rvalid_o <= 1'b0;
            wb_if_rdata_o  <= 32'b0;
        end else begin
            // Default: deassert rvalid
            wb_if_rvalid_o <= 1'b0;

            if (state == WAIT_RVALID && dmem_rvalid_i) begin
                wb_if_rvalid_o <= 1'b1;
                wb_if_rdata_o  <= dmem_rsp_rdata_i;
            end
        end
    end

endmodule
