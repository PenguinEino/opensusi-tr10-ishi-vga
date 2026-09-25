#!/usr/bin/env python3
"""Design-owned M1/M2 escape routing from actual core nets to configured edges.

Reuses the checked grid solver and pin audit. It does not alter standard cells
or upstream tools. Each escape is extracted again; DRC/LVS are separate gates.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np
import klayout.db as db
from check_toolchain import ROOT, verify
from poly_core_trial import deck_limit
from prune_route_vias import connectivity
from validate_route_candidate import pin_layer_map, non_top_cell_inventory
sys.path.insert(0, str(ROOT / 'tools/APRtools/apr'))
import rules


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--design-root', type=Path, required=True)
    a = ap.parse_args(); design = a.design_root.resolve(); verify()
    st = None
    for node in ast.parse((design / 'config.py').read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CORE_ESCAPE' for t in node.targets):
            st = ast.literal_eval(node.value)
    assert st is not None
    out = design / 'build'; out.mkdir(parents=True, exist_ok=True)
    src = ROOT / st['source_gds']; assert sha(src) == st['source_sha256']
    inputs = [src, design / 'config.py', Path(__file__), ROOT / 'scripts/maze_grid.cpp',
              ROOT / st['actual_pins'], ROOT / st['placement'], ROOT / 'toolchain.lock.json',
              ROOT / 'tools/APRtools/apr/rules.py', ROOT / 'scripts/prune_route_vias.py',
              ROOT / 'tools/TR-1um/libs.tech/klayout/tech/drc/run.drc',
              ROOT / 'tools/TR-1um/libs.tech/klayout/tech/drc/02_Device.drc']
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    ly = db.Layout(); ly.read(str(src)); top = ly.cell(st['top']); dbu = ly.dbu
    u = lambda x: round(x / dbu)
    tags = ('M1', 'M2', 'V1', 'GC', 'GR', 'CO')
    layers = {n: ly.layer(*getattr(rules, n)) for n in tags}
    pins = json.loads((ROOT / st['actual_pins']).read_text())
    pin_layers, _, _ = pin_layer_map(ROOT / st['placement'])
    baseline = connectivity(ly, top, pins, pin_layers)
    assert not baseline['pairs'] and not baseline['opens'] and not baseline['missing']
    cells = non_top_cell_inventory(ly, top.name)
    x0, y0, x1, y1 = st['bounds_um']; step = st['grid_um']
    w = round((x1 - x0) / step) + 1; h = round((y1 - y0) / step) + 1
    widths = {'M1': rules.M1_WIDTH_MIN, 'M2': rules.M2_WIRE_WIDTH}
    gap = {'M1': rules.M1_SPACE_MIN, 'M2': rules.M2_SPACE_MIN}
    vp = rules.V1_CUT / 2
    co_gap, _ = deck_limit(ROOT / 'tools/TR-1um/libs.tech/klayout/tech/drc/run.drc', 'V1.CO')
    exe = out / 'maze_grid'
    subprocess.run(['g++', '-O3', '-std=c++17', str(ROOT / 'scripts/maze_grid.cpp'), '-o', str(exe)], check=True)
    save = db.SaveLayoutOptions(); save.gds2_write_timestamps = False
    routes = []; added = {tag: [] for tag in ('M1', 'M2', 'V1')}

    def raster(region):
        arr = np.zeros((h, w), dtype=np.uint8)
        clip = region & db.Region(db.Box(u(x0-step), u(y0-step), u(x1+step), u(y1+step)))
        for p in clip.decompose_trapezoids_to_region().each():
            b = p.bbox()
            xa = max(0, int(np.ceil((b.left*dbu-x0)/step-1e-7)))
            xb = min(w-1, int(np.floor((b.right*dbu-x0)/step+1e-7)))
            ya = max(0, int(np.ceil((b.bottom*dbu-y0)/step-1e-7)))
            yb = min(h-1, int(np.floor((b.top*dbu-y0)/step+1e-7)))
            if xa <= xb and ya <= yb: arr[ya:yb+1, xa:xb+1] = 1
        return arr

    def extract():
        reg = {tag: db.Region(top.begin_shapes_rec(layers[tag])).merged() for tag in tags}
        l2n = db.LayoutToNetlist(top.name, dbu)
        for tag, r in reg.items(): l2n.register(r, tag); l2n.connect(r)
        for aa, bb in [('M1','V1'), ('M2','V1'), ('GC','CO'), ('M1','CO')]: l2n.connect(reg[aa],reg[bb])
        l2n.extract_netlist()
        return reg, l2n

    def rect(tag, coords):
        vals = [round(v / rules.MFG_GRID) * rules.MFG_GRID for v in coords]
        top.shapes(layers[tag]).insert(db.Box(*(u(v) for v in vals)))
        added[tag].append([round(v,4) for v in vals])

    for index, route in enumerate(st['ports']):
        name, edge = route['net'], route['edge']; reg, l2n = extract()
        roots = {}
        for inst, pin, x, y in pins[name]:
            n = l2n.probe_net(reg[pin_layers[(inst,pin)]], db.Point(u(x),u(y)))
            assert n is not None
            roots[n.expanded_name()] = n
        assert len(roots) == 1
        own_net = next(iter(roots.values()))
        owned = {t: l2n.shapes_of_net(own_net,reg[t],True).merged() for t in ('M1','M2','V1')}
        foreign = {t: (reg[t] - owned[t]).merged() for t in owned}
        wide = reg['M1'].sized(-u(rules.M1_WIDE_MIN/2)).merged().sized(u(rules.M1_WIDE_MIN/2)).merged()
        allow = np.stack([1-raster(foreign[t].sized(u(gap[t]+widths[t]/2))) for t in ('M1','M2')])
        allow[0] &= 1-raster(wide.sized(u(rules.M1_WIDE_SPACE_MIN+widths['M1']/2)))
        forbidden = (foreign['M1'].sized(u(gap['M1']+vp+rules.V1_ENC_M1)) +
            foreign['M2'].sized(u(gap['M2']+vp+rules.V1_ENC_M2)) +
            (reg['GC']+reg['GR']).sized(u(vp+rules.V1_GA_SPACE_MIN)) +
            reg['CO'].sized(u(vp+co_gap)) + reg['V1'].sized(u(vp+rules.V1_SPACE_MIN)) +
            wide.sized(u(rules.M1_WIDE_SPACE_MIN+vp+rules.V1_ENC_M1)))
        via = 1-raster(forbidden)
        start = np.zeros((2,h,w), dtype=np.uint8)
        for z,t in enumerate(('M1','M2')):
            if t in route.get('terminal_layers', st['terminal_layers']): start[z] = raster(owned[t]) & allow[z]
        goal = np.zeros_like(start)
        lo,hi = route.get('range_um', [x0,x1] if edge in ('TOP','BOTTOM') else [y0,y1])
        if edge in ('TOP','BOTTOM'):
            k = h-1 if edge == 'TOP' else 0
            indices = np.where((x0+np.arange(w)*step >= lo) & (x0+np.arange(w)*step <= hi))[0]
            goal[1,k,indices] = allow[1,k,indices]
        elif edge in ('LEFT','RIGHT'):
            k = 0 if edge == 'LEFT' else w-1
            indices = np.where((y0+np.arange(h)*step >= lo) & (y0+np.arange(h)*step <= hi))[0]
            goal[0,indices,k] = allow[0,indices,k]
        else: raise ValueError(edge)
        assert start.any() and goal.any(), ('no start/goal',name)
        folder = out / f'port_{index:02d}'; folder.mkdir(exist_ok=True)
        grid = folder/'grid.bin'; pathfile = folder/'path.txt'
        with grid.open('wb') as f:
            f.write(struct.pack('<4i',w,h,st['via_cost_steps'],st['max_expanded_nodes']))
            for arr in (allow,via,start,goal): f.write(arr.tobytes())
        run = subprocess.run([str(exe),str(grid),str(pathfile)],text=True,capture_output=True)
        (folder/'search.log').write_text(run.stdout+run.stderr)
        print(name,edge,run.stderr.strip(),flush=True)
        if run.returncode: raise RuntimeError(f'No escape path for {name}')
        path = [tuple(map(int,line.split())) for line in pathfile.read_text().splitlines()]
        compressed = [path[0]]
        for i in range(1,len(path)-1):
            aa,bb,cc = path[i-1:i+2]
            if tuple(b-a for a,b in zip(aa,bb)) != tuple(c-b for b,c in zip(bb,cc)): compressed.append(bb)
        compressed.append(path[-1]); vias = 0
        for aa,bb in zip(compressed,compressed[1:]):
            za,ia,ja=aa; zb,ib,jb=bb; xa,ya=x0+ia*step,y0+ja*step; xb,yb=x0+ib*step,y0+jb*step
            if za != zb:
                assert ia == ib and ja == jb; vias += 1
                for t,half in [('V1',vp),('M1',vp+rules.V1_ENC_M1),('M2',vp+rules.V1_ENC_M2)]: rect(t,[xa-half,ya-half,xa+half,ya+half])
            else:
                t = ('M1','M2')[za]; half = widths[t]/2
                rect(t,[min(xa,xb)-half,min(ya,yb)-half,max(xa,xb)+half,max(ya,yb)+half])
        for tag,*box in route.get('junction_boxes',[]): rect(tag,box)
        z,i,j=path[-1]; tag=('M1','M2')[z]; x,y=x0+i*step,y0+j*step
        after = connectivity(ly,top,pins,pin_layers)
        assert not after['pairs'] and not after['opens'] and not after['missing'], (name,after)
        assert after['power_component_counts'] == baseline['power_component_counts']
        assert after['rail_signal_nets'] == baseline['rail_signal_nets']
        # Check the escaped end explicitly before moving its only top label.
        rr,nn=extract(); end=nn.probe_net(rr[tag],db.Point(u(x),u(y)))
        for inst,pin,px,py in pins[name]:
            net=nn.probe_net(rr[pin_layers[(inst,pin)]],db.Point(u(px),u(py)))
            assert end and net and end.expanded_name()==net.expanded_name()
        removed_labels = []
        for t in ('M1','M2'):
            sl = ly.layer(*getattr(rules,t+'_LBL'))
            for shape in list(top.shapes(sl).each()):
                if shape.is_text() and shape.text.string == name:
                    removed_labels.append([t,shape.text.trans.to_s()]); top.shapes(sl).erase(shape)
        assert len(removed_labels) == 1, (name,removed_labels)
        top.shapes(ly.layer(*getattr(rules,tag+'_LBL'))).insert(db.Text(name,db.Trans(u(x),u(y))))
        half=widths[tag]/2
        top.shapes(ly.layer(*getattr(rules,tag+'_PIN'))).insert(db.Box(u(x-half),u(y-half),u(x+half),u(y+half)))
        checkpoint=folder/'checkpoint.gds'; ly.write(str(checkpoint),save)
        routes.append({'net':name,'edge':edge,'xy_um':[round(x,4),round(y,4)],'layer':tag,'path_nodes':len(path),'vias':vias,
            'old_label':removed_labels,'grid_sha256':sha(grid),'path_sha256':sha(pathfile),'checkpoint_sha256':sha(checkpoint)})
        (out/'partial_manifest.json').write_text(json.dumps({'status':'PARTIAL, not DRC/LVS validated','routes':routes,'added_boxes':added,'input_hashes':hashes},indent=2)+'\n')
    assert non_top_cell_inventory(ly,top.name)==cells
    assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    dest=out/'candidate.gds'; ly.write(str(dest),save); bb=top.dbbox()
    size=[bb.width(),bb.height()]; assert all(v<=lim for v,lim in zip(size,st['max_core_size_um'])), size
    manifest={'status':'TRIAL: connectivity passed; official DRC/LVS still required','candidate_sha256':sha(dest),
        'input_hashes':hashes,'routes':routes,'added_boxes':added,'bbox_um':[bb.left,bb.bottom,bb.right,bb.top],'size_um':size}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(dest,size,flush=True)


if __name__=='__main__': main()
