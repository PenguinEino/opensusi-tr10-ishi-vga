# 最新のコアGDS

[build/labeled_core.gds](build/labeled_core.gds) がポート注記済みの最新コア。SHA256: `3948145e00ad30fde2b0843e99b57dc275473ea02cc3441e15a5c27802a1b84c`。12個のトップTEXTのみ追加し、金属・セル形状・階層を変更していない。

描画DRC 0件、マスクFloating SG警告2件。公式LVSの採用参照は ../core_lvs_fixed のSPICE。注記に使った ../core_lvs の参照は12ポート宣言の由来だけとして保存し、最終LVSでは使わない。両者のポート一覧一致も検査済み。[全検証と再現](../../docs/CORE_ROUTING.md)。
