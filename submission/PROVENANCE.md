# 固定版・由来

- 採用回路：格子＋電源枝5本の図案に、文字の順次発光と64フレームの休止を追加。
- RTL・配置配線設定：`experiments/a_letter_scan_eco/`。装飾の後処理設定：`experiments/a_letter_silicon_art/config.py`。
- GDS SHA256：`95a799066aeade8a5ca04cd1425252759988ee61c429f383c699b1b17e4d29b3`。
- 岡村氏の[APRtools](https://github.com/jun1okamura/TR-1um_APRtools)：`8f6962bf2df1618d633f8a81c230fec895fc83aa`、v59_4のGDS／LEF／SPICE／特性化Libertyを組として使用。
- [OpenSUSI/TR-1um](https://github.com/OpenSUSI/TR-1um)：dev由来の `f408d3b5c23a8ebe44f02b0482a9270601e2880f` に固定。
- 記録済みのPCell technology lookupパッチだけを適用。上流のセル内部やプロセス定数は変更していません。

抽出は `klayout_extract.py --no-combine`。配布GDSから新規に再抽出し、同梱 `.extracted` とバイト一致を確認しました。1990素子のW/L・拡散面積・周長・接続を保ち、識別子だけをngspice向けに変換しています。識別子の衝突は0です。

抽出トップ端子順は `hsync vdd b r g clk vsync vss`。独立LVS参照の順序はその `.SUBCKT` 宣言を使用してください。同じ端子名でも位置順を流用しないでください。

`manifest.json` は全同梱ファイルのハッシュと複写元を記録します。検証ログの元ワークスペース内パスは由来情報です。自己完結した試験の入口は [REPRODUCE.md](REPRODUCE.md) に記載しています。

`simulation/models/` は固定PDKの原文です。[TR-1umのLICENSE](licenses/TR-1um-LICENSE)と各モデルの作者・版の注記を保持しています。ロゴ・スタンダードセル・モデルの権利を変更するものではありません。

装飾前GDSは `4a56593ff8f9d61112e69780ed80f04ef276713d3f8fa88901554c8dbbbee22b`、`release/ishi_vga_letter_scan_core` に保持しています。`verification/base_core.json` と `base_review.json` はこの凍結コアの結果です。`replay.json`、配置・配線・修復manifest、STA・functional記録も装飾前の由来です。最終GDSの物理検査は `verification/verification.json` と同フォルダのDRC／MDP／LVS、新規SPICEは `simulation/summary.json` を参照してください。装飾前後の全機能図形・端子・抽出回路の同一性を検査しています。
