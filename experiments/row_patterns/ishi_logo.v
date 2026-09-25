// Generated row-sharing B experiment: binary
`default_nettype none
module ishi_logo(input wire [7:0] h, input wire [7:0] y, output wire [5:0] rgb);
    wire select_1 = ((y >= 8'd19) && (y < 8'd25)) || ((y >= 8'd94) && (y < 8'd100));
    wire select_2 = ((y >= 8'd33) && (y < 8'd36)) || ((y >= 8'd83) && (y < 8'd86));
    wire select_3 = ((y >= 8'd36) && (y < 8'd42)) || ((y >= 8'd77) && (y < 8'd83));
    wire select_4 = ((y >= 8'd42) && (y < 8'd45)) || ((y >= 8'd54) && (y < 8'd56));
    wire select_5 = ((y >= 8'd45) && (y < 8'd54));
    wire select_6 = ((y >= 8'd56) && (y < 8'd62));
    wire select_7 = ((y >= 8'd62) && (y < 8'd65)) || ((y >= 8'd74) && (y < 8'd77));
    wire select_8 = ((y >= 8'd65) && (y < 8'd74));
    wire select_0 = !(select_1 | select_2 | select_3 | select_4 | select_5 | select_6 | select_7 | select_8);
    wire [5:0] pattern_0 = 6'b111111;
    reg [5:0] pattern_1;
    always @* begin
        pattern_1 = 6'b111111;
        if (((h >= 8'd18) && (h < 8'd141))) pattern_1 = 6'b011011;
    end
    reg [5:0] pattern_2;
    always @* begin
        pattern_2 = 6'b111111;
        if (((h >= 8'd18) && (h < 8'd141))) pattern_2 = 6'b011111;
    end
    reg [5:0] pattern_3;
    always @* begin
        pattern_3 = 6'b111111;
        if (((h >= 8'd30) && (h < 8'd41)) || ((h >= 8'd47) && (h < 8'd71)) || ((h >= 8'd79) && (h < 8'd85)) || ((h >= 8'd106) && (h < 8'd112)) || ((h >= 8'd117) && (h < 8'd129))) pattern_3 = 6'b110101;
    end
    reg [5:0] pattern_4;
    always @* begin
        pattern_4 = 6'b111111;
        if (((h >= 8'd33) && (h < 8'd38)) || ((h >= 8'd47) && (h < 8'd53)) || ((h >= 8'd79) && (h < 8'd85)) || ((h >= 8'd106) && (h < 8'd112)) || ((h >= 8'd120) && (h < 8'd126))) pattern_4 = 6'b110101;
    end
    reg [5:0] pattern_5;
    always @* begin
        pattern_5 = 6'b111111;
        if (((h >= 8'd24) && (h < 8'd135))) pattern_5 = 6'b010111;
        if (((h >= 8'd33) && (h < 8'd38)) || ((h >= 8'd47) && (h < 8'd53)) || ((h >= 8'd79) && (h < 8'd85)) || ((h >= 8'd106) && (h < 8'd112)) || ((h >= 8'd120) && (h < 8'd126))) pattern_5 = 6'b110101;
    end
    reg [5:0] pattern_6;
    always @* begin
        pattern_6 = 6'b111111;
        if (((h >= 8'd33) && (h < 8'd38)) || ((h >= 8'd47) && (h < 8'd71)) || ((h >= 8'd79) && (h < 8'd112)) || ((h >= 8'd120) && (h < 8'd126))) pattern_6 = 6'b110101;
    end
    reg [5:0] pattern_7;
    always @* begin
        pattern_7 = 6'b111111;
        if (((h >= 8'd33) && (h < 8'd38)) || ((h >= 8'd65) && (h < 8'd71)) || ((h >= 8'd79) && (h < 8'd85)) || ((h >= 8'd106) && (h < 8'd112)) || ((h >= 8'd120) && (h < 8'd126))) pattern_7 = 6'b110101;
    end
    reg [5:0] pattern_8;
    always @* begin
        pattern_8 = 6'b111111;
        if (((h >= 8'd24) && (h < 8'd94)) || ((h >= 8'd97) && (h < 8'd135))) pattern_8 = 6'b101011;
        if (((h >= 8'd33) && (h < 8'd38)) || ((h >= 8'd65) && (h < 8'd71)) || ((h >= 8'd79) && (h < 8'd85)) || ((h >= 8'd106) && (h < 8'd112)) || ((h >= 8'd120) && (h < 8'd126))) pattern_8 = 6'b110101;
    end
    reg [3:0] row_pattern;
    always @* begin
        row_pattern = 4'd0;
        if (select_1) row_pattern = 4'd1;
        if (select_2) row_pattern = 4'd2;
        if (select_3) row_pattern = 4'd3;
        if (select_4) row_pattern = 4'd4;
        if (select_5) row_pattern = 4'd5;
        if (select_6) row_pattern = 4'd6;
        if (select_7) row_pattern = 4'd7;
        if (select_8) row_pattern = 4'd8;
    end
    reg [5:0] selected_rgb;
    always @* begin
        case (row_pattern)
            4'd1: selected_rgb = pattern_1;
            4'd2: selected_rgb = pattern_2;
            4'd3: selected_rgb = pattern_3;
            4'd4: selected_rgb = pattern_4;
            4'd5: selected_rgb = pattern_5;
            4'd6: selected_rgb = pattern_6;
            4'd7: selected_rgb = pattern_7;
            4'd8: selected_rgb = pattern_8;
            default: selected_rgb = pattern_0;
        endcase
    end
    assign rgb = selected_rgb;
endmodule
`default_nettype wire
