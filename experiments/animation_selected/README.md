# 小面積アニメーションの比較実験

[動画と比較ページ](../../docs/animation_samples/README.md)。現行の `g_power` の形状を保ち、出力色だけを変える4案です。外部CLKは3.15 MHz、端子数は従来どおりです。

## 合成結果

同じ固定v59_4で静止画版も合成し直して比較しました。

| 案 | フレームカウンタの記述 | 合成セル数 | 合成セル面積 µm² | 静止画からの増分 |
|---|---|---:|---:|---:|
| 静止画 | なし | 209 | 301,192.8 | — |
| A：配線の白点灯 | 加算値を0/1にする | 222 | 335,834.6 | +11.50% |
| B：配線を走る光 | enable付き加算 | 227 | 344,494.8 | +14.38% |
| C：文字の順次点灯 | 加算値を0/1にする | 224 | 340,004.9 | +12.89% |
| D：色の切り替え | 加算値を0/1にする | 225 | 341,929.4 | +13.53% |

6bitのフレームカウンタを含む数字です。22個だったDFFが28個になり、64フレームで1周します。カウンタの2通りの書き方を全案で合成し、小さかった方を採りました。`selection.json` は選択元と実行時ファイルのハッシュ、`area.json` はセル種別ごとの集計です。

## 1800×900 µmへの見込み

現行の1792.8×897.2 µmのコア配置を調べると、4行目のフィラー面積は約60,303 µm²、全行の合計は約102,964 µm²でした。今回の増分34,642〜43,302 µm²は4行目のフィラー面積より小さく、セルを置く面積の余地はあります。出典と集計は `placement_room.json` に記録しました。

これは既存の外形を維持して配置配線を試す根拠であり、収まるという確定結果ではありません。配線の混雑とクロック負荷の増加は、採用候補を選んで配置配線する段階で確認します。基準面積には、現行提出版で合成後に追加したクロック分岐4セルを含めていません。

面積優先ならA、動きの分かりやすさならBを次の候補にします。

## 検証と設定の範囲

- RTL：64フレームを連続実行し、各案3,360,000クロックでRGB/HS/VSを照合。
- ゲート回路：位相0、8、16、24、32、40、48、56から各1フレームを実行し、各案420,000クロックで照合。
- 保存した代表8フレームの表示データはRTLとゲート回路でバイト一致。
- 初期化はテストベンチだけ。合成対象にresetや初期値は追加していません。

`config.py` は現行設計から派生した合成実験用設定です。冒頭の説明、`ADOPTED`、配置関連の値はコピー元の静止画設計の情報を引き継いでいます。この実験自体の範囲は末尾の `ANIMATION` に記録しています。既存の静止画用テストベンチとSTAは無効にし、上記のアニメーション専用試験を別に実行しています。新しい物理配置・DRC・LVS・STA結果として扱わないでください。

## 再現

ツールの準備は [APRtools採用手順](../../docs/APRTOOLS_ADOPTION.md) に従います。合成は固定APRtoolsの `syn/syn.sh` を `scripts/run_apr.py` 経由で実行します。

クリーンなチェックアウトで、リポジトリのルートから：

```sh
python3 scripts/apply_toolchain_patches.py
python3 scripts/check_toolchain.py
python3 scripts/animation_samples.py synthesize --directory experiments/animation_selected
python3 scripts/animation_samples.py rtl --directory experiments/animation_selected
python3 scripts/animation_samples.py gates --directory experiments/animation_selected
.venv/bin/python scripts/render_animation_samples.py --directory experiments/animation_selected --out build/animation_samples_recheck
xdg-open build/animation_samples_recheck/index.html
```

画像化にはNumPy、Pillow、Noto Sans CJKフォントが必要です。シミュレーション用ディレクトリ `sim_rtl` / `sim_gates` と画像の出力先は、既存結果を誤って上書きしないため新規である必要があります。

2通りのカウンタ記述からの選択も再実行する場合は、未作成の次のディレクトリを使います。

```sh
python3 scripts/animation_samples.py prepare --directory experiments/animation_samples --counter-style enable
python3 scripts/animation_samples.py synthesize --directory experiments/animation_samples
python3 scripts/animation_samples.py prepare --directory experiments/animation_addenable --counter-style add_enable
python3 scripts/animation_samples.py synthesize --directory experiments/animation_addenable
python3 scripts/animation_samples.py select --directory experiments/animation_reselected
```

`select` はこの2つの固定された比較元から選びます。公開済みのプレビューと測定ログは `docs/animation_samples` に保存しています。
