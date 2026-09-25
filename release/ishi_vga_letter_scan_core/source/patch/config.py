"""Synthesis-only auxiliary sequencer for the letter animation.

Use scripts/replay_letter_animation_core.py to reproduce the physical core.
Full-core synthesis alone does not recreate this incremental placement.
"""
from config_base import *

TOP_CELL_NAME = 'letter_scan_patch'
CHIP_TOP_CELL = 'tr_1um_ishi_kai_vga'
STDCELL = 'v59_4'
SC = os.path.join(APR_ROOT, 'stdcell', STDCELL)
LIB_GDS = CELL_GDS = os.path.join(SC, 'TR-1um_STDCELL.gds')
LIB_LEF = LEF_PATH = os.path.join(SC, 'TR-1um_cells.lef')
SYN_LIB = LIBERTY = os.path.join(SC, 'tr1um_typ_5v0_25c.lib')
CELL_INFO = os.path.join(SC, 'cell_info.json')
FRAME_GDS = os.path.join(APR_ROOT, 'pdk/pending-upstream/TR-1um_frame_25x25_GIO.gds')
FRAME_LVS_SPICE = os.path.join(APR_ROOT, 'pdk/frame/OSS_FRAME_GIO_nocombine.spice')
SYN_RTL = ['letter_scan_patch.v']
SYN_CELLS_V = 'build/tr1um_cells.v'
SYN_CELLS_GEN = True
SYN_CELLS_ARGS = ['--power', '--delay', '1']
SYN_TB_RTL = []
SYN_TB_NET = []
BUFTH_NETS = []
STA_CLK_PORT = None
STA_PERIOD_NS = 317.460317
STA_FALSE_PATH_FROM = []
STA_EXTRA_TCL = None
N_ROWS = 4
MACRO_MODE = 'none'
PAD_MAP = {}
RING_OSC_ORIGIN = None

finalize(globals())
