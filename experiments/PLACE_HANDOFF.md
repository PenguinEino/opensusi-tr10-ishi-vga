# 配置配線探索の引き継ぎ — 2026-09-25

ユーザーが実装担当モデルを変更したため、ここで新しい探索を止めて引き継ぐ。
独自配置アルゴリズム（spectral 分割や swap 改善）は未着手。
上流変更なし、root RTL/config/out/layout に変更なし。

## 最良の測定結果

**B案375セルをそのまま使い、配置と配線設定だけで 1611×2905.0 → 1611×2316.4 µm（高さ20.3%減）。**
ただし step6 の短絡疑い71件が残る。1800角に収まらず、提出用ではない。

- 設計: `experiments/place_b08_prl10`
- 診断用 GDS: `experiments/place_b08_prl10/build/diagnostic_compacted.gds`
- 元配置: `experiments/place_r7_s4_b08`
- 7 rows, 296 tracks = 1598.4 µm 行幅
- seed 4, restarts 80, order passes 20, balance tolerance 0.08, pad weight 1, fill alternate
- 配線チャネル `[216] + [900] * 6 + [216]` µm
- `PRL_MIN_PINS=10`, `SPAN_LANE_PACK=False`
- step6 簡易DRCは各項目0。公式DRC/LVS/寄生込みSTAではない。

## 比較

全件 root B netlist のコピー（375セル、幅8337.6 µm）を使用。
`source_manifest.json` に netlist SHA256 と設定、各 `build/*.log` に結果。
短絡数は verify_connectivity_m1m2 の「PROBLEM(S) FOUND」で、独立した短絡箇所数ではない。

| 案 | 圧縮後幅×高さ µm | 接続問題 | 備考 |
|---|---:|---:|---|
| 現行root B | 1611×2905.0 | 75 | 比較基準 |
| 8 rows / seed1 / 20 restarts | 1611×3687.3 | 146 | 増行だけでは悪化 |
| 7 rows / 幅1771.2 / seed1 / 20 restarts | 1783.8×3045.4 | 67 | 幅拡大だけでは改善せず |
| 6 rows / 幅1771.2 / seed1 / 40 restarts / tol .03 | 1783.8×3105.5 | 138 | 占有率上昇が悪影響 |
| root配置 / PRL10 | 1611×2829.4 | 165 | PRL単独は小幅削減 |
| root配置 / PRL999 | 1611×2942.8 | 184 | PRLほぼ無効化は悪化 |
| root配置 / span pack | 1611×2786.2 | 84 | 既知短絡リスクあり、非採用 |
| seed4 / 80 restarts / tol .08 / PRL5 | 1611×2624.2 | 44 | 配置だけで9.7%改善 |
| 同配置 / PRL10 | **1611×2316.4** | 71 | **最小の測定結果** |
| 同配置 / PRL8 | 1611×2516.2 | 84 | |
| 同配置 / PRL20 | 1611×2586.4 | 123 | |
| 同配置 / span pack | 1611×2570.2 | 51 | |

配置のみ実行済み:

- 7rows seed2 pad0 restarts80: cut450、まだrouteしていない。
- 7rows seed3 restarts20: cut618、悪いためroute省略。
- 9rows seed1 restarts20: cut638、悪いためroute省略。配置見積もり自体が枠超過。
- 7rows seed1 restarts40 tol .20: cut288まで改善したが、行偏りが大きく step3 TAP挿入で `_650_` が入らず失敗。GDS未生成。routeは明示的に失敗したログだけ。
- 7rows seed1 restarts80 tol .12: cut410、配置成功。PRL10 route実行中（下記）。
- 6rows 幅1771.2 seed1 restarts40 tol .08: cut407、配置成功。PRL10 routeを同一シェル内で続けるジョブを開始済み（下記）。

## 進行中プロセス（引継ぎ時点）

2026-09-25、記録時点のPIDは後で終了する可能性あり。psとログで確認すること。

1. PRL5 / tol .08 の短絡修正（最小PRL10版とは別）
   - tool session **51687**
   - shell PID252915, wrapper252916, route.py **252928**
   - `python3 scripts/run_apr.py --design-root experiments/place_r7_s4_b08 apr/route.py --from 7 --to 7`
   - log: `experiments/place_r7_s4_b08/build/route_step7.log`
   - 5 iterationまで進み修正を試行中、最終結果は未確定。
2. 2候補の追加route（開始済み。前半終了後に後半が続く）
   - tool session **71087**
   - shell PID **258421**
   - `python3 scripts/place_routing_knobs.py b12_prl10 --source experiments/place_r7_s1_b12 --prl 10 && python3 scripts/place_routing_knobs.py r6_b08_prl10 --source experiments/place_r6_w328_s1_b08 --prl 10`
   - 前半のroute PID258430（記録時点）、各実験build内にログと診断GDSを出す。

これ以外の探索ジョブは完了。`python3 scripts/place_results.py` で現在のログを集計して
`experiments/place_results.json` を更新できる（結果集計であり、新しいAPRは起動しない）。

## 作成した設計側スクリプト

- `scripts/place_sweep.py`: isolated config + root netlist copyを生成し、固定上流のplace/verify/route/squeezeを `run_apr.py --design-root` 経由で起動。
- `scripts/place_routing_knobs.py`: 既存step4配置をコピーし、設定されたPRL閾値/span packでroute/squeezeする。
- `scripts/place_results.py`: ログから結果を集計。返り値0を合格と判定しない。

再現例:

```sh
python3 scripts/check_toolchain.py
python3 scripts/place_sweep.py r7_s4_b08 --rows 7 --seed 4 --restarts 80 --balance .08 --route
python3 scripts/place_routing_knobs.py b08_prl10 --source experiments/place_r7_s4_b08 --prl 10
python3 scripts/place_results.py
```

同名実験を再実行するとその実験の成果物を上書きする。比較を残す場合は別名にすること。
新しいRTL/netlist候補には、その候補の設計configへ上の配置設定を適用して別の `place.py` を実行する。
本スクリプトは root netlist コピーを前提にしているので、そのまま新候補へ使わないこと。

## コードとの相違点・注意

- `cfg.getenv('PRL_MIN_PINS', ...)` は環境APR_*だけを見る。configへ同名の変数を足すだけでは効かない。
  実験config末尾の設計所有 `getenv` adapterが `ROUTING_KNOBS` 辞書を返す。その他は元関数に渡し、
  外部APR変数は既存guardで禁止。上流ファイルやルータ処理には手を入れていない。rootから採用許可済み。
- configの `finalize(globals())` は実験側の最終グローバル名前空間で一度呼ぶ。
  runpy(rootconfig)→値更新だと config_base._NS が古いままになる罠を避け、今回はroot設計config本文を
  snapshot化して設定行を書き換えている（上流コードのコピーではない）。
- frame開口の古い「幅1600を超すと縦開口1600へ減る」コメントは現行コードと不一致。
  現行 `config_base.frame_opening()` は実GDSから計算し、docstringは1840角が空くと明記。
  幅1771.2は5TAP列になり、TAP位置はcfgから自動計算される。独自プロセス定数なし。
- `SPAN_LANE_PACK=True` はジョグでX区間が膨らんだとき他ネットと接触する既知理由で既定False。
  診断比較としてのみ実行し、改善案の採用値にはしていない。
- row countを増やすと標準セル充填率は下がるが、行を跨ぐ合計距離が増えて今回の配線高さは悪化した。
  balance_tolを少し緩める方が有効。しかし .20 は配置詰めで失敗したため「低cutなら配置成功」と言わない。
