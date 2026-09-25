"""Adopted grid+five power branches: 7 terminals excluding shared VSS.

This is the current logical design. Archived physical checkpoints and the
current verified core are documented in docs/POWER_GRID_IMPLEMENTATION.md.
No package pad numbers are assigned while organizer frame integration waits.
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
SYN_TB_RTL = []
SYN_TB_NET = []
BUFTH_NETS = ['clk']
STA_CLK_PORT = None
STA_PERIOD_NS = 317.460317
STA_FALSE_PATH_FROM = []
N_ROWS = 4
CORE_WIDTH_TRACKS = 328
CH_HEIGHTS = [140.4] + [151.2] * 3 + [162.0]
ROUTE_CH_HEIGHTS = [216.0] + [900.0] * 3 + [216.0]
PLACE_SEED = 7
PLACE_RESTARTS = 40
PLACE_ORDER_PASSES = 20
PLACE_BALANCE_TOL = 0.02
PLACE_FILL_MODE = 'alternate'
PAD_WEIGHT = 0.0
NO_BOTTOM_PORTS = False
MACRO_MODE = 'none'
PAD_MAP = {}
RING_OSC_ORIGIN = None
ROUTING_KNOBS = {'PRL_MIN_PINS': 20, 'SPAN_LANE_PACK': False}
_upstream_getenv = getenv
def getenv(name, default=None, cast=None):
    if name not in ROUTING_KNOBS:
        return _upstream_getenv(name, default, cast)
    value = ROUTING_KNOBS[name]
    return cast(value) if cast else value

ROW_OPT = {'source': 'a_metal_g_power_anneal4', 'restarts': 24,
           'steps_per_restart': 4000000, 'seed': 91,
           'temperature_start': 4.0, 'temperature_end': 0.02,
           'spread_weight': 0, 'order_passes': 80,
           'max_width_average_factor': 1.20}
ADOPTED = {'art': 'g_power', 'reference': 'experiments/a_metal_g_power',
           'clock_hz': 3150000, 'terminals_excluding_vss': 7,
           'target_bbox_um': [1800, 900], 'reset': False, 'ring': False,
           'frame_integration': False, 'rgb_bits': [1, 1, 1]}
# Current physical implementation adds four row buffers after mapping.
# Reproduce with scripts/replay_clock_core.py and experiments/a_clock_tree/config.py.
STA_EXTRA_TCL = None
ANIMATION = {'counter_style': 'add_enable', 'mode': 'white_pulse', 'phase_bits': 6, 'phase_enable': 'h==100 && v==0', 'clock_hz': 3150000, 'frame_hz': 60, 'cycle_frames': 64, 'source': 'designs/grid_power', 'adopted': False, 'flow_scope': 'synthesis and digital simulation only'}
finalize(globals())
