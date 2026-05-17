module caesar_cipher (
    input  logic [7:0] input_char,
    input  logic [3:0] key,
    output logic [7:0] output_char
);

    always_comb begin
        if (input_char >= 8'd65 && input_char <= 8'd90) begin
            // Uppercase letter A-Z
            output_char = ((input_char - 8'd65 + {4'b0000, key}) % 8'd26) + 8'd65;
        end else if (input_char >= 8'd97 && input_char <= 8'd122) begin
            // Lowercase letter a-z
            output_char = ((input_char - 8'd97 + {4'b0000, key}) % 8'd26) + 8'd97;
        end else begin
            // Non-alphabetic character
            output_char = input_char;
        end
    end

endmodule
