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
SYN_TB_RTL = ['/home/ishi-kai/ishi-vga/tests/tb_vga.v']
SYN_TB_NET = ['/home/ishi-kai/ishi-vga/tests/tb_vga.v']
BUFTH_NETS = ['clk', 'reset_n']
STA_CLK_PORT = 'clk'
STA_PERIOD_NS = 155.0  # covers 6.45 MHz experiment; nominal 6.30 MHz is slower
STA_FALSE_PATH_FROM = ['reset_n']  # assertion asynchronous; release via two FFs
N_ROWS = 5
CORE_WIDTH_TRACKS = 328
CH_HEIGHTS = [140.4] + [151.2] * 4 + [162.0]
# Diagnostic routing budget; compaction must be measured against the 1800 um limit.
ROUTE_CH_HEIGHTS = [216.0] + [900.0] * 4 + [216.0]
PLACE_SEED = 4
PLACE_RESTARTS = 160
PLACE_ORDER_PASSES = 20
PAD_WEIGHT = 1.0
NO_BOTTOM_PORTS = False
MACRO_MODE = 'none'

# Initial pad plan. P8=VSS/P16=VDD are the GIO frame's fixed supply pads.
# OUT is a driver input; P is the pad's input-sense line.
PAD_MAP = {
    1: {'role':'clock input', 'P':'clk', 'OUT':'GND', 'HIZ':'VDD'},
    2: {'role':'active-low reset', 'P':'reset_n', 'OUT':'GND', 'HIZ':'VDD'},
    3: {'role':'red MSB', 'OUT':'r[1]', 'HIZ':'GND'},
    4: {'role':'green MSB', 'OUT':'g[1]', 'HIZ':'GND'},
    5: {'role':'blue MSB', 'OUT':'b[1]', 'HIZ':'GND'},
    6: {'role':'vertical sync', 'OUT':'vsync', 'HIZ':'GND'},
    7: {'role':'red LSB', 'OUT':'r[0]', 'HIZ':'GND'},
    9: {'role':'green LSB', 'OUT':'g[0]', 'HIZ':'GND'},
    10: {'role':'blue LSB', 'OUT':'b[0]', 'HIZ':'GND'},
    11: {'role':'horizontal sync', 'OUT':'hsync', 'HIZ':'GND'},
    12: {'role':'reserved for ring output', 'OUT':'GND', 'HIZ':'VDD'},
    13: {'role':'unused', 'OUT':'GND', 'HIZ':'VDD'},
    14: {'role':'unused', 'OUT':'GND', 'HIZ':'VDD'},
    15: {'role':'unused', 'OUT':'GND', 'HIZ':'VDD'},
}
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

MAZE_ROUTE = {'source_gds': 'experiments/maze_059_fix/build/candidate.gds',
 'source_sha256': '9bde25ccf75379b7be5eff6dc53dbb1a0fc5ef582241e62a72f955d774426619',
 'shapes': 'experiments/metal_repair/build/junction_y7296/net_shapes.json',
 'actual_pins': 'experiments/via_prune/build/audit/actual_pin_map.json',
 'placement': 'experiments/phys_desc5/layout/placement.json',
 'target': '_209_',
 'remove_shape_indices': [16, 17, 30, 43],
 'bounds_um': [-4.5, 100.8, 1773.0, 1756.8],
 'grid_um': 0.9,
 'via_cost_steps': 12,
 'max_expanded_nodes': 4000000,
 'drawing_baseline': 'experiments/via_groups/build/final_drawing.lyrdb',
 'mask_baseline': 'experiments/via_groups/build/via_groups_pruned_mdp.lyrdb',
 'remove_vias_um': [[947.7, 924.0], [947.7, 907.8], [947.7, 897.0]],
 'remove_shape_multiplicity': {'16': 3}}

finalize(globals())
