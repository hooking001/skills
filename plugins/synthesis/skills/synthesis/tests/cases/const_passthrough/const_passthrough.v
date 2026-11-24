// Feed-through and constant outputs next to a little logic; one input is unused.
module const_passthrough (
    input  wire [3:0] a,
    input  wire       unused,
    output wire [3:0] y_pass,
    output wire       y_and,
    output wire       one,
    output wire       zero,
    output wire [1:0] pattern
);
assign y_pass  = a;
assign y_and   = &a;
assign one     = 1'b1;
assign zero    = 1'b0;
assign pattern = 2'b10;
endmodule
