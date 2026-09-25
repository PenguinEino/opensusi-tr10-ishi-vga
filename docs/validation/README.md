# 2026-09-25 検証スナップショット

対象のハッシュ・ツール版・配置条件は`manifest.json`。現在のソースを変更したら、この保存結果をその変更の検証結果として扱わない。

- `verification.json` / `tests.log`: RTLと最終BUFTH入りネットリスト、6.30/6.45 MHzの全tick照合。
- `rtl_630.png` / `gates_630.png`: モデル出力から復元した画像。参考画像のコピーではない。
- `synthesis.log`: 最初の合成ログ。この時点ではOpenSTA未導入なので段9はskip。その後にビルドして実施したSTA結果が`sta.log`。
- `place.log` / `verify_placement.log`: 9行の配置とその検証。配線成功を意味しない。
- `route_compact_failed.log`: 小さいチャネル予算でのstep6失敗。
- `diagnostic_compaction.log`: 大きいチャネル予算によるstep6出力を、短絡修正前に診断目的で圧縮した結果。**1611×5544.9 µmで枠外、DRC/LVS未合格。提出禁止。**

完全な作業ログは`build/`、再生成可能なネットリストとGDSは`out/` / `layout/`にある。これらはGitの対象外。最終フレーム付きGDSや提出用`src/`はまだ作っていない。
