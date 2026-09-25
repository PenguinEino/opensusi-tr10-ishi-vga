# 再現の範囲と前提

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
.venv/bin/python scripts/run_apr.py --design-root designs/grid_power apr/drc_pdk.py \
  ../../src/ishi_vga_grid_power.gds ishi_vga_core -r build/recheck.lyrdb --mdp
.venv/bin/python scripts/run_apr.py --design-root designs/grid_power apr/lvs_pdk.py \
  ../../src/ishi_vga_grid_power.gds ishi_vga_core --sch ../../src/ishi_vga_core.spice \
  -r build/recheck.lvsdb
```

描画DRCとマスクDRCは別の結果。Floating SG 1件を無視してマスクDRC-cleanとは扱わない。
