#!/usr/bin/env python3
"""Render sampled digital-simulation outputs as GIFs and a local comparison UI."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from check_toolchain import ROOT

NAMES=['white_pulse','wire_scan','letter_scan','palette_swap']
TITLES=['A · 配線の白点灯','B · 配線を走る光','C · 文字の順次点灯','D · 色の切り替え']
DESCRIPTIONS=['水色の配線全体を、約0.53秒ごとに白く点灯。','8区画のハイライトが左から右へ移動。','I → S → H → I の順に、文字を白く点灯。','赤と緑の出力を切り替え、ロゴの配色を変化。']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--out',type=Path,default=ROOT/'docs/animation_samples');a=ap.parse_args()
 d=a.directory.resolve();out=a.out.resolve();assert d.is_relative_to(ROOT) and out.is_relative_to(ROOT);assert not out.exists()
 area=json.loads((d/'area.json').read_text());evidence={}
 for kind in ['rtl','gates']:
  p=d/('sim_'+kind)/'result.json';r=json.loads(p.read_text());assert r['status']=='PASS'
  for path,h in r['hashes'].items():assert sha(ROOT/path)==h,path
  evidence[kind]=r
 out.mkdir(parents=True,exist_ok=False)
 paths=[ROOT/'toolchain.lock.json',d/'area.json',Path(__file__)]
 cards=[];chosen=[];variants=[]
 palette=[]
 for c in range(8):palette += [255*((c>>s)&1) for s in [2,1,0]]
 palette += [0]*(768-len(palette))
 for i,name in enumerate(NAMES):
  rtl=d/'sim_rtl/build'/f'{name}.bin';gates=d/'sim_gates/build'/f'{name}.bin'
  assert rtl.read_bytes()==gates.read_bytes(),name
  raw=np.frombuffer(rtl.read_bytes(),dtype=np.uint8).reshape(8,525,100)
  data=np.repeat(raw[:,:480,:80]&7,8,axis=2)
  frames=[]
  for ar in data:
   im=Image.fromarray(ar).convert('P');im.putpalette(palette);frames.append(im)
  frames[0].save(out/f'{name}.gif',save_all=True,append_images=frames[1:],duration=[130,140,130,130,140,130,130,140],loop=0,disposal=2,optimize=False)
  sprite=Image.new('RGB',(640,480*8))
  for f,im in enumerate(frames):sprite.paste(im.convert('RGB'),(0,480*f))
  sprite.save(out/f'{name}_sprite.png')
  frames[4 if name!='wire_scan' else 2].convert('RGB').save(out/f'{name}_still.png')
  chosen.append(frames[4 if name!='wire_scan' else 2].convert('RGB'))
  ar=area['variants'][name]
  cards.append(f'''<article><div class="label"><h2>{TITLES[i]}</h2><span>セル面積 +{ar['additional_percent']:.1f}%</span></div>
<canvas width="640" height="480" data-name="{name}" aria-label="{TITLES[i]}のRTLシミュレーション"></canvas>
<p>{DESCRIPTIONS[i]}</p><div class="foot">追加 {ar['additional_cells']}セル / {ar['additional_area_um2']:,.0f} µm² <a href="{name}.gif">GIFを開く</a></div>
<img hidden id="sprite-{name}" src="{name}_sprite.png" alt=""></article>''')
  variants.append({'name':name,'title':TITLES[i],'description':DESCRIPTIONS[i],**ar})
  paths += [rtl,gates,d/name/'ishi_vga_core.v',d/name/'ishi_logo.v',d/name/'config.py',d/name/'out/ishi_vga_core_pnr.v',d/name/'build/synthesis.log']
  shutil.copyfile(d/name/'build/synthesis.log',out/f'{name}_synthesis.log')
  shutil.copyfile(d/name/'out/ishi_vga_core_pnr.v',out/f'{name}_mapped.v')
 # The historical comparison owns its frozen reference; submission is animated.
 reference=ROOT/'docs/animation_samples/static_reference.png'
 if reference.resolve()!=(out/'static_reference.png').resolve():
  shutil.copyfile(reference,out/'static_reference.png')
 shutil.copyfile(d/'static_reference/build/synthesis.log',out/'static_reference_synthesis.log')
 for kind in ['rtl','gates']:shutil.copyfile(d/('sim_'+kind)/'build/simulation.log',out/f'{kind}_simulation.log')
 page='''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ISHI VGA — アニメーション比較</title><style>
*{box-sizing:border-box}body{margin:0;background:#101821;color:#eef4fa;font:15px system-ui,sans-serif}main{max-width:1140px;margin:auto;padding:22px 24px}h1{font-size:27px;margin:0 0 6px}header p{margin:0;color:#b4c4d3;line-height:1.7}.controls{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:17px 0}button,select{background:#243446;color:white;border:1px solid #647991;border-radius:7px;padding:8px 12px;font:inherit;cursor:pointer}button{min-width:100px}input[type=range]{width:200px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}article{background:#1b2837;border:1px solid #33485d;border-radius:10px;padding:12px}.label{display:flex;justify-content:space-between;align-items:center;gap:10px}h2{font-size:18px;margin:0 0 10px}.label span{font-size:13px;color:#77ddd6;white-space:nowrap}canvas{display:block;width:100%;max-height:29vh;object-fit:contain;background:#000;image-rendering:pixelated}article p{margin:9px 0 6px;font-size:14px}.foot{font-size:12px;color:#b4c4d3;display:flex;justify-content:space-between}a{color:#80d2ff}footer{margin-top:15px;color:#aebed0;line-height:1.65;font-size:13px}#position{font-variant-numeric:tabular-nums;color:#8de4db}label{display:flex;align-items:center;gap:6px}@media(max-width:700px){.grid{grid-template-columns:1fr}canvas{max-height:none}.label{flex-wrap:wrap}main{padding:16px}}
</style><main><header><h1>ISHI VGA — アニメーション比較</h1><p>6bitのフレームカウンタで動かす4案。1周64フレーム＝約1.07秒、追加端子0本。</p></header>
<div class="controls"><button id="play">一時停止</button><label>速度<select id="speed"><option value="0.5">0.5×</option><option selected value="1">1×（実時間）</option><option value="2">2×</option></select></label><label><input id="original" type="checkbox">静止画と比較</label><input id="seek" type="range" min="0" max="63" value="0" aria-label="フレーム位置"><span id="position">0 / 64 frame</span></div>
<div class="grid">CARDS</div><footer>RTLは64フレームを連続実行し、各案のRGB・HSYNC・VSYNCを照合。ゲート回路でも代表8フレームを照合し、表示データが一致しました。<br>面積は同じv59_4で新規合成した静止画版との差分です。配線後の外形寸法ではありません。現行提出版とは別の試作です。</footer><img id="static" hidden src="static_reference.png" alt=""></main>
<script>
const canvases=[...document.querySelectorAll('canvas')],play=document.querySelector('#play'),speed=document.querySelector('#speed'),seek=document.querySelector('#seek'),position=document.querySelector('#position'),original=document.querySelector('#original');
let running=true,phase=0,last=performance.now();
function paint(){let frame=Math.floor(phase)%64,sample=Math.floor(frame/8);for(const c of canvases){const ctx=c.getContext('2d');ctx.imageSmoothingEnabled=false;if(original.checked){ctx.drawImage(document.querySelector('#static'),0,0)}else{ctx.drawImage(document.querySelector('#sprite-'+c.dataset.name),0,sample*480,640,480,0,0,640,480)}}seek.value=frame;position.textContent=frame+' / 64 frame'}
play.onclick=()=>{running=!running;play.textContent=running?'一時停止':'再生'};seek.oninput=()=>{phase=Number(seek.value);running=false;play.textContent='再生';paint()};
function step(now){const dt=Math.min(now-last,100);last=now;if(running)phase=(phase+dt*.06*Number(speed.value))%64;paint();requestAnimationFrame(step)}
Promise.all([...document.images].map(im=>im.decode())).then(()=>{last=performance.now();requestAnimationFrame(step)});
</script></html>'''.replace('CARDS','\n'.join(cards))
 (out/'index.html').write_text(page)
 font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',24)
 small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',18)
 sheet=Image.new('RGB',(1312,1112),'#101821');draw=ImageDraw.Draw(sheet)
 for i,im in enumerate(chosen):
  x=8+(i%2)*656;y=8+(i//2)*552
  draw.text((x+8,y+4),TITLES[i],font=font,fill='#eef4fa');sheet.paste(im,(x,y+42))
  r=variants[i];draw.text((x+8,y+524),f"追加 {r['additional_cells']}セル / +{r['additional_percent']:.1f}%",font=small,fill='#77ddd6')
 sheet.save(out/'comparison.png')
 report={'scope':'unadopted animation candidates; digital simulation and mapped cell area','cycle_seconds':64/60,'clock_hz':3150000,'phase_bits':6,'additional_external_pins':0,'simulation':evidence,'area':area,'variants':variants,'hashes':{str(p.relative_to(ROOT)):sha(p) for p in paths},'rendered':{p.name:sha(p) for p in out.iterdir() if p.suffix in ['.png','.gif','.html']}}
 (out/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 table='\n'.join(f"| {r['title']} | +{r['additional_cells']} | +{r['additional_area_um2']:,.0f} | +{r['additional_percent']:.1f}% |" for r in variants)
 readme=f'''# アニメーションの試作比較

[比較ページ](index.html)をローカルブラウザで開くと、4案を同時再生できます。一時停止、速度変更、フレーム位置指定、元の静止画との比較ができます。

```sh
xdg-open docs/animation_samples/index.html
```

| 案 | 追加セル数 | 追加セル面積〔µm²〕 | 増加率 |
|---|---:|---:|---:|
{table}

基準は同じ固定APRtools/v59_4で新規合成した静止画版（209セル、301,192.8 µm²）。現在の提出版に後から加えたクロック分岐4セルは、双方の比較から外しています。これはセル面積の測定であり、配線後の外形寸法ではありません。

全案で6bitカウンタをフレーム末に更新し、1周64フレーム・約1.07秒。カウンタも含めて合成しました。外部CLKは3.15 MHz、追加ピン0、同期タイミングと図案の形を維持します。

RTLは64フレーム・3,360,000クロック/案を連続実行して、独立した既存の静止画参照と画面座標で求めた色変化に対してRGB/HS/VSを照合しました。ゲート回路は8種類の位相開始フレーム・420,000クロック/案を照合し、保存した表示データがRTLとバイト一致しました。ゲートモデルは単位遅延で、初期化は試験側だけにあります。

GIFと比較ページは、このシミュレーションの出力を画像化したものです。GIFの時間単位は10 msなので再生周期は約1.07秒、比較ページは60 Hzを基準に再生します。見た目を描き直した画像ではありません。

## GIFサンプル

'''
 for title,name in zip(TITLES,NAMES):readme+=f'### {title}\n\n![{title}]({name}.gif)\n\n'
 readme+='## 再現\n\n設計ソース・設定は `'+str(d.relative_to(ROOT))+'`。生成・合成・シミュレーションは `scripts/animation_samples.py`、画像化は `scripts/render_animation_samples.py`。試作は現行の `designs/grid_power` と `submission` を変更しません。\n\n[面積の見込み・設定の範囲・再現コマンド](../../experiments/animation_selected/README.md)\n'
 (out/'README.md').write_text(readme)
 print(out/'index.html')

if __name__=='__main__':main()
