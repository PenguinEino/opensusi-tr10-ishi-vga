#!/usr/bin/env python3
"""Self-contained visual proposal board and hash-bound area evidence."""
import base64,hashlib,json,re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from logo_metal_variants import ROOT,B_NETS,G_NETS,ARTICLE

OUT=ROOT/'samples/metal_proposals'
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True,parents=True)
    files={};items=[]
    def keep(p):
        if p.exists():files[str(p.relative_to(ROOT))]=sha(p)
    for d in sorted((ROOT/'experiments').glob('a_metal_*')):
        trial=d/'trial.json'
        if not trial.exists():continue
        st=json.loads(trial.read_text());key=st['proposal']
        m=json.loads((d/'source_manifest.json').read_text())
        for path,h in m['sha256'].items():assert sha(ROOT/path)==h,path
        s=(d/'build/synthesis.log').read_text()
        area=re.search(r'合計\s+(\d+)\s+([\d,]+) um2',s)
        assert area and s.rstrip().endswith('完了'),d
        verification=d/'build/verification.json'
        gates='pending'
        if verification.exists():
            v=json.loads(verification.read_text());assert v['result']=='PASS'
            for path,h in v['sha256'].items():assert sha(ROOT/path)==h,path
            gates='PASS'
        item={'key':key,'title':st['title'],'base':st['base'],'nets':st['added_nets'],
              'segments':st['added_segments'],'split':st.get('grid_n_diff_split',False),
              'profile':'aligned' if key.endswith('aligned') else 'normal',
              'cells':int(area[1]),'cell_area_um2':int(area[2].replace(',','')),
              'rtl':'PASS' if '[ ok ] tb_rtl  PASS:' in s else 'FAIL','gates':gates,
              'image':'../../'+str((d/'build/reference.png').relative_to(ROOT)),
              'source':str(d.relative_to(ROOT)),'physical':[]}
        for p in sorted((ROOT/'experiments').glob('a_metal_'+key+'_*')):
            rp=p/'build/physical_report.json'
            if rp.exists():
                # Prefixes also match aligned/lite artwork variants. Physical
                # dimensions must belong to this exact synthesized netlist.
                if sha(p/'out/ishi_vga_core_pnr.v')!=sha(d/'out/ishi_vga_core_pnr.v'):continue
                pm=p/'source_manifest.json'
                if pm.exists():
                    for path,h in json.loads(pm.read_text())['sha256'].items():assert sha(ROOT/path)==h,path
                r=json.loads(rp.read_text())
                if 'height_um' in r:
                    q={'name':p.name,'width_um':r['width_um'],'height_um':r['height_um'],
                       'fits_bbox':r['width_um']<=1800 and r['height_um']<=900,
                       'status':'diagnostic, not signoff'}
                    audit=p/'build/audit/metal_connectivity.json'
                    if audit.exists():
                        a=json.loads(audit.read_text())
                        q.update(short_pairs=a['actual_short_net_pair_count'],opens=a['open_net_count'],missing=a['missing_actual_pin_count'])
                    item['physical'].append(q)
                    for f in ['source_manifest.json','config.py','build/physical_report.json','build/diagnostic_compacted.gds',
                              'build/diagnostic_pins.json','build/diagnostic_shapes.json','layout/placement.json',
                              'build/row_optimization.json','build/audit/metal_connectivity.json']:
                        keep(p/f)
        if item['physical']:
            best=min(item['physical'],key=lambda p:p['height_um'])
            item['area_text']=f"配線後 {best['width_um']:.0f}×{best['height_um']:.0f} µm"+('（寸法内・未完成）' if best['fits_bbox'] else '（900超え）')
        else:item['area_text']='配線後寸法：未測定'
        items.append(item)
        for f in ['source_manifest.json','config.py','trial.json','metal.json','ishi_logo.v','ishi_vga_core.v',
                  'build/synthesis.log','out/ishi_vga_core_pnr.v','build/verification.json','build/postbuf.log',
                  'tests/expected_frame.hex','build/reference.png']:
            keep(d/f)
    refs=[
      {'key':'b0','title':'元のB：比較基準','base':'B','segments':0,'nets':[],'cells':256,
       'cell_area_um2':356363,'area_text':'既測定 1784×1120 µm（900超え）','image':'../../experiments/a_half_b128_black/build/reference.png'},
      {'key':'a16','title':'A：全体像の比較','base':'B','segments':16,'cells':361,'cell_area_um2':475365,
       'area_text':'既測定 1784×1718 µm（900超え）','image':'../../experiments/a_half_a128_black/build/reference.png'},
      {'key':'g0','title':'格子版：比較基準','base':'grid','segments':0,'nets':[],'cells':176,'split':False,
       'cell_area_um2':267192,'area_text':'既測定 1784×759 µm（寸法内・未完成）','image':'../../experiments/a_half_grid64_black/build/reference.png'}]
    lookup={x['key']:x for x in [*refs,*items]}
    def font(n):return ImageFont.truetype(FONT,n)
    for name,keys,title in [
        ('b_comparison',['b0','b_y1','b_ends','b_outputs','b_power','a16'],'Bの字形を保って、接続を足す'),
        ('grid_comparison',['g0','g_y1','g_ends','g_power','g_y1_aligned','g_power_aligned'],'半枠向けの別字形：線端・線幅・接続の比較')]:
        cw,ch=544,510;im=Image.new('RGB',(cw*3+32,ch*2+128),'#111827');draw=ImageDraw.Draw(im)
        draw.text((22,14),title,font=font(30),fill='white')
        draw.text((22,62),'RGB111・黒背景 / 目標1800×900 µm / 図形の参照画像（シミュレーション画像ではない）',font=font(17),fill='#b8c7dd')
        for i,key in enumerate(keys):
            x=16+(i%3)*cw;y=112+(i//3)*ch;p=lookup[key]
            draw.rounded_rectangle((x,y,x+cw-12,y+ch-14),12,fill='#202c40')
            draw.text((x+12,y+10),p['title'],font=font(22),fill='white')
            image=Image.open((OUT/p['image']).resolve()).convert('RGB').resize((512,384),Image.Resampling.NEAREST)
            im.paste(image,(x+10,y+48))
            draw.text((x+12,y+440),f"追加{p['segments']}線分 / {p['cells']}セル / {p['cell_area_um2']/1e6:.3f} mm²（セルのみ）",font=font(17),fill='#d1e1f4')
            draw.text((x+12,y+466),p['area_text'],font=font(16),fill='#fed7aa')
        im.save(OUT/(name+'.png'));keep(OUT/(name+'.png'))
    data={'items':items,'refs':refs,'b_rects':json.loads((ROOT/'assets/logo_rectangles.json').read_text()),
          'b_nets':B_NETS,'g_nets':G_NETS,'glyphs':json.loads((ROOT/'experiments/a_half_grid64/glyphs.json').read_text()),
          'g_aligned':{'Y1':[[2,172,4,332]],'VDD':[[14,108,15,204],[41,108,42,204]],'VSS':[[14,300,15,396],[41,300,42,396],[60,300,61,396]]}}
    html='''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ISHIロゴ — Bに意味のある配線を足す</title><style>
*{box-sizing:border-box}body{margin:0;background:#0c1322;color:#e6edf7;font-family:system-ui,"Noto Sans CJK JP",sans-serif;line-height:1.65}main{max-width:1500px;margin:auto;padding:28px}h1{font-size:29px;margin:0}h2{font-size:22px;margin:24px 0 8px}.muted{color:#b5c4da}a{color:#86cff5}.lead{max-width:1100px}.live{display:grid;grid-template-columns:minmax(340px,640px) 1fr;gap:26px;padding:22px;background:#19263b;border-radius:16px}canvas{width:100%;background:#000;image-rendering:pixelated}select,button{background:#293e5b;color:white;border:1px solid #58708e;padding:8px;border-radius:6px;font-size:16px}label{display:inline-block;margin:6px 16px 6px 0}#metrics{color:#ffe0ac;font-weight:600}.cards{display:grid;grid-template-columns:repeat(3,minmax(260px,1fr));gap:16px}.card{padding:14px;background:#19263b;border:2px solid #2a3b53;border-radius:12px;cursor:pointer}.card:hover{border-color:#64d0f0}.card img{width:100%;image-rendering:pixelated}.card h3{margin:0;font-size:19px}.card p{margin:5px 0;font-size:14px}.badge{color:#ffe0ac}.small{font-size:14px}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #33445e;text-align:left;padding:10px}.filter{margin:20px 0}footer{margin:28px 0;color:#b5c4da}@media(max-width:1000px){.cards{grid-template-columns:repeat(2,minmax(240px,1fr))}.live{grid-template-columns:1fr}}@media(max-width:600px){main{padding:12px}.cards{grid-template-columns:1fr}}</style>
<main><h1>Bに、意味のある配線を足す</h1><p class="lead muted">INV / NAND / NOR の出力接続、または電源への枝を選ぶ。元Bの字形を守る案と、面積を抑えるため文字を整理した別案を分けて比較する。全候補RGB111・黒背景・RESETなし。VDD込み、共通VSSを除いて7端子。</p>
<div class="live"><div><canvas id="view" width="640" height="480"></canvas><div class="small muted">640×480の設計参照画像。コンタクトや隠れたポリ配線を省いた図なので、抽出・検証済みのCMOS回路図ではありません。</div></div><div><h2 style="margin-top:0">線を選んで比較</h2><select id="base"><option value="B">元Bの字形</option><option value="grid">格子へ整理した別字形</option></select><div id="toggles"></div><div id="gridControls"><label><input id="split" type="checkbox" checked>NAND/NOR間で下の拡散帯を分割</label><br><label><input id="aligned" type="checkbox">線端を帯の端へ／Y1は幅16 px</label></div><p id="description"></p><p id="metrics"></p><p class="small muted">未測定の組み合わせから、セル数や配線後寸法は推定しません。セル面積は配線・TAP/FILLを含みません。</p></div></div>
<h2>各線の意味</h2><table><tr><th>接続</th><th>線分数</th><th>描く意味</th></tr><tr><td>Y1</td><td>1</td><td>左IのPMOS/NMOSドレインをつなぐ：INVの出力 ¬B</td></tr><tr><td>Y2</td><td>4</td><td>SとH左側を囲むU字：NANDの出力 ¬(A∧B)</td></tr><tr><td>Y3</td><td>3</td><td>右上の折り返し：NORの出力 ¬(A∨B)</td></tr><tr><td>VDD / VSS</td><td>2 + 3</td><td>上下の電源レールとソース領域を接続する枝</td></tr></table><p class="small muted">元Bの4本の横線は追加数に含めない。下側metal2横線は原作でも装飾として残されたもの。RGB111ではmetal1/metal2を同じ水色にしているため、交差の層は原作を参照。</p>
<div class="filter"><button onclick="show('B')">元Bの字形を維持</button> <button onclick="show('grid')">半枠向けの別字形</button> <button onclick="show('all')">すべて</button></div><div id="cards" class="cards"></div>
<footer><a href="ARTICLE" target="_blank">参考：土谷さんの記事</a> / <a href="b_comparison.png">元Bの比較PNG</a> / <a href="grid_comparison.png">格子版の比較PNG</a> / <a href="../../docs/METAL_LOGO_PROPOSALS.md">設計・検証メモ</a><p>見た目の選択前の候補です。旧A/BのRTL・GDSは変更していません。配線結果があっても、DRC/LVS・端子引き出し・フレーム統合の合格を意味しません。</p></footer></main>
<script>const DATA=PAYLOAD;
const ctx=document.getElementById('view').getContext('2d'),base=document.getElementById('base'),split=document.getElementById('split'),aligned=document.getElementById('aligned');
const palette=['#000','#00f','#0f0','#0ff','#f00','#f0f','#ff0','#fff'];const names=['Y1','Y2','Y3','VDD','VSS'];
document.getElementById('toggles').innerHTML=names.map(n=>`<label><input type="checkbox" id="net_${n}" onchange="draw()">${n}</label>`).join('');
function enabled(){return names.filter(n=>document.getElementById('net_'+n).checked && !document.getElementById('net_'+n).disabled)}
function rect(c,x,y,w,h){ctx.fillStyle=palette[c];ctx.fillRect(x,y,w,h)}
function draw(){const b=base.value;document.getElementById('gridControls').style.display=b==='grid'?'block':'none';document.getElementById('net_Y2').disabled=b==='grid';let ns=enabled();const groups=b==='B'?DATA.b_nets:aligned.checked?{...DATA.g_nets,...DATA.g_aligned}:DATA.g_nets;let extras=ns.flatMap(n=>groups[n]);rect(0,0,0,640,480);
if(b==='B'){for(const color of [4,5,1,2,3]){for(const [co,a,y,c,d] of DATA.b_rects){if(co===color)rect(co===4?1:co===5?5:co===2?4:3,64+a*4,24+y*4,(c-a)*4,(d-y)*4)}if(color===1)for(const[a,y,c,d]of extras)rect(3,64+a*4,24+y*4,(c-a)*4,(d-y)*4)}}
else{rect(3,64,92,512,16);rect(3,64,396,512,16);rect(1,64,172,512,32);rect(5,64,300,512,32);if(split.checked)rect(0,384,300,8,32);for(const[a,y,c,d]of extras)rect(3,64+a*8,y,(c-a)*8,d-y);[...'ISHI'].forEach((letter,i)=>DATA.glyphs[letter].forEach((row,j)=>[...row].forEach((on,k)=>{if(on==='1')rect(4,64+i*128+k*16,140+j*32,16,32)})))}
const match=[...DATA.items,...DATA.refs.filter(p=>p.key!=='a16')].find(p=>p.base===b&&JSON.stringify([...p.nets].sort())===JSON.stringify([...ns].sort())&&(b==='B'||(p.split===split.checked&&(p.profile||'normal')===(aligned.checked?'aligned':'normal'))));
document.getElementById('description').textContent=`追加 ${extras.length} 線分：${ns.join(' / ')||'なし'}。${b==='B'?'元Bの文字・帯の座標を維持。':'文字の形・間隔を変更した別案。'}`;
document.getElementById('metrics').textContent=match?`${match.cells}セル / ${(match.cell_area_um2/1e6).toFixed(3)} mm²（セルのみ） / ${match.area_text}`:'この組み合わせは参照画像のみ。面積未測定。';}
function select(p){if(p.key==='a16')return; base.value=p.base;names.forEach(n=>document.getElementById('net_'+n).checked=(p.nets||[]).includes(n));split.checked=p.split!==false;aligned.checked=p.profile==='aligned';draw();document.querySelector('.live').scrollIntoView({behavior:'smooth',block:'start'})}
function show(filter){let all=[...DATA.refs,...DATA.items];document.getElementById('cards').innerHTML=all.filter(p=>filter==='all'||p.base===filter).map(p=>`<article class="card" data-key="${p.key}"><h3>${p.title}</h3><p>追加${p.segments}線分 · ${p.cells}セル · ${(p.cell_area_um2/1e6).toFixed(3)} mm²（セルのみ）</p><img src="${p.image}" alt="${p.title}"><p class="badge">${p.area_text}</p><p>${p.gates?'RTL '+p.rtl+' / 最終ゲート '+p.gates:'保存済み比較基準'}</p></article>`).join('');document.querySelectorAll('.card').forEach(c=>c.onclick=()=>select(all.find(p=>p.key===c.dataset.key)))}
base.onchange=draw;split.onchange=draw;aligned.onchange=draw;select(DATA.items.find(p=>p.key==='b_ends'));show('B');</script></html>'''
    html=html.replace('ARTICLE',ARTICLE).replace('PAYLOAD',json.dumps(data,ensure_ascii=False))
    (OUT/'index.html').write_text(html);keep(OUT/'index.html')
    for p in [Path(__file__),ROOT/'scripts/logo_metal_variants.py',ROOT/'scripts/logo_metal_aligned.py',ROOT/'scripts/logo_metal_lite.py',ROOT/'scripts/metal_route_knobs.py',ROOT/'research/logo_article/sources.json']:
        keep(p)
    preserved=[]
    for name in ['core_escape_snapshot.json','core_routing_snapshot.json','half_slot_results.json','half_a_results.json']:
        old=json.loads((ROOT/'docs'/name).read_text())
        for path,h in old['files'].items():assert sha(ROOT/path)==h,path
        preserved.append({'snapshot':name,'unchanged_files':len(old['files'])})
    result={'article':ARTICLE,'target_um':[1800,900],'proposals':items,'references':refs,'files':files,'preserved':preserved,
            'limits':'Design reference images; no logo-CMOS extraction. Physical results are diagnostic; no signoff or frame integration.'}
    (ROOT/'docs/metal_logo_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:p[k] for k in ['key','cells','cell_area_um2','gates','area_text']} for p in items],ensure_ascii=False,indent=2))


if __name__=='__main__':main()
