// SystemVerilog subset read with `read_verilog -sv`: logic, typedef enum,
// always_ff, always_comb, unique case and '0 literals.
module sv_fsm (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       start,
    input  logic [3:0] limit,
    output logic       busy,
    output logic       done,
    output logic [3:0] count
);
typedef enum logic [1:0] {IDLE = 2'd0, RUN = 2'd1, DONE = 2'd2} state_t;
state_t     state, state_n;
logic [3:0] count_n;

always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        state <= IDLE;
        count <= '0;
    end else begin
        state <= state_n;
        count <= count_n;
    end
end

always_comb begin
    state_n = state;
    count_n = count;
    unique case (state)
        IDLE: if (start) begin
            state_n = RUN;
            count_n = '0;
        end
        RUN: if (count == limit) state_n = DONE;
             else count_n = count + 4'd1;
        DONE: state_n = IDLE;
        default: state_n = IDLE;
    endcase
end

assign busy = (state == RUN);
assign done = (state == DONE);
endmodule
