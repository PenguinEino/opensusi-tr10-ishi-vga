#!/usr/bin/env python3
"""Generate four reverse-horizontal-counter variants of the current B design."""
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE_CORE=(ROOT/'rtl/ishi_vga_core.v').read_text()
BASE_LOGO=(ROOT/'rtl/ishi_logo.v').read_text()
BASE_CONFIG=(ROOT/'config.py').read_text()

def q_interval(a,b,start):
    """Translate q in [a,b) to the cyclic internal h interval."""
    lo=(start-b+1)%256
    hi=(start-a+1)%256
    if lo < hi:
        return f"((h >= 8'd{lo}) && (h < 8'd{hi}))"
    if hi == 0:
        return f"(h >= 8'd{lo})"
    return f"((h >= 8'd{lo}) || (h < 8'd{hi}))"

def translate_logo(start):
    n=0
    pattern=re.compile(r"\(h >= 8'd(\d+)\) && \(h < 8'd(\d+)\)")
    def sub(m):
        nonlocal n
        n+=1
        return q_interval(int(m.group(1)),int(m.group(2)),start)
    result=pattern.sub(sub,BASE_LOGO)
    assert n==21, f'expected 21 logo h ranges, replaced {n}'
    return result

def translate_core(start):
    core=BASE_CORE
    replacements=[
        ("h <= 8'd0;",f"h <= 8'd{start};",2),
        ("h == 8'd199",f"h == 8'd{(start-199)%256}",1),
        ("h <= h + 8'd1;","h <= h - 8'd1;",1),
        ("(h < 8'd160)",q_interval(0,160,start),1),
        ("((h >= 8'd164) && (h < 8'd188))",q_interval(164,188,start),1),
    ]
    for old,new,count in replacements:
        actual=core.count(old)
        assert actual==count, f'expected {count} occurrences of {old!r}, found {actual}'
        core=core.replace(old,new)
    return core

def write(start):
    name=f'descending_h{start}'
    d=ROOT/'experiments'/name
    d.mkdir(parents=True,exist_ok=True)
    for folder in ('build','tests'): (d/folder).mkdir(exist_ok=True)
    expected=d/'tests/expected_frame.hex'
    if not expected.exists(): expected.symlink_to('../../../tests/expected_frame.hex')
    (d/'ishi_vga_core.v').write_text(translate_core(start))
    (d/'ishi_logo.v').write_text(translate_logo(start))
    config=BASE_CONFIG.replace("SYN_RTL = ['rtl/ishi_vga_core.v', 'rtl/ishi_logo.v']",
                               "SYN_RTL = ['ishi_vga_core.v', 'ishi_logo.v']")
    config=config.replace("SYN_TB_RTL = ['tests/tb_vga.v']",
                          f"SYN_TB_RTL = ['{ROOT}/tests/tb_vga.v']")
    config=config.replace("SYN_TB_NET = ['tests/tb_vga.v']",
                          f"SYN_TB_NET = ['{ROOT}/tests/tb_vga.v']")
    (d/'config.py').write_text(config)
    return d

def write_h79_v500():
    """One combined candidate: h start 79, vertical counter offset 500."""
    d=write(79)
    d=ROOT/'experiments'/'descending_h79_v500'
    d.mkdir(parents=True,exist_ok=True)
    for folder in ('build','tests'): (d/folder).mkdir(exist_ok=True)
    expected=d/'tests/expected_frame.hex'
    if not expected.exists(): expected.symlink_to('../../../tests/expected_frame.hex')
    core=translate_core(79)
    replacements=[
        ("v <= 10'd0;","v <= 10'd500;",1),
        ("v <= (v == 10'd524) ? 10'd0 : v + 10'd1;",
         "v <= (v == 10'd0) ? 10'd500 : v + 10'd1;",1),
        ("(v < 10'd480)","((v >= 10'd500) && (v < 10'd980))",1),
        ("((v >= 10'd490) && (v < 10'd492))",
         "((v >= 10'd990) && (v < 10'd992))",1),
    ]
    for old,new,count in replacements:
        actual=core.count(old)
        assert actual==count, f'expected {count} occurrences of {old!r}, found {actual}'
        core=core.replace(old,new)
    (d/'ishi_vga_core.v').write_text(core)
    logo=translate_logo(79)
    n=0
    pat=re.compile(r"\(y >= 8'd(\d+)\) && \(y < 8'd(\d+)\)")
    def shift_y(m):
        nonlocal n
        n+=1
        lo,hi=int(m.group(1))+125,int(m.group(2))+125
        assert hi<=256, f'y range [{lo},{hi}) needs wrap handling'
        return f"((y >= 8'd{lo}) && (y < 8'd{hi}))"
    logo=pat.sub(shift_y,logo)
    assert n==21, f'expected 21 logo y ranges, replaced {n}'
    (d/'ishi_logo.v').write_text(logo)
    config=BASE_CONFIG.replace("SYN_RTL = ['rtl/ishi_vga_core.v', 'rtl/ishi_logo.v']",
                               "SYN_RTL = ['ishi_vga_core.v', 'ishi_logo.v']")
    config=config.replace("SYN_TB_RTL = ['tests/tb_vga.v']",
                          f"SYN_TB_RTL = ['{ROOT}/tests/tb_vga.v']")
    config=config.replace("SYN_TB_NET = ['tests/tb_vga.v']",
                          f"SYN_TB_NET = ['{ROOT}/tests/tb_vga.v']")
    (d/'config.py').write_text(config)
    return d

for value in (159,199,255,79):
    write(value)
write_h79_v500()
print('generated descending_h159, descending_h199, descending_h255, descending_h79, descending_h79_v500')
