// Full-adder cell and a parameterized ripple-carry adder built with generate.
module fa_cell (
    input  wire a,
    input  wire b,
    input  wire ci,
    output wire s,
    output wire co
);
assign s  = a ^ b ^ ci;
assign co = (a & b) | (ci & (a ^ b));
endmodule

module rca #(
    parameter W = 4
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         ci,
    output wire [W-1:0] s,
    output wire         co
);
wire [W:0] c;
assign c[0] = ci;
genvar i;
generate
    for (i = 0; i < W; i = i + 1) begin : g_bit
        fa_cell u_fa (.a(a[i]), .b(b[i]), .ci(c[i]), .s(s[i]), .co(c[i+1]));
    end
endgenerate
assign co = c[W];
endmodule
