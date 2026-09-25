#!/usr/bin/env python3
"""Connect an animation ECO with the design's existing M1/M2 maze solver.

Uses the same pinned clearances and component-to-component method as
clock_tree_eco.py. Records each route, supports resuming a failed checkpoint,
and never treats geometric connectivity as a substitute for DRC/LVS.
"""
import argparse, json, struct, subprocess
from pathlib import Path
import numpy as np
import klayout.db as db
from letter_animation_eco import ROOT, verify, settings, sha, extraction, pinmap, rules, lef_parser
from prune_route_vias import connectivity
from poly_core_trial import deck_limit

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--design-root',type=Path,required=True);ap.add_argument('--resume',action='store_true');a=ap.parse_args()
    verify();d=a.design_root.resolve();st=settings(d);out=d/'build';save=db.SaveLayoutOptions();save.gds2_write_timestamps=False
    original=out/'unrouted.gds';routes=[];source=original
    if a.resume:
        previous=json.loads((out/'routing_progress.json').read_text());routes=previous['routes']
        assert previous['unrouted_sha256']==sha(original)
        source=out/previous['checkpoint'];assert sha(source)==previous['checkpoint_sha256']
    ly=db.Layout();ly.read(str(source));top=ly.cell('ishi_vga_core');u=lambda v:round(v/ly.dbu)
    lef=lef_parser.parse_lef(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef')
    ys=sorted({round(i.trans.disp.y*ly.dbu,4) for i in top.each_inst() if i.cell.name in {c['foreign'] for c in lef.values()}})
    pins,pinlayers=pinmap(json.loads((d/'layout/placement.json').read_text()),lef,ys)
    result=connectivity(ly,top,pins,pinlayers);assert not result['pairs'] and not result['missing']
    layers={t:ly.layer(*getattr(rules,t)) for t in ('M1','M2','V1','GC','GR','CO')}
    x0,y0,x1,y1=st['bounds_um'];step=st['grid_um'];w=round((x1-x0)/step)+1;h=round((y1-y0)/step)+1
    widths={'M1':rules.M1_WIDTH_MIN,'M2':rules.M2_WIRE_WIDTH};gaps={'M1':rules.M1_SPACE_MIN,'M2':rules.M2_SPACE_MIN};vp=rules.V1_CUT/2
    co_gap,_=deck_limit(ROOT/'tools/TR-1um/libs.tech/klayout/tech/drc/run.drc','V1.CO')
    solver=ROOT/'scripts/maze_grid_preferred.cpp'
    exe=out/'maze_grid';subprocess.run(['g++','-O3','-std=c++17',str(solver),'-o',str(exe)],check=True)
    def raster(region):
        arr=np.zeros((h,w),dtype=np.uint8);clip=region&db.Region(db.Box(u(x0-step),u(y0-step),u(x1+step),u(y1+step)))
        for p in clip.decompose_trapezoids_to_region().each():
            bb=p.bbox();xa=max(0,int(np.ceil((bb.left*ly.dbu-x0)/step-1e-7)));xb=min(w-1,int(np.floor((bb.right*ly.dbu-x0)/step+1e-7)))
            ya=max(0,int(np.ceil((bb.bottom*ly.dbu-y0)/step-1e-7)));yb=min(h-1,int(np.floor((bb.top*ly.dbu-y0)/step+1e-7)))
            if xa<=xb and ya<=yb:arr[ya:yb+1,xa:xb+1]=1
        return arr
    def grow(region,distance):return region.sized(u(distance)-1)
    def span(n):
        pp=pins[n];return max(p[2] for p in pp)-min(p[2] for p in pp)+max(p[3] for p in pp)-min(p[3] for p in pp)
    priority=st['route_priority']
    order=[n for n in priority if n in result['opens']]+sorted((n for n in result['opens'] if n not in priority),key=span)
    print('Route order',order,flush=True)
    for name in order:
        while True:
            reg,l2n=extraction(ly,top);roots={}
            for inst,pin,x,y in pins[name]:
                nn=l2n.probe_net(reg[pinlayers[(inst,pin)]],db.Point(u(x),u(y)));assert nn
                roots[nn.expanded_name()]=nn
            if len(roots)==1:break
            own=[{t:l2n.shapes_of_net(nn,reg[t],True).merged() for t in ('M1','M2','V1')} for nn in roots.values()]
            own.sort(key=lambda rr:sum(rr[t].area() for t in ('M1','M2')))
            first=own[0];other={t:sum((r[t] for r in own[1:]),db.Region()).merged() for t in first}
            foreign={t:(reg[t]-first[t]-other[t]).merged() for t in first}
            wide=reg['M1'].sized(-u(rules.M1_WIDE_MIN/2)).merged().sized(u(rules.M1_WIDE_MIN/2)).merged()
            allow=np.stack([1-raster(grow(foreign[t],gaps[t]+widths[t]/2)) for t in ('M1','M2')])
            allow[0]&=1-raster(grow(wide,rules.M1_WIDE_SPACE_MIN+widths['M1']/2))
            forbidden=(grow(foreign['M1'],gaps['M1']+vp+rules.V1_ENC_M1)+grow(foreign['M2'],gaps['M2']+vp+rules.V1_ENC_M2)+grow(reg['GC']+reg['GR'],vp+rules.V1_GA_SPACE_MIN)+grow(reg['CO'],vp+co_gap)+grow(reg['V1'],vp+rules.V1_SPACE_MIN)+grow(wide,rules.M1_WIDE_SPACE_MIN+vp+rules.V1_ENC_M1))
            via=1-raster(forbidden)
            terminals=[np.stack([raster(rr[t]) for t in ('M1','M2')])&allow for rr in (first,other)]
            assert all(t.any() for t in terminals),(name,'no terminal access')
            folder=out/f'anim_route_{len(routes):03d}';folder.mkdir(exist_ok=True);grid=folder/'grid.bin';pathfile=folder/'path.txt'
            with grid.open('wb') as f:
                f.write(struct.pack('<5i',w,h,st['via_cost_steps'],st['max_expanded_nodes'],st['nonpreferred_cost']))
                for arr in (allow,via,*terminals):f.write(arr.tobytes())
            proc=subprocess.run([str(exe),str(grid),str(pathfile)],capture_output=True,text=True)
            (folder/'search.log').write_text(proc.stdout+proc.stderr);print(name,len(roots),proc.stderr.strip(),flush=True)
            if proc.returncode:raise RuntimeError('No legal route '+name)
            path=[tuple(map(int,line.split())) for line in pathfile.read_text().splitlines()];compressed=[path[0]]
            for i in range(1,len(path)-1):
                aa,bb,cc=path[i-1:i+2]
                if tuple(b-a for a,b in zip(aa,bb))!=tuple(c-b for b,c in zip(bb,cc)):compressed.append(bb)
            compressed.append(path[-1]);added=[]
            def rect(tag,box):
                box=[round(v/rules.MFG_GRID)*rules.MFG_GRID for v in box]
                top.shapes(layers[tag]).insert(db.Box(*(u(v) for v in box)));added.append([tag,*box])
            for aa,bb in zip(compressed,compressed[1:]):
                za,ia,ja=aa;zb,ib,jb=bb;xa,ya=x0+ia*step,y0+ja*step;xb,yb=x0+ib*step,y0+jb*step
                if za!=zb:
                    for tag,half in [('V1',vp),('M1',vp+rules.V1_ENC_M1),('M2',vp+rules.V1_ENC_M2)]:rect(tag,[xa-half,ya-half,xa+half,ya+half])
                else:
                    tag=('M1','M2')[za];half=widths[tag]/2
                    rect(tag,[min(xa,xb)-half,min(ya,yb)-half,max(xa,xb)+half,max(ya,yb)+half])
            check=connectivity(ly,top,pins,pinlayers);assert not check['pairs'] and not check['missing'],check
            checkpoint=folder/'checkpoint.gds';ly.write(str(checkpoint),save)
            routes.append({'net':name,'nodes':len(path),'added':added,'grid_sha256':sha(grid),'path_sha256':sha(pathfile)})
            progress={'status':'PARTIAL','unrouted_sha256':sha(original),'checkpoint':str(checkpoint.relative_to(out)),'checkpoint_sha256':sha(checkpoint),'routes':routes,'opens':check['opens']}
            (out/'routing_progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    result=connectivity(ly,top,pins,pinlayers);assert not result['pairs'] and not result['opens'] and not result['missing'],result
    assert result['power_component_counts']=={'vss':1,'vdd':1} and result['rail_signal_nets']=={'vss':[],'vdd':[]}
    bb=top.dbbox();assert bb.width()<=st['target_size_um'][0] and bb.height()<=st['target_size_um'][1]
    dest=out/'candidate.gds';ly.write(str(dest),save)
    report={'status':'ROUTED_NOT_SIGNED_OFF','gds_sha256':sha(dest),'size_um':[bb.width(),bb.height()],'routes':routes,'connectivity':{**result,'pairs':sorted(result['pairs'])},'hashes':{str(p.relative_to(ROOT)):sha(p) for p in [original,d/'config.py',d/'out/ishi_vga_core_pnr.v',d/'layout/placement.json',Path(__file__),ROOT/'scripts/letter_animation_eco.py',solver,ROOT/'toolchain.lock.json']}}
    (out/'routing_manifest.json').write_text(json.dumps(report,indent=2)+'\n');print('ROUTED',report['size_um'],flush=True)

if __name__=='__main__':main()
