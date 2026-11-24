// Two parameterized adder halves chained by carry, with a registered result.
// Exercises multi-file filelists, parameters, generate blocks and flattening.
module hier_generate #(
    parameter W = 12
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output reg  [W:0]   sum_q
);
localparam H = W / 2;
wire [H-1:0] s_lo, s_hi;
wire         c_lo, c_hi;

rca #(.W(H)) u_lo (.a(a[H-1:0]), .b(b[H-1:0]), .ci(1'b0), .s(s_lo), .co(c_lo));
rca #(.W(W - H)) u_hi (.a(a[W-1:H]), .b(b[W-1:H]), .ci(c_lo), .s(s_hi), .co(c_hi));

always @(posedge clk or negedge rst_n)
    if (!rst_n) sum_q <= {(W + 1){1'b0}};
    else sum_q <= {c_hi, s_hi, s_lo};
endmodule
