#!/usr/bin/env python3
"""Archive the design-owned clock ECO plus unchanged pinned-input checkpoint."""
import gzip
import hashlib
import io
from pathlib import Path
import tarfile
from check_toolchain import ROOT, verify


def main():
    verify();files={}
    def add(p): files[str(p.relative_to(ROOT))]=p.read_bytes()
    scripts=['clock_tree_eco.py','replay_clock_core.py','replay_power_core.py','poly_core_trial.py','prune_route_vias.py','validate_route_candidate.py','routing_diagnostics.py','maze_grid.cpp','run_apr.py','sta_guard.py','sta_guard.tcl','test_sta_guard.py','check_toolchain.py','apply_toolchain_patches.py','setup_python.sh','setup_local_eda.py','setup_sta.py']
    for f in scripts:add(ROOT/'scripts'/f)
    for p in (ROOT/'release/ishi_vga_grid_power_core').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:add(p)
    for f in ['toolchain.lock.json','config.py','docs/APRTOOLS_ADOPTION.md']:add(ROOT/f)
    for f in ['config.py','clock_electrical.tcl','clock_report.tcl']:add(ROOT/'experiments/a_clock_tree'/f)
    add(ROOT/'designs/grid_power/out/ishi_vga_core_pnr.v')
    # apply_toolchain_patches uses design-owned patch file recorded in the lock.
    for p in (ROOT/'patches').rglob('*'):
        if p.is_file():add(p)
    files['REPRODUCE.md']='''# クロックECO再現

これは製造レビュー対応後の現行再現セットです。内部の release/ishi_vga_grid_power_core は旧GDSの凍結入力で、そこへ移動して旧スクリプトを実行する手順ではありません。

このセットのルートに tools/APRtools と tools/TR-1um を用意し、toolchain.lock.json のURL・コミットへcheckoutしてください。APRtools 8f6962bf2df1618d633f8a81c230fec895fc83aa、PDK f408d3b5c23a8ebe44f02b0482a9270601e2880f。記録済みPCell lookup patchのみを scripts/apply_toolchain_patches.py で適用します。

`.venv/bin/python` にKLayout 0.30.6とnumpy、Pillow、KLayout CLI 0.30.9、g++、OpenSTA 2.6.0が必要です。元環境では `.tools/bin` に実行ファイルを用意しました。ツール自体は同梱しません。別版やローカルPDKへの自動代替はしません。

```sh
sha256sum -c SHA256SUMS
python3 scripts/check_toolchain.py
.venv/bin/python scripts/replay_clock_core.py --out build/new_clock_replay
.venv/bin/python scripts/test_sta_guard.py --out build/new_sta_controls
```

旧コアからFILL3を4個のBUF_X2へ交換し、DFFのクロック接続と配線を更新します。GDS SHA256 299b3203897dd4dffca7fb1a260a68dbd577c4ac4f98fb105cfe9e8579cf650c の一致を必須とし、公式DRC/MDP/strict LVSとguard付きSTAを新規実行します。描画DRC0、MDP Floating SG1は別々に判定します。

配線RC、フレーム、PVTの合格を意味しません。RTL／ゲート全状態・SPICEの再試験は、提出フォルダ側のREPRODUCE.mdを使います。保存入力やログを上書きせず新しい出力ディレクトリを指定してください。
'''.encode()
    files['SHA256SUMS']=''.join(hashlib.sha256(b).hexdigest()+'  '+n+'\n' for n,b in sorted(files.items())).encode()
    dest=ROOT/'release/ishi_vga_clock_eco_reproduce.tar.gz'
    with dest.open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='') as gz,tarfile.open(fileobj=gz,mode='w') as tar:
        for name,body in sorted(files.items()):
            info=tarfile.TarInfo('ishi_vga_clock_eco/'+name);info.size=len(body);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(body))
    print(dest,len(files),'files',hashlib.sha256(dest.read_bytes()).hexdigest())


if __name__=='__main__':main()
