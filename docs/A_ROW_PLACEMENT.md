# A案の行割当探索と配線修復試験

2026-09-25。[前回31構成の論理探索](a_trials/README.md) の最小回路 `a_h63_v500_x` をそのまま使い、行割当を改善した。**37矩形・RGB222・382セルを変えず、診断段階のGDSが1783.8×1744.7 µmに縮んだ。1800 µm角には入るが、短絡が残り、提出用ではない。** フレーム統合は停止中。B成果物は変更していない。

## 方法と固定版

既定配置の行割当は、単一セルを動かす改善探索では狭い行容量の局所解から抜けにくかった。設計側の `scripts/row_anneal.cpp` と `scripts/a_row_placement.py` で、セル交換と一時的な評価悪化を許す焼きなまし探索を追加した。セル幅・プロセス定数は固定設定から取得する。

APRtools自身の変更は既存のPCell検索パッチだけ。固定上流の `place.load`、`order_rows`、`pack_row`、`dump` をそのまま使い、配置検証・配線・圧縮は `scripts/run_apr.py` から上流の入口を呼ぶ。ライブラリ・PDKの版変更、過去repoやlegacyスクリプトの利用はない。

- 元配置: `a_phys_h63_alt6`、6行、328サイト、alternate fill、PRL20。
- 行割当探索: seed11、12再開×4,000,000試行、温度4.0→0.02、最大行幅=平均の1.025倍。
- 採用候補は再開2。行内並べ替え80パス。
- 行をまたぐ距離の和: **414→157**。
- チャネルを横断するネット数: **[3,27,40,33,38,30,7]**。
- 再現設定は `experiments/a_anneal_span6/config.py` の `ROW_OPT`、入力SHA256は `source_manifest.json`、探索結果は `build/row_optimization.json`。

## 検証結果

|項目|新配置・修復前 `a_anneal_span6`|上流短絡修復20回 `a_ripup_span6`|
|---|---:|---:|
|圧縮後寸法 µm|1783.8×1744.7|1783.8×1760.9|
|配置インスタンス（TAP/FILL込み）|523|523|
|実GDSとLEFから確認した信号端子|1301|1301|
|実端子取りこぼし|0|0|
|断線ネット|0|**2（h[2], v[2]）**|
|短絡成分|10|9|
|成分内の異なるネット対|75|20|
|公式描画DRC|GC.ANT 3件|GC.ANT 5件|
|公式マスクDRC|WAR06 3件|WAR06 5件|
|公式LVS|未実施|未実施|

修復試験は短絡を減らした一方で断線を新たに生じたため、**採用しない**。修復後のルータ端点表だけではこの問題を捉えられず、実GDSのセル変換とv59_4 LEFの実端子から確認した。基準は断線0の `a_anneal_span6` に維持する。どちらも定数端子の電源接続・コア外周端子の引き出しは未完成。

描画DRCとMDPはそれぞれ独立して実行。`build/diagnostic_compacted_mdp.lyrdb` がマスク検査結果であり、`drawing.lyrdb` と取り違えない。寄生込みタイミングは未検証。RTL・ネットリストは [元382セル版の機能検証](../experiments/a_h63_v500_x/build/verification.json) と同じ。セル変更がないことと、配線が正しいことは別の検証である。

冗長ビア削除 `a_via_prune` も45候補を試したが、断線なく改善できる削除は0件。採用結果なし。

## 成果物と再現

- 基準GDS: [a_anneal_span6/build/diagnostic_compacted.gds](../experiments/a_anneal_span6/build/diagnostic_compacted.gds)、SHA256 `44679ad20e2347c81d67ea85e79f51fa1516ddd64d633a104f7c71bf46e38309`。
- 入口: `build/ishi_vga_a_diagnostic.gds`。短絡が残る診断用。
- [実端子接続監査](../experiments/a_anneal_span6/build/audit/metal_connectivity.md) / [修復試験の監査](../experiments/a_ripup_span6/build/audit/metal_connectivity.md)。
- 数値・対象SHA256: [a_row_placement_snapshot.json](a_row_placement_snapshot.json)。旧31構成レポートは以前の探索時点を保存しており、この世代を含まない。

```sh
python3 scripts/check_toolchain.py
# 既存候補を上書きせず、新しい名前で再現する
.venv/bin/python scripts/a_row_placement.py prepare a_anneal_repeat
.venv/bin/python scripts/a_row_placement.py solve a_anneal_repeat
.venv/bin/python scripts/a_row_placement.py route a_anneal_repeat
.venv/bin/python scripts/routing_diagnostics.py \
  --gds experiments/a_anneal_repeat/build/diagnostic_compacted.gds \
  --pins experiments/a_anneal_repeat/build/diagnostic_pins.json \
  --shapes experiments/a_anneal_repeat/build/diagnostic_shapes.json \
  --placement experiments/a_anneal_repeat/layout/placement.json \
  --out experiments/a_anneal_repeat/build/audit --poly
```

上流修復試験の設定は `a_ripup_span6/config.py` の `A_RIPUP`。入口 `apr/ripup_reroute_shorts.py` に未圧縮step6 GDS、pin_map、net_shapes、placement、`216,900,900,900,900,900,216`、出力3ファイル、最大20回を渡した。ログは `build/ripup.log`。その出力を `apr/squeeze_channels.py` で圧縮後、接続監査と `apr/drc_pdk.py ... --mdp` を実行した。改善と退行の両方を記録し、成功扱いしない。
