module perf_counter #(
    parameter CNT_W = 8
) (
    input  wire             clk,
    input  wire             reset,
    input  wire             sw_req_i,
    input  wire             cpu_trig_i,
    output wire [CNT_W-1:0] p_count_o
);

    reg [CNT_W-1:0] count_q;
    reg [CNT_W-1:0] count_snap_q;

    // Counter logic
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            count_q <= {CNT_W{1'b0}};
        end else begin
            if (sw_req_i) begin
                // Reset after read; if trigger also active, start from 1
                if (cpu_trig_i) begin
                    count_q <= {{(CNT_W-1){1'b0}}, 1'b1};
                end else begin
                    count_q <= {CNT_W{1'b0}};
                end
            end else if (cpu_trig_i) begin
                count_q <= count_q + 1'b1;
            end
        end
    end

    // Snapshot register for output
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            count_snap_q <= {CNT_W{1'b0}};
        end else begin
            if (sw_req_i) begin
                count_snap_q <= count_q + {{(CNT_W-1){1'b0}}, cpu_trig_i};
            end else begin
                count_snap_q <= {CNT_W{1'b0}};
            end
        end
    end

    // Output driven by snapshot register
    assign p_count_o = count_snap_q;

endmodule
