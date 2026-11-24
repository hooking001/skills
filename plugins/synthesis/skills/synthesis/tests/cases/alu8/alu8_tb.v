`timescale 1ns/1ps
// Integer reference model, written independently of the RTL operators.
module alu8_tb;
    reg  [7:0] a, b;
    reg  [2:0] op;
    wire [7:0] y;
    wire       carry, zero;
    integer i, o, ia, ib, sa, sb, r, seed, checks;
    reg  [7:0] ey;
    reg        ec;
    alu8 uut (.a(a), .b(b), .op(op), .y(y), .carry(carry), .zero(zero));
    task check;
        begin
            #1;
            ia = a; ib = b; ec = 1'b0;
            sa = a[7] ? ia - 256 : ia;
            sb = b[7] ? ib - 256 : ib;
            case (op)
                3'd0: begin r = ia + ib; ey = r % 256; ec = r > 255; end
                3'd1: begin r = ia - ib + 256; ey = r % 256; ec = ia < ib; end
                3'd2: ey = a & b;
                3'd3: ey = a | b;
                3'd4: ey = a ^ b;
                3'd5: ey = (ia * (1 << (ib % 8))) % 256;
                3'd6: ey = ia / (1 << (ib % 8));
                default: ey = (sa < sb) ? 8'd1 : 8'd0;
            endcase
            if (y !== ey || carry !== ec || zero !== (ey == 0))
                $fatal(1, "op=%0d a=%0d b=%0d: got y=%0d c=%b z=%b, expected y=%0d c=%b",
                       op, a, b, y, carry, zero, ey, ec);
            checks = checks + 1;
        end
    endtask
    initial begin
        seed = 7; checks = 0;
        for (o = 0; o < 8; o = o + 1) begin
            op = o;
            a = 8'h00; b = 8'h00; check;
            a = 8'hff; b = 8'hff; check;
            a = 8'h80; b = 8'h7f; check;
            a = 8'h7f; b = 8'h80; check;
            for (i = 0; i < 400; i = i + 1) begin
                a = $random(seed);
                b = $random(seed);
                check;
            end
        end
        $display("PASS: alu8 %0d vectors", checks);
        $finish;
    end
endmodule
