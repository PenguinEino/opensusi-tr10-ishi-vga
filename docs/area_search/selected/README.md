# 面積探索の選択候補の証拠

後続の[実セル端子による監査と配線試験](../../ROUTING_AND_POLY.md)で、配線端点表に基づく接続検証の限界を確認した。この保存版の41件は当時の診断結果で、完全な実端子の接続証明ではない。

このディレクトリは監査用スナップショット。実行時の入口は manifest.json に記録した experiments ディレクトリ。
gates_630.png は候補の最終ネットリストのシミュレータ出力から復元した画像。
GDSは接続問題が残る診断用で、公式DRC/LVS合格やテープアウト可能という意味ではない。
route_step7.logは部分取得ログ（欠落と要約を含む）。postrepair_connectivity.log / postrepair_simple_drc.logは修正・圧縮後GDSを独立に再検査した完全な出力。
