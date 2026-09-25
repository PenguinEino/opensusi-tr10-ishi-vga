#!/usr/bin/env python3
"""Collect observed A results and bind evidence; never infers a DRC/LVS pass."""
import hashlib
import json
import re
from collections import Counter
import xml.etree.ElementTree as ET
from pathlib import Path
import klayout.db as kdb

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    trials, physical, files = [], [], {}
    for d in sorted((ROOT / 'experiments').glob('a_*')):
        manifest = d / 'source_manifest.json'
        if not manifest.exists():
            continue
        data = json.loads(manifest.read_text())
        for path, expected in data['sha256'].items():
            assert sha(ROOT / path) == expected, path
        files[str(manifest.relative_to(ROOT))] = sha(manifest)
        for name in ['build/synthesis.log', 'build/verification.json', 'out/STA_ishi_vga_core.txt',
                     'build/drawing.lyrdb', 'build/drc.log', 'build/audit/metal_connectivity.json']:
            p = d / name
            if p.exists(): files[str(p.relative_to(ROOT))] = sha(p)
        log = d / 'build/synthesis.log'
        if log.exists():
            text = log.read_text()
            item = {'name': d.name, 'log': str(log.relative_to(ROOT)), 'complete': text.rstrip().endswith('完了'),
                    'upstream_630_pass_count': text.count('PASS: 315017 pixel ticks')}
            m = re.search(r'合計\s+(\d+)\s+([\d,]+) um2', text)
            if m:
                item.update(cells=int(m[1]), cell_area_um2=int(m[2].replace(',', '')))
            m = re.search(r'セル幅の総和 ([\d,]+) um', text)
            if m: item['cell_width_sum_um_rounded'] = int(m[1].replace(',', ''))
            if not item['complete']:
                item['failure'] = 'ABC emitted BUFTH internally; pinned insert_bufth.py rejected an existing BUFTH. No workaround adopted.'
            trials.append(item)
        gds = d / 'build/diagnostic_compacted.gds'
        if gds.exists():
            ly = kdb.Layout(); ly.read(str(gds)); b = ly.cell('ishi_vga_core').dbbox()
            row = {'name': d.name, 'width_um': round(b.width(), 3), 'height_um': round(b.height(), 3),
                   'bbox_um': [round(v, 3) for v in [b.left, b.bottom, b.right, b.top]],
                   'gds': str(gds.relative_to(ROOT)), 'gds_sha256': sha(gds), 'status': 'DIAGNOSTIC_ONLY'}
            report = d / 'build/physical_report.json'
            if report.exists():
                details = json.loads(report.read_text())
                row.update(source=details['source_manifest']['source'],
                           settings=details['source_manifest']['physical'],
                           channel_crossings=details.get('channel_crossings'))
            else:
                row.update(source=data['source'], settings={'rows': 6, 'seed': 4, 'prl': 10, 'pad_weight': 1})
            physical.append(row)
            for name in ['config.py', 'build/diagnostic_compaction.log', 'build/route_step6.log',
                         'build/diagnostic_compacted.gds', 'layout/placement.json', 'out/ishi_vga_core_pnr.v']:
                p = d / name
                files[str(p.relative_to(ROOT))] = sha(p)
    complete = [t for t in trials if t['complete']]
    assert all(t['upstream_630_pass_count'] == 2 for t in complete)
    best_logic = min(complete, key=lambda t: t['cell_area_um2'])
    best_physical = min(physical, key=lambda t: t['width_um'] * t['height_um'])
    selected = ROOT / 'experiments' / best_physical['name']
    audit = json.loads((selected / 'build/audit/metal_connectivity.json').read_text())
    drc_items = ET.parse(selected / 'build/drawing.lyrdb').getroot().findall('./items/item')
    validation = {'actual_signal_pins': audit['actual_pin_shapes_labeled'],
                  'missing_actual_pins': audit['missing_actual_pin_count'],
                  'open_signal_nets': audit['open_net_count'],
                  'shorted_components': audit['actual_short_component_count'],
                  'transitive_short_net_pairs': audit['actual_short_net_pair_count'],
                  'drawing_drc_items': len(drc_items),
                  'drawing_drc_categories': dict(Counter(i.findtext('category') for i in drc_items)),
                  'lvs': 'NOT_RUN', 'mdp': 'NOT_RUN', 'post_route_timing': 'NOT_RUN'}
    for path in [Path(__file__), ROOT / 'toolchain.lock.json', ROOT / 'assets/logo_rectangles_a_corrected.json']:
        files[str(path.relative_to(ROOT))] = sha(path)
    b_checks = []
    for name in ['core_escape_snapshot.json', 'core_routing_snapshot.json']:
        data = json.loads((ROOT / 'docs' / name).read_text())
        for p, expected in data['files'].items(): assert sha(ROOT / p) == expected, p
        b_checks.append({'snapshot': name, 'files': len(data['files']), 'unchanged': True})
    result = {'date': '2026-09-25', 'scope': 'corrected A core fit trial; integration paused; no ring oscillator',
              'synthesis_trials': trials, 'physical_trials': physical, 'minimum_cell_area': best_logic,
              'minimum_routed_bbox': best_physical, 'b_artifacts_unchanged': b_checks, 'files': files,
              'best_physical_validation': validation,
              'limitations': 'No A geometry fits 1800um square. Shorted diagnostic routes; no final A LVS, MDP, or post-route timing. Upstream STA load remains GIO OUT capacitance, not analog pad/board signoff.'}
    report_dir = ROOT / 'docs/a_trials'
    report_dir.mkdir(exist_ok=True)
    (report_dir / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    rows = ['# 訂正A案の合成・配置配線の比較', '',
            '同一の37矩形・RGB222・走査タイミングを維持。セル面積はTAP/FILL・配線を含まない。', '',
            '|構成|最終セル数|セル面積 µm²|状態|', '|---|---:|---:|---|']
    for t in sorted(trials, key=lambda x: x.get('cell_area_um2', 1e20)):
        rows.append(f"|{t['name']}|{t.get('cells','—')}|{t.get('cell_area_um2','—')}|{'合成完了' if t['complete'] else 'BUFTH挿入前で停止'}|")
    rows.extend(['', f'合成完了{len(complete)}構成は上流のRTL／merged-netlist試験を6.30 MHzで各315,017tick通過。',
                 '最終BUFTH挿入後を6.30/6.45 MHzの双方で照合した対象は `a_group_y` と `a_h63_v500_x`。',
                 '他の候補まで同じ検証範囲とは扱わない。', '',
                 '|配置配線試験|幅 µm|高さ µm|1800角|', '|---|---:|---:|---|'])
    for t in sorted(physical, key=lambda x: x['height_um']):
        rows.append(f"|{t['name']}|{t['width_um']}|{t['height_um']}|未達|")
    rows.extend(['', '全てstep6配線→未使用チャネル圧縮の診断GDS。短絡修復・定数電源接続・外周端子引き出し・フレーム統合前。',
                 '詳細と各ファイルのSHA256は [results.json](results.json)。公式検証の結果は [A_RETRY.md](../A_RETRY.md)。', ''])
    (report_dir / 'README.md').write_text('\n'.join(rows))
    print(json.dumps({'syntheses': len(trials), 'completed': len(complete), 'physical': len(physical),
                      'best_logic': best_logic['name'], 'best_physical': best_physical}, indent=2))


if __name__ == '__main__': main()
