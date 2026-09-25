#!/usr/bin/env python3
"""Isolated animation RTL, measured v59_4 mapping and simulation-derived previews.

Does not modify designs/grid_power or submission. All animation counters use
one common input clock and a frame-end enable; no generated/gated clocks.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from check_toolchain import ROOT, verify

BASE=ROOT/'experiments/animation_samples'
MODES=['static_reference','white_pulse','wire_scan','letter_scan','palette_swap']
TITLES={'white_pulse':'A · 配線の白点灯','wire_scan':'B · 配線を走る光','letter_scan':'C · 文字の順次点灯','palette_swap':'D · 色の切り替え'}
EFFECTS={
 'white_pulse':"wire on = logo_rgb[1] & phase[5];\nwire [2:0] animated_rgb = {logo_rgb[2] | on, logo_rgb[1:0]};",
 'wire_scan':"wire on = logo_rgb[1] & ((~h[5:3]) == phase[5:3]);\nwire [2:0] animated_rgb = {logo_rgb[2] | on, logo_rgb[1:0]};",
 'letter_scan':"wire on = logo_rgb[2] & ~logo_rgb[0] & ((~h[5:4]) == phase[5:4]);\nwire [2:0] animated_rgb = {logo_rgb[2], logo_rgb[1] | on, logo_rgb[0] | on};",
 'palette_swap':"wire [2:0] animated_rgb = phase[5] ? {logo_rgb[1],logo_rgb[2],logo_rgb[0]} : logo_rgb;",
}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prepare(style):
 verify();BASE.mkdir(exist_ok=False)
 source=ROOT/'designs/grid_power'
 cfg=(source/'config.py').read_text()
 cfg=cfg.replace("SYN_TB_RTL = ['tests/tb_rtl.v']",'SYN_TB_RTL = []').replace("SYN_TB_NET = ['tests/tb_gates.v']",'SYN_TB_NET = []')
 cfg=cfg.replace("STA_CLK_PORT = 'clk'",'STA_CLK_PORT = None').replace("STA_EXTRA_TCL = os.path.join(ROOT, 'clock_electrical.tcl')",'STA_EXTRA_TCL = None')
 for mode in MODES:
  d=BASE/mode;d.mkdir();(d/'build').mkdir();(d/'out').mkdir()
  core=(source/'ishi_vga_core.v').read_text()
  if mode!='static_reference':
   core=core.replace('always @(posedge clk) begin',"reg [5:0] phase;\n"+EFFECTS[mode]+"\nalways @(posedge clk) begin\n  if ((h == 7'd100) && (v == 10'd0)) phase <= phase + 6'd1;")
   core=core.replace('{r,g,b}<=logo_rgb;','{r,g,b}<=animated_rgb;')
  if style=='add_enable':
   core=core.replace("if ((h == 7'd100) && (v == 10'd0)) phase <= phase + 6'd1;","phase <= phase + {5'b0, ((h == 7'd100) && (v == 10'd0))};")
  (d/'ishi_vga_core.v').write_text(core)
  shutil.copyfile(source/'ishi_logo.v',d/'ishi_logo.v')
  settings={'counter_style':style,'mode':mode,'phase_bits':0 if mode=='static_reference' else 6,'phase_enable':'h==100 && v==0','clock_hz':3150000,'frame_hz':60,'cycle_frames':64,'source':'designs/grid_power','adopted':False,'flow_scope':'synthesis and digital simulation only'}
  (d/'config.py').write_text(cfg.replace('finalize(globals())','ANIMATION = '+repr(settings)+'\nfinalize(globals())'))
 (BASE/'source_manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [source/'ishi_vga_core.v',source/'ishi_logo.v',source/'config.py',ROOT/'toolchain.lock.json',Path(__file__)]}},indent=2)+'\n')
 print(BASE)

def area():
 lib=(ROOT/'tools/APRtools/stdcell/v59_4/tr1um_typ_5v0_25c.lib').read_text()
 cells={n:float(a) for n,a in re.findall(r'cell \((\w+)\)\s*\{\s*area\s*:\s*([\d.]+)',lib)}
 result={}
 for mode in MODES:
  d=BASE/mode;p=d/'out/ishi_vga_core_pnr.v';text=p.read_text()
  used=Counter(re.findall(r'^\s*('+ '|'.join(cells)+r')\s+\S+\s*\(',text,re.M))
  assert used['DFF']==(22 if mode=='static_reference' else 28)
  result[mode]={'cells':sum(used.values()),'area_um2':round(sum(cells[n]*c for n,c in used.items()),1),'types':dict(sorted(used.items())),'net_sha256':sha(p)}
 base=result['static_reference']['area_um2']
 for mode,r in result.items():
  r['additional_cells']=r['cells']-result['static_reference']['cells'];r['additional_area_um2']=round(r['area_um2']-base,1);r['additional_percent']=round(100*(r['area_um2']/base-1),2)
 output={'scope':'fresh same-flow mapped cell area, before physical clock ECO; not routed core bbox','liberty_sha256':sha(ROOT/'tools/APRtools/stdcell/v59_4/tr1um_typ_5v0_25c.lib'),'variants':result}
 (BASE/'area.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))

def gate_init(mode,inst):
 text=(BASE/mode/'out/ishi_vga_core_pnr.v').read_text();lines=[];found={}
 for name,body in re.findall(r'\bDFF\s+(\S+)\s*\((.*?)\);',text,re.S):
  q=re.search(r'\.Q\(([^)]+)\)',body)[1].strip();q=q.lstrip('\\')
  if q in ['r','g','b','hsync','vsync']:value="1'b0"
  elif q.startswith('h['):value="1'b"+str((71>>int(q[2:-1]))&1)
  elif q.startswith('v['):value="1'b"+str((500>>int(q[2:-1]))&1)
  elif q.startswith('phase['):value=f'phase_value[{int(q[6:-1])}]'
  else:raise AssertionError((mode,name,q))
  assert q not in found;found[q]=name;lines.append(f'{inst}.{name}.q={value};')
 assert len(found)==28
 return '\n'.join(lines)

def simulate(kind):
 verify();d=BASE/('sim_'+kind);d.mkdir(exist_ok=False);(d/'build').mkdir()
 sources=[];declarations=[];inits=[];checks=[];writes=[]
 for i,mode in enumerate(MODES[1:]):
  src=BASE/mode/('ishi_vga_core.v' if kind=='rtl' else 'out/ishi_vga_core_pnr.v')
  target=d/(mode+'.v');target.write_text(src.read_text().replace('module ishi_vga_core',f'module core_{i}',1));sources.append(target)
  declarations.append(f'wire [4:0] out{i}; core_{i} dut{i}(.clk(clk),.vsync(out{i}[4]),.hsync(out{i}[3]),.r(out{i}[2]),.g(out{i}[1]),.b(out{i}[0])); integer fd{i};')
  inits.append(f'dut{i}.h=71;dut{i}.v=500;dut{i}.phase=phase_value;dut{i}.r=0;dut{i}.g=0;dut{i}.b=0;dut{i}.hsync=0;dut{i}.vsync=0;' if kind=='rtl' else gate_init(mode,f'dut{i}'))
  checks.append(f'if(out{i} !== exp{i}) $fatal(1,"{mode} frame=%0d tick=%0d got=%h expected=%h",frame,tick,out{i},exp{i});')
  writes.append(f'if ((frame%8)==0) $fwrite(fd{i},"%c",out{i});')
 init='\n'.join(inits)
 opening='\n'.join(f'fd{i}=$fopen("build/{m}.bin","wb");' for i,m in enumerate(MODES[1:]))
 # RTL free-runs a full 64-frame cycle. Gate fixture visits the 8 distinct
 # phases at normal VGA timing, including each frame-end counter transition.
 setup=init if kind=='rtl' else ''
 perframe='' if kind=='rtl' else 'phase_value=frame;\n'+init
 advance='frame=frame+1' if kind=='rtl' else 'frame=frame+8'
 tb='''`timescale 1ns/1ps
module tb_anim;
reg clk=0;
always #158.730158730159 clk=~clk;
DECL
reg [4:0] reference [0:52499];
reg [4:0] exp0,exp1,exp2,exp3;
reg [2:0] c;
reg [5:0] phase_value;
integer frame,tick,x,checked;
initial begin
 $readmemh("REFERENCE",reference);
 phase_value=0;checked=0;
 SETUP
 OPEN
 for(frame=0;frame<64;ADVANCE) begin
  PERFRAME
  for(tick=0;tick<52500;tick=tick+1) begin
   @(posedge clk); #80;
   c=reference[tick][2:0];x=tick%100;
   exp0=reference[tick];exp1=reference[tick];exp2=reference[tick];exp3=reference[tick];
   if(c==3 && frame>=32) exp0[2:0]=7;
   if(c==3 && x>=8 && x<72 && ((x-8)/8)==(frame/8)) exp1[2:0]=7;
   if(c==4 && x>=8 && x<72 && ((x-8)/16)==(frame/16)) exp2[2:0]=7;
   if(frame>=32) exp3[2:0]={c[1],c[2],c[0]};
   CHECKS
   WRITES
   checked=checked+1;
   @(negedge clk); #1;
  end
 end
 CLOSE
 $display("PASS: %0d ticks per variant; RGB and sync, 4 variants",checked);
 $finish;
end
initial begin #1200000000; $fatal(1,"watchdog"); end
endmodule
'''
 for a,b in {'DECL':'\n'.join(declarations),'REFERENCE':str(ROOT/'designs/grid_power/tests/expected_frame.hex'),'SETUP':setup,'OPEN':opening,'ADVANCE':advance,'PERFRAME':perframe,'CHECKS':'\n'.join(checks),'WRITES':'\n'.join(writes),'CLOSE':'\n'.join(f'$fclose(fd{i});' for i in range(4))}.items():tb=tb.replace(a,b)
 (d/'tb_anim.v').write_text(tb)
 sources.append(ROOT/'designs/grid_power/ishi_logo.v' if kind=='rtl' else BASE/'white_pulse/build/tr1um_cells.v')
 exe=d/'build/sim.vvp'
 with (d/'build/compile.log').open('w') as log:subprocess.run([str(ROOT/'.tools/bin/iverilog'),'-g2012','-s','tb_anim','-o',str(exe),str(d/'tb_anim.v'),*map(str,sources)],cwd=d,stdout=log,stderr=subprocess.STDOUT,check=True)
 with (d/'build/simulation.log').open('w') as log:subprocess.run([str(ROOT/'.tools/bin/vvp'),str(exe)],cwd=d,stdout=log,stderr=subprocess.STDOUT,check=True)
 log=(d/'build/simulation.log').read_text();assert 'PASS:' in log;print(log)
 for mode in MODES[1:]:assert (d/'build'/f'{mode}.bin').stat().st_size==8*52500
 (d/'result.json').write_text(json.dumps({'status':'PASS','model':kind,'frames':64 if kind=='rtl' else 8,'variants':4,'ticks_per_variant':(64 if kind=='rtl' else 8)*52500,'sampled_frames':list(range(0,64,8)),'clock_hz':3150000,'initialization':'test fixture only; no reset or initialization in synthesized RTL','scope':'RTL continuously advances phase; gates sample 8 phase-start frames with unit-delay cells','hashes':{str(p.relative_to(ROOT)):sha(p) for p in [d/'tb_anim.v',*sources,d/'build/simulation.log',*[d/'build'/f'{m}.bin' for m in MODES[1:]]]}},indent=2)+'\n')


def synthesize():
 verify()
 for mode in MODES:
  d=BASE/mode;(d/'build').mkdir(exist_ok=True);(d/'out').mkdir(exist_ok=True)
  with (d/'build/synthesis.log').open('w') as log:
   subprocess.run([sys.executable,str(ROOT/'scripts/run_apr.py'),'--design-root',str(d),'syn/syn.sh'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
  print(mode,'mapped',flush=True)
 area()

def select():
 verify();BASE.mkdir(exist_ok=False)
 choices=[ROOT/'experiments/animation_samples',ROOT/'experiments/animation_addenable']
 areas={p:json.loads((p/'area.json').read_text())['variants'] for p in choices};selected={}
 for mode in MODES:
  origin=min(choices,key=lambda p:areas[p][mode]['area_um2'])/mode
  dest=BASE/mode;dest.mkdir();(dest/'build').mkdir();(dest/'out').mkdir()
  for name in ['config.py','ishi_vga_core.v','ishi_logo.v','out/ishi_vga_core_pnr.v','build/tr1um_cells.v','build/synthesis.log']:
   shutil.copyfile(origin/name,dest/name)
  selected[mode]={'source':str(origin.relative_to(ROOT)),'files':{n:sha(dest/n) for n in ['config.py','ishi_vga_core.v','ishi_logo.v','out/ishi_vga_core_pnr.v','build/synthesis.log']}}
 (BASE/'selection.json').write_text(json.dumps(selected,indent=2)+'\n')
 area()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','synthesize','select','area','rtl','gates']);p.add_argument('--directory',type=Path,default=BASE);p.add_argument('--counter-style',choices=['enable','add_enable'],default='enable');a=p.parse_args()
 BASE=a.directory.resolve();assert BASE.is_relative_to(ROOT)
 if a.action=='prepare':prepare(a.counter_style)
 elif a.action=='synthesize':synthesize()
 elif a.action=='select':select()
 elif a.action=='area':area()
 else:simulate(a.action)
