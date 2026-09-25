#!/usr/bin/env python3
"""Independent read-only review of route-via pruning outputs."""
import hashlib,json,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
import klayout.db as db
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'experiments'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pairset(p):
 d=json.loads(Path(p).read_text());s=set()
 for c in d['actual_short_components']:
  ns=sorted(set(c['nets']))
  for i,a in enumerate(ns):
   for b in ns[i+1:]:s.add((a,b))
 return d,s
def markers(p):
 out=[]
 for i in ET.parse(p).getroot().iter('item'):
  c=(i.findtext('category') or '').strip();v=tuple(sorted(x.text.strip() for x in i.findall('values/value') if x.text and x.text.strip()))
  assert v,(p,c)
  out.append((c,v))
 return sorted(out)
def instances(p):
 l=db.Layout();l.read(str(p));t=l.cell('ishi_vga_core');assert t
 return Counter((i.cell.name,i.trans.to_s()) for i in t.each_inst()), list(t.bbox().to_s().split())
source=E/'routed_checkpoint/build/routed_checkpoint.gds';out=E/'via_prune/build/via_pruned.gds';manifestp=E/'via_prune/build/manifest.json'
man=json.loads(manifestp.read_text());manifest_pairs={tuple(x) for x in man['after']['pairs']}
base, bp=pairset(E/'routed_checkpoint/build/audit/metal_connectivity.json')
after, ap=pairset(E/'via_prune/build/audit/metal_connectivity.json')
assert bp=={tuple(x) for x in man['before']['pairs']}
assert ap==manifest_pairs
assert len(bp)==143 and len(ap)==50 and ap<bp and not (ap-bp)
assert base['open_net_count']==after['open_net_count']==0
assert base['missing_actual_pin_count']==after['missing_actual_pin_count']==0
assert base['actual_pin_shapes_labeled']==after['actual_pin_shapes_labeled']==987
assert base['placement_instances_matched_to_actual_gds']==after['placement_instances_matched_to_actual_gds']==421
assert base['placement_instances_missing_from_gds']==after['placement_instances_missing_from_gds']==[]
assert man['source_sha256']==sha(source) and man['output_sha256']==sha(out)
assert man['generator_sha256']==sha(ROOT/'scripts/prune_route_vias.py')
assert man['config_sha256']==sha(E/'via_prune/config.py')
si,sbbox=instances(source);oi,obbox=instances(out); removed=si-oi; added=oi-si
assert not added and len(removed)==17 and all(k[0].startswith('via_1') for k in removed)
assert len(man['accepted'])==17
manifest_locs=Counter(('via_1$2',f"r0 {round(a*1000)},{round(b*1000)}") for a,b in (r['xy_um'] for r in man['accepted']))
assert removed==manifest_locs,(removed,manifest_locs)
assert sbbox==obbox
reports={
 'drawing_baseline':E/'routed_checkpoint/build/routed_checkpoint.drc.lyrdb',
 'drawing_candidate':E/'via_prune/build/drawing.lyrdb',
 'mask_baseline':E/'routed_checkpoint/build/routed_checkpoint_mdp.lyrdb',
 'mask_candidate':E/'via_prune/build/via_pruned_mdp.lyrdb',
}
mr={k:markers(v) for k,v in reports.items()}
assert len(mr['drawing_baseline'])==len(mr['drawing_candidate'])==2
assert len(mr['mask_baseline'])==len(mr['mask_candidate'])==2
assert mr['drawing_baseline']==mr['drawing_candidate']
assert mr['mask_baseline']==mr['mask_candidate']
# Every report item is one of the expected two BUFTH floating substrate markers.
for key in reports:
 s=' '.join(v for _,vals in mr[key] for v in vals)
 assert '1009.3,1626.1' in s and '1592.5,1626.1' in s
result={
 'status':'independent review passed',
 'source_sha256':sha(source),'output_sha256':sha(out),'manifest_sha256':sha(manifestp),
 'generator_sha256':sha(ROOT/'scripts/prune_route_vias.py'),'config_sha256':sha(E/'via_prune/config.py'),
 'routing_diagnostics_sha256':sha(ROOT/'scripts/routing_diagnostics.py'),
 'connectivity':{'mode':after['mode'],'instances':after['placement_instances_matched_to_actual_gds'],'actual_signal_pins':after['actual_pin_shapes_labeled'],'missing_pins':after['missing_actual_pin_count'],'opens_before':base['open_net_count'],'opens_after':after['open_net_count'],'short_components_before':base['actual_short_component_count'],'short_components_after':after['actual_short_component_count'],'pairs_before':len(bp),'pairs_after':len(ap),'resolved_pairs':sorted(map(list,bp-ap)),'new_pairs':sorted(map(list,ap-bp)),'independent_pairset_matches_manifest':True},
 'gds_diff':{'top_instances_before':sum(si.values()),'top_instances_after':sum(oi.values()),'removed_instances':len(removed),'added_instances':len(added),'removed_refs':[{'cell':n,'transform':t} for n,t in sorted(removed)],'bbox_unchanged':sbbox==obbox},
 'drc':{k:{'sha256':sha(p),'item_count':len(mr[k]),'markers':[{'category':c,'values':list(v)} for c,v in mr[k]]} for k,p in reports.items()},
}
(E/'via_prune/build/verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['connectivity'],indent=2));print('Only 17 listed top-level vias removed; no additions; drawing/mask markers exactly match baseline.')
