# 再検証

このフォルダ単体でハッシュ検査、RTL／ゲート試験、保存したngspice波形の再判定・過渡解析の再実行ができます。

```sh
python3 tools/verify_bundle.py
python3 tools/run_letter_tests.py saved-spice
python3 tools/run_letter_tests.py rtl-gates --out ../letter_rtl_gate_recheck
python3 tools/run_letter_tests.py spice --case phase_127 --out ../letter_spice_recheck
```

新しい結果は提出フォルダ外の未作成ディレクトリへ保存します。SPICEの `--case` を省くと20試験すべてを実行します。Python 3＋NumPy、Icarus Verilog、ngspiceを使用します。提出時のngspiceは46+です。

回路は `simulation/core_sim.spice`、固定PDKモデルは `simulation/models/`、各刺激は `simulation/<試験名>/tb.spice` です。`wave.raw.gz` は実行したngspiceの生波形をgzipで保存したもので、再判定器が展開して各サンプルの状態24 bitと出力5 bitを照合します。

## GDSの再生成

リポジトリ全体を取得し、固定したサブモジュールを初期化します。

```sh
git submodule update --init --recursive
python3 scripts/apply_toolchain_patches.py
python3 scripts/check_toolchain.py
# .venv / .tools が未準備の場合（Ubuntu 24.04 arm64向け）
make setup
.venv/bin/python scripts/replay_letter_animation_core.py --out build/letter_recheck
.venv/bin/python scripts/verify_letter_animation_core.py --design-root build/letter_recheck
.venv/bin/python scripts/review_letter_submission.py --out build/letter_recheck/state_audit.json
# 装飾の追加・DRC/LVS/抽出は SILICON_ART.md の手順を実行後
.venv/bin/python scripts/letter_spice_check.py --design-root experiments/letter_art_spice
```

`replay_letter_animation_core.py` は装飾前コアを再現します。最終提出GDSには [SILICON_ART.md](SILICON_ART.md) の装飾工程を続けて実行してください。

`make setup` のビルド依存はリポジトリの `docs/IMPLEMENTATION.md` に記載しています。KLayoutのCLI（今回0.30.9）とngspiceは別途必要です。配線探索の中間ファイルだけで約1 GiBを使用します。ルートの `make synth`／`make test`／`make sta` は旧比較設計の入口で、現行アニメーションの検証には上記コマンドを使います。

`tools/APRtools`、`tools/TR-1um` の版は `toolchain.lock.json` に固定されています。`reproduce/static_*` は配置配線を再現するための固定入力で、提出対象のGDSはルートの `ishi_vga.gds` です。

図版は実GDSから `scripts/submission_figures.py` で生成しています。実機GIF／MP4は `scripts/make_demo_media.py` が入力動画を表示方向に解釈した後、90度左に回転したものです。元動画の名前・SHA256・変換内容は `fpga_demo.json` に記録しています。

`reproduce/` の梱包・図版スクリプトはリポジトリ全体から使います。提出フォルダ単独の入口は `tools/` です。
