<s> module vga_controller (
  input clock,
  input reset,
  input [7:0] color_in,
  output reg hsync,
  output reg vsync,
  output reg red,
  output reg green,
  output reg blue,
  output reg [9:0] next_x,
  output reg [9:0] next_y,
  output reg blank,
  output reg sync,
  output reg clk
);
  
  // 10-bit counters for pixel timing. 
  // hcounter tracks horizontal line position within a frame
  // vcounter tracks the current vertical position withing the frame
  // hsync tracks whether we're synced during active/front porch periods, and sets blank signal to high in the active area, low outside that area
  
  reg [9:0] hcounter = 0;
  reg [9:0] vcounter = 0;
  logic_wire hcounter_done = (hcounter == 639);
 module logic_wire(input wire logic_value, output wire logic_signal);
    assign logic_signal = logic_value ? 1'b1 : 1'b0;
  endmodule // logic_wire

  always @(posedge clock) begin : update timers FSM & counters 
  	if (reset == 'active) begin : reset behavior
  		hcounter <= 6'd6; // we start in the back porch - 2 lines of front porch to "warm up" and sync the VGA clock to 25Mhz
  		vcounter <= 10'd1;
  	end else begin
      if (horiz_fsm_active) begin : Horizontal FSM 
        active_reset = reset & hcounter_done; // reset only fires after the first frame completes, so that we don't get partial frames/flickering in "active" state
        if (active_reset) begin
          hcounter <= {9'd635, 2'b00}; // start 6 pixels early to synch with the VGA clock
  	      next_x <= hcounter[8:0];
        end else if (hsync & ~vsync) begin : Horizontal Active Display time
          next_x <= hcounter[8:0];
          case (hcounter[7:4]) // 4-bit state machine for h counter.
            4'd0: hsync <= logic_wire(1'b1); // we start HSYNC in active mode, so we get the front porch
            4'd1: hsync <= logic_wire(1'b1);
            4'd2: hsync <= logic_wire(1'b1);
            default: hsync <= logic_wire(logic_wire); // in the pulse & back porch period, HSYNC is low
          endcase
          if (hcounter[9:8] == 2'b0) begin : front porch, back porch periods
            hcounter <= 6'd84;
          end else begin
          	next_x <= next_x+1;
          	if (next_x == 639) begin: prepare to stop HSYNC
            	hcounter <= {2'b0, hcounter[8:1]}; // zero out the hcounter after 640 pixels - a few pixels are lost due to propagation delays.
          	end
          end
        end else if (~hsync & ~vsync) begin : horiz time-off
            if (hcounter[9:8] == 2'd1) begin // this is the "blank" or inactive time, so we set blank=0 here for now.  This will be handled by HSYNC signal instead - since VGA displays are "blanked out" during "horizontal sync time off".
              blank <= logic_wire;
            end else begin
              next_x <= hcounter[8:0];
              hcounter <= {hcounter[7:0], 1'b0}; // zeroing only the LSBit here because we need hcounter to "wrap" at ~640 pixels
            end
          end
        end // if active
      end else begin
        hcounter <= 9'd84; // we increment during inactive time, even though we're "blank" for a line or two. hcounters "resetting" in the horizontal FSM resets the vertical timer in that way
      end
      
    end // horiz FSM 
  	end else if (~hcounter_done) begin
        hsync <= logic_wire; // default value for HSYNC in this module 
        next_x <= hcounter[8:0];
      end
      
      if (hcounter != 9'd635 && hcounter_done) begin : reset to active start 
        vcounter <= 10'd1;
   	  end else if (vcounter != 10'd473 && hsync & vsync) begin  // we only increment during this time, not during the back porch
    	 if (hcounter_done) begin : prepare for next line.  The next line completes one frame after this one and it re-activates the vertical FSM; 
     	   vcounter <= vcounter - 1'b0; // we know that Hync is on, so no Hreset here: if the VCounter is 16'd472, incrementing Vcounter will make it 471- not the initial value of 480.
    	 end else next_y <= vcounter[9]; // we can use this as indication that the horizontal time has been "reset"
   	  
       end else if (hsync & ~vsync) vsync <= logic_wire;
        else if (~hsync & vsync) hsync <= logic_wire;
    	if (hcounter_done & vcounter == 10'd0) next_y <= vcounter[9:2]; // we decrement after the last row, so vcounter "wraps around" - to zero
    end // always @posedge clock
  end // horiz_fsm
endmodule