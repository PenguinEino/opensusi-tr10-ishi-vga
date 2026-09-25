# 採用：定数ピンを正規化した独立参照とstrict core LVS

prepare_core_lvs_reference.pyで合成VerilogからLVS用入力を作り、固定版mklvsnet.pyへ渡した。_542_.D の `1'h1` → `vdd` 以外にSPICE回路文が変わらないことを検査。元Verilog・配置・上流コードは変更せず、参照作成にGDSは使用しない。

採用SPICE: build/ishi_vga_core.spice。SHA256 `fcecae367fec09a6497ae8313a392a4e40961afae9a983dff9a76648339a189e`。生成コマンド・入力はbuild/reference_manifest.json、strict公式LVSの結果はbuild/core_lvs.logとcore.lvsdb、回路/ポート/全ネットの一致とハッシュはbuild/lvs_verification.json。[最新GDSと再検証](../../docs/CORE_ROUTING.md)。
