// 8 x 8-bit register file: one synchronous write port, two asynchronous read ports.
module regfile8x8 (
    input  wire       clk,
    input  wire       we,
    input  wire [2:0] waddr,
    input  wire [7:0] wdata,
    input  wire [2:0] raddr_a,
    input  wire [2:0] raddr_b,
    output wire [7:0] rdata_a,
    output wire [7:0] rdata_b
);
reg [7:0] mem [0:7];

always @(posedge clk)
    if (we) mem[waddr] <= wdata;

assign rdata_a = mem[raddr_a];
assign rdata_b = mem[raddr_b];
endmodule
