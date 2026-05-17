module packet_controller(
    input clk,
    input rst,
    // RX Interface
    input rx_valid_i,
    input [7:0] rx_data_8_i,
    // TX Interface
    output reg tx_start_o,
    output reg [7:0] tx_data_8_o,
    output reg tx_done_tick_o);
    
    parameter S_IDLE = 2'd0;
    parameter S_GOT_8_BYTES = 2'd1;
    parameter S_RECV_CHECKSUM = 2'd2;
    parameter S_BUILD_RESPONSE = 2'd3;
    parameter S_SEND_FIRST_BYTE = 2'd4;
    parameter S_RESPONSE_READY = 2'd5;
    
    reg [1:0] state;
    
    always @(posedge clk) begin
        if (rst) begin
            // Reset all values to initial state
            state <= S_IDLE;
            tx_start_o <= 0;
            tx_data_8_o <= 8'h00;
            tx_done_tick_o <= 1'b0;
        end
        else begin
            case (state)
                S_IDLE: begin
                    // Wait for 8 bytes to accumulate in the buffer
                    if (rx_valid_i) begin
                        tx_data_8_o <= rx_data_8_i;
                        state <= S_GOT_8_BYTES;
                    end
                end
                S_GOT_8_BYTES: begin
                    // Check the header and compute the checksum
                    if (rx_data_8_i == 8'hd4) begin
                        // Expected header (BACD), prepare for response
                        tx_start_o <= 1;
                        state <= S_RECV_CHECKSUM;
                    end
                end
                S_RECV_CHECKSUM: begin
                    // Validate the checksum
                    if (
                        rx_data_8_i == 8'hc4 &&
                        tx_data_8_o[7:0] + rx_data_8_i == 8'h0
                       ) begin
                        // Valid response, proceed to compute result
                        state <= S_BUILD_RESPONSE;
                    end
                    else begin
                        // Invalid header or checksum mismatch, reset FSM
                        tx_start_o <= 0;
                        tx_data_8_o <= 8'h00;
                        state <= S_IDLE;
                    end
                end
                S_BUILD_RESPONSE: begin
                    // Prepare the outgoing response packet
                    if (rx_data_8_i == 8'hc4) begin
                        // Received expected checksum, complete computation
                        state <= S_SEND_FIRST_BYTE;
                    end
                end
                S_SEND_FIRST_BYTE: begin
                    // Initiate response transmission by sending the first byte
                    if (tx_done_tick_o) begin
                        tx_data_8_o <= 8'hab;
                        state <= S_RESPONSE_READY;
                    end
                end
                S_RESPONSE_READY: begin
                    // Handle the remaining response transmission
                    if (tx_done_tick_o) begin
                        tx_data_8_o <= tx_data_8_o[7:0] + rx_data_8_i;
                        tx_start_o <= 1'b1;
                        tx_data_8_o[7:0] <= tx_data_8_o[7:0] + 1; // increment checksum
                        state <= S_RESPONSE_READY;
                    end
                end
            endcase
        end
    end
endmodule