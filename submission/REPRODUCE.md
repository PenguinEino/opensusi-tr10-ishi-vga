# 再検証

このフォルダ単体でハッシュ確認、RTL／ゲート試験、保存SPICE波形の再判定、新しいSPICE過渡解析ができます。実行バイナリのインストールや依存の自動更新は行いません。

## 同梱内容の確認

```sh
python3 tools/verify_bundle.py
```

`manifest.json` の全ファイルと `SHA256SUMS` を確認します。ハッシュ一致は回路の正しさの証明とは別です。

[可搬性試験](verification/portability.json)：別ディレクトリでRTL／ゲート2フレーム、全二値状態、ngspice上側110クロックを再実行して合格。展開した再現アーカイブからGDSバイト一致とDRC／LVS／STAも確認しました。バイナリと固定依存は同じPCのものを再利用しています。過去のレビュー対象と混同しないでください。

## RTL／ゲート

Icarus Verilog 12.0で実行済み。提出フォルダから、まだ存在しない出力ディレクトリを指定します。保存済み検証記録は上書きしません。

```sh
python3 tools/run_tests.py rtl --out ../vga_rtl_check
python3 tools/run_tests.py gates --out ../vga_gates_check
python3 tools/run_tests.py exhaustive --out ../vga_all_states_check
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

`reproduce/clock_eco_reproduce.tar.gz` を別ディレクトリへ展開し、同梱 `REPRODUCE.md` の固定依存と手順を使います。旧コアを入力としてクロック4分岐ECOを再実行し、GDSバイト一致、公式DRC／MDP／strict LVS、guard付きSTAを確認します。配置探索のやり直しではありません。

アーカイブ内の `release/ishi_vga_grid_power_core/` は旧版の凍結入力です。そこにある旧GDS・旧STA結果を現行の合格証拠として使わないでください。**現行は本提出フォルダ直下のGDSとverificationです。**

`source/config.py` は最終ECO設定です。単独の合成だけでは4分岐の物理変更を再現しません。再現スクリプトが、旧ネットリストのDFF CK接続とGDSを同時に更新します。

`scripts/run_apr.py ... syn/sta/sta.sh` の直接呼出しはguard付きで、エラー・未完了・違反時にexit 1です。上流 `syn/syn.sh` 内部のSTA終了コードだけで提出判定をしないでください。

`reproduce/package_submission.py` は元ワークスペース用の梱包スクリプトです。提出フォルダ単独から実行するものではありません。

端子図・ブロック図の生成元は `reproduce/submission_figures.py`。PythonのKLayout、matplotlib、Noto Sans CJKフォントを使用しています。元ワークスペースでは `/usr/bin/python3 scripts/submission_figures.py` で生成しました。配線の描画元は同梱の最終GDSで、回路を変更する処理はありません。[図版と端子座標の照合記録](verification/figures.json)に入力・出力のハッシュを保存しています。
