# 旧コアの抽出SPICE過渡解析（履歴）

現在はクロック4分岐修正版へ更新済みです。[変更・再検証](reviews/submission_manufacturing_response.md)／[現行提出仕様](../submission/SPEC.md)。以下は旧GDSの記録を保存したものです。

2026-09-25。前回のコア引き渡し時点では、RTL／ゲート機能試験、LVS、セル遅延STAまでで、抽出回路のngspice過渡解析は未実施だった。本記録は、その後に追加実行した結果。

**引き渡した最終GDSから直接抽出した回路で、選択した5試験・計668クロックのカウンタ状態と出力が一致した。** 回路やGDSを変更せず、試験を追加した。フレーム統合は保留を維持する。

## 対象と条件

- GDS：`release/ishi_vga_grid_power_core/src/ishi_vga_grid_power.gds`、top `ishi_vga_core`。
- GDS SHA256：`3bcfd73d98e2adca5b78eb20978a6145960e8023e60527ec7e960979cb86617e`。
- [抽出そのもの](../experiments/a_power_spice/build/core.extracted)／[ngspice向け識別子変換後](../experiments/a_power_spice/build/core_sim.spice)／[抽出・変換の監査記録](../experiments/a_power_spice/build/extraction_manifest.json)。
- 固定APRtools `8f6962bf2df1618d633f8a81c230fec895fc83aa`、固定TR-1um PDK `f408d3b5c23a8ebe44f02b0482a9270601e2880f`。v59_4の最終配置を使用。
- `klayout_extract.py --no-combine`。FILL内素子も含む階層展開後1774素子。素子のW/Lと拡散面積・周長を保持し、並列MOSをまとめない。
- ngspice 46+、実ログのソルバーはSPARSE 1.3。`-n` でユーザーの `.spiceinit` を無効化。既定の許容差、積分法 `trap`、最大時間刻み1 ns。
- PDK既定モデル、VDD 5 V、27℃、外部CLK 3.15 MHz、立上り・立下り2 ns。RGB／HSYNC／VSYNCそれぞれに仮定負荷1 pF。

モデルのMOS内部容量・拡散容量は使うが、**金属配線の抵抗・容量を抽出したPEXではない**。パッド・フレーム・外部DAC・75 Ω負荷は含めない。

## 結果

|試験ディレクトリ|内容|照合クロック数|結果|
|---|---|---:|---|
|`upper_init`|上側帯・電源枝・色境界、HSYNC|110|PASS|
|`lower_init`|下側帯・拡散帯の切れ目・電源枝、HSYNC|110|PASS|
|`vsync_init`|VSYNC開始、2行のLow、終了|210|PASS|
|`frame_wrap_init`|垂直カウンタ1023→0→500の折り返し|110|PASS|
|`powerup`|FFの状態指定なし、電源0→5 Vランプ|128|PASS|
|`upper_reference`|独立したLVS参照回路で上側試験を再実行|110|PASS|

抽出回路の合計は668クロック。参照回路の110クロックは別集計。実際に照合したRGBは黒・青・水色・赤・紫の5色すべてを含む。各クロックでh/vの17 bitとRGB／HS／VSの5 bitを確認した。

[集約JSON](power_grid_spice.json)に各試験の結果と入力・波形・ログのハッシュを保存した。個別の `verification.json`、`samples.json`、`tb.spice`、`ngspice.log`、`wave.raw` は `experiments/a_power_spice/build/<試験名>/` にある。`wave.raw` は実際のngspiceバイナリ波形。

判定は各クロック立上り開始から150 ns後に行い、1.5 V未満をLow、3.5 V超をHigh、その間は不合格とする。出力の期待値は採用画像の凍結済み `designs/grid_power/tests/expected_frame.hex` を使い、カウンタ遷移も別途照合した。

試験内で切り替わった出力の、外部CLKの50%点から出力50%点までの観測最大値は抽出回路で **19.118 ns**、参照回路の上側試験で19.330 ns。これは選択した遷移・負荷条件での測定値であり、全経路の最悪遅延、配線後Fmax、PVT保証には使わない。

## 初期化と試験範囲

4つの境界試験は長いフレーム待ちを省くため、h/vのFFのQとQBに `.ic` を指定し、時刻0で解放している。出力FFはその後のクロックで更新する。状態注入はテストベンチだけにあり、チップにRESETを追加していない。

電源投入試験はFFの `.ic` を置かず、`.tran ... uic` でゼロ初期値から開始する。VDDは0.1～1.1 µsで0→5 V、CLK開始は2 µs。160クロックを解析し、最初の32クロックを除いた128クロックを照合した。**電源立上り1条件の確認であり、任意のアナログ初期状態・ノイズ・全立上り速度からの起動を証明していない。** 以前の全131,072状態の二値モデル探索とは別の試験である。

準備段階の `pilot` はQだけへの `.ic` で狙った状態にならず不合格となった。Qはバッファ出力であるためQBの帰還ノードにも初期条件を与えて修正し、`pilot_init` で確認後に上記4試験を実施した。これはテストベンチの修正で、回路は変更していない。旧生成物 `upper` / `lower` / `vsync` / `frame_wrap` は未実行であり、上記結果には含めない。

16.7 msの全フレームをトランジスタ過渡解析したわけではない。全画面の論理機能は前回のRTL／ゲート2フレーム試験で確認し、今回は色・同期・折り返しの選択した時間窓をトランジスタレベルで確認した。PVT sweep、配線RC、実パッド負荷、実モニタの確認は未実施。

## 上流の版・手順の注意

固定版の [ngspiceガイド](../tools/APRtools/docs/31_verify_ngspice.md) は `gen_chip_sim_ready.py` を紹介するが、その固定実コードの抽出呼び出しは `--no-combine` を渡さない。一方、[改善台帳U96](../tools/APRtools/docs/90_improvement_notes.md) と現行の特性化コードは、並列MOSをまとめるとBSIM3の狭幅項などが変わる問題を扱っている。

今回の入口は **正本の `apr/klayout_extract.py` に明示的に `--no-combine` を渡す経路**。簡便スクリプトのmainは実行していない。識別子変換は同スクリプトの固定版関数をimportして使い、変換前後の接続・素子パラメータのトークン一致と大文字小文字を無視した識別子衝突0を確認した。上流コードの追加変更や旧設計のスクリプト使用はない。

抽出トップの端子順は `hsync vdd b g r clk vsync vss`、LVS参照回路は `b clk g hsync r vsync vdd vss`。それぞれ実ファイルから読んだ順序で接続しており、片方の順序を流用しない。

## 再確認

既存の波形の検査だけなら、以下で各 `verification.json` を再生成できる。

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/power_spice_check.py check upper_init
.venv/bin/python scripts/power_spice_check.py check lower_init
.venv/bin/python scripts/power_spice_check.py check vsync_init
.venv/bin/python scripts/power_spice_check.py check frame_wrap_init
.venv/bin/python scripts/power_spice_check.py check powerup
.venv/bin/python scripts/power_spice_check.py check upper_reference
```

試験を再実行する場合は `check` を `run` にしてから `check`。当該試験の波形・実行ログを上書きするため、今回の記録を保持するなら先に試験ディレクトリを複製する。ngspiceの直接の実行コマンドは、各試験ディレクトリを作業ディレクトリとして `ngspice -n -b -r wave.raw tb.spice`。

抽出に実際に使った入口は以下。`prepare` は抽出済みファイルを変換し、モデルの絶対パスを現在のチェックアウトに合わせて生成する。

```sh
.venv/bin/python scripts/run_apr.py --design-root experiments/a_power_spice \
  apr/klayout_extract.py \
  /home/ishi-kai/ishi-vga/release/ishi_vga_grid_power_core/src/ishi_vga_grid_power.gds \
  ishi_vga_core --no-combine -o build/core.extracted
.venv/bin/python scripts/power_spice_check.py prepare
```

旧コア引き渡しアーカイブは変更していない。本記録と抽出SPICE試験は追加の検証成果物として扱う。DRC／LVS／STAや未解決のFloating SG警告の状態は [コア引き渡し記録](POWER_GRID_IMPLEMENTATION.md) を参照する。
