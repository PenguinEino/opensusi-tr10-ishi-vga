# VGA実装と検証記録

最新のA半枠試験は [HALF_A_FEASIBILITY.md](HALF_A_FEASIBILITY.md)。共通VSSを除く7端子で機能検証したが、最小診断GDSは1783.8×1717.7 µmで、1800×900 µmには未達。以下の旧B/RGB222版のDRC・LVS結果をA半枠版へ流用しない。

**最新の作業目標は半枠・7ピンへ変更。** [HALF_SLOT_REDESIGN.md](HALF_SLOT_REDESIGN.md) に新しい字形・黒背景・RGB111・RESETなしの候補と実測を記録。1783.8×758.6 µm、短絡・断線0だがLVS等は未完了。以下は既存A/Bの履歴。

2026-09-25。現在の採用は **B案（21矩形）**。37矩形版の記録は`docs/validation/`に保存。B案の記録は`docs/validation_b/`。

最新のA再試行は [A_ROW_PLACEMENT.md](A_ROW_PLACEMENT.md)：[31構成の論理探索](A_RETRY.md)後、行割当の改善により同じ382セルが1783.8×1744.7 µmに縮んだ。1800角には入ったが短絡75ネット対が残る診断段階。統合はユーザー指示で停止中。リングは不搭載へ変更し、[信号10本＋電源2本](PIN_PLAN.md)を使用する。[RESET省略・直接RGBのbit削減](PIN_REDUCTION_REVIEW.md)は未採用の検討案。以下は既存B実装と過去の実行履歴。

後続の[10信号の外周引き出し](CORE_ESCAPE.md)も完了。現在の寸法は1797.3×1763.9 µm、短絡・断線0、公式描画DRC 0、strict公式LVS一致。以下の1793.7×1760.3 µmは引き出し前のコア内部配線の値。

**282セル版のコア内配線が完了し、1793.7×1760.3 µm、短絡・断線0、公式LVS一致。** 公式描画DRC 0件、マスクのFloating SG警告2件。外部ピンとフレームは未統合で、提出用チップGDSではない。[最新GDS・検証・定数入力のLVS変換](CORE_ROUTING.md)を参照。

追加の[面積探索](AREA_OPTIMIZATION.md)でB案の画素と外部動作を維持した282セル・407,684 µm²の候補を得た。その実端子接続を検査し直し、[配線修復](CORE_ROUTING.md)で短絡を解消した。rootのRTL/config/outと以下の記録は375セル版の比較基準として維持している。最適化版のRTL・合成検証ハッシュは `docs/area_search/`、最新物理結果は `docs/core_routing_snapshot.json` に記録している。

## 実装した動作

- トップ: `rtl/ishi_vga_core.v` の `ishi_vga_core`。
- 入力: `clk`、負論理 `reset_n`。出力: `r[1:0]`, `g[1:0]`, `b[1:0]`, `hsync`, `vsync`。
- h=0..199、v=0..524。水平有効160tick、HS Low=164..187。垂直有効480行、VS Low=490..491。
- 6.30 MHzで31.5 kHz/60 Hz、6.45 MHzで32.25 kHz/約61.43 Hz。RGBは1tick=横4画素。
- ロゴ128×108を512×432で中央配置。配置領域はh=[16,144)、v=[24,456)。ロゴ内にも白い余白があるため、着色部分の外接寸法はこれより小さい。
- `assets/logo_rectangles.json` の21矩形（B案）を `scripts/generate_logo_rtl.py` が比較回路へ変換。ROM/RAMなし。同色矩形をOR、元の重ね描き順を色の優先順位で保持する。
- 座標減算器を省くため、比較閾値を画面座標へ移してある。yは `v[9:2]`。24行のオフセットは閾値へ6を足すことで表現する。
- RGBとHS/VSを同じカウンタ値から同時にレジスタ出力し、組み合わせ回路のグリッチを外部へ出さない。表示外は黒、表示内の背景は白。
- リセットは非同期アサート、2段FFで解除を同期化。解除後2クロックは黒・同期非アクティブ、3クロック目に座標(0,0)を出す。電源投入時は外部から必ずリセットを与える。

### RGB222固定パレット

|番号|用途|R,G,B（0..3）|6 bit|
|---|---|---|---|
|0|白|3,3,3|111111|
|1|水色の上下横線|1,2,3|011011|
|2|赤文字|3,1,1|110101|
|3|シアン線|1,3,3|011111|
|4|濃青の帯|1,1,3|010111|
|5|紫の帯|2,2,3|101011|

`ishi_logo.v`は色マスクから直接RGBへ変換する。外部動作に不要な3 bit色番号レジスタは持たない。

## 再現

Ubuntu 24.04 arm64で実行した。`make setup`はローカル`.venv/`と`.tools/`へ導入する。ホストにPython/pip、C/C++コンパイラ、CMake、Bison、Flex、Tcl実行ライブラリ、zlib開発環境が必要。他OSの導入手順ではない。

```sh
git submodule update --init --recursive
make setup
make check
make synth
make sta
make test
```

`make test`は矩形の独立ラスタ描画を期待値に使い、RTLと、存在する場合は**最終BUFTH挿入後ネットリスト**を照合する。古いネットリストの再検証を避けるためRTL変更後は先に`make synth`を行う。

主な生成物:

|パス|内容|
|---|---|
|`out/ishi_vga_core_pnr.v`|固定v59_4へ合成した最終ネットリスト|
|`build/verification.json`|照合結果と対象RTL/ネットリストのSHA256|
|`build/rtl_630.png`, `build/gates_630.png`|実際のシミュレータ出力から復元した640×480画像|
|`out/STA_ishi_vga_core.txt`|配線前STA|
|`layout/step4/place_step4_fill.gds`|配置途中のGDS。配線済みでも提出物でもない|

## 比較基準375セル版の実測結果と限界

- RTLとBUFTH挿入後ゲートモデルの各々で6.30/6.45 MHzを検証。各315,017tick、合計1,260,068tickを照合しPASS。フレーム折り返し、帰線期間、途中リセット、クロック停止中のリセット、解除の同期化を含む。
- 合成: **375セル（FF 28 / 組み合わせ347）、セル面積495,252 µm²**。セル幅合計8,337.6 µm。37矩形版の491セル・617,462 µm²からセル数23.6%、セル面積19.8%減。配線・TAP/FILL・パッド・リング発振器はこの面積に含まない。
- OpenSTA 3.1.0、typ 5 V/25℃、155 ns周期: reg→reg slack **111.806 ns**、reg→out **118.194 ns**、hold **5.235 ns**。
- STAは配線容量なし、理想クロック。PVT全コーナー、配線後遅延、クロック分配、reset recovery/removalの保証ではない。ゲートシミュレーションも単位遅延モデルであり、STAの代用ではない。
- B案を7行×1598.4 µmで配置し、配置検証は全数OK。診断用の行間900 µmでstep6まで配線後、短絡修正前のGDSを圧縮した実測は **1611.0×2905.0 µm**（x=-6.3..1604.7）。37矩形版の9行・5544.9 µmから高さ47.6%減だが、1800×1800 µmには収まらない。行数も変更しているため、矩形削減だけの効果を分離した比較ではない。
- step6の簡易接続検査は **75件のSHORT SUSPECTED** を報告。これは75個の独立した物理短絡の数とは限らない。幅・間隔の簡易チェックが0件でも接続検証は未合格。枠外であるためstep7以降の短絡修正・最終統合は実行していない。最終の公式DRC/LVSとは別の検査である。
- 参考：旧37矩形版では9行×1598.4 µmの配置を生成し、上流の配置検証は全数OK。コンパクトなチャネル予算ではstep6が空きトラック不足で停止した。診断用に行間900 µmへ拡張するとstep6まで生成できたが、短絡修正前GDSを独立に圧縮した実測は **1611.0×5544.9 µm**（x=-6.3..1604.7）。1800×1800 µmに収まらず、step7の短絡修正を中断した。この寸法は今回の配置・配線の結果であり、回路の最小可能面積を証明するものではない。
- 最終フレーム、リング発振器、公式DRC/LVS、FPGA実機、モニタ接続は未完了。

### 比較基準375セル版の配置配線を再現するとき

`config.py`に初期配置の`CH_HEIGHTS`と、診断用に拡大した`ROUTE_CH_HEIGHTS`を明記した。後者は提出可能な予算ではない。`make place`/`make route`は探索用で、テープアウトの完了コマンドではない。

```sh
make place
# 診断目的。現行配置は1800 um内に収まらない
python3 scripts/run_apr.py apr/route.py --to 6
python3 scripts/run_apr.py apr/squeeze_channels.py \
  --in-gds layout/step6/route_step_2_routed_raw.gds \
  -o build/diagnostic_b_compacted.gds \
  --pin-map-in layout/pin_map.json --pin-map-out build/diagnostic_b_pins.json \
  --net-shapes-in layout/net_shapes.json --net-shapes-out build/diagnostic_b_shapes.json
```

この375セル版からの改善は[面積探索](AREA_OPTIMIZATION.md)と[コア配線](CORE_ROUTING.md)に記録した。64×54への変更は行わず、B案の全画素を維持した。

配線完了→接続検証→フレームと任意リングの統合→公式DRC/LVS→配線後タイミング・実機の順で残件を解消する。`gen_top_routing_plan.py`にはI2C由来の`PAD_ONLY_NETS={"DIS":"P7"}`も残るため、フレーム統合時にはVGAに不要な接続が生成されないか確認する。

### B案への変更内容

水色の輪郭18矩形のうち、上下の長い横線2矩形だけを残した。他の色・矩形の重ね順・VGAタイミング・クロック・リセットは共通。`assets/logo_rectangles_original37.json`に元の矩形を保存している。比較画像生成スクリプトはこの元データを使うため、B案への変更後もA〜Fの比較を再生成できる。

B案のラスタ参照と、ユーザーが選んだ`B_outline_bars.png`の全画素一致を検査する。RTLと合成後ネットリストの出力はそのラスタ参照の全tickと照合する。旧37矩形版のネットリスト・配置は`build/variant_a_37/`へ退避し、新しい`out/`と`layout/`でB案をビルドした。

## ピンとクロック

`config.py`の`PAD_MAP`が暫定実装表。フレーム統合前なのでボンディング表の確定版ではない。

|GIO pad|用途|
|---|---|
|1|CLK入力|
|2|RESET_N入力|
|3,4,5|R1,G1,B1|
|6|VSYNC|
|7,9,10|R0,G0,B0|
|11|HSYNC|
|12|リング出力用に予約（現状はHi-Z）|
|13,14,15|未使用、Hi-Z|
|8,16|固定VSS,VDD|

外部CLK入力は常に残す。リング発振器は`RING_OSC_ORIGIN=None`で現在未搭載。配線の収まりを確認してから、独立した出力pad12へ接続し、基板ジャンパでpad1へ戻す。RTL内の発振器やクロックMUXは追加しない。

Tang Primer 20Kで試す場合も同じコアを使い、クロック生成・ボードの端子割当はFPGA側ラッパで分離する。今回PLLや基板固有CSTはまだ作っていない。6.45 MHzでのシミュレーションPASSは、モニタがそのタイミングを受け入れる証拠ではない。

5 V ASICへのCLK/RESETは適切なレベル変換を行う。RGB/同期は3.3 V駆動の5 V入力対応バッファを経てVGA DACへ出す。VGAの75 ΩへASICセルから直接接続しない。電気条件は`APRTOOLS_ADOPTION.md`と固定セル/フレーム資料を参照。

## 現行依存に対する記録済み修正

APRtools本体の世代は変更していない。`patches/aprtools-pcell-technology.patch`は5箇所のPCell検索の第2引数を`"*"`から`"TR-1um"`へ変更するだけ。

固定PDKの`cells.tr_1um("TR-1um")`はそのtechnologyでライブラリを登録する。KLayout 0.30.6では`library_by_name("TR-1um","*")`はNone、`library_by_name("TR-1um","TR-1um")`はvia_1を持つライブラリを返すことを実行確認した。以前のままではstep6がAttributeErrorで停止した。

ロックにパッチ自身と変更後5ファイルのSHA256を記録し、検査は**その差分だけ**を認める。他の上流変更は拒否する。新規checkoutでは`python3 scripts/apply_toolchain_patches.py`で適用する。セル/フレーム資産は変更していない。

また、上流の配置ドキュメントが参照する`apr/insert_row_buffers.py`は固定コミットに存在しない。旧世代から探して実行してはいけない。今回は行別クロックバッファを未挿入であり、その分配検証は物理実装の残件である。

## 行パターン共用の追加実験

[実験記録](ROW_PATTERN_EXPERIMENT.md)。4 bit行番号版401セル、直接選択版389セルとなり、現行Bの375セルを上回った。直接選択版の配線途中の圧縮後コアも1611×3520.6 µmで悪化。両版の機能同一性は検証済みだが、採用はせず、本体は矩形方式のB案を維持している。
