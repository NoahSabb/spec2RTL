module car_parking_system #(
    parameter TOTAL_SPACES = 12
)(
    input  wire                             clk,
    input  wire                             reset,
    input  wire                             vehicle_entry_sensor,
    input  wire                             vehicle_exit_sensor,

    output wire [$clog2(TOTAL_SPACES)-1:0]  available_spaces,
    output wire [$clog2(TOTAL_SPACES)-1:0]  count_car,
    output wire                             led_status,
    output wire [6:0]                       seven_seg_display_available_tens,
    output wire [6:0]                       seven_seg_display_available_units,
    output wire [6:0]                       seven_seg_display_count_tens,
    output wire [6:0]                       seven_seg_display_count_units
);

    localparam ADDR_BITS = $clog2(TOTAL_SPACES);

    // Define states for the FSM
    localparam IDLE             = 2'b00;
    localparam ENTRY_PROCESSING = 2'b01;
    localparam EXIT_PROCESSING  = 2'b10;
    localparam FULL             = 2'b11;

    // State register
    reg [1:0] state;
    reg [1:0] next_state;

    // Internal registers for counting
    reg [ADDR_BITS-1:0] available_spaces_reg;
    reg [ADDR_BITS-1:0] count_car_reg;

    // 7-segment display encoding function (common-anode active-low)
    function [6:0] seg7_encode(input [3:0] digit);
        case(digit)
            4'd0: seg7_encode = 7'b1111110;
            4'd1: seg7_encode = 7'b0110000;
            4'd2: seg7_encode = 7'b1101101;
            4'd3: seg7_encode = 7'b1111001;
            4'd4: seg7_encode = 7'b0110011;
            4'd5: seg7_encode = 7'b1011011;
            4'd6: seg7_encode = 7'b1011111;
            4'd7: seg7_encode = 7'b1110000;
            4'd8: seg7_encode = 7'b1111111;
            4'd9: seg7_encode = 7'b1111011;
            default: seg7_encode = 7'b0000000;
        endcase
    endfunction

    // Next state logic
    always @(*) begin
        next_state = state;
        case (state)
            IDLE: begin
                if (vehicle_entry_sensor) begin
                    if (available_spaces_reg > 0)
                        next_state = ENTRY_PROCESSING;
                    else
                        next_state = FULL;
                end else if (vehicle_exit_sensor) begin
                    next_state = EXIT_PROCESSING;
                end
            end
            ENTRY_PROCESSING: begin
                next_state = IDLE;
            end
            EXIT_PROCESSING: begin
                next_state = IDLE;
            end
            FULL: begin
                if (vehicle_exit_sensor)
                    next_state = EXIT_PROCESSING;
                else
                    next_state = FULL;
            end
            default: begin
                next_state = IDLE;
            end
        endcase
    end

    // State update and counter logic
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            state               <= IDLE;
            available_spaces_reg <= TOTAL_SPACES[ADDR_BITS-1:0];
            count_car_reg       <= 0;
        end else begin
            state <= next_state;
            case (state)
                ENTRY_PROCESSING: begin
                    if (available_spaces_reg > 0) begin
                        available_spaces_reg <= available_spaces_reg - 1;
                        count_car_reg        <= count_car_reg + 1;
                    end
                end
                EXIT_PROCESSING: begin
                    if (count_car_reg > 0) begin
                        available_spaces_reg <= available_spaces_reg + 1;
                        count_car_reg        <= count_car_reg - 1;
                    end
                end
                default: begin
                    // No change
                end
            endcase
        end
    end

    // Continuous assignments for outputs
    assign available_spaces = available_spaces_reg;
    assign count_car        = count_car_reg;
    assign led_status       = (available_spaces_reg > 0);

    // 7-segment display logic
    wire [7:0] avail_8bit = {3'b000, available_spaces_reg};
    wire [7:0] count_8bit = {3'b000, count_car_reg};

    assign seven_seg_display_available_tens  = seg7_encode(avail_8bit / 8'd10);
    assign seven_seg_display_available_units = seg7_encode(avail_8bit % 8'd10);
    assign seven_seg_display_count_tens      = seg7_encode(count_8bit / 8'd10);
    assign seven_seg_display_count_units     = seg7_encode(count_8bit % 8'd10);

endmodule
