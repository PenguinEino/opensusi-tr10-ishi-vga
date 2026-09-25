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
SYN_RTL = ['rtl/ishi_vga_core.v', 'rtl/ishi_logo.v']
SYN_CELLS_V = 'build/tr1um_cells.v'
SYN_CELLS_GEN = True
SYN_CELLS_ARGS = ['--power', '--delay', '1']
SYN_TB_RTL = ['tests/tb_vga.v']
SYN_TB_NET = ['tests/tb_vga.v']
BUFTH_NETS = ['clk', 'reset_n']
STA_CLK_PORT = 'clk'
STA_PERIOD_NS = 155.0  # covers 6.45 MHz experiment; nominal 6.30 MHz is slower
STA_FALSE_PATH_FROM = ['reset_n']  # assertion asynchronous; release via two FFs
N_ROWS = 7  # B: 8337.6 um cell width / 7 rows, about 82% effective occupancy
CORE_WIDTH_TRACKS = 296
CH_HEIGHTS = [140.4] + [151.2] * 6 + [162.0]
# Diagnostic routing budget; compaction must be measured against the 1800 um limit.
ROUTE_CH_HEIGHTS = [216.0] + [900.0] * 6 + [216.0]
PLACE_SEED = 1  # initial seed; no sweep has been done
PLACE_RESTARTS = 80
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
finalize(globals())

# Literal input manifest for design-owned core-port text annotation.
CORE_PORT_LABELS = {
    'top': 'ishi_vga_core',
    'source_gds': 'experiments/maze_seq02/build/candidate.gds',
    'source_sha256': '4b378b730022f1c04dbb23ebb6e6b3314d54e7bcc7f0ff20edb0f8c20784dfc3',
    'actual_pin_map': 'experiments/maze_seq02/build/audit/actual_pin_map.json',
    'actual_pin_map_sha256': '833890d78b6ec6b848ca60b5982893b8b056ab875188fd16c916138223e69a98',
    'placement': 'experiments/phys_desc5/layout/placement.json',
    'placement_sha256': 'fa842099d39d350e9264f1f150d22dabf717923c1dc54bddae28a005ee71e0eb',
    'reference_spice': 'experiments/core_lvs/build/ishi_vga_core.spice',
    'reference_spice_sha256': 'd490d1e08633b3a858bd7adfc4cef5abee3826d22707529b54b3d2669c3739a8',
    'expected_ports': ['b[1]', 'b[0]', 'clk', 'g[1]', 'g[0]', 'hsync', 'r[1]', 'r[0]', 'reset_n', 'vsync', 'vdd', 'vss'],
}
