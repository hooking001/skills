// 8-bit ALU: arithmetic with carry/borrow, logic, shifts and signed compare.
module alu8 (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire [2:0] op,
    output reg  [7:0] y,
    output reg        carry,
    output wire       zero
);
always @* begin
    carry = 1'b0;
    case (op)
        3'd0: {carry, y} = {1'b0, a} + {1'b0, b};
        3'd1: {carry, y} = {1'b0, a} - {1'b0, b};
        3'd2: y = a & b;
        3'd3: y = a | b;
        3'd4: y = a ^ b;
        3'd5: y = a << b[2:0];
        3'd6: y = a >> b[2:0];
        default: y = ($signed(a) < $signed(b)) ? 8'd1 : 8'd0;
    endcase
end
assign zero = (y == 8'd0);
endmodule
