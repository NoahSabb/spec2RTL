<s> module microcode_sequencer(
    input clk,
    input c_inc_in,
    output c_inc_out,
    input c_n_in,
    output c_n_out,
    input cc,
    input [3:0] d_in,
    output reg [3:0] d_out,
    input full,
    input push,
    input pop,
    input src_sel,
    input stack_we,
    output ien,
    input r_en,
    output en
);

reg c_inc, c_n;
wire [4:0] instr_in;
wire stack_push, stack_pop, empty, full;
wire out_ce;
wire [3:0] stack_mux_sel, a_mux_sel, b_mux_sel;
wire d_out_mux_sel;
reg r, s;
wire [3:0] result_data;

// Instruction Decoder
instruction_decoder id(
    .clk(clk),  // input
    .instr_in(instr_in)     ,// output
    .cc(cc),
    .push(push),
    .pop(pop),
    .src_sel(src_sel)       ,  
    .out_ce(out_ce)         ,
    .full(full),
    .c_inc_in(c_inc),  // output
    .c_n_in(c_n),       //output
    .stack_push(stack_push),
    .stack_pop(stack_pop)     ,
    .stack_mux_sel(stack_mux_sel)        ,  
    .a_mux_sel(a_mux_sel),  
    .b_mux_sel(b_mux_sel)       ,
    .empty(empty),
    .c_inc_out(c_inc_out),  // output
    .c_n_out(c_n_out)           
);
 module instruction_decoder (
    input clk,
    output reg [4:0] instr_in ,
    output reg cc,
    output reg push,
    output reg pop,
    output reg src_sel, 
    output reg out_ce,
    output reg full,
    output reg c_inc,
    output reg c_n,
    output reg stack_push,
    output reg stack_pop,    
    output reg [1:0] stack_mux_sel,
    output reg [4:3] a_mux_sel,
    output reg [4:3] b_mux_sel,
    output reg empty,
	output reg ien,
	output reg r_en,
    output reg en
  );
    // input registers
    always @(posedge clk) begin
        if (clk !== 0) begin
            instr_in <= #1 {instr_in[3:1], d_in[4]};
            cc <= #1 cc;
            push <= #1 push;
            full <= #1 full;
            c_inc <= #1 c_inc;
            c_n <= #1 c_n;
            stack_push <= #1 stack_push;
            stack_pop <= #1 full & stack_push;
            s <= #1 en;
        	en <= r;  // flip flop implementation 
        end
    end		
    
    always @ (posedge clk) begin
        if (full || stack_push)
	      empty <= 0;
	    else if (pop & ~empty)
	      empty <= 1;
	    // r is used as the flip flop for en
	  r <= s;
         if(out_ce) ien <= 1'b0; // this is an optimized design where we don't need a register to hold input data
        //cc and src_sel are set through decoding of instruction opcode (instr_in[4:3])
	   case(instr_in[4:2])
	    "0 00": cc <= #1 1'b0;                 
	    "0 01": cc <= #1 ~cc;                    
	    "0 10": src_sel <= #1 ~src_sel;        
	   endcase
	    
	   out_ce <= #1|(instr_in[1:0]==0) ? 0 : cc;  // output enable is asserted only when the control is not stalled by cc=1, which can be set as result of opcode decoding (instead of using a comparator/mux to decide on the fly)
	   
     	////////////////////////////////////
	   // Multiplexer Selects 
	   ///////////////////////////////

	  if(instr_in[1:0]==4'b00) begin
	    stack_mux_sel <= #1 d_out_mux_sel;
        a_mux_sel <= #1 instr_in[3:2];
      end
	  else begin

	    // Set to full adder inputs based on the decoder selection
	    if (s || r_en) 
	       a_mux_sel <= #1 2'b10;  // aux_reg 
	    else                    
	      b_mux_sel <= #1 2'b10;  // program counter 
 
        case(instr_in[3:2]) 	   
          "0 0": d_out_mux_sel = 1'b0;   // fetch pc
          "0 1": d_out_mux_sel = 1'b1;   // fetch aux_reg
          "0B": d_out_mux_sel = 1'b0;   // push pc 
	      default: d_out_mux_sel <= #1 1'b1;
 module_select  ; // read aux_reg
        endcase
      end
    end

    // Microcode arithmetic unit (we have a full-adder here instead of shifter)
	// A and B selects are based full adders, and d_out is the output. (Auxiliary register contents could be stored in module registers, but this is for microcode execution)
    // Program counter output is routed via aux or full adder  module, as selected by the instruction decoder

	full_adder fa(
        .a_input (a_mux_sel==2'b10 ? d_out[3:0] : reg_d_in_1[3:0]),   // Program counter input to full adder A input
	.b_input (b_mux_sel==2'b10 ? d_out[3:0]     : result_data), // Stack data is routed based on decoder control
        .cin  (s || r_en),                    // Full Adder module assumes a 1-bit input as carry input. This input (carry in) has to be synchronized with data inputs when the control is being written out from a register, else we may end up in a weird result for add operations due to carry propagation effects
        .sum  (d_out[3:0]),                   // Full adder output is routed as the actual D value. 
        .cout ()                             // Carry out could be monitored from registers, but we aren't doing that 
    );

    
	
    
  // This auxiliary register is used in stack unit (in the above example it has no data input and outputs the contents as-is).
 module reg_din (
    input clk,
    output reg [3:0] d_out ,
    input ien,
    input r_en,
    input en,  // Write Enable control Signal from result register.
    input data_in // Data input could be the actual stack data in case of the stack memory unit or program counter value if control is being written out and this value is to be reloaded later as we proceed. It could also be a constant data value that was not changed at all, (which was the scenario with PUSH instruction) 
    output reg d_out_change // an indication of actual data change in the module register if any. It indicates only about changes in the data content and nothing else (so, it should not be used for data dependancy tracking  or anything more than a straight forward Write Enable indicator) 
  );
    
    reg [3:0] d_in;
  
  // write data into register if enabled
  always @(posedge clk) begin
    if (r_en | ien)
      d_out <= #1 en ? data_in : d_out;
       
    // this is more of an input register used to store inputs for the decoding logic in case of fetch. There are no actual write back operations on it. Its only used as an intermediate registers
    if (s) d_in <= #1 d_out;               
    else {                           
        reg s;                
      }                         
  end      
    
   // Output change is registered only when the output data changes, and a "change" signal is asserted during register read. (So the change is useful to track potential reload operations on those registers by the stack memory in place where they came from, which is typically used to implement a stack unit) 
  always @(posedge clk) begin
    if (r_en | en)
      d_out_change <= #1 ~(d_in == d_out);                  
    else
      d_out_change <= #1 1'b0; // we don't need to track changes when not writing back, (and also don't do anything with this signal since this is a result register)
  end    
      	 
endmodule

// Full adders for the Stack memory operations
module full_adder( 
    input [3:0] a_input ,
    input [3:0] b_input,
    output [3:0] sum    ,  
    output cout         
);

assign sum = a_input + b_input;
assign  cout= (a_input[3] & b_input[3]) | (sum[3]&(a_input[2] ^ b_input[2])) | ((a_input == 4'b1001) & b_input[0]);

endmodule