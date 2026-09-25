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

[提出物](submission/README.md) · [GDS](submission/ishi_vga.gds) · [仕様・端子](submission/SPEC.md) · [FPGA試験](docs/FPGA_ANIMATION_20260925.md)

描画DRC 0件・LVS一致。抽出回路のngspiceも20試験・922クロック合格しています。

Tang Primer 20K＋抵抗DACでの実機動画（2026-09-25）。[MP4](submission/fpga_demo.mp4)

<img src="submission/fpga_demo.gif" alt="Tang Primer 20KからVGAモニタへ出力したISHI会ロゴの実機動画" width="640">

文字発光版のゲートシミュレーションで観測した5段階の表示。

<img src="submission/animation.gif" alt="I、S、H、Iの順に点灯し、元のロゴへ戻る" width="640">

提出GDSのレイアウト。左側中央に名前とペンギンを配置しています。

<img src="submission/layout.png" alt="左側中央にEINOSUKE OKAZAKIとペンギンを配置した最終GDSの全体レイアウト" width="900">

<img src="submission/silicon_art.png" alt="名前とペンギンの拡大図、および最終GDSのメタル全体図" width="900">

[装飾の詳細](submission/SILICON_ART.md) · [端子位置の拡大図](submission/ishi_vga_pins.png)
