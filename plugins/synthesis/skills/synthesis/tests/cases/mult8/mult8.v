// 8x8 multipliers: unsigned and signed products from the same operands.
module mult8 (
    input  wire [7:0]  a,
    input  wire [7:0]  b,
    output wire [15:0] p_unsigned,
    output wire [15:0] p_signed
);
assign p_unsigned = a * b;
assign p_signed   = $signed(a) * $signed(b);
endmodule
