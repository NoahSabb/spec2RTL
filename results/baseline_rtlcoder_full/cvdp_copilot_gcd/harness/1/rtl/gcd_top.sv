<s> module gcd_top (
    clk, rst, A, B, go,
    OUT, done);

parameter WIDTH = 4;
    
input clk;
input rst;
input [WIDTH-1:0] A;
input [WIDTH-1:0] B;
input go;
output reg [WIDTH-1:0] OUT;
output reg done;
    
wire equal, greater_than;
reg [WIDTH-1:0] A_ff, B_ff;

gcd_controlpath gcp (
    .clk(clk),
    .rst(rst),
    .go(go),
    .equal(equal),
    .greater_than(greater_than),
    .controlpath_state(controlpath_state)
);
 module gcd_controlpath (
     input clk, rst, go,
     output reg equal, greater_than,
     output reg [1:0] controlpath_state
 ) ;
    
  // Finite state machine states:
  parameter IDLE = 2'b00;
  parameter DONE = 2'b01;
  parameter A_GT_B = 2'b10;
  parameter B_GT_A = 2'b11;  

  // State, Next State, and Output registers:
  reg [1:0] state, next_state;
  wire OUT_wire;
  assign OUT=OUT_wire;
  always @ (posedge clk) begin
    if (rst) begin
      state <= IDLE;
      equal<=0;
      greater_than<=0;
    end else begin
      state <= next_state;
      
      case(state)
        // State transition logic
        IDLE:begin
          if (go) next_state == A_GT_B;   
        end
        
        DONE:begin
          if (!go) next_state=IDLE;
        end
        
        A_GT_B: begin
          if (A>B) 
            next_state = A_GT_B;
          else if(equal) next_state=A_GT_B;
          else     next_state=B_GT_A;
        end
        
        B_GT_A: begin
          if (B>A) 
            next_state = B_GT_A;
          else if(equal) next_state=B_GT_A;
          else     next_state=A_GT_B;
        end
         default : begin
          next_state=IDLE;
        end
      endcase // case (state)
      
      case (next_state)
        A_GT_B:
          equal<=0;  greater_than<=1;
        
        B_GT_A:
          equal<=1;  greater_than<=0;
        
        default : begin
          equal<=0;  greater_than<=0;
        end
      endcase // case (next_state)
    end
  end
  assign controlpath_state=state;
 endmodule  
 
gcd_datapath gcp (
    .clk(clk), rst, A_ff, B_ff,
    .OUT(), equal, greater_than,
    .controlpath_state(controlpath_state) );
module gcd_controlpath (
    input clk, rst,
    input [WIDTH-1:0] A_ff, B_ff,
    output reg [WIDTH-1:0] OUT,
    output reg equal, greater_than, 
    input [1:0] controlpath_state); 
  initial OUT=WIDTH;
  always @ (posedge clk) begin
    if (rst) begin
      OUT <= WIDTH;
    end else begin
    	begin
      	if(controlpath_state==A_GT_B) begin    	 
          if(A_ff>B_ff) B_ff=A_ff - B_ff;
         A_ff=A_ff-B_ff;       
       end // else if (B_ff > A_ff)  
       else begin                   
         if(A_ff>B_ff) B_ff=A_ff - B_ff;
         A_ff=A_ff-B_ff; 
       end // subtraction logic
     end  
     
     if (equal==1) begin
        OUT <= {1'b0, A_ff, B_ff};
        done<=1;
     end
     else if ((A_ff == 2'b0 || B_ff == 2'b0) && equal==1) begin
 module gcd_datapath (
    input clk, rst,
    input [WIDTH-1:0] A, B,
    output reg [WIDTH-1:0] OUT,  
    output reg equal, greater_than, 
    input [1:0] controlpath_state); 
 
    always @ (posedge clk) begin
      if (rst) begin
        A <= WIDTH;
        B <= Width;
      end else begin
        A_ff<=A;
        B_ff<=B;    
        
       equal <= (A == B);  greater_than <= (A > B);  
                           
       OUT <= equal ? (A & B) : gcd (B, A % B);     
      end
    end // always @ (posedge clk)
   
 endmodule // gcd_datapath
    end 
  end 
endmodule