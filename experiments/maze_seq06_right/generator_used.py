#!/usr/bin/env python3
"""Design-owned iterative maze connection of several pure components of one net."""
import ast, hashlib, json, math, struct, subprocess, sys
from pathlib import Path
import numpy as np
from check_toolchain import ROOT, verify
sys.path.insert(0, str(ROOT / 'tools/APRtools/apr'))
import rules, lef_parser
import klayout.db as db
from poly_core_trial import deck_limit


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def settings(design):
    for n in ast.parse((design/'config.py').read_text()).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MAZE_ROUTE' for t in n.targets):
            return ast.literal_eval(n.value)
    raise RuntimeError('MAZE_ROUTE settings missing')


def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--design-root',type=Path,required=True)
    a=ap.parse_args(); design=a.design_root.resolve(); verify()
    st=settings(design); out=design/'build'; out.mkdir(parents=True,exist_ok=True)
    source=ROOT/st['source_gds']; assert sha(source)==st['source_sha256']
    ly=db.Layout(); ly.read(str(source)); top=ly.cell(st.get('top','ishi_vga_core')); dbu=ly.dbu
    def u(v): return round(v/dbu)
    shapes=json.loads((ROOT/st['shapes']).read_text()); target=st['target']; shape_rows=shapes[target]
    # Deduplicate route-map entries by physical layer/box, while validating the
    # configured multiplicity against the actual direct top-level GDS shapes.
    unique=[]; seen={}; removed=[]
    for index in st['remove_shape_indices']:
        tag,*coords=shape_rows[index]; key=(tag,tuple(round(float(x),4) for x in coords))
        if key in seen: continue
        seen[key]=index; unique.append(index)
    mult=st.get('remove_shape_multiplicity',{})
    for index in unique:
        tag,*coords=shape_rows[index]; box=db.Box(*(u(v) for v in coords)); layer=ly.layer(*getattr(rules,tag))
        matches=[s for s in top.shapes(layer).each() if s.is_box() and s.box==box]
        expected=int(mult.get(str(index),1))
        assert len(matches)==expected,(index,tag,coords,len(matches),expected)
        for s in matches: top.shapes(layer).erase(s); removed.append([tag,*coords])
    removed_vias=[]
    for x,y in st.get('remove_vias_um',[]):
        refs=[i for i in top.each_inst() if i.cell.name.startswith('via_1') and i.trans.disp==db.Vector(u(x),u(y))]
        assert refs or [x,y] in st.get('optional_remove_vias_um',[]),('missing configured via',x,y)
        for i in refs:
            removed_vias.append({'cell':i.cell.name,'trans':i.trans.to_s(),'xy_um':[x,y]}); i.delete()

    # Build a fresh flat-connectivity view after each route addition.
    pins=json.loads((ROOT/st['actual_pins']).read_text())
    lef=lef_parser.parse_lef(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef')
    place=json.loads((ROOT/st['placement']).read_text()); types={i['name']:i['type'] for row in place['rows'] for i in row}
    def pin_layer(inst,pin):
        metals={r[0] for r in lef[types[inst]]['pins'][pin]['rects'] if r[0] in ('METAL1','METAL2')}
        assert len(metals)==1,(inst,pin,metals)
        return {'METAL1':'M1','METAL2':'M2'}[next(iter(metals))]
    tags=('M1','M2','V1','GC','GR','CO')
    layers={n:ly.layer(*getattr(rules,n)) for n in tags}
    x0,y0,x1,y1=st['bounds_um']; step=st['grid_um']; w=round((x1-x0)/step)+1; h=round((y1-y0)/step)+1
    widths={'M1':rules.M1_WIDTH_MIN,'M2':rules.M2_WIRE_WIDTH}
    gaps={'M1':rules.M1_WIDE_SPACE_MIN,'M2':rules.M2_SPACE_MIN}
    co_gap,_=deck_limit(ROOT/'tools/TR-1um/libs.tech/klayout/tech/drc/run.drc','V1.CO')
    vp=rules.V1_CUT/2
    final_steps=[]; added={n:[] for n in ('M1','M2','V1')}

    def reextract():
        reg={n:db.Region(top.begin_shapes_rec(layers[n])).merged() for n in tags}
        l2n=db.LayoutToNetlist(top.name,dbu)
        for n,r in reg.items(): l2n.register(r,n); l2n.connect(r)
        for aa,bb in [('M1','V1'),('M2','V1'),('M1','CO'),('GC','CO')]: l2n.connect(reg[aa],reg[bb])
        l2n.extract_netlist()
        target_pins=[]; target_roots={}
        for inst,pin,x,y in pins[target]:
            n=l2n.probe_net(reg[pin_layer(inst,pin)],db.Point(u(x),u(y)))
            assert n is not None,('target actual pin is open',inst,pin,x,y)
            target_pins.append((n,inst,pin,x,y)); target_roots[n.expanded_name()]=n
        root_names=set(target_roots)
        for net,points in pins.items():
            if net==target: continue
            for inst,pin,x,y in points:
                n=l2n.probe_net(reg[pin_layer(inst,pin)],db.Point(u(x),u(y)))
                assert n is None or n.expanded_name() not in root_names,('foreign net still joins target',net,inst,pin,n.expanded_name() if n else None,[(p[1],p[2],p[3],p[4]) for p in target_pins if p[0].expanded_name()==n.expanded_name()])
        groups={}
        for n,inst,pin,x,y in target_pins: groups.setdefault(n.expanded_name(),{'net':n,'pins':[]})['pins'].append([inst,pin,x,y])
        owned={name:{tag:l2n.shapes_of_net(g['net'],reg[tag],True).merged() for tag in ('M1','M2','V1')} for name,g in groups.items()}
        return reg,l2n,groups,owned

    def raster(region):
        arr=np.zeros((h,w),dtype=np.uint8)
        clip=region & db.Region(db.Box(u(x0-step),u(y0-step),u(x1+step),u(y1+step)))
        for p in clip.decompose_trapezoids_to_region().each():
            b=p.bbox(); xa=max(0,int(np.ceil((b.left*dbu-x0)/step-1e-7))); xb=min(w-1,int(np.floor((b.right*dbu-x0)/step+1e-7)))
            ya=max(0,int(np.ceil((b.bottom*dbu-y0)/step-1e-7))); yb=min(h-1,int(np.floor((b.top*dbu-y0)/step+1e-7)))
            if xa<=xb and ya<=yb: arr[ya:yb+1,xa:xb+1]=1
        return arr

    def addrect(tag,xa,ya,xb,yb):
        vals=[round(v/rules.MFG_GRID)*rules.MFG_GRID for v in (xa,ya,xb,yb)]
        top.shapes(layers[tag]).insert(db.Box(*(u(v) for v in vals)))
        added[tag].append([round(v,4) for v in vals])

    # Optional disconnected-source bridge pieces are explicit design settings;
    # they are inserted before component extraction and pass the same purity guard.
    for tag,xa,ya,xb,yb in st.get('pre_route_boxes',[]):
        assert tag in ('M1','M2') and (xa<xb and ya<yb)
        addrect(tag,xa,ya,xb,yb)

    exe=out/'maze_grid'; subprocess.run(['g++','-O3','-std=c++17',str(ROOT/'scripts/maze_grid.cpp'),'-o',str(exe)],check=True)
    max_iter=int(st.get('max_route_iterations',8))
    for iteration in range(1,max_iter+1):
        reg,l2n,groups,owned=reextract()
        if len(groups)==1: break
        if len(groups)<2: raise RuntimeError('expected at least two pure target components')
        components=sorted(groups, key=lambda n:sum(int(r.area()) for r in owned[n].values()))
        startname=components[0]; goalnames=components[1:]
        own_union={tag:sum((owned[n][tag] for n in components),db.Region()).merged() for tag in ('M1','M2','V1')}
        foreign={tag:(reg[tag]-own_union.get(tag,db.Region())).merged() for tag in ('M1','M2','V1')}
        wide_m1=db.Region()
        if st.get('m1_spacing_mode','all_wide')=='local_wide':
            wide_m1=reg['M1'].sized(-u(rules.M1_WIDE_MIN/2)).merged().sized(u(rules.M1_WIDE_MIN/2)).merged(); gaps['M1']=rules.M1_SPACE_MIN
        allow=np.stack([1-raster(foreign[n].sized(u(gaps[n]+widths[n]/2))) for n in ('M1','M2')])
        if not wide_m1.is_empty(): allow[0] &= 1-raster(wide_m1.sized(u(rules.M1_WIDE_SPACE_MIN+widths['M1']/2)))
        forbidden=(foreign['M1'].sized(u(gaps['M1']+vp+rules.V1_ENC_M1))+
                   foreign['M2'].sized(u(gaps['M2']+vp+rules.V1_ENC_M2))+
                   (reg['GC']+reg['GR']).sized(u(vp+rules.V1_GA_SPACE_MIN))+
                   reg['CO'].sized(u(vp+co_gap))+reg['V1'].sized(u(vp+rules.V1_SPACE_MIN)))
        if not wide_m1.is_empty(): forbidden+=wide_m1.sized(u(rules.M1_WIDE_SPACE_MIN+vp+rules.V1_ENC_M1))
        via=1-raster(forbidden)
        terminal_layers=tuple(st.get('terminal_layers',('M1','M2')))
        if not terminal_layers or any(tag not in ('M1','M2') for tag in terminal_layers):
            raise ValueError('terminal_layers must be a nonempty subset of M1/M2')
        start=np.zeros((2,h,w),dtype=np.uint8)
        for layer_index,tag in enumerate(('M1','M2')):
            if tag in terminal_layers: start[layer_index]=raster(owned[startname][tag]) & allow[layer_index]
        goal=np.zeros((2,h,w),dtype=np.uint8)
        for n in goalnames:
            for layer_index,tag in enumerate(('M1','M2')):
                if tag in terminal_layers: goal[layer_index] |= raster(owned[n][tag]) & allow[layer_index]
        if not start.any() or not goal.any(): raise RuntimeError(f'iteration {iteration}: no legal start/goal access on grid')
        sd=out/f'step_{iteration:02d}'; sd.mkdir(exist_ok=True)
        binary=sd/'grid.bin'
        with binary.open('wb') as f:
            f.write(struct.pack('<4i',w,h,st['via_cost_steps'],st['max_expanded_nodes']))
            for arr in (allow,via,start,goal): f.write(arr.astype(np.uint8).tobytes())
        pathfile=sd/'path.txt'; run=subprocess.run([str(exe),str(binary),str(pathfile)],text=True,capture_output=True)
        (sd/'search.log').write_text(run.stdout+run.stderr)
        print(f'iteration={iteration} components={len(groups)} startpins={len(groups[startname]["pins"])} goalcomponents={len(goalnames)} {run.stderr.strip()}',flush=True)
        if run.returncode: raise RuntimeError(f'iteration {iteration}: no path; see {sd}/search.log')
        path=[tuple(map(int,l.split())) for l in pathfile.read_text().splitlines()]
        compressed=[path[0]]
        for i in range(1,len(path)-1):
            aa,bb,cc=path[i-1:i+2]
            if (bb[0]-aa[0],bb[1]-aa[1],bb[2]-aa[2])!=(cc[0]-bb[0],cc[1]-bb[1],cc[2]-bb[2]): compressed.append(bb)
        compressed.append(path[-1]); vcount=0
        for aa,bb in zip(compressed,compressed[1:]):
            za,ia,ja=aa; zb,ib,jb=bb; xa=x0+ia*step; ya=y0+ja*step; xb=x0+ib*step; yb=y0+jb*step
            if za!=zb:
                assert ia==ib and ja==jb; vcount+=1
                for tag,half in [('V1',vp),('M1',vp+rules.V1_ENC_M1),('M2',vp+rules.V1_ENC_M2)]: addrect(tag,xa-half,ya-half,xa+half,ya+half)
            else:
                tag=('M1','M2')[za]; half=widths[tag]/2
                addrect(tag,min(xa,xb)-half,min(ya,yb)-half,max(xa,xb)+half,max(ya,yb)+half)
        step_record={'iteration':iteration,'components_before':len(groups),'start_component':startname,
          'start_pins':groups[startname]['pins'],'goal_components':goalnames,'path_nodes':len(path),'vias':vcount,
          'grid_sha256':sha(binary),'path_sha256':sha(pathfile),'search_log':str((sd/'search.log').relative_to(ROOT))}
        final_steps.append(step_record)
        # Reextract and enforce purity and a strict component decrease now,
        # before spending another search iteration.
        _reg,_l2n,after,_owned_after=reextract()
        if len(after)>=len(groups): raise RuntimeError(f'iteration {iteration}: target component count did not strictly decrease ({len(groups)} -> {len(after)})')
        step_record['components_after']=len(after)
        checkpoint=sd/'checkpoint.gds'; checkpoint_options=db.SaveLayoutOptions(); checkpoint_options.gds2_write_timestamps=False; ly.write(str(checkpoint),checkpoint_options)
        step_record['checkpoint_gds']=str(checkpoint.relative_to(ROOT)); step_record['checkpoint_sha256']=sha(checkpoint)
        (out/'partial_manifest.json').write_text(json.dumps({'source_gds':st['source_gds'],'source_sha256':sha(source),'config_sha256':sha(design/'config.py'),'generator_sha256':sha(Path(__file__)),'iterations':final_steps,'removed_boxes':removed,'removed_vias':removed_vias,'added_boxes':added,'status':'PARTIAL CHECKPOINT; later route steps remain'},indent=2)+'\n')
    else: raise RuntimeError(f'target still has multiple components after {max_iter} route additions')
    reg,l2n,groups,owned=reextract()
    if len(groups)!=1: raise RuntimeError(f'final target remains split into {len(groups)} components')
    dest=out/'candidate.gds'; save=db.SaveLayoutOptions(); save.gds2_write_timestamps=False; ly.write(str(dest),save)
    manifest={'source_gds':st['source_gds'],'source_sha256':sha(source),'candidate_sha256':sha(dest),
      'config_sha256':sha(design/'config.py'),'generator_sha256':sha(Path(__file__)),'solver_sha256':sha(ROOT/'scripts/maze_grid.cpp'),
      'input_hashes':{p:sha(ROOT/p) for p in [st['shapes'],st['actual_pins'],st['placement'],'toolchain.lock.json','tools/APRtools/apr/rules.py','tools/TR-1um/libs.tech/klayout/tech/drc/run.drc','tools/TR-1um/libs.tech/klayout/tech/drc/02_Device.drc']},
      'removed_boxes':removed,'removed_vias':removed_vias,'added_boxes':added,'iterations':final_steps,
      'final_target_component_count':len(groups),'bbox_um':[top.dbbox().left,top.dbbox().bottom,top.dbbox().right,top.dbbox().top],
      'status':'TRIAL ONLY; run full candidate validator before considering adoption'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Candidate',dest,'steps',len(final_steps),'additions',sum(x['path_nodes'] for x in final_steps),flush=True)

if __name__=='__main__': main()
