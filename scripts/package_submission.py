#!/usr/bin/env python3
"""Package the adopted letter-animation core, transistor evidence and real video."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from check_toolchain import ROOT, verify


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='submission');a=ap.parse_args();verify()
    out=(ROOT/a.out).resolve();assert out.is_relative_to(ROOT) and not out.exists(), 'Choose a new directory'
    core=ROOT/'release/ishi_vga_letter_scan_core';spice=ROOT/'experiments/letter_art_spice/build'
    art=ROOT/'experiments/a_letter_silicon_art/build'
    original=json.loads((core/'manifest.json').read_text())
    assert all(sha(core/name)==digest for name,digest in original['files'].items())
    assert original['stage_frames']==[16,16,16,16,64] and original['fpga_programmed_mode']=='SRAM'
    summary=json.loads((spice/'summary.json').read_text())
    artwork=json.loads((art/'verification.json').read_text())
    assert artwork['status']=='ART_CORE_VERIFIED' and artwork['base_gds_sha256']==original['gds_sha256']
    assert all(sha(ROOT/path)==digest for path,digest in artwork['hashes'].items())
    assert summary['status']=='PASS' and summary['gds_sha256']==artwork['gds_sha256']
    for report in [summary,json.loads((spice/'extraction_manifest.json').read_text())]:
        assert all(sha(ROOT/path)==digest for path,digest in report['hashes'].items())
    cases=json.loads((spice/'cases.json').read_text())
    for name in cases:
        report=json.loads((spice/name/'verification.json').read_text())
        assert report['status']=='PASS'
        assert all(sha(ROOT/path)==digest for path,digest in report['hashes'].items())
    assert sha(spice/'core.extracted')==artwork['extracted_sha256']
    out.mkdir();sources={}
    def copy(src,dest):
        src=Path(src);target=out/dest;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,target)
        sources[dest]={'path':str(src.relative_to(ROOT)),'sha256':sha(src)}
    for p in sorted(core.rglob('*')):
        if p.is_file() and p.name not in ('manifest.json','SHA256SUMS','README.md'):
            copy(p,str(p.relative_to(core)))
    # Retain historical circuit verification explicitly; final physical reports
    # below belong to the decorated GDS. No historical checkpoint is rewritten.
    copy(core/'verification/verification.json','verification/base_core.json')
    copy(art/'candidate.gds','ishi_vga.gds')
    copy(art/'core.extracted','ishi_vga.extracted')
    for name in ['verification.json','art_geometry.json','drawing.lyrdb','candidate_mdp.lyrdb','core.lvsdb','drc.log','lvs.log']:
        copy(art/name,'verification/'+name)
    for name in ['README.md','SPEC.md','PROVENANCE.md','REPRODUCE.md','SPICE.md','REVIEW.md','SILICON_ART.md']:
        copy(ROOT/'docs/submission'/name,name)
        # Templates also render correctly inside the repository's docs/ tree.
        (out/name).write_text((out/name).read_text().replace('../../submission/',''))
        sources[name]['transform']='resolve docs-template submission links to bundle-relative paths'
    for name in ['core_sim.spice','core.extracted','state_nodes.json','extract.log','extraction_manifest.json','summary.json','cases.json']:
        copy(spice/name,'simulation/'+name)
    for p in sorted((spice/'models').iterdir()):
        if p.is_file():copy(p,'simulation/models/'+p.name)
    for name in cases:
        for file in ['tb.spice','case.json','ngspice.log','run.json','verification.json','samples.json','wave.raw.gz']:
            copy(spice/name/file,'simulation/'+name+'/'+file)
    for name in ['expected_frame.hex','expected_states.hex']:
        copy(ROOT/'designs/grid_power/tests'/name,'tests/'+name)
    for name in ['verify_bundle.py','check_letter_wave.py','run_letter_tests.py']:
        copy(ROOT/'scripts/submission_tools'/name,'tools/'+name)
    for ext in ['gif','mp4','json']:
        copy(ROOT/'docs/images'/('fpga-vga-animation-20260925.'+ext),'fpga_demo.'+ext)
    copy(ROOT/'tools/TR-1um/LICENSE','licenses/TR-1um-LICENSE')
    for name in ['package_submission.py','submission_figures.py','letter_spice_check.py','make_demo_media.py',
                 'add_letter_silicon_art.py','verify_letter_silicon_art.py','review_letter_submission.py']:
        copy(ROOT/'scripts'/name,'reproduce/'+name)
    copy(ROOT/'experiments/letter_art_spice/config.py','reproduce/spice_config.py')
    copy(ROOT/'experiments/a_letter_silicon_art/config.py','reproduce/silicon_art_config.py')
    for p in sorted((ROOT/'assets/silicon_art').iterdir()):
        if p.is_file():copy(p,'reproduce/silicon_art/'+p.name)
    review=ROOT/'docs/reviews/letter_submission_20260925.json'
    reviewed=json.loads(review.read_text())
    assert reviewed['gds_sha256']==original['gds_sha256']
    # This is a historical audit of the frozen base, including its old bundle.
    # Its checked_files are not assertions about the decorated bundle.
    copy(review,'verification/base_review.json')
    current_review={'verdict':reviewed['verdict'],'gds_sha256':artwork['gds_sha256'],
                    'base_review':'base_review.json','physical_verification':'verification.json',
                    'transistor_verification':'../simulation/summary.json',
                    'rtl_gate_sta_scope':'base results retained by exact functional geometry and extraction equivalence',
                    'fatal_core_defect_found':False,'manufacturing_signoff':False,'frame_integration_performed':False}
    (out/'verification/review.json').write_text(json.dumps(current_review,indent=2)+'\n')
    subprocess.run(['/usr/bin/python3',str(ROOT/'scripts/submission_figures.py'),'--directory',str(out)],cwd=ROOT,check=True)
    portability=ROOT/'docs/letter_art_submission_portability.json'
    if portability.exists():
        portable=json.loads(portability.read_text());assert portable['status']=='PASS'
        assert portable['gds_sha256']==artwork['gds_sha256']
        assert all(sha(out/name)==digest for name,digest in portable['checked_files'].items())
        copy(portability,'verification/portable_runs.json')
    files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    manifest={k:v for k,v in original.items() if k not in ('files','sources')}
    manifest.update(status='LETTER_ANIMATION_SUBMISSION',sources=sources,files=files,
                    gds_sha256=artwork['gds_sha256'],base_gds_sha256=original['gds_sha256'],
                    silicon_art={'cell':'ishi_vga_art','layer':'M1','bbox_um':artwork['art_bbox_um']},
                    extracted_spice_cases=summary['cases'],extracted_spice_cycles=summary['cycles_checked'],
                    hardware_demo='fpga_demo.gif',hardware_video='fpga_demo.mp4')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');files['manifest.json']=sha(out/'manifest.json')
    (out/'SHA256SUMS').write_text(''.join(digest+'  '+name+'\n' for name,digest in sorted(files.items())))
    print('Created',out,'with',len(files),'hashed files including manifest.json')


if __name__=='__main__':main()
