module axis_joiner(
    input clk, rst,
    input [7:0] s_axis_tdata_1,
    input [1:0] s_axis_tuser_1,
    input s_axis_tvalid_1,
    output s_axis_tready_1,
    input s_axis_tlast_1,
    input [7:0] s_axis_tdata_2,
    input [1:0] s_axis_tuser_2,
    input s_axis_tvalid_2,
    output s_axis_tready_2,
    input s_axis_tlast_2,
    input [7:0] s_axis_tdata_3,
    input [1:0] s_axis_tuser_3,
    input s_axis_tvalid_3,
    output s_axis_tready_3,
    input s_axis_tlast_3,
    output reg [7:0] m_axis_tdata,
    output reg m_axis_tvalid,
    input m_axis_tready,
    output reg m_axis_tlast,
    output reg [1:0] m_axis_tuser,
    output reg busy
);

// Finite State Machine to control selection of input streams
typedef enum logic [3:0] state_enum {STATE_IDLE = 2'h0, STATE_1 = 2'h1, STATE_2 = 2'h2, STATE_3 = 2'h3} state_t;
reg [3:0] fsm;
always @(posedge clk or negedge rst) begin
    if (~rst)
        fsm <= STATE_IDLE;
    else
        case (fsm)
            STATE_IDLE: begin
                if(s_axis_tvalid_1)
                    fsm <= STATE_1;
                else if(s_axis_tvalid_2 && !s_axis_tvalid_1)
                    fsm <= STATE_2;
                else if(s_axis_tvalid_3 && !s_axis_tvalid_1 && !s_axis_tvalid_2)
                    fsm <= STATE_3;
            end
            default: begin
                if(s_axis_tlast_3)
                    fsm <= STATE_IDLE;
            end
        endcase
end

// Multiplexers to select appropriate input data
wire [7:0] mux_tdata;
wire [1:0] mux_tuser;
assign mux_tdata = (fsm == STATE_1) ? s_axis_tdata_1 : (fsm == STATE_2) ? s_axis_tdata_2 : s_axis_tdata_3;
assign mux_tuser = (fsm == STATE_1) ? s_axis_tuser_1 : (fsm == STATE_2) ? s_axis_tuser_2 : s_axis_tuser_3;

// Mapping of TAG_ID based on input source
assign mux_tuser[1:0] = (fsm == STATE_1) ? 2'b01 : (fsm == STATE_2) ? 2'b10 : 2'b11;

// AXI Socket Interface signals
wire trans_done;
assign s_axis_tready_1 = m_axis_tready & !trans_done;
assign s_axis_tready_2 = m_axis_tready & !s_axis_tlast_3 & !trans_done;
assign s_axis_tready_3 = m_axis_tready & !s_axis_tvalid_1 & !s_axis_tvalid_2 & !s_axis_tvalid_3 & !trans_done;
assign trans_done = (fsm == STATE_IDLE) | s_axis_tlast_3;

// Outputting data buffer on m_axis stall
reg [7:0] temp_data;
reg temp;
always @(posedge clk or negedge rst) begin
    if (~rst)
        temp <= 1'b0;
    else if (!m_axis_tready)
        temp <= 1'b1;
    else if (temp == 1'b1)
        temp <= 1'b0;
end
assign s_axis_tdata_3 = s_axis_tvalid_3 ? mux_tdata : temp_data;
always @(posedge clk or negedge rst)
    if (~rst)
        assign m_axis_tlast = 1'b0;
    else if (m_axis_tready)
        assign m_axis_tlast = s_axis_tlast | trans_done;
    else if (!busy && fsm != STATE_IDLE)
        assign m_axis_tlast = 1'b1;

// Assigning output data and valid signals
assign m_axis_tdata = mux_tdata;
always @(posedge clk or negedge rst) begin
    if (~rst)
        assign m_axis_tvalid = 1'b0;
    else if (m_axis_tready)
        assign m_axis_tvalid = (!m_axis_tlast && fsm == STATE_IDLE);
end
assign m_axis_tuser = mux_tuser;

// Outputting status signal
assign busy = s_axis_tvalid_1 || s_axis_tvalid_2 || s_axis_tvalid_3;

endmodule