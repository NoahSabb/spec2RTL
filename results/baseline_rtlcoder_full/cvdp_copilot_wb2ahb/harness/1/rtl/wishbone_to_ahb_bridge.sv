module wishbone_to_ahb_bridge(
    input clk_i,
    input rst_i,
    input cyc_i,
    input stb_i,
    input [3:0] sel_i,
    input we_i,
    input [31:0] addr_i,
    input [31:0] data_i, // WB output
    output reg ack_o,

    input hclk,
    input hreset_n,
    input [31:0] hdata_r,
    output reg hresp_o, // AHB output
    output reg [3:0] htran_o,
    output reg [2:0] hsize_o,
    output reg [2:0] hburst_o,
    output reg hwrite_o,
    output reg [31:0] hwdata_o,

    input [3:0] hready,
    input [31:0] haddr // AHB output
);

// Registers for holding transaction attributes during pipeline stages.
reg [31:0] addr_hold;
reg [2:0] size_hold;
reg [3:0] trans_hold;
reg busy_f;
always @(posedge hclk) begin
    if (hreset_n == 0) begin
        addr_hold <= 'bz;
        size_hold <= 'bz;
        trans_hold <= 'bz;
        busy_f <= 1'b0;
    end else begin
        case (trans_hold)
            3'd0: begin
                if (!hready[3])
                    addr_hold <= {addr_i, hsize_o == 3'b00 ? 9'd0 : 8'bz, 8'bz}; // Derive AHB address from Wishbone
            end
            3'd1: begin
                if (!hready[2])
                    addr_hold <= {addr_i, hsize_o == 3'b00 ? 9'd0 : 8'bz, 8'bz}; // Derive AHB address from Wishbone
            end
            3'd2: begin
                if (!hready[1])
                    addr_hold <= {addr_i, hsize_o == 3'b00 ? 9'd0 : 8'bz, 8'bz}; // Derive AHB address from Wishbone
            end
            3'd3: begin
                if (!hready[0])
                    addr_hold <= {addr_i, hsize_o == 3'b00 ? 9'd0 : 8'bz, 8'bz}; // Derive AHB address from Wishbone
            end
        endcase
        if (we_i) begin
            trans_hold <= {addr_hold[28], addr_hold[27], addr_hold[23]};
            hwrite_o <= 1'b1;
            hwdata_o <= we_i ? data_i : hready[sel_i] & hsize_o > {3'd0, sel_i} ?
                             {{hsize_o - {3'd0, sel_i}}, hsize_o == 3'b00 ? 0 : {8'bz, {(43), sel_i}}},
                            ((we_i & (hsize_o > se[hsize_o])) | (~hwrite_o)) ? hready[sel_i] : data_i >> ({6'd12, 3'b0, 2'd0, {(43), sel_i}}) :
                             0
            ;
        end else begin // Read case
            trans_hold <= addr_hold[CW_OP];
            hresp_o <= trans_hold;
            htran_o <= trans_hold ? 4'b1011 : trans_hold ? 4'b0110 : 4'b0100; // AHB transactions types: IDLE, NON-SEQUENTIAL, BUSY. SINGLE only supported here
            hsize_o <= addr_hold[3:1];
            size_hold <= addr_hold[3:1];
        end
        
         hburst_o <= 4'b0000; // ALWAYS single in this design
    end
end

always @(posedge clk_i) begin
    if (rst_i == 0) begin
        ack_o <= 1'b0;
        busy_f <= 1'b0;
    end else begin
        case (trans_hold)
            3'd2: if (!hready[1]) ack_o <= 1'b1; else ack_o <= 1'b0; // Acknowledge only after hready asserted.
            3'd3: if (!hready[0]) ack_o <= 1'b1; else begin
                     ack_o <= 1'b0;
                     busy_f <= 1'b1; // AHB is still active by now
                end
        endcase
    end
end

endmodule