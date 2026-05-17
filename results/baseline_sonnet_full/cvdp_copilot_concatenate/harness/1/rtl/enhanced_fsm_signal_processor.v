module enhanced_fsm_signal_processor (
    input  wire        i_clk,
    input  wire        i_rst_n,
    input  wire        i_enable,
    input  wire        i_clear,
    input  wire        i_ack,
    input  wire        i_fault,
    input  wire [4:0]  i_vector_1,
    input  wire [4:0]  i_vector_2,
    input  wire [4:0]  i_vector_3,
    input  wire [4:0]  i_vector_4,
    input  wire [4:0]  i_vector_5,
    input  wire [4:0]  i_vector_6,
    output reg         o_ready,
    output reg         o_error,
    output reg  [1:0]  o_fsm_status,
    output reg  [7:0]  o_vector_1,
    output reg  [7:0]  o_vector_2,
    output reg  [7:0]  o_vector_3,
    output reg  [7:0]  o_vector_4
);

    // State encoding
    localparam [1:0] IDLE    = 2'b00;
    localparam [1:0] PROCESS = 2'b01;
    localparam [1:0] READY   = 2'b10;
    localparam [1:0] FAULT   = 2'b11;

    reg [1:0] current_state;

    // 32-bit concatenation bus
    wire [31:0] concat_bus;
    assign concat_bus = {i_vector_1, i_vector_2, i_vector_3, i_vector_4, i_vector_5, i_vector_6, 2'b11};

    always @(posedge i_clk or negedge i_rst_n) begin
        if (!i_rst_n) begin
            current_state <= IDLE;
            o_ready       <= 1'b0;
            o_error       <= 1'b0;
            o_fsm_status  <= IDLE;
            o_vector_1    <= 8'h00;
            o_vector_2    <= 8'h00;
            o_vector_3    <= 8'h00;
            o_vector_4    <= 8'h00;
        end else begin
            case (current_state)
                IDLE: begin
                    o_ready      <= 1'b0;
                    o_error      <= 1'b0;
                    o_vector_1   <= 8'h00;
                    o_vector_2   <= 8'h00;
                    o_vector_3   <= 8'h00;
                    o_vector_4   <= 8'h00;
                    if (i_fault) begin
                        current_state <= FAULT;
                        o_fsm_status  <= FAULT;
                        o_error       <= 1'b1;
                    end else if (i_enable) begin
                        current_state <= PROCESS;
                        o_fsm_status  <= PROCESS;
                    end
                end

                PROCESS: begin
                    if (i_fault) begin
                        current_state <= FAULT;
                        o_fsm_status  <= FAULT;
                        o_error       <= 1'b1;
                        o_vector_1    <= 8'h00;
                        o_vector_2    <= 8'h00;
                        o_vector_3    <= 8'h00;
                        o_vector_4    <= 8'h00;
                    end else begin
                        // Perform concatenation and splitting
                        o_vector_1    <= concat_bus[31:24];
                        o_vector_2    <= concat_bus[23:16];
                        o_vector_3    <= concat_bus[15:8];
                        o_vector_4    <= concat_bus[7:0];
                        current_state <= READY;
                        o_fsm_status  <= READY;
                    end
                end

                READY: begin
                    if (i_fault) begin
                        current_state <= FAULT;
                        o_fsm_status  <= FAULT;
                        o_error       <= 1'b1;
                        o_ready       <= 1'b0;
                        o_vector_1    <= 8'h00;
                        o_vector_2    <= 8'h00;
                        o_vector_3    <= 8'h00;
                        o_vector_4    <= 8'h00;
                    end else begin
                        o_ready <= 1'b1;
                        if (i_ack) begin
                            current_state <= IDLE;
                            o_fsm_status  <= IDLE;
                            o_ready       <= 1'b0;
                        end
                    end
                end

                FAULT: begin
                    o_error    <= 1'b1;
                    o_ready    <= 1'b0;
                    o_vector_1 <= 8'h00;
                    o_vector_2 <= 8'h00;
                    o_vector_3 <= 8'h00;
                    o_vector_4 <= 8'h00;
                    if (i_clear && !i_fault) begin
                        current_state <= IDLE;
                        o_fsm_status  <= IDLE;
                        o_error       <= 1'b0;
                    end
                end

                default: begin
                    current_state <= IDLE;
                    o_fsm_status  <= IDLE;
                    o_ready       <= 1'b0;
                    o_error       <= 1'b0;
                    o_vector_1    <= 8'h00;
                    o_vector_2    <= 8'h00;
                    o_vector_3    <= 8'h00;
                    o_vector_4    <= 8'h00;
                end
            endcase
        end
    end

endmodule
