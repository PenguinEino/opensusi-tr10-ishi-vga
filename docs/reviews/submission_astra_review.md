# ISHI VGA 提出物の独立レビュー

レビュー日：2026-09-25。依頼指定：gpt-6-astra / xhigh。初回レビュー対象は `/home/ishi-kai/ishi-vga/submission`、差分再レビュー対象は `/home/ishi-kai/ishi-vga/build/submission_review_candidate`。レビュー担当は回路・提出物を変更していない。

## 結論

**フレーム未統合のコア引き渡し資料として、重大・中程度の新規不具合は検出しなかった。初回の低優先度指摘1件も、修正候補で解消を確認した。** 未解決の新規指摘は0件。最終チップの製造承認を意味しない。フレーム統合の保留、CLK入力のFloating SG 1件、PEX・PVT・実機確認の未実施は既知の範囲制限であり、今回の梱包不具合として数えていない。

| 対象 | 初回レビュー開始・終了時のSHA256 |
|---|---|
| `submission/manifest.json` | `7482f9fc90251299cb7884946e8cdfb97f19bf996dce4e7174f59c368bebe60c` |
| `submission/ishi_vga.gds` | `3bcfd73d98e2adca5b78eb20978a6145960e8023e60527ec7e960979cb86617e` |
| `submission/reproduce/core_handoff.tar.gz` | `90d25224bc9f83ff6afc845da94019aa417df4a089e481b29d3a74c5e2dffded` |
| 修正候補 `build/submission_review_candidate/manifest.json` | `17b42690c920d78d05ca5f0d2dff0d5cec01c7dd4cbe5521a0a3604907b61598` |

初回対象のmanifestは開始から検査終了まで同一。修正候補は別ディレクトリで確認した。以下に初回検査と差分再レビューを区別して記録する。機械可読記録は [submission_astra_review.json](submission_astra_review.json)。このレビュー自身を同梱する最後のsealによってmanifestはさらに変わるため、その最終manifestハッシュを自己参照して記録してはいない。

## 指摘

### SUB-001 — Low：複数GDSトップの選択注意を追記する

- 場所：初回版 `submission/README.md:10`、`submission/SPEC.md:17`、`submission/SPEC.md:114`。
- 根拠：指定トップは正しく `ishi_vga_core` と明記されているが、実GDSには未参照のライブラリトップが11個残る。KLayoutの `Layout.top_cells()` は合計12セルを返した。
- 別トップ：`FILL1`、`REG8x16`、`REG4x16`、`via_1`、`RSLATCH`、`MUXDFFRB`、`AND4_X1`、`DFFRB`、`DEL1`、`TAP3`、`DFFS`。
- 影響：受け手が「全トップを一括配置」すると、本来のコア以外の図形を統合してしまう。例えばREG8x16/REG4x16の独立bbox上端は933 µmである。ただしこれらはコアから未参照なので、指定トップの1792.8×897.2 µmという寸法、回路機能、今回のDRC/LVS結果を否定しない。
- 再現：`.venv/bin/python -c "import klayout.db as d; l=d.Layout(); l.read('submission/ishi_vga.gds'); print([(c.name,str(c.dbbox())) for c in l.top_cells()])"`。
- 推奨：READMEと統合欄に「`ishi_vga_core` のみを明示選択し、GDSの全トップを一括配置しない」と追記する。採用GDSはハッシュを保って変更しない。
- 状態：**修正候補で解消確認済み**。候補 `README.md:22` と `SPEC.md:116` に、11個の未参照topが残ること、`ishi_vga_core` だけを選択することを明記。GDSハッシュは不変。

親担当が報告した端子図VSYNC注釈の引出線と文字の重なりも、修正候補を目視して改善を確認した。独立レビューの電気座標検査は合格しており、端子誤配線の指摘ではない。

## 検査範囲と結果

| 分野 | 実施した確認 | 結果 |
|---|---|---|
| 指示・固定依存 | `AGENTS.md`、`docs/APRTOOLS_ADOPTION.md`、`toolchain.lock.json`を先に読了。`python3 scripts/check_toolchain.py`を実行 | APRtools `8f6962bf…`、PDK `f408d3b5…`、v59_4、記録されたPCellパッチのみ。版チェックを回路検証と混同していない |
| 梱包整合 | `python3 submission/tools/verify_bundle.py`、manifestと実ファイルの集合比較、全sourcesの元ファイル/ハッシュ/複写またはgzip展開を比較 | 103 manifest対象、97 provenance対応が一致。未列挙・欠落ファイル0。4つの入口Markdownの相対リンク切れ0 |
| 類似提出物 | `../sram/submission` と `../balanced-ternary-logic/submission` の構成・READMEを確認 | GDS、抽出回路、参照回路、仕様、端子・レイアウト図という必要な要素を満たす。合成設計に実在しないXschem `.sch` を捏造していない |
| GDS同一性・外形 | KLayoutでGDSを直接読取。指定top、DBU、bbox、インスタンス種別を検査 | `ishi_vga_core`、0.001 µm、(-15.3,0)–(1777.5,897.2) µm。1800×900予算内。7.2/2.8 µmの差をフレーム配線余裕と誤って主張していない |
| 端子 | GDSトップのテキストと各座標が指定M1/M2図形内にあることを直接確認。ports.jsonとSPECを比較 | CLK/HS/VS/R/G/Bの6信号＋VDD＋共通VSS=8電気端子。共通VSSを除き7。全8点一致。電源点はレール注記でありパッド番号ではない |
| セル世代 | 使用セルの再帰的な全層図形を固定v59_4 GDSとXOR比較 | 配線用 `via_1$2` を除く使用23種類の差分0。209論理＋20 TAP＋116 FILL=345配置セル、別途850 viaインスタンス。論理セル面積301,193.64 µm²。リング/フレームは指定コアにない |
| 物理記録 | 保存 `.lyrdb` を直接読み、`core.lvsdb` の回路・端子・ネット・subcircuitペアを検査。ログと元報告のGDSハッシュも比較 | Drawing 0、MDP WAR06 1。23回路、top 8端子、234ネット、325 subcircuitペアがすべてMatch。20 TAPは抽出デバイスなしであり配置数との矛盾ではない |
| 配線監査 | `verification/physical/verification.json` と `metal_connectivity.json`、由来の対応を確認 | 保存された独立監査は信号696端子、欠落・短絡・断線0、VDD/VSS各1成分。今回この監査アルゴリズム全体の新規再実行はしていない |
| RTL・タイミング | RTL/ゲート・テストベンチとSPECのカウンタ式、同期極性、出力レジスタを比較。期待フレームを別途集計 | 外部3.15 MHz、100 tick×525行、31.5 kHz/60 Hz。HSYNCはx=[82,94)、VSYNCはy=[490,492)。帰線RGB黒。RESET/リングなし |
| 図案と画像 | 期待フレーム・観測hex・PNGの全画素を比較し、色・外接範囲を集計 | g_powerのRTLに5本の電源枝。5色。色付きbbox [64,576)×[92,412)。640×480 PNGとフレーム全画素一致。ngspice/実モニタ画像であるという主張なし |
| 二値起動 | 元スクリプトと異なる、入次数剥離＋逆順距離計算で全131,072状態を独立探索 | 唯一52,500 tick周期、最大到達49,928 tick=15.8501587 ms。アナログ起動保証・RTL formal proofとは扱っていない |
| STA | 保存STAとSPEC、固定Liberty、論理ネットリストの対応を確認 | typ 5 V/25℃、317.460317 ns、setup余裕275.957 ns、hold余裕6.634 ns。理想クロック・セル遅延による結果。最終配線RC込み保証/Fmax保証とは扱っていない |
| 抽出変換 | raw抽出とngspice回路を独立トークン比較。subckt階層を再帰計数 | 23 subckt、1774素子。397ノードの改名対応は一対一、全デバイス種別・W/L/AS/AD/PS/PDを保持。配線R/C追加なし |
| SPICE端子順 | 生抽出、LVS参照、ngspice参照、全刺激のXDUTを照合 | 抽出 `hsync vdd b g r clk vsync vss` と参照 `b clk g hsync r vsync vdd vss` を区別し、各刺激は対応する順序を使用 |
| モデル・刺激 | 同梱モデルを固定PDK原本/記録SHAと比較。全6tbを元run.jsonのSHAと比較。刺激・温度・負荷・.ic/uicを読取 | 5 V/27℃、3.15 MHz、2 nsエッジ、各出力1 pF、最大刻み1 ns、trap。元モデル/抽出/刺激は一致。変更は可搬性用includeのみ |
| 保存SPICE波形 | `python3 submission/tools/run_tests.py saved-spice` を独立実行。gzip展開SHA、単調時刻、有限値、全指定サンプルの17状態bitと5出力bitを確認 | 抽出5窓110+110+210+110+128=668 tick、独立参照110 tickともPASS。全6run exit_code=0。保存ngspiceログにwarning/error/convergence/timestep異常の記載なし |
| SPICE主張の範囲 | 元検証器と各reportを確認 | 150 ns後の1.5/3.5 V判定、境界試験のQ/QB初期化、powerup最初32tick除外を明記。19.118 nsは選択窓内で観測した出力遷移の値で、全経路最大ではない |
| 単独実行コード | `submission/tools/*`、相対include、source/test依存、出力先制約を読取 | ネットワーク/他PDK/元workspaceへの暗黙fallbackなし。結果は新規ディレクトリへ出力。config.pyを単独APRラッパと誤認させない説明あり |
| 凍結再現セット | tar内README/REPRODUCE・ファイル構成・全manifest hash・リンク種別を検査。再現スクリプトと固定入口を確認 | 125通常ファイル、33ディレクトリ、symlink等なし、123 manifest対象一致。固定チェックポイントから修復/注記/引出しを再現する範囲を説明。SPICE追加前の凍結版であることを外側REPRODUCEで明記 |
| 出典・権利注記 | PROVENANCE、PDK LICENSE、モデル内注記を確認 | 固定元を区別。APRtoolsルートにLICENSEがない事実を記載し独自ライセンスを捏造していない。法的権利の独立判定は本レビュー外 |

## 既知の保留事項

1. 主催者の実フレームとピン番号は未確定。GIO修正版とアナログOSS_FRAMEは同一ではなく、どちらも現在のGDSには統合されていない。フレーム統合はユーザーの明示指示により保留。
2. CLK BUFTH入力の `WAR06: Floating SG Detected` が1件残る。ESD接続後の警告消滅は未保証。最終統合後のDRC/MDP/strict LVSが必要。
3. VDD/VSSレール接続、0–5 VのCLK入力、実I/O駆動、RGB用外部抵抗DAC/バッファの設計は統合側の事項。1 pF試験は75 ΩVGA終端の直接駆動を保証しない。
4. PEX、全フレームanalog、PVT sweep、実パッド/基板負荷、実モニタ確認は未実施。RESETなしの二値全状態探索と一条件のゼロ初期値電源投入試験をアナログ任意初期状態の保証に拡張できない。

これらはいずれも初回README/SPECに明記されている。未実施の設計・試験を本レビューだけで合格に置き換えていない。

## 誤検知を避けるために確認した点

- 8 LVS端子と「7端子」は共通VSSを数えるかどうかの違いであり、矛盾しない。
- x=-15.3 µmの外形は明記されている。X=+15.3 µmの配置オフセットによって左端を0へ合わせられるが、内部GDSの書換えを必要としない。
- ロックにring資産、履歴configにpad12予約が存在することと、今回のコアにring回路が存在することは別である。
- 345配置セルとGDSの1195参照は850配線viaを含むかどうかの違い。LVSの325 subcircuitは20 TAPを含まない。
- 抽出参照とLVS参照の端子順・ノード名は異なるが、各tbの実接続は正しい。
- 保存ログの絶対パス、manifest.sourcesの元パス、source/config.pyは履歴・由来の記録。可搬性ツールの実行時参照先ではない。
- archive内の旧SPICE未実施記録は外側の更新済みSPEC/verificationと優先順位が説明されているため、現在の668tick試験と矛盾する最新版主張として扱わない。

## 今回新規実行しなかったもの

新しい全SPICE試験群、再合成、配置探索、P&R/局所修復の全replay、公式DRC/LVSデッキ再実行、配線RC抽出、PVT、ハードウェア試験は実施していない。物理合格についてはハッシュ対応した保存データベースを直接読んで検査した。

親担当からは別ディレクトリ複製で新規RTL/ゲート各105,000tick、新規ngspice upper_init 110tick、保存波形6窓、期待画像1bit改変の否定対照が合格したとの報告を受けた。シミュレータを新規起動した担当は親担当であり、上表の独立実行と区別する。追加された実ログと、新規SPICE実波形の独立再判定については次項を参照。

## 修正候補の差分再レビュー

対象manifest：`17b42690c920d78d05ca5f0d2dff0d5cec01c7dd4cbe5521a0a3604907b61598`。`python3 build/submission_review_candidate/tools/verify_bundle.py` は113ファイルでPASS。107のprovenance対応を原本・ハッシュ・複写/gzip展開で再照合し、差分0。未列挙/欠落ファイル0、入口4文書の相対リンク切れ0。

初回の既存ファイルで変わったものは `README.md`、`SPEC.md`、`REPRODUCE.md`、`ishi_vga_pins.png` の4点のみ。10ファイルが追加され、削除はない。最終GDS、RTL、ゲート回路、端子JSON、モデル、抽出/参照回路、各tb、検証スクリプト、既存物理/機能/SPICE証拠、凍結再現archiveは全てバイト不変。

- SUB-001の選択注意をREADME/SPECで確認。指摘をclose。
- 端子図を目視。VSYNCの引出線は文字に重ならず、CLKを含む全8ラベルの座標・層は変更なし。
- `REPRODUCE.md` の追加説明は、別ディレクトリで同じ実行バイナリを使った可搬性試験であること、記録されたmanifestは試験時ドラフトであることを明示している。別OSで新規導入した試験という過大主張はない。
- 追加 `reproduce/package_submission.py` は元workspace用の梱包ソースであると明記。単体での再シミュレーション入口との混同なし。
- 追加 `verification/portability.json` の15の元証拠ハッシュを実ファイルと照合して全一致。保存されたRTL/ゲート実ログは各105,000tick PASS、新規ngspiceログは27℃/SPARSE 1.3を記録。
- 親担当が新規に生成した `build/submission_portability01/spice_upper/simulation/upper_init/wave.raw` を、候補同梱のcase/expected/checkerで独立再判定し、17状態bit＋5出力bit、110tick PASSを確認。この波形は既存保存波形と別SHAで、新しい実行の証拠として元ファイルを照合した。

差分による新規指摘はない。親担当による候補の提出先への移動と、このレビュー記録の追加・最終manifest更新を残すのみ。検査済み回路資産を変えないことを前提に、この候補をフレーム未統合コアの提出資料として受け入れ可能と判定する。
