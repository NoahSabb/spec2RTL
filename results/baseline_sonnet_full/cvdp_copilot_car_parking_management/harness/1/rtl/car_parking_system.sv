module car_parking_system #(
    parameter TOTAL_SPACES = 12
)(
    input  logic clk,
    input  logic reset,
    input  logic vehicle_entry_sensor,
    input  logic vehicle_exit_sensor,
    output logic [$clog2(TOTAL_SPACES)-1:0] available_spaces,
    output logic [$clog2(TOTAL_SPACES)-1:0] count_car,
    output logic led_status,
    output logic [6:0] seven_seg_display_available_tens,
    output logic [6:0] seven_seg_display_available_units,
    output logic [6:0] seven_seg_display_count_tens,
    output logic [6:0] seven_seg_display_count_units
);

    // FSM State Encoding
    typedef enum logic [1:0] {
        IDLE            = 2'b00,
        ENTRY_PROCESSING = 2'b01,
        EXIT_PROCESSING  = 2'b10,
        FULL            = 2'b11
    } state_t;

    state_t current_state, next_state;

    // Internal registers
    logic [$clog2(TOTAL_SPACES):0] avail_spaces_reg;
    logic [$clog2(TOTAL_SPACES):0] count_car_reg;

    // 7-segment encoding function
    // MSB = segment A, LSB = segment G
    // Segments: A B C D E F G
    function automatic [6:0] seven_seg_encode(input [3:0] digit);
        case (digit)
            4'd0: seven_seg_encode = 7'b1111110; // 0
            4'd1: seven_seg_encode = 7'b0110000; // 1
            4'd2: seven_seg_encode = 7'b1101101; // 2
            4'd3: seven_seg_encode = 7'b1111001; // 3
            4'd4: seven_seg_encode = 7'b0110011; // 4
            4'd5: seven_seg_encode = 7'b1011011; // 5
            4'd6: seven_seg_encode = 7'b1011111; // 6
            4'd7: seven_seg_encode = 7'b1110000; // 7
            4'd8: seven_seg_encode = 7'b1111111; // 8
            4'd9: seven_seg_encode = 7'b1111011; // 9
            default: seven_seg_encode = 7'b0000000;
        endcase
    endfunction

    // FSM State Register (synchronous with async reset)
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            current_state <= IDLE;
        end else begin
            current_state <= next_state;
        end
    end

    // FSM Next State Logic
    always_comb begin
        next_state = current_state;
        case (current_state)
            IDLE: begin
                if (vehicle_entry_sensor && !vehicle_exit_sensor) begin
                    if (avail_spaces_reg > 0) begin
                        next_state = ENTRY_PROCESSING;
                    end else begin
                        next_state = FULL;
                    end
                end else if (vehicle_exit_sensor && !vehicle_entry_sensor) begin
                    if (count_car_reg > 0) begin
                        next_state = EXIT_PROCESSING;
                    end else begin
                        next_state = IDLE;
                    end
                end else begin
                    next_state = IDLE;
                end
            end
            ENTRY_PROCESSING: begin
                next_state = IDLE;
            end
            EXIT_PROCESSING: begin
                next_state = IDLE;
            end
            FULL: begin
                if (vehicle_exit_sensor) begin
                    next_state = EXIT_PROCESSING;
                end else begin
                    next_state = IDLE;
                end
            end
            default: next_state = IDLE;
        endcase
    end

    // Datapath: Update counters
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            avail_spaces_reg <= TOTAL_SPACES;
            count_car_reg    <= 0;
        end else begin
            case (current_state)
                ENTRY_PROCESSING: begin
                    if (avail_spaces_reg > 0) begin
                        avail_spaces_reg <= avail_spaces_reg - 1;
                        count_car_reg    <= count_car_reg + 1;
                    end
                end
                EXIT_PROCESSING: begin
                    if (count_car_reg > 0) begin
                        avail_spaces_reg <= avail_spaces_reg + 1;
                        count_car_reg    <= count_car_reg - 1;
                    end
                end
                default: begin
                    avail_spaces_reg <= avail_spaces_reg;
                    count_car_reg    <= count_car_reg;
                end
            endcase
        end
    end

    // Output assignments
    assign available_spaces = avail_spaces_reg[$clog2(TOTAL_SPACES)-1:0];
    assign count_car        = count_car_reg[$clog2(TOTAL_SPACES)-1:0];
    assign led_status       = (avail_spaces_reg > 0) ? 1'b1 : 1'b0;

    // 7-segment display for available spaces
    logic [3:0] avail_tens, avail_units;
    logic [3:0] count_tens, count_units;

    always_comb begin
        avail_tens  = (avail_spaces_reg / 10) % 10;
        avail_units = avail_spaces_reg % 10;
        count_tens  = (count_car_reg / 10) % 10;
        count_units = count_car_reg % 10;
    end

    assign seven_seg_display_available_tens  = seven_seg_encode(avail_tens);
    assign seven_seg_display_available_units = seven_seg_encode(avail_units);
    assign seven_seg_display_count_tens      = seven_seg_encode(count_tens);
    assign seven_seg_display_count_units     = seven_seg_encode(count_units);

endmodule
