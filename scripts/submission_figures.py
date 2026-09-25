#!/usr/bin/env python3
"""Design-owned submission figures from actual GDS and the adopted RTL.

Pin presentation follows balanced-ternary-logic's overview + metal close-ups.
Only the fixed submitted GDS is read; no dependency search or circuit edits.
Run with system Python (matplotlib, klayout), not the APR virtualenv.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/ishi-vga-submission-mpl')
import klayout.db as db
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon, Rectangle, FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
GDS_SHA = '95a799066aeade8a5ca04cd1425252759988ee61c429f383c699b1b17e4d29b3'
INK = '#17324d'
M1, M2, RED = '#477cab', '#c89434', '#c42b36'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fonts():
    font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
    plt.rcParams.update({'font.family': ['Noto Sans CJK JP', 'DejaVu Sans'],
                         'font.size': 12, 'svg.fonttype': 'path',
                         'svg.hashsalt': 'ishi-vga-submission-figures-v2'})


def pins(out):
    gds = out / 'ishi_vga.gds'
    assert sha(gds) == GDS_SHA
    ly = db.Layout(); ly.read(str(gds)); top = ly.cell('ishi_vga_core')
    info = json.loads((out / 'ports.json').read_text())
    ports = {p['name']: p for p in info['ports']}
    regions = {layer: db.Region(top.begin_shapes_rec(ly.layer(layer, 0))).merged()
               for layer in (13, 20)}
    for name, p in ports.items():
        layer = 13 if p['layer'] == 'M1' else 20
        point = db.Point(*(round(v / ly.dbu) for v in p['xy_um']))
        assert any(poly.inside(point) for poly in regions[layer].each()), name
        # Labels are on pin marker/text layers, not necessarily drawing metal.
        assert any(s.is_text() and s.text.string == name and s.text.x == point.x and s.text.y == point.y
                   for li in ly.layer_indexes() for s in top.shapes(li).each()), name

    def metal(ax, bounds):
        clip = db.Region(db.Box(*(round(v / ly.dbu) for v in bounds)))
        for layer, color in ((13, M1), (20, M2)):
            patches = []
            for poly in (regions[layer] & clip).each():
                for part in poly.decompose_trapezoids():
                    patches.append(Polygon([(p.x * ly.dbu, p.y * ly.dbu) for p in part.each_point()]))
            ax.add_collection(PatchCollection(patches, facecolor=color, edgecolor='none'))
        ax.set_xlim(bounds[0], bounds[2]); ax.set_ylim(bounds[1], bounds[3])
        ax.set_aspect('equal'); ax.set_facecolor('#f5f7fa')
        ax.tick_params(labelsize=10)
        for spine in ax.spines.values(): spine.set_color('#6f7f8e')

    fig = plt.figure(figsize=(16, 13.5), facecolor='white', layout='constrained')
    grid = fig.add_gridspec(4, 4, height_ratios=[3.05, 1.15, 1.15, .20], hspace=.12)
    overview = fig.add_subplot(grid[0, :])
    metal(overview, (-170, -95, 1840, 1030))
    overview.add_patch(Rectangle((-15.3, 0), 1792.8, 897.2, fill=False,
                                edgecolor='#67717d', linestyle='--', linewidth=1.2))
    labels = {'clk': (770, 977), 'vsync': (1080, 977), 'hsync': (261.9, -58),
              'g': (-100, 768), 'r': (-100, 690), 'b': (-100, 586),
              'vdd': (-100, 165), 'vss': (-100, 52)}
    for name, p in ports.items():
        x, y = p['xy_um']
        overview.plot(x, y, 'o', mfc='none', mec=RED, ms=9, mew=1.7, zorder=5)
        overview.annotate(name.upper(), (x, y), xytext=labels[name],
                          ha='center', va='center', fontsize=14, fontweight='bold', color=RED,
                          arrowprops={'arrowstyle': '-', 'color': RED, 'lw': 1.4}, zorder=6)
    overview.set_title('ISHI VGA  |  実レイアウト上の端子位置', loc='left', fontsize=18, fontweight='bold', pad=38)
    overview.text(0, 1.025, '青：M1 (13/0)     金：M2 (20/0)     赤丸：接続位置     点線：コア外形 1792.8 × 897.2 µm',
                  transform=overview.transAxes, fontsize=12, color=INK)
    overview.set_xlabel('X [µm] — GDS座標', fontsize=11)
    overview.set_ylabel('Y [µm]', fontsize=11)
    order = ['clk', 'hsync', 'vsync', 'vdd', 'r', 'g', 'b', 'vss']
    for i, name in enumerate(order):
        ax = fig.add_subplot(grid[1 + i // 4, i % 4])
        p = ports[name]; x, y = p['xy_um']
        metal(ax, (x - 12, y - 12, x + 12, y + 12))
        ax.plot(x, y, 'o', mfc='none', mec=RED, ms=24, mew=2.1)
        ax.plot(x, y, '+', color=RED, ms=12, mew=1.4)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(name.upper() + ('  電源レール' if name in ('vdd', 'vss') else ''),
                     fontweight='bold', fontsize=15, pad=9)
        ax.set_xlabel(f"{p['layer']} · ({x:.1f}, {y:.1f}) µm", fontsize=12, labelpad=8)
    footer = fig.add_subplot(grid[3, :]); footer.axis('off')
    footer.text(.5, .35, '拡大図はすべて24 × 24 µm。座標・端子名はGDSと照合済み。パッド／フレームは未統合。',
                ha='center', va='center', color=INK, fontsize=11)
    fig.savefig(out / 'ishi_vga_pins.png', dpi=180, bbox_inches='tight', pad_inches=.18)
    plt.close(fig)
    return {'pins_checked_on_metal_and_labels': ports, 'zoom_window_um': [24, 24]}


def artwork(out):
    import klayout.lay as lay
    view = lay.LayoutView(); view.load_layout(str(out/'ishi_vga.gds'), 0)
    cv = view.cellview(0); cv.cell_index = cv.layout().cell('ishi_vga_core').cell_index()
    view.load_layer_props(str(ROOT/'tools/TR-1um/libs.tech/klayout/tech/TR-1um.lyp'), 0, True)
    view.set_config('background-color', '#ffffff'); view.set_config('grid-visible', 'false')
    view.max_hier(); view.zoom_fit(); view.save_image(str(out/'layout.png'), 1800, 1000)
    ly = db.Layout(); ly.read(str(out/'ishi_vga.gds')); top = ly.cell('ishi_vga_core')
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={'width_ratios': [1, 2.6]}, layout='constrained')
    for ax, bounds, title in zip(axes, [(20, 395, 170, 515), (-25, -10, 1790, 910)],
                                 ['Name and penguin · M1', 'Actual core metal · artwork at left center']):
        clip = db.Region(db.Box(*(round(v/ly.dbu) for v in bounds)))
        for layer, color in [(13, M1), (20, M2)]:
            region = db.Region(top.begin_shapes_rec(ly.layer(layer, 0))) & clip
            patches = [Polygon([(p.x*ly.dbu, p.y*ly.dbu) for p in part.each_point()])
                       for poly in region.each() for part in poly.decompose_trapezoids()]
            ax.add_collection(PatchCollection(patches, facecolor=color, edgecolor='none'))
        ax.set(xlim=(bounds[0], bounds[2]), ylim=(bounds[1], bounds[3]), xlabel='X [µm]', ylabel='Y [µm]', title=title)
        ax.set_aspect('equal'); ax.set_facecolor('#f5f7fa')
    axes[1].add_patch(Rectangle((40, 404.1), 108, 97.9, fill=False, edgecolor=RED, linewidth=1.4))
    fig.savefig(out/'silicon_art.png', dpi=180); plt.close(fig)


def blocks(out):
    fig, ax = plt.subplots(figsize=(16, 9.2), facecolor='white')
    fig.subplots_adjust(left=.015, right=.985, top=.97, bottom=.035)
    ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.set_aspect('equal'); ax.axis('off')

    def text(x, y, s, size=16, weight='normal', color=INK, ha='center'):
        ax.text(x, y, s, ha=ha, va='center', fontsize=size, weight=weight, color=color, linespacing=1.55)

    def box(x, y, w, h, face='#eff5fb', edge='#6b8ba7', lw=1.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=.12',
                                   facecolor=face, edgecolor=edge, linewidth=lw))

    def arrow(x1, y1, x2, y2, color=INK, lw=2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>',
                                    mutation_scale=18, lw=lw, color=color,
                                    shrinkA=0, shrinkB=1))

    text(.45, 8.6, 'ISHI VGA  |  回路ブロック図', 25, 'bold', ha='left')
    text(.45, 8.05, '座標からロゴと同期信号を生成し、フレームごとに発光状態を進める', 16, ha='left', color='#566b80')

    # Two clocked groups; combinational logic sits between them.
    box(.5, 2.15, 3.6, 4.2)
    text(2.3, 5.95, '走査カウンタ', 21, 'bold')
    box(.8, 4.45, 3, 1, face='white')
    text(2.3, 4.95, '水平 h：7 bit\n100クロック / 行', 16)
    arrow(2.3, 4.45, 2.3, 3.65)
    text(2.52, 4.06, '行末で縦を更新', 12, ha='left')
    box(.8, 2.65, 3, 1, face='white')
    text(2.3, 3.15, '垂直 v：10 bit\n525行 / フレーム', 16)

    # Single h/v coordinate bus, explicitly branching to the two functions.
    ax.plot([4.1, 4.9], [4.25, 4.25], color=INK, lw=2)
    ax.plot([4.9, 4.9], [3.15, 7.2], color=INK, lw=2)
    ax.plot(4.9, 4.25, 'o', color=INK, ms=5)
    arrow(4.9, 5.35, 5.7, 5.35); arrow(4.9, 3.15, 5.7, 3.15)
    text(4.52, 4.57, 'h, v', 15, 'bold')

    box(5.7, 6.7, 4.05, 1.0, face='#fbeff3', edge='#ad7d92')
    text(7.725, 7.2, '発光カウンタ phase：7 bit\nCLKで更新・フレーム末に加算', 14)
    arrow(4.9, 7.2, 5.7, 7.2)
    arrow(7.725, 6.7, 7.725, 6.2)

    box(5.7, 4.5, 4.05, 1.7, face='#f1f7f1', edge='#76977e')
    text(7.725, 5.65, 'ロゴ描画＋文字の発光', 19, 'bold')
    text(7.725, 5.05, 'I → S → H → I：各16フレーム\n発光なし：64フレーム（ROMなし）', 14)
    box(5.7, 2.3, 4.05, 1.7, face='#faf5e9', edge='#b59b5c')
    text(7.725, 3.46, '同期信号の判定', 20, 'bold')
    text(7.725, 2.83, '水平同期・垂直同期\nHSYNC / VSYNC は負極性', 14)

    box(10.75, 2.15, 2.9, 4.2)
    text(12.2, 5.98, '出力レジスタ', 18, 'bold')
    box(11.05, 4.68, 2.3, 1, face='white')
    text(12.2, 5.16, 'RGB：3 bit', 17, 'bold')
    box(11.05, 2.65, 2.3, 1, face='white')
    text(12.2, 3.15, '同期：2 bit', 17, 'bold')
    arrow(9.75, 5.18, 11.05, 5.18)
    arrow(9.75, 3.15, 11.05, 3.15)
    arrow(13.35, 5.18, 14.3, 5.18)
    arrow(13.35, 3.15, 14.3, 3.15)
    text(14.9, 5.6, 'R / G / B', 18, 'bold')
    text(14.9, 4.85, '各1 bit', 14)
    text(14.92, 3.65, 'HSYNC\nVSYNC', 17, 'bold')

    # Shared CLK enters both clocked groups without crossing any data wires.
    clock = '#1675bd'
    text(.55, .82, '外部CLK\n3.15 MHz', 16, 'bold', clock, ha='left')
    ax.plot([.55, 12.2], [1.15, 1.15], color=clock, lw=2.4)
    arrow(2.3, 1.15, 2.3, 2.15, clock, 2.4)
    arrow(12.2, 1.15, 12.2, 2.15, clock, 2.4)
    ax.plot(2.3, 1.15, 'o', color=clock, ms=5)
    text(7.35, 1.43, 'BUFTH → 4分岐バッファ → 各行のFF', 12, color=clock)
    text(8, .28, '640 × 480 / 60 Hz相当     •     RGB111     •     RESETなし・リング発振器なし', 14, color='#566b80')
    fig.savefig(out / 'ishi_vga_blocks.svg', bbox_inches='tight', pad_inches=.16,
                metadata={'Date': None, 'Creator': 'ISHI VGA submission_figures.py'})
    fig.savefig(out / 'ishi_vga_blocks.png', dpi=180, bbox_inches='tight', pad_inches=.16)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--directory', default='submission')
    a = ap.parse_args(); out = (ROOT / a.directory).resolve()
    assert out.is_dir() and out.is_relative_to(ROOT)
    fonts(); report = pins(out); blocks(out); artwork(out)
    report.update({'gds_sha256': sha(out / 'ishi_vga.gds'), 'ports_sha256': sha(out / 'ports.json'),
                   'circuit_modified': False, 'script_sha256': sha(Path(__file__)),
                   'image_role': 'GDS pin-location illustration and explanatory RTL block diagram',
                   'matplotlib_version': matplotlib.__version__, 'klayout_version': db.__version__,
                   'images': {name: sha(out / name) for name in ['ishi_vga_pins.png', 'ishi_vga_blocks.svg', 'ishi_vga_blocks.png', 'layout.png', 'silicon_art.png']}})
    (out / 'verification/figures.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Rendered actual-metal pin overview + 8 close-ups and readable block diagram')


if __name__ == '__main__':
    main()
