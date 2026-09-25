# Tang Primer 20KでのVGA実験

目的は、B案の画像と走査タイミングをFPGAで実際のVGAモニタへ出し、
6.30 MHzと6.45 MHzの両方で表示・色・同期・リセットを確認すること。
TR-1umの配線遅延やリング発振器のPVT変動を検証する試験とは区別する。

## 先に用意するもの

- Tang Primer **20K Dockセット**。ユーザーの手元の製品は[秋月117540](https://akizukidenshi.com/catalog/g/g117540/)。
- VGA入力のあるモニタとVGAケーブル。
- VGA **メス・3列15ピン**の端子台／変換基板。2列15ピンのD-subと取り違えない。
- **430 Ω抵抗9本**（できれば1%）。各色に3本ずつ使い、430 Ωと860 Ωの2枝を作る。
- 接続線。できればオシロスコープまたは周波数を測れるロジックアナライザ。
- Tang Primer 20K用のGowin EDA／Programmer。まず公式LEDサンプルの書き込みを確認する。

20KはGW2A-LV18PG256C8/I7を使用し、DockとLiteがある。
搭載発振器は27 MHz。Dockの公式サンプルではクロック端子H11、リセットT10。
今回はVGA Pmodを使わず、DockのGPIOから抵抗DACへ接続する。
旧Tang Primer（Anlogic）やTang Nano 20K、Primer 25Kのピン表を流用しない。
[Sipeed製品資料](https://en.wiki.sipeed.com/hardware/en/tang/tang-primer-20k/primer-20k.html) /
[公式27 MHzの説明](https://en.wiki.sipeed.com/hardware/en/tang/tang-primer-20k/examples/led.html) /
[公式サンプルとDockピン表](https://github.com/sipeed/TangPrimer-20K-example)

## FPGAへ入れるソース

今回の最小ASIC候補と同じ、次の2ファイルをGowinのVerilogソースへ登録する。

```text
experiments/descending_h79_v500/ishi_vga_core.v
experiments/descending_h79_v500/ishi_logo.v
```

コアモジュールは `ishi_vga_core`。
端子は `clk`, `reset_n`, `r[1:0]`, `g[1:0]`, `b[1:0]`, `hsync`, `vsync`。
この候補はRTLとASIC合成後ネットリストで6.30/6.45 MHzの全フレーム比較に合格済み。
FPGAにはRTLを合成する。`*_pnr.v`、TR-1umのセルモデル、APRtoolsのLibertyは登録しない。

FPGA側に薄いトップラッパを用意し、27 MHz→PLL／整数分周→コアの `clk`、
ボタンとPLLのLOCK→コアの `reset_n`、RGB/同期→外部端子、と接続する。
PLLが安定するまでリセットを保持する。コアには解除の2段同期が入っている。
起動時に必ず一度リセットを入れ、FPGAの初期値だけに依存しない。

## クロック

まず6.30 MHz用と6.45 MHz用の2つの設定／ビットストリームを作る。
動的なクロック切り替えは初回試験には不要。
GowinのPLL IPで対象デバイスに適合する設定を生成し、実際の出力周波数とLOCKを確認する。
低周波を直接出せない設定では、PLLの高い出力を整数分周して使用する。
PLL／生成クロックのタイミング制約も入れる。

27 MHzから4クロックと5クロックを混ぜて平均6.3 MHzにする方法では、各周期が一定にならない。
今回の定周期クロック試験ではPLLまたは適切な外部クロック源を使う。
外部クロックを使う場合は、接続先のGCLK端子と3.3 Vの電気条件を確認する。

## VGA配線

Dockの **J5（RGB LCDと共用の2×6ヘッダ）** を使う。実験中はRGB LCDを外す。
以下は今回のVGA用割り当てであり、LCDとして使うときの色割り当てとは異なる。

|J5回路図上の端子番号|FPGAピン名|今回出す信号|VGA側への接続|
|---:|---|---|---|
|5|L9|`r[1]`|430 Ω→VGA 1|
|6|N8|`g[1]`|430 Ω→VGA 2|
|7|N9|`b[1]`|430 Ω→VGA 3|
|8|N7|`vsync`|VGA 14|
|9|N6|`r[0]`|860 Ω→VGA 1|
|10|D11|`g[0]`|860 Ω→VGA 2|
|11|A11|`b[0]`|860 Ω→VGA 3|
|12|B11|`hsync`|VGA 13|
|3, 4|GND|GND|VGA 5, 6, 7, 8, 10|
|1, 2|+3.3 V|使用しない|未接続|

番号はSipeed回路図のOdd/Even表記で、一般的なPmodの行ごとの番号とは異なる。
物理位置を数字だけで決めず、基板のFPGAピン名・GND・電源表記を照合する。
これは番号の付け方の違いであり、Pmodとの電気的な互換性を否定するものではない。

Dock 3713（Rev 1.1）と3714（Rev 1.3）のJ5接続を照合し、同じことを確認した。
L9/N8/N9/N7/N6はBank3、D11/A11/B11はBank7。SOMの回路図でBank3のVCCO3は
+3.3 V、Bank7も標準3.3 V設定。公式RGBサンプルのCSTもこれらをLVCMOS33としている。
ピン対応は[公式CSTの固定コミット](https://github.com/sipeed/TangPrimer-20K-example/blob/e469df4c0c9c41824f405a8515decf24ef1e8e6f/RGB_lcd/800x480_5inch_lcd/src/lcd.cst)、
ヘッダ番号は[公式Dock 3714回路図](https://api.dl.sipeed.com/file/download?file_url=TANG/Primer_20K/02_Schematic/Tang_Primer_20K_Dock_3714_Schematics.pdf)で確認した。
保存資料の版とSHA256は[調査記録](../research/fpga_dock/README.md)。

赤の例。緑・青も独立して同じものを組む。添字1がMSB。

```text
r[1] ── 430 Ω ──────────┐
                       ├── VGA pin 1 (R)
r[0] ── 430 Ω ── 430 Ω ─┘
```

|VGA端子番号|接続先|
|---:|---|
|1|赤の抵抗2枝の合流点|
|2|緑の抵抗2枝の合流点|
|3|青の抵抗2枝の合流点|
|13|`hsync` GPIO|
|14|`vsync` GPIO|
|5, 6, 7, 8, 10|Dock GND|
|4, 9, 11, 12, 15|今回の回路では未接続|

VGA端子番号は部品の刻印／仕様書で確認する。嵌合面から見た図とハンダ面から見た図は左右反転する。
RGBのGPIOをVGA入力へ直結しない。HS/VSはRGB用の重み付き抵抗には通さない。
配線は短くし、GNDを共通にする。モニタに75 Ω終端があるので、こちらで75 Ωを追加しない。
端子番号と75 Ω終端方式の出典は[DigilentのVGA資料](https://digilent.com/reference/_media/nexys_vga/nexys_vga_rm.pdf)の1ページ。

抵抗は理想3.3 V GPIOを仮定した設計値。430 Ω並列860 Ωは約286.7 Ωなので、
両ビットHighで `3.3 × 75 / (286.7 + 75) ≈ 0.684 V`。
4段階は理想値で0 / 0.228 / 0.456 / 0.684 V。
以前の概算420 Ω/840 Ωでは最大0.697 Vだが、今回は入手しやすい430 Ω9本で2:1の比を保つ。
GPIOの出力抵抗と抵抗誤差で実測値は変わる。RGB MSBは最大約6.7 mAを供給するので、
3.3 Vバンクを使い、GowinのI/O制約はLVCMOS33・DRIVE=8 mAを目安にする。
モニタを接続した状態で白部分をオシロ測定できれば、振幅も確認する。

## Dockの立ち上げ

1. PCとDockの **USB-JTAG** 側をデータ対応USBケーブルでつなぐ。
2. DockのDIPスイッチ1でコアを有効にする。公式説明では下側が有効。
3. Gowin EDAでデバイスを **GW2A-LV18PG256C8/I7（C版）** に合わせる。
4. [公式Dock LED手順](https://en.wiki.sipeed.com/hardware/en/tang/tang-primer-20k/examples/led.html)を実行し、まずSRAM書き込みでLEDの制御を確認する。

コア有効化とデバイス選択の根拠は[SipeedのFAQ](https://en.wiki.sipeed.com/hardware/en/tang/tang-primer-20k/primer-20k.html#Questions)。

## 試験順と記録

1. LEDサンプルで書き込み経路・発振器・基板の有効化を確認する。
2. 6.30 MHzでリセットを保持→解除し、HS/VSを測る。モニタの信号検出と表示を確認する。
3. RGBのビット順、青系の色、ロゴの形、中央配置を参照画像と比べる。
4. 6.45 MHz版へ書き換え、同じモニタで同期・画面の横流れ・ちらつき・位置を確認する。
5. それぞれでリセットを繰り返し、同じ画像に戻るかを確認する。
6. 数分表示し、可能なら別のモニタでも試す。モニタ機種、実測クロック、HS/VS、表示状態を記録する。

|項目|6.30 MHz|6.45 MHz|
|---|---:|---:|
|水平周波数|31.500 kHz|32.250 kHz|
|垂直周波数|60.000 Hz|61.429 Hz|
|1行の時間|31.746 µs|31.008 µs|
|HSのLow幅|3.810 µs|3.721 µs|
|VSのLow幅|63.492 µs|62.016 µs|

ロゴの表示領域は512×432画素、余白は左右64画素・上下24行。
論理画素は横4画素分・縦4行分なので、拡大された画素が正方形に見えることを確認する。
参照画像は [最小候補の合成後シミュレーション画像](area_search/selected/gates_630.png)。
CLI環境なら `xdg-open docs/area_search/selected/gates_630.png` で開ける。

この文書を作った時点では、ボード別CST・PLLラッパ・FPGAビットストリームは未生成。
Dock＋抵抗DACで進める。周波数を安定して受けるかは実モニタの試験結果で判断する。
