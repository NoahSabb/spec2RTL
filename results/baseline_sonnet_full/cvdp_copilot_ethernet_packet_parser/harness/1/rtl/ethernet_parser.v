module ethernet_parser (
    input  wire        clk,
    input  wire        rst,
    input  wire        vld,
    input  wire        sof,
    input  wire [31:0] data,
    input  wire        eof,
    output wire        ack,
    output reg  [15:0] field,
    output reg         field_vld
);

    // State encoding
    localparam IDLE       = 2'd0;
    localparam EXTRACTING = 2'd1;
    localparam DONE       = 2'd2;
    localparam FAIL_FINAL = 2'd3;

    reg [1:0]  state;
    reg [3:0]  beat_cnt;
    reg [15:0] temp_extracted_field;

    // ACK is always high
    assign ack = 1'b1;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state                <= IDLE;
            beat_cnt             <= 4'd0;
            field                <= 16'd0;
            field_vld            <= 1'b0;
            temp_extracted_field <= 16'd0;
        end else begin
            case (state)
                IDLE: begin
                    field_vld <= 1'b0;
                    field     <= 16'd0;
                    beat_cnt  <= 4'd0;
                    if (vld && sof) begin
                        beat_cnt <= 4'd1;
                        state    <= EXTRACTING;
                    end
                end

                EXTRACTING: begin
                    if (vld) begin
                        if (beat_cnt == 4'd1) begin
                            temp_extracted_field <= data[31:16];
                            beat_cnt             <= beat_cnt + 1'b1;
                            state                <= DONE;
                        end else begin
                            beat_cnt <= beat_cnt + 1'b1;
                        end
                    end
                    if (eof) begin
                        state <= IDLE;
                    end
                end

                DONE: begin
                    field     <= temp_extracted_field;
                    field_vld <= 1'b1;
                    if (vld) begin
                        beat_cnt <= beat_cnt + 1'b1;
                    end
                    if (eof) begin
                        state <= FAIL_FINAL;
                    end
                end

                FAIL_FINAL: begin
                    field_vld <= 1'b0;
                    state     <= IDLE;
                end

                default: begin
                    state <= IDLE;
                end
            endcase
        end
    end

endmodule
