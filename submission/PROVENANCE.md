# 由来・固定版

- 現採用図案：`g_power`（格子＋電源枝5本）。旧A／B案とは別。
- 最終GDS：`experiments/a_clock_tree/build/candidate.gds` とバイト一致。
- SHA256：`299b3203897dd4dffca7fb1a260a68dbd577c4ac4f98fb105cfe9e8579cf650c`。
- 論理：`designs/grid_power/`。RTLと参照フレームは不変。合成後ゲート回路に4個のクロック分岐BUF_X2を追加し、各行のDFFのCK接続を変更。
- スタンダードセル：岡村氏の [TR-1um_APRtools](https://github.com/jun1okamura/TR-1um_APRtools)、コミット `8f6962bf2df1618d633f8a81c230fec895fc83aa` のv59_4。
- PDKとSPICEモデル：[OpenSUSI/TR-1um](https://github.com/OpenSUSI/TR-1um)、コミット `f408d3b5c23a8ebe44f02b0482a9270601e2880f`。
- 固定資産・許可した5ファイルのPCell lookupパッチ：[toolchain.lock.json](toolchain.lock.json)。リングの資産も履歴上ロックに含まれますが、今回の回路にリングはありません。

`manifest.json` の `sources` は提出フォルダ内の各複写先から元ワークスペースへの対応と元SHA256を示します。元パスは履歴情報で、提出フォルダからの実行時依存ではありません。`verification/original/` の報告内パスとハッシュも元環境の履歴です。

## 抽出経路

固定版 `apr/klayout_extract.py --no-combine` で最終GDSから直接抽出。`gen_chip_sim_ready.py` の識別子変換関数のみをimportして、全接続と素子パラメータの保持、識別子衝突0を確認しました。抽出は1790素子、配線RCのPEXではありません。

固定版のガイドは `gen_chip_sim_ready.py` のmainを紹介しますが、そのmainは抽出器へ `--no-combine` を渡しません。改善台帳U96と特性化コードを優先して明示的な抽出経路を選択しました。並列MOSをまとめるとBSIM3の狭幅項等が変わるためです。上流コードは追加編集していません。

抽出トップ端子順：`hsync vdd b g r clk vsync vss`。
独立LVS参照トップ端子順：`b clk g hsync r vsync vdd vss`。
同じ端子名でも順序を取り違えないでください。

## 同梱第三者ファイル

`simulation/models/` は固定PDKのモデル原文です。[PDKのLICENSE](licenses/TR-1um-LICENSE)とモデル内の作者・版の注記を保持しています。v59_4ゲートモデル、独立LVS参照、最終GDSには固定APRtoolsセルが含まれます。固定APRtoolsルートにはLICENSEファイルがなかったため、こちらでライセンスを推定して付け替えていません。

ISHI会ロゴの図案を本設計用に簡略化しています。第三者のロゴ・標準セル・モデルの権利を、本フォルダの作成によって変更するものではありません。
