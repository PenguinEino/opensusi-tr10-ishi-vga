# TR-1um論理回路の設計フロー調査

調査日: 2026-09-25。公式PDK main/dev、提出テンプレート、設計者本人のリポジトリと記事を調査。公開資料の確認であり、各フローの再実行や製造後の動作確認は行っていない。

## 結論

標準セルを使うASIC設計が正攻法。小回路なら回路図＋手配置配線でもよい。今回のVGAは、Verilog → 論理合成 → 標準セル配置配線 → パッド統合 → DRC/LVS/タイミング検証 → GDS/CIR提出とする。

公式が提供しているPDK・提出検証と、参加者が提供するRTL設計用ツールは区別する。確認した公式main/devには、論理合成用LibertyやLEF、完成済みRTL-to-GDS設定一式は見当たらなかった。拡張子.libのファイルはSPICEモデルであり、Yosys用Libertyではない。

今回の有力候補は **jun1okamura/TR-1um_APRtools + v59_4セル一式**。これは公開の自作フローで、公式認定の万能自動化フローという意味ではない。採用前に最小カウンタで合成から公式DRC/LVSまで通し、設計固有の設定を確認する。

## 公式資料

- [OpenSUSI/TR-1um](https://github.com/OpenSUSI/TR-1um): デバイスモデル、回路図シンボル、スタセルGDS、KLayout用ルール/PCell、設計資料。
- [公式スタセルGDS](https://github.com/OpenSUSI/TR-1um/blob/main/libs.tech/klayout/libraries/TR-1um_STDCELL.gds)
- [公式スタセル回路図・シンボル](https://github.com/OpenSUSI/TR-1um/tree/main/libs.tech/xschem/TR-1um_5_stdcell): INV/NAND/NOR/AND/OR/XOR/MUX/FF等。存在する名前だけで、すべてのセルが自動フローで利用可能と判断しない。
- [DrawingとMaskの区別](https://github.com/OpenSUSI/TR-1um/blob/main/Document/Drawing_vs_Mask.md): 旧IP62マスク層と新しい描画層を混同しない。
- [TR-1um_MPW_template](https://github.com/OpenSUSI/TR-1um_MPW_template): `src/<top>.gds`、`src/<top>.cir`、`info.yaml`を中心とする提出形式。
- [公式CI](https://github.com/OpenSUSI/TR-1um_MPW_template/blob/main/.github/workflows/check.yml): Precheck/DRC/LVS/MDP。RTLを自動合成するサービスではない。
- [公式MPW集約](https://github.com/OpenSUSI/OpenSUSI_MPW_TR2026): シャトル上の配置と参加者一覧。

今回はISHI会経由の枠なので、独立の申込み手続きへ変更する話ではない。フレーム・ネットリスト・説明をISHI会の取りまとめと整合させる。

## 参加者による実例

| 資料 | 今回に役立つ点 |
|---|---|
| [I2C 2026](https://github.com/jun1okamura/TR-1um_I2C_2026) | 提出用GDS/CIR、リング発振器統合、公式DRC/LVS・抽出SPICEの検証報告 |
| [SCLK SPI](https://github.com/jun1okamura/TR-1um_SCLK_SPI) | 外部クロック同期回路。VGAのカウンタに近い設計スタイル。RTL・ゲート・パッド込みの検証 |
| [TD4](https://github.com/jun1okamura/TR-1um_TD4) | 同期CPUとマクロを組み合わせた配置配線例。今回はCPU設計を再開する根拠にはしない |
| [I2C実装・白旗編](https://qiita.com/jun1okamura/items/898248762a03492cdc33) | 当初Libertyが無く、補って合成した経緯。初期のAI推定や未検証事項を現在の仕様として流用しない |
| [I2C実装・コンプリート編](https://qiita.com/jun1okamura/items/928e6e1464e75a68b394) | 実装を完了するまでの経緯 |
| [kuchiee氏・スタセルのW比](https://qiita.com/kuchiee/items/29aac784d06ac36d8745) | セルのトランジスタ構成をngspiceで調べる設計例 |
| [kuchiee氏・ICGセル](https://qiita.com/kuchiee/items/9514ec83304716759cce) | 足りないセルを回路レベルから追加する例。今回のVGAは単一クロック＋enableで進める |

各リポジトリのPASSや周波数は著者の報告であり、今回のVGAに対する測定値でも製造後の保証でもない。

## APRtoolsでそろえる資産

[APRtools](https://github.com/jun1okamura/TR-1um_APRtools) はM1/M2の2層向けにチャネル配置配線、セル資産、特性化、チップ統合をまとめている。OpenLane/OpenROADを標準設定のまま使えるとは考えない。ただし、2層ならあらゆる汎用ツールが原理的に使えない、という一般論まではここから断定しない。

| 資産 | 意味 |
|---|---|
| Verilogセルモデル | ゲートレベル機能シミュレーション |
| Liberty | 論理機能・面積・遅延・setup/hold等 |
| LEF | 配置配線用のセル寸法・ピン・障害物 |
| GDS | 実際に製造する形状 |
| SPICE | トランジスタ回路、LVS参照、電気的検証 |

**全資産を同じセル世代にそろえる。** [v59_4 README](https://github.com/jun1okamura/TR-1um_APRtools/blob/main/stdcell/v59_4/README.md)は、公式PDKの同名GDSとは別物と明記している。現行v59_4の行高59.4 µm、旧v64_8の64.8 µmを混ぜない。前回の面積例はv64_8由来なので、採用時にv59_4で見積り直す。

現行の`stdcell/v59_4/tr1um_typ_5v0_25c.lib`はSPICE特性化版。`*_area.lib`やプレースホルダ遅延のgenlibはSTA用にしない。[合成資料](https://github.com/jun1okamura/TR-1um_APRtools/blob/main/docs/20_flow_syn.md)・[特性化資料](https://github.com/jun1okamura/TR-1um_APRtools/blob/main/docs/50_char.md)

特性化はtypicalモデル・5 V・25℃が中心。製造ばらつきを含む全PVT保証として扱わない。レイアウト抽出SPICEに拡散面積が入ることと、全配線のRC寄生が抽出されることも区別する。

## 今回の実装順

1. PDK、APRtools、セル、フレームの版を記録して固定する。
2. リセット付き小カウンタをVerilogで作り、RTLシミュレーションする。
3. Yosysの`dfflibmap`でFF、`abc -liberty`で組合せ回路を同一ライブラリへ割り当てる。未マップセル・意図しないラッチ・浮き入力を確認する。
4. ゲートネットリストで同じテストを実行する。RTLの合格とセルへの正しい変換を分けて確認する。
5. 行配置、M1/M2配線、電源・基板/ウェル接続、クロック分配、リセット配線を作る。クロックは単なる一般信号配線で済ませない。
6. コアの公式DRC/LVSを通す。成功してからVGA全体へ拡大する。
7. フレームのパッド方向・入力受け・出力ドライバ・電源へ接続する。1800×1800を信号セルで使い切らず、周辺配線の余地を見込む。
8. タイミングを確認する。6.3 MHzだけでなく、リング6.45 MHz試験なら155.04 ns以下の周期も対象。クロック枝の負荷、出力負荷、リセット解除を確認する。
9. 公式DRC/LVS、必要な抽出SPICE、MDP後のマスク検証を行いGDS/CIRを出す。抽出した回路をそのままLVSの正解側へ置く自己比較はしない。

公式ルールでの最終確認は[APRtoolsの検証手順](https://github.com/jun1okamura/TR-1um_APRtools/blob/main/docs/30_verify_drc_lvs.md)にも明記される。ツールの内部チェッカだけの合格で提出判断をしない。

公開フローの主要入口は`selfcheck.py`、`syn/syn.sh`、`apr/place.py`、`apr/route.py`、`apr/assemble_top.py`、`apr/route_chip.py`、`apr/export_mpw.py`。設計側に`config.py`が必要で、そのまま実行できる万能コマンド列ではない。テンプレートや文書に旧パスが残る例もあるため、採用コミットのコードと設定を照合する。

## 今回の回路に直接影響する発見

- [セル一覧](https://github.com/jun1okamura/TR-1um_APRtools/blob/main/stdcell/CELLS.md)では、入力BUFTHの立上りしきい値がtyp/5 V/25℃で3.433 Vと報告される。これを使うなら3.3 V GPIOのCLK/RESET直結を前提にせず、5 Vレベルへの変換を入れる。
- 逆方向の5 V出力→Tiny VGAは、搭載74LVC245Aの許容条件・基板版を確認して接続する。Pmod電源は3.3 V。
- リング発振器はVGA RTLの外のマクロとする。リング出力専用ピン→基板ジャンパ→CLK入力、という合意済み構成を維持する。
- リングをリセットで止めるなら、コアのリセットはクロック停止中にも有効になる構成とし、解除側だけ同期化する。
- 画像生成RTLからGDSへの変換には、矩形37個という画像の話とは別に、物理配線・電源・クロック設計が必要。

## 調査記録

参照版のAPI応答は`digital_flow/revisions.json`、文書のローカル控えは`digital_flow/`。調査時のmain HEADはPDK `d83eb77`、テンプレート `f09b35f`、APRtools `8f6962b`。PDK devも調べ、論理合成用Liberty/LEFを見つけていない。製作時に使用すべきPDKは主催者の指定版と照合して決める。
