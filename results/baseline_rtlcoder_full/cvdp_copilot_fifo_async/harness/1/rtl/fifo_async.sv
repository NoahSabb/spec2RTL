module fifo_async(
  input wire w_clk,
  input wire w_rst,
  input wire w_inc,
  input wire [DATA_WIDTH-1:0] w_data,
  output reg w_full,
  input wire r_clk,
  input wire r_rst,
  input wire r_inc,
  output reg r_empty,
  output reg [ DATA_WIDTH-1 : 0 ] r_data
);

parameter DEPTH = 4;

reg [$clog2(DEPTH)-1:0] write_ptr = 1;
reg [$clog2(DEPTH)-1:0] read_ptr = 1;
reg full_reg, empty_reg, wg_rst;
wire is_empty = (write_ptr == read_ptr);
wire is_full = ((write_ptr & ~read_ptr[DATA_WIDTH-2:0]) |
                (~write_ptr[DATA_WIDTH-1] & read_ptr));
wire wg_sync;
wire rg_sync;

// Write Gray counter
always @(posedge w_clk or posedge w_rst) begin
  if (w_rst) begin
    write_ptr <= 1;
  end else if (w_inc & ~wg_rst && ~wg_sync) begin
    write_ptr <= write_ptr ^ {write_ptr[DATA_WIDTH-2:0], w_full};
  end
end

always @(negedge w_clk or posedge w_rst) begin
  if (w_rst) begin
    wg_rst <= 1'b0;
  end else if (~wg_sync & r_inc) begin
    wg_rst <= 1'b1;
  end
end

always @(negedge r_clk or posedge read_ptr[DATA_WIDTH-2:0]) begin
  if (r_full & ~wg_sync) begin
    full_reg <= wg_rst;
  end else begin
    full_reg <= is_full;
  end
end

// Read Gray counter
always @(posedge r_clk or posedge r_rst) begin
  if (r_rst) begin
    read_ptr <= {DEPTH{1'b0}};
  end else if (r_inc & full_reg) begin
    read_ptr <= read_ptr ^ {1'b0, read_ptr[DATA_WIDTH-1:1]};
  end
end

always @(negedge r_clk or posedge read_ptr > wk_cnt) begin
  if (r_full | ((read_ptr & ~wk_cnt) != {(DEPTH){1'b0}})) begin
    empty_reg <= 1'b1;
  end else begin
    empty_reg <= is_empty;
  end
end

assign rg_sync = (read_ptr >= write_ptr);
assign wk_cnt = {DEPTH-1{1'b0}} - read_ptr + write_ptr[DATA_WIDTH-2:0];
assign r_data = rg_sync ? read_ptr[DATA_WIDTH - 1:0] : w_full;
always @(negedge r_clk or posedge empty_reg) begin
  r_empty <= ~empty_reg;
end

always @(negedge r_clk or posedge full_reg) begin
  full_reg <= 1'b0;
end

initial wg_rst = 1'b0;
initial rg_sync = 1'b0;
initial empty_reg = 1'b1;
initial write_ptr[0] = 1'b0;
initial read_ptr[0] = 1'b0;
initial full_reg = 1'b0;
initial r_empty = 1'b0;
endmodule