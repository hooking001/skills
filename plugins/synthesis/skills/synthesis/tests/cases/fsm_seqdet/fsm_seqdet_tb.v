`timescale 1ns/1ps
// Reference: the last four received bits, so detection needs no state encoding.
module fsm_seqdet_tb;
    reg        clk = 0, rst_n = 1, din = 0;
    wire       moore, mealy;
    reg  [3:0] hist;
    integer i, seed, moore_hits, mealy_hits;
    fsm_seqdet uut (.clk(clk), .rst_n(rst_n), .din(din), .moore(moore), .mealy(mealy));
    always #5 clk = ~clk;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) hist <= 4'd0;
        else hist <= {hist[2:0], din};
    task check;
        begin
            if (moore !== (hist == 4'b1011) || mealy !== ({hist[2:0], din} == 4'b1011))
                $fatal(1, "t=%0t hist=%b din=%b: moore=%b mealy=%b", $time, hist, din, moore, mealy);
            moore_hits = moore_hits + moore;
            mealy_hits = mealy_hits + mealy;
        end
    endtask
    initial begin
        seed = 3; moore_hits = 0; mealy_hits = 0;
        #1 rst_n = 0;
        #2 rst_n = 1;
        for (i = 0; i < 600; i = i + 1) begin
            @(negedge clk);
            // Bias towards ones so that overlapping patterns occur often.
            din = ($random(seed) & 3) != 0;
            if (i == 300) begin rst_n = 0; #1 rst_n = 1; end
            #1 check;
            @(posedge clk); #1 check;
        end
        if (moore_hits < 10 || mealy_hits < 10)
            $fatal(1, "too few detections: %0d/%0d", moore_hits, mealy_hits);
        $display("PASS: fsm_seqdet %0d Moore and %0d Mealy detections", moore_hits, mealy_hits);
        $finish;
    end
endmodule
