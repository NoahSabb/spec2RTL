module dbi_enc (
    input [39:0] data_in,
    input clk,
    input rst_n,
    output reg [39:0] data_out,
    output reg [1:0] dbi_cntrl
);

// Internal signals
reg [19:0] group0;
reg [19:0] group1;
reg [1:0] prev_dbi_cntrl;
wire [19:0] inv_group0;
wire [19:0] inv_group1;
wire [39:0] inverted_data;
wire [39:0] raw_data;  // Raw data after splitting into groups
wire [19:0] xor_group0 = group0 ^ (prev_dbi_cntrl[0] ? ~{2'b0, group0} : group0);
wire [19:0] xor_group1 = group1 ^ (prev_dbi_cntrl[1] ? ~{2'b0, group1} : group1);
reg [39:0] prev_data;

// Split incoming data into two groups
assign raw_data = {group1, group0};
assign inverted_data = {inv_group1, inv_group0};
assign data_out = (dbi_cntrl == 2'b11) ? inverted_data : raw_data;

// Generate control signals
always @(posedge clk) begin
    if (!rst_n) begin
        dbi_cntrl <= 2'b00;
        prev_dbi_cntrl <= 2'b00;
    end else begin
        // Calculate # of bit toggles since reset or previous operation
        if (group1 != 20'h0) begin
            if ($countone(xor_group1) > 10) dbi_cntrl[1] <= 1;
            else dbi_cntrl[1] <= 0;
        end else begin
            previous_dbi_cnsrtrl[1] <= {2'b0, prev_data[39:20]};
            if ($countone(previous_group1) > 10) dbi_cntrl[1] <= 1;
            else dbi_cntrl[1] <= 0;
        end
        if (group0 != 20'h0) begin
            if ($countone(xor_group0) > 10) dbi_cntrl[0] <= 1;
            else dbi_cntrl[0] <= 0;
        end else begin
            previous_dbi_cnsrtrl[0] <= {2'b0, prev_data[19:0]};
            if ($countone(previous_group0) > 10) dbi_cntrl[0] <= 1;
            else dbi_cntrl[0] <= 0;
        end
        
        // Update previous data for next comparison
        prev_data <= data_out;
        previous_dbi_cnsrtrl <= {prev_dbi_cntrl, prev_data[39:20]};
    end
end

// Invert group if control signal is high
assign inv_group1 = (dbi_cntrl[1]) ? ~{2'b0, group1} : group1;
assign inv_group0 = (dbi_cntrl[0]) ? ~{2'b0, group0} : group0;

// Initialize to zeroes on reset or power up
initial begin
    dbi_cntrl <= 2'b00;
    prev_dbi_cntrl <= 2'b00;
    data_out <= 40'h0;
end

endmodule