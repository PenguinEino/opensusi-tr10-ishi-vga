#!/usr/bin/env python3
"""Experiment: deduplicate whole raster rows, then select their X-to-RGB circuit."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'experiments/row_patterns'
OUT.mkdir(parents=True, exist_ok=True)
rects = json.loads((ROOT/'assets/logo_rectangles.json').read_text())
rows = [[0]*128 for _ in range(108)]
for c,x0,y0,x1,y1 in rects:
    for y in range(y0,y1): rows[y][x0:x1] = [c]*(x1-x0)
patterns = [tuple([0]*128)]
runs = []
for y,row in enumerate(rows):
    row = tuple(row)
    if row not in patterns: patterns.append(row)
    ident = patterns.index(row)
    if runs and runs[-1][2] == ident: runs[-1][1] = y+1
    else: runs.append([y,y+1,ident])
assert len(patterns)==9 and len(runs)==17
palette=[63,27,53,31,23,43]
(OUT/'patterns.json').write_text(json.dumps({'unique_rows_including_white':len(patterns),'y_runs':runs,'patterns':patterns},indent=2)+'\n')
# Preserve paint priority: a blue/purple band may continue behind a later red
# foreground. Expanding those hidden spans avoids artificial holes from raster RLE.
priority = {c:i for i,c in enumerate([0,4,5,1,2,3])}
def spans(row, color):
    result=[]; start=None
    for x,c in enumerate((*row,0)):
        allowed = x < 128 and priority[c] >= priority[color]
        if allowed and start is None: start=x
        if not allowed and start is not None:
            if color in row[start:x]: result.append((start,x))
            start=None
    return result

for selection in ['binary','onehot']:
    target = OUT if selection=='binary' else ROOT/'experiments/row_patterns_onehot'
    target.mkdir(parents=True,exist_ok=True)
    (target/'build').mkdir(exist_ok=True)
    if not (target/'tests').exists(): (target/'tests').symlink_to('../../tests',target_is_directory=True)
    lines=['// Generated row-sharing B experiment: '+selection,
           '`default_nettype none',
           'module ishi_logo(input wire [7:0] h, input wire [7:0] y, output wire [5:0] rgb);']
    for ident in range(1,9):
        terms=[f"((y >= 8'd{a+6}) && (y < 8'd{b+6}))" for a,b,p in runs if p==ident]
        lines.append(f"    wire select_{ident} = {' || '.join(terms)};")
    lines.append('    wire select_0 = !('+' | '.join(f'select_{i}' for i in range(1,9))+');')
    lines.append("    wire [5:0] pattern_0 = 6'b111111;")
    for ident,row in enumerate(patterns[1:],1):
        lines.append(f'    reg [5:0] pattern_{ident};')
        lines.extend(['    always @* begin',f"        pattern_{ident} = 6'b111111;"])
        for color in [4,5,1,2,3]:
            intervals=spans(row,color)
            if not intervals: continue
            terms=[f"((h >= 8'd{a+16}) && (h < 8'd{b+16}))" for a,b in intervals]
            lines.append(f"        if ({' || '.join(terms)}) pattern_{ident} = 6'b{palette[color]:06b};")
        lines.append('    end')
    if selection=='binary':
        lines+=['    reg [3:0] row_pattern;', '    always @* begin', "        row_pattern = 4'd0;"]
        for i in range(1,9): lines.append(f"        if (select_{i}) row_pattern = 4'd{i};")
        lines+=['    end','    reg [5:0] selected_rgb;','    always @* begin','        case (row_pattern)']
        for i in range(1,9): lines.append(f"            4'd{i}: selected_rgb = pattern_{i};")
        lines+=['            default: selected_rgb = pattern_0;','        endcase','    end','    assign rgb = selected_rgb;']
    else:
        lines.append('    assign rgb = '+' |\n        '.join(f'({{6{{select_{i}}}}} & pattern_{i})' for i in range(9))+';')
    lines+=['endmodule','`default_nettype wire','']
    (target/'ishi_logo.v').write_text('\n'.join(lines))
