#!/usr/bin/env python3
"""Replace four existing filler sites by pinned buffers and split clock by row.

Data placement/routing and the submitted RTL are preserved. Each incremental
route is found by the existing design-owned maze solver and checked against
all signal pin connectivity. Official DRC/LVS remain separate gates.
"""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import numpy as np
import klayout.db as db
from check_toolchain import ROOT, verify
from poly_core_trial import deck_limit
from prune_route_vias import connectivity
sys.path.insert(0, str(ROOT / 'tools/APRtools/apr'))
import lef_parser
import rules


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--design-root', type=Path, required=True)
    a = ap.parse_args(); verify(); design = a.design_root.resolve()
    st = next(ast.literal_eval(n.value) for n in ast.parse((design/'config.py').read_text()).body
              if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CLOCK_ECO' for t in n.targets))
    out = design/'build'; out.mkdir(exist_ok=True)
    for name in ['layout','out']:(design/name).mkdir(exist_ok=True)
    src = ROOT/st['source_gds']; assert sha(src) == st['source_sha256']
    ly = db.Layout(); ly.read(str(src)); top = ly.cell('ishi_vga_core'); u = lambda v: round(v/ly.dbu)
    save = db.SaveLayoutOptions(); save.gds2_write_timestamps = False
    tags = ('M1','M2','V1','GC','GR','CO')
    layers = {t: ly.layer(*getattr(rules,t)) for t in tags}
    lef = lef_parser.parse_lef(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef')
    place = json.loads((ROOT/st['placement']).read_text())
    oldpins = json.loads((ROOT/st['pins']).read_text())
    shapes = json.loads((ROOT/st['shapes']).read_text())
    foreign = {v['foreign'] for v in lef.values()}
    row_y = sorted({round(i.trans.disp.y*ly.dbu,4) for i in top.each_inst() if i.cell.name in foreign})
    removed = []
    for idx in st['remove_clock_boxes']:
        tag,*coords = shapes['clk_buf'][idx]; b = db.Box(*(u(v) for v in coords))
        hits = [s for s in top.shapes(layers[tag]).each() if s.is_box() and s.box == b]
        assert len(hits) == 1, (idx,len(hits))
        top.shapes(layers[tag]).erase(hits[0]); removed.append([tag,*coords])
    for x,y in st['remove_clock_vias']:
        hits = [i for i in top.each_inst() if i.cell.name.startswith('via_1') and i.trans.disp == db.Vector(u(x),u(y))]
        assert hits, (x,y)
        for i in hits: i.delete()
    replacements = []
    typ = st['buffer_cell']; cell = ly.cell(lef[typ]['foreign']); assert cell
    for ri,row in enumerate(place['rows']):
        for item in row:
            if item['type'] == 'DFF':
                assert item['pins']['CK']['net'] == 'clk_buf'
                item['pins']['CK']['net'] = f'clk_row{ri}'
            if item['name'] == st['replace_fillers'][ri]:
                assert item['type'] == 'FILL3' and abs(item['width'] - lef[typ]['size'][0]) < .001
                hits = [i for i in top.each_inst() if i.cell.name == lef['FILL3']['foreign'] and i.trans.disp == db.Vector(u(item['x']),u(row_y[ri]))]
                assert len(hits) == 1
                trans = hits[0].trans; hits[0].delete(); top.insert(db.CellInstArray(cell.cell_index(),trans))
                replacements.append({'old':item['name'],'new':f'u_clk_row{ri}','row':ri,'x':item['x'],'y':row_y[ri]})
                item.update(type=typ, name=f'u_clk_row{ri}', pins=copy.deepcopy(lef[typ]['pins']))
                for pn,p in item['pins'].items():
                    p['net'] = {'A':'clk_buf','Y':f'clk_row{ri}'}.get(pn)
    assert len(replacements) == 4
    pins = {}; pin_layers = {}
    for ri,row in enumerate(place['rows']):
        for item in row:
            for pn,meta in item['pins'].items():
                if not meta.get('net') or meta.get('use') in ('POWER','GROUND'): continue
                rects = lef[item['type']]['pins'][pn]['rects']
                tag,x1,y1,x2,y2 = next(r for r in rects if r[0] in ('METAL1','METAL2'))
                tag = {'METAL1':'M1','METAL2':'M2'}[tag]
                x = item['x']+(x1+x2)/2; y = row_y[ri]+(y1+y2)/2
                pins.setdefault(meta['net'],[]).append([item['name'],pn,round(x,4),round(y,4)])
                pin_layers[(item['name'],pn)] = tag
    (design/'layout/placement.json').write_text(json.dumps(place,indent=2)+'\n')
    (out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    (out/'shapes.json').write_text('{}\n')
    net = (ROOT/st['netlist']).read_text()
    for ri,row in enumerate(place['rows']):
        for item in row:
            if item['type'] != 'DFF': continue
            pat = r'(\bDFF\s+'+re.escape(item['name'])+r'\s*\(.*?)\.CK\(clk_buf\)'
            net,n = re.subn(pat,lambda m:m[1]+f'.CK(clk_row{ri})',net,flags=re.S); assert n == 1
    body = '\n' + '\n'.join(f'  wire clk_row{ri};\n  {typ} u_clk_row{ri} (.A(clk_buf), .Y(clk_row{ri}));' for ri in range(4)) + '\n'
    net = net.replace('endmodule',body+'endmodule')
    (design/'out/ishi_vga_core_pnr.v').write_text(net)
    ly.write(str(out/'unrouted.gds'),save)
    result = connectivity(ly,top,pins,pin_layers)
    assert not result['pairs'] and not result['missing'], result
    print('Prepared',replacements,'opens',result['opens'],flush=True)

    x0,y0,x1,y1 = st['bounds_um']; step = st['grid_um']
    w = round((x1-x0)/step)+1; h = round((y1-y0)/step)+1
    widths = {'M1':rules.M1_WIDTH_MIN,'M2':rules.M2_WIRE_WIDTH}
    gaps = {'M1':rules.M1_SPACE_MIN,'M2':rules.M2_SPACE_MIN}; vp = rules.V1_CUT/2
    co_gap,_ = deck_limit(ROOT/'tools/TR-1um/libs.tech/klayout/tech/drc/run.drc','V1.CO')
    exe = out/'maze_grid'
    subprocess.run(['g++','-O3','-std=c++17',str(ROOT/'scripts/maze_grid.cpp'),'-o',str(exe)],check=True)
    def raster(region):
        arr = np.zeros((h,w),dtype=np.uint8)
        clip = region & db.Region(db.Box(u(x0-step),u(y0-step),u(x1+step),u(y1+step)))
        for p in clip.decompose_trapezoids_to_region().each():
            b = p.bbox()
            xa=max(0,int(np.ceil((b.left*ly.dbu-x0)/step-1e-7))); xb=min(w-1,int(np.floor((b.right*ly.dbu-x0)/step+1e-7)))
            ya=max(0,int(np.ceil((b.bottom*ly.dbu-y0)/step-1e-7))); yb=min(h-1,int(np.floor((b.top*ly.dbu-y0)/step+1e-7)))
            if xa<=xb and ya<=yb: arr[ya:yb+1,xa:xb+1]=1
        return arr
    def grow(region,d): return region.sized(u(d)-1)
    def extract():
        reg = {t:db.Region(top.begin_shapes_rec(layers[t])).merged() for t in tags}
        l2n=db.LayoutToNetlist(top.name,ly.dbu)
        for t,r in reg.items(): l2n.register(r,t); l2n.connect(r)
        for aa,bb in [('M1','V1'),('M2','V1'),('GC','CO'),('M1','CO')]: l2n.connect(reg[aa],reg[bb])
        l2n.extract_netlist(); return reg,l2n
    routes = []
    for name in st['route_order']:
        while True:
            reg,l2n = extract(); roots = {}
            for inst,pin,x,y in pins[name]:
                n=l2n.probe_net(reg[pin_layers[(inst,pin)]],db.Point(u(x),u(y))); assert n
                roots[n.expanded_name()] = n
            if len(roots)==1: break
            owned = [{t:l2n.shapes_of_net(n,reg[t],True).merged() for t in ('M1','M2','V1')} for n in roots.values()]
            # Connect the smallest component to any of the remaining components.
            owned.sort(key=lambda r:sum(r[t].area() for t in ('M1','M2')))
            first=owned[0]; other={t:sum((r[t] for r in owned[1:]),db.Region()).merged() for t in first}
            foreign={t:(reg[t]-first[t]-other[t]).merged() for t in first}
            wide=reg['M1'].sized(-u(rules.M1_WIDE_MIN/2)).merged().sized(u(rules.M1_WIDE_MIN/2)).merged()
            allow=np.stack([1-raster(grow(foreign[t],gaps[t]+widths[t]/2)) for t in ('M1','M2')])
            allow[0] &= 1-raster(grow(wide,rules.M1_WIDE_SPACE_MIN+widths['M1']/2))
            forbid=(grow(foreign['M1'],gaps['M1']+vp+rules.V1_ENC_M1)+grow(foreign['M2'],gaps['M2']+vp+rules.V1_ENC_M2)+grow(reg['GC']+reg['GR'],vp+rules.V1_GA_SPACE_MIN)+grow(reg['CO'],vp+co_gap)+grow(reg['V1'],vp+rules.V1_SPACE_MIN)+grow(wide,rules.M1_WIDE_SPACE_MIN+vp+rules.V1_ENC_M1))
            via=1-raster(forbid)
            terminals=[np.stack([raster(r[t]) for t in ('M1','M2')]) & allow for r in (first,other)]
            assert all(t.any() for t in terminals),(name,'no terminal access')
            folder=out/f'route_{len(routes):02d}'; folder.mkdir(exist_ok=True)
            grid=folder/'grid.bin'; pathfile=folder/'path.txt'
            with grid.open('wb') as f:
                f.write(struct.pack('<4i',w,h,st['via_cost_steps'],st['max_expanded_nodes']))
                for arr in (allow,via,*terminals): f.write(arr.tobytes())
            proc=subprocess.run([str(exe),str(grid),str(pathfile)],text=True,capture_output=True)
            (folder/'search.log').write_text(proc.stdout+proc.stderr)
            print(name,len(roots),proc.stderr.strip(),flush=True)
            if proc.returncode: raise RuntimeError('No legal route '+name)
            path=[tuple(map(int,l.split())) for l in pathfile.read_text().splitlines()]
            compressed=[path[0]]
            for i in range(1,len(path)-1):
                aa,bb,cc=path[i-1:i+2]
                if tuple(b-a for a,b in zip(aa,bb))!=tuple(c-b for b,c in zip(bb,cc)): compressed.append(bb)
            compressed.append(path[-1]); added=[]
            def rect(tag,box):
                box=[round(v/rules.MFG_GRID)*rules.MFG_GRID for v in box]
                top.shapes(layers[tag]).insert(db.Box(*(u(v) for v in box))); added.append([tag,*box])
            for aa,bb in zip(compressed,compressed[1:]):
                za,ia,ja=aa;zb,ib,jb=bb; xa,ya=x0+ia*step,y0+ja*step;xb,yb=x0+ib*step,y0+jb*step
                if za!=zb:
                    for tag,half in [('V1',vp),('M1',vp+rules.V1_ENC_M1),('M2',vp+rules.V1_ENC_M2)]:rect(tag,[xa-half,ya-half,xa+half,ya+half])
                else:
                    tag=('M1','M2')[za];half=widths[tag]/2
                    rect(tag,[min(xa,xb)-half,min(ya,yb)-half,max(xa,xb)+half,max(ya,yb)+half])
            result=connectivity(ly,top,pins,pin_layers)
            assert not result['pairs'] and not result['missing'], result
            ly.write(str(folder/'checkpoint.gds'),save)
            routes.append({'net':name,'nodes':len(path),'added':added,'grid_sha256':sha(grid),'path_sha256':sha(pathfile)})
    result=connectivity(ly,top,pins,pin_layers)
    assert not result['pairs'] and not result['missing'] and not result['opens'],result
    bb=top.dbbox();assert bb.width()<=st['target_size_um'][0] and bb.height()<=st['target_size_um'][1]
    ly.write(str(out/'candidate.gds'),save)
    report={'status':'ROUTED_NOT_SIGNED_OFF','source_sha256':sha(src),'gds_sha256':sha(out/'candidate.gds'),'replacements':replacements,'routes':routes,'size_um':[bb.width(),bb.height()],'power':result['power_component_counts'],'input_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [src,design/'config.py',Path(__file__),ROOT/st['placement'],ROOT/st['pins'],ROOT/st['shapes'],ROOT/st['netlist']]}}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print('ROUTED',report['size_um'],flush=True)


if __name__ == '__main__': main()
