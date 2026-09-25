# 主催者テンプレートと採用済みGIO版の照合

2026-09-25。主催者が会話で指定した [MPWテンプレート](https://github.com/OpenSUSI/TR-1um_MPW_template/blob/main/src/tr_1um_username.gds) のmainを読取専用で取得し、コミット `f09b35f66d71f979bfad0d50c863bb0b3e066e9a` とファイルSHAを `research/organizer_template/provenance.json` に記録した。実行用の固定PDK・APRtoolsは変更していない。

|項目|主催者指定リンクのテンプレート|固定済みAPRtoolsのGIO版|
|---|---|---|
|フレームセル|OSS_FRAME|OSS_FRAME_GIO（組立時の改名と区別）|
|信号パッド|OSS_ESD_5V_ANA ×14|OSS_ESD_5V_DIO ×14|
|コア向け信号|パッド信号P<n>|P<n>、OUT<n>、HIZ<n>|
|出力ドライバ|GIOのOSS_DRVを持たない|修正版OSS_DRVあり|
|電源・パッド位置|VSS=8、VDD=16|同じ|
|ダイ|2500×2500 µm|2500×2500 µm|

同じパッド配置でも電気回路は同一ではなく、GIO版をOSS_FRAMEと改名しただけでは指定テンプレートと同じにならない。固定GIO版を使う場合は、これまでどおり対応する凍結SPICEと必ずセットで扱う。

GIO版使用について、ユーザーから「まだ確認していない」と回答があった。その後の指示「統合はまだやらないでいい。とりあえずAやって」に従い、**フレーム統合は停止中**。この差を未解決のままGIOを提出版に確定せず、どちらのGDS/SPICEも混在させない。B案の外周への信号引き出しは完了し、現在は独立したA案コアの面積試験を行っている。

なお、取得したテンプレートのinfo.yamlはPDKタグ `v1.2609.0` を指定している。現在の固定PDKコミットと同一か、最終提出時に互換性を確認する必要があり、この調査では自動更新しない。
