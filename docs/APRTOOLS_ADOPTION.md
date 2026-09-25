# APRtools採用版と実装時の参照規約

更新日: 2026-09-25。今回のVGA設計が使うツールの選択を記録する。一般的なTR-1um調査や過去記事より、この文書と`toolchain.lock.json`を優先する。

同じ固定版を使う最新の拡張は [文字発光＋消灯段階](LETTER_SCAN_IMPLEMENTATION.md)（241論理セル）です。以下の213セルは、その基礎である静止画コアの値です。

**現在の回路は[格子＋電源枝5本](POWER_GRID_IMPLEMENTATION.md)。** 同じ固定依存で1792.8×897.2 µm、213論理セル（クロック4分岐修正後）、描画DRC 0、strict LVS合格、マスク警告1件。以下にある282セル・マスク警告2件はツール採用時の旧Bコアの実績であり、現採用版の値ではない。

**採用はAPRtools現行集約版＋v59_4。説明文だけで決めず、固定した実コードのパス解決を実行して照合した。** VGAのRTL・合成・機能検証・配線前STAに加え、282セルのコア内配線とstrict portの公式LVSが成立した。描画DRCは0件、マスク警告2件、フレーム統合は未完了。[最新の物理検証](CORE_ROUTING.md)／[実装記録](IMPLEMENTATION.md)。

## 1. 固定した版

| 対象 | 取得元 | 固定コミット |
|---|---|---|
| APRtools | `https://github.com/jun1okamura/TR-1um_APRtools.git` | `8f6962bf2df1618d633f8a81c230fec895fc83aa` |
| PDK | `https://github.com/OpenSUSI/TR-1um.git` | `f408d3b5c23a8ebe44f02b0482a9270601e2880f` |

両方とも`tools/`以下のGit submoduleとして取得し、detached HEADで固定した。PDKは調査時のdev由来だが、実行時に動くブランチ名`dev`を追従させない。既存の`~/pdk/TR-1um`は他の作業から更新され得るので今回のビルドには使わない。

このPDK固定は作業用の選択であり、主催者指定テンプレートとの統合検証が済んだという意味ではない。提出時の`info.yaml`とCIも同じ版へそろえ、最終フレームを確認する。

完全な版情報・選択資産のSHA256は[toolchain.lock.json](../toolchain.lock.json)。この表を編集するだけでは版を更新したことにならない。

## 2. 実コードが読むファイル

下表のAPRtools内パスはすべて`tools/APRtools/`からの相対パス。

| 用途 | 採用ファイル | 実コードの根拠 |
|---|---|---|
| セルGDS | `stdcell/v59_4/TR-1um_STDCELL.gds` | `apr/config_base.py: finalize()`の`LIB_GDS`/`CELL_GDS` |
| セルLEF | `stdcell/v59_4/TR-1um_cells.lef` | 同`LIB_LEF`/`LEF_PATH` |
| 合成・STA Liberty | `stdcell/v59_4/tr1um_typ_5v0_25c.lib` | 同`LIBERTY`/`SYN_LIB` |
| セル寸法表 | `stdcell/v59_4/cell_info.json` | 同`CELL_INFO`。設計側の古い写しを置かない |
| 配線層等のLEF | `stdcell/v59_4/TR-1um_tech.lef` | 同世代の付随資産として固定 |
| セルSPICE | `stdcell/v59_4/simulation/` | セルと同じsubmoduleコミットで固定 |
| GIOフレーム | `pdk/pending-upstream/TR-1um_frame_25x25_GIO.gds` | `pdk_frame_gds()`はこの同梱修正版を上流PDKより先に選ぶ |
| フレームLVS参照 | `pdk/frame/OSS_FRAME_GIO_nocombine.spice` | **設計configで`FRAME_LVS_SPICE`へ明示する必要あり** |
| フレームSPICEシミュレーション用 | `pdk/frame/OSS_FRAME_GIO.spice` | 上記修正版フレームと対になる正本 |
| リング発振器 | `macro/ringosc/RING_OSC.gds`と`.lef` | `finalize()`の`RING_OSC_GDS`/`RING_OSC_LEF` |

実行したパス解決の結果は[apr_resolution.json](apr_resolution.json)。[audit_apr_resolution.py](../scripts/audit_apr_resolution.py)は固定版`config_base.finalize()`を検査用の名前空間で呼び、結果をロックファイルと比較する。**この検査用名前空間はVGAのconfigやフロアプランではない。**

設計`config.py`でも上の資産へ明示的にそろえる。特に`CELL_INFO`の自動探索は、`layout/cell_info.json`が存在するとそちらを優先するため、正本を明示する。`FRAME_LVS_SPICE`の既定はNoneで、`mkchipnet.py`は設計側の古い置き場へフォールバックする。ここを放置しない。

## 3. レビュワーが踏みやすい罠

| 読むと紛らわしいもの | 今回の判断と裏付け |
|---|---|
| `stdcell/v59_4/README.md`の「P&RはPNR.gds/lefを読む」 | **古い説明。採用しない。** `docs/91_decisions.md`決定25、台帳U89、`config_base.py`の実装がライブラリ本体を選んでいる |
| `TR-1um_PNR.gds` / `.lef` | 不採用のMEMPORTを含む派生物。ファイルが存在しても採用しない |
| PDK同梱の`TR-1um_STDCELL.gds` | APRtools版と同名だが別物。パス全体で区別する |
| `stdcell/v64_8/` | 凍結された旧世代。旧I2C/SPI記事のLiberty・LEFを持ち込まない |
| `*_area.lib` / 仮遅延genlib | 面積調査用。今回の合成・STAの既定にはしない |
| 上流GIOフレームと修正版フレーム | OSS_DRVの回路が異なる。GDSだけ差し替えずLVS/SPICE参照も一組で扱う |
| 非GIO版`TR-1um_frame_25x25.gds` | 名前が似ているが今回選んだGIO版ではない |
| フレームPRの状態 | Markdown内に「push未」と「push済」が混在。状態の文章から自動選択しない。実際に選ばれるGDSと対応SPICEを固定する |
| 台帳前半の「未解決」や残件数 | 過去の記述が残る。`docs/90_improvement_notes.md`の§7-1索引とコードを読む。実行時の台帳検査は99項目・開3・決着96だった |
| `templates/`や昔の設計のbuild.sh | 現在の入口とは限らない。`syn/syn.sh`と`apr/`直下を使う。ひな形はコードを確認してから使う |
| 「PAD_MAPはスクリプトへ直書き」という古い文書 | 現行`gen_top_routing_plan.py`のconfig取得を確認して使う。I2Cのピン割り当てをVGAへコピーしない |
| ロゴ配置スクリプト | `place_logo.py`はGDS上に置く装飾ロゴ。VGAの矩形描画RTL（現在21矩形）とは別物 |
| 旧設計のPASSログ・面積・周波数 | 参考値。今回のネットリスト/GDSの結果として流用しない |
| 修復後の `pin_map_rr.json` と実セル端子 | 修復処理は配線端点の座標を更新する。実セル端子の座標表として流用せず、GDS配置とv59_4 LEFから独立に接続も検査する。[実例と訂正](ROUTING_AND_POLY.md) |
| `mklvsnet.py` の `1'h1` 入力 | この固定版はVerilog定数をSPICEノード名として残す。設計側で該当する定数ピンだけをLVS用入力のvddへ正規化し、上流で参照を再生成する。元回路や上流コードは変更しない。[原因と採用参照](CORE_ROUTING.md#lvs参照回路の定数変換) |

固定コミットに対し、PCellのtechnology検索5箇所だけ記録済みパッチを適用している。根拠・差分・SHA256は[IMPLEMENTATION.md](IMPLEMENTATION.md#現行依存に対する記録済み修正)とロックに記録。他の上流変更は許容しない。セル/フレーム資産に変更なし。

## 4. 読む順序

1. `README.md`、`apr/README.md`で入口を確認。
2. `docs/91_decisions.md`と`docs/90_improvement_notes.md`§7で現行の判断・残件を確認。
3. `stdcell/CELLS.md`、`pdk/README.md`、`pdk/frame/README.md`でセルとフレームの由来を確認。
4. `docs/20_flow_syn.md`→`21_flow_place.md`→`22_flow_route.md`→`23_flow_chip.md`を読み、実行するスクリプトの現行コードと照合。
5. `docs/30_verify_drc_lvs.md`、`31_verify_ngspice.md`、`40_gotchas.md`、`50_char.md`で検証の範囲・限界を確認。

`docs/01,02,05,06,07,08,09,92`は主に履歴資料。`legacy/`、旧設計repo、今回の`research/digital_flow/`は調査・履歴用で、実行用の正本ではない。

## 5. 実行と確認

設計ルートで実行する。

```sh
git submodule update --init --recursive
python3 scripts/apply_toolchain_patches.py
python3 scripts/check_toolchain.py
python3 scripts/audit_apr_resolution.py
python3 scripts/run_apr.py apr/check_ledger.py
```

`git submodule update --remote`やサブモジュール内の`git pull`で最新版へ追従しない。

[check_toolchain.py](../scripts/check_toolchain.py)は、コミット・取得元・追跡ファイルの記録済みパッチとの一致・資産SHA256・外部環境変数を確認する。[run_apr.py](../scripts/run_apr.py)は検査後、固定したAPRtools/PDK/PYTHONPATHと`PYTHONHASHSEED=0`で上流の入口を実行する。設計`config.py`がない段階では、設計に依存する処理を起動しない。

このラッパは回路検証ツールではない。また、将来の`config.py`の内容を全自動で保証するものではない。実装時には解決後の`LIB_GDS`・`LEF_PATH`・`SYN_LIB`・`CELL_INFO`・`FRAME_GDS`・`FRAME_LVS_SPICE`を再確認する。配置シード・行数・チャネル・パッド割当等は設計configに記録し、端末に残った`APR_*`上書きで変更しない。

採用時の確認結果:

- 版・ハッシュ・未変更状態の検査: PASS。
- 固定版コードを呼んだパス解決: ロックと一致。
- 上流台帳検査: PASS。
- 否定対照: v64_8指定、別PDK指定、legacyの入口、configなしの合成をすべて拒否。
- 上記は版の採用時の記録。現在の282セル版はコア内短絡・断線0、公式描画DRC 0、公式LVS一致。マスク警告2件とフレーム統合は残る。[現在の検証記録](CORE_ROUTING.md)を参照。

## 6. 更新時とレビュー時

版を変えるときは、上流差分→セル/フレームの変更→ロック更新→パス解決再検査→対象設計の必要な再検証の順に進める。新しい版のハッシュを機械的に写すだけでは更新を完了しない。変更前の提出物があれば世代別に保存する。

レビュワーは、まずこの文書、ロック、実際のsubmodule HEADが一致するかを見る。その後で設計config、実行ログ、実際の最終GDS/CIRを確認する。DRC/LVSは固定PDKの公式デッキで判定し、STAには実特性化Libertyを使う。依存固定が合格しても回路が合格したとは報告しない。

## 7. VGA固有の合意

最新のユーザー指示でリング発振器は不搭載、外部CLKのみ。半枠候補はCLK・HS/VS・RGB111の6信号＋VDD、共通VSSを除く7端子を目標として実装した。[A半枠試験](HALF_A_FEASIBILITY.md)／[ピン・クロック仕様](PIN_PLAN.md)。旧RGB222保存版は10信号＋VDD/VSSの12端子であり、世代を区別する。過去の実験configにはCLK=pad1、リング用予約=pad12という記述が残るが、どの確定コアにもリング実体は入っていない。ハッシュ付き過去configを後から書き換えず、最終ラッパではpad12のリング予約を廃止する。

v59_4のBUFTHを5 Vで使う場合、3.3 VのCLK/RESET直結を前提にしない。値の根拠は上流`char/schmitt.json`とセル資料に置き、この文書で独自のしきい値を作らない。
