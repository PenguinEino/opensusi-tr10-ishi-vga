# FPGAアニメーション試験（2026-09-25）

Tang Primer 20K Dock、従来のJ5配線・抵抗DAC・3.15 MHz PLLを使用。ASICのRTLをボード用ラッパで動かします。

## 現行：文字点灯＋長い発光なし段階

**I → S → H → I → 発光なし**。各文字16フレーム（約0.267秒）、発光なし64フレーム（約1.067秒）、1周128フレーム（約2.13秒）です。

```sh
python3 scripts/build_fpga.py vga_letter_animation
bash scripts/fpga_loader.sh -b tangprimer20k --detect
python3 scripts/program_fpga.py vga_letter_animation
```

- コア：[a_letter_scan_eco/ishi_vga_core.v](../experiments/a_letter_scan_eco/ishi_vga_core.v)。
- ビットストリームSHA256：`02d049bcfc497c8c76a276dabe16dc1e5ea80e50dcd395a36753d95fb782a77b`。
- 8 I/Oの配置・電圧／駆動設定とPLLパラメータを、実機表示確認済みの直前の文字発光版と照合。
- nextpnr：3.15 MHz制約PASS。報告上の最大周波数244.260 MHz（実測値ではない）。
- FPGA専用のresetや初期値はコアへ追加していません。

**延長版のSRAM書き込み完了。** JTAG IDCODE `0x81b`、ロード100%、DONE、終了コード0を確認しました。Flashへの書き込みは行っていません。USB再接続で外れていたアクセス権は、利用者の指示に基づいて対象の `/dev/bus/usb/002/010` にだけ再設定しました。USBを再接続した場合は、`lsusb` でデバイス番号を照合し、必要に応じてユーザーACLを設定してください。

書き込みスクリプトはSRAMだけを対象にし、入力とビットストリームのハッシュを確認します。今回のログ・ビットストリーム・実行結果を結ぶ `programming.json` も保存しました。[引き渡しフォルダ](../submission/README.md)には、この版への転送成功が確認できた場合だけ書き込み記録を収録します。

実機の録画（横向きへ回転）。[MP4](../submission/fpga_demo.mp4)

<img src="../submission/fpga_demo.gif" alt="Tang Primer 20Kで文字が順番に発光する動画" width="640">

## 以前の短い発光なし段階

Gitコミット `a31d3ee` の80フレーム周期版は、各文字も発光なしも16フレームでした。ビットストリームSHA256は `cc24d9046a72a3dda4f862b013312b218caf96f83e5c815ec3ec297c417e3cdb`。JTAG IDCODE `0x81b`、SRAMロード100%、DONE、終了コード0を確認しました。その後、利用者から「5段階で動いている」と回答があり、実機モニタでの動作も確認済みです。

## 先に試した配線発光版

`vga_animation` は配線上を光が走る旧候補です。SRAM書き込み後、利用者が動きを確認しました。初めは水色が青、白がピンクに見えるとの報告がありました。緑配線の接触確認後に改善し、ハイライトはグレーに見えるとのことでした。RGBのアナログ電圧は測定していません。

現行の文字発光版を書き込む際は、`vga_animation` ではなく **`vga_letter_animation`** を選びます。接続表は [FPGA試験手順](FPGA_BRINGUP.md) を参照してください。
