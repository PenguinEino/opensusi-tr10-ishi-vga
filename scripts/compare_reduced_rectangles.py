#!/usr/bin/env python3
"""Render deterministic rectangle-reduction proposals; does not change RTL."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'samples/reduced_rectangles'
RECTS = json.loads((ROOT / 'assets/logo_rectangles_original37.json').read_text())
PALETTE = np.array([63, 27, 53, 31, 23, 43], dtype=np.uint8)
OUT.mkdir(parents=True, exist_ok=True)

def render(rects):
    logo = np.zeros((108, 128), dtype=np.uint8)
    for c, x0, y0, x1, y1 in rects:
        logo[y0:y1, x0:x1] = c
    canvas = np.full((480, 640), 63, dtype=np.uint8)
    canvas[24:456, 64:576] = np.repeat(np.repeat(PALETTE[logo], 4, axis=0), 4, axis=1)
    return Image.fromarray(np.stack([((canvas >> 4) & 3)*85,
                                    ((canvas >> 2) & 3)*85, (canvas & 3)*85], axis=-1))

variants = [
    ('A', 'original', '元の37矩形版', '元の37矩形。比較の基準。', RECTS),
    ('B', 'outline_bars', '採用B：上下の横線だけ', '水色の細い配線を省略。外側の横線は残す。',
     [r for r in RECTS if r[0] != 1 or (r[1] == 2 and r[3] == 125)]),
    ('C', 'no_outline', '水色の輪郭をすべて省略', '赤文字・青と紫の帯・シアンの横線を残す。',
     [r for r in RECTS if r[0] != 1]),
    ('D', 'letters_and_bands', '赤文字＋青・紫の帯', 'シアンの横線も省略。背景の帯は残す。',
     [r for r in RECTS if r[0] in (2, 4, 5)]),
    ('E', 'letters_and_cyan', '赤文字＋シアンの横線', '背景の帯を省略。文字を上下の線で挟む。',
     [r for r in RECTS if r[0] in (2, 3)]),
    ('F', 'letters_only', '赤文字のみ', '既存の文字形状を保つ、最も簡単な案。',
     [r for r in RECTS if r[0] == 2]),
]
assert [len(v[4]) for v in variants] == [37, 21, 19, 17, 16, 14]
font_path = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
bold_path = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
font = ImageFont.truetype(font_path, 22)
small = ImageFont.truetype(font_path, 19)
title = ImageFont.truetype(bold_path, 28)
heading = ImageFont.truetype(bold_path, 32)
sheet = Image.new('RGB', (1360, 2040), '#edf1f5')
draw = ImageDraw.Draw(sheet)
draw.text((28, 17), 'ISHIロゴ：矩形を減らした6案', font=heading, fill='#172b40')
draw.text((28, 67), '全案 640×480 / ロゴ座標128×108を4倍 / 同じRGB222・配置・文字サイズ', font=font, fill='#45596d')
records = []
for i, (label, slug, name, description, rects) in enumerate(variants):
    img = render(rects)
    img.save(OUT / f'{label}_{slug}.png')
    (OUT / f'{label}_{slug}.json').write_text(json.dumps(rects, indent=2)+'\n')
    x, y = 24 + (i % 2)*668, 117 + (i // 2)*620
    draw.rounded_rectangle((x, y, x+644, y+605), radius=12, fill='white')
    draw.text((x+12, y+9), f'{label}  {name}', font=title, fill='#172b40')
    draw.text((x+12, y+49), f'{len(rects)}矩形  |  37矩形版比 −{37-len(rects)}矩形', font=font, fill='#406580')
    sheet.paste(img, (x+2, y+81))
    # Keep explanatory text outside the simulated VGA image.
    draw.text((x+12, y+572), description, font=small, fill='#45596d')
    records.append({'id':label,'name':name,'rectangles':len(rects),
                    'description':description,'image':f'{label}_{slug}.png'})
draw.text((28, 2000), '矩形数は回路面積の比率ではありません。B案は実装済み。面積・配線の結果は実装記録を参照。', font=font, fill='#45596d')
sheet.save(OUT / 'comparison.png')
(OUT / 'variants.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
baseline = Image.open(ROOT / 'docs/validation/rtl_630.png').convert('RGB')
assert np.array_equal(np.asarray(render(RECTS)), np.asarray(baseline)), 'Baseline differs from verified RTL'
(OUT / 'README.md').write_text('''# 矩形削減案の見た目比較

`../../scripts/compare_reduced_rectangles.py`で生成。各PNGは640×480、RGB222、
128×108座標を4倍表示。文字の位置・大きさ・色は全案同じ。
JSONは元の描画順を保った矩形リスト。この比較スクリプト自体はRTLを変更しない。
比較基準Aの画素は検証済みRTL出力画像と完全一致することを生成時に検査する。

|案|内容|矩形数|
|---|---|---:|
|A|元の37矩形版|37|
|B|水色の輪郭を上下2本の横線だけに|21|
|C|水色の輪郭を全部省略|19|
|D|赤文字と青・紫の帯|17|
|E|赤文字とシアンの横線|16|
|F|赤文字のみ|14|

B案は実装・合成済み。結果はdocs/IMPLEMENTATION.mdを参照。その他の案は未合成。矩形数の削減率を面積削減率として扱わない。
''')
print(OUT / 'comparison.png')
