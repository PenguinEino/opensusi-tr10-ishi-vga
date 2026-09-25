`default_nettype none
module letter_scan_patch(input wire clk,frame_end_n,h4,h5,red,green,blue,output wire green_new,blue_new);
reg [6:0] phase;
wire carry = !frame_end_n & (&phase[3:0]);
always @(posedge clk) begin
 phase[0] <= phase[0] ^ (!frame_end_n);
 phase[1] <= phase[1] ^ (!frame_end_n & (&phase[0:0]));
 phase[2] <= phase[2] ^ (!frame_end_n & (&phase[1:0]));
 phase[3] <= phase[3] ^ (!frame_end_n & (&phase[2:0]));
 if(carry) phase[6:4] <= phase[6:4]+3'd1;
end
wire on = red & ~blue & ~phase[6] & ((~{h5,h4}) == phase[5:4]);
assign green_new=green | on;
assign blue_new=blue | on;
endmodule
`default_nettype wire
