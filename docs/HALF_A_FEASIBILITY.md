# Aの形を保った半枠化の追加試験

2026-09-25。「A案でも1800×900 µmくらいにできないか」に対する実装・測定記録。

**今回の探索では未達。Aの37矩形の座標を変えないRGB111・黒背景版の最小診断GDSは1783.8×1717.7 µmだった。** 900 µmへは、さらに高さを約47.6%減らす必要がある。これはAが原理的に収まらないという証明ではなく、下記の論理・配置・配線を実行した範囲の結論。

前回の1783.8×758.6 µmの格子版は、字形と配線模様を描き直した別候補。Aを同じサイズに収めた結果として扱わない。[前回の半枠比較](HALF_SLOT_REDESIGN.md)は保存した。

## 今回維持したものと削減済みのもの

- `assets/logo_rectangles_a_corrected.json` の37矩形、128×108、画面内の位置・線幅・文字形状を維持。左下は訂正後の `[1,25,62,46,65]`。
- 色はRGB111、黒背景。元のRGB222・白背景のAと同色ではない。通常候補のパレットは `[0,3,4,3,1,5]`（背景、各矩形の色番号順）。赤・水色・青・紫の4前景色。
- 外部CLK 6.30 MHz、1行200 tick、525行。640×480・60 Hz相当。格子版の3.15 MHzとは異なる。
- RESETなし、リングなし、外部色デコーダなし。VDD、CLK、HSYNC、VSYNC、R、G、Bで**共通VSSを除いて7端子**。主催者の確定したパッド番号を意味しない。
- フレーム統合は停止したまま。サブエージェントは使用していない。

`cover3`/`cover2`だけは追加の減色比較で、通常候補とは分ける。矩形座標は同じだが、色を統合した部分の境界は見えなくなる。未採用。

## 論理合成の比較

全て固定APRtools/v59_4の同じ合成入口を実行。面積はBUFTH挿入後の論理セル合計で、配線・TAP/FILLを含まない。

|試験（`experiments/`以下）|変更|セル数|セル面積 µm²|
|---|---|---:|---:|
|`a_half_a128_black`|黒背景、H63/V500、矩形判定|361|475,365|
|`a_half_a143_x`|Hを143開始にして、ロゴ座標を7 bitへそろえる|415|527,330|
|`a_half_a143_x_direct`|7 bit座標＋色の直接論理式|424|538,234|
|`a_half_a143_y`|7 bit座標、Y区間を共有|停止|—|
|`a_half_a_bitmap_rows`|各RGB bitで同じ行を共有|579|734,861|
|`a_half_a_bitmap_rowcode`|21種の行へ5 bitの番号を付ける|694|889,145|
|`a_half_a_bitmap_rowgray`|行番号をGray符号化|680|862,843|
|`a_half_a_bitmap_setclear`|境界イベントでRGBをset/clear|540|708,557|
|`a_half_a_bitmap_toggle`|境界イベントでRGBを反転|521|685,142|
|`a_half_a_bitmap_tt`|全画素の真理値表をEspressoで最小化|1018|1,276,300|
|`a_half_a_cover4`|上の色に隠れる部分をdon't-careにして矩形を統合|364|473,762|
|`a_half_a_direct4`|H63のまま、共通色マスクを直接共有|**344**|**459,969**|
|`a_half_a_cover3`|追加減色：紫を青へ統合|停止|—|
|`a_half_a_cover2`|追加減色：配線・帯を水色へ統合、文字は赤|315|422,761|

停止した2件はABCが内部バッファとしてBUFTHを選び、固定版`insert_bufth.py`の「既にBUFTHが入っている」検査で停止した。外部CLKのBUFTH挿入まで完了した合成結果とは数えない。検査の無効化や上流コードの変更はしていない。

344セル版は、R/G/Bを別々に求め、青成分を持つ図形の和などを明示的に共有したもの。黒背景のAと全画素一致する。候補の優劣はこの合成フローでの実測であり、行共有やイベント駆動が一般に不利という結論ではない。

## 配置・配線後の実測

|試験|行数|GDSの幅×高さ µm|実端子の短絡対 / 断線|
|---|---:|---:|---:|
|`a_half_a_black_phys6`|6|1783.8×2889.5|未検査|
|`a_half_a_black_anneal6`|6|**1783.8×1717.7**|47 / 0|
|`a_half_a_direct4_phys5`|5|セル1個がTAP間へ入らず停止|—|
|`a_half_a_direct4_phys5s11`|5|配置seed変更後もセル1個が入らず停止|—|
|`a_half_a_direct4_tight5`|5|1794.6×2814.6|未検査|
|`a_half_a_direct4_anneal5`|5|行割当探索後のパッキングで停止|—|
|`a_half_a_direct4_repack5`|5|1794.6×1794.0|36 / 0|

6行版はネットがまたぐ行間の合計を447から149へ減らして配線した。GDSの実セル540個・実信号端子1194個をLEFと照合し、欠落端子0、断線0、短絡47ネット対（13成分）。採用可能な完成回路ではない。

344セルの5行版はセル総幅7743.6 µm。最初の行幅1771.2 µmでは総容量は足りてもTAP間の断片化で収容できなかった。行幅を330サイト=1782.0 µmへ広げ、行幅のばらつきを0.5%に制限すると配置できた。さらに行割当を探索し、詰め方に合うよう3行のセル順序を変えた。全セルを保持し、固定上流の`pack_row`と`verify_placement.py`を通している。

5行版の行間通過数合計は127まで減ったが、配線チャネルは内部で52、52、72、73トラック必要だった。6行版の48、39、42、55、45トラックに比べ、行を減らした利益が消えている。5行版の実セル427個・実信号端子1153個、欠落端子0、断線0、短絡36ネット対（7成分）。**セル数を約5%減らし、セルを1行減らしても、今回の配線後面積は改善しなかった。**

追加減色の315セル版もセル総幅7117.2 µmあり、同じ行幅では4行の容量を超える。5行版の配線は未実行なので、その最終寸法は主張しない。

## 検証範囲と成果物

12件の完走した論理候補は、RTLと最終BUFTH挿入後ネットリストの両方で同期獲得後2フレーム・210,000 tickを照合した。各実装と独立した元矩形の描画結果を参照している。344セル版の参照フレームは361セル版とバイト単位で同一。

試験側だけでFFを0へ初期化している。合成するRTLに初期値やRESETはない。この試験は任意初期状態の形式検証、アナログ起動試験、実配線遅延を含むSTA、モニタ実験ではない。

今回のA半枠試験は**公式描画DRC・MDP・LVS・配線後STA・端子引き出し・フレーム統合を未実施**。寸法が未達で短絡も残る診断段階であり、旧BのDRC/LVS合格を流用しない。

- 最小寸法の診断GDS：[a_half_a_black_anneal6/build/diagnostic_compacted.gds](../experiments/a_half_a_black_anneal6/build/diagnostic_compacted.gds)。`build/ishi_vga_half_a_diagnostic.gds` はこれへのリンク。
- GDS SHA256：`f958cbde0d3be19add0c8c656591d76d1aec63a90ebc9ea5d5ba8a0bfb98c272`。
- 最少セルの同一画像RTL：[a_half_a_direct4/ishi_logo.v](../experiments/a_half_a_direct4/ishi_logo.v)。物理最小候補とは別。
- [344セル版のゲートシミュレーション画像](../experiments/a_half_a_direct4/build/gates.png)。VSYNC起点のダンプを画面起点へ戻し、参照画像との全tick一致を確認して生成。
- [機械可読な結果・使用ファイルのSHA256](half_a_results.json)。旧B保存版38ファイル、前回半枠比較201ファイルはハッシュ一致を再確認。

## 再現・版の区別

APRtools `8f6962bf2df1618d633f8a81c230fec895fc83aa`、TR-1um `f408d3b5c23a8ebe44f02b0482a9270601e2880f`、v59_4を維持。[採用規約](APRTOOLS_ADOPTION.md)と[ロック](../toolchain.lock.json)を参照。上流には記録済みPCell検索パッチ以外の変更なし。

各候補の`source_manifest.json`と`config.py`が入力の正本。生成スクリプトは既存候補を上書きしない。今回使った入口は以下。生成処理を再実行する場合は、候補ディレクトリがまだない作業コピーを使う。

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/half_a_cover_trial.py direct4
.venv/bin/python scripts/run_apr.py --design-root experiments/a_half_a_direct4 syn/syn.sh
.venv/bin/python scripts/half_slot_trial.py verify a_half_a_direct4

# 記録済みの5行物理試験を参照元にする追加配置
.venv/bin/python scripts/half_a_tight_rows.py seed
.venv/bin/python scripts/a_row_placement.py route a_half_a_direct4_tight5
.venv/bin/python scripts/half_a_tight_rows.py prepare
.venv/bin/python scripts/a_row_placement.py solve a_half_a_direct4_anneal5
# 上記solveは記録したセル収容エラーで停止する。その行割当を次が再配置する。
.venv/bin/python scripts/half_a_repack.py
.venv/bin/python scripts/report_half_a_trials.py
```

`half_a_tight_rows.py`の`prepare`は元の準備マニフェストを保存し、行幅制約を1.025から1.005へ明示変更して現在のマニフェストを更新する。`a_half_a_direct4_anneal5_incomplete_config`は準備に失敗した退避物で、候補に含めない。

継承したconfigの古いコメントにはリングを後から載せる記述があるが、実行設定は全候補で`MACRO_MODE='none'`、`RING_OSC_ORIGIN=None`、`PAD_MAP={}`。リングは作らず、既存のハッシュ付きconfigのコメントだけを後から書き換えない。

## 判断

7端子化は実装・機能検証できた。Aの座標と現在のRGB111配色を保った1800×900 µm化は、今回の14論理候補と配置・配線試験では達成していない。引き続きAを優先するなら、次に比較すべきは配線模様を残しつつ線幅・文字間隔を共通の格子へそろえる案。これはAの座標を変える別の見た目候補となり、まだ合成・配線結果はない。
