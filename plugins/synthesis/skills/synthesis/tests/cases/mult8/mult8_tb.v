`timescale 1ns/1ps
// Exhaustive check of all 65536 operand pairs.
module mult8_tb;
    reg  [7:0]  a, b;
    wire [15:0] p_unsigned, p_signed;
    integer i, sa, sb, eu, es;
    mult8 uut (.a(a), .b(b), .p_unsigned(p_unsigned), .p_signed(p_signed));
    initial begin
        for (i = 0; i < 65536; i = i + 1) begin
            a = i / 256;
            b = i % 256;
            #1;
            sa = a[7] ? a - 256 : a;
            sb = b[7] ? b - 256 : b;
            eu = a * b;
            es = (sa * sb + 65536) % 65536;
            if (p_unsigned !== eu[15:0] || p_signed !== es[15:0])
                $fatal(1, "a=%0d b=%0d: got %0d/%0d, expected %0d/%0d",
                       a, b, p_unsigned, p_signed, eu, es);
        end
        $display("PASS: mult8 all 65536 operand pairs");
        $finish;
    end
endmodule
