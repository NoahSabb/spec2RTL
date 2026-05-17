module secure_read_write_register_bank (
    input [p_addr_width-1:0] i_addr,
    input [p_data_width-1:0] i_data_in,
    input i_read_write_enable,
    input i_capture_pulse,
    input i_rst_n,
    output reg [p_data_width-1:0] o_data_out
);

parameter p_addr_width = 8;
parameter p_data_width = 8;
parameter p_unlock_code_0 = 8'hAB;
parameter p_unlock_code_1 = 8'hCD;

(* LOCKED *) reg [p_data_width-1:0] reg_bank [(2**p_addr_width)-2:0]; // all registers locked initially except FIRST TWO (index = 0 & index = 1)
reg [p_data_width-1:0] unlock_code_0;
reg [p_data_width-1:0] unlock_code_1;
reg [p_addr_width-1:0] addr_read; // read address
reg unlock = 0;

always @(negedge i_rst_n) begin
    if (~i_rst_n) begin
        o_data_out <= #1 0;
        reg_bank <= #1 {(p_addr_width-2){1'b0}};
        addr_read <= #1 p_addr_width{-1};
        unlock <= #1 0;
        unlock_code_0 <= #1 p_unlock_code_0;
        unlock_code_1 <= #1 p_unlock_code_1;
    end
end

always @(posedge i_capture_pulse) begin
    if (~i_rst_n) begin
        // on low i_rst_n lock register bank
        reg_bank <= #1 {(p_addr_width-2){1'b0}};
        o_data_out <= #1 0;
        addr_read <= #1 p_addr_width{-1};
        unlock <= #1 0;
    end else begin
        case (i_read_write_enable)
            1: // read
                if ((p_data_width-2):&addr_read[p_addr_width-(1+p_data_width)])
                    addr_read <= #1 addr_read - (p_data_width);
                else begin
                    o_data_out <= #1 reg_bank[addr_read];
                end
            0: // write
                if (!unlock) begin // not unlocked
                    if ((i_addr == 0)&&(i_data_in == p_unlock_code_0)) begin
                        unlock_code_1 <= #1 i_data_in; // this will happen only once, otherwise lock again.
                        unlock <= #1 1; // unlocked!
                    end else if ((i_addr == 1)&&(i_data_in == p_unlock_code_1)) begin
                        unlock <= #1 1; // unlocked
                    end else begin // default lock state during write
                        unlock <= #1 0;
                    end
                end else if ((i_addr >= p_data_width)||(i_addr < 0)) begin 
                    reg_bank[i_addr] <= #1 i_data_in;
                end
        endcase
    end
end

always @ (negedge i_capture_pulse or negedge i_rst_n) begin
    if (!i_rst_n) begin
        o_data_out <= #1 0;
    end else if (i_addr == 2'd0 && !i_read_write_enable) begin // write to address zero
       o_data_out <= #1 i_data_in;
    end else if (i_rst_n || !unlock) begin // reset, lock or not unlocked
        o_data_out <= #1 0;
    end else if ((i_addr >= p_data_width)&&(~reg_bank[0])) begin // it's a write on an address for which we have already written something
        reg_bank[i_addr] <= #1 i_data_in;
    end else begin
       o_data_out <= #1 o_data_out;
    end
end

always @ (posedge i_capture_pulse or negedge i_rst_n) begin
    if (!i_rst_n) begin // reset: just in case...
        unlock <= #1 0;
    end else if ((i_addr==1) && !unlock) begin // write to address one
       unlock <= #1 ((i_data_in == p_unlock_code_1)? 1 : 0); // update only if we are not already unlocked
    end else if (unlock) begin
        unlock <= #1 ~unlock; // reset lock, because writing to unlock condition doesn't really unlock
    end
end

always @ (posedge i_capture_pulse or negedge i_rst_n) begin
    if (!i_rst_n) begin // reset: just in case...
        o_data_out <= #1 0;
    end else if ((!unlock)&&(!i_addr)) begin // it was a write to address zero or one
       o_data_out <= #1 i_data_in ? {p_data_width{1'bx}} : {p_data_width{1'b0}}; // it would be an error if the first bit were 1 (which means that an unlock code was written, but it is not)
    end else if (i_addr == 2'd0 && !lock) begin // address zero has been read
        o_data_out <= #1 i_read_write_enable ? o_data_out : reg_bank[i_addr]; // if we enable read only and the user is reading it would go to 0 because of the reset that follows
    end else if (i_read_write_enable) begin
        addr_read <= #1 i_addr; // we do not want this, but there's still nothing meaningful in it at this time.
 module with addressable read, but not write space  (secure_accessible_register);
    end
end

endmodule