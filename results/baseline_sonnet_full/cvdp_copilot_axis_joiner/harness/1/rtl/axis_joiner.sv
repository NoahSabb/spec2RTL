module axis_joiner (
    input  logic        clk,
    input  logic        rst,

    // AXI Stream Input 1
    input  logic [7:0]  s_axis_tdata_1,
    input  logic        s_axis_tvalid_1,
    output logic        s_axis_tready_1,
    input  logic        s_axis_tlast_1,

    // AXI Stream Input 2
    input  logic [7:0]  s_axis_tdata_2,
    input  logic        s_axis_tvalid_2,
    output logic        s_axis_tready_2,
    input  logic        s_axis_tlast_2,

    // AXI Stream Input 3
    input  logic [7:0]  s_axis_tdata_3,
    input  logic        s_axis_tvalid_3,
    output logic        s_axis_tready_3,
    input  logic        s_axis_tlast_3,

    // AXI Stream Output
    output logic [7:0]  m_axis_tdata,
    output logic        m_axis_tvalid,
    input  logic        m_axis_tready,
    output logic        m_axis_tlast,
    output logic [1:0]  m_axis_tuser,

    // Status
    output logic        busy
);

    // FSM States
    typedef enum logic [1:0] {
        STATE_IDLE = 2'b00,
        STATE_1    = 2'b01,
        STATE_2    = 2'b10,
        STATE_3    = 2'b11
    } state_t;

    // TAG IDs
    localparam logic [1:0] TAG_ID_1 = 2'h1;
    localparam logic [1:0] TAG_ID_2 = 2'h2;
    localparam logic [1:0] TAG_ID_3 = 2'h3;

    state_t current_state, next_state;

    // Internal registers for buffering
    logic [7:0] temp_data;
    logic        temp_valid;
    logic        temp_last;
    logic [1:0]  temp_user;
    logic        temp_flag;

    // MUX signals
    logic [7:0]  mux_tdata;
    logic        mux_tvalid;
    logic        mux_tlast;
    logic [1:0]  mux_tuser;

    // FSM Sequential Logic
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            current_state <= STATE_IDLE;
        end else begin
            current_state <= next_state;
        end
    end

    // FSM Next State Logic
    always_comb begin
        next_state = current_state;
        case (current_state)
            STATE_IDLE: begin
                if (s_axis_tvalid_1)
                    next_state = STATE_1;
                else if (s_axis_tvalid_2)
                    next_state = STATE_2;
                else if (s_axis_tvalid_3)
                    next_state = STATE_3;
                else
                    next_state = STATE_IDLE;
            end
            STATE_1: begin
                // Stay in STATE_1 until tlast is transferred
                if (s_axis_tvalid_1 && s_axis_tlast_1 && (m_axis_tready || !temp_flag))
                    next_state = STATE_IDLE;
                else if (temp_flag && temp_last && m_axis_tready)
                    next_state = STATE_IDLE;
            end
            STATE_2: begin
                if (s_axis_tvalid_2 && s_axis_tlast_2 && (m_axis_tready || !temp_flag))
                    next_state = STATE_IDLE;
                else if (temp_flag && temp_last && m_axis_tready)
                    next_state = STATE_IDLE;
            end
            STATE_3: begin
                if (s_axis_tvalid_3 && s_axis_tlast_3 && (m_axis_tready || !temp_flag))
                    next_state = STATE_IDLE;
                else if (temp_flag && temp_last && m_axis_tready)
                    next_state = STATE_IDLE;
            end
            default: next_state = STATE_IDLE;
        endcase
    end

    // MUX: Select input based on current state
    always_comb begin
        case (current_state)
            STATE_1: begin
                mux_tdata  = s_axis_tdata_1;
                mux_tvalid = s_axis_tvalid_1;
                mux_tlast  = s_axis_tlast_1;
                mux_tuser  = TAG_ID_1;
            end
            STATE_2: begin
                mux_tdata  = s_axis_tdata_2;
                mux_tvalid = s_axis_tvalid_2;
                mux_tlast  = s_axis_tlast_2;
                mux_tuser  = TAG_ID_2;
            end
            STATE_3: begin
                mux_tdata  = s_axis_tdata_3;
                mux_tvalid = s_axis_tvalid_3;
                mux_tlast  = s_axis_tlast_3;
                mux_tuser  = TAG_ID_3;
            end
            default: begin
                mux_tdata  = 8'h00;
                mux_tvalid = 1'b0;
                mux_tlast  = 1'b0;
                mux_tuser  = 2'h0;
            end
        endcase
    end

    // Buffering Logic and Output Assignment
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            temp_data  <= 8'h00;
            temp_valid <= 1'b0;
            temp_last  <= 1'b0;
            temp_user  <= 2'h0;
            temp_flag  <= 1'b0;
        end else begin
            if (temp_flag) begin
                // We have buffered data waiting to be sent
                if (m_axis_tready) begin
                    // Buffered data has been consumed
                    temp_flag  <= 1'b0;
                    temp_valid <= 1'b0;
                end
            end else begin
                // No buffered data
                if (mux_tvalid && !m_axis_tready && current_state != STATE_IDLE) begin
                    // Need to buffer the data since downstream is not ready
                    temp_data  <= mux_tdata;
                    temp_valid <= mux_tvalid;
                    temp_last  <= mux_tlast;
                    temp_user  <= mux_tuser;
                    temp_flag  <= 1'b1;
                end
            end
        end
    end

    // Output assignments
    always_comb begin
        if (temp_flag) begin
            m_axis_tdata  = temp_data;
            m_axis_tvalid = temp_valid;
            m_axis_tlast  = temp_last;
            m_axis_tuser  = temp_user;
        end else begin
            m_axis_tdata  = mux_tdata;
            m_axis_tvalid = mux_tvalid;
            m_axis_tlast  = mux_tlast;
            m_axis_tuser  = mux_tuser;
        end
    end

    // Ready signal assignments
    // Only assert ready for the active stream when downstream is ready and no temp data pending
    always_comb begin
        s_axis_tready_1 = 1'b0;
        s_axis_tready_2 = 1'b0;
        s_axis_tready_3 = 1'b0;

        case (current_state)
            STATE_1: begin
                s_axis_tready_1 = m_axis_tready && !temp_flag;
            end
            STATE_2: begin
                s_axis_tready_2 = m_axis_tready && !temp_flag;
            end
            STATE_3: begin
                s_axis_tready_3 = m_axis_tready && !temp_flag;
            end
            default: begin
                s_axis_tready_1 = 1'b0;
                s_axis_tready_2 = 1'b0;
                s_axis_tready_3 = 1'b0;
            end
        endcase
    end

    // Busy signal
    assign busy = (current_state != STATE_IDLE);

endmodule
