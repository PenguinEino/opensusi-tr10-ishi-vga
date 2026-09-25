# 配線継続とポリシリコン配線の試験 — 2026-09-25

**後続の金属配線修復で短絡143→0、断線0、公式LVS一致を達成した。** 最新は[CORE_ROUTING.md](CORE_ROUTING.md)。以下の表・GDS・`routing_snapshot.json`はその前の金属／GC比較実験の履歴として保存する。

今回の入力は `experiments/phys_desc5/build/postrepair_compacted.gds`。
282セルの下降H79/V+500候補で、B案のRTL・画像・走査タイミングは変更しない。
入力GDSと以前の比較資料を保存し、金属配線の修正とGC配線の試験を別ディレクトリに置く。

この比較実験時の改善済みコアは
[`experiments/routed_checkpoint/build/routed_checkpoint.gds`](../experiments/routed_checkpoint/build/routed_checkpoint.gds)。
金属の短絡1か所の修正と定数入力のVDD接続を合成したもので、**提出可能な完成GDSではない**。
再現手順とハッシュは[そのREADME](../experiments/routed_checkpoint/README.md)、
検証の詳細は[verification.json](../experiments/routed_checkpoint/build/verification.json)。

|検査|入力|改善済みコア|
|---|---:|---:|
|外接寸法 µm|1783.8×1756.2|1783.8×1760.3|
|実信号端子の検出|987/987|987/987|
|信号ネットの分断|0|0|
|短絡した接続成分|14|14|
|短絡成分内のネットの組合せ|153対|143対|
|公式描画DRC|3件|2件|
|公式マスクDRC|3件|2件|

改善済みコアの描画・マスクDRCの残件は、入力にも存在したCLK/RESETのBUFTHの2か所。
位置を含めて照合し、追加の違反がないことを確認した。
信号短絡、外部引き出し、フレーム統合、回路LVS、寄生込みのタイミング確認は未完了。

## 接続検証の訂正

以前の「41件のSHORT SUSPECTED」は上流の `postrepair_pins.json` を使用した結果。
この表には修復時に動いた配線端点が入り、実際のセル端子の座標と一致しない。
したがって、この件数だけでセル端子間の完全な接続を保証することはできない。

例：`_386_.B` の表の座標は `(1584.9,1586.8)` µm。
実GDSのNAND2配置と固定v59_4のLEFから復元した端子中心は `(251.1,535.9)` µm。
短絡の有無だけでなく、修復中に新たな断線を作っていないかも実端子で確認する必要がある。

設計側の `scripts/routing_diagnostics.py` でGDSのセル配置変換、配置JSONのネット割り当て、
v59_4 LEFの端子図形から独立に接続を照合する。
上流の配線端点表は配線の内部データとして残し、実端子表と区別する。

監査すると、旧表の1017点はすべて対応する実端子と同じ金属の接続成分上にあった。
座標が違うこと自体を断線とは判定しない。一方、旧表には41個の重複があり、
実端子987個のうち11個が含まれていなかった（RGB/HS/VSの8出力、CLK/RESETの2入力、
リセット同期FFの定数1入力）。この11個も含めて検査する。

実GDSとの照合は421インスタンス（282論理セル＋139 TAP/FILL）すべてで成立。
元コアは実信号端子987個が見つかり、信号ネットの分断0、短絡した接続成分14個だった。
短絡成分の中にある異なるネットの全組合せは153対。
これは推移的につながる組合せも数えるため、153か所に金属が重なるという意味ではない。
外部ポートへの引き出しと電源・定数接続は、この信号端子間検査だけでは完了を証明しない。

## 実コア上のGC橋渡し

`experiments/poly_core/build/poly_core_trial.gds` は、実際に残っていたM1の重なり1か所を
GC（ゲート用ポリシリコン、8/1）とCO（11/0）で橋渡しした試験。
抵抗用GR（8/2）は使っていない。

対象は `_079_` と `_246_` が `y=708 µm`、`x=1061.1..1071.9 µm` で重なる部分。
`_079_` のM1を局所的に切り、`x=1053,1080 µm` でM1→CO→GCへ接続する。
GCを `y=710.7 µm` へずらすことで、相手の既存V1にも重ならない形にした。

|項目|結果|
|---|---|
|GC中心線の長さ|32.4 µm|
|橋の幅|1 µm、接点と曲がり角は拡幅|
|追加コンタクト|2個|
|変更層|M1、GC、COのみ|
|コア外接寸法|1783.8 × 1756.2 µm、入力から変更なし|
|既存活性領域へのGC追加|なし。新しいMOSを作らない|
|局所接続検査|橋の左右は導通し、交差相手とは分離|
|負の対照試験|GCを接続抽出から外すと橋が断線することも確認|
|公式描画DRC|入力と同じ3件。追加・変化した違反マーカーなし|
|マスク生成後の公式DRC|入力と同じ3件のFloating SG。追加・変化したマーカーなし|
|GC/COを含めたコア全体の実端子検査|987端子検出、分断0。短絡ネットの組合せ153→143対|

検査は完成GDSから実図形を切り出し、KLayoutの接続抽出で行う。
意図した配線図だけを再描画して検査する方法ではない。
`scripts/verify_poly_core_trial.py` と `build/verification.json` が検査と結果。
これは局所の交差解消を証明するもので、コア全体のLVS合格ではない。
全体の検査でも `_079_` が短絡グループから外れたことを確認した。
残る短絡グループの数は14のままであり、「グループ数が不変だから改善なし」とも扱わない。

最初の試作では接点から細いGCへ曲げる部分に `GC.S1` が2件出た。
曲がり角まで接点の幅を保つ形に直し、再検査でこの2件は消えた。
最終結果と入力に共通して残る3件は `GC.ANT`。これらを除外したり、ルールを緩めたりしてはいない。

公式LVSデッキの `--netlist-only` による抽出も完了した。
**ネットリスト抽出の完了と、設計ネットリストとのLVS一致は別**であり、後者の合格とは扱わない。

## 金属だけでの比較

`experiments/metal_repair/build/junction_y7296/candidate.gds` は、同じ箇所を金属だけで直した比較版。
`_246_` の短いM1接続と両端のV1を、`y=708` から空いている `729.6 µm` へ移し、
両端から来る自身のM2配線を短くした。実セルの端子は移動していない。

実信号端子987個の分断0、短絡ネットの組合せ153→143対、外接寸法もGC案と同じ。
この箇所は金属だけで同等に直せたので、GC案による面積削減が実証されたとは扱わない。
金属版を改善済みの途中成果として保持し、GC版は比較用に分離する。

別の `_040_` / `_058_` のM2衝突も迂回を試した。
行をまたぐ4個のV1とM1横配線を追加する案では、対象短絡を取り除けた候補でも
M1間隔違反を新設した。DRCの増加や別ネットとの短絡を生じた候補は採用しない。
詳しい座標とログは `experiments/metal_repair/` に保存している。

`_108_` / `_173_` のM2共有区間も、別の空き列 `x=418.5 µm` へ迂回した。
この2ネットは別の場所にも重なりがあり、1区間の変更では短絡が残った。
公式DRCも3→11件へ増加したため不採用。改善済みの金属配線は引き続き
`junction_y7296/candidate.gds` を採用する。

## 定数入力と電源の接続

端子の監査で、リセット解除を同期するFF `_542_.D` の定数 `1'h1` が
VDDへつながっていないことも見つかった。1端子だけのネットなので、
「同じ信号ネットが分断していない」という検査だけではこの不足を検出できない。

`experiments/constant_tie/` では実セルのVDDラベルと接続するM2電源幹線を抽出し、
Dから上側の空き領域へM2で出て、M1でVDDへ接続した。
入力の987信号端子を調べ、VDDへ新しく加わる信号は `1'h1` のみ、
VSSは変化せず、VDD/VSSも短絡していないことを確認した。
高さは1756.2→1760.3 µm、幅1783.8 µmは変わらない。
公式描画DRCは3→2件となり、FFの `GC.ANT` が解消した。
残る2件はまだ外部へ出していないCLK/RESET入力BUFTHのマーカー。
コア単体の確認であり、全セルの電源網・外部パッド・フレームの最終検証は残る。

## ポリシリコン配線の独立試験

[poly_probeの結果](../experiments/poly_probe/REPORT.md)では、GCの長さ10/20/40/80 µmと
幅1/2/3 µmを組み合わせた12例も試した。各GC配線は独立したM1配線と交差し、
両端は固定v59_4のINV_X1のA入力へ接続する。
これは両端のゲート接続を持つ幾何試験であり、信号を駆動して遅延を測る回路ではない。

- セル付きの12例：公式描画DRC 0、公式マスクDRC 0。
- 接続抽出：各GC配線に2つのA入力が接続、交差M1とは分離。
- 否定対照：GCを切ると断線し、交差位置へCOを追加すると短絡する。
- セルなしの配線試験：描画DRCは0だが、マスクDRCではFloating SGが36件。こちらを合格扱いしない。

独立試験のGDSは `experiments/poly_probe/poly_probe_device_array.gds`。
実コアで使える局所形状が存在することは示したが、長距離GC配線の遅延保証や
自動配線全体の面積削減率を示す結果ではない。

## 版と再現

APRtools `8f6962bf2df1618d633f8a81c230fec895fc83aa`、
TR-1um `f408d3b5c23a8ebe44f02b0482a9270601e2880f`、v59_4は変更していない。
上流の変更はロック済みPCell検索パッチのみ。試験コードは設計リポジトリの `scripts/` に置く。
公式DRC/LVSはKLayout CLI 0.30.9で固定デッキをそのまま実行する。

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/poly_core_trial.py
python3 scripts/run_apr.py --design-root experiments/poly_core apr/drc_pdk.py \
  build/poly_core_trial.gds ishi_vga_core -r build/poly_core_trial.lyrdb \
  --mdp --mdp-gds build/poly_core_mask.gds
python3 scripts/run_apr.py --design-root experiments/phys_desc5 apr/drc_pdk.py \
  build/postrepair_compacted.gds ishi_vga_core \
  -r ../routing_audit/postrepair_baseline.lyrdb \
  --mdp --mdp-gds ../routing_audit/postrepair_mask.gds
python3 scripts/run_apr.py --design-root experiments/poly_core apr/lvs_pdk.py \
  build/poly_core_trial.gds ishi_vga_core --netlist-only -r build/poly_core_extraction.lvsdb
.venv/bin/python scripts/verify_poly_core_trial.py
```

入力・出力・生成コード・config・ロック・デッキのSHA256は
`experiments/poly_core/build/manifest.json` に保存する。
比較に使う入力の公式DRCレポートは `experiments/routing_audit/postrepair_baseline.lyrdb`。
描画／マスクDRCの残件があるため、これらのDRCコマンドの終了コードは非0になる。
差分比較のPASSを、コア全体のDRCゼロという意味では扱わない。

## 電気的な評価の範囲

GCを導体として接続抽出できることと、その抵抗・容量を正しく抽出できることは別。
今回の接続検査やLVS用抽出はGC配線の寄生RCを含まない。
GRの抵抗素子用モデルを、そのままGC配線のシート抵抗として流用しない。
配線前STAの余裕を、今回のGC橋渡しの遅延保証とも扱わない。

この試験で示せたのは、**固定PDKの幾何規則を守り、実コアの交差を局所的に解消できる**こと。
コア全体の配線完了、面積削減量、寄生込みの動作保証は別に評価する。
