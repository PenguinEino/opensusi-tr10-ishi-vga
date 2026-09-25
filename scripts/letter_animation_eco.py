#!/usr/bin/env python3
"""Place a separately mapped letter highlight and idle-stage circuit into verified static filler sites.

Pinned standard cells are unchanged. The old data inputs rerouted are G.D/B.D;
new input branches attach to existing count/decode/colour nets. All geometry
must subsequently pass independent connectivity, official DRC and strict LVS.
"""
import argparse, ast, copy, hashlib, json, math, random, re, sys
from pathlib import Path
import klayout.db as db
from check_toolchain import ROOT, verify
from prune_route_vias import connectivity
sys.path.insert(0,str(ROOT/'tools/APRtools/apr'))
import lef_parser, rules

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cells(text):
    return [(t,n,dict(re.findall(r'\.(\w+)\(([^)]+)\)',b)))
            for t,n,b in re.findall(r'^\s*(\w+)\s+(\S+)\s*\((.*?)\);',text,re.M|re.S) if t!='module']
def settings(d):
    return next(ast.literal_eval(n.value) for n in ast.parse((d/'config.py').read_text()).body
                if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ANIMATION_ECO' for t in n.targets))
def extraction(ly,top):
    regs={t:db.Region(top.begin_shapes_rec(ly.layer(*getattr(rules,t)))).merged() for t in ('M1','M2','V1','GC','GR','CO')}
    l2n=db.LayoutToNetlist(top.name,ly.dbu)
    for t,r in regs.items():l2n.register(r,t);l2n.connect(r)
    for a,b in [('M1','V1'),('M2','V1'),('GC','CO'),('M1','CO')]:l2n.connect(regs[a],regs[b])
    l2n.extract_netlist()
    return regs,l2n
def pinmap(place,lef,ys):
    pins={};layers={}
    for ri,row in enumerate(place['rows']):
        for it in row:
            for pn,p in it['pins'].items():
                if not p.get('net') or p.get('use') in ('POWER','GROUND'):continue
                tag,x1,y1,x2,y2=next(r for r in lef[it['type']]['pins'][pn]['rects'] if r[0] in ('METAL1','METAL2'))
                pins.setdefault(p['net'],[]).append([it['name'],pn,round(it['x']+(x1+x2)/2,4),round(ys[ri]+(y1+y2)/2,4)])
                layers[(it['name'],pn)]={'METAL1':'M1','METAL2':'M2'}[tag]
    return pins,layers

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--design-root',type=Path,required=True);a=ap.parse_args()
    verify();d=a.design_root.resolve();st=settings(d);b=d/'build'
    source=ROOT/st['source_gds'];assert sha(source)==st['source_sha256']
    ly=db.Layout();ly.read(str(source));top=ly.cell('ishi_vga_core');u=lambda v:round(v/ly.dbu)
    lef=lef_parser.parse_lef(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef')
    ys=sorted({round(i.trans.disp.y*ly.dbu,4) for i in top.each_inst() if i.cell.name in {c['foreign'] for c in lef.values()}})
    place=json.loads((ROOT/st['placement']).read_text());oldpins,pl=pinmap(place,lef,ys)
    patch=d/st['patch_dir']/'out/letter_scan_patch_pnr.v'
    portnets=st['port_nets']
    def netname(n):return portnets.get(n,'anim_'+re.sub(r'[^A-Za-z0-9_]','_',n))
    extra=[(t,'anim'+n,{p:netname(net) for p,net in pp.items()}) for t,n,pp in cells(patch.read_text())]
    assert sum(t=='DFF' for t,n,p in extra)==7
    net=(ROOT/st['netlist']).read_text()
    for inst,pin,oldnet,newnet in st['replacements']:
        net,count=re.subn(r'(\bDFF\s+'+re.escape(inst)+r'\s*\(.*?)\.'+pin+r'\('+re.escape(oldnet)+r'\)',lambda m:m[1]+'.'+pin+'('+newnet+')',net,flags=re.S);assert count==1
    newnets=sorted({v for t,n,p in extra for v in p.values() if v.startswith('anim_')})
    addition='\n'.join('  wire '+n+';' for n in newnets)+'\n'
    addition+='\n'.join('  '+t+' '+n+' ('+', '.join('.'+pn+'('+nn+')' for pn,nn in pp.items())+');' for t,n,pp in extra)+'\n'
    (d/'out/ishi_vga_core_pnr.v').write_text(net.replace('endmodule',addition+'endmodule'))
    # Disconnect only the old G.D and B.D top-level routes, retaining cell internals.
    reg,l2n=extraction(ly,top)
    replaced_pins={}
    owned={tag:db.Region() for tag in ('M1','M2','V1')}
    for inst,pin,oldnet,newnet in st['replacements']:
        rp=next(p for p in oldpins[oldnet] if p[:2]==[inst,pin]);replaced_pins[newnet]=rp
        rn=l2n.probe_net(reg[pl[tuple(rp[:2])]],db.Point(u(rp[2]),u(rp[3])));assert rn
        for tag in owned:owned[tag]+=l2n.shapes_of_net(rn,reg[tag],True).merged()
    removed=[]
    for tag in owned:
        li=ly.layer(*getattr(rules,tag))
        for s in list(top.shapes(li).each()):
            if s.is_text():continue
            shape=db.Region(s.polygon)
            if (shape&owned[tag]).is_empty():continue
            assert (shape-owned[tag]).is_empty(),(tag,'partial foreign shape')
            removed.append([tag,s.polygon.to_s()]);top.shapes(li).erase(s)
    for i in list(top.each_inst()):
        if not i.cell.name.startswith('via_'):continue
        vr=db.Region(i.cell.begin_shapes_rec(ly.layer(*rules.V1))).transformed(i.trans)
        if not (vr&owned['V1']).is_empty():i.delete()
    # Long filler runs between retained taps and logic provide the placement bins.
    runs=[]
    for ri in st['rows']:
        for it in sorted(place['rows'][ri],key=lambda it:it['x']):
            if not it['type'].startswith('FILL') or it['name'].startswith('FILLPRI'):continue
            if runs and runs[-1]['row']==ri and abs(runs[-1]['end']-it['x'])<.001:
                runs[-1]['end']=it['x']+it['width'];runs[-1]['names'].append(it['name'])
            else:runs.append({'row':ri,'start':it['x'],'end':it['x']+it['width'],'names':[it['name']]})
    site=min(v['size'][0] for t,v in lef.items() if t.startswith('FILL'))
    runs=[r for r in runs if r['end']-r['start']>=site-.001]
    widths={n:lef[t]['size'][0] for t,n,p in extra};types={n:t for t,n,p in extra};ports={n:p for t,n,p in extra}
    existing_m2=db.Region(top.shapes(ly.layer(*rules.M2))).merged()
    cell_m2={typ:db.Region(ly.cell(lef[typ]['foreign']).begin_shapes_rec(ly.layer(*rules.M2))).merged() for typ in set(types.values())}
    collision_cache={}
    def collision(typ,ri,x):
        key=(typ,ri,x)
        if key not in collision_cache:
            moving=cell_m2[typ].transformed(db.Trans(u(x),u(ys[ri])))
            collision_cache[key]=0 if (moving&existing_m2).is_empty() else st['pin_collision_penalty']
        return collision_cache[key]
    def pack(order):
        placed={};cursors=[run['start'] for run in runs]
        for n in order:
            eligible=[]
            for j,run in enumerate(runs):
                x=cursors[j]
                while x+widths[n]<=run['end']+.001:
                    if not collision(types[n],run['row'],round(x,4)):
                        eligible.append((j,x));break
                    x+=site
            if not eligible:return None
            j,x=eligible[0];placed[n]=(runs[j]['row'],round(x,4));cursors[j]=x+widths[n]
        return placed
    external={}
    for n in portnets.values():
        pp=oldpins.get(n,[])
        if n in replaced_pins:pp=[replaced_pins[n]]
        for inst,pin,oldnet,newnet in st['replacements']:
            if n==oldnet:pp=[p for p in pp if p[:2]!=[inst,pin]]
        if pp:external[n]=[(p[2],p[3]) for p in pp]
    def score(order):
        xy=pack(order)
        if xy is None:return 1e12
        points={n:list(pp) for n,pp in external.items()}
        for n,(ri,x) in xy.items():
            for pn,nn in ports[n].items():
                if pn=='QB' and sum(nn in p.values() for p in ports.values())==1:continue
                rr=next(r for r in lef[types[n]]['pins'][pn]['rects'] if r[0] in ('METAL1','METAL2'))
                points.setdefault(nn,[]).append((x+(rr[1]+rr[3])/2,ys[ri]+(rr[2]+rr[4])/2))
        return sum(max(x for x,y in pp)-min(x for x,y in pp)+max(y for x,y in pp)-min(y for x,y in pp) for pp in points.values())+sum(collision(types[n],ri,x) for n,(ri,x) in xy.items())
    rng=random.Random(st['seed']);order=list(widths);current=score(order);best=(current,order[:])
    steps=st['placement_steps']
    for iteration in range(steps):
        aa,bb=rng.sample(range(len(order)),2);order[aa],order[bb]=order[bb],order[aa]
        value=score(order);temp=st['anneal_temp_start']*(1-iteration/steps)**4+st['anneal_temp_end']
        if value<current or rng.random()<math.exp(min(0,(current-value)/temp)):
            current=value
            if current<best[0]:best=(current,order[:])
        else:order[aa],order[bb]=order[bb],order[aa]
    xy=pack(best[1]);assert xy is not None
    combined=(d/'out/ishi_vga_core_pnr.v').read_text()
    for typ,n,pp in extra:
        if typ!='DFF':continue
        ri,_=xy[n];oldclock=pp['CK'];pp['CK']=f'clk_row{ri}'
        combined,count=re.subn(r'(\bDFF\s+'+re.escape(n)+r'\s*\(.*?)\.CK\('+re.escape(oldclock)+r'\)',lambda m:m[1]+'.CK('+pp['CK']+')',combined,flags=re.S);assert count==1
    (d/'out/ishi_vga_core_pnr.v').write_text(combined)
    removed_names={n for run in runs for n in run['names']};removed_fill=[]
    for ri,row in enumerate(place['rows']):
        for it in row[:]:
            if it['name'] not in removed_names:continue
            matches=[i for i in top.each_inst() if i.cell.name==lef[it['type']]['foreign'] and i.trans.disp==db.Vector(u(it['x']),u(ys[ri]))]
            assert len(matches)==1;matches[0].delete();row.remove(it);removed_fill.append(it)
        for it in row:
            for inst,pin,oldnet,newnet in st['replacements']:
                if it['name']==inst:it['pins'][pin]['net']=newnet
    def insert(typ,name,ri,x,nn):
        cell=ly.cell(lef[typ]['foreign']);assert cell,typ
        top.insert(db.CellInstArray(cell.cell_index(),db.Trans(u(x),u(ys[ri]))))
        pp=copy.deepcopy(lef[typ]['pins'])
        for pn,p in pp.items():p['net']=nn.get(pn)
        place['rows'][ri].append({'type':typ,'name':name,'row':ri,'x':x,'width':lef[typ]['size'][0],'pins':pp})
    for typ,n,pp in extra:
        ri,x=xy[n];insert(typ,n,ri,x,pp)
    filltypes=sorted((t for t in lef if t.startswith('FILL')),key=lambda t:lef[t]['size'][0],reverse=True)
    fi=0
    for run in runs:
        here=sorted((x,n) for n,(ri,x) in xy.items() if ri==run['row'] and run['start']-.001<=x<run['end']-.001)
        cursor=run['start']
        for x,n in here+[(run['end'],None)]:
            while x-cursor>.001:
                typ=next(t for t in filltypes if lef[t]['size'][0]<=x-cursor+.001)
                insert(typ,f'anim_fill_{fi}',run['row'],round(cursor,4),{});fi+=1;cursor+=lef[typ]['size'][0]
            if n:cursor=x+widths[n]
    for row in place['rows']:row.sort(key=lambda i:i['x'])
    pins,layers=pinmap(place,lef,ys);result=connectivity(ly,top,pins,layers)
    for p,val in [('placement.json',place)]: (d/'layout'/p).write_text(json.dumps(val,indent=2)+'\n')
    (b/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');(b/'shapes.json').write_text('{}\n')
    save=db.SaveLayoutOptions();save.gds2_write_timestamps=False;ly.write(str(b/'unrouted.gds'),save)
    report={'source_sha256':sha(source),'added_cells':len(extra),'new_cell_width_um':sum(widths.values()),'hpwl_um':best[0],'placements':xy,'removed_fillers':[i['name'] for i in removed_fill],'removed_colour_shapes':removed,'connections':{**result,'pairs':sorted(result['pairs'])},'hashes':{str(p.relative_to(ROOT)):sha(p) for p in [d/'config.py',patch,Path(__file__),ROOT/st['placement'],ROOT/st['netlist']]}}
    (b/'placement_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k in ('added_cells','new_cell_width_um','hpwl_um','connections')},indent=2))
    assert not result['pairs'] and not result['missing'], 'new cell access overlaps existing routing'

if __name__=='__main__':main()
