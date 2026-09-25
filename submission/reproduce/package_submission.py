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
             if p.is_file() and p.name not in ('manifest.json', 'SHA256SUMS')}
    m = {'schema': 1, 'status': 'CORE_SUBMISSION_FRAME_INTEGRATION_PENDING',
         'top': 'ishi_vga_core', 'gds_sha256': sha(out / 'ishi_vga.gds'),
         'size_um': [1792.8, 897.2], 'bbox_um': [-15.3, 0, 1777.5, 897.2],
         'terminals_excluding_common_vss': 7, 'clock_hz': 3150000,
         'frame_integrated': False, 'drawing_drc': 0, 'mask_warnings': 1,
         'strict_lvs': 'PASS', 'extracted_spice_cycles': 668,
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
    for name in ['experiments/a_power_escape/build/verification.json',
                 'designs/grid_power/build/functional_verification.json', 'docs/power_grid_spice.json']:
        report = json.loads((ROOT / name).read_text())
        for path, expected in report['hashes'].items():
            assert sha(ROOT / path) == expected, path
    assert sha(ROOT / 'release/ishi_vga_grid_power_core.tar.gz') == '90d25224bc9f83ff6afc845da94019aa417df4a089e481b29d3a74c5e2dffded'
    out.mkdir(parents=True); sources = {}
    def copy(src, dst):
        source = ROOT / src; target = out / dst; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        sources[dst] = {'path': src, 'sha256': sha(source), 'transform': 'none'}
    copy('release/ishi_vga_grid_power_core/src/ishi_vga_grid_power.gds', 'ishi_vga.gds')
    copy('experiments/a_power_spice/build/core.extracted', 'ishi_vga.extracted')
    copy('release/ishi_vga_grid_power_core/ports.json', 'ports.json')
    copy('toolchain.lock.json', 'toolchain.lock.json')
    copy('scripts/package_submission.py', 'reproduce/package_submission.py')
    copy('scripts/submission_figures.py', 'reproduce/submission_figures.py')
    copy('tools/TR-1um/LICENSE', 'licenses/TR-1um-LICENSE')
    copy('release/ishi_vga_grid_power_core.tar.gz', 'reproduce/core_handoff.tar.gz')
    for p in ['README.md', 'SPEC.md', 'REPRODUCE.md', 'PROVENANCE.md']:
        copy('docs/submission/' + p, p)
    for p in sorted((ROOT / 'scripts/submission_tools').glob('*.py')):
        copy(str(p.relative_to(ROOT)), 'tools/' + p.name)
    for p in ['ishi_vga_core.v', 'ishi_logo.v', 'config.py', 'out/ishi_vga_core_pnr.v', 'build/tr1um_cells.v']:
        copy('designs/grid_power/' + p, 'source/' + Path(p).name)
    for p in ['tb_rtl.v', 'tb_gates.v', 'expected_frame.hex']:
        copy('designs/grid_power/tests/' + p, 'tests/' + p)
    for p in ['functional_verification.json', 'rtl.log', 'gates.log', 'observed.hex']:
        copy('designs/grid_power/build/' + p, 'verification/functional/' + p)
    for p in ['verification.json', 'drawing.lyrdb', 'candidate_mdp.lyrdb', 'core.lvsdb', 'drc.log', 'lvs.log']:
        copy('experiments/a_power_escape/build/' + p, 'verification/physical/' + p)
    copy('experiments/a_power_escape/build/audit/metal_connectivity.json', 'verification/physical/metal_connectivity.json')
    copy('experiments/a_power_flex4/build/sta.log', 'verification/sta.log')
    copy('experiments/a_power_flex4/out/STA_ishi_vga_core.txt', 'verification/STA_ishi_vga_core.txt')
    copy('docs/power_grid_spice.json', 'verification/original/power_grid_spice.json')
    for p in ['extraction_manifest.json', 'reference_manifest.json', 'state_nodes.json', 'extract.log']:
        copy('experiments/a_power_spice/build/' + p, 'verification/original/' + p)
    copy('scripts/power_spice_check.py', 'verification/original/power_spice_check.py')
    copy('experiments/a_power_spice/config.py', 'verification/original/config.py')
    copy('experiments/a_power_flex4/build/ishi_vga_core.spice', 'simulation/ishi_vga_lvs.spice')
    for p in ['core_sim.spice', 'reference_sim.spice']:
        copy('experiments/a_power_spice/build/' + p, 'simulation/' + p)
    for p in sorted((ROOT / 'tools/TR-1um/libs.tech/spice/models').iterdir()):
        if p.is_file(): copy(str(p.relative_to(ROOT)), 'simulation/models/' + p.name)
    (out / 'simulation/models.spice').write_text("* Portable include; model files copied unchanged from pinned PDK\n.include '../models/ip62_models'\n")
    for name in CASES:
        origin = 'experiments/a_power_spice/build/' + name + '/'
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
               'evidence': ['physical/verification.json', 'functional/functional_verification.json', 'original/power_grid_spice.json']}
    (out / 'verification/summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    if (ROOT / 'docs/submission_portability.json').is_file():
        copy('docs/submission_portability.json', 'verification/portability.json')
        for name in ['rtl', 'gates']:
            for p in ['result.json', 'compile.log', 'simulation.log']:
                copy('build/submission_portability01/' + name + '/' + p,
                     'verification/portable_runs/' + name + '/' + p)
        copy('build/submission_portability01/spice_upper/result.json',
             'verification/portable_runs/spice_upper/result.json')
        copy('build/submission_portability01/spice_upper/simulation/upper_init/ngspice.log',
             'verification/portable_runs/spice_upper/ngspice.log')
    seal(out, sources)
    print('Created', out, 'with', len(json.loads((out / 'manifest.json').read_text())['files']), 'hashed files')


if __name__ == '__main__':
    main()
