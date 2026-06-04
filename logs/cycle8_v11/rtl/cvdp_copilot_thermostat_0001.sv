module thermostat (
    input  wire       i_clk,
    input  wire       i_rst,
    input  wire [5:0] i_temp_feedback,
    input  wire       i_fan_on,
    input  wire       i_enable,
    input  wire       i_fault,
    input  wire       i_clr,
    output reg        o_heater_full,
    output reg        o_heater_medium,
    output reg        o_heater_low,
    output reg        o_aircon_full,
    output reg        o_aircon_medium,
    output reg        o_aircon_low,
    output reg        o_fan,
    output reg  [2:0] o_state
);

    localparam HEAT_LOW  = 3'b000;
    localparam HEAT_MED  = 3'b001;
    localparam HEAT_FULL = 3'b010;
    localparam AMBIENT   = 3'b011;
    localparam COOL_LOW  = 3'b100;
    localparam COOL_MED  = 3'b101;
    localparam COOL_FULL = 3'b110;

    reg [2:0] state_reg;
    reg [2:0] next_state;

    wire i_full_cold   = i_temp_feedback[5];
    wire i_medium_cold = i_temp_feedback[4];
    wire i_low_cold    = i_temp_feedback[3];
    wire i_low_hot     = i_temp_feedback[2];
    wire i_medium_hot  = i_temp_feedback[1];
    wire i_full_hot    = i_temp_feedback[0];

    // Next state logic
    always @(*) begin
        if (!i_enable || i_fault) begin
            next_state = AMBIENT;
        end else begin
            if      (i_full_cold)   next_state = HEAT_FULL;
            else if (i_medium_cold) next_state = HEAT_MED;
            else if (i_low_cold)    next_state = HEAT_LOW;
            else if (i_full_hot)    next_state = COOL_FULL;
            else if (i_medium_hot)  next_state = COOL_MED;
            else if (i_low_hot)     next_state = COOL_LOW;
            else                    next_state = AMBIENT;
        end
    end

    // State register
    always @(posedge i_clk or negedge i_rst) begin
        if (!i_rst) begin
            state_reg <= AMBIENT;
        end else begin
            state_reg <= next_state;
        end
    end

    // Output register
    always @(posedge i_clk or negedge i_rst) begin
        if (!i_rst) begin
            o_heater_full   <= 0;
            o_heater_medium <= 0;
            o_heater_low    <= 0;
            o_aircon_full   <= 0;
            o_aircon_medium <= 0;
            o_aircon_low    <= 0;
            o_fan           <= 0;
            o_state         <= AMBIENT;
        end else begin
            case (state_reg)
                HEAT_LOW: begin
                    o_heater_full   <= 0;
                    o_heater_medium <= 0;
                    o_heater_low    <= 1;
                    o_aircon_full   <= 0;
                    o_aircon_medium <= 0;
                    o_aircon_low    <= 0;
                    o_fan           <= 1;
                    o_state         <= HEAT_LOW;
                end
                HEAT_MED: begin
                    o_heater_full   <= 0;
                    o_heater_medium <= 1;
                    o_heater_low    <= 0;
                    o_aircon_full   <= 0;
                    o_aircon_medium <= 0;
                    o_aircon_low    <= 0;
                    o_fan           <= 1;
                    o_state         <= HEAT_MED;
                end
                HEAT_FULL: begin
                    o_heater_full   <= 1;
                    o_heater_medium <= 0;
                    o_heater_low    <= 0;
                    o_aircon_full   <= 0;
                    o_aircon_medium <= 0;
                    o_aircon_low    <= 0;
                    o_fan           <= 1;
                    o_state         <= HEAT_FULL;
                end
                AMBIENT: begin
                    o_heater_full   <= 0;
                    o_heater_medium <= 0;
                    o_heater_low    <= 0;
                    o_aircon_full   <= 0;
                    o_aircon_medium <= 0;
                    o_aircon_low    <= 0;
                    o_fan           <= i_fan_on;
                    o_state         <= AMBIENT;
                end
                COOL_LOW: begin
                    o_heater_full   <= 0;
                    o_heater_medium <= 0;
                    o_heater_low    <= 0;
                    o_aircon_full   <= 0;
                    o_aircon_medium <= 0;
                    o_aircon_low    <= 1;
                    o_fan           <= 1;
                    o_state         <= COOL_LOW;
                end
                COOL_MED: begin
                    o_heater_full   <= 0;
                    o_heater_medium <= 0;
                    o_heater_low    <= 0;
                    o_aircon_full   <= 0;
                    o_aircon_medium <= 1;
                    o_aircon_low    <= 0;
                    o_fan           <= 1;
                    o_state         <= COOL_MED;
                end
                COOL_FULL: begin
                    o_heater_full   <= 0;
                    o_heater_medium <= 0;
                    o_heater_low    <= 0;
                    o_aircon_full   <= 1;
                    o_aircon_medium <= 0;
                    o_aircon_low    <= 0;
                    o_fan           <= 1;
                    o_state         <= COOL_FULL;
                end
                default: begin
                    o_heater_full   <= 0;
                    o_heater_medium <= 0;
                    o_heater_low    <= 0;
                    o_aircon_full   <= 0;
                    o_aircon_medium <= 0;
                    o_aircon_low    <= 0;
                    o_fan           <= 0;
                    o_state         <= AMBIENT;
                end
            endcase
        end
    end

endmodule
