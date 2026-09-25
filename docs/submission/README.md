# ISHI VGA — TR-1um

ISHI会ロゴを「格子＋5本の電源枝」の図案としてVGAへ出力する固定映像回路です。外部CLK 3.15 MHzで、640×480・60 Hz相当の同期信号とRGB111を生成します。

**コア外形1792.8×897.2 µm、VDD込み7端子（共通VSSを除く）。** 岡村氏のAPRtools／v59_4スタンダードセルを使用し、VerilogからYosysで論理合成、配置配線と局所修復を行いました。

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

本回路はRTLから合成しているため、手描きのXschem回路図はありません。回路の正本は上記RTL・ゲート回路・LVS参照で、下図は説明用ブロック図です。

GDSを統合するときは **`ishi_vga_core` だけを明示して配置**してください。ハッシュを保存したGDSには未参照のライブラリtopセル11個も残っており、すべてのtopセルをまとめて配置するものではありません。

## 設計で試したこと

- 画像ROMを使わず、座標ビット・共有した文字パターン・少数の線分から固定画像を生成。
- 水平を8画素時間単位で進め、CLKを3.15 MHzへ抑えたVGAタイミング生成。
- RESET端子なしのカウンタを採用。全二値状態からの遷移モデルと、限定した電源投入SPICE条件を別々に検証。
- 4行のセル配置を均等割当から変更し、M1/M2だけで半枠内へ配置配線。固定版ツール、修復前チェックポイント、再現手順を保存。
- 同じ最終GDSについて、描画DRC・strict LVS・抽出SPICEの結果を対応づけた。

これらは実装・再現性の成果であり、新しい標準セルや製造プロセスを開発したという主張ではありません。

## 状態

製造レビューを受けて4個のクロック分岐バッファを追加しました。面積・端子・RTLは不変です。[指摘への対応と未解決事項](REVIEW.md)。

描画DRC 0、strict LVS一致、RTL／ゲート2フレーム一致。抽出SPICEは5 V・27℃・各出力1 pFで、選択した5試験・計668クロック一致（境界540＋起動中128、起動試験の画面同期獲得は未確認）。

**フレーム・パッド・ESDは未統合です。** マスク検査の `WAR06: Floating SG Detected` がCLK入力に1件残っています。本フォルダは主催者へコアを引き渡すための資料であり、フレーム込みの製造最終版ではありません。統合後にDRC／MDP／LVSを再確認してください。

## 表示画像・レイアウト

Tang Primer 20K＋抵抗DACでのVGA実機表示（2026-09-25）。利用者提供の写真を反時計回りに90°回転して掲載しています。

<img src="ishi_vga_fpga_photo.png" alt="Tang Primer 20KからVGAモニタへ出力したISHI会ロゴの実機写真" width="640">

ゲートシミュレーションで観測した表示画像。保存済みの `observed.hex` から生成した640×480画像です。

<img src="ishi_vga_output.png" alt="合成後ゲートシミュレーションの観測フレーム" width="640">

![最終GDSのレイアウト](ishi_vga_layout.png)

![回路の説明用ブロック図](ishi_vga_blocks.png)

[拡大用のSVG](ishi_vga_blocks.svg)
