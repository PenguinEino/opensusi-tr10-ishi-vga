# B案（21矩形）の検証 — 2026-09-25

現在の実装。旧37矩形版の結果は`../validation/`に分離して保存。

- `verification.json`: RTL／BUFTH挿入後ネットリストの6.30/6.45 MHz照合PASS。各315,017tick。
- `rtl_630.png` / `gates_630.png`: 実際のモデル出力。事前に選んだB案と全画素一致。
- `synthesis.log`: 今回の合成＋STA＋全画素検証のログ。375セル、495,252 µm²。
- `sta.log`: typ 5 V/25℃・155 ns周期の配線前STA。reg→reg slack 111.806 ns。
- `place.log` / `verify_placement.log`: 7行の配置と検証PASS。
- `route_step6.log`: 初期配線。簡易接続検査は75件のSHORT SUSPECTEDを報告。終了コードだけでPASSにしない。
- `diagnostic_compaction.log`: 短絡修正前のGDSを圧縮し1611×2905 µm。枠外であり、提出不可。
- `manifest.json`: 対象のハッシュ、版、配置・配線条件。

短絡修正、フレーム／リング統合、公式DRC/LVS、配線後タイミング、実機試験は未完了。
