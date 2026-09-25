#!/usr/bin/env python3
"""Build a shallow, portable submission directory from frozen core evidence.

This is design-owned packaging code. It does not modify the GDS or upstream.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from check_toolchain import ROOT, verify

CASES = ['upper_init', 'lower_init', 'vsync_init', 'frame_wrap_init', 'powerup', 'upper_reference']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def seal(out, sources):
    files = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*'))
             if p.is_file() and p not in (out/'manifest.json',out/'SHA256SUMS')}
    m = {'schema': 1, 'status': 'CLOCK_ECO_CORE_HANDOFF_NOT_MANUFACTURING_SIGNOFF',
         'top': 'ishi_vga_core', 'gds_sha256': sha(out / 'ishi_vga.gds'),
         'size_um': [1792.8, 897.2], 'bbox_um': [-15.3, 0, 1777.5, 897.2],
         'terminals_excluding_common_vss': 7, 'clock_hz': 3150000,
         'frame_integrated': False, 'drawing_drc': 0, 'mask_warnings': 1,
         'strict_lvs': 'PASS', 'extracted_spice_cycles': 668,
         'clock_pin_capacitance_violation': False, 'interconnect_rc': False,
         'manufacturing_ready': False,
         'sources': sources, 'files': files}
    (out / 'manifest.json').write_text(json.dumps(m, indent=2, ensure_ascii=False) + '\n')
    files['manifest.json'] = sha(out / 'manifest.json')
    (out / 'SHA256SUMS').write_text(''.join(h + '  ' + p + '\n' for p, h in sorted(files.items())))


def pictures(out):
    import klayout.db as db
    import klayout.lay as lay
    import numpy as np
    from PIL import Image
    ly = db.Layout(); ly.read(str(out / 'ishi_vga.gds'))
    top = ly.cell('ishi_vga_core')
    assert ly.dbu == .001
    assert [round(x * ly.dbu, 3) for x in [top.bbox().left, top.bbox().bottom,
                                          top.bbox().right, top.bbox().top]] == [-15.3, 0, 1777.5, 897.2]
    view = lay.LayoutView()
    view.load_layout(str(out / 'ishi_vga.gds'), 0)
    cv = view.cellview(0)
    cv.cell_index = cv.layout().cell('ishi_vga_core').cell_index()
    view.load_layer_props(str(ROOT / 'tools/TR-1um/libs.tech/klayout/tech/TR-1um.lyp'), 0, True)
    view.set_config('background-color', '#ffffff')
    view.set_config('grid-visible', 'false')
    view.max_hier(); view.zoom_fit()
    view.save_image(str(out / 'ishi_vga_layout.png'), 1800, 1000)
    # Actual gate observation starts at raster index 49000 (VSYNC assertion).
    observed = np.array([int(x, 16) for x in (out / 'verification/functional/observed.hex').read_text().split()])
    expected = np.array([int(x, 16) for x in (out / 'tests/expected_frame.hex').read_text().split()])
    assert len(observed) == 52500 and np.array_equal(observed, np.roll(expected, -49000))
    frame = np.roll(observed, 49000).reshape(525, 100)[:480, :80] & 7
    rgb = np.stack([((frame >> s) & 1) * 255 for s in [2, 1, 0]], axis=-1).astype('uint8')
    Image.fromarray(np.repeat(rgb, 8, axis=1)).save(out / 'ishi_vga_output.png')
    subprocess.run(['/usr/bin/python3', str(ROOT / 'scripts/submission_figures.py'),
                    '--directory', str(out)], cwd=ROOT, check=True)



def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='submission')
    a = ap.parse_args(); verify(); out = (ROOT / a.out).resolve()
    assert out.is_relative_to(ROOT) and not out.exists(), 'Choose a new workspace directory'
    # Validate evidence before presenting it under a new name.
    report=json.loads((ROOT/'experiments/a_clock_tree/build/verification.json').read_text())
    for path,expected in report['hashes'].items():
        assert sha(ROOT/path)==expected,path
    assert report['status']=='CORE_ECO_VERIFIED_NOT_MANUFACTURING_SIGNOFF'
    assert sha(ROOT/'release/ishi_vga_grid_power_core.tar.gz')=='90d25224bc9f83ff6afc845da94019aa417df4a089e481b29d3a74c5e2dffded'
    out.mkdir(parents=True); sources = {}
    def copy(src, dst):
        source = ROOT / src; target = out / dst; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        sources[dst] = {'path': src, 'sha256': sha(source), 'transform': 'none'}
    copy('experiments/a_clock_tree/build/candidate.gds','ishi_vga.gds')
    copy('experiments/a_clock_tree/build/core.extracted', 'ishi_vga.extracted')
    copy('release/ishi_vga_grid_power_core/ports.json', 'ports.json')
    copy('toolchain.lock.json', 'toolchain.lock.json')
    copy('scripts/package_submission.py', 'reproduce/package_submission.py')
    copy('scripts/submission_figures.py', 'reproduce/submission_figures.py')
    copy('tools/TR-1um/LICENSE', 'licenses/TR-1um-LICENSE')
    copy('release/ishi_vga_clock_eco_reproduce.tar.gz', 'reproduce/clock_eco_reproduce.tar.gz')
    for p in ['README.md', 'SPEC.md', 'REPRODUCE.md', 'PROVENANCE.md']:
        copy('docs/submission/' + p, p)
    for p in sorted((ROOT / 'scripts/submission_tools').glob('*.py')):
        copy(str(p.relative_to(ROOT)), 'tools/' + p.name)
    for p in ['ishi_vga_core.v', 'ishi_logo.v', 'out/ishi_vga_core_pnr.v', 'build/tr1um_cells.v']:
        copy('designs/grid_power/' + p, 'source/' + Path(p).name)
    copy('experiments/a_clock_tree/config.py','source/config.py')
    for p in ['tb_rtl.v', 'tb_gates.v', 'tb_exhaustive.v', 'expected_frame.hex','expected_states.hex']:
        copy('designs/grid_power/tests/' + p, 'tests/' + p)
    for p in ['functional_verification.json', 'rtl.log', 'gates.log', 'observed.hex']:
        copy('experiments/a_clock_tree/build/' + p, 'verification/functional/' + p)
    for p in ['verification.json', 'drawing.lyrdb', 'candidate_mdp.lyrdb', 'core.lvsdb', 'drc.log', 'lvs.log']:
        copy('experiments/a_clock_tree/build/' + p, 'verification/physical/' + p)
    copy('experiments/a_clock_tree/build/audit/metal_connectivity.json', 'verification/physical/metal_connectivity.json')
    copy('experiments/a_clock_tree/build/sta.log', 'verification/sta.log')
    copy('experiments/a_clock_tree/out/STA_ishi_vga_core.txt', 'verification/STA_ishi_vga_core.txt')
    copy('experiments/a_clock_tree/out/STA_ishi_vga_core.guard.json','verification/STA_ishi_vga_core.guard.json')
    copy('experiments/a_clock_tree/build/exhaustive.log','verification/functional/exhaustive.log')
    copy('build/clock_replay02/replay.json','verification/clock_replay.json')
    for p in ['extraction_manifest.json', 'reference_manifest.json', 'state_nodes.json', 'extract.log']:
        copy('experiments/a_clock_tree/build/' + p, 'verification/original/' + p)
    copy('scripts/power_spice_check.py', 'verification/original/power_spice_check.py')
    copy('experiments/a_clock_tree/config.py', 'verification/original/config.py')
    copy('experiments/a_clock_tree/build/ishi_vga_core.spice', 'simulation/ishi_vga_lvs.spice')
    for p in ['core_sim.spice', 'reference_sim.spice']:
        copy('experiments/a_clock_tree/build/' + p, 'simulation/' + p)
    for p in sorted((ROOT / 'tools/TR-1um/libs.tech/spice/models').iterdir()):
        if p.is_file(): copy(str(p.relative_to(ROOT)), 'simulation/models/' + p.name)
    (out / 'simulation/models.spice').write_text("* Portable include; model files copied unchanged from pinned PDK\n.include '../models/ip62_models'\n")
    for name in CASES:
        origin = 'experiments/a_clock_tree/build/' + name + '/'
        for p in ['tb.spice', 'case.json', 'config.py']:
            copy(origin + p, 'simulation/' + name + '/' + p)
        for p in ['verification.json', 'samples.json', 'ngspice.log', 'run.json']:
            copy(origin + p, 'verification/spice/' + name + '/' + p)
        target = 'verification/spice/' + name + '/wave.raw.gz'
        (out / target).write_bytes(gzip.compress((ROOT / (origin + 'wave.raw')).read_bytes(), mtime=0))
        sources[target] = {'path': origin + 'wave.raw', 'sha256': sha(ROOT / (origin + 'wave.raw')), 'transform': 'gzip, mtime=0'}
    pictures(out)
    summary = {'scope': 'unintegrated core', 'gds_sha256': sha(out / 'ishi_vga.gds'),
               'drawing_drc': 0, 'mask_warnings': [{'rule': 'WAR06 Floating SG', 'count': 1, 'node': 'CLK BUFTH input'}],
               'strict_lvs': 'PASS: 8 ports', 'short_pairs': 0, 'open_nets': 0,
               'rtl_and_gate_frames': 2, 'ticks_per_functional_test': 105000,
               'transistor_extracted_cycles': 668, 'transistor_reference_cycles': 110,
               'interconnect_rc': False, 'full_frame_analog': False, 'pvt_sweep': False,
               'frame_integrated': False, 'hardware_test': False,
               'manufacturing_ready':False, 'binary_states_checked':131072,
               'spice_raster_cycles':540, 'spice_startup_cycles':128, 'analog_frame_acquisition_observed':False,
               'evidence': ['physical/verification.json', 'functional/functional_verification.json', 'original/extraction_manifest.json']}
    (out / 'verification/summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    copy('docs/submission/REVIEW.md','REVIEW.md')
    for name in ['submission_manufacturing_review.md','submission_manufacturing_response.md','submission_astra_review.md','submission_astra_review.json','submission_reviewed_manifest.json']:
        copy('docs/reviews/'+name,'review/'+name)
    for p in sorted((ROOT/'docs/reviews/submission_manufacturing_20260925').rglob('*')):
        if p.is_file():copy(str(p.relative_to(ROOT)),'review/submission_manufacturing_20260925/'+str(p.relative_to(ROOT/'docs/reviews/submission_manufacturing_20260925')))
    base=ROOT/'build/sta_guard_replay01'
    for p in sorted(base.rglob('*')):
        if p.is_file() and (p.name in ['results.json','sta.log','control.tcl'] or p.name.endswith('.guard.json')):
            copy(str(p.relative_to(ROOT)),'review/sta_guard_controls/'+str(p.relative_to(base)))
    if (ROOT/'docs/clock_eco_portability.json').exists():
        copy('docs/clock_eco_portability.json','verification/portability.json')
        for mode in ['rtl','gates','states','spice']:
            copy('build/clock_bundle_'+mode+'/result.json','verification/portable_runs/'+mode+'/result.json')
        copy('build/clock_archive_portability/ishi_vga_clock_eco/build/portable_replay/replay.json','verification/archive_replay.json')
    seal(out, sources)
    print('Created', out, 'with', len(json.loads((out / 'manifest.json').read_text())['files']), 'hashed files')


if __name__ == '__main__':
    main()
