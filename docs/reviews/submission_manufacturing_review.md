2026-09-25 — `submission` 製造前レビュー

**判定：現状をそのまま製造へ出してよいとは判定できない（NO-GO）。新規の重要な電気的問題1件と、検証入口の問題1件を検出した。** 論理・配線接続・描画DRCの再検査は合格したが、CLK負荷違反があり、フレーム未統合および配線後の電気的サインオフも未完了である。

これは「必ずシリコンが動かない」という判定ではない。実際に検出した制約違反、確認済みの正常動作、未検証事項を以下で区別する。主催者がコアだけを受領して統合する契約であれば、未統合自体は提出範囲の不履行とは限らない。ただし製造する全体回路の合否は、統合担当側でも別途確定する必要がある。以前のレビューは「未統合コアの引き渡し資料」が対象であり、今回の製造可否とは判定範囲が異なる。

**対象と依存**

対象は [submission](../../submission/README.md)。GDS SHA256は `3bcfd73d98e2adca5b78eb20978a6145960e8023e60527ec7e960979cb86617e`、manifest SHA256は `96bdc4c6b83d5897faae4dacc655521eccb0fdae85942f0e51505179ace87c5c`。このレビューで提出ファイル、設計、固定依存を変更していない。検査用のファイルは別ディレクトリに生成した。

ユーザー指定どおり **TR-1um dev** を使用した。リモート `refs/heads/dev` を照会し、現在の固定PDK `f408d3b5c23a8ebe44f02b0482a9270601e2880f` と一致した。APRtoolsは `8f6962bf2df1618d633f8a81c230fec895fc83aa`、v59_4 GDS/LEF/SPICE/Libertyの組を維持。`check_toolchain.py` で記録済みPCellパッチ5ファイル以外の変更がないことを確認した。devへの依存更新やmainへの切替は行っていない。

実行環境は既存のIcarus Verilog、OpenSTA、ngspice 46+、KLayout CLI 0.30.9／Python API 0.30.6。依存検査のPASSと、以下の回路検査の結果は別の判定である。リモート照会結果・対象ハッシュ・生データのハッシュは [検査manifest](submission_manufacturing_20260925/manifest.json) に保存した。

**MFG-001 — P1・新規：CLKのBUFTHがLibertyの最大負荷を超えている**

場所：`submission/source/ishi_vga_core_pnr.v:1214–1344,1354`、`tools/APRtools/stdcell/v59_4/tr1um_typ_5v0_25c.lib:602,829`。

`u_bufth_clk/Y` は22個のDFFのCKを直接駆動する。CK入力容量は各59.637 fFなので、ピン容量だけで **22 × 59.637 = 1312.014 fF（1.312 pF）**。BUFTH/Yの `max_capacitance` は **800 fF（0.800 pF）**、同セルの遅延表も800 fFまでであり、配線容量を足す前から **512.014 fF、約64%超過**している。

従来のSTAを再実行すると、保存値のsetup +275.957 ns／hold +6.634 nsを再現した。しかしこれは理想クロックであり、クロックの電気的負荷を合格と判定した結果ではない。追加で `set_propagated_clock [all_clocks]` と最大容量・slew検査を実行したところ、次を検出した。

```text
Pin                     Limit(fF)    Cap(fF)       Slack(fF)
u_bufth_clk/Y            800.000000   1312.013672   -512.013672 (VIOLATED)
```

出典：[追加STA実ログ](submission_manufacturing_20260925/sta_electrical.log)、[実行Tcl](submission_manufacturing_20260925/electrical.tcl)。OpenSTA値の丸めとLiberty値からの計算の微差は単精度表現によるもの。

追加STAでも配線RCなしのsetup +275.599 ns／hold +6.749 nsは正で、最大slew違反は報告されなかった。今回の典型条件SPICEにも機能失敗はない。しかしこれらは容量違反を解消せず、表の範囲外を使ったタイミング値を製造保証へ置き換えられない。まして実際のCLK配線容量・遅延差は未算入である。

製造前の処置：クロック分岐バッファ等で各段を実配線込みの許容負荷に収め、slew・setup/hold・skew・パルス幅を再検証する。意図して現在の負荷で使うなら、その範囲の特性化と配線を含む検証が必要である。Libertyの上限の数値だけを書き換えて合格にしてはいけない。修正によるセル追加・再配線は1800×900 µmの制約内で再評価し、GDS/抽出/LVS/STAの証拠も更新する。

**MFG-002 — P1・既知の製造前提：フレーム・パッド・ESD・正式ピン割当がない**

場所：`submission/source/config.py:41`、`submission/ports.json:17`、`submission/SPEC.md:88,116–120`。

現GDSの対象トップはコア `ishi_vga_core` のみ。`PAD_MAP={}`、パッド番号はnullで、主催者フレーム、ボンディングパッド、I/O回路、ESDは未統合。これは既存の保留指示に沿った状態であり、このレビューで統合しなかった。再実行したマスクDRCも **WAR06: Floating SG Detected 1件**で終了コード1となった。対象はCLKのBUFTH入力。[DRC/MDPログ](submission_manufacturing_20260925/drc.log)

コアへの端子注記はボンディングパッドではない。また、Floating SGの消滅だけでESD耐量を証明できるわけではない。採用I/O回路と電源保護を接続し、最終全体のDRC・MDP・strict LVSを再確認する必要がある。

公開[主催者テンプレートのinfo.yaml](https://github.com/OpenSUSI/TR-1um_MPW_template/blob/f09b35f66d71f979bfad0d50c863bb0b3e066e9a/info.yaml)は `tr_1um_` で始まる一意のトップ、LVS用 `.cir` 等を定義している。現submissionには同形式の `info.yaml`、`src/<top>.gds`／対応`.cir`、完成チップトップがない。コア引き渡しとは別に、実際の提出インターフェースを確定すること。テンプレートmainも記録済み `f09b35f…` とリモートが一致した。

主催者のアナログ `OSS_FRAME` と固定APRtoolsの `OSS_FRAME_GIO` は同一でない。[既存の比較](../FRAME_CHOICE.md)のとおり、アナログフレームにGIOと同じ出力ドライバがあると仮定してはいけない。GIOを使う場合は対応する修正済みGDSと凍結SPICEをセットで使い、主催者側の採用条件を満たすこと。テンプレート既定のPDKタグは今回のdev固定コミットとは異なるため、最終CIも今回の検査版と整合させる必要がある。

寸法は1792.8×897.2 µmで予算内だが、余裕は横7.2／縦2.8 µmしかない。負のX原点と境界に近い端子もあり、実際の共有枠への配置・隣接ブロックとの間隔・電源と信号の引き込みが成立する証拠はまだない。コアbboxの合格だけでは統合可能とは確定しない。

**MFG-003 — P1・既知のサインオフ不足：配線後のタイミング・電源・I/O負荷を保証していない**

場所：`submission/SPEC.md:80,93–112`、`submission/verification/summary.json`。

提出STAはtyp 5 V/25℃、理想クロック、配線RCなし。抽出SPICEもMOSと拡散寄生を扱うが、金属のR/C、配線間結合、電源配線抵抗を持つPEXではない。したがってCLKの実際の分配、短いデータ経路のhold、遠端slew、実負荷下の出力エッジ、電源降下は未判定である。低いクロック周波数によるsetup余裕だけでholdや電源品質は保証できない。

電源の導通は再検査で正常だったが、電源電流、IR drop、電流密度、同時切替時の電源変動の数値評価は提出証拠にない。VDD/VSSが各1成分という結果は、電源品質の合格とは異なる。

STAの出力負荷は上流config既定のGIO入力45.923 fF。SPICEでは全出力1 pFを仮定している。正式なフレームが未確定なので、どちらも最終実負荷の検証とはならない。RGB／HS／VSはコアDFF出力であり、75 ΩのVGA負荷を直接駆動する構成ではない。外部バッファ／RGB抵抗DAC、CLKの入力レベルとエッジ、基板・ケーブル負荷を含めて評価する必要がある。

製造前の処置：許容VDD範囲・温度範囲・CLKのduty/立上り/立下り・負荷と起動シーケンスを規定し、適用できるプロセスモデル範囲とともに評価する。実フレームを含む配線RCを抽出し、clock propagatedのsetup/hold・最大容量・slew・パルス幅および電源品質を確認する。必要なプロセスコーナーがPDKから得られない場合は、任意のしきい値摂動を公式PVTと呼ばず、残る保証範囲を明記して製造担当側で判断する。

全フレームのトランジスタ過渡解析やFPGA／実モニタ試験が未実施であることだけを、独立した致命傷とは扱わない。全二値論理の検査は今回強化できた。未完なのは、それでは代替できない電気的な最悪条件と最終接続の検証である。

**MFG-004 — P2・新規：STAでTclエラーが起きても終了コード0を返す**

場所：`tools/APRtools/syn/sta/sta.sh` のOpenSTA→awk→tee実行部、`scripts/run_apr.py` の終了コード転送。

検査用の別ディレクトリで、レポートTclを意図的な `error {INTENTIONAL_REVIEW_NEGATIVE_CONTROL}` に置き換えた。OpenSTAは明確にErrorを出して解析報告を完了しなかったが、ラッパ全体は **exit 0** で終了した。[負の対照ログ](submission_manufacturing_20260925/sta_negative/run.log)／[結果](submission_manufacturing_20260925/sta_negative/result.json)

現在の保存STAがこの問題で誤って合格したと判断したわけではない。通常のSTAは今回正常に再現できた。ただし、今後の制約の誤記やツールエラーを終了コードだけで判定すると、失敗を成功として提出記録に残せる。

処置：設計側の検証入口でError行、必須レポートと経路の存在、必要な違反件数を明示的に判定し、この負の対照が非0で失敗するようにする。パイプラインの終了コード対策だけでは、OpenSTA自身がTclエラーを正常終了扱いする場合を取りこぼし得る。固定APRtoolsを無断編集するのではなく、ロック方針に従う設計側ラッパで対処する。

**各設計レイヤーの確認結果**

| レイヤー | 今回の確認 | 判定・限界 |
|---|---|---|
| 要求・世代 | g_power、外部3.15 MHz、RGB111、RESETなし、7端子＋共通VSS。現行RTL/GDSを照合 | 旧B／RGB222／6.3 MHzやリング入り設計との取り違えなし |
| 固定依存・dev | submodule、記録済み差分、資産SHA、リモートdev、提出lock一致 | PASS。依存確認は回路の合格と別 |
| VGAタイミング・図案 | 100 tick×525行、HS/VS負極性、porch、帰線RGB黒、glyph/線分データから独立描画 | 52,500 tickの期待値と一致。640×480・60 Hz相当の論理。実モニタの受信は未確認 |
| RTL | 同梱試験2フレームを再実行 | 105,000 tick PASS |
| 合成ゲート | 同梱ゲート試験2フレームを再実行 | 105,000 tick PASS。単位遅延モデル |
| 全二値状態・合成整合 | h/vの全131,072状態をRTLとゲートへそれぞれ設定し、1クロック後の17状態bitと5出力を全照合 | PASS。通常ラスタ52,500状態では独立期待値とも一致。出力FFにフィードバックがないので前回出力値には依存しない |
| 起動の二値モデル | 全状態の遷移グラフを再計算 | 単一周期52,500 tick、最大到達49,928 tick。RESETなしに二値的な永久ロック状態なし |
| クロック・STA | 保存STA再現、伝播クロックで電気制約を追加検査 | MFG-001。配線なしのsetup/hold自体は正 |
| GDS・配置・端子 | 指定トップ、bbox、345セル＋via実体、8端子のラベル／実メタル、レイヤー一覧 | 記録どおり。DRC除外マスク63/0なし。パッド未統合 |
| 独立配線監査 | GDS配置とv59_4 LEFから696信号端子を再構成 | 欠落0、短絡0、断線0。345配置セル一致 |
| 電源・ボディ | 金属接続、VDD/VSS分離、TAP/FILL、公式デッキ | VDD/VSS各1成分、信号への誤接続なし。IR/EM評価ではない |
| 描画DRC | devの公式run.drc、ルール削除オプションなし | 0件 |
| MDP・マスクDRC | 生成マスクへdevのrun_IP62.drc | WAR06 1件。エラー終了を警告込みPASSへ置き換えていない |
| LVS | 提出GDS対独立参照、strict port mode、xrefを機械検査 | 23回路一致、トップ8端子・234ネット・325子回路一致。TAP20個は素子を持たないため325子回路の集計外 |
| LVS参照の独立性 | 提出ゲート＋固定セルSPICE＋配置表から上流mklvsnetで新規生成 | コメントを除く回路行が提出参照と一致。GDS抽出物を参照側へ流用していない |
| 抽出SPICEの由来 | 提出GDSからno-combineで新規抽出 | 提出 `ishi_vga.extracted` とバイト一致。1774素子の抽出経路を再確認 |
| トランジスタ機能 | 保存6波形をハッシュ検証して再判定。powerupを新規ngspice実行 | 保存：抽出668＋参照110 tick PASS。新規：powerup128評価tick PASS。5 V/27℃・出力1 pF・wire RCなし |
| 電源投入・復帰 | 実回路の保存刺激と新規powerup解析を確認 | 1 µsランプ・CLK後開始・UIC初期条件の1条件のみ。遅い立上り、先行CLK、brownout、アナログ不定状態は未保証 |
| VGA外部電気系 | コア出力、CLK電圧、DAC／終端条件、フレーム差を確認 | 正式I/Oと基板負荷が未定。3.3 V CLK直結を認める証拠なし |
| 提出梱包 | 121 payloadの全ハッシュ、全ファイル集合、symlinkなし、GDSとlock整合 | PASS。製造テンプレート形式はMFG-002 |
| 再現性・検証手順 | 同梱試験の新規出力先、独立参照再生成、抽出再生成、既存再現記録を確認 | 元の配置探索と局所修復全工程は今回は再実行していない。最終GDSそのものを検証した |

GDSには未使用ライブラリtopが11個残ることを再確認した。README/SPECに対象トップを明示する注意書きがあるので、新規欠陥には数えない。統合担当は `ishi_vga_core` だけを選択すること。現在の出力画像はゲート観測値由来であり、SPICEの全フレーム画像や実機写真とは扱っていない。

**検証をどう強化したか**

既存RTL/ゲート試験は、最初にFFを0へ初期化してから同期獲得後2フレームを見る。これだけでは違う二値初期状態を直接試していないため、今回の [全状態テストベンチ](submission_manufacturing_20260925/tb_exhaustive.v) ではカウンタ全組合せを設定して、安定後の次状態と出力を実際の提出RTL／ゲートで検査した。これは2値の網羅シミュレーションであり、アナログのメタステーブル状態からの収束証明ではない。[実ログ](submission_manufacturing_20260925/exhaustive.log)

同梱SPICEチェッカはクロック立上り開始150 ns後にLow<1.5 V／High>3.5 Vで観測する。1サンプル／周期の機能照合であり、周期内グリッチ、実負荷下の最悪slew、全経路タイミングの保証にはならない。今回の新規powerupも同じ検査契約に対する再現性確認として数えた。全二値状態の検査を、このサンプル型のアナログ検査で済ませたとは主張しない。

**閉じる順序**

1. CLK負荷違反を解消または必要範囲の特性化で根拠づけ、狭い面積予算内で物理実装を再成立させる。
2. 主催者との受け渡し範囲、正式フレームとピン割当、外部I/O回路・負荷、電源／CLKの動作範囲を確定する。
3. 統合GDS／独立参照／RC付き抽出を同一世代にそろえ、DRC・MDP・strict LVS、電気制約・タイミング・電源・起動条件を検証する。残警告は解消または製造担当による根拠付き受容を記録する。
4. Errorを見落とさない検証ゲートで最終成果物を検査し、主催者が実際に読むトップ・ファイル形式・PDK版とmanifestを一致させる。

現時点の「論理機能とコア接続に明白な破綻を検出しなかった」という結果を維持しつつ、MFG-001と既知の製造残件を解消するまで製造可とはしない。

**再検査の所在**

要約・追加テスト入力・実ログは [証拠ディレクトリ](submission_manufacturing_20260925/manifest.json)、生のGDS・DRC/LVS DB・新規SPICE波形はワークスペースの `build/submission_review_20260925/` にある。提出物を上書きしない新規ディレクトリで実行した。実行した検査用Pythonも同ディレクトリへ保存している。`prepare_checks.py`／`audit_static.py` は `build/<検査名>/` にコピーして使う作業用コードであり、提出のビルド入口ではない。

代表的な再実行コマンド（ワークスペースルート、検査用configと提出GDSのコピーがある場合）：

```sh
python3 scripts/check_toolchain.py
python3 submission/tools/verify_bundle.py
python3 scripts/run_apr.py --design-root build/submission_review_20260925 \
  apr/drc_pdk.py ishi_vga.gds ishi_vga_core -r drawing.lyrdb --mdp
python3 scripts/run_apr.py --design-root build/submission_review_20260925 \
  apr/lvs_pdk.py ishi_vga.gds ishi_vga_core \
  --sch ../../submission/simulation/ishi_vga_lvs.spice -r core.lvsdb
python3 scripts/run_apr.py --design-root build/submission_review_20260925 \
  syn/sta/sta.sh out/ishi_vga_core_pnr.v ishi_vga_core 317.460317 \
  ../../docs/reviews/submission_manufacturing_20260925/electrical.tcl
```

上記DRCコマンドは残警告により非0、追加STAは容量違反を表示しても現ツールでは0終了する。終了コードだけで成功扱いせず、レポートを確認すること。
