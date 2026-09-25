# ISHI文字の順次点灯＋消灯段階

2026-09-25の採用版。**I → S → H → I → 発光なし**を繰り返します。各段階16フレーム、1周80フレーム（約1.33秒）。発光なしの段階では元のロゴを表示します。

**1792.8×897.2 µm、共通VSSを除き7端子。** 外部CLK 3.15 MHz、640×480・60 Hz相当、RGB111。文字の赤い部分だけをRGB=111にし、背景・格子・電源枝の形と同期タイミングを維持します。

- [引き渡しデータとGDS](../release/ishi_vga_letter_scan_core/README.md)
- [コアRTL](../experiments/a_letter_scan_eco/ishi_vga_core.v)・[実行設定](../experiments/a_letter_scan_eco/config.py)
- [FPGAの書き込み記録](FPGA_ANIMATION_20260925.md)

## 実装と検証

既存の静止画コアに34セルを追加しました。フレーム分周4 bitと5段階の状態3 bitに分け、カウンタを小さくしています。合計247論理セル、29 DFFです。追加セルは既存のフィラー領域に配置し、M1/M2で接続しました。元のセルの位置、外周端子、外形を維持しています。

追加回路は固定したAPRtools/v59_4で論理合成し、既存回路のフレーム末信号を流用しました。その信号の意味はh/vの全131,072状態で検査しています。緑と青の出力FFの入力を差し替え、文字のハイライトを加えています。

| 検証 | 結果 |
|---|---|
| 描画DRC | 0件 |
| strict LVS | 全8電気端子を含めて一致 |
| 実形状からの配線検査 | 欠落・短絡・断線0 |
| RTL／ゲート | 80フレーム連続、各420万クロックでRGB/HS/VS一致 |
| 段階カウンタ | 全80遷移と全128二値初期状態を照合 |
| セル遅延STA | setup 274.527 ns、hold 6.687 ns、ピン容量違反なし |

配線端の同一ネット内の隙間を埋め、既存クロック枝の終端を局所的に迂回してDRCを解消しました。修正座標は `LOCAL_REPAIR`、実行記録は引き渡しデータに保存しています。標準セル内部とPDKは変更していません。

マスク生成後は以前からのCLKのFloating SG警告1件が残ります。フレーム統合は引き続き保留です。STAはセル遅延とピン容量を対象とし、配線RC・PVTの検証ではありません。添付の `.extracted` は今回のGDSを `--no-combine` で抽出した回路です。旧静止画版のngspice結果を、この版の結果として流用していません。

## 再現

依存の準備は [APRtools採用手順](APRTOOLS_ADOPTION.md) に従います。新規ディレクトリを指定してください。

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/replay_letter_animation_core.py --out build/letter_recheck
.venv/bin/python scripts/verify_letter_animation_core.py --design-root build/letter_recheck
```

凍結した静止画コア、配置表、ゲート回路は `release/ishi_vga_letter_scan_core/reproduce/` にあります。追加回路の再合成、配置、配線、局所修復、GDSのSHA256照合、DRC/LVS/STA、RTLとゲートの照合まで実行します。過去の配線発光版 `a_wire_scan_eco` と、今回の文字発光版 `a_letter_scan_eco` は別の実験です。
