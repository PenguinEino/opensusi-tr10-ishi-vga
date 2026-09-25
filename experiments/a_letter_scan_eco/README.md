# 現行の文字発光版

I → S → H → I → 発光なし、各文字16フレーム、発光なし64フレーム（1周128フレーム）。外部3.15 MHz、RGB111、RESETなし。

- [実装・検証・再現手順](../../docs/LETTER_SCAN_IMPLEMENTATION.md)
- [GDSと検証データ](../../submission/README.md)

物理実装は固定した静止画コアへのECOです。`patch_split_toggle` が実際に合成した追加回路、`config.py` の `ANIMATION_ECO` と `LOCAL_REPAIR` が配置・配線・局所修復の設定です。未使用の試作と混ぜず、`scripts/replay_letter_animation_core.py` から再現してください。
