#!/usr/bin/env python3
"""Search bounded pairs/triples of neutral top-level routing-via removals.

The source is the frozen via_pruned GDS. Only explicitly configured via_1
locations are removed; every candidate starts from the current accepted copy.
Connectivity, process rules, and DRC marker parsing reuse prune_route_vias.py.
"""
from __future__ import annotations
import argparse, ast, hashlib, itertools, json, subprocess, sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DESIGN=ROOT/'experiments/via_groups'
sys.path.insert(0,str(ROOT/'scripts'))
import prune_route_vias as prune
from check_toolchain import verify
import rules, lef_parser, klayout.db as db

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_settings():
    for n in ast.parse((DESIGN/'config.py').read_text()).body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VIA_GROUPS' for t in n.targets):
            return ast.literal_eval(n.value)
    raise RuntimeError('config.py must define VIA_GROUPS')
S=load_settings()
def path(key):
    p=Path(S[key]); return p if p.is_absolute() else ROOT/p
def exact_vias(top,ly,xy):
    x,y=xy; tol=S['coordinate_tolerance_um']; found=[]
    for inst in list(top.each_inst()):
        if not inst.cell.name.startswith('via_1'): continue
        xx=inst.trans.disp.x*ly.dbu; yy=inst.trans.disp.y*ly.dbu
        if abs(xx-x)<=tol and abs(yy-y)<=tol: found.append(inst)
    return found
def del_at(top,ly,xy):
    refs=exact_vias(top,ly,xy)
    if not refs: raise RuntimeError(f'configured via location absent: {xy}')
    removed=[]
    for inst in refs:
        removed.append({'center_um':[round(inst.trans.disp.x*ly.dbu,4),round(inst.trans.disp.y*ly.dbu,4)],'cell':inst.cell.name,'cell_inst':inst.cell_inst})
        inst.delete()
    return removed
def restore(top,removed):
    for x in removed: top.insert(x['cell_inst'])
def pin_layers(placement_path):
    lef=lef_parser.parse_lef(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef')
    place=json.loads(placement_path.read_text()); result={}
    for row in place['rows']:
        for inst in row:
            cell=lef[inst['type']]
            for pin,entry in cell['pins'].items():
                metals=[{'METAL1':'M1','METAL2':'M2'}[r[0]] for r in entry['rects'] if r[0] in ('METAL1','METAL2')]
                if metals: result[(inst['name'],pin)]=metals[0]
    return result
def state_serial(st):
    return {'pair_count':len(st['pairs']),'pairs':sorted(map(list,st['pairs'])),'groups':st['groups'],
            'opens':st['opens'],'missing':st['missing'],'power_component_counts':st['power_component_counts'],
            'rail_signal_nets':st['rail_signal_nets']}
def run_drc(gds,report,log):
    cmd=[sys.executable,str(ROOT/'scripts/run_apr.py'),'--design-root',str(DESIGN),
         'apr/drc_pdk.py',str(gds),'ishi_vga_core','-r',str(report)]
    proc=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    log.write_text(proc.stdout+proc.stderr)
    markers=prune.markers(report) if report.exists() else None
    return proc.returncode,markers
def main():
    verify(); build=DESIGN/'build';build.mkdir(exist_ok=True)
    source=path('source_gds'); expected=S['source_sha256']
    if sha(source)!=expected: raise RuntimeError('frozen source GDS hash mismatch')
    pins=json.loads(path('actual_pins').read_text()); shapes=json.loads(path('shapes').read_text())
    pinlayer=pin_layers(path('placement'))
    if len(pinlayer)<987: raise RuntimeError(f'incomplete LEF pin layer map: {len(pinlayer)}')
    drawing_ref=path('drawing_baseline'); base_markers=prune.markers(drawing_ref)
    ly=db.Layout();ly.read(str(source));top=ly.cell(S['top'])
    source_state=prune.connectivity(ly,top,pins,pinlayer)
    if len(source_state['pairs'])!=50 or source_state['opens'] or source_state['missing']:
        raise RuntimeError('frozen via-pruned source does not match expected 50-pair clean-pin baseline')
    current=source_state
    groups=[];trials=[];trial_count=0; accepted_count=0
    # Apply the known local repair first and gate it like every later group.
    removed=[]
    for pt in S['known_initial_group']: removed.extend(del_at(top,ly,pt))
    seed=prune.connectivity(ly,top,pins,pinlayer)
    seed_ok=(not seed['opens'] and not seed['missing'] and seed['pairs']<current['pairs'] and
             seed['power_component_counts']==source_state['power_component_counts'] and
             seed['rail_signal_nets']==source_state['rail_signal_nets'])
    seed_dir=build/'seed_known_048';seed_dir.mkdir(exist_ok=True)
    seed_gds=seed_dir/'candidate.gds';ly.write(str(seed_gds))
    rc,seed_markers=run_drc(seed_gds,seed_dir/'drawing.lyrdb',seed_dir/'drc.log')
    seed_ok=seed_ok and seed_markers is not None and not (seed_markers-base_markers)
    seed_record={'known_group':S['known_initial_group'],'removed_vias':[{'center_um':v['center_um'],'cell':v['cell']} for v in removed],
                 'connectivity':state_serial(seed),'drc_exit':rc,'new_drc_markers':None if seed_markers is None else len(seed_markers-base_markers),
                 'accepted':seed_ok,'candidate_gds_sha256':sha(seed_gds)}
    (seed_dir/'result.json').write_text(json.dumps(seed_record,indent=2)+'\n')
    if not seed_ok:
        restore(top,removed)
        raise RuntimeError('known _048_/h[0] pair failed acceptance gate')
    current=seed;groups.append(seed_record);accepted_count+=1
    with (build/'search.log').open('w') as log:
        log.write(f"source={S['source_gds']} sha256={expected} baseline_pairs=50\n")
        log.write(f"known pair accepted: pairs={len(current['pairs'])}, removed={sorted(source_state['pairs']-current['pairs'])}\n")
        log.flush()
        for pass_no in range(S['max_passes']):
            neutral=[]
            for item in S['neutral_candidates']:
                xy=item['xy_um']; refs=exact_vias(top,ly,xy)
                if not refs: continue
                gone=del_at(top,ly,xy); one=prune.connectivity(ly,top,pins,pinlayer)
                same=(one['pairs']==current['pairs'] and not one['opens'] and not one['missing'] and
                      one['power_component_counts']==source_state['power_component_counts'] and
                      one['rail_signal_nets']==source_state['rail_signal_nets'])
                restore(top,gone)
                if same: neutral.append(item)
            log.write(f'pass={pass_no} neutral_single_locations={len(neutral)}\n');log.flush()
            accepted_this_pass=False
            for size in S['group_sizes']:
                for combo in itertools.combinations(neutral,size):
                    if trial_count>=S['max_trials']: break
                    trial_count+=1; gone=[]
                    try:
                        for item in combo: gone.extend(del_at(top,ly,item['xy_um']))
                        candidate=prune.connectivity(ly,top,pins,pinlayer)
                        record={'trial':trial_count,'pass':pass_no,'group_size':size,
                                'xy_um':[x['xy_um'] for x in combo],
                                'removed_vias':[{'center_um':v['center_um'],'cell':v['cell']} for v in gone],
                                'before_pair_count':len(current['pairs']),'pair_count':len(candidate['pairs']),
                                'removed_pairs':sorted(map(list,current['pairs']-candidate['pairs'])),
                                'added_pairs':sorted(map(list,candidate['pairs']-current['pairs'])),
                                'opens':candidate['opens'],'missing':candidate['missing'],
                                'power_component_counts':candidate['power_component_counts'],
                                'rail_signal_nets':candidate['rail_signal_nets'],'accepted':False}
                        improves=(not candidate['opens'] and not candidate['missing'] and
                                  candidate['pairs']<current['pairs'] and
                                  candidate['power_component_counts']==source_state['power_component_counts'] and
                                  candidate['rail_signal_nets']==source_state['rail_signal_nets'])
                        if improves:
                            folder=build/f'group_{len(groups):02d}_trial_{trial_count:04d}'
                            folder.mkdir(exist_ok=False);gds=folder/'candidate.gds';ly.write(str(gds))
                            rc,mset=run_drc(gds,folder/'drawing.lyrdb',folder/'drc.log')
                            record.update({'candidate_gds':str(gds.relative_to(ROOT)),'candidate_gds_sha256':sha(gds),
                                           'drc_exit':rc,'new_drc_markers':None if mset is None else len(mset-base_markers)})
                            if mset is not None and not (mset-base_markers):
                                record['accepted']=True;current=candidate;groups.append(record);accepted_count+=1
                                accepted_this_pass=True
                                log.write(f"ACCEPT trial={trial_count} group={record['xy_um']} pairs={len(current['pairs'])} resolved={record['removed_pairs']}\n")
                            else:
                                restore(top,gone)
                        else: restore(top,gone)
                        trials.append(record);log.write(json.dumps(record,sort_keys=True)+'\n');log.flush()
                    except Exception:
                        restore(top,gone);raise
                    if accepted_this_pass: break
                if accepted_this_pass or trial_count>=S['max_trials']: break
            if not accepted_this_pass or trial_count>=S['max_trials']: break
    final=build/'via_groups_pruned.gds';ly.write(str(final))
    # Full independent pin-shape/M1/M2/V1/GC/CO audit for the final checkpoint.
    audit=build/'final_audit';audit.mkdir(exist_ok=True)
    cmd=[sys.executable,str(ROOT/'scripts/routing_diagnostics.py'),'--gds',str(final),
         '--pins',str(path('actual_pins')),'--shapes',str(path('shapes')),
         '--placement',str(path('placement')),'--out',str(audit),'--poly']
    proc=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    (build/'final_pin_shape_audit.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode: raise RuntimeError('final routing_diagnostics failed')
    # Official drawing and mask DRC on the final GDS through the locked wrapper.
    draw=build/'final_drawing.lyrdb'; drawlog=build/'final_drawing_drc.log'
    drawrc,_=run_drc(final,draw,drawlog)
    mask=build/'via_groups_pruned_mdp.lyrdb'; maskgds=build/'via_groups_pruned_mask.gds'
    maskcmd=[sys.executable,str(ROOT/'scripts/run_apr.py'),'--design-root',str(DESIGN),
       'apr/drc_pdk.py',str(final),'ishi_vga_core','-r',str(mask),'--mdp','--mdp-gds',str(maskgds)]
    maskproc=subprocess.run(maskcmd,cwd=ROOT,text=True,capture_output=True)
    (build/'final_mask_drc.log').write_text(maskproc.stdout+maskproc.stderr)
    final_actual=json.loads((audit/'metal_connectivity.json').read_text())
    manifest={'source_gds':str(source.relative_to(ROOT)),'source_sha256':sha(source),
      'generator_sha256':sha(Path(__file__)),'config_sha256':sha(DESIGN/'config.py'),
      'toolchain_lock_sha256':sha(ROOT/'toolchain.lock.json'),'source_state':state_serial(source_state),
      'accepted_groups':groups,'group_trials':trials,'trial_count':trial_count,
      'final_state':state_serial(current),'output_gds':str(final.relative_to(ROOT)),
      'output_gds_sha256':sha(final),'final_actual_pin_audit':{
        'report':'experiments/via_groups/build/final_audit/metal_connectivity.json',
        'sha256':sha(audit/'metal_connectivity.json'),'actual_signal_pins':final_actual['placement_signal_pin_count'],
        'missing_actual_pins':final_actual['missing_actual_pin_count'],'opens':final_actual['open_net_count'],
        'short_components':final_actual['actual_short_component_count'],'short_pairs':final_actual['actual_short_net_pair_count']},
      'final_drawing_drc':{'exit':drawrc,'report_sha256':sha(draw) if draw.exists() else None,
        'new_markers_vs_source':len(prune.markers(draw)-base_markers) if draw.exists() else None},
      'final_mask_drc':{'exit':maskproc.returncode,'report_sha256':sha(mask) if mask.exists() else None,
        'mask_gds_sha256':sha(maskgds) if maskgds.exists() else None},
      'settings':S,'limitations':'No routing geometry was added. Official DRC nonzero is expected when inherited markers remain; marker-set changes are reported separately.'}
    (build/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if sha(source)!=expected: raise RuntimeError('immutable frozen source changed')
    print(f"Finished {trial_count} combo trials; {accepted_count} accepted groups; pairs {len(source_state['pairs'])}->{len(current['pairs'])}; final {final}",flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    main()
