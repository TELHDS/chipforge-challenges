`timescale 1ns/1ps
module adder_ff (
    input         clk,
    input  [3:0]  a_in,
    input  [3:0]  b_in,
    input         cin_in,
    output reg [3:0] sum_ff,
    output reg    cout_ff
);

    // Registered inputs
    reg [3:0] a_ff, b_ff;
    reg       cin_ff;

    // Combinational adder result
    wire [4:0] result;
    assign result = a_ff + b_ff + cin_ff;

    always @(posedge clk) begin
        // Latch inputs
        a_ff   <= a_in;
        b_ff   <= b_in;
        cin_ff <= cin_in;

        // Latch outputs
        sum_ff  <= result[3:0];
        cout_ff <= result[4];
    end

endmodule
