module car_parking_system #(parameter TOTAL_SPACES = 12) (
    input clk,
    input reset,
    input vehicle_entry_sensor,
    input vehicle_exit_sensor,
    output reg [log2(TOTAL_SPACES)-1:0] available_spaces,
    output reg [log2(TOTAL_SPACES)-1:0] count_car,
    output reg led_status,
    output reg [6:0] seven_seg_display_available_tens,
    output reg [6:0] seven_seg_display_available_units,
    output reg [6:0] seven_seg_display_count_tens,
    output reg [6:0] seven_seg_display_count_units
);

// Define state variables
reg [1:0] current_state;
reg [1:0] next_state;
reg [log2(TOTAL_SPACES)-1:0] available; // Available Spaces counter
reg [log2(TOTAL_SPACES)-1:0] count; // Count of cars currently parked

// Define state encoding
parameter Idle = 2'b00;
parameter EntryProcessing = 2'b01;
parameter ExitProcessing = 2'b10;
parameter Full = 2'b11;

initial begin
    // Reset the system
    current_state <= Idle;
    next_state <= Idle;
    available <= TOTAL_SPACES;
    count <= 0;
    led_status <= 1; // Initialize to Parking Available status
    seven_seg_display_available_tens <= 7'b0000001;
    seven_seg_display_available_units <= 7'b1000000;
    seven_seg_display_count_tens <= 7'b0000001;
    seven_seg_display_count_units <= 7'b1000000;
end

always @(posedge clk) begin
    if (reset) begin
        // Reset the system
        current_state <= Idle;
        next_state <= Idle;
        available <= TOTAL_SPACES;
        count <= 0;
        led_status <= 1; // Initialize to Parking Available status
        seven_seg_display_available_tens <= 7'b0000001;
        seven_seg_display_available_units <= 7'b1000000;
        seven_seg_display_count_tens <= 7'b0000001;
        seven_seg_display_count_units <= 7'b1000000;
    end else begin
        // Update the state machine
        current_state <= next_state;
        
        case (current_state)
            Idle: begin
                if (vehicle_entry_sensor) begin
                    next_state <= EntryProcessing;
                    available -= 1;
                    count += 1;
                    led_status <= 0; // Parking full status
                    seven_seg_display_available_tens <= 7'b1000000;
                    seven_seg_display_count_tens <= count / 10;
                    seven_seg_display_count_units <= (count % 10);
                end else if (vehicle_exit_sensor) begin
                    next_state <= ExitProcessing;
                    increment_spaces();
                    decrement_cars();
                    led_status <= 1; // Parking Available status
                end
            end
            EntryProcessing: begin
                next_state <= Full;
                available -= 1;
                count += 1;
                led_status <= 0; // Parking full status
                seven_seg_display_available_tens <= 7'b1000000;
                seven_seg_display_count_tens <= (~count[log2(TOTAL_SPACES)-2:0] & ~count);
                seven_seg_display_count_units <= count[log2(TOTAL_SPACES)-1];
        // No need to update the display for the number of cars as we incremented it in EntryProcessing state
                    end
            ExitProcessing: begin
                next_state <= Idle;
                decrement_spaces();
                decrement_cars();
                led_status <= 1; // Parking Available status
                                    
                seven_seg_display_available_tens <= 7'b0000001;
                seven_seg_display_available_units <= seven_seg_display_count_tens[6:0];
                    // TODO: Update the display if cars are present
                seven_seg_display_count_tens <= seven_seg_display_count_tens;
                seven_seg_display_count_units <= seven_seg_display_count_units;
            end
        endcase
    end
end

// Helper functions for updating the state machine
function logic increment_spaces; return logic; integer space;
    input [log2(TOTAL_SPACES)-1:0] count_upward;
    reg [log2(TOTAL_SPACES)-1:0] count;
    begin
        count >= 1 ? (space = next(count_upward)) : (space = TOTAL_SPACES); // Wrap around at max
        increment_spaces <= space!=current || space!=next(count, count_upward) || (count + 1) != current;   // Check if we need to increment spaces
    end endfunction

function logic decrement_spaces; return logic; integer space;
    input [log2(TOTAL_SPACES)-1:0] count_downward;
    reg [log2(TOTAL_SPACES)-1:0] count;
    begin
        decrement_spaces <= (count[log2(TOTAL_SPACES)-2]-1)!=(count[log2(TOTAL_SPACES)-1]) ||  // Check if we need to decrement spaces, no overflowing or underflowing
            next(count_downward)!=(count != 0) || count + -1 != current;   
    end endfunction

function logic decrement_cars; return logic; integer car;
    reg [log2(TOTAL_SPACES)-1:0] count_max;
    begin
        decrement_cars <= decrement_spaces(count-car) && total_space(current) ? 1 : 0;   // Check if we need to decrement cars
    end endfunction

function logic increment_cars; return logic; integer car;
    reg [log2(TOTAL_SPACES)-1:0] count_car;
    register regs[5:0]; // Segments encoder of the display
    assign seven_seg_display_count_tens = {regs[6], regs[5], regs[4]} + 1'b0;        // Add one to the count tens digit
    assign seven_seg_display_count_units = {regs[3], regs[2], regs[1], regs[0]};      // Encoder segment of the count units digit
    begin
        // Calculate the number of cars in real time from the current parking space status
        for (car=count-1; car>=0 && decrement_spaces(current, 1)!=0; car=car-1) count_max <= total_space(~current) ? 2'h0 : ~TOTAL_SPACES;            // Scan the parking space count from maximum to minimum as this should be the first one available
            
        increment_cars <= decrement_spaces(count_max) || increament_spaces(count) ;   // Check if we need to increment cars and update the display accordingly or not
    end endfunction

function logic total_space; return logic; integer count;
    begin
        total_space <= (current[log2(TOTAL_SPACES)-1]&TOTAL_SPACES) != current;       // Check if the most significant bit is 0 or not, where we know all parking space are available
    end endfunction

always @* begin
    count_max <= total_space(current) ? log2(TOTAL_SPACES-1) : log2(`log2(TOTAL_SPACES)); // Count max can be any place in the parking lot. log2 for binary to decimal conversions
    current <= increment_cars && count < count_max ? current + 1'b1 : 
              decrement_spaces == total_space(current) ? TOTAL_SPACES - 1'b1 : current; // If we were able to increament cars the counter should be updated, else if all parking spaces are free set parking status to full
    count <= increment_cars && count < total_spaces-1 ? (count == 0 && decrement_spaces) ? 0 : count + 1'b1 : decrement_cars-(current==0)?1'b0:--count;     // If we were able to increament cars the counter should be updated, else if all parking spaces are full set parking status to Parking Available
end

assign seven_seg_display_available_tens = 7'b0000001;
assign seven_seg_display_count_units = (count % 10)+2'h4; // O(TOTAL_SPACES); if more significant bit is set, count is greater than 9 and needs to shifted on its own.
endmodule