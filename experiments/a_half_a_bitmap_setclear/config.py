"""Corrected A trial; core only. No frame integration. Mode: group_y."""
"""VGA design configuration for the locked APRtools v59_4 flow.
Placement settings are initial budgets, not a claim that routing fits.
"""
from config_base import *

TOP_CELL_NAME = 'ishi_vga_core'
CHIP_TOP_CELL = 'tr_1um_ishi_kai_vga'
STDCELL = 'v59_4'
SC = os.path.join(APR_ROOT, 'stdcell', STDCELL)
LIB_GDS = CELL_GDS = os.path.join(SC, 'TR-1um_STDCELL.gds')
LIB_LEF = LEF_PATH = os.path.join(SC, 'TR-1um_cells.lef')
SYN_LIB = LIBERTY = os.path.join(SC, 'tr1um_typ_5v0_25c.lib')
CELL_INFO = os.path.join(SC, 'cell_info.json')
FRAME_GDS = os.path.join(APR_ROOT, 'pdk/pending-upstream/TR-1um_frame_25x25_GIO.gds')
FRAME_LVS_SPICE = os.path.join(APR_ROOT, 'pdk/frame/OSS_FRAME_GIO_nocombine.spice')
SYN_RTL = ['ishi_vga_core.v', 'ishi_logo.v']
SYN_CELLS_V = 'build/tr1um_cells.v'
SYN_CELLS_GEN = True
SYN_CELLS_ARGS = ['--power', '--delay', '1']
SYN_TB_RTL = ['/home/ishi-kai/ishi-vga/experiments/a_half_a_bitmap_setclear/tests/tb_rtl.v']
SYN_TB_NET = []
BUFTH_NETS = ['clk']
STA_CLK_PORT = 'clk'
STA_PERIOD_NS = 155.0
STA_FALSE_PATH_FROM = []
N_ROWS = 4
CORE_WIDTH_TRACKS = 328
CH_HEIGHTS = [140.4] + [151.2] * 3 + [162.0]
# Diagnostic routing budget; compaction must be measured against the 1800 um limit.
ROUTE_CH_HEIGHTS = [216.0] + [900.0] * 3 + [216.0]
PLACE_SEED = 4
PLACE_RESTARTS = 160
PLACE_ORDER_PASSES = 20
PAD_WEIGHT = 0.0
NO_BOTTOM_PORTS = False
MACRO_MODE = 'none'

# Initial pad plan. P8=VSS/P16=VDD are the GIO frame's fixed supply pads.
# OUT is a driver input; P is the pad's input-sense line.
PAD_MAP = {}
# Core-only first. Ring is integrated after routed size and power clearances are known.
RING_OSC_ORIGIN = None
CHIP = os.path.join(ROOT, 'layout/chip')
CHIP_ROUTE_IN_GDS = os.path.join(CHIP, 'step1_assembled.gds')
PLACE_BALANCE_TOL = 0.02
PLACE_FILL_MODE = 'alternate'
ROUTING_KNOBS = {'PRL_MIN_PINS': 10, 'SPAN_LANE_PACK': False}
_upstream_getenv = getenv
def getenv(name, default=None, cast=None):
    if name not in ROUTING_KNOBS:
        return _upstream_getenv(name, default, cast)
    value = ROUTING_KNOBS[name]
    return cast(value) if cast else value

HALF_SLOT = {'art': 'A', 'scale': 4, 'h_start': 143, 'h_end': 200, 'h_bits': 8, 'v_start': 500, 'v_last': 0, 'horizontal_total': 200, 'palette_rgb111': [7, 3, 4, 3, 1, 5], 'signals': 6, 'including_vdd_excluding_common_vss': 7, 'target_bbox_um': [1800, 900], 'adopted': False, 'reset': False, 'background': 'black', 'source': 'a_half_a128_5col', 'coordinate_mode': 'H143, h[6:0], v[8:2], !h[7] logo select', 'group_axis': 'x', 'direct_color': False, 'renderer': 'setclear'}
finalize(globals())
