`timescale 1ns/1ps
module tb_vga;
    reg clk = 0;
    reg reset_n = 1;
    wire [1:0] r,g,b;
    wire hsync,vsync;
    ishi_vga_core dut(.clk(clk),.reset_n(reset_n),.r(r),.g(g),.b(b),.hsync(hsync),.vsync(vsync));
    real half_period = 79.365079365;
    reg clock_enable = 1;
    initial begin
        if ($value$plusargs("HALF_NS=%f", half_period)) begin end
        forever begin #(half_period); if (clock_enable) clk=~clk; end
    end
    reg [7:0] expected [0:104999];
    integer tick, count, fd;
    reg [1023:0] dump_path;
    task check_reset;
        begin
            #35;
            if ({vsync,hsync,r,g,b} !== 8'hc0)
                $fatal(1,"FAIL: reset outputs %h", {vsync,hsync,r,g,b});
        end
    endtask
    task release_reset;
        begin
            @(negedge clk); #7; reset_n=1;
            // Both synchronizer filling clocks must remain black with sync inactive.
            repeat (2) begin @(posedge clk); check_reset; end
        end
    endtask
    task check_frame_ticks;
        input integer n;
        input integer dump;
        begin
            for (count=0; count<n; count=count+1) begin
                @(posedge clk); #35;
                if ({vsync,hsync,r,g,b} !== expected[count%105000])
                    $fatal(1,"FAIL: tick %0d expected %h got %h",count,expected[count%105000],{vsync,hsync,r,g,b});
                if (dump && count<105000) $fdisplay(fd,"%02x",{vsync,hsync,r,g,b});
            end
        end
    endtask
    initial begin
        $readmemh("tests/expected_frame.hex",expected);
        if (!$value$plusargs("DUMP=%s",dump_path)) dump_path="build/rtl_frame.hex";
        fd=$fopen(dump_path,"w");
        if (!fd) $fatal(1,"FAIL: cannot open dump");
        #13; reset_n=0; check_reset;
        release_reset;
        check_frame_ticks(210017,1); // two complete frames plus rollover
        $fclose(fd);
        // Reset asynchronously in the middle of a frame, with clock stopped.
        @(negedge clk); clock_enable=0;
        #19; reset_n=0; check_reset;
        #400; check_reset;
        clock_enable=1;
        release_reset;
        check_frame_ticks(105000,0);
        $display("PASS: 315017 pixel ticks, frame wrap, stopped-clock reset, release; half=%f ns",half_period);
        $finish;
    end
    initial begin #100000000; $fatal(1,"FAIL: watchdog"); end
endmodule
