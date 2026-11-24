`timescale 1ns/1ps
// Every entry is written before it is read, then writes and reads are random.
module regfile8x8_tb;
    reg        clk = 0, we = 0;
    reg  [2:0] waddr = 0, raddr_a = 0, raddr_b = 0;
    reg  [7:0] wdata = 0;
    wire [7:0] rdata_a, rdata_b;
    reg  [7:0] model [0:7];
    integer i, seed, checks;
    regfile8x8 uut (.clk(clk), .we(we), .waddr(waddr), .wdata(wdata), .raddr_a(raddr_a),
                    .raddr_b(raddr_b), .rdata_a(rdata_a), .rdata_b(rdata_b));
    always #5 clk = ~clk;
    always @(posedge clk) if (we) model[waddr] <= wdata;
    task check;
        begin
            #1;
            if (rdata_a !== model[raddr_a] || rdata_b !== model[raddr_b])
                $fatal(1, "t=%0t read %0d/%0d: got %h/%h expected %h/%h", $time, raddr_a, raddr_b,
                       rdata_a, rdata_b, model[raddr_a], model[raddr_b]);
            checks = checks + 1;
        end
    endtask
    initial begin
        seed = 9; checks = 0;
        for (i = 0; i < 8; i = i + 1) begin
            @(negedge clk); we = 1; waddr = i; wdata = 8'h11 * i + 8'h0f;
        end
        @(negedge clk); we = 0;
        for (i = 0; i < 64; i = i + 1) begin
            raddr_a = i % 8; raddr_b = 7 - i % 8; check;
        end
        for (i = 0; i < 500; i = i + 1) begin
            @(negedge clk);
            we = $random(seed); waddr = $random(seed); wdata = $random(seed);
            raddr_a = $random(seed); raddr_b = waddr;
            check;                      // reads before the write lands
            @(posedge clk); check;      // and after it
        end
        $display("PASS: regfile8x8 %0d checks", checks);
        $finish;
    end
endmodule
