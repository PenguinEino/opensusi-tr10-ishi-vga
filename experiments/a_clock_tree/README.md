# 製造レビュー対応：クロック4分岐

設定はconfig.py、現行提出物は `../../submission/`。FILL3を4個のv59_4 BUF_X2に交換し、既存行クロックを分割する。RTL・図案・寸法・外部端子は不変。詳細は `../../docs/reviews/submission_manufacturing_response.md`。

再現はリポジトリルートから `.venv/bin/python scripts/replay_clock_core.py --out build/new_clock_replay`。build/out/layoutはローカル検証領域でGitに載せず、提出フォルダの記録と再現アーカイブへ梱包する。旧releaseを上書きしない。

本ディレクトリのRTLは試験用に現行designs/grid_powerから複写したもの。新規合成だけでは物理クロックECOは反映されない。リング、リセット、フレームを追加しない。
