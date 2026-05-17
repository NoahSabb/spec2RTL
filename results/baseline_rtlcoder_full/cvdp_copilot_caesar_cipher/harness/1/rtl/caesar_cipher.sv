module caesar_cipher (
    input [7:0] input_char,
    input [3:0] key,
    output reg [7:0] output_char
);

// Define a constant for the ASCII value of 'a'
localparam ASCII_a = 97;

always @(*) begin
    // Check if input character is uppercase (A-Z)
    if (input_char >= 65 && input_char <= 90) begin
        // Calculate the new alphabet index based on key and modulo 26
        output_char = (input_char - 65 + key);
        // Wrap around to 'A' if the result is greater than Z
        if (output_char > 90) begin
            output_char = output_char - 26;
        end
    end
    // Check if input character is lowercase (a-z)
    else if (input_char >= ASCII_a && input_char <= 122) begin
        // Calculate the new alphabet index based on key and modulo 26
        output_char = ((input_char - ASCII_a + key);
        // Wrap around to 'a' if the result is greater than z
        if (output_char > 122) begin
            output_char = output_char - 26;
        end
    end
    else begin
        // No alphabetic shift required, output character unchanged
        output_char = input_char;
    end
end

endmodule