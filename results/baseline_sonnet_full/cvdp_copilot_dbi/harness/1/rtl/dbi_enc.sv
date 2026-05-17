module dbi_enc (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [39:0] data_in,
    output logic [39:0] data_out,
    output logic [1:0]  dbi_cntrl
);

    // Internal signals
    logic [19:0] group1_in;
    logic [19:0] group0_in;
    
    logic [19:0] prev_group1;
    logic [19:0] prev_group0;
    
    logic [19:0] xor_group1;
    logic [19:0] xor_group0;
    
    logic [4:0]  toggle_count1;
    logic [4:0]  toggle_count0;
    
    logic        ctrl1;
    logic        ctrl0;
    
    logic [19:0] encoded_group1;
    logic [19:0] encoded_group0;
    
    // Split incoming data into two 20-bit groups
    assign group1_in = data_in[39:20]; // MSBs
    assign group0_in = data_in[19:0];  // LSBs
    
    // XOR current data with previous data to find toggles
    assign xor_group1 = group1_in ^ prev_group1;
    assign xor_group0 = group0_in ^ prev_group0;
    
    // Count number of toggled bits in each group
    integer i;
    always_comb begin
        toggle_count1 = 5'd0;
        toggle_count0 = 5'd0;
        for (i = 0; i < 20; i = i + 1) begin
            toggle_count1 = toggle_count1 + {4'b0, xor_group1[i]};
            toggle_count0 = toggle_count0 + {4'b0, xor_group0[i]};
        end
    end
    
    // Determine control bits
    assign ctrl1 = (toggle_count1 > 5'd10) ? 1'b1 : 1'b0;
    assign ctrl0 = (toggle_count0 > 5'd10) ? 1'b1 : 1'b0;
    
    // Encode data based on control bits
    assign encoded_group1 = ctrl1 ? ~group1_in : group1_in;
    assign encoded_group0 = ctrl0 ? ~group0_in : group0_in;
    
    // Combinational data_out and dbi_cntrl (registered below)
    // data_out and dbi_cntrl are registered outputs
    
    // Sequential logic: register outputs and previous data
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            data_out   <= 40'h00_0000_0000;
            dbi_cntrl  <= 2'b00;
            prev_group1 <= 20'h00000;
            prev_group0 <= 20'h00000;
        end else begin
            dbi_cntrl  <= {ctrl1, ctrl0};
            data_out   <= {encoded_group1, encoded_group0};
            prev_group1 <= encoded_group1;
            prev_group0 <= encoded_group0;
        end
    end

endmodule
