#!/usr/bin/env python3
"""Verify and record the composed constant-tie metal-repair checkpoint."""
import collections, hashlib, itertools, json, runpy, sys
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pairs(data):return {tuple(sorted(p)) for s in data['actual_short_components'] for p in itertools.combinations(s['nets'],2)}
def items(path):
    root=ET.parse(path).getroot(); out=[]
    for it in root.findall('./items/item'):
        values=tuple(v.text or '' for v in it.findall('./values/value'))
        if not values or any(not v for v in values):raise RuntimeError(f'DRC item has no geometry values: {path}')
        out.append({'category':(it.findtext('category') or '').strip().strip("'"),'values':values})
    return out
def main():
    design=ROOT/'experiments/routed_checkpoint';sys.path[:0]=[str(design),str(ROOT/'tools/APRtools/apr')]
    st=runpy.run_path(str(design/'config.py'))['CONSTANT_TIE_INTEGRATION'];b=design/'build'
    manifest=json.loads((b/'manifest.json').read_text())
    patch_path=ROOT/st['patch_json'];source_path=ROOT/st['source_gds'];config_path=design/'config.py'
    output_path=b/'routed_checkpoint.gds'
    for field,path in [('source_gds_sha256',source_path),('patch_sha256',patch_path),
                       ('config_sha256',config_path),('output_gds_sha256',output_path),
                       ('actual_pin_map_sha256',ROOT/st['actual_pins']),
                       ('routing_shapes_sha256',ROOT/st['routing_shapes'])]:
        if manifest.get(field)!=sha(path):raise RuntimeError(f'generation manifest is stale: {field}')
    if manifest.get('generator_sha256')!=sha(ROOT/'scripts/apply_constant_tie_checkpoint.py'):
        raise RuntimeError('generation manifest does not match current composition script')
    baseline_path=ROOT/'experiments/metal_repair/build/junction_y7296/routing_audit/metal_connectivity.json'
    candidate_path=b/'audit/metal_connectivity.json'
    baseline=json.loads(baseline_path.read_text());candidate=json.loads(candidate_path.read_text())
    oldpairs,newpairs=pairs(baseline),pairs(candidate)
    if candidate['placement_instances_matched_to_actual_gds']!=421 or candidate['placement_instances_missing_from_gds']:
        raise RuntimeError('GDS placed-instance matching incomplete')
    if candidate['placement_signal_pin_count']!=987 or candidate['actual_pin_shapes_labeled']!=987 or candidate['missing_actual_pin_count']:
        raise RuntimeError('actual signal-pin coverage incomplete')
    if candidate['open_net_count']!=0 or len(oldpairs)!=143 or oldpairs!=newpairs:
        raise RuntimeError('candidate connectivity differs from accepted metal checkpoint')
    if manifest['after_rail_signal_nets']!={'vss':[],'vdd':["1'h1"]}:
        raise RuntimeError(f'rail-probe output unexpected: {manifest["after_rail_signal_nets"]}')
    draw_report=b/'routed_checkpoint.drc.lyrdb';mask_report=b/'routed_checkpoint_mdp.lyrdb'
    if not draw_report.is_file() or not mask_report.is_file():raise RuntimeError('official DRC report missing')
    drawing=items(draw_report);mask=items(mask_report)
    if len(drawing)!=2 or {x['category'] for x in drawing}!={'GC.ANT:GC must electrically connect to Substrate (or text if not chip level)'}:
        raise RuntimeError(f'unexpected official drawing DRC items: {drawing}')
    if len(mask)!=2 or {x['category'] for x in mask}!={'WAR06: Floating SG Detected'}:
        raise RuntimeError(f'unexpected official mask DRC items: {mask}')
    baseline_draw=items(ROOT/'experiments/routing_audit/postrepair_baseline.lyrdb')
    baseline_mask=items(ROOT/'experiments/phys_desc5/build/postrepair_compacted_mdp.lyrdb')
    if not {(x['category'],x['values']) for x in drawing}<={(x['category'],x['values']) for x in baseline_draw}:
        raise RuntimeError('candidate introduced a drawing DRC marker')
    if not {(x['category'],x['values']) for x in mask}<={(x['category'],x['values']) for x in baseline_mask}:
        raise RuntimeError('candidate introduced a mask DRC marker')
    source=source_path;patch=patch_path;config=config_path
    report={'status':'PASS','candidate_gds_sha256':sha(b/'routed_checkpoint.gds'),
      'source_gds_sha256':sha(source),'tie_patch_sha256':sha(patch),
      'generator_sha256':sha(ROOT/'scripts/apply_constant_tie_checkpoint.py'),
      'verifier_sha256':sha(Path(__file__)),'config_sha256':sha(config),
      'routing_diagnostics_sha256':sha(ROOT/'scripts/routing_diagnostics.py'),
      'actual_pin_map_sha256':sha(ROOT/st['actual_pins']),
      'routing_shapes_sha256':sha(ROOT/st['routing_shapes']),
      'toolchain_lock_sha256':sha(ROOT/'toolchain.lock.json'),
      'baseline_connectivity_report_sha256':sha(baseline_path),
      'candidate_connectivity_report_sha256':sha(candidate_path),
      'actual_signal_pins':candidate['actual_pin_shapes_labeled'],
      'missing_actual_pins':candidate['missing_actual_pin_count'],
      'opens':candidate['open_net_count'],'short_components':candidate['actual_short_component_count'],
      'short_net_pairs':len(newpairs),'new_short_pairs':sorted(map(list,newpairs-oldpairs)),
      'resolved_short_pairs':sorted(map(list,oldpairs-newpairs)),
      'rail_signals_after_tie':manifest['after_rail_signal_nets'],
      'official_drawing_drc':{'item_count':len(drawing),'categories':dict(collections.Counter(x['category'] for x in drawing)),
        'markers':drawing,'baseline_markers':baseline_draw,
        'report_sha256':sha(draw_report),'console_log_sha256':sha(b/'drawing_drc.log')},
      'official_mask_drc':{'item_count':len(mask),'categories':dict(collections.Counter(x['category'] for x in mask)),
        'markers':mask,'baseline_markers':baseline_mask,
        'report_sha256':sha(mask_report),'console_log_sha256':sha(b/'mask_drc.log'),
        'mask_gds_sha256':sha(b/'routed_checkpoint_mdp.gds')},
      'baseline_drawing_items':len(baseline_draw),'baseline_mask_items':len(baseline_mask),
      'limitations':'Two inherited BUFTH GC.ANT and corresponding WAR06 remain; unrelated short components remain.'}
    (b/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    manifest['status']='VERIFIED; no added opens, short pairs, or drawing/mask DRC markers'
    manifest['verification_json']='experiments/routed_checkpoint/build/verification.json'
    manifest['verification_json_sha256']=sha(b/'verification.json')
    manifest['routing_diagnostics_sha256']=report['routing_diagnostics_sha256']
    manifest['limitations']=report['limitations']
    (b/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
