from pathlib import Path
from collections import Counter
import sys, json, hashlib, re
import numpy as np
import klayout.db as db

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/APRtools/apr'))
import rules

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sub=ROOT/'submission'
mf=json.loads((sub/'manifest.json').read_text())
actual={str(p.relative_to(sub)) for p in sub.rglob('*') if p.is_file()}
assert actual==set(mf['files'])|{'manifest.json','SHA256SUMS'}, actual-set(mf['files'])
assert not any(p.is_symlink() for p in sub.rglob('*'))
assert all(sha(sub/p)==s for p,s in mf['files'].items())
assert (sub/'toolchain.lock.json').read_bytes()==(ROOT/'toolchain.lock.json').read_bytes()
ly=db.Layout();ly.read(str(sub/'ishi_vga.gds'));top=ly.cell('ishi_vga_core')
counts=Counter(i.cell.name for i in top.each_inst())
layers={}
for idx in ly.layer_indices():
    r=db.Region(top.begin_shapes_rec(idx)).merged()
    if not r.is_empty():
        layers[str(ly.get_info(idx))]={'polygons':r.count(),'area_um2':r.area()*ly.dbu**2}
ports=json.loads((sub/'ports.json').read_text())
labels={}
for tag in ['M1','M2']:
    for s in top.shapes(ly.layer(*getattr(rules,tag+'_LBL'))).each():
        if s.is_text():
            assert s.text.string not in labels
            labels[s.text.string]=(tag,s.text.x*ly.dbu,s.text.y*ly.dbu)
assert len(labels)==8
for p in ports['ports']:
    t,x,y=labels[p['name']]
    assert t==p['layer'] and all(abs(a-b)<ly.dbu/2 for a,b in zip([x,y],p['xy_um']))
    metal=db.Region(top.begin_shapes_rec(ly.layer(*getattr(rules,t)))).merged()
    px,py=round(x/ly.dbu),round(y/ly.dbu)
    assert not metal.interacting(db.Region(db.Box(px,py,px+1,py+1))).is_empty()
box=top.dbbox()
assert list(ports['bbox_um'])==[box.left,box.bottom,box.right,box.top]
lv=db.LayoutVsSchematic();lv.read(str(OUT/'core.lvsdb'));xref=lv.xref()
circuits=[];pinpairs=[];nets=0;subcircuits=0
for pair in xref.each_circuit_pair():
    assert pair.first() and pair.second() and pair.status()==xref.Match
    circuits.append(pair.first().name)
    if pair.first().name=='ishi_vga_core':
        for p in xref.each_pin_pair(pair):
            assert p.first() and p.second() and p.status()==xref.Match
            assert p.first().name().lower()==p.second().name().lower()
            pinpairs.append(p.first().name())
        for p in xref.each_net_pair(pair):
            assert p.status()==xref.Match
            nets+=1
        for p in xref.each_subcircuit_pair(pair):
            assert p.status()==xref.Match
            subcircuits+=1
assert sorted(pinpairs)==sorted(labels)

# Independent screen-coordinate painter from the accepted glyph/segment data.
frame=np.zeros((525,100),dtype=np.uint8)
frame[92:108,8:72]=3;frame[396:412,8:72]=3
frame[172:204,8:72]=1;frame[300:332,8:72]=5;frame[300:332,48]=0
segments=json.loads((ROOT/'experiments/a_metal_g_power/metal.json').read_text())
for rectangles in segments.values():
    for x0,y0,x1,y1 in rectangles:frame[y0:y1,x0+8:x1+8]=3
glyphs=json.loads((ROOT/'experiments/a_half_grid64/glyphs.json').read_text())
for i,letter in enumerate('ISHI'):
    for row,bits in enumerate(glyphs[letter]):
        for col,bit in enumerate(bits):
            if bit=='1':frame[140+row*32:172+row*32,8+i*16+col*2:10+i*16+col*2]=4
frame[:,:82]|=8;frame[:,94:]|=8;frame[:490,:]|=16;frame[492:,:]|=16
expected=np.array([int(s,16) for s in (sub/'tests/expected_frame.hex').read_text().split()])
assert np.array_equal(frame.ravel(),expected)

# Transition graph independently constructed as numeric state indexes.
def nxt(s):
    h=s%128;v=s//128
    if h!=100:return v*128+(h-1)%128
    return (500 if v==0 else (v+1)%1024)*128+71
distance={};cycles=[]
for start in range(131072):
    seen={};path=[];s=start
    while s not in distance and s not in seen:
        seen[s]=len(path);path.append(s);s=nxt(s)
    if s in seen:
        i=seen[s];cycles.append(len(path)-i)
        for q in path[i:]:distance[q]=0
        path=path[:i]
    for q in reversed(path):distance[q]=distance[nxt(q)]+1
assert cycles==[52500] and max(distance.values())==49928
report={'manifest_sha256':sha(sub/'manifest.json'),'gds_sha256':sha(sub/'ishi_vga.gds'),
    'payload_files':len(mf['files']),'exact_file_set':True,'bbox_um':ports['bbox_um'],
    'top_cells':[c.name for c in ly.top_cells()], 'direct_instance_counts':dict(counts),
    'layer_inventory':layers,'ports_match_labels_and_metal':True,
    'lvs':{'matching_circuits':len(circuits),'ports':pinpairs,'top_nets':nets,'top_subcircuits':subcircuits},
    'independent_artwork_and_raster_match':True,
    'startup':{'states':len(distance),'cycle_lengths':cycles,'max_ticks_to_cycle':max(distance.values())}}
(OUT/'static_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
