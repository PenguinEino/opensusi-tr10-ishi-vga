# 最初のLVS：参照変換の問題により不一致

固定版mklvsnet.pyが _542_.D の `1'h1` をSPICEノード名のまま出力した。最初のcore.lvsdb/logは不一致の記録として保存。**このSPICEを最終LVS参照に使わない。** 採用する独立参照は ../core_lvs_fixed。

セル定義やGDSを変更する代わりに、合成Verilogの当該定数だけをLVS用派生入力でvddに正規化した。[原因・補正・検証](../../docs/CORE_ROUTING.md#lvs参照回路の定数変換)。
