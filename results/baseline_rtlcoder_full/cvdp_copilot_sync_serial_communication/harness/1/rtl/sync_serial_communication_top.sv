<s> module sync_serial_communication_top(
    input clk, reset_n,
    input [2:0] sel, data_in, data_out,
    output reg done
);

reg [63:0] parallel_data;
reg [1:0] state = 2'b00;
wire serial_clk = 1'b0;
tx_block tx_inst(.clk(clk), .reset_n(reset_n), .data_in(data_in), .serial_out(serial_out), .sel(sel), .serial_clk(serial_clk), .done(tx_done));
module rx_block (.clk(clk), .reset_n(reset_n), .data_in(serial_out), .sel(sel), .data_out(parallel_data), .done(rx_done));
assign data_out = parallel_data;

always @ (posedge clk or negedge reset_n) begin
    if (~reset_n) begin
        {state, tx_done} <= 2'b00_1;
        done <= 1'b0;
    end else if ({tx_done & sel[0], ~sel[1:0]}) begin
        case (state)
            2'd0: state <= 2'b00;
            2'd1: {serial_clk, parallel_data} = 2'b01;
            default: state <= 2'd0;
        endcase
    end else if ({rx_done & sel[1]}) begin
        case (state)
            2'd0: state <= 2'b01;
            2'd1: {serial_clk, parallel_data} = 2'b10;
            default: state <= 2'd0;
        endcase
    end else begin
        state <= 2'd0;
        tx_done <= 1'b0;
        rx_done <= 1'b0;
    end
end

always @ (posedge clk or negedge reset_n) begin
    if (~reset_n) begin
        serial_clk <= 1'b0;
    end else if (state == 2'd1) begin
        serial_clk <= ~serial_clk;
    end else if ({sel[1], sel != 3'h4}) begin
    // Default state is sel==3 in which no data is sent, hence no need for the gated clock to be asserted
        serial_clk <= 1'b0;
    end
end

assign rx_done = done;
always @ (posedge clk or negedge reset_n) begin
    if (~reset_n) begin
        done <= 1'b0;
    end else if (state == 2'd1 || state == 2'd2) begin
        done <= 1'b1;
    end else begin
        done <= 1'b0;
    end
end

endmodule

// Transmitter block
module tx_block (
    input clk, reset_n,
    input [2:0] sel, data_in, // 0 represents no transmission
    output reg serial_out, // Serialized output from LSB-first parallel input
    output reg serial_clk,
    output reg done // A HIGH on this signal indicates the availability of a stable result; wait for the rx_block to do so. Default value is 1'b0
);
always @ (posedge clk or negedge reset_n) begin
    if (~reset_n) begin
        {serial_clk, serial_out} <= 2'b00;
        done <= 1'b0;
    end else if ({sel[1:0], sel != 3'd4}) begin
        // Transmitter will only go into active state when one of the valid data is chosen. Default value is 0
       serial_out = data_in[2] ? 1'b0 : 1'b1;
       {serial_clk, serial_out} <= 2'b10;
       done <= 1'b1;
    end else begin
        // Default case when sel is not one of the valid values
       serial_out = 1'bx;
       serial_clk <= 1'b0;
       done <= 1'b0;
    end
end

endmodule
// Receiver block
module rx_block (
    input clk, reset_n,
    input [2:0] sel, data_in, // 0 represents no reception. This input is received after sampling has happened and is used to reconstruct the final output in the receiver (RX) only when done = 1.
    input serial_clk,
    output reg [63:0] data_out,
    output reg rx_done
);
always @ (posedge clk or negedge reset_n) begin
    // rx_done is asynchronous with the transmitter, hence asserted on the first edge after transmission.
    if (~reset_n) begin
        data_out = 64'h0;
        rx_done <= 1'b0;
    end else if ({sel[1:0], sel != 3'd4}) begin
       case (sel)
           3'h0: data_out = {56'h0, data_in[7:0]};
           3'h1: data_out = {48'h0, data_in[15:0]};
           3'h2: data_out = {40'h0, data_in[31:0]};
           3'h3: data_out = {32'h0, data_in[63:0]};
           default: data_out = 64'h0; // Default case for an invalid value of sel
       endcase
       rx_done <= (|data_out);  // A HIGH in this signal for one clock cycle represents the availability of the stable result of the receiver, default value is 1'b0
    end else if ({sel[1], ~rx_done}) begin
      // Do nothing as no data has to be received as long as rx_done is not ready on the first edge.
      // If any valid case is triggered after that(i.e tx_block has done transmitting), the rx_block will start sampling from the next rising clock edge
        $display("sel %h  -- resetting rx_done", sel);
        rx_done <= 1'b0;
    end else if ({~serial_clk & ~rx_done}) begin
      // Serialized data has stopped (either HIGH or LOW) from the transmitter, hence capture it now.
        case (sel)
            3'h0: data_out = {56'h0, data_in[7:0], serial_out};
            3'h1: data_out = {48'h0, data_in[15:0], serial_out};
            3'h2: data_out = {40'h0, data_in[31:0], serial_out};
            3'h3: data_out = {32'h0, data_in[63:0]};  // Default case for an invalid value of sel. Hence this data is always appended to the end if rx_done == 0
            default: data_out = 64'h0;
        endcase
       $display("sel %h  -- data_out %x serial_out %d -- resetting rx_done", sel, data_out[63:0],serial_out);
        rx_done <= 1'b1;
    end else begin
      rx_done <= 1'b0;   // When this case is reached, it means the default state has been chosen, hence no data_out has to be computed. Just reset rx_done and wait for the next edge after another valid sel is received.
    end
end

endmodule