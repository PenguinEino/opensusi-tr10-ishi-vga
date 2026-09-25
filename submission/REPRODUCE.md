# 再検証

このフォルダ単体でハッシュ確認、RTL／ゲート試験、保存SPICE波形の再判定、新しいSPICE過渡解析ができます。実行バイナリのインストールや依存の自動更新は行いません。

## 同梱内容の確認

```sh
python3 tools/verify_bundle.py
```

`manifest.json` の全ファイルと `SHA256SUMS` を確認します。ハッシュ一致は回路の正しさの証明とは別です。

[可搬性の実行記録](verification/portability.json)：提出フォルダを別ディレクトリへ複製し、RTL・ゲート各2フレームと `upper_init` のngspice解析を新規実行して合格しました。実行バイナリは同じ環境のものを使っており、別OSへツールを新規インストールした試験ではありません。この記録内のmanifestハッシュは試験時の提出ドラフトを識別します。

## RTL／ゲート

Icarus Verilog 12.0で実行済み。提出フォルダから、まだ存在しない出力ディレクトリを指定します。保存済み検証記録は上書きしません。

```sh
python3 tools/run_tests.py rtl --out ../vga_rtl_check
python3 tools/run_tests.py gates --out ../vga_gates_check
```

PATHにない場合は `--iverilog /絶対パス/iverilog --vvp /絶対パス/vvp` を付けます。合成後ゲート回路とセルモデルは同梱しているため、再合成やPDKは不要です。

## ngspice

Pythonのnumpyとngspiceが必要です（実行済み版：ngspice 46+）。保存した6試験の実波形を再判定する場合：

```sh
python3 tools/run_tests.py saved-spice
```

新しい過渡解析を実行する場合：

```sh
python3 tools/run_tests.py spice --case upper_init --out ../vga_spice_upper
```

`--case` は `upper_init`、`lower_init`、`vsync_init`、`frame_wrap_init`、`powerup`、`upper_reference`。
`--ngspice /絶対パス/ngspice` も指定可能。実行は `ngspice -n -b -r wave.raw tb.spice`。
同梱モデルは固定PDKからバイト一致で複写しています。`models.spice` のincludeだけを提出フォルダ内の相対パスへ変更しました。元の抽出回路・モデル・刺激は変えていません。

`verification/spice/<試験名>/wave.raw.gz` は元の実波形をgzip圧縮したものです。再判定では展開後のSHA256も元の `run.json` と照合します。元ログにある作業環境の絶対パスは履歴であり、現在の実行時参照先ではありません。

## 物理検証と配置配線の再現

`reproduce/core_handoff.tar.gz` は、元の125ファイルのコア引き渡し一式です。凍結APR出力から局所配線修復→端子注記→引き出しを再実行するスクリプト・中間データと、当時のDRC／LVS／STA記録を含みます。

別ディレクトリへ展開し、その `REPRODUCE.md` と `toolchain.lock.json` に従って固定依存を用意します。使うのはAPRtools `8f6962bf2df1618d633f8a81c230fec895fc83aa` とTR-1um `f408d3b5c23a8ebe44f02b0482a9270601e2880f`。v59_4と記録済みPCell lookupパッチのみ。古い版やローカルPDKへの代替は行いません。

これは元の配置探索を初めから再探索するものではありません。また、このアーカイブはSPICE追加試験より前に凍結したため、**現在の検証結果は提出フォルダ側のSPECとverificationが優先**です。

同梱の `source/config.py` は実装設定の記録で、単独でAPRtoolsを動かすラッパではありません。再合成・DRC・LVSの固定依存実行には上の再現アーカイブを使います。

`reproduce/package_submission.py` は今回の提出フォルダを作った設計側スクリプトの保存です。元ワークスペースの検証済み成果物を集める用途で、提出フォルダ単体から実行するものではありません。

端子図・ブロック図の生成元は `reproduce/submission_figures.py`。PythonのKLayout、matplotlib、Noto Sans CJKフォントを使用しています。元ワークスペースでは `/usr/bin/python3 scripts/submission_figures.py` で生成しました。配線の描画元は同梱の最終GDSで、回路を変更する処理はありません。[図版と端子座標の照合記録](verification/figures.json)に入力・出力のハッシュを保存しています。
