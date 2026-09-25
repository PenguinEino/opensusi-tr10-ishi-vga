#!/usr/bin/env python3
"""A-only rectangle covers with geometric don't-cares under the red letters.

cover4 keeps the current RGB111/black image exactly. cover3 and cover2 are
explicit palette alternatives. No coordinates or source rectangles are moved.
All trial outputs are immutable, and only the pinned upstream synthesizer runs.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image
from half_slot_trial import ROOT, tb


def cover(on, dc, xs, ys):
    allowed = on | dc
    candidates = []
    height, width = on.shape
    target = sum(1 << (int(y) * width + int(x)) for y, x in zip(*np.where(on)))
    for top in range(height):
        cols = np.ones(width, dtype=bool)
        for bottom in range(top + 1, height + 1):
            cols &= allowed[bottom - 1]
            left = 0
            while left < width:
                if not cols[left]:
                    left += 1
                    continue
                right = left + 1
                while right < width and cols[right]:
                    right += 1
                if ((top == 0 or not allowed[top - 1, left:right].all()) and
                        (bottom == height or not allowed[bottom, left:right].all())):
                    bits = sum(1 << (y * width + x) for y in range(top, bottom)
                               for x in range(left, right) if on[y, x])
                    if bits:
                        candidates.append((bits, [xs[left], ys[top], xs[right], ys[bottom]]))
                left = right
    remain = target
    chosen = []
    while remain:
        bits, rectangle = max(candidates, key=lambda p: ((p[0] & remain).bit_count(),
                                                        p[0].bit_count(), tuple(-v for v in p[1])))
        assert bits & remain
        chosen.append(rectangle)
        remain &= ~bits
    result = np.zeros_like(on)
    for x0, y0, x1, y1 in chosen:
        result[ys.index(y0):ys.index(y1), xs.index(x0):xs.index(x1)] = True
    assert (result[on]).all() and not (result & ~allowed).any()
    return chosen


def generate(mode):
    src = ROOT / 'experiments/a_half_a128_black'
    dst = ROOT / 'experiments' / ('a_half_a_' + mode)
    assert not dst.exists()
    for sub in ('build', 'tests'):
        (dst / sub).mkdir(parents=True, exist_ok=True)
    source = ROOT / 'assets/logo_rectangles_a_corrected.json'
    rects = json.loads(source.read_text())
    count = 4 if mode == 'direct4' else int(mode[-1])
    palettes = {4: [0, 3, 4, 3, 1, 5], 3: [0, 3, 4, 3, 1, 1], 2: [0, 3, 4, 3, 3, 3]}
    palette = palettes[count]
    xs = sorted({0, 128} | {x for _, a, b, c, d in rects for x in (a, c)})
    ys = sorted({0, 108} | {y for _, a, b, c, d in rects for y in (b, d)})
    masks = {c: np.zeros((len(ys)-1, len(xs)-1), dtype=bool) for c in range(1, 6)}
    for c, x0, y0, x1, y1 in rects:
        masks[c][ys.index(y0):ys.index(y1), xs.index(x0):xs.index(x1)] = True
    red, cyan, purple = masks[2], masks[1] | masks[3], masks[5]
    circuit = cyan | masks[4] | purple
    layers = {'red': red, 'cyan': cyan, 'purple': purple, 'circuit': circuit}
    dcs = {'red': np.zeros_like(red), 'cyan': red, 'purple': red | cyan, 'circuit': red}
    needed = ['red', 'circuit'] + (['cyan'] if count >= 3 else []) + (['purple'] if count == 4 else [])
    selected = {}
    for key in needed:
        selected[key] = cover(layers[key], dcs[key], xs, ys)
    if mode == 'direct4':
        selected = {'red': [r[1:] for r in rects if r[0] == 2],
                    'cyan': [r[1:] for r in rects if r[0] in [1, 3]],
                    'purple': [r[1:] for r in rects if r[0] == 5],
                    'circuit': [r[1:] for r in rects if r[0] != 2]}
    def raw(axis, a, b):
        if a == 0: return f"({axis} < 8'd{b})" if b < 256 else "1'b1"
        if b == 256: return f"({axis} >= 8'd{a})"
        return f"(({axis} >= 8'd{a}) && ({axis} < 8'd{b}))"
    def interval(axis, a, b):
        if axis == 'y': return raw('y', a+131, b+131)
        lo, hi = (48-b) % 256, (48-a) % 256
        if lo < hi: return raw('h', lo, hi)
        return '(' + raw('h', lo, 256) + ' | ' + raw('h', 0, hi) + ')'
    lines = ['`default_nettype none', 'module ishi_logo(input wire [7:0] h,y, output wire [2:0] rgb);']
    pixel_masks = {}
    for name, rectangles in selected.items():
        groups = {}
        plane = np.zeros((108, 128), dtype=bool)
        for a, b, c, d in rectangles:
            groups.setdefault((a, c), []).append((b, d))
            plane[b:d, a:c] = True
        pixel_masks[name] = plane
        terms = ['(' + interval('h', *key) + ' & (' + ' | '.join(interval('y', *v) for v in values) + '))'
                 for key, values in groups.items()]
        lines.append(f'wire {name} = ' + ' |\n'.join(terms) + ';')
    lines += ["assign rgb[2] = red" + (' | (purple & ~cyan)' if count == 4 else '') + ';',
              "assign rgb[1] = " + ('cyan' if count >= 3 else 'circuit') + ' & ~red;',
              'assign rgb[0] = circuit & ~red;', 'endmodule', '`default_nettype wire', '']
    reference = np.zeros((108, 128), dtype=np.uint8)
    for c, a, b, d, e in rects: reference[b:e, a:d] = palette[c]
    pm = pixel_masks
    rr = pm['red'] | (pm['purple'] & ~pm['cyan']) if count == 4 else pm['red']
    gg = (pm['cyan'] if count >= 3 else pm['circuit']) & ~pm['red']
    bb = pm['circuit'] & ~pm['red']
    assert np.array_equal(reference, rr.astype(np.uint8)*4 + gg.astype(np.uint8)*2 + bb.astype(np.uint8))
    screen = np.zeros((480, 160), dtype=np.uint8)
    screen[24:456, 16:144] = np.repeat(reference, 4, axis=0)
    frame = np.zeros((525, 200), dtype=np.uint8)
    frame[:480, :160] = screen
    frame[:, :164] |= 8; frame[:, 188:] |= 8
    frame[:490, :] |= 16; frame[492:, :] |= 16
    (dst / 'tests/expected_frame.hex').write_text(''.join(f'{v:02x}\n' for v in frame.flat))
    rgb = np.stack([((screen >> bit) & 1)*255 for bit in (2,1,0)], axis=-1)
    Image.fromarray(np.repeat(rgb, 4, axis=1)).save(dst / 'build/reference.png')
    (dst / 'ishi_logo.v').write_text('\n'.join(lines))
    (dst / 'ishi_vga_core.v').write_bytes((src / 'ishi_vga_core.v').read_bytes())
    settings = json.loads((src / 'trial.json').read_text())
    settings.update(renderer=mode, palette_rgb111=palette, foreground_colors=count,
                    image_exact_to_rgb111_A_black=(count == 4), coordinates_changed=False)
    (dst / 'trial.json').write_text(json.dumps(settings, indent=2)+'\n')
    (dst / 'covers.json').write_text(json.dumps(selected, indent=2)+'\n')
    (dst / 'tests/tb_rtl.v').write_text(tb(settings, 'dut.h=0; dut.v=0;'))
    cfg = (src / 'config.py').read_text().replace(str(src / 'tests/tb_rtl.v'), str(dst / 'tests/tb_rtl.v'))
    cfg = re.sub(r'^HALF_SLOT = .*$', f'HALF_SLOT = {settings!r}', cfg, flags=re.M)
    (dst / 'config.py').write_text(cfg)
    paths = [Path(__file__), ROOT / 'scripts/half_slot_trial.py', source, src / 'source_manifest.json',
             *[dst / p for p in ['config.py','trial.json','covers.json','ishi_vga_core.v','ishi_logo.v',
                                'tests/expected_frame.hex','tests/tb_rtl.v']]]
    (dst / 'source_manifest.json').write_text(json.dumps({'scope': 'A coordinate-preserving palette/cover trial',
        'rectangles_per_mask': {k:len(v) for k,v in selected.items()},
        'sha256': {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}, indent=2)+'\n')
    print(dst.name, {k:len(v) for k,v in selected.items()})


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=['cover4','cover3','cover2','direct4'])
    generate(ap.parse_args().mode)
