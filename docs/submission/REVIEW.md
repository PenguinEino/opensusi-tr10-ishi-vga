# レビューと対応状況

**製造レビューの既知クロック容量違反とSTAの失敗検出を修正しました。製造GOではありません。**

- [製造レビュー原文](review/submission_manufacturing_review.md)：旧GDS `3bcfd73d…` が対象。
- [修正内容・検証・残件](review/submission_manufacturing_response.md)：現GDS `299b3203…` が対象。
- [STA正常／異常系の再試験](review/sta_guard_controls/results.json)。

MFG-001はFILL3を4個のBUF_X2へ置き換えてピン容量違反を修正。面積1792.8×897.2 µmと外部端子は維持。配線容量込みの確認はMFG-003に残ります。MFG-004は設計側STA guardで対応しました。

MFG-002（フレーム・パッド・ESD）とMFG-003（RC/PVT、実I/O負荷、IR/EM等）は未解決です。フレーム統合は利用者の指示で保留。Floating SG 1件も残っています。

旧版に対する[gpt-6-astra/xhighレビュー](review/submission_astra_review.md)と[当時のmanifest](review/submission_reviewed_manifest.json)は履歴として保存しています。現行のクロックECOは主担当が検証しており、独立レビュワーの再承認はまだ受けていません。
