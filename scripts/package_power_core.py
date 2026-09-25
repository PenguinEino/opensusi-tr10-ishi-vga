#!/usr/bin/env python3
"""Assemble a reviewable core handoff, preserving old variants and checkpoints."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from check_toolchain import ROOT, verify


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    verify()
    release=ROOT/'release/ishi_vga_grid_power_core'
    assert not release.exists(), 'Never overwrite a released bundle'
    physical=ROOT/'experiments/a_power_escape/build/verification.json'
    v=json.loads(physical.read_text())
    assert v['status']=='ACCEPTED' and v['strict_lvs']=='PASS' and v['drawing_drc']==0
    assert v['size_um'][0]<=1800 and v['size_um'][1]<=900
    assert all(sha(ROOT/p)==h for p,h in v['hashes'].items())
    functional=ROOT/'designs/grid_power/build/functional_verification.json'
    f=json.loads(functional.read_text());assert f['status']=='PASS'
    assert all(sha(ROOT/p)==h for p,h in f['hashes'].items())
    replay=ROOT/'build/power_core_replay/replay.json';r=json.loads(replay.read_text())
    assert r['status']=='PASS' and r['final_gds_sha256']==v['candidate_sha256']
    preserved=[]
    for name in ['core_escape_snapshot','core_routing_snapshot','half_slot_results','half_a_results','metal_logo_results']:
        p=ROOT/'docs'/f'{name}.json';d=json.loads(p.read_text())
        assert all(sha(ROOT/pp)==hh for pp,hh in d['files'].items()),name
        preserved.append({'snapshot':str(p.relative_to(ROOT)),'file_count':len(d['files']),'unchanged':True})
    release.mkdir(parents=True);copies={}
    def copy(source,destination=None):
        src=ROOT/source;dst=release/(destination or source)
        assert src.is_file(),str(src)
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
        copies[str(dst.relative_to(release))]={'source':source,'sha256':sha(src)}
    copy('experiments/a_power_escape/build/candidate.gds','src/ishi_vga_grid_power.gds')
    copy('experiments/a_power_flex4/build/ishi_vga_core.spice','src/ishi_vga_core.spice')
    for p in ['ishi_vga_core.v','ishi_logo.v','config.py','out/ishi_vga_core_pnr.v',
              'tests/tb_rtl.v','tests/tb_gates.v','tests/expected_frame.hex',
              'build/tr1um_cells.v','build/reference.png','build/functional_verification.json','build/rtl.log','build/gates.log']:
        copy('designs/grid_power/'+p)
    # lef_parser resolves config at cwd even when a downstream tool receives
    # --design-root. Supply an explicit adopted root config in the standalone
    # archive rather than relying on the workspace's preserved old-B config.
    cfg=(ROOT/'designs/grid_power/config.py').read_text()
    cfg=cfg.replace("SYN_RTL = ['ishi_vga_core.v', 'ishi_logo.v']",
                    "SYN_RTL = ['designs/grid_power/ishi_vga_core.v', 'designs/grid_power/ishi_logo.v']")
    cfg=cfg.replace("SYN_TB_RTL = ['tests/tb_rtl.v']", "SYN_TB_RTL = ['designs/grid_power/tests/tb_rtl.v']")
    cfg=cfg.replace("SYN_TB_NET = ['tests/tb_gates.v']", "SYN_TB_NET = ['designs/grid_power/tests/tb_gates.v']")
    cfg=cfg.replace('finalize(globals())',
                    "NET_PATH = os.path.join(ROOT, 'designs/grid_power/out/ishi_vga_core_pnr.v')\nfinalize(globals())")
    (release/'config.py').write_text(cfg)
    for name in ['check_toolchain.py','run_apr.py','apply_toolchain_patches.py',
                 'maze_route.py','power_maze_route.py','maze_grid.cpp','label_power_ports.py',
                 'prune_route_vias.py','validate_route_candidate.py','poly_core_trial.py',
                 'route_core_escape.py','routing_diagnostics.py','verify_power_core.py',
                 'replay_power_core.py','test_power_core.py','package_power_core.py',
                 'a_row_placement.py','row_anneal.cpp','power_layout_search.py']:
        copy('scripts/'+name)
    for name in ['toolchain.lock.json','requirements.txt','patches/aprtools-pcell-technology.patch',
                 'docs/POWER_GRID_IMPLEMENTATION.md','docs/APRTOOLS_ADOPTION.md','docs/PIN_PLAN.md']:
        copy(name)
    for name in ['a_power_fix066','a_power_fix172eq','a_power_labels','a_power_escape']:
        copy(f'experiments/{name}/config.py')
        # Preserve the selected physical evidence, excluding bulky search grids.
        for p in (ROOT/'experiments'/name/'build').glob('*'):
            if p.is_file() and p.suffix in ('.json','.gds','.log','.lyrdb','.lvsdb'):
                copy(str(p.relative_to(ROOT)))
        audit=ROOT/'experiments'/name/'build/audit'
        for fn in ['metal_connectivity.json','actual_pin_map.json']:
            if (audit/fn).is_file():copy(str((audit/fn).relative_to(ROOT)))
    for p in ['config.py','source_manifest.json','ishi_logo.v','ishi_vga_core.v',
              'out/ishi_vga_core_pnr.v','tests/expected_frame.hex','layout/placement.json','layout/row_assignment.json',
              'build/diagnostic_compacted.gds','build/diagnostic_shapes.json','build/diagnostic_pins.json',
              'build/audit/actual_pin_map.json','build/audit/metal_connectivity.json',
              'build/ishi_vga_core.spice','build/reference.log','build/sta.log','out/STA_ishi_vga_core.txt',
              'build/row_graph.txt','build/assignment.txt','build/row_optimization.json',
              'build/drawing.lyrdb','build/diagnostic_compacted_mdp.lyrdb','build/drc.log']:
        copy('experiments/a_power_flex4/'+p)
    for p in (ROOT/'experiments/a_power_flex4/layout/step4').glob('*'):
        if p.is_file():copy(str(p.relative_to(ROOT)))
    for p in ['ishi_logo.v','ishi_vga_core.v','out/ishi_vga_core_pnr.v','tests/expected_frame.hex',
              'tests/tb_rtl.v','tests/tb_gates.v','build/tr1um_cells.v','build/verification.json']:
        copy('experiments/a_metal_g_power/'+p)
    copy('build/power_core_replay/replay.json','reports/replay.json')
    copy('build/power_core_replay/a_power_escape/build/verification.json','reports/replay_verification.json')
    portable=ROOT/'build/power_bundle_check02/ishi_vga_grid_power_core/build/portable_replay'
    pr=json.loads((portable/'replay.json').read_text())
    assert pr['status']=='PASS' and pr['final_gds_sha256']==v['candidate_sha256']
    copy(str((portable/'replay.json').relative_to(ROOT)),'reports/portable_replay.json')
    copy(str((portable/'a_power_escape/build/verification.json').relative_to(ROOT)),
         'reports/portable_replay_verification.json')
    copy('docs/POWER_GRID_IMPLEMENTATION.md','README.md')
    # README links are repository-relative in the original; provide direct
    # package entry paths first so the archive is self-explanatory.
    intro='''# ISHI VGA 格子＋電源枝5本：コア引き渡しセット

入口は `src/ishi_vga_grid_power.gds`（top: `ishi_vga_core`）。
**1792.8×897.2 µm、描画DRC 0、strict LVS PASS。フレーム未統合。**
CLKは3.15 MHz、RGB111、RESETなし。共通VSSを除きVDD込み7端子。
CLK入力のFloating SGマスク警告1件は未解消として添付。

- `ports.json`：実GDS座標・層・方向。パッケージ番号は未割当。
- `src/ishi_vga_core.spice`：配置と論理ネットリストから作った独立LVS参照。
- `designs/grid_power/`：現行RTL、config、最終ゲート回路、参照画像、機能試験。
- `experiments/a_power_escape/build/verification.json`：最終の接続・寸法・DRC・LVS検証。
- 同ディレクトリの `drawing.lyrdb`、`candidate_mdp.lyrdb`、`core.lvsdb`：公式結果。
- `experiments/a_power_flex4/build/sta.log`：配線寄生を含まないSTA。配線後保証ではない。
- `manifest.json`、`SHA256SUMS`：全同梱ファイルのハッシュと検証範囲。
- `REPRODUCE.md`：保存したAPRチェックポイントから最終GDSまでの再現手順。

フレーム／パッド／ESD接続、最終チップDRC・MDP・LVS、実機動作はこのセットの範囲外。
詳しい実装記録は `docs/POWER_GRID_IMPLEMENTATION.md`。そこにある相対リンクは元ワークスペース基準。
'''
    (release/'README.md').write_text(intro)
    copies['README.md']={'source':'package description','sha256':sha(release/'README.md')}
    ports=[{'name':p['net'],'direction':'input' if p['net']=='clk' else 'output',
            'layer':p['layer'],'xy_um':p['xy_um'],'edge':p['edge']} for p in v['ports']]
    ports += [{'name':'vdd','direction':'power','layer':'M1','xy_um':[2.7,132.0],'edge':'rail label'},
              {'name':'vss','direction':'ground','layer':'M1','xy_um':[2.7,77.3],'edge':'rail label'}]
    (release/'ports.json').write_text(json.dumps({'top':'ishi_vga_core','bbox_um':v['bbox_um'],
        'size_um':v['size_um'],'clock_hz':3150000,'signal_ports':6,'including_vdd_excluding_vss':7,
        'package_pad_numbers':None,'ports':ports},indent=2)+'\n')
    (release/'REPRODUCE.md').write_text('''# 再現の範囲と前提

保存した `experiments/a_power_flex4/build/diagnostic_compacted.gds` を開始点にする。
配置探索を初めから繰り返すものではない。修復→注記→6信号引き出しの4段階は
元ワークスペースで再実行し、各GDSのバイト単位一致と最終DRC/LVSを確認済み。

必要な依存は `toolchain.lock.json` の固定Git checkout。パスは
`tools/APRtools` と `tools/TR-1um`。それぞれ記録されたorigin URLとcommitを使い、
`scripts/apply_toolchain_patches.py` で記録済みPCellパッチだけを適用する。
古い版のライブラリや個人のPDKへのフォールバックは行わない。
Python環境 `.venv/bin/python` はklayout 0.30.6とnumpy、Pillowを含む。
KLayout CLIは0.30.9、C++コンパイラはg++、Icarus Verilogは12.0を使用した。
機能試験は `.tools/bin/iverilog` と `.tools/bin/vvp` を使う。
外部依存・実行バイナリはこのアーカイブに含めていない。

セットのルートで実行する。既存の検証済みデータは上書きしない。

```sh
python3 scripts/check_toolchain.py
sha256sum -c SHA256SUMS
.venv/bin/python scripts/test_power_core.py
.venv/bin/python scripts/replay_power_core.py --out build/new_replay
```

同梱GDSの再DRC/LVSだけなら、固定依存を用意したうえで以下を実行できる。

```sh
.venv/bin/python scripts/run_apr.py --design-root designs/grid_power apr/drc_pdk.py \\
  ../../src/ishi_vga_grid_power.gds ishi_vga_core -r build/recheck.lyrdb --mdp
.venv/bin/python scripts/run_apr.py --design-root designs/grid_power apr/lvs_pdk.py \\
  ../../src/ishi_vga_grid_power.gds ishi_vga_core --sch ../../src/ishi_vga_core.spice \\
  -r build/recheck.lvsdb
```

描画DRCとマスクDRCは別の結果。Floating SG 1件を無視してマスクDRC-cleanとは扱わない。
''')
    manifest={'status':'CORE_HANDOFF_READY_FRAME_INTEGRATION_PENDING','gds_sha256':v['candidate_sha256'],
              'size_um':v['size_um'],'bbox_um':v['bbox_um'],'terminals_excluding_vss':7,
              'clock_hz':3150000,'artwork':'g_power','physical_status':v['status'],
              'drawing_drc':0,'mdp_warnings':1,'strict_lvs':'PASS','functional_tests':'PASS',
              'exact_gds_replay':'PASS','extracted_bundle_replay':'PASS',
              'portable_test_scope':'separate extracted directory; same pinned dependency checkouts and EDA binaries',
              'preserved_prior_artifacts':preserved,
              'limitations':v['limitations'],'copies':copies}
    manifest['files']={str(p.relative_to(release)):sha(p) for p in sorted(release.rglob('*')) if p.is_file()}
    (release/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    all_files={str(p.relative_to(release)):sha(p) for p in sorted(release.rglob('*')) if p.is_file()}
    (release/'SHA256SUMS').write_text(''.join(f'{h}  {p}\n' for p,h in all_files.items()))
    archive=release.with_suffix('.tar.gz')
    with tarfile.open(archive,'w:gz') as tar:tar.add(release,arcname=release.name)
    (archive.with_name(archive.name+'.sha256')).write_text(f'{sha(archive)}  {archive.name}\n')
    alias=ROOT/'build/ishi_vga_grid_power_core.gds'
    assert not alias.exists();alias.symlink_to('../release/ishi_vga_grid_power_core/src/ishi_vga_grid_power.gds')
    result={'directory':str(release.relative_to(ROOT)),'archive':str(archive.relative_to(ROOT)),
            'archive_sha256':sha(archive),'gds_sha256':v['candidate_sha256'],'size_um':v['size_um'],
            'file_count':len(all_files)+1,'preserved':preserved}
    (ROOT/'docs/power_grid_release.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
