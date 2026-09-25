`timescale 1ns/1ps
module tb_logo_equivalence;
    reg [7:0] h,y;
    wire [5:0] expected,actual;
    integer i,j;
    ishi_logo_reference reference(.h(h),.y(y),.rgb(expected));
    ishi_logo candidate(.h(h),.y(y),.rgb(actual));
    initial begin
        for(i=0;i<256;i=i+1) begin
            for(j=0;j<256;j=j+1) begin
                h=i; y=j; #1;
                if(actual !== expected)
                    $fatal(1,"FAIL: h=%0d y=%0d expected=%h actual=%h",i,j,expected,actual);
            end
        end
        $display("PASS: all 65536 h/y combinations equivalent");
        $finish;
    end
endmodule
