module caesar_cipher (
    input  wire [7:0] input_char,
    input  wire [3:0] key,
    output reg  [7:0] output_char
);

    reg [7:0] shifted;

    always @(*) begin
        if (input_char >= 8'd65 && input_char <= 8'd90) begin
            // Uppercase letter A-Z
            shifted = input_char - 8'd65 + {4'b0000, key};
            if (shifted >= 8'd26) begin
                shifted = shifted - 8'd26;
            end
            output_char = shifted + 8'd65;
        end else if (input_char >= 8'd97 && input_char <= 8'd122) begin
            // Lowercase letter a-z
            shifted = input_char - 8'd97 + {4'b0000, key};
            if (shifted >= 8'd26) begin
                shifted = shifted - 8'd26;
            end
            output_char = shifted + 8'd97;
        end else begin
            // Non-alphabetic character
            output_char = input_char;
        end
    end

endmodule
