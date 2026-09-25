# ISHI VGA — TR-1um

ISHI会ロゴを「格子＋5本の電源枝」の図案としてVGAへ出力する固定映像回路です。外部CLK 3.15 MHzで、640×480・60 Hz相当の同期信号とRGB111を生成します。

**コア外形1792.8×897.2 µm、VDD込み7端子（共通VSSを除く）。** 岡村氏の[APRtools](https://github.com/jun1okamura/TR-1um_APRtools)／v59_4スタンダードセルを使用し、VerilogからYosysで論理合成、配置配線と局所修復を行いました。

| 内容 | ファイル |
|---|---|
| 仕様・端子・動作・検証範囲 | [SPEC.md](SPEC.md) |
| レイアウト | [ishi_vga.gds](ishi_vga.gds) — top: **`ishi_vga_core`** |
| GDSから直接抽出した回路 | [ishi_vga.extracted](ishi_vga.extracted) |
| 独立したLVS参照回路 | [simulation/ishi_vga_lvs.spice](simulation/ishi_vga_lvs.spice) |
| ngspice用の抽出回路 | [simulation/core_sim.spice](simulation/core_sim.spice) |
| 論理回路のソース | [RTL](source/ishi_vga_core.v)・[描画RTL](source/ishi_logo.v)・[合成後ゲート回路](source/ishi_vga_core_pnr.v) |
| 端子の機械可読表 | [ports.json](ports.json) |
| 再検証方法 | [REPRODUCE.md](REPRODUCE.md) |
| 依存の固定版・由来 | [toolchain.lock.json](toolchain.lock.json)・[PROVENANCE.md](PROVENANCE.md) |
| 検証記録 | [verification/summary.json](verification/summary.json) |

統合時はトップセル **`ishi_vga_core`** を指定します。

## 実装内容

- 座標ビット・共有した文字パターン・線分判定から固定ロゴを生成。
- 水平を8画素時間単位で進め、3.15 MHzでVGAタイミングを生成。
- RESET端子を省いた水平・垂直カウンタを実装。
- 4行のセル配置とM1/M2配線で、1800×900 µmの半枠に収めたコアを作成。
- クロックを4個のバッファで分岐し、各行のFFを駆動。
- ツール・セル・PDKの版を固定し、チェックポイントから同じGDSを再生成できる手順を整備。

## 検証結果

| 項目 | 結果 |
|---|---|
| 描画DRC・strict LVS | 描画DRC 0件、strict LVS一致 |
| RTL／ゲート | 各2フレーム・105,000クロック一致。全131,072二値カウンタ状態の次状態・出力も一致 |
| セル遅延STA | 5 V・25℃、setup余裕276.025 ns、hold余裕6.687 ns |
| 抽出SPICE | 5 V・27℃・各出力1 pFで、5試験・計668クロック一致（境界540＋起動中128） |
| FPGA実機 | Tang Primer 20K＋抵抗DACでVGAモニタへのロゴ表示を確認 |
| 再現性 | チェックポイントから再生成したGDSのSHA256一致、DRC／LVS／STAを再確認 |

## 表示画像・レイアウト

Tang Primer 20K＋抵抗DACでのVGA実機表示（2026-09-25）。

<img src="ishi_vga_fpga_photo.png" alt="Tang Primer 20KからVGAモニタへ出力したISHI会ロゴの実機写真" width="640">

ゲートシミュレーションで観測した表示画像。保存済みの `observed.hex` から生成した640×480画像です。

<img src="ishi_vga_output.png" alt="合成後ゲートシミュレーションの観測フレーム" width="640">

![最終GDSのレイアウト](ishi_vga_layout.png)

![回路の説明用ブロック図](ishi_vga_blocks.png)

[拡大用のSVG](ishi_vga_blocks.svg)
