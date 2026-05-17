Module Name: signed_comparator WIDTH: 5 -------------------- mode, enable, greater, lesser, equal inputs (in order): mode (active high): selects the comparison mode (1 for signed mode, 0 for magnitude mode); if magnitude mode is selected, the MSB of the input registers will be ignored. enable (active high): enables or disables the comparison logic in case the value we want to compare is unknown and it's possible that we really want to keep the values as-is; lesser or greater: these signals are active low, indicating if A < B or A > B. 0 will mean equality. equal (active high): the input registers can be kept as-is because they are equivalent equality logic is not used here since we need an enable signal to make the comparison happen. inputs: A and B have a WIDTH bits width (including the MSB when mode == 1; this is why signed mode does not work for widths < 8), and both are registered; i_mode and i_enable can be freely synthesizable if the FPGA tools support them. output signals: o_greater, o_less, o_equal. -------------------- module signed_unsigned_comparator(
    input [WIDTH-1:0] i_A,
    input [WIDTH-1:0] i_B,
    input i_mode,
    input i_enable,
    output reg o_greater,
    output reg o_less,
    output reg o_equal
);

always @(*) begin
    if (i_enable) begin // comparison is requested
        if (i_mode) begin // signed mode
            if ((i_A[WIDTH-1] == 1 && i_B[WIDTH-1] == 0) || (i_A[WIDTH-1] == 0 && i_B[WIDTH-1] == 1)) begin
                o_greater = 1;
                o_less = 0;
                o_equal = 0;
            end else if ((i_A[WIDTH-1] == 1) && (i_B[WIDTH-1] == 0)) begin // A has a negative sign, B doesn't
                o_greater = 1;
                o_less = 0;
                o_equal = 0;
            end else if ((~i_A[WIDTH-1]) && i_B[WIDTH-1]) begin // A has a positive sign, B doesn't
                o_greater = 0;
                o_less = 1;
                o_equal = 0;
            end else if (i_A == i_B) begin
                o_greater = 0;
                o_less = 0;
                o_equal = 1;
            end else begin // neither A nor B have a sign, just treat them as unsigned numbers
                if (i_A > i_B) begin
                    o_greater = 1;
                    o_less = 0;
                    o_equal = 0;
                end else if (i_A < i_B) begin
                    o_greater = 0;
                    o_less = 1;
                    o_equal = 0;
                end else begin // i_A == i_B
                    o_greater = 0;
                    o_less = 0;
                    o_equal = 1;
                end
            end
        end else begin // magnitude mode
            if (i_A > i_B) begin // B < A, i.e. lesser
                o_greater = 0;
                o_less = 1;
                o_equal = 0;
            end else if (i_A < i_B) begin // A < B, greater
                o_greater = 1;
                o_less = 0;
                o_equal = 0;
            end else begin // i_A == i_B
                o_greater = 0;
                o_less = 0;
                o_equal = 1;
            end
        end
    end else begin // comparison is disabled, output low signals regardless of the inputs
        o_greater = 0;
        o_less = 0;
        o_equal = 0;
    end
end

// synthesis attribute to work around tools that do not yet understand i_mode/i_enable
initial begin
    $synthesis_synopsys_compatibility("mode");
end

endmodule