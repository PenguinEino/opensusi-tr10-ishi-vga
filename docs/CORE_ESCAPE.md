# コア外周への10信号の引き出し — 2026-09-25

**B案の10信号を外周へ引き出し、1797.3×1763.9 µm、短絡・断線0、公式描画DRC 0、strict公式LVS一致を確認した。**
マスク側のCLK/RESETのFloating SG警告2件は入力と同じ。パッド・電源・フレーム接続はこの成果に含まない。

最新GDSは [core_escape_v4/build/candidate.gds](../experiments/core_escape_v4/build/candidate.gds)。
`klayout build/ishi_vga_core_escaped.gds` で開ける。
元の[コア内部配線](CORE_ROUTING.md)のGDSと `build/ishi_vga_core_routed.gds` は前段チェックポイントとして保存した。

|ポート|引き出し辺|層|コア座標 µm|
|---|---|---|---|
|r[1]|下|M2|(1520.1, 1.8)|
|r[0]|下|M2|(1584.9, 1.8)|
|g[0]|下|M2|(1649.7, 1.8)|
|b[0]|下|M2|(1714.5, 1.8)|
|vsync|右|M1|(1780.2, 844.2)|
|g[1]|右|M1|(1780.2, 839.7)|
|hsync|右|M1|(1780.2, 850.5)|
|b[1]|右|M1|(1780.2, 1339.2)|
|reset_n|上|M2|(1006.2, 1762.2)|
|clk|上|M2|(1589.4, 1762.2)|

各端点の同名ラベルを移動し、実金属内にM1PIN/M2PINを追加した。電源のトップラベル2個は前段の実レール上に維持している。全987信号端子と421セル配置を再監査し、端点から意図した実端子への導通、他ネットとの分離、電源接続の不変を確認した。標準セルの形状・階層・配置、RTL、B案の画素は変更していない。

[生成設定](../experiments/core_escape_v4/config.py)／[生成記録](../experiments/core_escape_v4/build/manifest.json)／[総合検証](../experiments/core_escape_v4/build/verification.json)／[ハッシュ一覧](core_escape_snapshot.json)。
公式レポートは [描画](../experiments/core_escape_v4/build/drawing.lyrdb)、[マスク](../experiments/core_escape_v4/build/candidate_mdp.lyrdb)、[LVS](../experiments/core_escape_v4/build/core.lvsdb)、[LVSログ](../experiments/core_escape_v4/build/lvs.log)。LVS参照は[定数変換済みの独立参照](../experiments/core_lvs_fixed/build/ishi_vga_core.spice)を継続使用した。

## 探索の修正

最初はセル端子の外へ抜けられないものがあった。M2の3.4 µmピン同士が合法な最小間隔2 µmで隣接する箇所で、障害物の膨張領域の境界を閉区間として塗ったため、ちょうど規則どおりの経路まで禁止していた。
`route_core_escape.py` では探索の禁止領域だけを1 DBU内側にした。金属幅・via寸法・要求間隔は固定ルールどおりで、デッキの規則は変更していない。この探索候補を公式DRCと回路LVSで検証した。

前段の `core_escape`、`core_escape_v2`、`core_escape_v3` は経路探索途中で停止した実験で、完成候補ではない。採用は `core_escape_v4` のみ。

生成には `scripts/route_core_escape.py --design-root experiments/core_escape_v4`、総合検証には次を実行した。再生成する場合は別実験ディレクトリを使い、凍結GDSを上書きしない。

```sh
.venv/bin/python scripts/verify_core_escape.py --design-root experiments/core_escape_v4 \
  --reference experiments/core_lvs_fixed/build/ishi_vga_core.spice
```

次のフレーム統合では[指定テンプレートとGIO版の違い](FRAME_CHOICE.md)について確認が必要。A案の再挑戦は、そのB案の現在作業の後に行うよう[作業内容と元JSON](A_RETRY.md)を記録した。
