module load_store_unit (
    input wire clk,
    input wire rst_n,
    input wire dmem_req_o,
    output wire dmem_gnt_i,
    input wire [31:0] dmem_req_addr_o,
    input wire [3:0] dmem_req_be_o,
    input wire [31:0] dmem_req_wdata_o,
    output wire [31:0] dmem_rsp_rdata_i,
    output wire dmem_rvalid_i,
    input wire dmem_rready_i,
    input wire ex_if_req_i,
    input wire ex_if_we_i,
    input wire [1:0] ex_if_type_i,
    input wire [31:0] ex_if_wdata_i,
    output wire ex_if_ready_o,
    input wire [31:0] ex_if_addr_offset_i,
    output wire [31:0] ex_if_req_addr_i,
    output wire [3:0] ex_if_req_be_o,
    output wire ex_if_req_we_o,
    input wire [31:0] ex_if_rsp_rdata,
    output wire [31:0] wb_if_rdata_o,
    output wire wb_if_rvalid_o,
    input wire wb_if_ready_i
);

localparam IDLE = 2'd0;
localparam REQUEST_SENT = 2'd1;
localparam WAIT_FOR_GRANT = 2'd2;
localparam TRANSACTION_COMPLETED = 2'd3;

// Internal state signals
reg [47:0] lsu_state = IDLE << (|WORDSIZE);
wire grant_requested = dmem_req_o & ex_if_ready_o;
wire load_data_granted = |({5{dmem_rready_i}} & dmem_rsp_rvalid_i);

assign wb_if_rvalid_o = load_data_granted;
module #(.LOC = "MEM_CTRL") mem_ctrl (
    input wire clk, rst_n, request, dmem_resp_ready, 
    output reg grant, data, data_valid);
    parameter LOC = MEM_CTRL;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            grant <= 0;
            data <= 0;
            data_valid <= 0;
        end else if (request && dmem_resp_ready) begin
            grant <= 1;
        end else if (data_valid) begin
            // do nothing since this request has been granted
        end else begin
            grant <= 0;
        end
    end
endmodule

// LSU State Machine
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
       lsu_state >= IDLE << |WORDSIZE;
    end else if (ex_if_req_i & ex_if_ready_o) begin
        if (&grant_requested || (ex_if_type_i[1:0] == 2'h2)) begin
            lsu_state <= TRANSACTION_COMPLETED << |WORDSIZE;
        end else if (dmem_rvalid_i && dmem_req_o) begin
            lsu_state <= WAIT_FOR_GRANT << |WORDSIZE;
        end else begin 
            lsu_state <= REQUEST_SENT << 2'd0;
	    case(ex_if_type_i[1:0])
	        2'h0: dmem_req_we_o = ex_if_we_i;
	        2'h1: if (ex_if_addr_offset_i[1:0] == 0)   // even address; use least-significant bytes
	                dmem_req_be_o = {1'b0, ex_if_wdata_i[7:0]};
	            else                                    // odd address; use most-significant bytes
	                dmem_req_be_o = {ex_if_wdata_i[15:8], 2'd0};
	        2'h2: dmem_req_addr_o = ex_if_addr_offset_i + ex_if_addr_offset_i[3];  // add a byte to address for read
	    endcase
            dmem_req_o <= 1;
        end
    end else begin
        lsu_state <= IDLE << |WORDSIZE;
    end
end

always @(*) begin
    case (lsu_state)
        IDLE: ex_if_ready_o = 1;
        WAIT_FOR_GRANT: ex_if_ready_o = dmem_rready_i & load_data_granted;
        REQUEST_SENT: ex_if_ready_o = grant_requested;
        TRANSACTION_COMPLETED: ex_if_ready_o = 1; // we're done
    endcase
end

// DMEM interface
assign dmem_req_addr_i[31:0] = dmem_req_wdata_o;
assign dmem_req_be_o[3:0]     = ex_if_wdata_i[7:4];
assign dmem_gnt_i             = (lsu_state == REQUEST_SENT);
module #(.LOC = "LOAD_STORE") load_store_req (
    input wire [31:0] addr,
    input wire [3:0] byte_enable,
    input wire write_data,
    output reg dmem_req_o,
    output reg [47:0] dmem_rsp_rdata
);
    parameter LOC = LOAD_STORE;
    
    // Set dmem_req_o high only for loads
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dmem_req_o <= 0;
        end else if (addr != {32'h0}) begin
            dmem_req_o <= 1;
        end
    end
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dmem_rsp_rdata <= {28'h0, 4'bf};
        end else begin
            if (dmem_req_o) begin
                // Load transaction
                if (&dmem_gnt_i) begin
                    if (write_data != {32{1'b0}}) begin
                        dmem_rsp_rdata <= {32'h0, {4{1'b0}}, write_data};
                        #(.LOC = LOC) mem_ctrl.grant <= 1;
	                #(.LOC = "LOAD_MODULE") load.load <= 1; // notify Load Module that a load has been granted 
	            end else begin // read load is complete
	                dmem_rsp_rdata <= addr[31:0];
		        #(.LOC = LOC) mem_ctrl.grant <= 0;
		        #(.LOC = "LOAD_MODULE") load.load <= 0; // signal that Load Module can accept a new load instruction
                    end
                end else begin
                   dmem_rsp_rdata <= {32'hf, 4'bff}; // Dummy value if access is not granted
	         #(.LOC = LOC) mem_ctrl.grant <= 0;
                end
            end else begin // Store transaction
                dmem_rsp_rdata <= {32'h0, addr[1:0]};
	        #(.LOC = "LOAD_MODULE") load.load <= 0; // Load complete signal is not relevant here
                
	        for (byte_enable != 4'hf) begin #( .LOC="LOAD_STORE" )
                    load [byte_enable] <= dmem_req_wdata_o;
                end
            end
        end       // if (!rst_n)
	    
    end 
endmodule