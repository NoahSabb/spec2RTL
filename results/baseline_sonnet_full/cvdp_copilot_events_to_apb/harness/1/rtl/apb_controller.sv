module apb_controller (
    input  logic        clk,
    input  logic        reset_n,
    
    // Event select signals
    input  logic        select_a_i,
    input  logic        select_b_i,
    input  logic        select_c_i,
    
    // Event A address and data
    input  logic [31:0] addr_a_i,
    input  logic [31:0] data_a_i,
    
    // Event B address and data
    input  logic [31:0] addr_b_i,
    input  logic [31:0] data_b_i,
    
    // Event C address and data
    input  logic [31:0] addr_c_i,
    input  logic [31:0] data_c_i,
    
    // APB interface
    input  logic        apb_pready_i,
    output logic        apb_psel_o,
    output logic        apb_penable_o,
    output logic        apb_pwrite_o,
    output logic [31:0] apb_paddr_o,
    output logic [31:0] apb_pwdata_o
);

    // State encoding
    typedef enum logic [1:0] {
        IDLE   = 2'b00,
        SETUP  = 2'b01,
        ACCESS = 2'b10
    } state_t;
    
    state_t current_state, next_state;
    
    // Internal registers for captured address and data
    logic [31:0] captured_addr;
    logic [31:0] captured_data;
    
    // Timeout counter
    logic [3:0] timeout_cnt;
    logic        timeout;
    
    // Assign timeout when counter reaches 15
    assign timeout = (timeout_cnt == 4'hF);
    
    // State register
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            current_state <= IDLE;
        end else begin
            current_state <= next_state;
        end
    end
    
    // Capture address and data in IDLE when select signals are asserted
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            captured_addr <= 32'h0;
            captured_data <= 32'h0;
        end else begin
            if (current_state == IDLE) begin
                if (select_a_i) begin
                    captured_addr <= addr_a_i;
                    captured_data <= data_a_i;
                end else if (select_b_i) begin
                    captured_addr <= addr_b_i;
                    captured_data <= data_b_i;
                end else if (select_c_i) begin
                    captured_addr <= addr_c_i;
                    captured_data <= data_c_i;
                end
            end
        end
    end
    
    // Timeout counter
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            timeout_cnt <= 4'h0;
        end else begin
            if (current_state == ACCESS) begin
                if (apb_pready_i || timeout) begin
                    timeout_cnt <= 4'h0;
                end else begin
                    timeout_cnt <= timeout_cnt + 4'h1;
                end
            end else begin
                timeout_cnt <= 4'h0;
            end
        end
    end
    
    // Next state logic
    always_comb begin
        next_state = current_state;
        case (current_state)
            IDLE: begin
                if (select_a_i || select_b_i || select_c_i) begin
                    next_state = SETUP;
                end else begin
                    next_state = IDLE;
                end
            end
            SETUP: begin
                next_state = ACCESS;
            end
            ACCESS: begin
                if (apb_pready_i || timeout) begin
                    next_state = IDLE;
                end else begin
                    next_state = ACCESS;
                end
            end
            default: begin
                next_state = IDLE;
            end
        endcase
    end
    
    // Output logic
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            apb_psel_o    <= 1'b0;
            apb_penable_o <= 1'b0;
            apb_pwrite_o  <= 1'b0;
            apb_paddr_o   <= 32'h0;
            apb_pwdata_o  <= 32'h0;
        end else begin
            case (next_state)
                IDLE: begin
                    apb_psel_o    <= 1'b0;
                    apb_penable_o <= 1'b0;
                    apb_pwrite_o  <= 1'b0;
                    apb_paddr_o   <= 32'h0;
                    apb_pwdata_o  <= 32'h0;
                end
                SETUP: begin
                    apb_psel_o    <= 1'b1;
                    apb_penable_o <= 1'b0;
                    apb_pwrite_o  <= 1'b1;
                    // Use captured values (already captured in IDLE on this same clock edge)
                    // Need to use the values that will be captured
                    if (current_state == IDLE) begin
                        if (select_a_i) begin
                            apb_paddr_o  <= addr_a_i;
                            apb_pwdata_o <= data_a_i;
                        end else if (select_b_i) begin
                            apb_paddr_o  <= addr_b_i;
                            apb_pwdata_o <= data_b_i;
                        end else if (select_c_i) begin
                            apb_paddr_o  <= addr_c_i;
                            apb_pwdata_o <= data_c_i;
                        end
                    end else begin
                        apb_paddr_o  <= captured_addr;
                        apb_pwdata_o <= captured_data;
                    end
                end
                ACCESS: begin
                    apb_psel_o    <= 1'b1;
                    apb_penable_o <= 1'b1;
                    apb_pwrite_o  <= 1'b1;
                    apb_paddr_o   <= captured_addr;
                    apb_pwdata_o  <= captured_data;
                end
                default: begin
                    apb_psel_o    <= 1'b0;
                    apb_penable_o <= 1'b0;
                    apb_pwrite_o  <= 1'b0;
                    apb_paddr_o   <= 32'h0;
                    apb_pwdata_o  <= 32'h0;
                end
            endcase
        end
    end

endmodule
