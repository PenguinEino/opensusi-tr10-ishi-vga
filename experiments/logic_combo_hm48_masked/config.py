"""Exact-image combinational experiment: logic_combo_hm48_masked."""
from pathlib import Path
import runpy
PROJECT = Path(__file__).resolve().parents[2]
settings = runpy.run_path(str(PROJECT/'config.py'))
globals().update({k:v for k,v in settings.items() if not k.startswith('__')})
SYN_RTL = [str(PROJECT/'experiments/logic_combo_hm48_masked/ishi_vga_core.v'), str(PROJECT/'experiments/logic_combo_hm48_masked/ishi_logo.v')]
SYN_TB_RTL = SYN_TB_NET = [str(PROJECT/'tests/tb_vga.v')]
