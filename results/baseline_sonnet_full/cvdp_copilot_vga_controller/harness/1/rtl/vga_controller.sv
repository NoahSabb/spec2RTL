module vga_controller (
    input  logic        clock,
    input  logic        reset,
    input  logic [7:0]  color_in,
    output logic        hsync,
    output logic        vsync,
    output logic [7:0]  red,
    output logic [7:0]  green,
    output logic [7:0]  blue,
    output logic [9:0]  next_x,
    output logic [9:0]  next_y,
    output logic        sync,
    output logic        clk,
    output logic        blank
);

    // Horizontal timing parameters
    parameter H_ACTIVE = 640;
    parameter H_FRONT  = 16;
    parameter H_PULSE  = 96;
    parameter H_BACK   = 48;

    // Vertical timing parameters
    parameter V_ACTIVE = 480;
    parameter V_FRONT  = 10;
    parameter V_PULSE  = 2;
    parameter V_BACK   = 33;

    // State encoding for horizontal FSM
    typedef enum logic [1:0] {
        H_ACT  = 2'b00,
        H_FP   = 2'b01,
        H_SYNC = 2'b10,
        H_BP   = 2'b11
    } h_state_t;

    // State encoding for vertical FSM
    typedef enum logic [1:0] {
        V_ACT  = 2'b00,
        V_FP   = 2'b01,
        V_SYNC = 2'b10,
        V_BP   = 2'b11
    } v_state_t;

    h_state_t h_state;
    v_state_t v_state;

    logic [9:0] h_counter;
    logic [9:0] v_counter;
    logic       line_done;

    // VGA clock directly connected
    assign clk  = clock;
    // Sync fixed at 0
    assign sync = 1'b0;

    always_ff @(posedge clock or posedge reset) begin
        if (reset) begin
            h_state   <= H_ACT;
            v_state   <= V_ACT;
            h_counter <= 10'd0;
            v_counter <= 10'd0;
            line_done <= 1'b0;
            hsync     <= 1'b1;
            vsync     <= 1'b1;
            red       <= 8'd0;
            green     <= 8'd0;
            blue      <= 8'd0;
            next_x    <= 10'd0;
            next_y    <= 10'd0;
            blank     <= 1'b0;
        end else begin
            // Default line_done
            line_done <= 1'b0;

            // Horizontal FSM
            case (h_state)
                H_ACT: begin
                    hsync <= 1'b1;
                    // Active display: output color
                    red   <= {color_in[7:5], 5'd0};
                    green <= {color_in[4:2], 5'd0};
                    blue  <= {color_in[1:0], 6'd0};
                    // next_x tracks pixel position
                    next_x <= h_counter;

                    if (h_counter == H_ACTIVE - 1) begin
                        h_counter <= 10'd0;
                        h_state   <= H_FP;
                    end else begin
                        h_counter <= h_counter + 10'd1;
                    end
                end

                H_FP: begin
                    hsync  <= 1'b1;
                    red    <= 8'd0;
                    green  <= 8'd0;
                    blue   <= 8'd0;
                    next_x <= 10'd0;

                    if (h_counter == H_FRONT - 1) begin
                        h_counter <= 10'd0;
                        h_state   <= H_SYNC;
                    end else begin
                        h_counter <= h_counter + 10'd1;
                    end
                end

                H_SYNC: begin
                    hsync  <= 1'b0;
                    red    <= 8'd0;
                    green  <= 8'd0;
                    blue   <= 8'd0;
                    next_x <= 10'd0;

                    if (h_counter == H_PULSE - 1) begin
                        h_counter <= 10'd0;
                        h_state   <= H_BP;
                    end else begin
                        h_counter <= h_counter + 10'd1;
                    end
                end

                H_BP: begin
                    hsync  <= 1'b1;
                    red    <= 8'd0;
                    green  <= 8'd0;
                    blue   <= 8'd0;
                    next_x <= 10'd0;

                    if (h_counter == H_BACK - 1) begin
                        h_counter <= 10'd0;
                        h_state   <= H_ACT;
                        line_done <= 1'b1;
                    end else begin
                        h_counter <= h_counter + 10'd1;
                    end
                end

                default: begin
                    h_state   <= H_ACT;
                    h_counter <= 10'd0;
                end
            endcase

            // Vertical FSM - advances when line_done (will be set next cycle, use current)
            // line_done is set this cycle when H_BP ends; we need to act on it
            // Since line_done is set in the same always_ff block, we need to check condition directly
            // Instead, check vertical transitions based on the horizontal state transition

            // We handle vertical transitions by checking if we are at the last cycle of H_BP
            if (h_state == H_BP && h_counter == H_BACK - 1) begin
                case (v_state)
                    V_ACT: begin
                        vsync  <= 1'b1;
                        next_y <= v_counter;

                        if (v_counter == V_ACTIVE - 1) begin
                            v_counter <= 10'd0;
                            v_state   <= V_FP;
                        end else begin
                            v_counter <= v_counter + 10'd1;
                        end
                    end

                    V_FP: begin
                        vsync  <= 1'b1;
                        next_y <= 10'd0;

                        if (v_counter == V_FRONT - 1) begin
                            v_counter <= 10'd0;
                            v_state   <= V_SYNC;
                        end else begin
                            v_counter <= v_counter + 10'd1;
                        end
                    end

                    V_SYNC: begin
                        vsync  <= 1'b0;
                        next_y <= 10'd0;

                        if (v_counter == V_PULSE - 1) begin
                            v_counter <= 10'd0;
                            v_state   <= V_BP;
                        end else begin
                            v_counter <= v_counter + 10'd1;
                        end
                    end

                    V_BP: begin
                        vsync  <= 1'b1;
                        next_y <= 10'd0;

                        if (v_counter == V_BACK - 1) begin
                            v_counter <= 10'd0;
                            v_state   <= V_ACT;
                        end else begin
                            v_counter <= v_counter + 10'd1;
                        end
                    end

                    default: begin
                        v_state   <= V_ACT;
                        v_counter <= 10'd0;
                    end
                endcase
            end else begin
                // Maintain vsync based on current v_state when not transitioning
                case (v_state)
                    V_ACT:  begin vsync <= 1'b1; next_y <= v_counter; end
                    V_FP:   begin vsync <= 1'b1; next_y <= 10'd0; end
                    V_SYNC: begin vsync <= 1'b0; next_y <= 10'd0; end
                    V_BP:   begin vsync <= 1'b1; next_y <= 10'd0; end
                    default: vsync <= 1'b1;
                endcase
            end

            // Blank signal: active when not in active display area for both H and V
            if ((h_state == H_ACT) && (v_state == V_ACT)) begin
                blank <= 1'b0;
            end else begin
                blank <= 1'b1;
            end
        end
    end

endmodule
