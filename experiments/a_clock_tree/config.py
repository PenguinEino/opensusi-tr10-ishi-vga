"""Adopted grid+five power branches: 7 terminals excluding shared VSS.

This is the current logical design. Archived physical checkpoints and the
final signed-off core are documented in docs/POWER_GRID_IMPLEMENTATION.md.
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
SYN_TB_RTL = ['tests/tb_rtl.v']
SYN_TB_NET = ['tests/tb_gates.v']
BUFTH_NETS = ['clk']
STA_CLK_PORT = 'clk'
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
CLOCK_ECO = {
    'source_gds': 'release/ishi_vga_grid_power_core/src/ishi_vga_grid_power.gds',
    'source_sha256': '3bcfd73d98e2adca5b78eb20978a6145960e8023e60527ec7e960979cb86617e',
    'placement': 'release/ishi_vga_grid_power_core/experiments/a_power_flex4/layout/placement.json',
    'pins': 'release/ishi_vga_grid_power_core/experiments/a_power_flex4/build/audit/actual_pin_map.json',
    'shapes': 'release/ishi_vga_grid_power_core/experiments/a_power_flex4/build/diagnostic_shapes.json',
    'netlist': 'release/ishi_vga_grid_power_core/designs/grid_power/out/ishi_vga_core_pnr.v',
    'replace_fillers': ['FILL_r0_23', 'FILL_r1_17', 'FILL_r2_15', 'FILL_r3_41'],
    'remove_clock_boxes': [41,42,51,52,53,56,57,58,61,62,63,64],
    'remove_clock_vias': [[224.1,66.8],[224.1,309.1],[159.3,309.1],[159.3,583.8],[175.5,583.8],[175.5,799.1],[866.7,799.1]],
    'bounds_um': [-12.6, 3.6, 1774.8, 893.7],
    'grid_um': 0.9,
    'via_cost_steps': 12,
    'max_expanded_nodes': 8000000,
    'route_order': ['clk_row0','clk_row1','clk_row2','clk_row3','clk_buf'],
    'buffer_cell': 'BUF_X2',
    'target_size_um': [1800,900],
}
SPICE_CHECK = {'gds': 'experiments/a_clock_tree/build/candidate.gds', 'gds_sha256': '299b3203897dd4dffca7fb1a260a68dbd577c4ac4f98fb105cfe9e8579cf650c', 'top': 'ishi_vga_core', 'voltage_v': 5.0, 'temperature_c': 27, 'clock_hz': 3150000, 'clock_rise_ns': 2, 'max_step_ns': 1, 'output_load_pf': 1.0, 'extraction_combine': False, 'frame_integration': False, 'interconnect_rc': False}
STA_EXTRA_TCL = os.path.join(ROOT, 'clock_electrical.tcl')
finalize(globals())
