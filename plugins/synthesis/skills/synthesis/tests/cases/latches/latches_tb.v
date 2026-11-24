`timescale 1ns/1ps
// en and d never change in the same time step after start-up. They start
// unknown and are set at #1, because time-zero initial values would not
// trigger the RTL always @* blocks.
module latches_tb;
    reg        en;
    reg  [3:0] d;
    wire [3:0] q_hi, q_lo;
    reg  [3:0] m_hi, m_lo;
    integer i, seed, checks;
    latches uut (.en(en), .d(d), .q_hi(q_hi), .q_lo(q_lo));
    task check;
        begin
            #1;
            if (q_hi !== m_hi || q_lo !== m_lo)
                $fatal(1, "en=%b d=%h: got %h/%h expected %h/%h", en, d, q_hi, q_lo, m_hi, m_lo);
            checks = checks + 1;
        end
    endtask
    initial begin
        seed = 5; checks = 0;
        #1 d = 0; en = 0; m_lo = 0; check;  // q_lo transparent first, q_hi still unknown
        en = 1; #1 d = 4'h9; m_hi = d; check;
        for (i = 0; i < 400; i = i + 1) begin
            if ($random(seed) & 1) begin
                en = ~en;
            end else begin
                d = $random(seed);
            end
            if (en) m_hi = d; else m_lo = d;
            check;
        end
        $display("PASS: latches %0d checks", checks);
        $finish;
    end
endmodule
