module ethernet_parser(
    input clk,
    input rst,
    input vld,
    input sof,
    input [31:0] data,
    output ack,
    output reg [15:0] field,
    output reg field_vld,
    output reg [4:0] beat_cnt
);

// Beat counter
reg [4:0] beat_cnt;
always @(posedge clk) begin
    if (rst) begin
        beat_cnt <= 0;
        field_vld <= 0;
    end else if (sof) begin // Start of new frame detected, reset counters and prepare extraction
        beat_cnt <= 0;
        field_vld <= 0;
    end else if (vld) begin
        beat_cnt <= beat_cnt + 1;
    end
end

// Temporary storage
reg [15:0] temp_extracted_field;
always @(posedge clk) begin
    if (rst) begin
        temp_extracted_field <= 0;
    end else if (sof && vld && beat_cnt == 1) begin // 2nd beat of the burst, capture most significant bytes
        temp_extracted_field <= data[31:16];
    end
end

// State machine
reg [1:0] state;
parameter IDLE = 2'd0;
parameter EXTRACTING = 2'd1;
parameter DONE = 2'd2;
parameter FAIL_FINAL = 2'd3;
always @(posedge clk) begin
    if (rst) begin
        state <= IDLE;
        field <= 0;
        beat_cnt <= 0;
    end else if (sof) begin // Start of new frame detected, reset counters and prepare extraction
        state <= IDLE;
        field <= 0;
        beat_cnt <= 0;
        field_vld <= 0;
    end else if (state == IDLE && vld) begin
        state <= EXTRACTING;
    end else if (state == EXTRACTING && vld) begin
        beat_cnt <= beat_cnt + 1;
        if (beat_cnt == 1) begin // 2nd beat of the burst, capture most significant bytes
            temp_extracted_field <= data[31:16];
            state <= DONE;
        end else if (eof) begin // End of burst detected, reset state and wait for next burst
            state <= FAIL_FINAL;
        end
    end else if (state == FAIL_FINAL && eof) begin
        field_vld <= 0;
        beat_cnt <= 0;
        state <= IDLE;
    end else if (state != DONE) begin // For all states expect Done, output is cleared
        temp_extracted_field <= 0;
    end
end

// Assignments
assign ack = 1'b1;
always @(posedge clk) begin
    if (rst) begin
        field <= 0;
    end else if (state == DONE & ~eof) begin
        field <= temp_extracted_field;
        field_vld <= 1'b1;
    end else if (eof && state != FAIL_FINAL) begin
        field_vld <= 0;
    end
end

endmodule