// rtl/packet_controller.sv

module packet_controller (
    input  logic       clk,
    input  logic       rst,
    input  logic       rx_valid_i,
    input  logic [7:0] rx_data_8_i,
    input  logic       tx_done_tick_i,
    output logic       tx_start_o,
    output logic [7:0] tx_data_8_o
);

    // FSM States
    typedef enum logic [2:0] {
        S_IDLE           = 3'd0,
        S_GOT_8_BYTES    = 3'd1,
        S_RECV_CHECKSUM  = 3'd2,
        S_BUILD_RESPONSE = 3'd3,
        S_SEND_FIRST_BYTE= 3'd4,
        S_RESPONSE_READY = 3'd5
    } state_t;

    state_t state, next_state;

    // RX buffer: 8 bytes
    logic [7:0] rx_buf [0:7];
    logic [2:0] byte_cnt;

    // Parsed fields
    logic [15:0] header;
    logic [15:0] num1, num2;
    logic [7:0]  opcode;
    logic [7:0]  rx_checksum;

    // Checksum computation
    logic [7:0] computed_checksum;

    // Response packet: 5 bytes (header 2 bytes + result 2 bytes + checksum 1 byte)
    logic [7:0] resp_buf [0:4];
    logic [2:0] tx_byte_cnt;

    // Result
    logic [15:0] result;

    // -------------------------
    // RX byte accumulation
    // -------------------------
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            byte_cnt <= 3'd0;
            for (int i = 0; i < 8; i++) rx_buf[i] <= 8'd0;
        end else begin
            case (state)
                S_IDLE: begin
                    if (rx_valid_i) begin
                        rx_buf[byte_cnt] <= rx_data_8_i;
                        byte_cnt <= byte_cnt + 3'd1;
                    end
                end
                S_RECV_CHECKSUM: begin
                    // Reset byte counter for next packet
                    byte_cnt <= 3'd0;
                end
                default: begin
                    // Keep byte_cnt as is unless we go back to IDLE
                    if (next_state == S_IDLE) begin
                        byte_cnt <= 3'd0;
                    end
                end
            endcase
        end
    end

    // -------------------------
    // TX byte counter
    // -------------------------
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            tx_byte_cnt <= 3'd0;
        end else begin
            case (state)
                S_SEND_FIRST_BYTE: begin
                    tx_byte_cnt <= 3'd1;
                end
                S_RESPONSE_READY: begin
                    if (tx_done_tick_i) begin
                        tx_byte_cnt <= tx_byte_cnt + 3'd1;
                    end
                end
                default: begin
                    tx_byte_cnt <= 3'd0;
                end
            endcase
        end
    end

    // -------------------------
    // FSM State Register
    // -------------------------
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            state <= S_IDLE;
        end else begin
            state <= next_state;
        end
    end

    // -------------------------
    // Parse fields from rx_buf
    // -------------------------
    always_comb begin
        header      = {rx_buf[0], rx_buf[1]};
        num1        = {rx_buf[2], rx_buf[3]};
        num2        = {rx_buf[4], rx_buf[5]};
        opcode      = rx_buf[6];
        rx_checksum = rx_buf[7];
    end

    // -------------------------
    // Checksum Validation
    // (sum of all 8 bytes mod 256 == 0)
    // -------------------------
    always_comb begin
        computed_checksum = rx_buf[0] + rx_buf[1] + rx_buf[2] + rx_buf[3] +
                            rx_buf[4] + rx_buf[5] + rx_buf[6] + rx_buf[7];
    end

    // -------------------------
    // Arithmetic Operation
    // -------------------------
    always_comb begin
        case (opcode)
            8'h00: result = num1 + num2;
            8'h01: result = num1 - num2;
            default: result = 16'd0;
        endcase
    end

    // -------------------------
    // Build Response Buffer
    // -------------------------
    // Response: [0xAB, 0xCD, result_hi, result_lo, checksum]
    // checksum = -(0xAB + 0xCD + result_hi + result_lo) mod 256
    logic [7:0] resp_checksum;
    always_comb begin
        resp_checksum = -(8'hAB + 8'hCD + result[15:8] + result[7:0]);
    end

    // -------------------------
    // FSM Next State Logic
    // -------------------------
    always_comb begin
        next_state = state;
        case (state)
            S_IDLE: begin
                if (byte_cnt == 3'd7 && rx_valid_i) begin
                    next_state = S_GOT_8_BYTES;
                end
            end
            S_GOT_8_BYTES: begin
                if (header == 16'hBACD) begin
                    next_state = S_RECV_CHECKSUM;
                end else begin
                    next_state = S_IDLE;
                end
            end
            S_RECV_CHECKSUM: begin
                if (computed_checksum == 8'd0) begin
                    next_state = S_BUILD_RESPONSE;
                end else begin
                    next_state = S_IDLE;
                end
            end
            S_BUILD_RESPONSE: begin
                next_state = S_SEND_FIRST_BYTE;
            end
            S_SEND_FIRST_BYTE: begin
                next_state = S_RESPONSE_READY;
            end
            S_RESPONSE_READY: begin
                if (tx_done_tick_i && tx_byte_cnt == 3'd4) begin
                    next_state = S_IDLE;
                end
            end
            default: next_state = S_IDLE;
        endcase
    end

    // -------------------------
    // Response Buffer Register
    // -------------------------
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            resp_buf[0] <= 8'd0;
            resp_buf[1] <= 8'd0;
            resp_buf[2] <= 8'd0;
            resp_buf[3] <= 8'd0;
            resp_buf[4] <= 8'd0;
        end else if (state == S_BUILD_RESPONSE) begin
            resp_buf[0] <= 8'hAB;
            resp_buf[1] <= 8'hCD;
            resp_buf[2] <= result[15:8];
            resp_buf[3] <= result[7:0];
            resp_buf[4] <= resp_checksum;
        end
    end

    // -------------------------
    // Output Logic
    // -------------------------
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            tx_start_o  <= 1'b0;
            tx_data_8_o <= 8'd0;
        end else begin
            case (state)
                S_SEND_FIRST_BYTE: begin
                    tx_start_o  <= 1'b1;
                    tx_data_8_o <= resp_buf[0];
                end
                S_RESPONSE_READY: begin
                    tx_start_o <= 1'b1;
                    if (tx_done_tick_i) begin
                        if (tx_byte_cnt < 3'd4) begin
                            tx_data_8_o <= resp_buf[tx_byte_cnt];
                        end else begin
                            tx_start_o  <= 1'b0;
                            tx_data_8_o <= 8'd0;
                        end
                    end
                end
                default: begin
                    tx_start_o  <= 1'b0;
                    tx_data_8_o <= 8'd0;
                end
            endcase
        end
    end

endmodule
