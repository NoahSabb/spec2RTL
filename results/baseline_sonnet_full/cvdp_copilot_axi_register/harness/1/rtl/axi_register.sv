module axi_register #(
    parameter int ADDR_WIDTH = 32,
    parameter int DATA_WIDTH = 32
)(
    input  logic                        clk_i,
    input  logic                        rst_n_i,

    // Write Address Channel
    input  logic [ADDR_WIDTH-1:0]       awaddr_i,
    input  logic                        awvalid_i,
    output logic                        awready_o,

    // Write Data Channel
    input  logic [DATA_WIDTH-1:0]       wdata_i,
    input  logic                        wvalid_i,
    input  logic [(DATA_WIDTH/8)-1:0]   wstrb_i,
    output logic                        wready_o,

    // Write Response Channel
    output logic [1:0]                  bresp_o,
    output logic                        bvalid_o,
    input  logic                        bready_i,

    // Read Address Channel
    input  logic [ADDR_WIDTH-1:0]       araddr_i,
    input  logic                        arvalid_i,
    output logic                        arready_o,

    // Read Data Channel
    output logic [DATA_WIDTH-1:0]       rdata_o,
    output logic                        rvalid_o,
    output logic [1:0]                  rresp_o,
    input  logic                        rready_i,

    // Hardware Interface
    input  logic                        done_i,
    output logic [19:0]                 beat_o,
    output logic                        start_o,
    output logic                        writeback_o
);

    // Fixed ID value
    localparam logic [31:0] ID_VALUE = 32'h0001_0001;

    // Register offsets
    localparam logic [11:0] BEAT_OFFSET      = 12'h100;
    localparam logic [11:0] START_OFFSET     = 12'h200;
    localparam logic [11:0] DONE_OFFSET      = 12'h300;
    localparam logic [11:0] WRITEBACK_OFFSET = 12'h400;
    localparam logic [11:0] ID_OFFSET        = 12'h500;

    // Internal registers
    logic [19:0]            beat_reg;
    logic                   start_reg;
    logic                   done_reg;
    logic                   writeback_reg;

    // Write state machine
    typedef enum logic [1:0] {
        WR_IDLE,
        WR_ADDR,
        WR_DATA,
        WR_RESP
    } wr_state_t;

    wr_state_t wr_state;

    // Read state machine
    typedef enum logic [1:0] {
        RD_IDLE,
        RD_ADDR,
        RD_DATA
    } rd_state_t;

    rd_state_t rd_state;

    // Latched addresses
    logic [ADDR_WIDTH-1:0]  awaddr_lat;
    logic [ADDR_WIDTH-1:0]  araddr_lat;

    // Latched write data
    logic [DATA_WIDTH-1:0]  wdata_lat;
    logic [(DATA_WIDTH/8)-1:0] wstrb_lat;

    // Write response
    logic [1:0]             bresp_lat;

    // Sync done_i to internal register
    always_ff @(posedge clk_i or negedge rst_n_i) begin
        if (!rst_n_i) begin
            done_reg <= 1'b0;
        end else begin
            if (done_i) begin
                done_reg <= 1'b1;
            end
        end
    end

    // -----------------------------------------------------------------------
    // Write State Machine
    // -----------------------------------------------------------------------
    always_ff @(posedge clk_i or negedge rst_n_i) begin
        if (!rst_n_i) begin
            wr_state     <= WR_IDLE;
            awready_o    <= 1'b0;
            wready_o     <= 1'b0;
            bvalid_o     <= 1'b0;
            bresp_o      <= 2'b00;
            bresp_lat    <= 2'b00;
            awaddr_lat   <= '0;
            wdata_lat    <= '0;
            wstrb_lat    <= '0;
            beat_reg     <= 20'h0;
            start_reg    <= 1'b0;
            writeback_reg<= 1'b0;
        end else begin
            case (wr_state)
                WR_IDLE: begin
                    awready_o <= 1'b0;
                    wready_o  <= 1'b0;
                    bvalid_o  <= 1'b0;
                    if (awvalid_i) begin
                        awaddr_lat <= awaddr_i;
                        awready_o  <= 1'b1;
                        wr_state   <= WR_ADDR;
                    end
                end

                WR_ADDR: begin
                    awready_o <= 1'b0;
                    wready_o  <= 1'b1;
                    wr_state  <= WR_DATA;
                end

                WR_DATA: begin
                    if (wvalid_i) begin
                        wready_o  <= 1'b0;
                        wdata_lat <= wdata_i;
                        wstrb_lat <= wstrb_i;

                        // Determine if full write (all strobe bits set)
                        logic full_write;
                        full_write = &wstrb_i;

                        // Default response
                        bresp_lat <= 2'b00;

                        // Decode address and update registers
                        case (awaddr_lat[11:0])
                            BEAT_OFFSET: begin
                                if (full_write) begin
                                    beat_reg  <= wdata_i[19:0];
                                    bresp_lat <= 2'b00;
                                end else begin
                                    bresp_lat <= 2'b00; // partial write, no update
                                end
                            end

                            START_OFFSET: begin
                                if (full_write) begin
                                    start_reg <= wdata_i[0];
                                    bresp_lat <= 2'b00;
                                end else begin
                                    bresp_lat <= 2'b00;
                                end
                            end

                            DONE_OFFSET: begin
                                if (full_write) begin
                                    if (wdata_i[0]) begin
                                        done_reg <= 1'b0;
                                    end
                                    bresp_lat <= 2'b00;
                                end else begin
                                    bresp_lat <= 2'b00;
                                end
                            end

                            WRITEBACK_OFFSET: begin
                                if (full_write) begin
                                    writeback_reg <= wdata_i[0];
                                    bresp_lat     <= 2'b00;
                                end else begin
                                    bresp_lat <= 2'b00;
                                end
                            end

                            ID_OFFSET: begin
                                // Read-only register: return SLVERR
                                bresp_lat <= 2'b10;
                            end

                            default: begin
                                // Invalid address
                                bresp_lat <= 2'b10;
                            end
                        endcase

                        bvalid_o  <= 1'b1;
                        bresp_o   <= bresp_lat;
                        wr_state  <= WR_RESP;
                    end
                end

                WR_RESP: begin
                    bresp_o <= bresp_lat;
                    if (bready_i) begin
                        bvalid_o  <= 1'b0;
                        wr_state  <= WR_IDLE;
                    end
                end

                default: begin
                    wr_state <= WR_IDLE;
                end
            endcase
        end
    end

    // -----------------------------------------------------------------------
    // Read State Machine
    // -----------------------------------------------------------------------
    always_ff @(posedge clk_i or negedge rst_n_i) begin
        if (!rst_n_i) begin
            rd_state   <= RD_IDLE;
            arready_o  <= 1'b0;
            rvalid_o   <= 1'b0;
            rdata_o    <= '0;
            rresp_o    <= 2'b00;
            araddr_lat <= '0;
        end else begin
            case (rd_state)
                RD_IDLE: begin
                    arready_o <= 1'b0;
                    rvalid_o  <= 1'b0;
                    if (arvalid_i) begin
                        araddr_lat <= araddr_i;
                        arready_o  <= 1'b1;
                        rd_state   <= RD_ADDR;
                    end
                end

                RD_ADDR: begin
                    arready_o <= 1'b0;

                    // Decode read address and prepare data
                    case (araddr_lat[11:0])
                        BEAT_OFFSET: begin
                            rdata_o  <= {{(DATA_WIDTH-20){1'b0}}, beat_reg};
                            rresp_o  <= 2'b00;
                        end

                        START_OFFSET: begin
                            rdata_o  <= {{(DATA_WIDTH-1){1'b0}}, start_reg};
                            rresp_o  <= 2'b00;
                        end

                        DONE_OFFSET: begin
                            rdata_o  <= {{(DATA_WIDTH-1){1'b0}}, done_reg};
                            rresp_o  <= 2'b00;
                        end

                        WRITEBACK_OFFSET: begin
                            rdata_o  <= {{(DATA_WIDTH-1){1'b0}}, writeback_reg};
                            rresp_o  <= 2'b00;
                        end

                        ID_OFFSET: begin
                            rdata_o  <= {{(DATA_WIDTH-32){1'b0}}, ID_VALUE};
                            rresp_o  <= 2'b00;
                        end

                        default: begin
                            rdata_o  <= '0;
                            rresp_o  <= 2'b10;
                        end
                    endcase

                    rvalid_o <= 1'b1;
                    rd_state <= RD_DATA;
                end

                RD_DATA: begin
                    if (rready_i) begin
                        rvalid_o <= 1'b0;
                        rd_state <= RD_IDLE;
                    end
                end

                default: begin
                    rd_state <= RD_IDLE;
                end
            endcase
        end
    end

    // -----------------------------------------------------------------------
    // Output assignments
    // -----------------------------------------------------------------------
    assign beat_o      = beat_reg;
    assign start_o     = start_reg;
    assign writeback_o = writeback_reg;

endmodule
