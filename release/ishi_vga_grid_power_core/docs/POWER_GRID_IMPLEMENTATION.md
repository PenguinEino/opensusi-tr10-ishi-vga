# 採用版：格子＋5線（電源枝）

2026-09-25、ユーザーが `g_power` を採用し、半枠に収めて提出用コアへ仕上げるよう指示した。
過去のA/Bと比較試験は保存する。旧文書の「未採用」は当時の状態であり、今回の選択は本書を優先する。

- 図案の正本：`experiments/a_metal_g_power/`。VDD枝2本、VSS枝3本と下側拡散帯の切れ目を含む。
- RGB111、黒背景、外部CLK 3.15 MHz、RESETなし、リングなし。
- VDD、CLK、HSYNC、VSYNC、R、G、Bの7端子（共通VSSを除く）。
- 予算1800×900 µm。フレーム統合はユーザーの保留指示を維持する。
- 元の209セル・301,193 µm²の論理回路と参照フレームを固定して配置配線を最適化する。
- 出発点は `a_metal_g_power_anneal4` の1783.8×984.7 µm、短絡17ネット対、断線0。

**コア単体の引き渡し版を完成。最終GDSは1792.8×897.2 µm、公式描画DRC 0、strict LVS合格。**
フレーム・パッド・ESD接続は保留指示に従って未実施であり、フレーム込み最終チップの提出可否とは区別する。

探索は `scripts/power_layout_search.py` と既存の設計内配置探索スクリプトから、固定APRtoolsの配置・配線・圧縮入口を実行する。
標準セル・PDK・設計規則は変更しない。各試行の設定はその `config.py`、入力は `source_manifest.json` に記録する。

## 引き渡すファイル

- [引き渡し用GDS](../release/ishi_vga_grid_power_core/src/ishi_vga_grid_power.gds)。トップは `ishi_vga_core`。
- [ファイル一式](../release/ishi_vga_grid_power_core.tar.gz)。GDS、SPICE、ゲート回路、RTL、端子表、機能・接続・DRC・MDP・LVS・STAの記録、再現用チェックポイントを含む。
- [物理検証の正本](../experiments/a_power_escape/build/verification.json)。[GDSの正本](../experiments/a_power_escape/build/candidate.gds)。
- [現行の設計config](../designs/grid_power/config.py)。rootの `config.py` / `rtl/` は旧Bの比較基準であり、こちらを合成しない。

最終GDS SHA256: `3bcfd73d98e2adca5b78eb20978a6145960e8023e60527ec7e960979cb86617e`。
GDS bboxは **(-15.3, 0)–(1777.5, 897.2) µm**。原点はbbox左下ではない。1800×900枠内の左下に配置するなら、bbox左端とコア原点の15.3 µm差も考慮する。
外接面積1.6085 mm²。予算に対する寸法余裕は横7.2 µm、縦2.8 µmで、フレーム側の配線余白を別に確保したという意味ではない。

## 最終検証

|項目|結果・範囲|
|---|---|
|採用画像・RTL・ゲート回路|採用元 `a_metal_g_power` とバイト一致|
|論理セル|209、セル面積301,193 µm²|
|配置セル|345：論理209＋TAP20＋FILL2 15＋FILL3 101|
|信号端子の実形状照合|696端子、欠落0|
|短絡・断線|ともに0。実LEF端子図形と独立した点抽出の両方で確認|
|電源|VDD/VSSそれぞれ1成分、互いに分離、信号への誤接続なし|
|公式描画DRC|0件|
|公式MDP・マスクDRC|`WAR06: Floating SG Detected` 1件。外部CLKのBUFTH入力。未解消として添付|
|公式LVS|strict port mode、8ポートすべて一致。全回路・トップの全ネット・子回路一致|
|RTL／ゲート機能|3.15 MHz、同期獲得後2フレームの全105,000 tick照合PASS|
|起動の二値モデル|h/vの131,072状態を探索、周期52,500 tickが1つ、周期へ入る最大49,928 tick（約15.85 ms）|
|セル遅延STA|typ 5 V/25℃、周期317.460317 ns。reg→reg setup余裕275.957 ns、hold余裕6.634 ns|
|修復からの再現|凍結APR出力から4段階を再実行、各GDSのSHA256一致。最終DRC/LVSも再実行して合格|

STAは固定Libertyとideal clockによる**配線寄生を含まない**評価。配線後PEX/PVT保証やモニタ実機動作を示さない。機能試験は試験側だけでFFを0に置いており、起動の全状態探索はRTL形式検証やアナログ電源立上り検証とは別の二値遷移モデル。
MDPのFloating SGはコアの外部入力がパッド／ESD未接続である段階の残件。フレーム統合後の消滅を未確認のまま保証せず、最終チップでDRC・MDP・LVSを再実行する。

## 接続条件と端子

外部CLK **3.15 MHz**、水平100 tick、垂直525行、640×480・60 Hz相当。旧B用の6.3 MHzを入力すると走査周波数が2倍になる。
RGB111のデジタル出力で外部パレットデコーダは不要。コアセルはVGAの75 Ωを直接駆動しない。外部バッファとRGB111用抵抗DACへ接続する。5 Vセルへのクロック入力の電圧条件は固定v59_4のBUFTH仕様に従う。3.3 V GPIO直結を前提にしない。

|端子|方向|層|GDS座標〔µm〕|接続位置|
|---|---|---|---|---|
|clk|入力|M2|(844.2, 895.5)|上辺|
|hsync|出力・負論理|M2|(261.9, 1.8)|下辺|
|vsync|出力・負論理|M2|(974.7, 895.5)|上辺|
|r|出力|M1|(-14.4, 690.3)|左辺|
|g|出力|M1|(-14.4, 693.9)|左辺|
|b|出力|M1|(-14.4, 601.2)|左辺|
|vdd|電源|M1|(2.7, 132.0)|既存の電源レール上の注記点|
|vss|共通電源|M1|(2.7, 77.3)|既存の電源レール上の注記点|

これは**コア端子表であってパッケージ／フレームのピン番号表ではない**。6信号＋VDDで7端子、共通VSSを含めた電気端子は8本。

## 何を変えて収めたか

4行への均等なセル量割当を緩め、関連する回路の行をまとめた。配置の論理セル幅は1447.2／1420.2／1517.4／685.8 µmとなり、行間を通るネットの合計距離指標が56→50へ減少した。

|段階|寸法〔µm〕|短絡ネット対|
|---|---|---:|
|採用時の比較GDS|1783.8×984.7|17|
|柔軟な行割当 `a_power_flex4`|1783.8×892.9|2|
|2か所の局所再配線|1783.8×892.9|0|
|6信号の外周引き出し|1792.8×897.2|0|

3行はTAP等を含めた実効幅にセルが収まらず不採用。ほかの配置・配線設定の試行は `a_power_*` に隔離した。
最終修復は `_066_` と `_172_` の交差を既存のM1/M2で迂回したもの。セル内部・配置・非配線層は元のAPR出力と同一。M3やポリ配線を追加していない。
`power_maze_route.py` は設計内の旧 `maze_route.py` を保存したまま派生させ、最小間隔ちょうどの合法な位置を探索格子で排除しないよう境界だけを扱う。配線幅やプロセス規則は変更しておらず、採否は公式デッキで検査した。

## 再現・再確認

ツールの固定版は [APRTOOLS_ADOPTION.md](APRTOOLS_ADOPTION.md) と [toolchain.lock.json](../toolchain.lock.json)。KLayout CLI 0.30.9、Python KLayout 0.30.6で今回実行した。

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/test_power_core.py
# 新しい出力ディレクトリを指定。凍結した既存GDSやログを上書きしない。
.venv/bin/python scripts/replay_power_core.py --out build/power_recheck_01
klayout release/ishi_vga_grid_power_core/src/ishi_vga_grid_power.gds
```

再現は保存したAPR出力 `a_power_flex4/build/diagnostic_compacted.gds` を出発点とし、局所修復→ポート注記→端子引き出し→接続監査→公式DRC/MDP/LVSを実行する。初期の配置探索を毎回繰り返すものではない。最初の実行結果は `build/power_core_replay/replay.json`。
配置探索自体の正本は `a_power_flex4/config.py`、`build/row_graph.txt`、`build/assignment.txt`、`layout/step4/`、使用した `scripts/a_row_placement.py` と `row_anneal.cpp`。上流の `place.py` のpack/dumpをそのまま使用した。

提出用セットはレビュー・フレーム統合へ渡す**コアの完成版**であり、主催者への送信やリポジトリへの投稿はしていない。
