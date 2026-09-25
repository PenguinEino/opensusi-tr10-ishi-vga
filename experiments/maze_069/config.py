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

MAZE_ROUTE = {
 'source_gds': 'experiments/maze_073/build/candidate.gds',
 'source_sha256': 'd695d2cd225ba3f2db0970f8451708a4f855979d6de2760005122af562c5355b',
 'shapes': 'experiments/metal_repair/build/junction_y7296/net_shapes.json',
 'actual_pins': 'experiments/via_prune/build/audit/actual_pin_map.json',
 'placement': 'experiments/phys_desc5/layout/placement.json',
 'target': '_069_',
 'remove_shape_indices': [3, 4, 5, 8, 9, 10, 12, 13, 14, 17, 19, 21, 26, 28, 30, 35, 37, 39],
 'remove_shape_multiplicity': {'8': 1, '9': 4, '13': 4, '14': 4, '17': 1, '26': 1, '35': 1},
 'duplicate_index_groups': {'9': [9,18,27,36], '13': [13,22,31,40], '14': [14,23,32,41]},
 'remove_vias_um': [[267.3,390.1],[267.3,951.0],[267.3,940.2],[267.3,929.4],[267.3,918.6],[267.3,907.8],
                    [342.9,390.1],[342.9,940.2],[342.9,929.4],[342.9,918.6],[342.9,907.8]],
 'pre_route_boxes': [['M2', 265.6, 1257.3, 269.0, 1333.7]],
 'bounds_um': [-18.0, 1.8, 1773.0, 1796.4],
 'grid_um': 0.9,
 'via_cost_steps': 12,
 'max_expanded_nodes': 8000000,
 'max_route_iterations': 8,
 'max_core_size_um': [1800.0, 1800.0],
 'm1_spacing_mode': 'local_wide',
 'terminal_layers': ['M2'],
}


finalize(globals())
