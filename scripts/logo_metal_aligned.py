#!/usr/bin/env python3
"""Explicit parameter variants of the design-owned proposal generator."""
import hashlib
import json
from pathlib import Path
import logo_metal_variants as design


def main():
    # Contacts may sit anywhere inside their diffusion region. Align endpoints
    # with already decoded blue/purple edges, and share source-column selectors.
    design.G_NETS['Y1']=[[2,172,4,332]]
    design.G_NETS['VDD']=[[14,108,15,204],[41,108,42,204]]
    design.G_NETS['VSS']=[[14,300,15,396],[41,300,42,396],[60,300,61,396]]
    entries=[('g_y1_aligned','格子+1：帯にそろえる','grid',['Y1']),
             ('g_power_aligned','格子+5：電源枝を共通化','grid',['VDD','VSS'])]
    design.CATALOG.extend(entries)
    for key,*_ in entries:
        design.generate(key)
        dst=design.ROOT/'experiments'/('a_metal_'+key)
        p=dst/'source_manifest.json';m=json.loads(p.read_text())
        script=Path(__file__)
        m['sha256'][str(script.relative_to(design.ROOT))]=hashlib.sha256(script.read_bytes()).hexdigest()
        m['parameter_override']={'Y1_width_screen_pixels':16,'endpoint_policy':'diffusion band edges',
                                 'power_columns_shared':True}
        p.write_text(json.dumps(m,indent=2)+'\n')


if __name__=='__main__':main()
