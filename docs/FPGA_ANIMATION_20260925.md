# FPGAアニメーション試験（2026-09-25）

Tang Primer 20K Dock、従来のJ5配線・抵抗DAC・3.15 MHz PLLを使用。ASICのRTLをボード用ラッパで動かします。

## 現行：文字点灯＋消灯段階

**I → S → H → I → 発光なし**。各16フレーム、1周約1.33秒です。

```sh
python3 scripts/build_fpga.py vga_letter_animation
bash scripts/fpga_loader.sh -b tangprimer20k --detect
bash scripts/fpga_loader.sh -b tangprimer20k -m build/fpga_vga_letter_animation/vga_letter_animation.fs
```

- コア：[a_letter_scan_eco/ishi_vga_core.v](../experiments/a_letter_scan_eco/ishi_vga_core.v)。
- ビットストリームSHA256：`cc24d9046a72a3dda4f862b013312b218caf96f83e5c815ec3ec297c417e3cdb`。
- JTAG：Gowin IDCODE `0x81b`。SRAMロード100%、DONE、終了コード0。
- 8 I/Oの配置・電圧／駆動設定とPLLパラメータを、表示実績のある静止画版と照合。
- nextpnr：3.15 MHz制約PASS。報告上の最大周波数269.833 MHz（実測値ではない）。
- FPGA専用のresetや初期値はコアへ追加していません。
- Flashへの書き込みは行っていません。

書き込みログ・入力ハッシュ・ビットストリームは [引き渡しフォルダ](../release/ishi_vga_letter_scan_core/README.md) に保存します。画面の5段階の見え方は、利用者へ確認しています。

## 先に試した配線発光版

`vga_animation` は配線上を光が走る旧候補です。SRAM書き込み後、利用者が動きを確認しました。初めは水色が青、白がピンクに見えるとの報告がありました。緑配線の接触確認後に改善し、ハイライトはグレーに見えるとのことでした。RGBのアナログ電圧は測定していません。

現行の文字発光版を書き込む際は、`vga_animation` ではなく **`vga_letter_animation`** を選びます。接続表とUSB権限の扱いは [FPGA試験手順](FPGA_BRINGUP.md) を参照してください。
