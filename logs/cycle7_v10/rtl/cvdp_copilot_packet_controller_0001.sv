module packet_controller (
    input wire clk,
    input wire rst,
    input wire rx_valid_i,
    input wire [7:0] rx_data_8_i,
    input wire tx_done_tick_i,
    output reg tx_start_o,
    output reg [7:0] tx_data_8_o
);

    // Define states
    localparam S_IDLE            = 3'd0;
    localparam S_GOT_8_BYTES     = 3'd1;
    localparam S_RECV_CHECKSUM   = 3'd2;
    localparam S_BUILD_RESPONSE  = 3'd3;
    localparam S_SEND_FIRST_BYTE = 3'd4;
    localparam S_RESPONSE_READY  = 3'd5;
    localparam S_SEND_LAST_BYTE  = 3'd6;

    reg [2:0] current_state;

    // Buffer to store received data (8 bytes)
    reg [7:0] rx_buffer [0:7];
    reg [3:0] rx_count;

    // Variables for packet processing
    reg [15:0] header;
    reg [15:0] num1, num2;
    reg [7:0]  opcode;
    reg [7:0]  rx_checksum, computed_checksum;
    reg [15:0] response_payload;
    reg [7:0]  tx_buffer [0:4];
    reg [2:0]  tx_count;

    // Validity flag
    reg packet_valid;

    // Wire for checksum computation
    wire [7:0] w_computed_checksum;
    assign w_computed_checksum = (8'd0 - (rx_buffer[0] + rx_buffer[1] + rx_buffer[2] +
                                          rx_buffer[3] + rx_buffer[4] + rx_buffer[5] +
                                          rx_buffer[6]));

    // Main FSM
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            current_state  <= S_IDLE;
            rx_count       <= 0;
            tx_start_o     <= 0;
            tx_data_8_o    <= 0;
            tx_count       <= 0;
            header         <= 0;
            num1           <= 0;
            num2           <= 0;
            opcode         <= 0;
            rx_checksum    <= 0;
            computed_checksum <= 0;
            response_payload  <= 0;
            packet_valid   <= 0;
            rx_buffer[0] <= 0; rx_buffer[1] <= 0; rx_buffer[2] <= 0; rx_buffer[3] <= 0;
            rx_buffer[4] <= 0; rx_buffer[5] <= 0; rx_buffer[6] <= 0; rx_buffer[7] <= 0;
            tx_buffer[0] <= 0; tx_buffer[1] <= 0; tx_buffer[2] <= 0;
            tx_buffer[3] <= 0; tx_buffer[4] <= 0;
        end else begin
            case (current_state)
                S_IDLE: begin
                    tx_start_o <= 0;
                    tx_count   <= 0;
                    if (rx_valid_i) begin
                        rx_buffer[rx_count] <= rx_data_8_i;
                        if (rx_count == 7) begin
                            rx_count      <= 0;
                            current_state <= S_GOT_8_BYTES;
                        end else begin
                            rx_count <= rx_count + 1;
                        end
                    end
                end

                S_GOT_8_BYTES: begin
                    header            <= {rx_buffer[0], rx_buffer[1]};
                    num1              <= {rx_buffer[2], rx_buffer[3]};
                    num2              <= {rx_buffer[4], rx_buffer[5]};
                    opcode            <= rx_buffer[6];
                    rx_checksum       <= rx_buffer[7];
                    computed_checksum <= w_computed_checksum;
                    current_state     <= S_RECV_CHECKSUM;
                end

                S_RECV_CHECKSUM: begin
                    if (header == 16'hBACD && rx_checksum == computed_checksum) begin
                        current_state <= S_BUILD_RESPONSE;
                    end else begin
                        current_state <= S_IDLE;
                    end
                end

                S_BUILD_RESPONSE: begin
                    // Compute result
                    case (opcode)
                        8'h00: response_payload <= num1 + num2;
                        8'h01: response_payload <= num1 - num2;
                        default: response_payload <= 16'd0;
                    endcase
                    current_state <= S_SEND_FIRST_BYTE;
                end

                S_SEND_FIRST_BYTE: begin
                    // Build tx_buffer now that response_payload is ready
                    tx_buffer[0] <= 8'hAB;
                    tx_buffer[1] <= 8'hCD;
                    tx_buffer[2] <= response_payload[15:8];
                    tx_buffer[3] <= response_payload[7:0];
                    tx_buffer[4] <= 8'd0 - (8'hAB + 8'hCD + response_payload[15:8] + response_payload[7:0]);
                    // Assert tx_start and send first byte
                    tx_start_o  <= 1;
                    tx_data_8_o <= 8'hAB;
                    tx_count    <= 1;
                    current_state <= S_RESPONSE_READY;
                end

                S_RESPONSE_READY: begin
                    if (tx_done_tick_i) begin
                        tx_data_8_o <= tx_buffer[tx_count];
                        if (tx_count == 4) begin
                            // Send last byte but keep tx_start_o high
                            // Transition to S_SEND_LAST_BYTE to wait for final tx_done_tick_i
                            tx_start_o    <= 1;
                            current_state <= S_SEND_LAST_BYTE;
                        end else begin
                            tx_count <= tx_count + 1;
                        end
                    end
                end

                S_SEND_LAST_BYTE: begin
                    if (tx_done_tick_i) begin
                        tx_start_o    <= 0;
                        current_state <= S_IDLE;
                    end
                end

                default: begin
                    current_state <= S_IDLE;
                end
            endcase
        end
    end

endmodule
