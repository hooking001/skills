`timescale 1ns/1ps
// Inputs change away from clock edges; outputs are compared after every edge
// and after every asynchronous set/reset pulse.
module ff_styles_tb;
    reg        clk = 0, rst_n = 1, rst = 0, set_n = 1, en = 0;
    reg  [3:0] d = 0;
    wire [3:0] q_arst_n, q_arst_p, q_aset, q_mixed, q_sync_en, q_neg;
    wire       q_sr;
    reg  [3:0] m_arst_n, m_arst_p, m_aset, m_mixed, m_sync_en, m_neg;
    reg        m_sr;
    integer i, k, seed, checks;
    ff_styles uut (.clk(clk), .rst_n(rst_n), .rst(rst), .set_n(set_n), .en(en), .d(d),
                   .q_arst_n(q_arst_n), .q_arst_p(q_arst_p), .q_aset(q_aset), .q_mixed(q_mixed),
                   .q_sr(q_sr), .q_sync_en(q_sync_en), .q_neg(q_neg));
    always #5 clk = ~clk;

    // Reference model.
    always @(posedge clk or negedge rst_n) if (!rst_n) m_arst_n <= 0; else m_arst_n <= d;
    always @(posedge clk or posedge rst) if (rst) m_arst_p <= 0; else m_arst_p <= ~d;
    always @(posedge clk or negedge set_n) if (!set_n) m_aset <= 4'hf; else m_aset <= d ^ 4'h5;
    always @(posedge clk or negedge rst_n) if (!rst_n) m_mixed <= 4'b1010; else m_mixed <= d + 4'd1;
    always @(posedge clk or posedge rst or negedge set_n)
        if (rst) m_sr <= 0; else if (!set_n) m_sr <= 1; else m_sr <= ^d;
    always @(posedge clk) if (rst) m_sync_en <= 0; else if (en) m_sync_en <= d;
    always @(negedge clk) m_neg <= d;

    task check;
        begin
            if ({q_arst_n, q_arst_p, q_aset, q_mixed, q_sr, q_sync_en, q_neg} !==
                {m_arst_n, m_arst_p, m_aset, m_mixed, m_sr, m_sync_en, m_neg})
                $fatal(1, "t=%0t got %h %h %h %h %b %h %h expected %h %h %h %h %b %h %h", $time,
                       q_arst_n, q_arst_p, q_aset, q_mixed, q_sr, q_sync_en, q_neg,
                       m_arst_n, m_arst_p, m_aset, m_mixed, m_sr, m_sync_en, m_neg);
            checks = checks + 1;
        end
    endtask

    initial begin
        seed = 11; checks = 0;
        #1 rst_n = 0; rst = 1; set_n = 0;
        #1 check;                       // reset wins over set for q_sr
        set_n = 1;
        #1 check;
        rst_n = 1;                      // rst stays high through the first rising edge,
        #1 check;                       // so q_sync_en starts from a known value

        for (i = 0; i < 400; i = i + 1) begin
            @(posedge clk); #1 check;
            #1 d = $random(seed); en = $random(seed); rst = ($random(seed) & 7) == 0;
            #1 check;                   // asynchronous effect of rst
            k = $random(seed) & 15;
            if (k == 0) begin rst_n = 0; #1 check; rst_n = 1; end
            if (k == 1) begin set_n = 0; #1 check; set_n = 1; end
            @(negedge clk); #1 check;
            #1 d = $random(seed);
        end
        $display("PASS: ff_styles %0d checks", checks);
        $finish;
    end
endmodule
