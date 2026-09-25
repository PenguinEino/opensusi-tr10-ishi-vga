# 採用候補の全差分監査

record_routing_checkpoint.pyで検証済みmaze_seq06_fixedをバイト単位でコピーし、143対のrouted_checkpointとの全差分をvalidate_route_candidate.pyで再検証した。結果は短絡143→0対、断線・欠落0、電源・セル階層維持、M1/M2/V1以外の形状変更なし、公式描画/MDPの新規マーカーなし。

入力のSHAとコピー元検証JSONのSHAはconfig.py、結果はbuild/verification.json。[最終GDSとLVS](../../docs/CORE_ROUTING.md)。
