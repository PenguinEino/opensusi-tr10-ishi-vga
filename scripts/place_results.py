#!/usr/bin/env python3
"""Collect dimensions and diagnostic outcomes without treating return code as signoff."""
import json,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
rows=[]
for d in sorted((root/'experiments').glob('place_*')):
    if not d.is_dir():continue
    manifest=json.loads((d/'source_manifest.json').read_text())
    row={'name':d.name,**manifest}
    place=d/'layout/step1/place_step1_rows.json'
    if place.exists():
        p=json.loads(place.read_text());row.update(cut=p.get('cut'),crossings=p.get('channel_crossings'))
    for name in ['place','verify_placement','route_step6','diagnostic_compaction']:
        p=d/'build'/(name+'.log')
        if not p.exists():continue
        s=p.read_text()
        m=re.search('RETURN_CODE=(\\d+)',s);row[name+'_return']=int(m[1]) if m else None
        if name=='route_step6':
            m=re.search('(\\d+) PROBLEM\\(S\\) FOUND',s)
            row['connectivity_problems']=int(m[1]) if m else (0 if 'No connectivity problems' in s else None)
            row['drc_diagnostic']=[line for line in s.splitlines() if 'viol' in line]
        if name=='diagnostic_compaction':
            m=re.search(r'コア高 実測 ([\d.]+) um.*bbox ([\d.-]+),([\d.-]+) - ([\d.-]+),([\d.-]+)',s)
            if m:row.update(width_um=round(float(m[4])-float(m[2]),3),height_um=float(m[1]))
    k=d/'routing_knobs.json'
    if k.exists():row['routing_knobs']=json.loads(k.read_text())
    rows.append(row)
(root/'experiments/place_results.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
for r in rows:
    print(r['name'],r.get('cut'),r.get('width_um'),r.get('height_um'),r.get('connectivity_problems'),r.get('route_step6_return'))
