`timescale 1ns/1ps
module const_passthrough_tb;
    reg  [3:0] a = 0;
    reg        unused = 0;
    wire [3:0] y_pass;
    wire       y_and, one, zero;
    wire [1:0] pattern;
    integer i;
    const_passthrough uut (.a(a), .unused(unused), .y_pass(y_pass), .y_and(y_and),
                           .one(one), .zero(zero), .pattern(pattern));
    initial begin
        for (i = 0; i < 32; i = i + 1) begin
            {unused, a} = i;
            #1;
            if (y_pass !== a || y_and !== (a == 4'hf) || one !== 1'b1 || zero !== 1'b0 ||
                pattern !== 2'b10)
                $fatal(1, "a=%h: got %h %b %b %b %b", a, y_pass, y_and, one, zero, pattern);
        end
        $display("PASS: const_passthrough 32 vectors");
        $finish;
    end
endmodule
