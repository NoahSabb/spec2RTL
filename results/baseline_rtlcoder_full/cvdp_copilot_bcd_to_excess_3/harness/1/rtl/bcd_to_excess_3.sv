module bcd_to_excess_3(input [3:0] bcd, output reg [3:0] excess3, output reg error);
  
  always @ (*) begin
    case (bcd)
      4'd0: begin
        excess3 = 4'b0011;
        error = 1'b0;
      end
      4'd1: begin
        excess3 = 4'b0100;
        error = 1'b0;
      end
      4'd2: begin
        excess3 = 4'b0101;
        error = 1'b0;
      end
      4'd3: begin
        excess3 = 4'b0110;
        error = 1'b0;
      end
      4'd4: begin
        excess3 = 4'b0111;
        error = 1'b0;
      end
      4'd5: begin
        excess3 = 4'b1000;
        error = 1'b0;
      end
      4'd6: begin
        excess3 = 4'b1001;
        error = 1'b0;
      end
      4'd7: begin
        excess3 = 4'b1010;
        error = 1'b0;
      end
      4'd8: begin
        excess3 = 4'b1011;
        error = 1'b0;
      end
      4'd9: begin
        excess3 = 4'b1100;
        error = 1'b0;
      end
      default: begin
        excess3 = 4'b0000;
        error = 1'b1;
      end
    endcase
  end
endmodule