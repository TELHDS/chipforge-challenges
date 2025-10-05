`timescale 1ns/1ps
module tb_top;
    // DUT I/O
    reg        clk;
    reg  [3:0] a_in, b_in;
    reg        cin_in;
    wire [3:0] sum_ff;
    wire       cout_ff;

    // DUT
    adder_ff uut (
        .clk(clk),
        .a_in(a_in),
        .b_in(b_in),
        .cin_in(cin_in),
        .sum_ff(sum_ff),
        .cout_ff(cout_ff)
    );

    // Stats
    integer pass_cnt = 0;
    integer fail_cnt = 0;
    integer total    = 0;

    integer i, num_tests, seed, max_fail_logs, fail_logs;
    reg [4:0] exp;
    reg [3:0] exp_sum;
    reg       exp_cout;
    real      func_score;

    // Clock generator
    always #5 clk = ~clk;

    initial begin
        // VCD
        $dumpfile("adder_ff.vcd");
        $dumpvars(0, tb_adder_ff);

        // Defaults
        num_tests     = 500;
        seed          = 32'h1234;
        max_fail_logs = 10;
        fail_logs     = 0;

        if ($value$plusargs("NUM_TESTS=%d", num_tests)) ;
        if ($value$plusargs("SEED=%d", seed)) ;

        clk    = 0;
        a_in   = 0;
        b_in   = 0;
        cin_in = 0;

        // Apply randomized tests
        for (i = 0; i < num_tests; i = i + 1) begin
            a_in   = $random(seed) & 4'hF;
            b_in   = $random(seed) & 4'hF;
            cin_in = $random(seed) & 1'b1;

            @(posedge clk); // wait for output update

            // Expected reference
            exp      = a_in + b_in + cin_in;
            exp_sum  = exp[3:0];
            exp_cout = exp[4];

            if (sum_ff === exp_sum && cout_ff === exp_cout) begin
                pass_cnt++;
            end else begin
                fail_cnt++;
                if (fail_logs < max_fail_logs) begin
                    $display("FAIL: a=%0d b=%0d cin=%0d -> got sum=%0d cout=%0d, exp sum=%0d cout=%0d",
                             a_in, b_in, cin_in, sum_ff, cout_ff, exp_sum, exp_cout);
                    fail_logs++;
                end
            end
            total++;
        end

        // Final score
        if (total > 0)
            func_score = pass_cnt * 1.0 / total;
        else
            func_score = 0.0;

        $display("FUNC_SUMMARY pass=%0d fail=%0d total=%0d", pass_cnt, fail_cnt, total);
        $display("FUNC_SCORE: %0.6f", func_score);

        $finish;
    end
endmodule
