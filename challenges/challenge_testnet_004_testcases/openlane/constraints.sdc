# Create the main clock (period = 10 ns → 100 MHz target)
create_clock -name clk -period 10.0 [get_ports clk]

# Add clock uncertainty margin
set_clock_uncertainty 0.25 [get_clocks clk]

# Exclude async reset from timing
set_false_path -from [get_ports resetn_i]

# Apply input delays: explicitly list all inputs except clk and resetn_i
foreach port [get_ports *] {
    if { $port ne "clk" } {
        set_input_delay 0.20 -clock clk [get_ports $port]
    }
}

# Apply output delays on all outputs
set_output_delay 0.20 -clock clk [all_outputs]
