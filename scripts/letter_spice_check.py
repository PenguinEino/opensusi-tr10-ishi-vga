#!/usr/bin/env python3
"""Fresh no-combine extraction and selected transistor transients of the letter core."""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import numpy as np
from check_toolchain import ROOT, verify
from power_spice_check import blocks, sha


def settings(design):
    return next(ast.literal_eval(n.value) for n in ast.parse((design/'config.py').read_text()).body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SPICE_CHECK' for t in n.targets))


def prepare(design, cfg):
    build = design/'build'
    build.mkdir(exist_ok=True)
    assert sha(ROOT/cfg['gds']) == cfg['gds_sha256']
    with (build/'extract.log').open('w') as log:
        subprocess.run([sys.executable, str(ROOT/'scripts/run_apr.py'), '--design-root', str(design),
                        'apr/klayout_extract.py', str(ROOT/cfg['gds']), cfg['top'], '--no-combine',
                        '-o', str(build/'core.extracted')], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    raw = build/'core.extracted'
    assert sha(raw) == sha(ROOT/cfg['extracted'])
    # Import only the pinned identifier helpers, never its convenience extractor.
    os.environ['APRTOOLS'] = str(ROOT/'tools/APRtools')
    os.environ['TR1UM_PDK'] = str(ROOT/'tools/TR-1um')
    os.chdir(design)
    sys.path.insert(0, str(ROOT/'tools/APRtools/apr'))
    import gen_chip_sim_ready as conv
    text = raw.read_text()
    before = blocks(text)
    converted = conv.debracket(text)[0]
    converted = conv.sanitize(converted)[0]
    converted = conv.fix_diodes(converted)[0]
    converted = conv.rename_models(converted)[0]
    after = blocks(converted)
    rename = lambda token: conv.sanitize(conv.debracket(token)[0])[0]
    assert len(before) == len(after)
    for name, cell in before.items():
        other = after[rename(name)]
        assert [rename(p) for p in cell['ports']] == other['ports']
        assert len(cell['elements']) == len(other['elements'])
        ids, element_ids = set(cell['ports']), set()
        for old, new in zip(cell['elements'], other['elements']):
            assert [rename(t) for t in old] == new, (name, old, new)
            element_ids.add(old[0])
            ids.update(t for t in old[1:] if '=' not in t)
        for bag in [ids, element_ids]:
            names = [rename(t).lower() for t in bag]
            assert len(names) == len(set(names)), 'Identifier collision'
    (build/'core_sim.spice').write_text('* Fresh no-combine GDS extraction; identifiers renamed only\n'+converted)
    import klayout.db as db
    ly = db.Layout(); ly.read(str(ROOT/cfg['gds'])); top = ly.cell(cfg['top'])
    ys = sorted({round(i.trans.disp.y*ly.dbu, 3) for i in top.each_inst() if i.cell.name == 'DFF'})
    placement = json.loads((ROOT/cfg['placement']).read_text())
    assert len(ys) == len(placement['rows'])
    logical = {(round(c['x'], 3), y): c for row, y in zip(placement['rows'], ys) for c in row if c['type'] == 'DFF'}
    nodes, last = {}, None
    for line in text.splitlines():
        match = re.match(r'\* cell instance (\S+) r0 \*1 ([\d.-]+),([\d.-]+)', line)
        if match: last = (match[1], round(float(match[2]), 3), round(float(match[3]), 3))
        tokens = line.split()
        if tokens and tokens[0].startswith('X') and tokens[-1] == 'DFF':
            assert last and tokens[0] == 'X'+last[0]
            item = logical[last[1:]]
            ports = dict(zip(before['DFF']['ports'], tokens[1:-1]))
            assert len(ports) == len(before['DFF']['ports'])
            key = item['pins']['Q']['net']
            assert key not in nodes
            nodes[key] = {'node': rename(ports['Q']), 'qb_node': rename(ports['QB']),
                          'logical_instance': item['name'], 'extracted_instance': rename(tokens[0])}
    assert len(nodes) == 29
    (build/'state_nodes.json').write_text(json.dumps(nodes, indent=2)+'\n')
    models = ROOT/'tools/TR-1um/libs.tech/spice/models'
    (build/'models').mkdir(exist_ok=True)
    for p in sorted(models.iterdir()):
        if p.is_file(): shutil.copyfile(p, build/'models'/p.name)
    def count(name):
        return sum(count(t[-1]) if t[-1] in after else 1 for t in after[name]['elements'])
    paths = [ROOT/cfg['gds'], raw, ROOT/cfg['placement'], design/'config.py', Path(__file__), ROOT/'toolchain.lock.json',
             ROOT/'scripts/power_spice_check.py', ROOT/'tools/APRtools/apr/klayout_extract.py',
             ROOT/'tools/APRtools/apr/gen_chip_sim_ready.py', *sorted(models.iterdir())]
    report = {'gds_sha256': cfg['gds_sha256'], 'raw_sha256': sha(raw), 'simulation_sha256': sha(build/'core_sim.spice'),
              'hierarchical_device_count': count(cfg['top']), 'no_combine': True,
              'connection_and_device_parameter_tokens_preserved': True, 'identifier_collisions': 0,
              'interconnect_rc': False, 'hashes': {str(p.relative_to(ROOT)): sha(p) for p in paths if p.is_file()}}
    (build/'extraction_manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Prepared:', count(cfg['top']), 'devices;', len(nodes), 'DFF state nodes', flush=True)


def generate(design, cfg, name, h, v, phase, ticks, natural=False):
    build = design/'build'; out = build/name; out.mkdir(exist_ok=True)
    nodes = json.loads((build/'state_nodes.json').read_text())
    ports = blocks((build/'core_sim.spice').read_text())[cfg['top']]['ports']
    period = 1e9/cfg['clock_hz']; delay = 2000 if natural else 1000
    groups = [('h', h, 7), ('v', v, 10), ('phase', phase, 7)]
    key = lambda axis, i: f'anim_phase_{i}_' if axis == 'phase' else f'{axis}[{i}]'
    lines = [f'* Letter scan {name}: final extracted transistor core', ".include '../models/ip62_models'",
             ".include '../core_sim.spice'", f'.temp {cfg["temperature_c"]}', '.options method=trap',
             'VDD vdd 0 PWL(0 0 100n 0 1100n 5)' if natural else 'VDD vdd 0 5',
             f'VCLK clk 0 PULSE(0 5 {delay}n 2n 2n {period/2-2:.12f}n {period:.12f}n)',
             'XDUT '+' '.join('0' if p.lower() == 'vss' else p for p in ports)+' '+cfg['top']]
    lines += [f'C_{p} {p} 0 {cfg["output_load_pf"]}p' for p in ['r','g','b','hsync','vsync']]
    if not natural:
        for axis, val, count in groups:
            for i in range(count):
                node = nodes[key(axis, i)]; voltage = 5*((val >> i) & 1)
                lines.append(f'.ic v(xdut.{node["node"]})={voltage} v(xdut.{node["qb_node"]})={5-voltage}')
    signals = ['clk','r','g','b','hsync','vsync']+['xdut.'+nodes[key(axis,i)]['node'] for axis,_,count in groups for i in range(count)]
    lines += ['.save '+' '.join(f'v({n})' for n in signals),
              f'.tran 1n {delay+ticks*period+200:.12f}n 0 {cfg["max_step_ns"]}n'+(' uic' if natural else ''), '.end', '']
    (out/'tb.spice').write_text('\n'.join(lines))
    case = {'name': name, 'h': h, 'v': v, 'phase': phase, 'ticks': ticks, 'natural': natural,
            'delay_ns': delay, 'period_ns': period, 'signals': signals, 'sample_offset_ns': cfg['sample_offset_ns'],
            'voltage_v': cfg['voltage_v'], 'temperature_c': cfg['temperature_c'], 'output_load_pf': cfg['output_load_pf'],
            'max_step_ns': cfg['max_step_ns']}
    (out/'case.json').write_text(json.dumps(case, indent=2)+'\n')
    return name


def run_check(design, cfg, name, rerun=True):
    out = design/'build'/name; case = json.loads((out/'case.json').read_text())
    if rerun:
        start = time.monotonic()
        with (out/'ngspice.log').open('w') as log:
            result = subprocess.run(['ngspice','-n','-b','-r','wave.raw','tb.spice'], cwd=out, stdout=log, stderr=subprocess.STDOUT)
        run = {'exit_code': result.returncode, 'elapsed_seconds': time.monotonic()-start,
               'tb_sha256': sha(out/'tb.spice'), 'raw_sha256': sha(out/'wave.raw') if (out/'wave.raw').exists() else None}
        (out/'run.json').write_text(json.dumps(run, indent=2)+'\n')
    run = json.loads((out/'run.json').read_text()); assert run['exit_code'] == 0, (name, run)
    assert run['tb_sha256'] == sha(out/'tb.spice') and run['raw_sha256'] == sha(out/'wave.raw')
    header, data = (out/'wave.raw').read_bytes().split(b'Binary:\n', 1); header = header.decode()
    assert 'Flags: real' in header and 'Plotname: Transient Analysis' in header
    count = int(re.search(r'No\. Variables:\s*(\d+)', header)[1]); points = int(re.search(r'No\. Points:\s*(\d+)', header)[1])
    names = {m[2].lower(): int(m[1]) for m in re.finditer(r'^\s*(\d+)\s+(\S+)\s+\S+\s*$', header.split('Variables:\n')[1], re.M)}
    data = np.frombuffer(data, dtype=np.float64).reshape(points, count); times = data[:,0]
    assert np.isfinite(data).all() and np.all(np.diff(times) > 0)
    sample_t = (case['delay_ns']+np.arange(case['ticks'])*case['period_ns']+case['sample_offset_ns'])*1e-9
    assert times[-1] >= sample_t[-1]
    vals = np.array([np.interp(sample_t, times, data[:,names[f'v({n.lower()})']]) for n in case['signals']]).T
    bits = np.where(vals < 1.5, 0, np.where(vals > 3.5, 1, -1))
    hs = bits[:,6:13] @ 2**np.arange(7); vs = bits[:,13:23] @ 2**np.arange(10); phases = bits[:,23:30] @ 2**np.arange(7)
    observed = bits[:,1:6] @ np.array([4,2,1,8,16])
    reference = ROOT/'designs/grid_power/tests/expected_states.hex'
    expected = np.array([int(x,16) for x in reference.read_text().split()]); assert len(expected) == 131072
    first = 32 if case['natural'] else 0
    prev = tuple(int(a[first-1]) for a in [hs,vs,phases]) if first else (case['h'],case['v'],case['phase'])
    errors, samples, transitions, rgb_seen = [], [], [], set()
    for i in range(first, case['ticks']):
        h,v,phase = prev
        nh,nv = (71, 500 if v == 0 else (v+1)%1024) if h == 100 else ((h-1)%128,v)
        np_ = (phase+1)%128 if h == 100 and v == 0 else phase
        actual = (int(hs[i]),int(vs[i]),int(phases[i]))
        if (bits[i] < 0).any(): errors.append([i,'undefined voltage'])
        if actual != (nh,nv,np_): errors.append([i,'state',actual,(nh,nv,np_)])
        exp = int(expected[(v << 7)|h]); x = (71-h)%128
        if exp&7 == 4 and phase < 64 and 8 <= x < 72 and (x-8)//16 == phase//16: exp |= 3
        if int(observed[i]) != exp: errors.append([i,'output',int(observed[i]),exp])
        if np_ != phase: transitions.append([phase,np_])
        rgb_seen.add(exp&7); samples.append([i,*actual,int(observed[i]),exp])
        prev = actual
    low = vals[first:,1:6][bits[first:,1:6] == 0]; high = vals[first:,1:6][bits[first:,1:6] == 1]
    paths = [out/'tb.spice',out/'case.json',out/'wave.raw',out/'ngspice.log',out/'run.json',design/'build/core_sim.spice',reference,Path(__file__)]
    report = {'status': 'PASS' if not errors else 'FAIL', 'case': case, 'cycles_checked': case['ticks']-first,
              'state_bits': 24, 'output_bits': 5, 'phase_transitions': transitions, 'rgb_values_seen': sorted(rgb_seen),
              'max_low_sample_v': float(low.max()) if low.size else None, 'min_high_sample_v': float(high.min()) if high.size else None,
              'errors': errors, 'scope': 'extracted full-core transistor simulation, selected time window; no wire RC or PVT sweep',
              'hashes': {str(p.relative_to(ROOT)): sha(p) for p in paths}}
    (out/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    (out/'samples.json').write_text(json.dumps({'columns':['tick','h_after','v_after','phase_after','actual','expected'],'rows':samples},indent=2)+'\n')
    (out/'wave.raw.gz').write_bytes(gzip.compress((out/'wave.raw').read_bytes(), mtime=0))
    print(name, report['status'], report['cycles_checked'], 'ticks', errors[:2], flush=True)
    assert not errors, (name, errors[:5])
    return report


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--design-root',type=Path,default=ROOT/'experiments/letter_spice')
    ap.add_argument('--check-only',action='store_true'); a = ap.parse_args(); verify()
    design = a.design_root.resolve(); assert design.is_relative_to(ROOT); cfg = settings(design)
    if not a.check_only: prepare(design,cfg)
    cases = []
    if not a.check_only:
        for i,phase in enumerate(cfg['stage_phases']): cases.append(generate(design,cfg,f'stage_{i}',71,672,phase,100))
        cases += [generate(design,cfg,'lower',71,860,32,100), generate(design,cfg,'vsync',103,989,80,210)]
        for p in cfg['transition_phases']: cases.append(generate(design,cfg,f'phase_{p:03d}',101,0,p,4))
        cases.append(generate(design,cfg,'powerup',71,500,0,96,True))
        (design/'build/cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    cases = json.loads((design/'build/cases.json').read_text())
    with ThreadPoolExecutor(max_workers=cfg['workers']) as pool:
        results = list(pool.map(lambda n:run_check(design,cfg,n,not a.check_only), cases))
    observed_transitions = {tuple(t) for r in results for t in r['phase_transitions']}
    assert all((p,(p+1)%128) in observed_transitions for p in cfg['transition_phases'])
    summary = {'status':'PASS','gds_sha256':cfg['gds_sha256'],'cases':len(results),
               'cycles_checked':sum(r['cycles_checked'] for r in results),'stage_phases':cfg['stage_phases'],
               'phase_transitions':sorted(observed_transitions),'scope':'selected windows; 5 V/27 C, 1 pF outputs, 3.15 MHz; no wire RC, full-frame analog or PVT sweep',
               'results':{r['case']['name']:{k:v for k,v in r.items() if k not in ('hashes','case','errors')} for r in results},
               'hashes':{str(p.relative_to(ROOT)):sha(p) for p in [design/'config.py',Path(__file__),design/'build/extraction_manifest.json',
                         *[design/'build'/name/'verification.json' for name in cases]]}}
    (design/'build/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('PASS:',len(results),'cases;',summary['cycles_checked'],'checked transistor clocks',flush=True)


if __name__ == '__main__':
    main()
