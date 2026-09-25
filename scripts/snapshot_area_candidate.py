#!/usr/bin/env python3
"""Freeze exact evidence for an area candidate without changing the root design."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('logical')
    ap.add_argument('physical')
    a = ap.parse_args()
    assert '/' not in a.logical and '/' not in a.physical
    logical = ROOT/'experiments'/a.logical
    physical = ROOT/'experiments'/a.physical
    verification = logical/'build/verification.json'
    if not verification.exists():
        verification = logical/'build/metrics.json'
    checks = json.loads(verification.read_text())
    assert len(checks['checks']) == 4 and all(c['result'] == 'PASS' for c in checks['checks'])
    for name, expected in checks['sha256'].items():
        assert digest(ROOT/name) == expected, f'Stale evidence: {name}'
    net = logical/'out/ishi_vga_core_pnr.v'
    assert digest(net) == digest(physical/'out/ishi_vga_core_pnr.v')
    dest = ROOT/'docs/area_search/selected'
    dest.mkdir(parents=True, exist_ok=True)
    sources = {
        'ishi_vga_core.v': logical/'ishi_vga_core.v',
        'ishi_logo.v': logical/'ishi_logo.v',
        'synthesis_config.py': logical/'config.py',
        'physical_config.py': physical/'config.py',
        'ishi_vga_core_pnr.v': net,
        'verification.json': verification,
        'verification.log': logical/'build/verification.log',
        'SYN_RESULTS.txt': logical/'out/SYN_RESULTS.txt',
        'STA.txt': logical/'out/STA_ishi_vga_core.txt',
        'physical_report.json': physical/'build/physical_report.json',
        'source_manifest.json': physical/'source_manifest.json',
        'route_step6.log': physical/'build/route_step6.log',
        'diagnostic_compaction.log': physical/'build/diagnostic_compaction.log',
    }
    for optional in ['route_step7.log', 'postrepair_compaction.log',
                     'postrepair_connectivity.log', 'postrepair_simple_drc.log']:
        if (physical/'build'/optional).exists():
            sources[optional] = physical/'build'/optional
    for name, path in sources.items():
        shutil.copyfile(path, dest/name)
    # Render actual simulator bytes, not the preview/reference PNG.
    frame = next((logical/'build').glob('gates_6.3*.hex'))
    assert frame.read_bytes() == (ROOT/'tests/expected_frame.hex').read_bytes()
    data = np.array([int(x,16) for x in frame.read_text().split()], dtype=np.uint8)
    active = data.reshape(525,200)[:480,:160]
    rgb = np.stack([((active>>4)&3)*85,((active>>2)&3)*85,(active&3)*85], axis=-1)
    Image.fromarray(np.repeat(rgb,4,axis=1)).save(dest/'gates_630.png')
    gds = physical/'build/diagnostic_compacted.gds'
    manifest = {'logical':str(logical.relative_to(ROOT)), 'physical':str(physical.relative_to(ROOT)),
        'diagnostic_gds':str(gds.relative_to(ROOT)), 'diagnostic_gds_sha256':digest(gds),
        'original_sources':{name:str(path.relative_to(ROOT)) for name,path in sources.items()},
        'sha256':{name:digest(dest/name) for name in sources},
        'toolchain_lock_sha256':digest(ROOT/'toolchain.lock.json'),
        'limitations':'Diagnostic GDS, including a bounded repair attempt if recorded; remaining shorts. Not a tapeout result. Root RTL/config remain the baseline.'}
    repaired = physical/'build/postrepair_compacted.gds'
    if repaired.exists():
        manifest['postrepair_gds'] = str(repaired.relative_to(ROOT))
        manifest['postrepair_gds_sha256'] = digest(repaired)
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (dest/'README.md').write_text('# 面積探索の選択候補の証拠\n\n'
        '後続の[実セル端子による監査と配線試験](../../ROUTING_AND_POLY.md)で、配線端点表による接続検査の限界を確認した。保存版の接続ログは当時の診断値で、完全な実端子接続の証明ではない。\n\n'
        'このディレクトリは監査用スナップショット。実行時の入口は manifest.json に記録した experiments ディレクトリ。\n'
        'gates_630.png は候補の最終ネットリストのシミュレータ出力から復元した画像。\n'
        'GDSは接続問題が残る診断用で、公式DRC/LVS合格やテープアウト可能という意味ではない。\n'
        'route_step7.logは部分取得ログ（欠落と要約を含む）。postrepair_connectivity.log / postrepair_simple_drc.logは修正・圧縮後GDSを独立に再検査した完全な出力。\n')
    print(dest.relative_to(ROOT))


if __name__ == '__main__':
    main()
