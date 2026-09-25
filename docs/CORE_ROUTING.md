# B案コアの配線と公式LVS — 2026-09-25

**後続成果:** [10信号の外周への引き出し](CORE_ESCAPE.md)も1797.3×1763.9 µmで完了し、DRC・LVSを維持した。本ページのGDSとハッシュは、その前段のコア内部配線の確定記録として保存する。

**コア内部の短絡・断線を解消し、固定PDKの公式LVSがstrict port modeで一致した。**
B案の画素、RTL、282セルの合成回路は変更していない。今回追加した配線はM1/M2/V1のみで、ポリシリコン配線案は混ぜていない。

この段階のGDSは [labeled_core.gds](../experiments/core_ports_final/build/labeled_core.gds)。
開く際の固定入口は `build/ishi_vga_core_routed.gds`（同ファイルへのリンク）。
トップは `ishi_vga_core`、SHA256は `3948145e00ad30fde2b0843e99b57dc275473ea02cc3441e15a5c27802a1b84c`。
これは**フレーム・パッド未統合のコア**であり、提出用チップGDSではない。

## 実測と検証

|項目|結果|
|---|---|
|コア外接寸法|1793.7 × 1760.3 µm|
|bbox|(-16.2, 0)–(1777.5, 1760.3) µm|
|論理セル／TAP・FILL|282／139、全421配置が元データと一致|
|実信号端子|987/987、欠落0|
|短絡ネット対|143 → 0、短絡した接続成分0|
|断線|0、点抽出と実端子図形の両方式で確認|
|電源接続|VDD/VSS各1成分、互いに分離、定数入力の接続を維持|
|公式描画DRC|0件（正しいコアポート名を付けた最終GDS）|
|公式マスクDRC|`WAR06: Floating SG Detected` 2件、入力時と同じCLK/RESETのBUFTH|
|公式回路LVS|PASS、24セル回路＋トップが一致、12ポートすべて一致|

1800 µm角に対して幅6.3 µm、高さ39.7 µmの余裕があるという**外接寸法の測定**である。フレームの配線余白やピン引き出しを確保したという意味ではない。
セル・階層は変更せず、最初の143対のチェックポイントからの全差分でも、変更がトップM1/M2/V1に限られることを検証した。

正本の検証記録:

- [全差分の実端子・電源・DRC検査](../experiments/core_route_audit/build/verification.json)
- [12ポートの注記と形状不変の検査](../experiments/core_ports_final/build/label_report.json)
- [公式LVS結果の解析と入力ハッシュ](../experiments/core_lvs_fixed/build/lvs_verification.json)
- [公式LVSログ](../experiments/core_lvs_fixed/build/core_lvs.log) / [LVSデータベース](../experiments/core_lvs_fixed/build/core.lvsdb)
- [採用ファイルと中間成果のハッシュ一覧](core_routing_snapshot.json)

## 修復方法と失敗候補

冗長なトップviaを削除して143→50対、viaの組合せ削除で50→45対とした。その後、衝突する既存枝を切り、固定ルールから作った障害物の間を2層で探索して順次つなぎ直した。[検証方法](ROUTING_REPAIR_METHOD.md)も参照。

採用した主な段階は `via_prune → via_groups → maze_040 → maze_227 → maze_v2 → maze_148 → maze_073 → maze_103 → maze_059_fix → maze_209_fix → maze_194 → maze_seq00 … maze_seq05 → maze_seq06_fixed`。
seq00は検証済みh[1]と193の差分を統合し、以降は必ず直前の採用GDSから再配線した。

最後の `_069_` は左側への探索では0.9/0.3 µm格子とも経路がなかった。探索範囲を右端1782 µmまで広げると2本の経路を発見した。実際の配線は既存bbox内に収まり、全体寸法は増えていない。2経路の同一ネットviaパッド間に残った0.2 µmの隙間は、`post_route_boxes` の明示的なM1接続で埋め、DRCを再検証した。

`maze_seq06_right` は短絡0でもM1間隔違反があり**不採用**。`maze_cumulative` とその派生 `maze_038` も、統合時の新規短絡があるため不採用。個々のペア数や局所的なACCEPTED表示だけで選ばない。最終採用候補は `core_route_audit` で143対の祖先と改めて比較している。

## LVS参照回路の定数変換

固定版 `apr/mklvsnet.py` は、Verilogの `_542_.D(1'h1)` をSPICEのノード名 `1'h1` として出力した。最初の公式LVSはリセット同期FF周辺で不一致となった。この結果は `experiments/core_lvs/build/core.lvsdb` とログに保存してある。**そのSPICEを最終LVS参照として使わない。**

設計側の [prepare_core_lvs_reference.py](../scripts/prepare_core_lvs_reference.py) は、合成済みVerilogのこの1か所だけを、LVS用の派生入力で `vdd` へ正規化する。その入力を固定版の `mklvsnet.py` に渡し直す。セルSPICEのD端子位置からも照合し、生成後の参照回路がこの1トークン以外で変わっていないことを検査する。元Verilog、配置、上流コードは変更しない。参照の作成にGDSや抽出回路は使わない。

採用参照は [core_lvs_fixed/build/ishi_vga_core.spice](../experiments/core_lvs_fixed/build/ishi_vga_core.spice)、SHA256 `fcecae367fec09a6497ae8313a392a4e40961afae9a983dff9a76648339a189e`。
[入力・正規化内容の記録](../experiments/core_lvs_fixed/build/reference_manifest.json)をセットで参照する。先行したポート注記処理は旧参照の12ポート宣言だけを使用したが、LVS検証記録では補正後参照とのポート一覧の同一性も確認している。

## ポート注記とDRCの範囲

生の配線GDSにはトップのポート名がなかったため、実セル端子上にRGB/同期/CLK/RESETの10信号、実電源レール上にvdd/vssをTEXTとして付けた。図形・セル階層・配線は完全に同じである。
公式 `03_Electrical.drc` はSCRBのないコアでトップポート注記を考慮するので、描画側のGC.ANT 2件は0になった。マスク側は同じ扱いではなく、Floating SGの2件が残る。パッドとESD接続を含むチップ全体の検証はまだ済んでいない。

## 再検証

下記はこのワークスペースに保存したGDSと生成済み参照を検査するコマンド（リポジトリルートから実行）。LVSは別名のレポートに出し、凍結成果を上書きしない。`build/`はgitignore対象なので、別環境へ渡す場合はGDS・参照・JSON・レポートを併せて渡す。全チェックポイントが素のGit checkoutだけで再生成できるという意味ではない。

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/run_apr.py --design-root experiments/core_lvs_fixed \
  apr/lvs_pdk.py "$PWD/experiments/core_ports_final/build/labeled_core.gds" ishi_vga_core \
  --sch "$PWD/experiments/core_lvs_fixed/build/ishi_vga_core.spice" \
  -r "$PWD/build/core_recheck.lvsdb" > build/core_recheck.log 2>&1
# 次は上の再実行結果ではなく、保存済みの正式記録を解析するコマンド
.venv/bin/python scripts/report_core_lvs.py --design-root experiments/core_lvs_fixed \
  --gds experiments/core_ports_final/build/labeled_core.gds \
  --route-audit experiments/core_route_audit/build/verification.json \
  --labels experiments/core_ports_final/build/label_report.json
klayout build/ishi_vga_core_routed.gds
```

実行済みの正式記録は `core_lvs_fixed/build/core_lvs.log` と `core.lvsdb` に保存した。公式wrapperの終了コードだけでなく、lvsdbの各回路・トップネット・ポートの一致も検査している。

残作業は、主催者の実テンプレートへの配置、外部ピンへの引き出し、パッド・電源・ESD接続、チップ全体のDRC/LVS。リング発振器は未搭載で、外部CLKは維持する。配線後の寄生込みSTA、PVT、FPGA／モニタ実機も未完了。既存の配線前STAの余裕を配線後保証として流用しない。
