module apb_controller (
    input logic clk,
    input logic reset_n,
    input logic select_a_i,
    input logic select_b_i,
    input logic select_c_i,
    input logic [31:0] addr_a_i,
    input logic [31:0] data_a_i,
    input logic [31:0] addr_b_i,
    input logic [31:0] data_b_i,
    input logic [31:0] addr_c_i,
    input logic [31:0] data_c_i,
    input logic apb_pready_i,

    output logic apb_psel_o,
    output logic apb_penable_o,
    output logic apb_pwrite_o,
    output logic [31:0] apb_paddr_o,
    output logic [31:0] apb_pwdata_o
);

    // States for the state machine
    typedef enum logic [1:0] {
        IDLE = 2'b00,
        SETUP = 2'b01,
        ACCESS = 2'b10
    } state_t;

    state_t state, next_state;
    logic [31:0] addr_reg;
    logic [31:0] data_reg;
    logic [3:0] timeout_counter;

    // Next state logic
    always_comb begin
        next_state = state;
        case (state)
            IDLE: begin
                if (select_a_i || select_b_i || select_c_i) begin
                    next_state = SETUP;
                end
            end
            SETUP: begin
                next_state = ACCESS;
            end
            ACCESS: begin
                if (apb_pready_i || timeout_counter == 4'd15) begin
                    next_state = IDLE;
                end
            end
            default: begin
                next_state = IDLE;
            end
        endcase
    end

    // State transition and output logic
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state <= IDLE;
            timeout_counter <= 4'b0000;
            apb_psel_o <= 1'b0;
            apb_penable_o <= 1'b0;
            apb_pwrite_o <= 1'b0;
            apb_paddr_o <= 32'b0;
            apb_pwdata_o <= 32'b0;
            addr_reg <= 32'b0;
            data_reg <= 32'b0;
        end else begin
            state <= next_state;
            
            // Capture address and data in IDLE when select signals are asserted
            if (state == IDLE) begin
                if (select_a_i) begin
                    addr_reg <= addr_a_i;
                    data_reg <= data_a_i;
                end else if (select_b_i) begin
                    addr_reg <= addr_b_i;
                    data_reg <= data_b_i;
                end else if (select_c_i) begin
                    addr_reg <= addr_c_i;
                    data_reg <= data_c_i;
                end
            end
            
            // Output assignments based on next_state
            case (next_state)
                IDLE: begin
                    apb_psel_o <= 1'b0;
                    apb_penable_o <= 1'b0;
                    apb_pwrite_o <= 1'b0;
                    apb_paddr_o <= 32'b0;
                    apb_pwdata_o <= 32'b0;
                    timeout_counter <= 4'b0000;
                end
                SETUP: begin
                    apb_psel_o <= 1'b1;
                    apb_penable_o <= 1'b0;
                    apb_pwrite_o <= 1'b1;
                    // Use captured addr_reg/data_reg, but if coming from IDLE this cycle,
                    // we need to use the just-captured values
                    if (state == IDLE) begin
                        if (select_a_i) begin
                            apb_paddr_o <= addr_a_i;
                            apb_pwdata_o <= data_a_i;
                        end else if (select_b_i) begin
                            apb_paddr_o <= addr_b_i;
                            apb_pwdata_o <= data_b_i;
                        end else if (select_c_i) begin
                            apb_paddr_o <= addr_c_i;
                            apb_pwdata_o <= data_c_i;
                        end
                    end else begin
                        apb_paddr_o <= addr_reg;
                        apb_pwdata_o <= data_reg;
                    end
                    timeout_counter <= 4'b0000;
                end
                ACCESS: begin
                    apb_psel_o <= 1'b1;
                    apb_penable_o <= 1'b1;
                    apb_pwrite_o <= 1'b1;
                    apb_paddr_o <= addr_reg;
                    apb_pwdata_o <= data_reg;
                    if (!apb_pready_i) begin
                        timeout_counter <= timeout_counter + 1;
                    end else begin
                        timeout_counter <= 4'b0000;
                    end
                end
                default: begin
                    apb_psel_o <= 1'b0;
                    apb_penable_o <= 1'b0;
                    apb_pwrite_o <= 1'b0;
                    apb_paddr_o <= 32'b0;
                    apb_pwdata_o <= 32'b0;
                    timeout_counter <= 4'b0000;
                end
            endcase
        end
    end

endmodule
