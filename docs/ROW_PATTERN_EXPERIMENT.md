# B案の行パターン共用実験 — 2026-09-25

**今回の実装では削減にならなかった。現行B案を維持する。**

128×108のB案画像は、白紙を含めて9種類の行パターン、連続したY区間は17区間。
同じ行パターンについてはX座標→RGBの回路を一つだけ生成し、複数のY区間からそれを選ぶ構成を試した。
RGBの部分式だけの共有ではなく、横一行の描画回路の共用を明示している。

## 結果

|構成|セル数|セル面積 µm²|reg→reg slack ns|短絡修正前の圧縮後コア µm|
|---|---:|---:|---:|---|
|現行B：21矩形|375|495,252|111.806|1611.0×2905.0|
|行共用：4 bit行番号＋選択回路|401|530,215|107.591|未試行|
|行共用：各パターンの有効信号で直接選択|389|516,423|112.501|1611.0×3520.6|

後者でもセル面積は4.3%増、圧縮後高さは21.2%増。初期配線の簡易接続検査も
75件から166件の問題報告へ増えた。これらの件数は独立した短絡箇所数とは限らない。
いずれも提出用GDSではなく、公式DRC/LVS・配線後STAの合格を意味しない。

セル、Liberty、Yosys/ABC、入出力負荷、155 ns周期の条件は現行Bと同じ。
物理比較も7行、1598.4 µm行幅、seed=1、restarts=80、order_passes=20、pad_weight=1.0、
配線チャネル=[216,900,900,900,900,900,900,216] µmでそろえた。短絡修正前のstep6を
同じ圧縮スクリプトで評価した。一つの配置条件の比較であり、最良配置や最小面積の証明ではない。

## 機能の同一性

- 描画回路のh,y各8 bit、全65,536組を現行Bの矩形RTLと比較して両版PASS。
- 両版それぞれについて、RTL／最終BUFTH挿入後ネットリスト、6.30/6.45 MHzを検証。
- 各条件315,017tickを独立ラスタ参照と照合してPASS。フレーム折り返し、帰線期間、停止クロックでのリセットを含む。
- 出力フレームはB案の期待値と完全一致。タイミング評価は単位遅延シミュレーションと配線前STAまで。

## 構成と解釈

`scripts/generate_row_pattern_rtl.py`が、矩形データを一度ラスタ化して同一行を集約する。
Pythonのラスタ配列は生成時だけ使い、RTLには画像ROMも追加FFも持たせない（FFは全版28個）。
青・紫の帯は赤文字の下にも続けて描けるようにし、隠れた部分を不必要に分割することを避けた。

`row_patterns`はYから4 bitの行番号を求め、9通りのX→RGB回路の出力を選ぶ。
`row_patterns_onehot`は各行パターンの有効条件を直接生成し、そのRGB出力を選択する。
両方とも同じ公式採用フローのflattenとABC最適化を通した。

考えられる理由は、現行の矩形方式が**異なる行にまたがる部分図形**も共用できる一方、
行全体でまとめ直す方式ではYの選択回路とその接続が増えること。
本実験だけで「現行回路ですべての行共有がすでに最適化済み」とは断定できない。
確認できたのは、今回の2種類の明示的な行共有が、現行Bに対して面積改善を示さなかったこと。

## 再現と成果物

本体のRTL・config・ネットリストは変更していない。実験は`experiments/`内に分離し、
`config.py`は本体の条件を読み、描画RTLだけを差し替える。将来本体configが変わると
実験条件も変わるので、保存版manifestのSHA256と照合すること。

```sh
.venv/bin/python scripts/reference_frame.py
.venv/bin/python scripts/generate_row_pattern_rtl.py
python3 scripts/run_apr.py --design-root experiments/row_patterns syn/syn.sh
python3 scripts/run_apr.py --design-root experiments/row_patterns_onehot syn/syn.sh
.venv/bin/python scripts/test_row_patterns.py

python3 scripts/run_apr.py --design-root experiments/row_patterns_onehot apr/place.py
python3 scripts/run_apr.py --design-root experiments/row_patterns_onehot apr/verify_placement.py
python3 scripts/run_apr.py --design-root experiments/row_patterns_onehot apr/route.py --to 6
python3 scripts/run_apr.py --design-root experiments/row_patterns_onehot apr/squeeze_channels.py \
  --in-gds layout/step6/route_step_2_routed_raw.gds -o build/diagnostic_compacted.gds \
  --pin-map-in layout/pin_map.json --pin-map-out build/diagnostic_pins.json \
  --net-shapes-in layout/net_shapes.json --net-shapes-out build/diagnostic_shapes.json
```

ログ・対象のハッシュは`docs/validation_rows/`。
診断用GDSは`experiments/row_patterns_onehot/build/diagnostic_compacted.gds`。
現行BのGDSは従来の`build/diagnostic_b_compacted.gds`で、取り違えないこと。
