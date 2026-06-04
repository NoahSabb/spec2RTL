module load_store_unit (
    // Clock and Reset
    input wire clk,
    input wire rst_n,

    // Data-Cache Interface
    output reg dmem_req_o,
    input wire dmem_gnt_i,
    output reg [31:0] dmem_req_addr_o,
    output reg dmem_req_we_o,
    output reg [3:0] dmem_req_be_o,
    output reg [31:0] dmem_req_wdata_o,
    input wire dmem_rvalid_i,
    input wire [31:0] dmem_rsp_rdata_i,

    // Execution Stage Interface
    input wire ex_if_req_i,
    input wire ex_if_we_i,
    input wire [1:0] ex_if_type_i,
    input wire [31:0] ex_if_wdata_i,
    input wire [31:0] ex_if_addr_base_i,
    input wire [31:0] ex_if_addr_offset_i,
    output reg ex_if_ready_o,

    // Writeback Interface
    output reg [31:0] wb_if_rdata_o,
    output reg wb_if_rvalid_o
);

    // Internal signals
    wire [31:0] req_addr;
    wire [3:0]  req_be;
    reg  req_we;

    // Calculate the effective address combinationally
    assign req_addr = ex_if_addr_base_i + ex_if_addr_offset_i;

    // Determine byte enable signals based on data type and alignment
    assign req_be = (ex_if_type_i == 2'b00) ? (
                        (req_addr[1:0] == 2'b00) ? 4'b0001 :
                        (req_addr[1:0] == 2'b01) ? 4'b0010 :
                        (req_addr[1:0] == 2'b10) ? 4'b0100 :
                                                    4'b1000
                    ) :
                    (ex_if_type_i == 2'b01) ? (
                        (req_addr[1:0] == 2'b00) ? 4'b0011 :
                        (req_addr[1:0] == 2'b10) ? 4'b1100 :
                                                    4'b0000
                    ) :
                    (ex_if_type_i == 2'b10) ? (
                        (req_addr[1:0] == 2'b00) ? 4'b1111 :
                                                    4'b0000
                    ) : 4'b0000;

    // FSM states
    typedef enum logic [1:0] {
        IDLE,
        REQUEST_SENT,
        WAIT_RVALID
    } state_t;

    state_t state;

    // Sequential FSM and output logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state           <= IDLE;
            dmem_req_o      <= 1'b0;
            dmem_req_addr_o <= 32'b0;
            dmem_req_we_o   <= 1'b0;
            dmem_req_be_o   <= 4'b0;
            dmem_req_wdata_o<= 32'b0;
            ex_if_ready_o   <= 1'b1;
            wb_if_rdata_o   <= 32'b0;
            wb_if_rvalid_o  <= 1'b0;
            req_we          <= 1'b0;
        end else begin
            // Default: clear rvalid each cycle
            wb_if_rvalid_o <= 1'b0;

            case (state)
                IDLE: begin
                    if (ex_if_req_i && ex_if_ready_o && (req_be != 4'b0000)) begin
                        // Accept request - latch to dmem outputs next cycle
                        dmem_req_o       <= 1'b1;
                        dmem_req_addr_o  <= req_addr;
                        dmem_req_we_o    <= ex_if_we_i;
                        dmem_req_be_o    <= req_be;
                        dmem_req_wdata_o <= ex_if_wdata_i;
                        ex_if_ready_o    <= 1'b0;
                        req_we           <= ex_if_we_i;
                        state            <= REQUEST_SENT;
                    end
                end

                REQUEST_SENT: begin
                    if (dmem_gnt_i) begin
                        // Clear dmem request signals
                        dmem_req_o       <= 1'b0;
                        dmem_req_addr_o  <= 32'b0;
                        dmem_req_we_o    <= 1'b0;
                        dmem_req_be_o    <= 4'b0;
                        dmem_req_wdata_o <= 32'b0;

                        if (req_we) begin
                            // Store: complete immediately, reassert ready
                            ex_if_ready_o <= 1'b1;
                            state         <= IDLE;
                        end else begin
                            // Load: wait for rvalid
                            state <= WAIT_RVALID;
                        end
                    end
                end

                WAIT_RVALID: begin
                    if (dmem_rvalid_i) begin
                        wb_if_rdata_o  <= dmem_rsp_rdata_i;
                        wb_if_rvalid_o <= 1'b1;
                        ex_if_ready_o  <= 1'b1;
                        state          <= IDLE;
                    end
                end

                default: begin
                    state <= IDLE;
                end
            endcase
        end
    end

endmodule
