"""Exact-image combinational experiment: logic_bdd_yx_msb."""
from pathlib import Path
import runpy
PROJECT = Path(__file__).resolve().parents[2]
settings = runpy.run_path(str(PROJECT/'config.py'))
globals().update({k:v for k,v in settings.items() if not k.startswith('__')})
SYN_RTL = [str(PROJECT/'rtl/ishi_vga_core.v'), str(PROJECT/'experiments/logic_bdd_yx_msb/ishi_logo.v')]
SYN_TB_RTL = SYN_TB_NET = [str(PROJECT/'tests/tb_vga.v')]
