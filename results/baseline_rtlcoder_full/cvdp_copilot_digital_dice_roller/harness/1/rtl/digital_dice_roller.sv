<s> module digital_dice_roller (
  input clk,
  input reset_n,
  input button,
  output reg [2:0] dice_value
);

  // Define the states for the Finite State Machine
  parameter IDLE = 3'b000;
  parameter ROLLING = 3'b100;
  
  // Define the counter and its states
  reg [5:0] counter;
  always @ (posedge clk) begin
    if(!reset_n) begin
      counter <= 6;
    end else if(counter == 7'b1111111) begin
      counter <= 0;
    end else begin
      counter <= counter + 1;
    end
  end
  
  // Define the states for the FSM and their outputs for this module
  reg [2:0] state;
  always @ (posedge clk) begin
    if(!reset_n) begin
      state <= IDLE;
      dice_value <= 3'b000;
    end else if(button && state == IDLE) begin
      state <= ROLLING;
      dice_value <= 3'b000;
    end else if(!button && state == ROLLING) begin
      state <= IDLE;
      dice_value <= 3'b111; // Output the last value
    end
  end
  
  // Assign the counter value to the output, when it's in the acceptable range for a Dice value
  always @ (posedge clk) begin
    if(counter == 6 && state == ROLLING) begin
      dice_value <= 3'b001;
    end else if(counter == 5 && state == ROLLING) begin
      dice_value <= 3'b010;
    end else if(counter == 4 && state == ROLLING) begin
      dice_value <= 3'b011;
    end else if(counter == 3 && state == ROLLING) begin
      dice_value <= 3'b100;
    end else if(counter == 2 && state == ROLLING) begin
      die_value <= 3'b101;
    end else if(counter == 1 && state == ROLLING) begin
      dice_value <= 3'b110;
    end else begin
      dice_value <= 3'b111; // Output 6, when counter goes out of range
    end
  end
  
endmodule