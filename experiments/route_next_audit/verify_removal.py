#!/usr/bin/env python3
"""Verify exact two-via deletion connectivity and official drawing/mask DRC deltas."""
import hashlib, json, xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXP=ROOT/'experiments'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pairs(path):
 d=json.loads(Path(path).read_text()); out=set()
 for c in d['actual_short_components']:
  ns=sorted(set(c['nets']))
  for i,a in enumerate(ns):
   for b in ns[i+1:]: out.add((a,b))
 return d,out
def markers(path):
 root=ET.parse(path).getroot(); out=[]
 for it in root.findall('.//item'):
  cat=(it.findtext('category') or '').strip()
  vals=tuple(sorted((v.text or '').strip() for v in it.findall('values/value') if (v.text or '').strip()))
  if not vals: raise AssertionError(f'empty marker values: {path} {cat}')
  out.append((cat,vals))
 return sorted(out)
baseline=EXP/'routed_checkpoint/build/audit/metal_connectivity.json'
candidate=EXP/'route_next_audit/build/audit/metal_connectivity.json'
bd,bp=pairs(baseline); cd,cp=pairs(candidate)
assert bd['open_net_count']==cd['open_net_count']==0
assert bd['missing_actual_pin_count']==cd['missing_actual_pin_count']==0
assert bd['actual_pin_shapes_labeled']==cd['actual_pin_shapes_labeled']==987
assert bd['placement_instances_matched_to_actual_gds']==cd['placement_instances_matched_to_actual_gds']==421
assert bp-cp=={('_034_','_052_'),('_104_','_139_')}, sorted(bp-cp)
assert cp-bp==set(), sorted(cp-bp)
assert len(bp)==143 and len(cp)==141
reports={
 'drawing_baseline':EXP/'routed_checkpoint/build/routed_checkpoint.drc.lyrdb',
 'drawing_candidate':EXP/'route_next_audit/build/candidate_no_stale_vias.drc.lyrdb',
 'mask_baseline':EXP/'routed_checkpoint/build/routed_checkpoint_mdp_drawing.drc.lyrdb',
 'mask_candidate':EXP/'route_next_audit/build/candidate_no_stale_vias_mdp_drawing.drc.lyrdb',
}
mr={k:markers(v) for k,v in reports.items()}
for axis in ('drawing','mask'):
 base=mr[axis+'_baseline']; cand=mr[axis+'_candidate']
 assert len(base)==2 and len(cand)==2, (axis,len(base),len(cand))
 assert set(cand)==set(base), (axis, set(cand)-set(base), set(base)-set(cand))
# Ensure the two remaining locations are the known BUFTH markers, not the removed DFFRB marker.
for axis in ('drawing','mask'):
 vals=[v for cat,vs in mr[axis+'_candidate'] for v in vs]
 joined=' '.join(vals)
 assert '1009.3,1626.1' in joined and '1592.5,1626.1' in joined
 out={
  'status':'verified',
  'input_gds_sha256':sha(EXP/'routed_checkpoint/build/routed_checkpoint.gds'),
  'candidate_gds_sha256':sha(EXP/'route_next_audit/build/candidate_no_stale_vias.gds'),
  'remove_script_sha256':sha(EXP/'route_next_audit/remove_stale_vias.py'),
  'verify_script_sha256':sha(Path(__file__)),
  'config_sha256':sha(EXP/'route_next_audit/config.py'),
  'routing_diagnostics_sha256':sha(ROOT/'scripts/routing_diagnostics.py'),
  'connectivity':{'actual_pins':987,'matched_instances':421,'opens_before':bd['open_net_count'],'opens_after':cd['open_net_count'],'short_components_before':bd['actual_short_component_count'],'short_components_after':cd['actual_short_component_count'],'short_pairs_before':len(bp),'short_pairs_after':len(cp),'resolved_pairs':sorted([list(x) for x in bp-cp]),'new_pairs':sorted([list(x) for x in cp-bp])},
  'official_drc':{},
 }
 for name,p in reports.items(): out['official_drc'][name]={'report_sha256':sha(p),'item_count':len(mr[name]),'markers':[{'category':c,'values':list(v)} for c,v in mr[name]]}
 Path(EXP/'route_next_audit/build/verification.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps(out['connectivity'],indent=2))
 print('Drawing and mask marker sets: exactly identical marker sets; all reports contain values.')
