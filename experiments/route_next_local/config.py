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

METAL_LOCAL_REPAIR = {
    'input_gds': 'experiments/routed_checkpoint/build/routed_checkpoint.gds',
    'input_sha256': '9653d8a5b6a9aba7d696e9b881a98042cc749457260c531f3f7ea33b08da7634',
    'pins': 'experiments/route_next_local/build/actual_pin_map.json',
    'net_shapes': 'experiments/route_next_local/build/net_shapes.json',
    'placement': 'experiments/phys_desc5/layout/placement.json',
    'via_trials': {
        'near_048_h0': {'xy_um': [774.9, 287.5], 'nets': ['_048_', 'h[0]']},
        'near_048_h0_two_vias': {'via_centers_um': [[774.9, 287.5], [774.9, 157.9]], 'nets': ['_048_', 'h[0]']},
        'near_247_h4': {'xy_um': [1109.7, 697.2], 'nets': ['_247_', 'h[4]']},
        'near_222_223': {'xy_um': [240.3, 670.2], 'nets': ['_222_', '_223_']},
    },
}

CONSTANT_TIE_INTEGRATION = {'source_gds': 'experiments/metal_repair/build/junction_y7296/candidate.gds', 'reference_gds': 'experiments/phys_desc5/build/postrepair_compacted.gds', 'patch_json': 'experiments/constant_tie/build/constant_tie_patch.json', 'placement': 'experiments/phys_desc5/layout/placement.json', 'actual_pins': 'experiments/routing_audit/actual_pin_map.json', 'routing_shapes': 'experiments/metal_repair/build/junction_y7296/net_shapes.json', 'top': 'ishi_vga_core', 'accepted_edit_manifest': 'experiments/metal_repair/build/junction_y7296/edit_manifest.json'}

finalize(globals())
