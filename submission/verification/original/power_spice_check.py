#!/usr/bin/env python3
"""Transistor-level checks of the final GDS, using pinned no-combine extraction.

No upstream code edits. Stimuli and checks are design-owned; conversion calls
the pinned helper functions and verifies one-to-one names. No wire RC claimed.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import numpy as np
from check_toolchain import ROOT, verify

D=ROOT/'experiments/a_clock_tree'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def settings():
    return next(ast.literal_eval(n.value) for n in ast.parse((D/'config.py').read_text()).body
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SPICE_CHECK' for t in n.targets))


def blocks(text):
    result={};current=None
    for line in text.splitlines():
        s=line.strip()
        if not s or s.startswith('*'):continue
        t=s.split()
        if t[0].lower()=='.subckt':
            current=t[1];result[current]={'ports':t[2:],'elements':[]}
        elif t[0].lower()=='.ends':current=None
        elif current:
            assert not s.startswith('+'),'Unexpected continuation in normalized circuit'
            result[current]['elements'].append(t)
    return result


def prepare():
    verify();st=settings();b=D/'build';raw=b/'core.extracted'
    assert sha(ROOT/st['gds'])==st['gds_sha256'] and raw.is_file()
    # Dependency helper import only; never invoke the convenience extractor
    # which omits --no-combine at this pinned commit.
    os.environ['APRTOOLS']=str(ROOT/'tools/APRtools');os.environ['TR1UM_PDK']=str(ROOT/'tools/TR-1um')
    os.chdir(D);sys.path.insert(0,str(ROOT/'tools/APRtools/apr'))
    import gen_chip_sim_ready as conv
    text=raw.read_text();before=blocks(text)
    converted,nvec,nocc=conv.debracket(text)
    converted,nesc=conv.sanitize(converted)
    converted,ndi=conv.fix_diodes(converted)
    converted,nmod=conv.rename_models(converted)
    # Keep every subcircuit: this core needs no empty-frame-cell pruning.
    after=blocks(converted);assert len(before)==len(after)
    def rename(token):return conv.sanitize(conv.debracket(token)[0])[0]
    mappings={}
    for name,c in before.items():
        other=after[rename(name)];assert len(c['elements'])==len(other['elements'])
        ids=set(c['ports']);component_ids=set()
        for old,new in zip(c['elements'],other['elements']):
            assert [rename(t) for t in old]==new,(name,old,new)
            component_ids.add(old[0]);ids.update(t for t in old[1:] if '=' not in t)
        for bag in (ids,component_ids):
            vals=[rename(x).lower() for x in bag];assert len(vals)==len(set(vals)),(name,'identifier collision')
        mappings[name]={p:rename(p) for p in ids}
    sim=b/'core_sim.spice';sim.write_text('* No-combine final GDS extraction; renamed identifiers only\n'+converted)
    # Map extracted top instances to original logical instances via independent
    # physical coordinates. Device parameters/connectivity are never rewritten.
    placement=json.loads((ROOT/'release/ishi_vga_grid_power_core/experiments/a_power_flex4/layout/placement.json').read_text())
    import klayout.db as db
    ly=db.Layout();ly.read(str(ROOT/st['gds']));top=ly.cell(st['top'])
    row_y=sorted({round(i.trans.disp.y*ly.dbu,3) for i in top.each_inst() if i.cell.name=='DFF'})
    assert len(row_y)==len(placement['rows'])
    logical={}
    for row,y in zip(placement['rows'],row_y):
        for c in row:
            if c['type']=='DFF':logical[(round(c['x'],3),y)]=c
    dff_ports=before['DFF']['ports'];mapping={};last=None
    for line in text.splitlines():
        m=re.match(r'\* cell instance (\S+) r0 \*1 ([\d.-]+),([\d.-]+)',line)
        if m:last=(m[1],round(float(m[2]),3),round(float(m[3]),3))
        t=line.split()
        if t and t[0].startswith('X') and t[-1]=='DFF':
            assert last and t[0]=='X'+last[0];item=logical[last[1:]]
            portnodes=dict(zip(dff_ports,t[1:-1]));assert len(portnodes)==len(dff_ports)
            for pin in ('Q','QB'):
                net=item['pins'].get(pin,{}).get('net')
                if net:mapping[net]={'node':rename(portnodes[pin]),'extracted_instance':rename(t[0]),
                                      'logical_instance':item['name'],'pin':pin,
                                      'qb_node':rename(portnodes['QB'])}
    states=[f'h[{i}]' for i in range(7)]+[f'v[{i}]' for i in range(10)]
    assert all(n in mapping for n in states)
    (b/'state_nodes.json').write_text(json.dumps(mapping,indent=2)+'\n')
    # Resolve model include through a single generated shim.
    models=ROOT/'tools/TR-1um/libs.tech/spice/models/ip62_models'
    (b/'models.spice').write_text(f".include '{models}'\n")
    def devices(name):
        n=0
        for t in after[name]['elements']:
            target=t[-1] if '=' not in t[-1] else None
            n+=devices(target) if target in after else 1
        return n
    inputs=[ROOT/st['gds'],raw,D/'config.py',Path(__file__),ROOT/'toolchain.lock.json',
            ROOT/'tools/APRtools/apr/klayout_extract.py',ROOT/'tools/APRtools/apr/gen_chip_sim_ready.py']
    inputs+=sorted(models.parent.glob('*'))
    (b/'extraction_manifest.json').write_text(json.dumps({'gds_sha256':st['gds_sha256'],
        'raw_sha256':sha(raw),'simulation_sha256':sha(sim),'top_ports':after[st['top']]['ports'],
        'hierarchical_device_count':devices(st['top']),'no_combine':True,
        'connection_and_device_parameter_tokens_preserved':True,'identifier_collisions':0,
        'interconnect_rc':False,'hashes':{str(p.relative_to(ROOT)):sha(p) for p in inputs if p.is_file()}},indent=2)+'\n')
    print('Prepared uncombined extraction',devices(st['top']),'devices',after[st['top']]['ports'])


def generate(name,h,v,ticks,natural=False):
    verify();st=settings();b=D/'build';d=b/name;d.mkdir(exist_ok=False)
    ports=blocks((b/'core_sim.spice').read_text())[st['top']]['ports']
    nodes=json.loads((b/'state_nodes.json').read_text())
    per=1e9/st['clock_hz'];delay=2000 if natural else 1000;end=delay+ticks*per+200
    lines=[f'* ISHI core {name}; no wire RC',".include '../models.spice'",".include '../core_sim.spice'",
           '.temp '+str(st['temperature_c']),'.options method=trap',
           ('VDD vdd 0 PWL(0 0 100n 0 1100n 5)' if natural else 'VDD vdd 0 5'),
           f'VCLK clk 0 PULSE(0 5 {delay}n 2n 2n {per/2-2:.12f}n {per:.12f}n)',
           'XDUT '+' '.join('0' if p.lower()=='vss' else p for p in ports)+' '+st['top']]
    for out in ['r','g','b','hsync','vsync']:lines.append(f'C_{out} {out} 0 {st["output_load_pf"]}p')
    if not natural:
        for axis,val,n in [('h',h,7),('v',v,10)]:
            for i in range(n):
                node=nodes[f'{axis}[{i}]'];voltage=5*((val>>i)&1)
                # Q is a buffered output, not the storage node. Initialize
                # the complementary QB feedback node too; release both at t=0.
                lines.append(f'.ic v(xdut.{node["node"]})={voltage} v(xdut.{node["qb_node"]})={5-voltage}')
    signals=['clk','r','g','b','hsync','vsync']+['xdut.'+nodes[f'{axis}[{i}]']['node'] for axis,n in [('h',7),('v',10)] for i in range(n)]
    lines += ['.save '+' '.join(f'v({n})' for n in signals),
              f'.tran 1n {end:.12f}n 0 {st["max_step_ns"]}n'+(' uic' if natural else ''),'.end','']
    (d/'tb.spice').write_text('\n'.join(lines))
    case=dict(name=name,h=h,v=v,ticks=ticks,natural=natural,
           delay_ns=delay,period_ns=per,signals=signals,voltage_v=5.0,temp_c=27,
           output_load_pf=st['output_load_pf'],max_step_ns=st['max_step_ns'])
    (d/'case.json').write_text(json.dumps(case,indent=2)+'\n')
    (d/'config.py').write_text('SPICE_CASE = '+repr(case)+'\n')
    print(d)


def run(name):
    verify();d=D/'build'/name;t=time.monotonic()
    with (d/'ngspice.log').open('w') as log:
        p=subprocess.run(['ngspice','-n','-b','-r','wave.raw','tb.spice'],cwd=d,stdout=log,stderr=subprocess.STDOUT)
    (d/'run.json').write_text(json.dumps({'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-t,
        'tb_sha256':sha(d/'tb.spice'),'raw_sha256':sha(d/'wave.raw') if (d/'wave.raw').exists() else None},indent=2)+'\n')
    assert p.returncode==0,(name,p.returncode)
    print(name,'finished',round(time.monotonic()-t,2),'seconds')


def check(name):
    d=D/'build'/name;c=json.loads((d/'case.json').read_text());run=json.loads((d/'run.json').read_text())
    assert run['exit_code']==0 and run['tb_sha256']==sha(d/'tb.spice') and run['raw_sha256']==sha(d/'wave.raw')
    binary=(d/'wave.raw').read_bytes();head,body=binary.split(b'Binary:\n',1);header=head.decode()
    assert 'Flags: real' in header and 'Plotname: Transient Analysis' in header
    n=int(re.search(r'No\. Variables:\s*(\d+)',header)[1]);points=int(re.search(r'No\. Points:\s*(\d+)',header)[1])
    names={m[2].lower():int(m[1]) for m in re.finditer(r'^\s*(\d+)\s+(\S+)\s+\S+\s*$',header.split('Variables:\n')[1],re.M)}
    data=np.frombuffer(body,dtype=np.float64).reshape(points,n);time_s=data[:,0]
    assert np.all(np.diff(time_s)>0) and np.isfinite(data).all()
    sampled_t=(c['delay_ns']+np.arange(c['ticks'])*c['period_ns']+150)*1e-9
    assert time_s[-1]>=sampled_t[-1], 'Incomplete transient time coverage'
    values=np.array([np.interp(sampled_t,time_s,data[:,names['v('+s.lower()+')']]) for s in c['signals']]).T
    logic=np.where(values<1.5,0,np.where(values>3.5,1,-1))
    states_h=logic[:,6:13]@2**np.arange(7);states_v=logic[:,13:23]@2**np.arange(10)
    observed=logic[:,1:6]@np.array([4,2,1,8,16])
    expected=np.array([int(x,16) for x in (ROOT/'designs/grid_power/tests/expected_frame.hex').read_text().split()])
    def next_state(h,v):return (71,500 if v==0 else (v+1)%1024) if h==100 else ((h-1)%128,v)
    state_reference=None
    if c.get('binary_state_reference'):
        state_reference=np.array([int(x,16) for x in (ROOT/'designs/grid_power/tests'/c['binary_state_reference']).read_text().split()])
        assert len(state_reference)==131072
    raster_checked=0
    start=32 if c['natural'] else 0;errors=[];records=[];checked=0;rgb_seen=set();last_h=c['h'];last_v=c['v']
    if c['natural']:last_h,last_v=int(states_h[start-1]),int(states_v[start-1])
    for i in range(start,c['ticks']):
        h,v=int(states_h[i]),int(states_v[i]);nh,nv=next_state(last_h,last_v)
        if (logic[i]<0).any():errors.append({'tick':i,'type':'undefined voltage at sample'})
        if (h,v)!=(nh,nv):errors.append({'tick':i,'type':'counter mismatch','actual':[h,v],'expected':[nh,nv]})
        x=(71-last_h)%128;y=(last_v-500)%1024
        in_raster=x<100 and y<525
        raster_checked+=int(in_raster)
        if in_raster or state_reference is not None:
            exp=int(state_reference[(last_v<<7)|last_h]) if state_reference is not None else int(expected[y*100+x])
            checked+=1;rgb_seen.add(exp&7)
            if int(observed[i])!=exp:errors.append({'tick':i,'type':'output mismatch','actual':int(observed[i]),'expected':exp,'screen_tick':[x,y]})
            records.append([i,int(h),int(v),int(observed[i]),exp])
        last_h,last_v=h,v
    assert checked>0
    out_vals=values[start:,1:6]
    valid_lo=out_vals[logic[start:,1:6]==0];valid_hi=out_vals[logic[start:,1:6]==1]
    delays=[]
    for i in range(max(start+1,1),c['ticks']):
        edge=(c['delay_ns']+i*c['period_ns']+1)*1e-9
        lo=max(0,int(np.searchsorted(time_s,edge))-1);hi=int(np.searchsorted(time_s,edge+149e-9))+1
        for j,signal in enumerate(['r','g','b','hsync','vsync'],1):
            if logic[i,j] not in (0,1) or logic[i-1,j] not in (0,1) or logic[i,j]==logic[i-1,j]:continue
            trace=data[lo:hi,names['v('+signal+')']];ts=time_s[lo:hi]
            crossings=np.flatnonzero(np.diff(trace>=2.5)==True)
            assert len(crossings)>0,(name,i,signal,'missing analog crossing')
            k=int(crossings[-1]);t50=ts[k]+(2.5-trace[k])/(trace[k+1]-trace[k])*(ts[k+1]-ts[k])
            delays.append({'tick':i,'signal':signal,'clk50_to_output50_ns':float((t50-edge)*1e9)})
    report={'status':'PASS' if not errors else 'FAIL','scope':c.get('view','full-core extracted transistor transient')+'; selected time window',
        'case':c,'counter_cycles_checked':c['ticks']-start,'output_cycles_checked':checked,
        'raster_cycles_checked':raster_checked, 'first_checked_state':[int(states_h[start-1]),int(states_v[start-1])] if start else [c['h'],c['v']],
        'signals_per_output_cycle':5,'rgb_values_seen':sorted(rgb_seen),'errors':errors,
        'max_low_sample_v':float(valid_lo.max()) if valid_lo.size else None,
        'min_high_sample_v':float(valid_hi.min()) if valid_hi.size else None,
        'elapsed_seconds':run['elapsed_seconds'],'sample_offset_ns':150,
        'output_transition_count':len(delays),'max_clk50_to_output50_ns':max((p['clk50_to_output50_ns'] for p in delays),default=None),
        'hashes':{str(p.relative_to(ROOT)):sha(p) for p in [d/'wave.raw',d/'tb.spice',d/'case.json',d/'ngspice.log',Path(__file__)]},
        'limitations':'1 pF assumed output load; typical 5 V/27C; no wire RC, PVT sweep, full-frame analog simulation or frame/pads.'}
    if state_reference is not None:
        ref=ROOT/'designs/grid_power/tests'/c['binary_state_reference'];report['hashes'][str(ref.relative_to(ROOT))]=sha(ref)
        report['limitations']+=' Power-up window checks binary progress only; normal frame acquisition is not observed.'
    (d/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (d/'samples.json').write_text(json.dumps({'columns':['tick','h_after','v_after','actual_rgbhs_vs','expected_rgbhs_vs'],'rows':records},indent=2)+'\n')
    print(name,report['status'],'checked',checked,'ticks','errors',errors[:5],flush=True)
    assert not errors


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--design-root',type=Path,default=D);ap.add_argument('action',choices=['prepare','generate','run','check']);ap.add_argument('name',nargs='?')
    ap.add_argument('--h',type=int,default=71);ap.add_argument('--v',type=int,default=672)
    ap.add_argument('--ticks',type=int,default=8);ap.add_argument('--natural',action='store_true');a=ap.parse_args()
    D=a.design_root.resolve()
    assert D.is_relative_to(ROOT)
    if a.action=='prepare':prepare()
    elif a.action=='generate':generate(a.name,a.h,a.v,a.ticks,a.natural)
    elif a.action=='run':run(a.name)
    else:check(a.name)
