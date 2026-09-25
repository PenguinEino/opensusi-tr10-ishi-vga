# ISHI文字の順次点灯＋消灯段階

2026-09-25の採用版。**I → S → H → I → 発光なし**を繰り返します。各文字16フレーム（約0.267秒）、発光なし64フレーム（約1.067秒）、1周128フレーム（約2.13秒）。発光なしの段階では元のロゴを表示します。

**1792.8×897.2 µm、共通VSSを除き7端子。** 外部CLK 3.15 MHz、640×480・60 Hz相当、RGB111。文字の赤い部分だけをRGB=111にし、背景・格子・電源枝の形と同期タイミングを維持します。

- [引き渡しデータとGDS](../submission/README.md)
- [コアRTL](../experiments/a_letter_scan_eco/ishi_vga_core.v)・[実行設定](../experiments/a_letter_scan_eco/config.py)
- [FPGAの書き込み記録](FPGA_ANIMATION_20260925.md)

最終提出物には左側中央の空きスペースに名前とペンギンを追加しました。[装飾工程・再現手順](submission/SILICON_ART.md)と[提出レビュー](submission/REVIEW.md)を参照してください。設定は `experiments/a_letter_silicon_art/config.py`、装飾後のSPICEは `experiments/letter_art_spice` です。以下の回路・STA結果は、装飾前後の全機能図形・抽出回路の同一性を検査して継承しています。`release/ishi_vga_letter_scan_core` は装飾前のチェックポイントとして保持しています。

## 実装と検証

既存の静止画コアに28セルを追加しました。7 bitカウンタが0〜127を循環し、前半64フレームで4文字を順に点灯、後半64フレームは発光なしにします。合計241論理セル、29 DFFです。追加セルは既存のフィラー領域に配置し、M1/M2で接続しました。元のセルの位置、外周端子、外形を維持しています。

以前の80フレーム周期版から折り返し回路を省き、6セル削減しました。追加回路の合成セル面積は60,944 µm²から56,133 µm²へ約7.9%減少しています。以前の版はGitコミット `a31d3ee` に保存されています。

追加回路は固定したAPRtools/v59_4で論理合成し、既存回路のフレーム末信号を流用しました。その信号の意味はh/vの全131,072状態で検査しています。緑と青の出力FFの入力を差し替え、文字のハイライトを加えています。

| 検証 | 結果 |
|---|---|
| 描画DRC | 0件 |
| strict LVS | 全8電気端子を含めて一致 |
| 実形状からの配線検査 | 欠落・短絡・断線0 |
| RTL／ゲート | 128フレーム連続、各672万クロックでRGB/HS/VS一致 |
| 抽出SPICE | 1990素子、20試験・922クロック一致（5 V/27℃、出力各1 pF） |
| 段階カウンタ | 全128遷移と全128二値初期状態を照合 |
| セル遅延STA | setup 274.741 ns、hold 6.687 ns、ピン容量違反なし |

配線端の同一ネット内の隙間を埋め、既存クロック枝の終端を局所的に迂回してDRCを解消しました。修正座標は `LOCAL_REPAIR`、実行記録は引き渡しデータに保存しています。標準セル内部とPDKは変更していません。

マスク生成後は以前からのCLKのFloating SG警告1件が残ります。フレーム統合は引き続き保留です。STAはセル遅延とピン容量を対象とし、配線RC・PVTの検証ではありません。添付の `.extracted` は今回のGDSを `--no-combine` で抽出した回路です。同じGDSから再抽出してバイト一致を確認し、ngspiceで状態24 bitと出力5 bitを照合しました。[抽出SPICEの条件と結果](../submission/SPICE.md)。

## 再現

依存の準備は [APRtools採用手順](APRTOOLS_ADOPTION.md) に従います。新規ディレクトリを指定してください。

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/replay_letter_animation_core.py --out build/letter_recheck
.venv/bin/python scripts/verify_letter_animation_core.py --design-root build/letter_recheck
```

凍結した静止画コア、配置表、ゲート回路は `release/ishi_vga_letter_scan_core/reproduce/` にあります。追加回路の再合成、配置、配線、局所修復、GDSのSHA256照合、DRC/LVS/STA、RTLとゲートの照合まで実行します。過去の配線発光版 `a_wire_scan_eco` と、今回の文字発光版 `a_letter_scan_eco` は別の実験です。

## 表示

FPGA実機の記録（[MP4](../submission/fpga_demo.mp4)）：

<img src="../submission/fpga_demo.gif" alt="文字の順次発光を表示するFPGA実機" width="640">

ゲートシミュレーションの観測結果：

<img src="../submission/animation.gif" alt="16/16/16/16/64フレームの発光周期" width="640">
