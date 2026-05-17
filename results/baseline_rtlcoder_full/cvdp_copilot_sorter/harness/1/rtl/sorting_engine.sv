Module sorting_engine(
    input clk,
    input rst,
    input start,
    input [N*WIDTH-1:0] in_data,
    output reg done,
    output reg [N*WIDTH-1:0] out_data
);

parameter N = 8;
parameter WIDTH = 16;

reg [2:0] state;
parameter IDLE = 3'h0, SORTING = 3'h1, DONE = 3'h2;
reg [0:6] i;
wire [WIDTH-1:0] data_from_bus[6:0];
reg [WIDTH-1:0] sorted_data[6:0];
reg done = 0;
reg [8:0] current_value, next_value;
reg pass = 0;

integer swap_count;

// Instantiate a bubble sort engine module here
module bubble_sorter(
    input clk,
    input rst,
    input done,
    input [6:0] data_in,
    output reg [6:0] sorted_data_out,
    output reg swap_count_out
);

wire [6:0] swapped;
bubble_sorter_engine bse(
    .clk(clk),
    .done(done),
    .in(swapped),
    .out(sorted_data_out),
    .swap_count_out(swap_count_out)
);

// The actual bubble sorter engine module implementation goes here.
reg [6:0] sorted[7:0];
reg [3:0] pass_count = 0;
always @(posedge clk or posedge rst) begin
    if (rst) begin
        pass_count <= 0;
    end else if (!done) begin
        sort.clk <= clk;
        sort.in[6:0] <= data_from_bus[pass][7:1];
        sort.out[6:0] <= swapped;
        
        if (swap_count_out == 0 && pass_count >= 1) begin
            // Done with this pass
            done <= 1;
        end else if (sorted_data_out[0] < sorted_data_out[1]) begin
            swapped[0] <= sorted_data_out[0];
            swapped[1] <= sorted_data_out[1];
            swap_count_out <= 1;
        end else if (sorted_data_out[1] < sorted_data_out[2]) begin
            swapped[1] <= sorted_data_out[2];
            swapped[2] <= swapped[1];
            swap_count_out <= 1;
        end else if (sorted_data_out[2] < sorted_data_out[3]) begin
            swapped[2] <= sorted_data_out[3];
            swapped[3] <= swapped[2];
            swap_count_out <= 1;
        end else if (sorted_data_out[3] < sorted_data_out[4]) begin
            swapped[3] <= sorted_data_out[4];
            swapped[4] <= swapped[3];
            swap_count_out <= 1;
        end else if (sorted_data_out[4] < sorted_data_out[5]) begin
            sorted_data_in[4] <= swapped[5];
            swapped[5:4] <= {swapped[4], swapped[3]};
            swap_count_out <= 1;
        end else if (sorted_data_out[5] < sorted_data_out[6]) begin
            sorted_data_in[5] <= swapped[6];
            swapped[6:5] <= {swapped[4], swapped[3]};
            swap_count_out <= 1;
        end else if (sorted_data_out[6] < sorted_data_out[7]) begin
            sorted_data_in[6] <= swapped[7];
            swapped[7:6] <= {swapped[5], swapped[4]};
            swap_count = 1;
        end
        
        if (sorted_data_out[0] == 0 && pass != 0) begin
            pass_count <= 0;
            pass <= 1;
        end else if (pass == N) begin
            done <= 1;
            pass <= 0;
            pass_count = pass + 1;
        end else if (swap_count_out > 0 && pass != sorting_engine.pass) begin
            swap_count <= 0;
            pass <= pass + 1;
        end
    end
end

assign sorted_data[7] = out_data[WIDTH*6+:WIDTH]; // Store the last element first to mimic array notation

always @(posedge clk or posedge rst) begin
    if (rst) begin
        data_from_bus <= 0;
        sorted_data_out <= 0;
        swap_count_out <= 0;
    end else if (!done && start) begin
        // Get the input data from the bus into memory
        for (i = 0; i < N-1; i=i+1) begin
            data_from_bus[i] = in_data[N*(i+1):WIDTH*i];
        end
        
        current_value <= data_from_bus[0][0:6];
        next_value <= 9'd0;
        pass <= 1;
    end else if (!rst && start) begin
        // Assign the values back to the output bus by sorting them.
        for (i = 6; i >= 0; i=i-1) begin
            sorted_data[i] <= 0;
        end
        for (i = N-2; i >= 0; i=i-1) begin
            sorted_data[0] <= data_from_bus[i][0:6];
            for (integer j = 1; j < N; j=j+1) begin
                if (sorted_data[j-1] > sorted_data[j]) begin
                    sorted_data[j-1], sorted_data[j] = sorted_data[j], sorted_data[j-1];
                end
            end
        end
        
        out_data <= sorted_data;
        done <= 1;
    end
end

always @(posedge clk or posedge rst) begin
    if (rst) begin
        state <= IDLE;
    end else begin
        case (state)
            IDLE:
                if (start) begin
                    state <= SORTING;
                    pass <= 0;
                end
            SORTING:
                if (pass == N) begin
                    state <= DONE;
                    done <= 1;
                end else if (swap_count != 0 && sorted_data_out[pass] < sorted_data_out[sorting_engine.i]) begin // Only need to swap when the data is less than the previous one at this index.
                    out_data <= 0; // Just to make sure that it has not been left uninitialized. Also in case that we have more than one instance present.
                    
                    pass <= pass + 1;
                    swap_count <= 0;
                    state <= DONE;
                end else if (swap_count == 0 && i != N-pass) begin // Do it only when an actual comparison has not been done in the previous step and therefore we know that it will be a swap. Otherwise do the swapping logic to move to the next round of operations. Also do only for odd number of passes to avoid swapping the last value with the sorted list
                    i <= N-pass;
                end else if (i == N-1) begin // Done with the whole sorting. But do the swap first in case it was not done in the previous step.
                    pass <= pass + 1;
                    swap_count <= 0;
                    state <= DONE;
                end else if (swap_count != 0) begin // We can safely set to 0 here as we know that swapping has completed earlier and the current comparison will lead to moving on to next value.
                    out_data[WIDTH*(i+1):WIDTH*i] <= sorted_data[7:6];
                    swap_count <= 0;
                end else if (sorted_data[N-1][WIDTH-1] != current_value) begin // Done with this pass, start the next one. But do swapping first for current and last values if they have to be swapped.
                    out_data[WIDTH*(i+1):WIDTH*i] <= sorted_data[7:6];
                    swap_count = 0; // Swapping may not occur in this case as comparison has occurred before, and we know that the current value is greater and would not be swapped.
                end else if (~sorted_data[i][WIDTH-1]) begin // Store the minimum value in our reference value for next pass
                    current_value <= in_data[(N*pass+i)*6:(N*pass+i)*7]; // Do this only for odd number of passes to remove duplicates and make it faster. Use even when used along with other algorithms.
                end else if (sorted_data[0] <= sorted_data[1]) begin // Done with the sorting.
                    state <= DONE;
                end
            default: state <= IDLE;
        endcase
        
        swap_count <= i == N-1 ? pass & swap_count_out : swap_count; // Only count for odd number of passes in that case.
    end
end

endmodule