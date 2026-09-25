# ISHI VGA 格子＋電源枝5本：コア引き渡しセット

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
