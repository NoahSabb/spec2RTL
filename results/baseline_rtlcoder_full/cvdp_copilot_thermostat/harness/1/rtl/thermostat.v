<s> module thermostat (
  input clk,      // Clock input
  input rst,      // Asynchronous reset input
  
  input [5:0] temp_feedback,    // Temperature Feedback Inputs
  input enable,  // Enable/disable control
  input fan_on, // User control to turn the fan on or off
  
  output reg [5:0] out_heater,    // Heating Outputs
  output reg [2:0] o_state,     // FSM Output State
  output reg fan, // Fan Control
);

  parameter HEAT_FULL = 3'b100;
  parameter HEAT_MED = 3'b010;
  parameter HEAT_LOW = 3'b011;
  parameter COOL_FULL = 3'b001;  // A2I: Reverses ordering in spec - full (hot) is higher state than med/low  
  parameter COOL_MED = 3'b000;
  parameter COOL_LOW = 3'b110;
  parameter AMBIENT = 3'b100;
  
  // FSM State declaration
  reg [2:0] fsm_next_state, fsm_state;
  
  always @ (posedge clk or negedge rst) begin
    if(!rst) begin
      {fsm_state, fan} <= AMBIENT + 1'b0; // Initialize to "Off" state by default. Not sure how it's supposed to behave if reset while on.   
    end
     else if (enable) begin
       case(fsm_next_state)
         HEAT_LOW : {fsm_state, fan} <= HEAT_LOW + 1'b0; // Output logic depends on the state
         HEAT_MED : {fsm_state, fan} <= HEAT_MED + 1'b0; // Don't force heating at this time.
 module heaters (
   input clk,         
   input fsm_state,   
   output reg out_full,
   output reg out_med,
   output reg out_low
 );
     
 assign out_low = fsm_state == HEAT_LOW;  // Only output if the appropriate heating state is active.
 assign out_full = fsm_state == HEAT_FULL;
 assign out_med = fsm_state == HEAT_MED;

   always @ (posedge clk or negedge rst) begin
     if(!rst) begin
       out_low <= 0;
       out_full <= 0;
       out_med <= 0;
     end else if ((i_temp_feedback[5] || i_temp_feedback[4]) == 1 && fsm_state != AMBIENT) begin // Only heat when necessary, and only in the appropriate state.  
 module fault ( 
    input clk,          // Clock input
    input fsm_state_next,     // Next FSM State Input
    output reg i_fault      // Fault Signal
 );
    always @ (posedge clk or negedge rst) begin
      if(!rst) begin
        i_fault <= 0;
      end else if ((temp.i_full_cold || temp.i_medium_cold) && fsm_state == AMBIENT) begin // Only fault when the temperature is too cold (for hot condition), and in AMBIENT state (don't care what it does otherwise)
        i_fault <= 1;
      end else if ((temp.i_full_hot || temp.i_medium_hot) && fsm_state == COOL_FULL || fsm_state == COOL_MED) begin // Fault if we're in a cooling state, but the temperature is too hot.  The user can always override this with the fan on.
 module heaters_and_aircons (
   input clk,         
   input fsm_next_state,   // FSM Next State input
   output reg o_fan      // Fan Outputs
 );

  always @ (posedge clk or negedge rst) begin
    if(!rst) begin
      o_fan <= 0;
    end else if (((temp.o_heater_full || temp.o_heater_medium || temp.o_aircon_full || temp.o_aircon_medium) && fsm_next_state == AMBIENT) || ((~i_fault) && fsm_next_state != AMBIENT)) begin    // Only turn on fan if the thermostat is active, or a fault condition occurs
      o_fan <= 1'b1;  
    end else begin
      o_fan <= 0;   
    end
  end

 } // module instantiation
       end
     end   
   end
 endmodule