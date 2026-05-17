module FILO_RTL #(
    parameter DATA_WIDTH = 8,
    parameter FILO_DEPTH = 16
)(
    input  logic                    clk,
    input  logic                    reset,
    input  logic                    push,
    input  logic                    pop,
    input  logic [DATA_WIDTH-1:0]   data_in,
    output logic [DATA_WIDTH-1:0]   data_out,
    output logic                    full,
    output logic                    empty
);

    // Internal memory array
    logic [DATA_WIDTH-1:0] mem [0:FILO_DEPTH-1];
    
    // Stack pointer - points to the next empty location
    logic [$clog2(FILO_DEPTH):0] top;
    
    // Feedthrough register
    logic [DATA_WIDTH-1:0] feedthrough_data;
    logic                  feedthrough_valid;

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            top              <= 0;
            full             <= 1'b0;
            empty            <= 1'b1;
            feedthrough_valid <= 1'b0;
            feedthrough_data  <= '0;
        end else begin
            feedthrough_valid <= 1'b0;
            
            // Feedthrough: FILO is empty and both push and pop asserted
            if (empty && push && pop) begin
                feedthrough_data  <= data_in;
                feedthrough_valid <= 1'b1;
                // top remains 0, empty remains 1, full remains 0
            end
            // Push only (not full)
            else if (push && !pop && !full) begin
                mem[top] <= data_in;
                top      <= top + 1;
                empty    <= 1'b0;
                if (top + 1 == FILO_DEPTH) begin
                    full <= 1'b1;
                end
            end
            // Pop only (not empty)
            else if (pop && !push && !empty) begin
                top  <= top - 1;
                full <= 1'b0;
                if (top - 1 == 0) begin
                    empty <= 1'b1;
                end
            end
            // Push and pop simultaneously, buffer not empty
            else if (push && pop && !empty) begin
                // Pop the top element and push new data at same position
                // Net effect: replace top element, top doesn't change
                // Actually: pop decrements top, push increments - net 0
                // But we store new data at current top-1 position? 
                // Let's think: pop first then push
                // pop: top goes to top-1, then push: store at top-1, top goes back to top
                // Net: replace top-1 element with new data, top unchanged
                mem[top-1] <= data_in;
                // top stays the same
                // full and empty stay the same
            end
        end
    end

    // Output logic
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            data_out <= '0;
        end else begin
            if (empty && push && pop) begin
                // feedthrough - will be captured next cycle or we handle combinatorially
                data_out <= data_in;
            end else if (pop && !push && !empty) begin
                data_out <= mem[top-1];
            end else if (push && pop && !empty) begin
                // Simultaneous push/pop when not empty: output the current top
                data_out <= mem[top-1];
            end
        end
    end

endmodule
