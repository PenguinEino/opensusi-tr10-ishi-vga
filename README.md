# ISHI VGA — OpenSUSI TR-1um

ISHI会ロゴをVGAに出力し、文字を **I → S → H → I → 発光なし** の順に点灯する回路です。各文字は約0.267秒、発光なしは約1.067秒、1周は約2.13秒です。

| 項目 | 仕様 |
|---|---|
| 映像出力 | 640×480・60 Hz相当、RGB111 |
| クロック | 外部3.15 MHz |
| 電源 | VDD=5 V、VSS=0 V |
| 端子数 | 8（共通VSSを除くと7） |
| コア外形 | 1792.8 × 897.2 µm（1800 × 900 µm枠） |
| PDK | [TR-1um](https://github.com/OpenSUSI/TR-1um) dev / `f408d3b` に固定 |
| スタンダードセル | 岡村氏の[APRtools](https://github.com/jun1okamura/TR-1um_APRtools) / `v59_4` |

[文字発光版・GDS](release/ishi_vga_letter_scan_core/README.md) · [実装・再検証](docs/LETTER_SCAN_IMPLEMENTATION.md) · [FPGA書き込み](docs/FPGA_ANIMATION_20260925.md) · [静止画版の提出物](submission/README.md)

フレーム未統合のコアです。検証結果と残件は仕様書に記載しています。

静止画版のTang Primer 20K＋抵抗DACでの実機表示（2026-09-25）。

<img src="docs/images/fpga-vga-monitor-20260925.png" alt="Tang Primer 20KからVGAモニタへ出力したISHI会ロゴの実機写真" width="640">

文字発光版のゲートシミュレーションで観測した5段階の表示。

<img src="release/ishi_vga_letter_scan_core/animation.gif" alt="I、S、H、Iの順に点灯し、元のロゴへ戻る" width="640">
