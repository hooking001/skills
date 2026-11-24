// Register styles that need different sequential cells or extra logic.
module ff_styles (
    input  wire       clk,
    input  wire       rst_n,      // asynchronous, active low
    input  wire       rst,        // asynchronous for q_arst_p/q_sr, synchronous for q_sync_en
    input  wire       set_n,      // asynchronous set, active low
    input  wire       en,
    input  wire [3:0] d,
    output reg  [3:0] q_arst_n,   // async reset to 0
    output reg  [3:0] q_arst_p,   // async active-high reset to 0
    output reg  [3:0] q_aset,     // async set to all ones
    output reg  [3:0] q_mixed,    // async reset to 4'b1010
    output reg        q_sr,       // separate async reset (priority) and set
    output reg  [3:0] q_sync_en,  // sync reset with enable
    output reg  [3:0] q_neg       // falling-edge clock, no reset
);
always @(posedge clk or negedge rst_n)
    if (!rst_n) q_arst_n <= 4'd0;
    else q_arst_n <= d;

always @(posedge clk or posedge rst)
    if (rst) q_arst_p <= 4'd0;
    else q_arst_p <= ~d;

always @(posedge clk or negedge set_n)
    if (!set_n) q_aset <= 4'hf;
    else q_aset <= d ^ 4'h5;

always @(posedge clk or negedge rst_n)
    if (!rst_n) q_mixed <= 4'b1010;
    else q_mixed <= d + 4'd1;

always @(posedge clk or posedge rst or negedge set_n)
    if (rst) q_sr <= 1'b0;
    else if (!set_n) q_sr <= 1'b1;
    else q_sr <= ^d;

always @(posedge clk)
    if (rst) q_sync_en <= 4'd0;
    else if (en) q_sync_en <= d;

always @(negedge clk)
    q_neg <= d;
endmodule
