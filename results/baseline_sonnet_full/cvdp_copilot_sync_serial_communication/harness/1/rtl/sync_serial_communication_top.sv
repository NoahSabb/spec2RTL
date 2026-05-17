// rtl/sync_serial_communication_top.sv

module tx_block (
    input  logic        clk,
    input  logic        reset_n,
    input  logic [63:0] data_in,
    input  logic [2:0]  sel,
    output logic        serial_out,
    output logic        done,
    output logic        serial_clk
);

    logic [6:0]  bit_count;
    logic [6:0]  total_bits;
    logic [63:0] shift_reg;
    logic        transmitting;

    always_comb begin
        case (sel)
            3'h1: total_bits = 7'd8;
            3'h2: total_bits = 7'd16;
            3'h3: total_bits = 7'd32;
            3'h4: total_bits = 7'd64;
            default: total_bits = 7'd0;
        endcase
    end

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            serial_out   <= 1'b0;
            done         <= 1'b0;
            bit_count    <= 7'd0;
            shift_reg    <= 64'd0;
            transmitting <= 1'b0;
        end else begin
            if (!transmitting && !done) begin
                if (total_bits > 0) begin
                    // Load data and start transmission
                    case (sel)
                        3'h1: shift_reg <= {56'h0, data_in[7:0]};
                        3'h2: shift_reg <= {48'h0, data_in[15:0]};
                        3'h3: shift_reg <= {32'h0, data_in[31:0]};
                        3'h4: shift_reg <= data_in[63:0];
                        default: shift_reg <= 64'd0;
                    endcase
                    bit_count    <= 7'd0;
                    transmitting <= 1'b1;
                    done         <= 1'b0;
                end
            end else if (transmitting) begin
                if (bit_count < total_bits) begin
                    // Transmit MSB first
                    serial_out <= shift_reg[total_bits - 1 - bit_count];
                    bit_count  <= bit_count + 1;
                end
                if (bit_count == total_bits - 1) begin
                    // Last bit being transmitted
                end
                if (bit_count == total_bits) begin
                    transmitting <= 1'b0;
                    done         <= 1'b1;
                    serial_out   <= 1'b0;
                end
            end else if (done) begin
                done <= 1'b0;
            end
        end
    end

    // Gated clock: only active during transmission
    assign serial_clk = clk & transmitting;

endmodule


module rx_block (
    input  logic        clk,
    input  logic        reset_n,
    input  logic        data_in,
    input  logic [2:0]  sel,
    input  logic        serial_clk,
    output logic [63:0] data_out,
    output logic        done
);

    logic [6:0]  bit_count;
    logic [6:0]  total_bits;
    logic [63:0] shift_reg;
    logic        prev_serial_clk;
    logic        serial_clk_posedge;
    logic        receiving;
    logic        was_receiving;

    always_comb begin
        case (sel)
            3'h1: total_bits = 7'd8;
            3'h2: total_bits = 7'd16;
            3'h3: total_bits = 7'd32;
            3'h4: total_bits = 7'd64;
            default: total_bits = 7'd0;
        endcase
    end

    assign serial_clk_posedge = serial_clk & ~prev_serial_clk;

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            data_out         <= 64'd0;
            done             <= 1'b0;
            bit_count        <= 7'd0;
            shift_reg        <= 64'd0;
            prev_serial_clk  <= 1'b0;
            receiving        <= 1'b0;
            was_receiving    <= 1'b0;
        end else begin
            prev_serial_clk <= serial_clk;
            done <= 1'b0;

            if (serial_clk_posedge && total_bits > 0) begin
                receiving <= 1'b1;
                was_receiving <= 1'b1;
                // Shift in data MSB first
                shift_reg <= {shift_reg[62:0], data_in};
                bit_count <= bit_count + 1;

                if (bit_count == total_bits - 1) begin
                    // This is the last bit
                    receiving <= 1'b0;
                end
            end

            // Detect end of reception: serial_clk goes low after receiving
            if (was_receiving && !serial_clk && !prev_serial_clk && !receiving) begin
                // Reconstruct data_out
                case (sel)
                    3'h0: data_out <= 64'h0;
                    3'h1: data_out <= {56'h0, shift_reg[7:0]};
                    3'h2: data_out <= {48'h0, shift_reg[15:0]};
                    3'h3: data_out <= {32'h0, shift_reg[31:0]};
                    3'h4: data_out <= shift_reg[63:0];
                    default: data_out <= 64'h0;
                endcase
                done         <= 1'b1;
                was_receiving <= 1'b0;
                bit_count    <= 7'd0;
                shift_reg    <= 64'd0;
            end
        end
    end

endmodule


module sync_serial_communication_top (
    input  logic        clk,
    input  logic        reset_n,
    input  logic [63:0] data_in,
    input  logic [2:0]  sel,
    output logic [63:0] data_out,
    output logic        done
);

    logic serial_data;
    logic serial_clk;
    logic tx_done;

    tx_block tx_inst (
        .clk        (clk),
        .reset_n    (reset_n),
        .data_in    (data_in),
        .sel        (sel),
        .serial_out (serial_data),
        .done       (tx_done),
        .serial_clk (serial_clk)
    );

    rx_block rx_inst (
        .clk        (clk),
        .reset_n    (reset_n),
        .data_in    (serial_data),
        .sel        (sel),
        .serial_clk (serial_clk),
        .data_out   (data_out),
        .done       (done)
    );

endmodule
