# 文字発光版の抽出SPICE試験

採用GDSを `--no-combine` で再抽出し、配布済み `.extracted` とのバイト一致と、ngspiceでのトランジスタ動作を確認します。条件・対象GDS・試験ケースは `config.py` に固定しています。

```sh
.venv/bin/python scripts/letter_spice_check.py
.venv/bin/python scripts/letter_spice_check.py --check-only
```

20試験・922クロック合格。刺激・モデル・波形・再判定器を [提出フォルダ](../../submission/SPICE.md) に収録しています。5 V/27℃、出力各1 pF、選択した時間区間の検証です。金属配線RCを含むPEXではありません。
