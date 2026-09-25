#!/usr/bin/env python3
"""Publish the checked core and FPGA image, with hash-bound programming evidence."""
import argparse,hashlib,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image
import klayout.lay as lay
from check_toolchain import ROOT,verify

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--allow-unprogrammed',action='store_true');a=ap.parse_args();verify()
    d=a.evidence.resolve();b=d/'build';out=ROOT/'release/ishi_vga_letter_scan_core'
    report=json.loads((b/'verification.json').read_text());assert report['status']=='CORE_VERIFIED'
    for path,h in report['hashes'].items():assert sha(ROOT/path)==h,path
    replay=json.loads((d/'replay.json').read_text());assert replay['status']=='PASS'
    for path,h in replay['hashes'].items():assert sha(ROOT/path)==h,path
    fpga=ROOT/'build/fpga_vga_letter_animation'
    assert json.loads((fpga/'preprogram_verification.json').read_text())['status']=='PASS'
    assert sha(fpga/'vga_letter_animation.fs')==json.loads((fpga/'preprogram_verification.json').read_text())['bitstream_sha256']
    fpga_hashes=json.loads((fpga/'sha256.json').read_text())
    assert all(sha(ROOT/path)==h for path,h in fpga_hashes.items())
    for name in ['ishi_vga_core.v','ishi_logo.v']:
        assert sha(d/name)==fpga_hashes['experiments/a_letter_scan_eco/'+name]
    receipt=json.loads((fpga/'programming.json').read_text()) if (fpga/'programming.json').exists() else {}
    program=(fpga/'program.log').read_bytes() if (fpga/'program.log').exists() else b''
    programmed=(receipt.get('status')=='PASS' and receipt.get('mode')=='SRAM'
        and receipt.get('returncode')==0 and b'100.00%' in program and b'DONE' in program
        and receipt.get('bitstream_sha256')==sha(fpga/'vga_letter_animation.fs')
        and receipt.get('program_log_sha256')==sha(fpga/'program.log')
        and receipt.get('script_sha256')==sha(ROOT/'scripts/program_fpga.py'))
    assert programmed or a.allow_unprogrammed, 'No successful programming receipt for this bitstream'
    sources={}
    def copy(src,name):
        src=Path(src);target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
        if src.resolve()!=target.resolve():shutil.copyfile(src,target)
        sources[name]={'path':str(src.relative_to(ROOT)),'sha256':sha(src)}
    copy(b/'candidate.gds','ishi_vga.gds');copy(b/'core.extracted','ishi_vga.extracted')
    copy(b/'ishi_vga_core.spice','ishi_vga_lvs.spice')
    copy(ROOT/'submission/ports.json','ports.json');copy(ROOT/'toolchain.lock.json','toolchain.lock.json')
    copy(ROOT/'submission/tools/verify_bundle.py','tools/verify_bundle.py')
    copy(Path(__file__),'reproduce/package_letter_animation_core.py')
    for name in ['ishi_vga_core.v','ishi_logo.v','config.py','clock_electrical.tcl','clock_report.tcl']:copy(d/name,'source/'+name)
    copy(d/'out/ishi_vga_core_pnr.v','source/ishi_vga_core_pnr.v')
    copy(d/'patch_split_toggle/build/tr1um_cells.v','source/tr1um_cells.v')
    for name in ['config.py','letter_scan_patch.v']:copy(d/'patch_split_toggle'/name,'source/patch/'+name)
    copy(d/'patch_split_toggle/out/letter_scan_patch_pnr.v','source/patch/letter_scan_patch_pnr.v')
    copy(d/'layout/placement.json','verification/placement.json')
    for name in ['verification.json','drawing.lyrdb','candidate_mdp.lyrdb','drc.log','core.lvsdb','lvs.log','pins.json','routing_manifest.json','placement_manifest.json','repair_manifest.json','audit/metal_connectivity.json','functional/verification.json','functional/simulation.log','functional/observed.bin','functional/tb.v']:
        copy(b/name,'verification/'+name)
    for name in ['STA_ishi_vga_core.guard.json','STA_ishi_vga_core.txt']:copy(d/'out'/name,'verification/'+name)
    copy(d/'replay.json','verification/replay.json')
    for name in ['vga_letter_animation.fs','preprogram_verification.json','sha256.json','commands.json','timing.json','synth.log','pnr.log','pack.log']:copy(fpga/name,'fpga/'+name)
    for name in ['program.log','programming.json']:
        if programmed:copy(fpga/name,'fpga/'+name)
        else:(out/'fpga'/name).unlink(missing_ok=True)
    # Render the five actual sampled gate frames; the checker also compared RTL.
    raw=np.frombuffer((b/'functional/observed.bin').read_bytes(),dtype=np.uint8).reshape(5,525,100)
    data=np.repeat(raw[:,:480,:80]&7,8,axis=2);palette=[]
    for c in range(8):palette.extend(255*((c>>s)&1) for s in [2,1,0])
    palette += [0]*(768-len(palette));frames=[]
    for frame in data:
        im=Image.fromarray(frame).convert('P');im.putpalette(palette);frames.append(im)
    frames[0].save(out/'animation.gif',save_all=True,append_images=frames[1:],duration=[270,260,270,270,1060],loop=0,disposal=2,optimize=False)
    view=lay.LayoutView();view.load_layout(str(out/'ishi_vga.gds'),0)
    cv=view.cellview(0);cv.cell_index=cv.layout().cell('ishi_vga_core').cell_index()
    view.load_layer_props(str(ROOT/'tools/TR-1um/libs.tech/klayout/tech/TR-1um.lyp'),0,True)
    view.set_config('background-color','#ffffff');view.set_config('grid-visible','false');view.max_hier();view.zoom_fit()
    view.save_image(str(out/'layout.png'),1800,1000)
    files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name not in ('manifest.json','SHA256SUMS')}
    manifest={'schema':1,'status':'LETTER_ANIMATION_CORE_HANDOFF','top':'ishi_vga_core','gds_sha256':sha(out/'ishi_vga.gds'),'size_um':[1792.8,897.2],'clock_hz':3150000,'terminals_excluding_common_vss':7,'frame_integrated':False,'drawing_drc':0,'mask_warnings':1,'strict_lvs':'PASS','logical_cells':241,'dffs':29,'stages':['I','S','H','I','idle'],'stage_frames':[16,16,16,16,64],'cycle_frames':128,'rtl_gate_ticks':6720000,'fpga_programmed_mode':'SRAM' if programmed else None,'interconnect_rc':False,'sources':sources,'files':files}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');files['manifest.json']=sha(out/'manifest.json')
    (out/'SHA256SUMS').write_text(''.join(h+'  '+p+'\n' for p,h in sorted(files.items())))
    print(out,flush=True)

if __name__=='__main__':main()
