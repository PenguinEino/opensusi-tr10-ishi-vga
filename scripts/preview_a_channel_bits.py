#!/usr/bin/env python3
"""Design-reference previews of direct RGB DAC alternatives, not RTL results.

Retained single-bit channels use the original channel MSB and full-scale DAC.
The original A geometry and palette remain unchanged on disk.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/logo_rectangles_a_corrected.json'
OUT = ROOT / 'samples/a_channel_bits'
PALETTE = [63, 27, 53, 31, 23, 43]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    logo = np.zeros((108, 128), dtype=np.uint8)
    for c, x0, y0, x1, y1 in json.loads(SOURCE.read_text()):
        logo[y0:y1, x0:x1] = c
    original = np.array([[(p >> 4) & 3, (p >> 2) & 3, p & 3] for p in PALETTE])
    variants = [
        ('RGB222', (2, 2, 2), False),
        ('RGB221', (2, 2, 1), False),
        ('RGB121', (1, 2, 1), False),
        ('RGB121_red', (1, 2, 1), True),
        ('RGB111', (1, 1, 1), False),
    ]
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
    sheet = Image.new('RGB', (1328, 1788), '#e7e7e7')
    draw = ImageDraw.Draw(sheet)
    reports = []
    for i, (name, bits, red_adjust) in enumerate(variants):
        pal = original.copy()
        for channel, nbits in enumerate(bits):
            if nbits == 1:
                pal[:, channel] = (pal[:, channel] >> 1) * 3
        if red_adjust:
            pal[2, 1] = 0
        screen = np.full((480, 640, 3), 255, dtype=np.uint8)
        screen[24:456, 64:576] = np.repeat(np.repeat((pal[logo] * 85).astype(np.uint8), 4, 0), 4, 1)
        picture = Image.fromarray(screen)
        picture.save(OUT / (name + '.png'))
        distinct = len(set(map(tuple, pal.tolist())))
        x, y = 16 + (i % 2) * 656, 12 + (i // 2) * 592
        draw.text((x, y), name + (' (red G=0)' if red_adjust else ''), fill='black', font=font)
        draw.text((x, y + 31), f'{sum(bits)} RGB wires; {distinct}/6 distinct logo colors; geometry unchanged', fill='black', font=small)
        sheet.paste(picture, (x, y + 60))
        for j, rgb in enumerate(pal * 85):
            draw.rectangle((x + j * 104, y + 550, x + j * 104 + 95, y + 574), fill=tuple(rgb))
        reports.append({'name': name, 'channel_bits': bits, 'rgb_8bit': (pal * 85).tolist(),
                        'distinct_logo_colors': distinct, 'manual_red_green_zero': red_adjust,
                        'signal_count_without_reset': sum(bits) + 3})
    draw.text((672, 1210), 'Direct DAC signals, no palette decoder.', fill='black', font=font)
    draw.text((672, 1250), 'Single-bit channels use MSB -> 0 or full scale.', fill='black', font=small)
    draw.text((672, 1280), 'Design previews only; not RTL simulation output.', fill='black', font=small)
    draw.text((672, 1310), 'Power, clock and sync are not shown in pictures.', fill='black', font=small)
    sheet.save(OUT / 'comparison.png')
    paths = [SOURCE, Path(__file__), *sorted(OUT.glob('*.png'))]
    (OUT / 'manifest.json').write_text(json.dumps({'scope': 'Unadopted direct-channel color alternatives; design references only',
        'variants': reports, 'sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}, indent=2) + '\n')
    print(OUT / 'comparison.png')


if __name__ == '__main__':
    main()
