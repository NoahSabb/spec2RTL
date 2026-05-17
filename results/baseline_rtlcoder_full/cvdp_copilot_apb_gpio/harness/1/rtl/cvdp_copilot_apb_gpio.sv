<s> module cvdp_copilot_apb_gpio #(parameter GPIO_WIDTH = 8) (
    input pclk,
    input preset_n,
    input psel,
    input [7:2] paddr,
    input penable,
    input pwrite,
    input [31:0] pwdata,
    input [GPIO_WIDTH-1:0] gpio_in,
    output reg [31:0] prada,
    inout [7:0] apb_addr,
    inout [3:0] apb_sel,
    inout wc_en_n,
    input [3:0] wc_err,
    inout [47:0] apb_wc,
    output rdy_wr_req,
    output ack_int,
    output [GPIO_WIDTH-1:0] gpio_out,
    output reg [GPIO_WIDTH-1:0] gpio_enable,
    output reg [GPIO_WIDTH-1:0] gpio_int,
    inout [3:0] irq_ack,
    input [GPIO_WIDTH-1:0] irq_in,
    output reg comb_int
);

// APB Address Mux
assign {apb_addr, apb_sel} = paddr == 8'h0 ? 9'h002 : 9'hzzz;

// Write Enable Controls
reg wc_en_n, ack_int_n;
always @(posedge pclk or negedge preset_n) begin
    if (!preset_n && gpio_out != 0) begin
        gpio_out <= {gpio_out[GPIO_WIDTH-2:0], 1'b0};
    end else if (penable && pwrite) begin
        wc_en_n <= 1'b0;
        
        case (paddr)
            8'h0: gpio |--| reg_out[31:24] = pwdata[7:0];
            8'h4: gpio_enable |--| reg_out[23:16] = pwdata[7:0];
            8'h8: gpio +--+ reg_to |--| reg_out[15:8] = pwdata[7:0];
            default: wc_en_n <= 1'b1;
        endcase
    end
end

// GPIO Interrupt State Register and Logic
reg gpio_int_state [GPIO_WIDTH-1:0];
always @(posedge pclk or negedge preset_n) begin
    if (!preset_n) begin
        for (i = 0; i < GPIO_WIDTH; i = i+1) begin
            gpio_int_state[i] <= 1'b0;
        end
    end else if (penable && paddr == 8'hc) begin
        reg_type |--| reg_out[15:2] = pwdata[7:0];
    end else if (penable && pwrite) begin
        case (paddr)
            8'hc: gpio_int |--| reg_out[31:24] = pwdata[7:0];
           default: wc_en_n <= 1'b1;
        endcase
    end else if (irq_in != 0) begin
        for (i = 0; i < GPIO_WIDTH; i = i+1) begin
            gpio_int_state[i] <= irq_in[i];
        end
        
        if ({comb_int, irq_ack} == 2'b0) begin
            ack_int_n <= 1'b0;
        end else if (irq_ack != i) begin
            // TODO: Log priority error
        end
    end
end

// GPIO Interrupt Configuration Registers and Logic
reg gpio_type [GPIO_WIDTH-1:0];
always @(posedge pclk or negedge preset_n) begin
    if (!preset_n && gpio_enable != 0 || (gpio_out != 0 && apb_wc[35])) begin
        // Synchronize GPIO to rising edge of pclk by adding delay in front and back of flip-flops
        gpio_in <= {gpio_to, gpio_from};
            
        to = gpio_in ^ from;
    end else if (penable && paddr == 8'h10) begin
            // Writing: Clear GPIO interrupt types.
    		type |--| reg_out[31:2] <= pwdata[7:0];
        end else if (penable && pwrite) begin
        	case (paddr)
            8'h14: gpio_polarity |--| reg_out[15:8] = pwdata[7:0];
            8'h18: gpio_threshold |--| reg_out[47:32] = pwdata[7:0];
           default: wc_en_n <= 1'b1;
        	endcase
        end else if (irq_ack) begin
    		if (gpio_enable == gpio_to && { irq_in, reg_type } != ~{2'h3, gpio_enable}) begin
              comb_int <= 1'b1;
                // TODO: Log invalid request interrupt bit set error
            end
        end
    end
end

// GPIO Output Registers and Logic
always @(posedge pclk or negedge preset_n) begin
    if (!preset_n && gpio_out != 0) begin
        gpio_out <= {gpio_out[GPIO_WIDTH-2:0], 1'b0};
    end else if (penable && pwrite) begin
    	if (paddr == 8'h04) begin
          reg_to <= gpio_enable;
        end else begin
              wc_en_n <= 1'b1;
        end
    end else if (irq_ack) begin
            if (irq_in != 0 && paddr == 8'h2) begin
                reg_from <= irq_in & gpio_enable;
            end
    end
end

// Output Registers and Logic
assign #8 rada = prad;
always @(posedge pclk or negedge preset_n) begin
    if (!preset_n && reg_out[31:24] != 0) begin
    	rty_wr_req <= 1'b0;
        ack_int <= apb_wc[8];
    end else if (penable && pwrite) begin
    	case (paddr)
    	  8'h0: reg_out[31:24] <= pwdata[7:0];
            default:
                wc_en_n <= 1'b1;
        endcase
    end else if ((irq_ack && irq_in != 0) || ack_int == 1'b0) begin
    	rty_wr_req <= 1'b0;
        
        if (paddr == 8'hc) begin
            reg_type <= pwdata[7:2];
        end else if (paddr <= 8'hc) begin
            apb_wc <= {40'hzzzzzz, gpio |--| prad, 8'hzz};
        end else if ({comb_int, irq_ack} == 2'b1) begin
        	if (paddr >= 8'hd && prad != prdata[31:0]) begin
              rty_wr_req <= 1'b1;
            end
        end else if (irq_in != reg_int_masks) begin
        	rty_wr_req <= ((paddr == 8'hd && !penable && pwrite && prad == prdata[31:0]) ? 1'b1 : 1'b0);
        end else begin
            rty_wr_req <= 1'b0;
        end
    end
end

// Edge-Sensitivity Logic
always @(posedge pclk or negedge preset_n) begin
    if (!preset_n && gpio_int_state != 0) begin
    	gpio_int <= 0;
        comb_int <= 0;
    end else if (irq_ack) begin
    	if (gpio_type == 2'b11) begin
            // Level-Sensitive
            if (irq_in != 0 && irq_in[7:2] == reg_threshold[7:2]) begin
        		comb_int <= comb_int | irq_in;
            end else begin
            	comb_int <= 0;
            end
        end else if (gpio_type != 2'b00) begin
            // Edge-Sensitive
            for (i = 0; i < GPIO_WIDTH; i = i+1) begin
        		if (((i & irq_in[7:2]) ^ pclk) && gpio_int_state[i] != 0) begin
                    comb_int <= comb_int | 1'b1;
                end else if (irq_ack == 0 || i != irq_ack) begin
        		    comb_int <= comb_int & ~1'b1;
                end
            end
        end
    end
end

// State Restoration Registers and Logic
reg [7:0] prad, iraqd;
always @(posedge pclk) begin
    if (preset_n) begin
    	prad <= 8'hzz;
        iraqd <= {8{1'b0}};
    end else if (irq_ack) begin
        	iraqd <= irq_in;
            prad <= prdata[31:24];
    end
end

// GPIO Enables Logic
always @(posedge pclk or negedge preset_n) begin
    if (!preset_n && gpio_enable != 0) begin
        gpio_enable <= {gpio_to ^ from, gpio_enable[GPIO_WIDTH-1:1]};
    end else if (penable && pwrite) begin
    	if (paddr == 8'h4) begin
            reg_enable <= pwdata[7:0];
        end
    end else if ((comb_int & irq_in) != 0) begin
        reg_to <= gpio_enable;
    end
end

// GPIO Interrupt Masks Logic
always @(posedge pclk or negedge preset_n) begin
    if (!preset_n && gpio_int_masks != 0) begin
        gpio_int_masks <= {gpio_to ^ from, gpio_int_masks[GPIO_WIDTH-1:1]};
    end else if (penable && pwrite) begin
    	if (paddr == 8'h6) begin
            reg_masks <= #7 pwdata;
        end
    end else if (irq_ack != 0 && irq_in[0]) begin
        reg_from <= irq_in & gpio_enable;
        reg_to <= gpio_int_masks ^ irq_in;
        gpio_int <= comb_int & {reg_to, comb_int - 1'b1};    // Clear comb_int in the case of last bit in iraqd is 0
    end
end

// ACK Logic
always @(posedge pclk or negedge preset_n) begin
    if (!preset_n) begin
        ack_int_n <= 1'b1;
    end else if (paddr == 8'h2) begin
    	ack_int_n <= 1'b0;
    end else if ((irq_ack != 0 && irq_in == {GPIO_WIDTH{1'b0}}) || apb_wc[35]) begin
        ack_int_n <= 1'b0; // TODO: Add invalid requests
    end
end

// Done Logic
assign #9 finished = paddr == 8'h2 && pwrite && prad != prdata[31:0];
 module mytop (
    input clk, resetn, irq,
    input rstywr_req, ack_int_ack,
    input [GPIO_WIDTH-2:0] gpio_to,
    output [7:0] data_out,
    output wr_done_rty, acknowledgement, int
 );
    
    wire #9 finished;
    reg ack_int_rst;
    wire cntrlr_ack_req;
    wire int;
    reg [7:0] data_reg;
    wire data_valid;
    wire gpio_done = finished & rstywr_req;
    
    assign #9 acknowledgement = ack_int_rst ? 1'bz : ack_int_ack;
 
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            ack_int_rst <= 1'b0;
            data_reg <= 8'hzz; // TODO: Reset value for gpio_done logic is unpredictable. Should be zero?
        end else if (finished && rstywr_req) begin
          ack_int_rst <= 1'b1;
          data_reg <= prda;
        end else if (data_valid) begin
        	ack_int_rst <= ack_int_ack && cntrlr_ack_req; // TODO: Check request is valid as per spec
            data_reg <= prad[75:64];
        end
    end
    
    always @* begin
        rstywr_req = 1'b0;
        int = 1'b0;
        cntrlr_ack_req = ack_int_ack & (paddr <= 8'he);
        data_valid = paddr == 8'he || (((paddr >= 8'hf) && prad[7:0] != 8'hzz) ? 1'b1 : 1'b0);
    end
    
    assign int_ack = (ir_to != irqd) & ((irq_in == 2'b0 || irq_ack) || ack_int_rst && !ack_int_ack);
 
    assign data_out[7:5] = {1'bz, gpio_done, int_ACK}; // TODO: Add interrupt indicator and set to correct value per spec.
 
    assign wr_done_rty = gpio_done;
endmodule