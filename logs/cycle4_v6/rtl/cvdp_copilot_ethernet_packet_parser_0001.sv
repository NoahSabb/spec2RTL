module field_extract (
    input wire clk,
    input wire rst,
    input wire vld,
    input wire sof,
    input wire [31:0] data,
    input wire eof,

    output reg ack,
    output reg [15:0] field,
    output reg field_vld
);

    // State definitions
    localparam IDLE = 2'b00;
    localparam EXTRACTING = 2'b01;
    localparam DONE = 2'b10;
    localparam FAIL_FINAL = 2'b11;

    // State register
    reg [1:0] state, next_state;

    // Beat counter
    reg [3:0] beat_cnt;

    // Temporary storage for extracted field
    reg [15:0] temp_extracted_field;

    // State transition logic
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state <= IDLE;
            beat_cnt <= 4'b0;
            field <= 16'b0;
            field_vld <= 1'b0;
        end else begin
            state <= next_state;
            case (next_state)
                IDLE: begin
                    beat_cnt <= 4'b0;
                    field <= 16'b0;
                    field_vld <= 1'b0;
                end
                EXTRACTING: begin
                    if (vld)
                        beat_cnt <= beat_cnt + 1;
                end
                DONE: begin
                    // Hold the field value and field_vld
                end
                FAIL_FINAL: begin
                    field_vld <= 1'b0;
                end
            endcase
        end
    end

    // Next state logic
    always @(*) begin
        next_state = state;
        case (state)
            IDLE: begin
                if (vld && sof)
                    next_state = EXTRACTING;
            end
            EXTRACTING: begin
                if (vld && beat_cnt == 4'd1) begin
                    next_state = DONE;
                end else if (eof) begin
                    next_state = FAIL_FINAL;
                end
            end
            DONE: begin
                if (eof)
                    next_state = FAIL_FINAL;
            end
            FAIL_FINAL: begin
                next_state = IDLE;
            end
        endcase
    end

    // Output assignments
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            ack <= 1'b1;
            temp_extracted_field <= 16'b0;
        end else begin
            ack <= 1'b1; // Always acknowledge
            case (state)
                EXTRACTING: begin
                    if (vld && beat_cnt == 4'd1) begin
                        temp_extracted_field <= data[31:16];
                        field <= data[31:16];
                        field_vld <= 1'b1;
                    end
                end
                DONE: begin
                    field <= temp_extracted_field;
                    field_vld <= 1'b1;
                end
                FAIL_FINAL: begin
                    field_vld <= 1'b0;
                end
            endcase
        end
    end

endmodule
