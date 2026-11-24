// Level-sensitive latches, transparent while en is high and while en is low.
module latches (
    input  wire       en,
    input  wire [3:0] d,
    output reg  [3:0] q_hi,
    output reg  [3:0] q_lo
);
always @*
    if (en) q_hi = d;

always @*
    if (!en) q_lo = d;
endmodule
