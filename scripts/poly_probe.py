#!/usr/bin/env python3
"""Generate and verify a pinned-TR-1um GC-over-M1 routing test array."""
from __future__ import annotations
import argparse, collections, hashlib, json, os, re, runpy, subprocess, sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
EXP=ROOT/'experiments/poly_probe'
PDK=ROOT/'tools/TR-1um'
APR=ROOT/'tools/APRtools'
sys.path.insert(0,str(APR/'apr'))
import rules
import klayout.db as db

TOP='poly_probe_array'
DEFAULT_LENGTHS=(10.0,20.0,40.0,80.0)
DEFAULT_WIDTHS=(1.0,2.0,3.0)

def deck_value(pattern: str, label: str) -> float:
    text=(PDK/'libs.tech/klayout/tech/drc/run.drc').read_text()
    matches=re.findall(pattern,text)
    if len(matches)!=1: raise RuntimeError(f'{label}: expected one live DRC value, got {matches}')
    return float(matches[0])

def um(layout, value): return int(round(value/layout.dbu))

def add_box(cell, layer, layout, x0,y0,x1,y1):
    cell.shapes(layer).insert(db.Box(um(layout,x0),um(layout,y0),um(layout,x1),um(layout,y1)))

def add_label(cell, label_layer, layout, name, x, y):
    cell.shapes(label_layer).insert(db.Text(name,db.Trans(um(layout,x),um(layout,y))))

def source_evidence():
    # These enclosures are read from the locked, live DRC deck instead of copied
    # into a design rules table. The remaining dimensions come from pinned rules.py.
    co_gc=deck_value(r"\(CO\s+\)\.drc\( enclosed\(GC \+ GR\) <\s*([0-9.]+) \)","CO-GC enclosure")
    m1_co=deck_value(r"\(M1\s+\)\.drc\(enclosing\(CO\s+\) <\s*([0-9.]+) \)","M1-CO enclosure")
    m2_v1=deck_value(r"\(M2\s+\)\.drc\(enclosing\(V1\s+\) <\s*([0-9.]+) \)","M2-V1 enclosure")
    v1_m1=deck_value(r"\(V1\s+\)\.drc\( enclosed\(M1\s+\) <\s*([0-9.]+) \)","V1-M1 enclosure")
    v1_m2=m2_v1
    return co_gc,m1_co,v1_m1,v1_m2

def local_config():
    EXP.mkdir(parents=True,exist_ok=True)
    p=EXP/'config.py'
    if not p.exists():
        p.write_text('''"""Reproducible settings for the GC/M1 crossing test array."""\nimport os\nfrom pathlib import Path\nROOT=str(Path(__file__).resolve().parents[2])\nTOP_CELL_NAME=CHIP_TOP_CELL="poly_probe_array"\nSTDCELL="v59_4"\nPROBE_LENGTHS_UM=(10.0,20.0,40.0,80.0)\nPROBE_WIDTHS_UM=(1.0,2.0,3.0)\nPROBE_ORIGIN_X_UM=20.0\nPROBE_ORIGIN_Y_UM=20.0\nPROBE_PITCH_Y_UM=20.0\nDEVICE_PROBE_ORIGIN_X_UM=20.0\nDEVICE_PROBE_ORIGIN_Y_UM=1200.0\nDEVICE_PROBE_PITCH_Y_UM=90.0\ndef pdk_root():\n    return os.environ.get("TR1UM_PDK", str(Path(ROOT)/"tools/TR-1um"))\ndef show(path):\n    return str(path)\n''')
    return runpy.run_path(str(p))

def build(cfg):
    EXP.mkdir(parents=True,exist_ok=True)
    (EXP/'build').mkdir(exist_ok=True)
    lengths=tuple(cfg['PROBE_LENGTHS_UM']); widths=tuple(cfg['PROBE_WIDTHS_UM'])
    origin_x=float(cfg['PROBE_ORIGIN_X_UM']); origin_y=float(cfg['PROBE_ORIGIN_Y_UM'])
    pitch_y=float(cfg['PROBE_PITCH_Y_UM'])
    ly=db.Layout(); ly.dbu=rules.DBU
    cell=ly.create_cell(TOP)
    gc=ly.layer(*rules.GC); co=ly.layer(*rules.CO); m1=ly.layer(*rules.M1)
    v1=ly.layer(*rules.V1); m2=ly.layer(*rules.M2)
    m1lbl=ly.layer(*rules.M1_LBL)
    co_gc,m1_co,v1_m1,v1_m2=source_evidence()
    gc_landing=rules.CO_SIZE+2*co_gc
    m1_contact_pad=rules.CO_SIZE+2*m1_co
    v1_m1_pad=rules.V1_CUT+2*v1_m1
    v1_m2_pad=rules.V1_CUT+2*v1_m2
    cases=[]
    row=0
    case_id=0
    for length in lengths:
        for width in widths:
            y=origin_y+row*pitch_y; x0=origin_x; x1=x0+length; xm=(x0+x1)/2
            aid=f'P{case_id}'
            # Continuous gate poly bridge, with only the minimum contact landing
            # enlarged at each end. No AP/AN/WN is drawn anywhere in this GDS.
            add_box(cell,gc,ly,x0,y-width/2,x1,y+width/2)
            for x in (x0,x1):
                add_box(cell,gc,ly,x-gc_landing/2,y-gc_landing/2,
                        x+gc_landing/2,y+gc_landing/2)
                add_box(cell,co,ly,x-rules.CO_SIZE/2,y-rules.CO_SIZE/2,
                        x+rules.CO_SIZE/2,y+rules.CO_SIZE/2)
                add_box(cell,m1,ly,x-m1_contact_pad/2,y-m1_contact_pad/2,
                        x+m1_contact_pad/2,y+m1_contact_pad/2)
                add_label(cell,m1lbl,ly,aid,x-0.5,y-0.5)
            # Independent M1 wire crosses the GC bridge at its midpoint. It has
            # its own label and no CO at the crossing.
            add_box(cell,m1,ly,xm-rules.M1_WIDTH_MIN/2,y-6,
                    xm+rules.M1_WIDTH_MIN/2,y+6)
            add_label(cell,m1lbl,ly,f'X{case_id}',xm,y-0.5)
            cases.append({'kind':'gc','id':case_id,'label':aid,'cross_label':f'X{case_id}',
                          'length_um':length,'width_um':width,'y_um':y,
                          'endpoint_x_um':[x0,x1],'cross_x_um':xm})
            case_id+=1; row+=1

    # Four metal-only controls. Each has the same two labeled M1 endpoints and
    # an independent M1 crossing, while M2 and two V1s provide the connection.
    for length in lengths:
        y=origin_y+row*pitch_y; x0=origin_x; x1=x0+length; xm=(x0+x1)/2
        aid=f'M{case_id}'
        m1pad=max(v1_m1_pad,m1_contact_pad)
        m2width=max(rules.M2_WIDTH_MIN,v1_m2_pad)
        add_box(cell,m2,ly,x0-v1_m2_pad/2,y-m2width/2,
                x1+v1_m2_pad/2,y+m2width/2)
        for x in (x0,x1):
            add_box(cell,v1,ly,x-rules.V1_CUT/2,y-rules.V1_CUT/2,
                    x+rules.V1_CUT/2,y+rules.V1_CUT/2)
            add_box(cell,m1,ly,x-m1pad/2,y-m1pad/2,x+m1pad/2,y+m1pad/2)
            add_label(cell,m1lbl,ly,aid,x-0.5,y-0.5)
        add_box(cell,m1,ly,xm-rules.M1_WIDTH_MIN/2,y-6,
                xm+rules.M1_WIDTH_MIN/2,y+6)
        add_label(cell,m1lbl,ly,f'X{case_id}',xm,y-0.5)
        cases.append({'kind':'m2_control','id':case_id,'label':aid,'cross_label':f'X{case_id}',
                      'length_um':length,'width_um':m2width,'y_um':y,
                      'endpoint_x_um':[x0,x1],'cross_x_um':xm})
        case_id+=1; row+=1

    gds=EXP/'poly_probe_array.gds'
    ly.write(str(gds))
    (EXP/'build/geometry.json').write_text(json.dumps({
      'top':TOP,'database_unit_um':ly.dbu,'lengths_um':lengths,'gc_widths_um':widths,
      'pitch_y_um':pitch_y,'cases':cases,'layer_counts':{
        'GC':sum(1 for _ in cell.shapes(gc).each()),'CO':sum(1 for _ in cell.shapes(co).each()),
        'M1':sum(1 for _ in cell.shapes(m1).each()),'V1':sum(1 for _ in cell.shapes(v1).each()),
        'M2':sum(1 for _ in cell.shapes(m2).each())},
      'unwanted_device_layers':{'AP':0,'AN':0,'WN':0},
      'dimensions_um':{'GC_CO_enclosure':co_gc,'M1_CO_enclosure':m1_co,
                       'V1_M1_enclosure':v1_m1,'V1_M2_enclosure':v1_m2,
                       'GC_contact_landing':gc_landing,'M1_CO_pad':m1_contact_pad,
                       'V1_M1_pad':v1_m1_pad,'V1_M2_pad':v1_m2_pad}
    },indent=2)+'\n')
    return gds

def build_device(cfg):
    """Device-connected variant with real v59_4 inverter gate endpoints."""
    lengths=tuple(cfg['PROBE_LENGTHS_UM']); widths=tuple(cfg['PROBE_WIDTHS_UM'])
    ox=float(cfg['DEVICE_PROBE_ORIGIN_X_UM']); oy=float(cfg['DEVICE_PROBE_ORIGIN_Y_UM'])
    pitch=float(cfg['DEVICE_PROBE_PITCH_Y_UM'])
    ly=db.Layout(); ly.dbu=rules.DBU
    lib=APR/'stdcell/v59_4/TR-1um_STDCELL.gds'
    ly.read(str(lib))
    cell=ly.create_cell('poly_probe_device_array')
    gc=ly.layer(*rules.GC); co=ly.layer(*rules.CO); m1=ly.layer(*rules.M1)
    v1=ly.layer(*rules.V1); m2=ly.layer(*rules.M2); m1lbl=ly.layer(*rules.M1_LBL)
    co_gc,m1_co,v1_m1,v1_m2=source_evidence()
    gc_landing=rules.CO_SIZE+2*co_gc
    m1pad=max(rules.CO_SIZE+2*m1_co,rules.V1_CUT+2*v1_m1)
    m2width=max(rules.M2_WIDTH_MIN,rules.V1_CUT+2*v1_m2)
    inv=ly.cell('INV_X1')
    if inv is None: raise RuntimeError('INV_X1 missing from pinned v59_4 GDS')
    cases=[]; row=0; ci=0
    for length in lengths:
      for width in widths:
        y=oy+row*pitch; x0=ox; x1=x0+length; xm=(x0+x1)/2
        add_box(cell,gc,ly,x0,y-width/2,x1,y+width/2)
        for x in (x0,x1):
          add_box(cell,gc,ly,x-gc_landing/2,y-gc_landing/2,x+gc_landing/2,y+gc_landing/2)
          add_box(cell,co,ly,x-rules.CO_SIZE/2,y-rules.CO_SIZE/2,x+rules.CO_SIZE/2,y+rules.CO_SIZE/2)
          add_box(cell,m1,ly,x-m1pad/2,y-m1pad/2,x+m1pad/2,y+m1pad/2)
        # Place both gate receivers beyond the ends of the coupon. Their A pins
        # connect through M2/V1 to the GC/CO/M1 landing stack.
        left_origin=x0-25.2; right_origin=x1+22.4
        cell.insert(db.CellInstArray(inv.cell_index(),db.Trans(db.Point(um(ly,left_origin),um(ly,y-29.6)))))
        cell.insert(db.CellInstArray(inv.cell_index(),db.Trans(db.Point(um(ly,right_origin),um(ly,y-29.6)))))
        a_left=left_origin+2.6; a_right=right_origin+2.6
        via_left=x0-4.2; via_right=x1+4.2; via_y=y
        for x,via_x in ((x0,via_left),(x1,via_right)):
          # V1 must sit clear of GC and CO. A short M1 spur takes it outside
          # the forbidden overlap zone while staying short of the crossing wire.
          add_box(cell,m1,ly,min(x,via_x)-m1pad/2,y-m1pad/2,
                  max(x,via_x)+m1pad/2,y+m1pad/2)
          add_box(cell,m1,ly,via_x-m1pad/2,y-m1pad/2,via_x+m1pad/2,y+m1pad/2)
          add_box(cell,v1,ly,via_x-rules.V1_CUT/2,via_y-rules.V1_CUT/2,
                  via_x+rules.V1_CUT/2,via_y+rules.V1_CUT/2)
        for via_x,a in ((via_left,a_left),(via_right,a_right)):
          add_box(cell,m2,ly,min(via_x,a)-(rules.V1_CUT/2+v1_m2),y-m2width/2,
                  max(via_x,a)+(rules.V1_CUT/2+v1_m2),y+m2width/2)
        add_box(cell,m1,ly,xm-rules.M1_WIDTH_MIN/2,y-6,xm+rules.M1_WIDTH_MIN/2,y+6)
        add_label(cell,m1lbl,ly,f'DP{ci}',x0-0.5,y-0.5)
        add_label(cell,m1lbl,ly,f'DP{ci}',x1-0.5,y-0.5)
        add_label(cell,m1lbl,ly,f'DX{ci}',xm,y-0.5)
        cases.append({'kind':'gc_device','id':ci,'label':f'DP{ci}','cross_label':f'DX{ci}',
          'length_um':length,'width_um':width,'y_um':y,'endpoint_x_um':[x0,x1],
          'cross_x_um':xm,'inv_instances':2,'top':'poly_probe_device_array'})
        ci+=1; row+=1
    out=EXP/'poly_probe_device_array.gds'; ly.write(str(out))
    (EXP/'build/device_geometry.json').write_text(json.dumps({'top':'poly_probe_device_array',
      'database_unit_um':ly.dbu,'stdcell_gds':str(lib),'stdcell_sha256':digest(lib),
      'case_count':len(cases),'cases':cases,'expected_device_instances':2*len(cases),
      'layers':{'GC':(8,1),'CO':(11,0),'M1':(13,0),'V1':(19,0),'M2':(20,0)},
      'dims_um':{'CO_GC_enclosure':co_gc,'M1_CO_enclosure':m1_co,
        'V1_M1_enclosure':v1_m1,'V1_M2_enclosure':v1_m2,'M1_pad':m1pad,'M2_width':m2width}},indent=2)+'\n')
    return out,cases

def named_nets(gds, top=TOP):
    # Use the current pinned APRtools KLayout extractor; it reproduces the PDK
    # layer connect graph (GC-CO-M1 and V1-M2) and attaches M1 text labels.
    import klayout_extract
    l2n=klayout_extract.build(str(gds),top)
    nl=l2n.netlist(); circuit=nl.circuit_by_name(top)
    if circuit is None: raise RuntimeError('KLayout extractor did not create the probe circuit')
    nets=list(circuit.each_net())
    by_name=collections.defaultdict(list)
    for net in nets: by_name[net.name].append(net)
    device_count=sum(sum(1 for _ in c.each_device()) for c in nl.each_circuit())
    return nets,by_name,device_count

def check_device_connectivity(gds,cases):
    import klayout_extract
    top='poly_probe_device_array'
    nets,by_name,device_count=named_nets(gds,top)
    missing=[]; shorted=[]
    for c in cases:
      if len(by_name.get(c['label'],[]))!=1: missing.append(c['label'])
      if len(by_name.get(c['cross_label'],[]))!=1: missing.append(c['cross_label'])
      elif by_name[c['label']][0]==by_name[c['cross_label']][0]: shorted.append(c['id'])
    # The pinned extractor represents repeated cell instances as subcircuits;
    # the INV_X1 master contains two extracted MOS devices.
    l2n=klayout_extract.build(str(gds),top); nl=l2n.netlist(); c=nl.circuit_by_name(top)
    inst_count=sum(1 for _ in c.each_subcircuit())
    master=nl.circuit_by_name('INV_X1')
    master_devices=sum(1 for _ in master.each_device()) if master else 0
    pin_nets=collections.defaultdict(list); bad_instances=[]
    for inst in c.each_subcircuit():
      ref=inst.circuit_ref()
      if ref.name!='INV_X1': bad_instances.append(ref.name); continue
      for pin in ref.each_pin():
        net=inst.net_for_pin(pin.id())
        if pin.name() in ('A','Y','vss'):
          pin_nets[pin.name()].append(net.name if net else None)
    gate_pin_counts={label:pin_nets['A'].count(label) for label in (x['label'] for x in cases)}
    c0=cases[0];x0,x1=c0['endpoint_x_um'];y=c0['y_um'];w=c0['width_um']
    opened=EXP/'build/device_negative_open.gds'
    mutate_shape(gds,opened,(8,1),(x0,y-w/2,x1,y+w/2),top=top)
    _,open_names,_=named_nets(opened,top)
    open_ok=(len(open_names.get(c0['label'],[]))==2 and len(open_names.get(c0['cross_label'],[]))==1)
    xm=c0['cross_x_um'];shorted_gds=EXP/'build/device_negative_short.gds'
    mutate_shape(gds,shorted_gds,(11,0),(xm-0.5,y-0.5,xm+0.5,y+0.5),insert=True,top=top)
    _,short_names,_=named_nets(shorted_gds,top)
    short_ok=(len(short_names.get(c0['label']+','+c0['cross_label'],[]))==1)
    if (missing or shorted or not open_ok or not short_ok or bad_instances or
        inst_count!=2*len(cases) or master_devices!=2 or
        any(v!=2 for v in gate_pin_counts.values())):
      raise RuntimeError(f'device connectivity failure: missing={missing},shorted={shorted},open={open_ok},short={short_ok},instances={inst_count},INV_MOS={master_devices},A_pin_nets={gate_pin_counts},bad_inst={bad_instances}')
    return {'status':'PASS','net_count':len(nets),'top_level_inv_instances':inst_count,
      'inv_master_mos_devices':master_devices,'case_count':len(cases),
      'inv_A_gate_pins_connected_per_bridge_net':gate_pin_counts,
      'distinct_bridge_and_crossing_nets':len(cases),
      'negative_controls':{'gc_open_creates_two_same_name_endpoint_nets':open_ok,
        'CO_at_crossing_merges_bridge_and_crossing_nets':short_ok},
      'method':'APRtools klayout_extract.py / LayoutToNetlist including hierarchical v59_4 INV_X1 devices.'}

def mutate_shape(gds,out,layer_pair,box_um,insert=False,top=TOP):
    ly=db.Layout();ly.read(str(gds));cell=ly.cell(top);li=ly.layer(*layer_pair)
    scale=1/ly.dbu
    target=tuple(int(round(v*scale)) for v in box_um)
    found=False
    if insert:
        cell.shapes(li).insert(db.Box(*target));found=True
    else:
        for shape in list(cell.shapes(li).each()):
            bb=shape.bbox()
            if (bb.left,bb.bottom,bb.right,bb.top)==target:
                cell.shapes(li).erase(shape);found=True;break
    if not found: raise RuntimeError(f'negative-control shape not found: {layer_pair} {box_um}')
    ly.write(str(out))
    return out

def check_connectivity(gds,cases):
    nets,by_name,device_count=named_nets(gds)
    expected_labels={c['label'] for c in cases}|{c['cross_label'] for c in cases}
    missing=sorted(expected_labels-set(by_name))
    duplicates={k:len(v) for k,v in by_name.items() if k in expected_labels and len(v)!=1}
    shorted=[]
    for c in cases:
        a=by_name.get(c['label'],[]); x=by_name.get(c['cross_label'],[])
        if len(a)==1 and len(x)==1 and a[0]==x[0]: shorted.append(c['id'])
    if missing or duplicates or shorted or device_count:
        raise RuntimeError(f'connectivity failure: missing={missing}, duplicate={duplicates}, '
                           f'shorted={shorted}, devices={device_count}')

    # Negative opens prove each named end pair really depends on its jumper.
    gc_case=next(c for c in cases if c['kind']=='gc')
    x0,x1=gc_case['endpoint_x_um']; y=gc_case['y_um']; w=gc_case['width_um']
    open_gc=EXP/'build/negative_open_gc.gds'
    mutate_shape(gds,open_gc,(8,1),(x0,y-w/2,x1,y+w/2))
    _,gc_open,_=named_nets(open_gc)
    gc_open_ok=(len(gc_open[gc_case['label']])==2 and len(gc_open[gc_case['cross_label']])==1)
    control=next(c for c in cases if c['kind']=='m2_control')
    x0,x1=control['endpoint_x_um']; y=control['y_um']; w=control['width_um']
    co_gc,m1_co,v1_m1,v1_m2=source_evidence()
    control_bridge=(x0-(rules.V1_CUT+2*v1_m2)/2,y-w/2,
                    x1+(rules.V1_CUT+2*v1_m2)/2,y+w/2)
    open_metal=EXP/'build/negative_open_m2.gds'
    mutate_shape(gds,open_metal,(20,0),control_bridge)
    _,metal_open,_=named_nets(open_metal)
    metal_open_ok=(len(metal_open[control['label']])==2 and len(metal_open[control['cross_label']])==1)
    if not gc_open_ok or not metal_open_ok:
        raise RuntimeError(f'negative open control missed: GC={gc_open_ok}, M2={metal_open_ok}')

    # One deliberate CO at the GC/M1 crossing must short P0 to X0 in extraction.
    short_case=gc_case;x0,x1=short_case['endpoint_x_um'];y=short_case['y_um'];xm=(x0+x1)/2
    short_gds=EXP/'build/negative_short_gc_m1.gds'
    mutate_shape(gds,short_gds,(11,0),(xm-0.5,y-0.5,xm+0.5,y+0.5),insert=True)
    _,short_nets,_=named_nets(short_gds)
    merged_name=short_case['label']+','+short_case['cross_label']
    short_ok=(len(short_nets.get(merged_name,[]))==1)
    if not short_ok: raise RuntimeError('negative short control did not merge GC and crossing M1 nets')

    return {'status':'PASS','net_count':len(nets),'device_count':device_count,
      'case_count':len(cases),'distinct_endpoint_and_crossing_nets':len(cases),
      'endpoint_nets':sorted(c['label'] for c in cases),
      'crossing_nets':sorted(c['cross_label'] for c in cases),
      'negative_controls':{'gc_open_detected_by_two_same_name_nets':gc_open_ok,
                           'm2_open_detected_by_two_same_name_nets':metal_open_ok,
                           'gc_m1_short_detected_by_merged_net_label':short_ok},
      'method':'APRtools klayout_extract.py / KLayout LayoutToNetlist; live pinned PDK connection definitions.'}

def run_apr(*args):
    return subprocess.run(['python3',str(ROOT/'scripts/run_apr.py'),
      '--design-root','experiments/poly_probe',*map(str,args)],cwd=ROOT,text=True,
      stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--generate-only',action='store_true')
    a=ap.parse_args()
    # Pin verification is a build prerequisite; the APR wrapper repeats it before
    # the official DRC and extraction entry points.
    chk=subprocess.run(['python3',str(ROOT/'scripts/check_toolchain.py')],cwd=ROOT,
                       text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(chk.stdout,end='')
    if chk.returncode: return chk.returncode
    cfg=local_config()
    gds=build(cfg)
    if a.generate_only: return 0
    geometry=json.loads((EXP/'build/geometry.json').read_text())
    conn=check_connectivity(gds,geometry['cases'])
    (EXP/'build/net_connectivity.json').write_text(json.dumps(conn,indent=2)+'\n')
    device_gds,device_cases=build_device(cfg)
    device_conn=check_device_connectivity(device_gds,device_cases)
    (EXP/'build/device_net_connectivity.json').write_text(json.dumps(device_conn,indent=2)+'\n')
    out={}
    drc=run_apr('apr/drc_pdk.py',gds.relative_to(EXP),TOP,
                '-r',(EXP/'build/poly_probe_array.drc.lyrdb').resolve())
    (EXP/'build/drc.log').write_text(drc.stdout)
    print(drc.stdout,end='')
    out['drc_exit']=drc.returncode
    out['connectivity']=conn
    out['device_gds_sha256']=digest(device_gds)
    out['device_connectivity']=device_conn
    devdrc=run_apr('apr/drc_pdk.py',device_gds.relative_to(EXP),'poly_probe_device_array',
                '-r',(EXP/'build/poly_probe_device_array.drc.lyrdb').resolve())
    (EXP/'build/device_drc.log').write_text(devdrc.stdout)
    print(devdrc.stdout,end='')
    out['device_drc_exit']=devdrc.returncode
    dev_report=EXP/'build/poly_probe_device_array.drc.lyrdb'
    dev_items=[]
    if dev_report.exists():
        dev_root=ET.parse(dev_report).getroot()
        dev_items=[{'category':(it.findtext('category') or '').strip(),'value':(it.findtext('value') or '').strip()} for it in dev_root.iter('item')]
    out['device_drc_items']=dev_items
    out['device_drc_item_count']=len(dev_items)
    report=EXP/'build/poly_probe_array.drc.lyrdb'
    items=[]
    if report.exists():
        root=ET.parse(report).getroot()
        items=[{'category':(it.findtext('category') or '').strip(),
                'value':(it.findtext('value') or '').strip()} for it in root.iter('item')]
    out['drc_items']=items
    out['drc_item_count']=len(items)
    out['top']=TOP
    out['gds_sha256']=digest(gds)
    out['generator_sha256']=digest(Path(__file__))
    out['config_sha256']=digest(EXP/'config.py')
    out['evidence_sha256']={
      'toolchain.lock.json':digest(ROOT/'toolchain.lock.json'),
      'rules.py':digest(APR/'apr/rules.py'),
      'run.drc':digest(PDK/'libs.tech/klayout/tech/drc/run.drc'),
      '00_Layers.drc':digest(PDK/'libs.tech/klayout/tech/drc/00_Layers.drc'),
      '02_Device.drc':digest(PDK/'libs.tech/klayout/tech/drc/02_Device.drc'),
      '03_Electrical.drc':digest(PDK/'libs.tech/klayout/tech/drc/03_Electrical.drc'),
      '01_Extract.lvs':digest(PDK/'libs.tech/klayout/tech/lvs/01_Extract.lvs'),
      '02_Extract.lvs':digest(PDK/'libs.tech/klayout/tech/lvs/02_Extract.lvs'),
      'run_IP62.drc':digest(PDK/'libs.tech/klayout/tech/drc/run_IP62.drc'),
      'IP62/06_Check.drc':digest(PDK/'libs.tech/klayout/tech/drc/IP62/06_Check.drc'),
      'models_IP62_res_v5.lib':digest(PDK/'libs.tech/spice/models/models_IP62_res_v5.lib'),
      'v59_4_cell_gds':digest(APR/'stdcell/v59_4/TR-1um_STDCELL.gds')}
    if drc.returncode==0 and len(items)==0:
        mdp_gds=(EXP/'build/poly_probe_array_mdp.gds').resolve()
        mdp=run_apr('apr/drc_pdk.py',gds.relative_to(EXP),TOP,
                    '-r',(EXP/'build/poly_probe_array_mdp_drawing.drc.lyrdb').resolve(),
                    '--mdp','--mdp-gds',mdp_gds)
        (EXP/'build/mdp.log').write_text(mdp.stdout)
        print(mdp.stdout,end='')
        out['mdp_exit']=mdp.returncode
        mdp_report=EXP/'poly_probe_array_mdp.lyrdb'
        mdp_items=[]
        if mdp_report.exists():
            mdp_root=ET.parse(mdp_report).getroot()
            mdp_items=[{'category':(it.findtext('category') or '').strip(),
                        'value':(it.findtext('value') or '').strip()} for it in mdp_root.iter('item')]
        out['mdp_drc_items']=mdp_items
        out['mdp_drc_item_count']=len(mdp_items)
        out['mdp_gds_sha256']=digest(mdp_gds) if mdp_gds.exists() else None
    (EXP/'build/results.json').write_text(json.dumps(out,indent=2)+'\n')
    if devdrc.returncode==0 and len(dev_items)==0:
        devmdp=run_apr('apr/drc_pdk.py',device_gds.relative_to(EXP),'poly_probe_device_array',
          '-r',(EXP/'build/poly_probe_device_array_mdp_drawing.drc.lyrdb').resolve(),
          '--mdp','--mdp-gds',(EXP/'build/poly_probe_device_array_mdp.gds').resolve())
        (EXP/'build/device_mdp.log').write_text(devmdp.stdout)
        print(devmdp.stdout,end='')
        out['device_mdp_exit']=devmdp.returncode
        dev_mdp_report=EXP/'poly_probe_device_array_mdp.lyrdb'
        dev_mdp_items=[]
        if dev_mdp_report.exists():
          dev_mdp_root=ET.parse(dev_mdp_report).getroot()
          dev_mdp_items=[{'category':(it.findtext('category') or '').strip(),'value':(it.findtext('value') or '').strip()} for it in dev_mdp_root.iter('item')]
        out['device_mdp_items']=dev_mdp_items
        out['device_mdp_item_count']=len(dev_mdp_items)
        out['device_mdp_gds_sha256']=digest(EXP/'build/poly_probe_device_array_mdp.gds')
    # A successful subprocess without its required report is not evidence of
    # zero violations. Keep this explicit for future tool-wrapper changes.
    reports_present = all(p.is_file() for p in (
      report, dev_report, EXP/'poly_probe_device_array_mdp.lyrdb'))
    out['required_reports_present'] = reports_present
    out['status']={
      'wire_coupon_drawing_drc':'PASS' if drc.returncode==0 and not items else 'FAIL',
      'wire_coupon_mdp':'WARN' if out.get('mdp_drc_item_count',0)>0 else ('PASS' if out.get('mdp_exit')==0 else 'NOT_RUN'),
      'device_coupon_drawing_drc':'PASS' if devdrc.returncode==0 and not dev_items else 'FAIL',
      'device_coupon_mask_drc':'PASS' if out.get('device_mdp_exit')==0 and out.get('device_mdp_item_count')==0 else 'FAIL_OR_NOT_RUN',
      'layout_connectivity':'PASS' if conn['status']=='PASS' and device_conn['status']=='PASS' else 'FAIL'}
    (EXP/'build/results.json').write_text(json.dumps(out,indent=2)+'\n')
    return 0 if (reports_present and drc.returncode==0 and len(items)==0 and conn['status']=='PASS' and
      device_conn['status']=='PASS' and devdrc.returncode==0 and len(dev_items)==0 and
      out.get('device_mdp_exit')==0 and out.get('device_mdp_item_count')==0) else 1

if __name__=='__main__': sys.exit(main())
