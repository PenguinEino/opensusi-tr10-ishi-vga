#!/usr/bin/env python3
"""Check the reused frame pulse exhaustively, then the assembled gate animation."""
import argparse, json, re, subprocess
from pathlib import Path
import numpy as np
from letter_animation_eco import ROOT, verify, sha, cells, settings

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--design-root',type=Path,required=True);a=ap.parse_args();verify()
    d=a.design_root.resolve();st=settings(d);out=d/'build/functional';out.mkdir(exist_ok=True)
    original=ROOT/st['netlist'];cc=cells(original.read_text())
    drivers={net:(typ,pp) for typ,name,pp in cc for pin,net in pp.items() if pin in ('Y','Q','QB')}
    def support(net):
        typ,pp=drivers[net]
        if typ=='DFF':return {pp['Q']}
        return set().union(*(support(nn) for pin,nn in pp.items() if pin!='Y'))
    assert support(st['frame_end_n']) <= {f'{axis}[{i}]' for axis,n in [('h',7),('v',10)] for i in range(n)}
    h=np.arange(131072,dtype=np.uint32)%128;v=np.arange(131072,dtype=np.uint32)//128
    values={'clk':np.zeros(len(h),dtype=bool)}
    for typ,name,pp in cc:
        if typ!='DFF':continue
        q=pp['Q'];val=np.zeros(len(h),dtype=bool)
        if q.startswith('h['):val=((h>>int(q[2:-1]))&1).astype(bool)
        elif q.startswith('v['):val=((v>>int(q[2:-1]))&1).astype(bool)
        values[q]=val;values[pp['QB']]=~val
    pending=[c for c in cc if c[0]!='DFF']
    while pending:
        count=len(pending)
        for c in pending[:]:
            typ,name,pp=c
            if not all(net in values for p,net in pp.items() if p!='Y'):continue
            ins={p:values[net] for p,net in pp.items() if p!='Y'}
            if typ.startswith(('INV','BUF')):val=ins['A'] if typ.startswith('BUF') else ~ins['A']
            elif typ=='MUX2':val=np.where(ins['S'],ins['B'],ins['A'])
            elif typ.startswith(('AND','NAND')):
                val=np.logical_and.reduce(list(ins.values()));val=~val if typ.startswith('NAND') else val
            elif typ.startswith(('OR','NOR')):
                val=np.logical_or.reduce(list(ins.values()));val=~val if typ.startswith('NOR') else val
            elif typ in ('XOR2','XNOR2'):
                val=ins['A']^ins['B'];val=~val if typ=='XNOR2' else val
            else:raise ValueError(typ)
            values[pp['Y']]=val;pending.remove(c)
        assert len(pending)<count
    assert np.array_equal(values[st['frame_end_n']],~((h==100)&(v==0)))
    net=d/'out/ishi_vga_core_pnr.v';mapped=cells(net.read_text());init=[];state_init=[]
    for typ,name,pp in mapped:
        if typ!='DFF':continue
        q=pp['Q']
        if q.startswith('h['):value=(71>>int(q[2:-1]))&1
        elif q.startswith('v['):value=(500>>int(q[2:-1]))&1
        elif q.startswith('anim_phase_') or q in ['r','g','b','hsync','vsync']:value=0
        else:raise ValueError(q)
        init.append(f'dut.{name}.q=1\'b{value};')
        if q.startswith('h['):state_value="1'b"+str((100>>int(q[2:-1]))&1)
        elif q.startswith('anim_phase_'):state_value=f'seed[{int(q.split("_")[-2])}]'
        else:state_value="1'b0"
        state_init.append(f'dut.{name}.q={state_value};')
    assert len(init)==29
    tb='''`timescale 1ns/1ps
module tb;
reg clk=0;
always #158.730158730159 clk=~clk;
wire [4:0] observed,rtl_observed;
rtl_core rtl(.clk(clk),.vsync(rtl_observed[4]),.hsync(rtl_observed[3]),.r(rtl_observed[2]),.g(rtl_observed[1]),.b(rtl_observed[0]));
ishi_vga_core dut(.clk(clk),.vsync(observed[4]),.hsync(observed[3]),.r(observed[2]),.g(observed[1]),.b(observed[0]));
reg [4:0] reference [0:52499];
reg [4:0] expected;
integer frame,tick,x,fd,seed,next_phase;
initial begin
 INIT
 rtl.h=71;rtl.v=500;rtl.phase=0;rtl.r=0;rtl.g=0;rtl.b=0;rtl.hsync=0;rtl.vsync=0;
 $readmemh("REFERENCE",reference);
 fd=$fopen("observed.bin","wb");
 for(frame=0;frame<128;frame=frame+1) begin
  for(tick=0;tick<52500;tick=tick+1) begin
   @(posedge clk);#80;
   x=tick%100;expected=reference[tick];
   if(expected[2:0]==4 && frame<64 && x>=8 && x<72 && ((x-8)/16)==frame/16) expected[2:0]=7;
   if(observed !== expected || rtl_observed !== expected) $fatal(1,"frame=%0d tick=%0d got=%h expected=%h",frame,tick,observed,expected);
   if((frame%16)==0 && frame<=64) $fwrite(fd,"%c",observed);
   @(negedge clk);#1;
  end
  if({dut.anim_phase_6_,dut.anim_phase_5_,dut.anim_phase_4_,dut.anim_phase_3_,dut.anim_phase_2_,dut.anim_phase_1_,dut.anim_phase_0_} !== ((frame+1)%128))
   $fatal(1,"phase transition at frame %0d",frame);
 end
 $fclose(fd);
 for(seed=0;seed<128;seed=seed+1) begin
  STATE_INIT
  rtl.h=100;rtl.v=0;rtl.phase=seed;
  next_phase=(seed+1)%128;
  @(posedge clk);#80;
  if({dut.anim_phase_6_,dut.anim_phase_5_,dut.anim_phase_4_,dut.anim_phase_3_,dut.anim_phase_2_,dut.anim_phase_1_,dut.anim_phase_0_} !== next_phase || rtl.phase !== next_phase)
   $fatal(1,"initial phase state %0d",seed);
  @(negedge clk);#1;
 end
 $display("PASS: 128 continuous RTL/gate frames, 6720000 RGB/HS/VS ticks, all 128 phase transitions, all 128 binary phase initial states; stage lengths 16/16/16/16/64 frames");
 $finish;
end
initial begin #2300000000;$fatal(1,"watchdog");end
endmodule
'''.replace('STATE_INIT','\n'.join(state_init)).replace('INIT','\n'.join(init)).replace('REFERENCE',str(ROOT/'designs/grid_power/tests/expected_frame.hex'))
    (out/'tb.v').write_text(tb);model=d/st['patch_dir']/'build/tr1um_cells.v';exe=out/'sim.vvp'
    rtl=out/'rtl_core.v';rtl.write_text((d/'ishi_vga_core.v').read_text().replace('module ishi_vga_core','module rtl_core',1))
    with (out/'compile.log').open('w') as f:subprocess.run([str(ROOT/'.tools/bin/iverilog'),'-g2012','-s','tb','-o',str(exe),str(out/'tb.v'),str(net),str(model),str(rtl),str(d/'ishi_logo.v')],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
    with (out/'simulation.log').open('w') as f:subprocess.run([str(ROOT/'.tools/bin/vvp'),str(exe)],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
    log=(out/'simulation.log').read_text();assert 'PASS:' in log
    reference=ROOT/'designs/grid_power/tests/expected_frame.hex'
    base=np.array([int(v,16) for v in reference.read_text().split()],dtype=np.uint8)
    x=np.arange(52500)%100;frames=[]
    for stage in range(5):
        frame=base.copy()
        if stage<4:frame[((base&7)==4)&(x>=8)&(x<72)&(((x-8)//16)==stage)]|=3
        frames.append(frame)
    assert (out/'observed.bin').read_bytes()==np.concatenate(frames).tobytes()
    result={'status':'PASS','decoder_states':131072,'continuous_frames':128,'ticks':6720000,'counter_transitions_checked':128,'binary_phase_initial_states_checked':128,'max_frames_to_valid_phase_cycle':0,'stage_frames':[16,16,16,16,64],'sampled_frame_bytes':'5 distinct stages including unchanged base logo; independently checked','model':'RTL and mapped unit-delay gate cells; fixture initialization only','hashes':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),d/'config.py',original,net,model,rtl,d/'ishi_vga_core.v',d/'ishi_logo.v',out/'tb.v',out/'simulation.log',out/'observed.bin',reference]}}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(log,flush=True)

if __name__=='__main__':main()
