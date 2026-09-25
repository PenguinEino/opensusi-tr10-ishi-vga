#!/usr/bin/env python3
"""Controlled, isolated metal-only repair experiments for the desc5 route.

The input GDS and its maps are copied from experiments/phys_desc5 and are
never edited.  This script begins with a full GDS hierarchy connectivity scan
and a same-layer router-box ownership audit; candidate edits must be written
to a separate checkpoint and pass independent full-GDS DRC/connectivity.
"""
import argparse
import ast
import hashlib
import itertools
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "experiments/metal_repair"

def load_design_settings():
    tree=ast.parse((DESIGN/"config.py").read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(
            isinstance(target,ast.Name) and target.id=="METAL_REPAIR_SETTINGS"
            for target in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError("config.py must define literal METAL_REPAIR_SETTINGS")


SETTINGS=load_design_settings()
GDS=DESIGN/SETTINGS["input_gds"]
PINS=DESIGN/SETTINGS["actual_pin_map"]
SHAPES=DESIGN/SETTINGS["input_net_shapes"]
sys.path.insert(0, str(ROOT / "tools/APRtools/apr"))
import rules as apr_rules
LAYERS = {"M1": apr_rules.M1, "V1": apr_rules.V1, "M2": apr_rules.M2}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unite(parent, a, b):
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb


def all_polys(top, layer_index):
    return list(__import__("klayout.db", fromlist=["Region"]).Region(
        top.begin_shapes_rec(layer_index)).merged().each())


def point_component(polys, db, x_um, y_um, dbu):
    xi, yi = int(round(x_um / dbu)), int(round(y_um / dbu))
    probe = db.Region(db.Box(xi - 2, yi - 2, xi + 2, yi + 2))
    for i, poly in enumerate(polys):
        b = poly.bbox()
        if b.left - 5 <= xi <= b.right + 5 and b.bottom - 5 <= yi <= b.top + 5:
            if probe.interacting(db.Region(poly)).count() > 0:
                return i
    return None


def box_um(box, dbu):
    return [round(box.left * dbu, 3), round(box.bottom * dbu, 3),
            round(box.right * dbu, 3), round(box.top * dbu, 3)]


def diagnose(gds_path=GDS, pin_path=PINS, shape_path=SHAPES, report_path=None):
    import klayout.db as db
    gds_path=Path(gds_path); pin_path=Path(pin_path); shape_path=Path(shape_path)
    pins = json.loads(pin_path.read_text())
    net_shapes = json.loads(shape_path.read_text())
    ly = db.Layout(); ly.read(str(gds_path)); top = ly.cell("ishi_vga_core")
    idx = {n: ly.layer(*pair) for n, pair in LAYERS.items()}
    polys = {n: all_polys(top, idx[n]) for n in ("M1", "M2")}
    vias = list(db.Region(top.begin_shapes_rec(idx["V1"])).merged().each())
    parent = {}
    for name in ("M1", "M2"):
        for i in range(len(polys[name])):
            parent[(name, i)] = (name, i)
    for via in vias:
        vb = via.bbox(); vreg = db.Region(via)
        hits = {}
        for name in ("M1", "M2"):
            hits[name] = [i for i, p in enumerate(polys[name])
                          if (p.bbox().overlaps(vb) or p.bbox().touches(vb))
                          and vreg.interacting(db.Region(p)).count()]
        for name in ("M1", "M2"):
            for i in hits[name][1:]: unite(parent, (name, hits[name][0]), (name, i))
        if hits["M1"] and hits["M2"]:
            for i in hits["M1"]:
                for j in hits["M2"]: unite(parent, ("M1", i), ("M2", j))

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    components = defaultdict(lambda: {"nets": defaultdict(list), "nodes": []})
    for n in ("M1", "M2"):
        for i, p in enumerate(polys[n]): components[find((n, i))]["nodes"].append((n, i))
    owner = {}
    for net, netpins in pins.items():
        for inst, pin, x, y in netpins:
            loc = point_component(polys["M1"], db, x, y, ly.dbu)
            layer = "M1"
            if loc is None:
                loc = point_component(polys["M2"], db, x, y, ly.dbu); layer = "M2"
            if loc is None:
                components[None]["nets"][net].append({"inst": inst, "pin": pin,
                                                        "xy_um": [x, y], "missing": True})
                continue
            root = find((layer, loc)); owner.setdefault(root, set()).add(net)
            components[root]["nets"][net].append({"inst": inst, "pin": pin,
                                                  "xy_um": [round(x,3), round(y,3)],
                                                  "located_layer": layer, "component": loc})

    conflicts=[]
    for root, data in components.items():
        nets=sorted(data["nets"])
        if len(nets)<2: continue
        bbs=[polys[n][i].bbox() for n,i in data["nodes"]]
        if bbs:
            union_box=db.Box(min(b.left for b in bbs),min(b.bottom for b in bbs),
                             max(b.right for b in bbs),max(b.top for b in bbs))
            bbox=box_um(union_box,ly.dbu)
        else: bbox=None
        conflicts.append({"nets":nets,"bbox_um":bbox,
                          "terminal_pins":dict(data["nets"]),
                          "geometry_components":len(data["nodes"]),
                          "component_layers":{n:sum(1 for layer,_ in data["nodes"] if layer==n)
                                              for n in ("M1","M2")}})

    # Report exact direct overlap/touch coordinates among router-owned boxes.
    # This intentionally excludes cross-layer coincidence: V1 cells are not
    # represented in net_shapes.json and the full GDS graph remains the oracle.
    direct=[]
    pairs={pair for c in conflicts for pair in itertools.combinations(sorted(c["nets"]),2)}
    for na,nb in sorted(pairs):
        for ia,a in enumerate(net_shapes.get(na,[])):
            for ib,b in enumerate(net_shapes.get(nb,[])):
                if a[0]!=b[0]: continue
                ax0,ay0,ax1,ay1=map(float,a[1:]); bx0,by0,bx1,by1=map(float,b[1:])
                x0=max(ax0,bx0); y0=max(ay0,by0); x1=min(ax1,bx1); y1=min(ay1,by1)
                if x0 <= x1+1e-6 and y0 <= y1+1e-6:
                    direct.append({"nets":[na,nb],"layer":a[0],"shape_indices":[ia,ib],
                                   "intersection_or_touch_um":[round(x0,3),round(y0,3),round(x1,3),round(y1,3)],
                                   "a":a,"b":b})
    dbbox=top.dbbox()
    report={"source_gds_sha256":sha(gds_path),"source_pin_map_sha256":sha(pin_path),
            "source_net_shapes_sha256":sha(shape_path),"top_bbox_um":[round(dbbox.left,3),round(dbbox.bottom,3),round(dbbox.right,3),round(dbbox.top,3)],
            "hierarchy_cells":ly.cells(),"merged_components":{"M1":len(polys["M1"]),
            "M2":len(polys["M2"]),"V1":len(vias)},
            "missing_pin_count":sum(1 for c in components.values() for ns in c["nets"].values()
                                     for pin in ns if pin.get("missing")),
            "cross_net_components":conflicts,"direct_router_shape_overlaps":direct}
    out=Path(report_path) if report_path else DESIGN/"build/conflict_report.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(f"cross-net components={len(conflicts)} direct same-layer shape overlaps/touches={len(direct)} missing pins={report['missing_pin_count']}")
    for c in conflicts[:12]:
        points=[]
        for net, term in c['terminal_pins'].items():
            points.extend(f"{net}:{p['inst']}.{p['pin']}@{tuple(p['xy_um'])}" for p in term[:2])
        print(f"nets={c['nets']} bbox={c['bbox_um']} layers={c['component_layers']} terminals={'; '.join(points)}")
    print(f"report={out.resolve().relative_to(ROOT)}")
    return report


def _dbu(value_um, dbu):
    return int(round(value_um / dbu))


def repair_junction(track_y):
    """Move only net _246_'s internal M1 merge and its two branch vias."""
    import klayout.db as db
    src_ly=db.Layout(); src_ly.read(str(GDS)); top=src_ly.cell("ishi_vga_core")
    dbu=src_ly.dbu
    old_y=708.0
    x_left,x_right=1061.1,1071.9
    track_y=round(float(track_y),3)
    if not (old_y < track_y < 853.8):
        raise RuntimeError("junction track must remain between old anchor and upper branch endpoint")
    m1i=src_ly.layer(*LAYERS["M1"]); m2i=src_ly.layer(*LAYERS["M2"])

    def exact_box(b, coords):
        want=[_dbu(v,dbu) for v in coords]
        return [b.left,b.bottom,b.right,b.top]==want

    def delete_box(layer, coords, label):
        cellsh=top.shapes(layer)
        found=[s for s in cellsh.each() if s.is_box() and exact_box(s.box,coords)]
        if len(found)!=1:
            raise RuntimeError(f"expected exactly one {label} top-level box, found {len(found)}")
        cellsh.erase(found[0]); return len(found)

    # The old branch vias are electrical junctions, not real cell pins.
    old_vias=[]; via_cell=None
    for inst in list(top.each_inst()):
        if not inst.cell.name.startswith("via_1"):
            continue
        x=inst.trans.disp.x*dbu; y=inst.trans.disp.y*dbu
        if abs(y-old_y)<0.001 and min(abs(x-x_left),abs(x-x_right))<0.001:
            old_vias.append(inst); via_cell=inst.cell
    if len(old_vias)!=2:
        raise RuntimeError(f"expected the two _246_ branch vias at y={old_y}, got {len(old_vias)}")
    for inst in old_vias: inst.delete()

    # Remove the old junction and shorten both _246_ M2 branches to the new
    # vias. Exact boxes were matched against the source router map and GDS.
    delete_box(m1i,[x_left,old_y-0.9,x_right,old_y+0.9],"_246_ old M1 trunk")
    moved_m2=[]
    for coords in ([1070.2,old_y,1073.6,853.8],
                   [1059.4,old_y,1062.8,964.5]):
        delete_box(m2i,coords,"_246_ old M2 branch start")
        newcoords=list(coords); newcoords[1]=track_y
        top.shapes(m2i).insert(db.Box(*[_dbu(v,dbu) for v in newcoords]))
        moved_m2.append(newcoords)

    # Recreate matched via_1 PCells on the selected track and reconnect them
    # with one M1 trunk. Existing via geometry supplies all layer dimensions.
    for x in (x_left,x_right):
        top.insert(db.CellInstArray(via_cell,
            db.Trans(_dbu(x,dbu),_dbu(track_y,dbu))))
    top.shapes(m1i).insert(db.Box(_dbu(x_left,dbu),_dbu(track_y-0.9,dbu),
                                  _dbu(x_right,dbu),_dbu(track_y+0.9,dbu)))
    out_dir=DESIGN/f"build/junction_y{int(round(track_y*10))}"
    out_dir.mkdir(parents=True,exist_ok=False)
    out_gds=out_dir/"candidate.gds"; src_ly.write(str(out_gds))

    shapes=json.loads(SHAPES.read_text())
    updated=[]
    for shape in shapes["_246_"]:
        if shape[0]=="M1" and all(abs(float(a)-b)<0.001 for a,b in zip(shape[1:],[x_left,old_y-0.9,x_right,old_y+0.9])):
            continue
        if shape[0]=="M2" and (
            all(abs(float(a)-b)<0.001 for a,b in zip(shape[1:],[1070.2,old_y,1073.6,853.8])) or
            all(abs(float(a)-b)<0.001 for a,b in zip(shape[1:],[1059.4,old_y,1062.8,964.5]))):
            s=list(shape); s[2]=track_y; updated.append(s); continue
        if shape[0]=="M2" and shape[1]==1070.2 and shape[3]==1073.6 and abs(shape[2]-old_y)<0.001 and abs(shape[4]-old_y)<0.001:
            s=list(shape); s[2]=track_y; s[4]=track_y; updated.append(s); continue
        updated.append(shape)
    updated.append(["M1",x_left,track_y-0.9,x_right,track_y+0.9])
    shapes["_246_"]=updated
    out_shapes=out_dir/"net_shapes.json"; out_shapes.write_text(json.dumps(shapes,indent=1)+'\n')
    out_pins=out_dir/"actual_pin_map.json"; out_pins.write_bytes(PINS.read_bytes())
    manifest={"edit":"move _246_ internal M1 branch junction and two via_1 instances",
              "source_gds_sha256":sha(GDS),"candidate_gds_sha256":sha(out_gds),
              "source_pin_map_sha256":sha(PINS),"source_net_shapes_sha256":sha(SHAPES),
              "old_track_y_um":old_y,"new_track_y_um":track_y,
              "via_centers_um":[[x,track_y] for x in (x_left,x_right)],
              "moved_m2_segments_um":moved_m2,
              "real_cell_pins_moved":False,"source_unchanged":True}
    (out_dir/"edit_manifest.json").write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))
    return out_dir


def repair_040_detour(base_gds, base_shapes, track_x, low_y, high_y):
    """Detour only _040_'s vertical branch through row-2 FILLPRI corridor."""
    import klayout.db as db
    base_gds=Path(base_gds); base_shapes=Path(base_shapes)
    ly=db.Layout(); ly.read(str(base_gds)); top=ly.cell("ishi_vga_core"); dbu=ly.dbu
    x0,x1=974.7,float(track_x); y0,y1=float(low_y),float(high_y)
    m1i=ly.layer(*LAYERS["M1"]); m2i=ly.layer(*LAYERS["M2"])
    def dbu_i(v): return _dbu(v,dbu)
    def delbox(layer,coords,label):
        want=[dbu_i(v) for v in coords]
        matches=[s for s in top.shapes(layer).each() if s.is_box() and
                 [s.box.left,s.box.bottom,s.box.right,s.box.top]==want]
        if len(matches)!=1: raise RuntimeError(f"expected one {label} box; found {len(matches)}")
        top.shapes(layer).erase(matches[0])
    # Remove the three _040_ boxes covering its old continuous column.
    old_boxes=([973.0,870.0,976.4,964.5], [973.0,964.5,976.4,1023.9],
               [973.0,1023.9,976.4,1369.8])
    for i,b in enumerate(old_boxes): delbox(m2i,b,f"_040_ M2 segment {i}")
    # Retain the route below/above the cell row and bridge its middle via M1.
    for b in ([973.0,870.0,976.4,y0], [973.0,y1,976.4,1369.8],
              [x1-1.7,y0,x1+1.7,y1]):
        top.shapes(m2i).insert(db.Box(*[dbu_i(v) for v in b]))
    bridges=([min(x0,x1),y0-.9,max(x0,x1),y0+.9],
             [min(x0,x1),y1-.9,max(x0,x1),y1+.9])
    for b in bridges: top.shapes(m1i).insert(db.Box(*[dbu_i(v) for v in b]))
    # Reuse the pinned via_1 PCell master from the existing design.
    via_cell=None
    for inst in top.each_inst():
        if inst.cell.name.startswith("via_1"):
            via_cell=inst.cell; break
    if via_cell is None: raise RuntimeError("no existing via_1 PCell instance found")
    for y in (y0,y1):
        for x in (x0,x1):
            top.insert(db.CellInstArray(via_cell,db.Trans(dbu_i(x),dbu_i(y))))
    out_dir=DESIGN/f"build/detour_040_x{int(round(x1*10))}_y{int(round(y0*10))}_{int(round(y1*10))}"
    out_dir.mkdir(parents=True,exist_ok=False)
    out_gds=out_dir/"candidate.gds"; ly.write(str(out_gds))
    shapes=json.loads(base_shapes.read_text())
    updated=[]
    for sh in shapes["_040_"]:
        if sh[0]=="M2" and (
            all(abs(float(a)-b)<.001 for a,b in zip(sh[1:],[973.,870.,976.4,964.5])) or
            all(abs(float(a)-b)<.001 for a,b in zip(sh[1:],[973.,964.5,976.4,1023.9])) or
            all(abs(float(a)-b)<.001 for a,b in zip(sh[1:],[973.,1023.9,976.4,1369.8]))):
            continue
        updated.append(sh)
    updated.extend([["M2",973.,870.,976.4,y0],["M2",973.,y1,976.4,1369.8],
                    ["M2",x1-1.7,y0,x1+1.7,y1],
                    ["M1",min(x0,x1),y0-.9,max(x0,x1),y0+.9],
                    ["M1",min(x0,x1),y1-.9,max(x0,x1),y1+.9]])
    shapes["_040_"]=updated
    out_shapes=out_dir/"net_shapes.json"; out_shapes.write_text(json.dumps(shapes,indent=1)+'\n')
    out_pins=out_dir/"actual_pin_map.json"; out_pins.write_bytes(PINS.read_bytes())
    manifest={"edit":"_040_ M2 around row 2 using FILLPRI_r2_16 corridor",
       "base_gds":str(base_gds.resolve().relative_to(ROOT)),"base_gds_sha256":sha(base_gds),
       "candidate_gds_sha256":sha(out_gds),"base_shapes_sha256":sha(base_shapes),
       "fill_cell":"FILLPRI_r2_17","fill_x_um":[426.6,442.8],
       "alternate_m2_track_center_x_um":x1,"source_column_center_x_um":x0,
       "four_via_centers_um":[[x,y] for y in (y0,y1) for x in (x0,x1)],
       "m1_bridge_boxes_um":[list(b) for b in bridges],
       "m2_segments_um":[[973.,870.,976.4,y0],[x1-1.7,y0,x1+1.7,y1],
                        [973.,y1,976.4,1369.8]],
       "real_cell_pins_moved":False,"source_unchanged":True}
    (out_dir/"edit_manifest.json").write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2)); return out_dir


def repair_173_branch(base_gds, base_shapes, track_x, low_y, high_y):
    """Move the isolated _173_ M2 branch away from _108_'s real pin/trunk."""
    import klayout.db as db
    base_gds=Path(base_gds); base_shapes=Path(base_shapes)
    ly=db.Layout(); ly.read(str(base_gds)); top=ly.cell("ishi_vga_core"); dbu=ly.dbu
    old_x, xalt=206.2, float(track_x); ylo,yhi=float(low_y),float(high_y)
    m1i=ly.layer(*LAYERS["M1"]); m2i=ly.layer(*LAYERS["M2"])
    def dbu_i(v): return _dbu(v,dbu)
    def delbox(coords,label):
        want=[dbu_i(v) for v in coords]
        matches=[s for s in top.shapes(m2i).each() if s.is_box() and
                 [s.box.left,s.box.bottom,s.box.right,s.box.top]==want]
        if len(matches)!=1: raise RuntimeError(f"expected one {label} box; found {len(matches)}")
        top.shapes(m2i).erase(matches[0])
    # Split the original _173_ vertical branch around the full _108_ M2 span.
    for i,b in enumerate(([206.2,265.9,209.6,506.2],
                           [206.2,506.2,209.6,565.6],
                           [206.2,565.6,209.6,961.8])):
        delbox(b,f"_173_ M2 route segment {i}")
    for b in ([old_x-1.7,265.9,old_x+1.7,ylo],
              [xalt-1.7,ylo,xalt+1.7,yhi],
              [old_x-1.7,yhi,old_x+1.7,961.8]):
        top.shapes(m2i).insert(db.Box(*[dbu_i(v) for v in b]))
    bridges=([min(old_x,xalt),ylo-.9,max(old_x,xalt),ylo+.9],
             [min(old_x,xalt),yhi-.9,max(old_x,xalt),yhi+.9])
    for b in bridges: top.shapes(m1i).insert(db.Box(*[dbu_i(v) for v in b]))
    via_cell=None
    for inst in top.each_inst():
        if inst.cell.name.startswith("via_1"):
            via_cell=inst.cell; break
    if via_cell is None: raise RuntimeError("no existing via_1 PCell instance found")
    for y in (ylo,yhi):
        for x in (old_x,xalt): top.insert(db.CellInstArray(via_cell,db.Trans(dbu_i(x),dbu_i(y))))
    out_dir=DESIGN/f"build/detour_173_x{int(round(xalt*10))}_y{int(round(ylo*10))}_{int(round(yhi*10))}"
    out_dir.mkdir(parents=True,exist_ok=False)
    out_gds=out_dir/"candidate.gds"; ly.write(str(out_gds))
    shapes=json.loads(base_shapes.read_text()); updated=[]
    old_shapes=([206.2,265.9,209.6,506.2],[206.2,506.2,209.6,565.6],
                [206.2,565.6,209.6,961.8])
    for sh in shapes["_173_"]:
        if sh[0]=="M2" and any(all(abs(float(a)-b)<.001 for a,b in zip(sh[1:],old)) for old in old_shapes):
            continue
        updated.append(sh)
    updated.extend([["M2",old_x-1.7,265.9,old_x+1.7,ylo],
                    ["M2",xalt-1.7,ylo,xalt+1.7,yhi],
                    ["M2",old_x-1.7,yhi,old_x+1.7,961.8],
                    ["M1",*bridges[0]],["M1",*bridges[1]]])
    shapes["_173_"]=updated
    out_shapes=out_dir/"net_shapes.json"; out_shapes.write_text(json.dumps(shapes,indent=1)+'\n')
    out_pins=out_dir/"actual_pin_map.json"; out_pins.write_bytes(PINS.read_bytes())
    manifest={"edit":"detour _173_ M2 branch around _108_ actual-pin and route metal",
       "base_gds":str(base_gds.resolve().relative_to(ROOT)),"base_gds_sha256":sha(base_gds),
       "candidate_gds_sha256":sha(out_gds),"base_shapes_sha256":sha(base_shapes),
       "source_m2_center_x_um":old_x,"alternate_m2_center_x_um":xalt,
       "filler_corridor":"FILL2_r1_22","filler_box_x_um":[415.8,426.6],
       "four_via_centers_um":[[x,y] for y in (ylo,yhi) for x in (old_x,xalt)],
       "m1_bridge_boxes_um":[list(b) for b in bridges],
       "m2_segments_um":[[old_x-1.7,265.9,old_x+1.7,ylo],
                         [xalt-1.7,ylo,xalt+1.7,yhi],
                         [old_x-1.7,yhi,old_x+1.7,961.8]],
       "real_cell_pins_moved":False,"source_unchanged":True}
    (out_dir/"edit_manifest.json").write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2)); return out_dir


def run_checker(which, gds_path, pin_path=PINS):
    gds_path=Path(gds_path)
    if not gds_path.is_absolute(): gds_path=ROOT/gds_path
    gds_arg=str(gds_path.resolve().relative_to(DESIGN.resolve()))
    if which == "connectivity":
        entry="apr/verify_connectivity_m1m2.py"
        pin_path=Path(pin_path)
        if not pin_path.is_absolute(): pin_path=ROOT/pin_path
        pin_arg=str(pin_path.resolve().relative_to(DESIGN.resolve()))
        args=[gds_arg,pin_arg,"0","5000","1801.2"]
    elif which == "drc":
        entry="apr/drc_check.py"; args=[gds_arg,"ishi_vga_core"]
    else: raise ValueError(which)
    log=DESIGN/f"build/{gds_path.stem}_{which}.log"
    with log.open('w') as f:
        rc=subprocess.call(["python3",str(ROOT/"scripts/run_apr.py"),"--design-root",
            str(DESIGN.relative_to(ROOT)),entry,*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    print(f"{which}: rc={rc}, log={log.relative_to(ROOT)}")
    return rc


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("command",choices=["diagnose","check-connectivity","check-drc","repair-junction","repair-040","repair-173"])
    ap.add_argument("--gds",default=str(GDS)); ap.add_argument("--pins",default=str(PINS));
    ap.add_argument("--shapes",default=str(SHAPES)); ap.add_argument("--report")
    ap.add_argument("--track-y",type=float,default=SETTINGS["junction"]["track_y_um"])
    ap.add_argument("--base-gds",default=str(DESIGN/SETTINGS["repair_040"]["base_gds"]))
    ap.add_argument("--base-shapes",default=str(DESIGN/SETTINGS["repair_040"]["base_shapes"]))
    ap.add_argument("--track-x",type=float,default=SETTINGS["repair_040"]["track_x_um"])
    ap.add_argument("--low-y",type=float,default=SETTINGS["repair_040"]["low_y_um"])
    ap.add_argument("--high-y",type=float,default=SETTINGS["repair_040"]["high_y_um"])
    ap.add_argument("--base-gds-173",default=str(DESIGN/SETTINGS["repair_173"]["base_gds"]))
    ap.add_argument("--base-shapes-173",default=str(DESIGN/SETTINGS["repair_173"]["base_shapes"]))
    ap.add_argument("--track-x-173",type=float,default=SETTINGS["repair_173"]["track_x_um"])
    ap.add_argument("--low-y-173",type=float,default=SETTINGS["repair_173"]["low_y_um"])
    ap.add_argument("--high-y-173",type=float,default=SETTINGS["repair_173"]["high_y_um"])
    a=ap.parse_args()
    if a.command=="diagnose": diagnose(a.gds,a.pins,a.shapes,a.report)
    elif a.command=="check-connectivity": run_checker("connectivity",a.gds,a.pins)
    elif a.command=="check-drc": run_checker("drc",a.gds,a.pins)
    elif a.command=="repair-junction": repair_junction(a.track_y)
    elif a.command=="repair-040": repair_040_detour(a.base_gds,a.base_shapes,a.track_x,a.low_y,a.high_y)
    elif a.command=="repair-173": repair_173_branch(a.base_gds_173,a.base_shapes_173,a.track_x_173,a.low_y_173,a.high_y_173)

if __name__=="__main__": main()
