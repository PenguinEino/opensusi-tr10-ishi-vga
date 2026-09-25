#!/usr/bin/env python3
"""Summarize measured trials; incomplete flows never count as final mapped results."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/area_search'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect():
    rows = []
    for d in sorted((ROOT/'experiments').iterdir()):
        if not d.is_dir():
            continue
        logpath = d/'out/SYN_RESULTS.txt'
        # map_* uses a deliberately separate experimental frontend.
        if not logpath.exists() and d.name.startswith('map_'):
            logpath = d/'build/synthesis.log'
        if not logpath.exists():
            continue
        log = logpath.read_text(errors='replace')
        stats = re.findall(r'ishi_vga_core\s+(\d+) セル.*?([\d,]+) um2', log)
        if not stats:
            continue
        cells, area = stats[-1]
        net = d/'out/ishi_vga_core_pnr.v'
        r = {'name':d.name, 'last_report_cells':int(cells),
             'last_report_area_um2':int(area.replace(',', '')),
             'has_final_netlist':net.exists(), 'log':str(logpath.relative_to(ROOT)),
             'netlist_sha256':sha(net) if net.exists() else None,
             'complete_four_checks':False, 'evidence':[]}
        for p in [d/'build/metrics.json', d/'build/verification.json', d/'result.json']:
            if not p.exists():
                continue
            data = json.loads(p.read_text())
            checks = data.get('checks', [])
            hashes = data.get('sha256', {})
            current = bool(hashes) and all((ROOT/f).exists() and sha(ROOT/f) == h for f,h in hashes.items())
            r['complete_four_checks'] |= current and len(checks) == 4 and all(c.get('result') == 'PASS' for c in checks)
            if hashes and not current:
                r.setdefault('stale_evidence', []).append(str(p.relative_to(ROOT)))
            r['evidence'].append(str(p.relative_to(ROOT)))
        # Upstream RTL and post-merge tests are distinct from final PNR tests.
        r['upstream_completed'] = '完了' in log and net.exists()
        r['blocked_existing_bufth'] = '既に BUFTH が入っている' in log
        if not net.exists():
            r['warning'] = 'Last reported area is an intermediate netlist, NOT a completed candidate.'
        rows.append(r)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = collect()
    result = {'baseline_cells':375, 'baseline_cell_area_um2':495252,
              'baseline_raw_compacted_bbox_um':[1611, 2905],
              'limitations':'Cell area excludes routing/TAP/FILL/frame/ring. Physical trial GDS is diagnostic until connectivity, official DRC/LVS and timing pass.',
              'trials':rows}
    (OUT/'synthesis_trials.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    lines = ['# 合成試験一覧', '',
             '自動集計。面積はセルのみ。最終ネットリストが無い行は上流フロー途中の値であり、採用候補と比較しない。',
             '全4条件はRTLと最終ネットリストそれぞれの6.30/6.45 MHz試験。物理検証の合否とは別。', '',
             '|案|セル数|セル面積 µm²|最終net|全4条件の記録|',
             '|---|---:|---:|---|---|']
    for r in sorted(rows, key=lambda x:(not x['has_final_netlist'], x['last_report_area_um2'])):
        lines.append(f"|{r['name']}|{r['last_report_cells']}|{r['last_report_area_um2']:,}|{'有' if r['has_final_netlist'] else '未完了'}|{'PASS' if r['complete_four_checks'] else '別ログ確認/未実施'}|")
    (OUT/'SYNTHESIS_TRIALS.md').write_text('\n'.join(lines)+'\n')
    print(f'{len(rows)} synthesis trials collected to {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
