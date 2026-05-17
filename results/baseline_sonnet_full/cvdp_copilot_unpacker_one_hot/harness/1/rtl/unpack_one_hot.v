module unpack_one_hot (
    input  wire        sign,
    input  wire        size,
    input  wire [2:0]  one_hot_selector,
    input  wire [255:0] source_reg,
    output reg  [511:0] destination_reg
);

    integer i;

    always @(*) begin
        destination_reg = 512'b0;

        case (one_hot_selector)
            3'b001: begin
                // Each 1-bit segment of source_reg unpacked into 8-bit segment of destination_reg
                // source_reg has 256 bits -> 256 1-bit segments
                // destination_reg has 512 bits, but we only have 256 segments of 8 bits = 2048 bits
                // Wait - destination is 512 bits. 256 segments * 8 bits = 2048 bits. 
                // That doesn't fit. Let me reconsider.
                // Perhaps we only unpack the lower portion that fits.
                // 512 bits / 8 bits per element = 64 elements
                // So we take 64 1-bit segments from source_reg
                for (i = 0; i < 64; i = i + 1) begin
                    if (sign && source_reg[i]) begin
                        destination_reg[i*8 +: 8] = 8'hFF;
                    end else begin
                        destination_reg[i*8 +: 8] = {7'b0, source_reg[i]};
                    end
                end
            end

            3'b010: begin
                // Each 2-bit segment of source_reg unpacked into 8-bit segment of destination_reg
                // 512 bits / 8 bits per element = 64 elements
                // 64 elements * 2 bits = 128 bits from source_reg
                for (i = 0; i < 64; i = i + 1) begin
                    if (sign && source_reg[i*2 + 1]) begin
                        destination_reg[i*8 +: 8] = {{6{1'b1}}, source_reg[i*2 +: 2]};
                    end else begin
                        destination_reg[i*8 +: 8] = {6'b0, source_reg[i*2 +: 2]};
                    end
                end
            end

            3'b100: begin
                if (size) begin
                    // Each 8-bit segment of source_reg unpacked into 16-bit segment of destination_reg
                    // 512 bits / 16 bits per element = 32 elements
                    // 32 elements * 8 bits = 256 bits from source_reg (fits exactly)
                    for (i = 0; i < 32; i = i + 1) begin
                        if (sign && source_reg[i*8 + 7]) begin
                            destination_reg[i*16 +: 16] = {{8{1'b1}}, source_reg[i*8 +: 8]};
                        end else begin
                            destination_reg[i*16 +: 16] = {8'b0, source_reg[i*8 +: 8]};
                        end
                    end
                end else begin
                    // Each 4-bit segment of source_reg unpacked into 8-bit segment of destination_reg
                    // 512 bits / 8 bits per element = 64 elements
                    // 64 elements * 4 bits = 256 bits from source_reg (fits exactly)
                    for (i = 0; i < 64; i = i + 1) begin
                        if (sign && source_reg[i*4 + 3]) begin
                            destination_reg[i*8 +: 8] = {{4{1'b1}}, source_reg[i*4 +: 4]};
                        end else begin
                            destination_reg[i*8 +: 8] = {4'b0, source_reg[i*4 +: 4]};
                        end
                    end
                end
            end

            default: begin
                // Direct assignment of source_reg to destination_reg
                destination_reg = {256'b0, source_reg};
            end
        endcase
    end

endmodule
