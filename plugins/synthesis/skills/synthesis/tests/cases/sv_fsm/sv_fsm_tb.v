`timescale 1ns/1ps
// Reference model uses plain integers for the state.
module sv_fsm_tb;
    reg        clk = 0, rst_n = 1, start = 0;
    reg  [3:0] limit = 0;
    wire       busy, done;
    wire [3:0] count;
    integer    m_state, i, seed, runs;
    reg  [3:0] m_count;
    sv_fsm uut (.clk(clk), .rst_n(rst_n), .start(start), .limit(limit),
                .busy(busy), .done(done), .count(count));
    always #5 clk = ~clk;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            m_state <= 0; m_count <= 0;
        end else case (m_state)
            0: if (start) begin m_state <= 1; m_count <= 0; runs = runs + 1; end
            1: if (m_count == limit) m_state <= 2; else m_count <= m_count + 1;
            default: m_state <= 0;
        endcase
    task check;
        begin
            if (busy !== (m_state == 1) || done !== (m_state == 2) || count !== m_count)
                $fatal(1, "t=%0t state=%0d: busy=%b done=%b count=%0d expected count=%0d",
                       $time, m_state, busy, done, count, m_count);
        end
    endtask
    initial begin
        seed = 17; runs = 0;
        #1 rst_n = 0;
        #1 check;
        rst_n = 1;
        for (i = 0; i < 800; i = i + 1) begin
            @(negedge clk);
            start = ($random(seed) & 3) == 0;
            if (m_state == 0) limit = $random(seed);
            #1 check;
            @(posedge clk); #1 check;
        end
        if (runs < 20) $fatal(1, "only %0d runs started", runs);
        $display("PASS: sv_fsm %0d runs", runs);
        $finish;
    end
endmodule
