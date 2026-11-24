`timescale 1ns/1ps
module hier_generate_tb;
    reg         clk = 0, rst_n = 1;
    reg  [11:0] a = 0, b = 0;
    wire [12:0] sum_q;
    reg  [12:0] expected;
    integer i, seed;
    hier_generate uut (.clk(clk), .rst_n(rst_n), .a(a), .b(b), .sum_q(sum_q));
    always #5 clk = ~clk;
    initial begin
        seed = 21;
        #1 rst_n = 0;
        #1 if (sum_q !== 13'd0) $fatal(1, "reset failed: %h", sum_q);
        rst_n = 1;
        for (i = 0; i < 1000; i = i + 1) begin
            @(negedge clk);
            case (i)
                0: begin a = 12'hfff; b = 12'h001; end
                1: begin a = 12'hfff; b = 12'hfff; end
                2: begin a = 12'h03f; b = 12'h001; end
                default: begin a = $random(seed); b = $random(seed); end
            endcase
            expected = a + b;
            @(posedge clk); #1;
            if (sum_q !== expected) $fatal(1, "%0d + %0d: got %0d", a, b, sum_q);
        end
        $display("PASS: hier_generate 1000 registered sums");
        $finish;
    end
endmodule
