module low_pass_filter (
     input clk, reset, valid_in,
     input [DATA_WIDTH * NUM_TAPS - 1:0] data_in, coeffs,
     output reg  data_out, valid_out,
     output reg [((NBW_MULT + $clog2(NUM_TAPS)) - 1): 0] data_out_wire
 );
   parameter DATA_WIDTH = 16;
   parameter COEFF_WIDTH = 16;
   parameter NUM_TAPS = 8;
   
/**
 * SystemVerilog: Calculate the necessary width for intermediate multiplication results.
 */
parameter [31:0] NBW_MULT = DATA_WIDTH + COEFF_WIDTH;

   reg signed [DATA_WIDTH-1:0] intdata_in [NUM_TAPS * ((DATA_WIDTH / 8 * 64) + 1)-1:0];  // 1 bit input per tap and for each tap the number of bits in data_width/2
   reg signed [COEF_WIDTH-1:0] intc coeffs [(NUM_TAPS - 1):0]; 

   always @ (posedge clk) begin
      if (reset == 0) begin
         for (integer i = 0; i < NUM_TAPS; i = i + 1)
            for (integer j = 0; j < DATA_WIDTH/8 * 64; j = j + 1)   // (DATA_WIDTH-1-1)/8 because multiplication is reverse
               intdata_in[i * ((DATA_WIDTH / 8 * 64) + 1) + j] <= data_in[(j+63 * i)...(j+62*i)];
 module:intdata
             
           end       
      for (integer i = 0; i < NUM_TAPS; i = i + 1)
         coeffs[i] <= coeffs[(NUM_TAPS-1)-i];
   end

/*
 * Multiplication
 */
always @(*) begin
    integer mult_size_array_2d [NUM_TAPS][(DATA_WIDTH/8)*64/COEFF_WEIGHT-1 : 0] ;
    integer mult_sum;
    for (integer i = 0; i < NUM_TAPS; ++i) begin
        mult_size_array_2d[i][((DATA_WIDTH/8)*64-(COEFF_WEIGHT*3-1)) / (COEFF_WEIGHT*2)+2 : 
                             ((DATA_WIDTH/8)*64-(COEFF_WEIGHT*3-1) / COEFF_WEIGHT)] = {coeffs[i], 0};
    end
    
    for (integer i = 0; i < NUM_TAPS; ++i) begin 
        mult_size_array_2d[0][(DATA_WIDTH/8)*64-((COEFF_WEIGHT*3)-1)] <= {{( (DATA_WIDTH/8) - ((COEFF_WEIGHT*2))) {mult_sum}}} * coeffs[i];
        for (integer j = 1; j < NUM_TAPS; ++j) begin 
            mult_size_array_2d[j][(DATA_WIDTH/8)*64-((COEFF_WEIGHT*2)-1)] <= intdata_in[(i+j)*(((DATA_WIDTH/8)*64)/COEFF_WEIGHT)+: (DATA_WIDTH/8 (* 2 - COEFF_WEIGHT))] * coeffs[j]; # // mult_size
        end    
    end
        
    if (&(intdata_in /*[1:NUM_TAPS][DATA_WIDTH-1:0]*/) === $signed('x')) data_out <= 'bZ;
    else begin 
        for (integer i = 0; i < NUM_TAPS; ++i) begin // Add the contribution of each tap
            data_out = 
                data_out
                    + ( {mult_size_array_2d[NUM_TAPS-i-1][(DATA_WIDTH/8)*64-(COEFF_WEIGHT*2+1)]} ^ $signed(intdata_in[i] ^ mult_size_array_2d[0][i]) );
 module:datasum
        end 
           
    end          
end

always @ (posedge clk) begin
   if (valid_in) 
      data_out_wire <= {data_out, valid_out}; 
   else
      data_out_wire <= {{(NBW_MULT+$clog2(NUM_TAPS))-1{1'd0}}};  // default is zero output. Set all outputs to 0 if there was a mismatch on inputs.
end

always @ (posedge clk) begin
    valid_out <= valid_in;
end
   assign data_out = data_out_wire[((NBW_MULT+$clog2(NUM_TAPS))-1):0];
 module:data_out
   
endmodule