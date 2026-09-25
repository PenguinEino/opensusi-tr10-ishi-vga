# 採用：最後の069配線修復

入力はseq05の6対のGDS。右側を含む探索と、configのpost_route_boxesに記録した同一ネットのM1接続により、短絡6→0対、断線・欠落0。描画・MDPとも入力と同じ2件だけ。bboxは(-16.2,0)–(1777.5,1760.3) µmで入力から変更なし。

候補SHA256: `bf999c94134037f42314edbcf5c9ad539207f2d77609c742f61617809aad8215`。

生成器は scripts/maze_route_multicomponent.py、検証器は scripts/validate_route_candidate.py。いずれも `--design-root experiments/maze_seq06_fixed` を使用した。configとbuild/manifest.json、build/verification.jsonをセットで参照する。凍結済み候補を上書きしない。

最初の143対の祖先との全差分検査は ../core_route_audit。最終ポート付きGDSと公式LVSは [最新報告](../../docs/CORE_ROUTING.md)。
