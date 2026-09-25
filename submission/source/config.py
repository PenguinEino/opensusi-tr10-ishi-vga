"""Adopted letter animation with an idle stage; immutable static-core ECO.

Use scripts/replay_letter_animation_core.py to reproduce the physical core.
Full-core synthesis alone does not recreate this incremental placement.
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
STA_CLK_PORT = 'clk'
STA_PERIOD_NS = 317.460317
STA_FALSE_PATH_FROM = []
STA_EXTRA_TCL = os.path.join(ROOT, 'clock_electrical.tcl')
N_ROWS = 4
MACRO_MODE = 'none'
PAD_MAP = {}
RING_OSC_ORIGIN = None

ANIMATION = {'mode': 'letter_scan_idle',
 'phase_bits': 7,
 'phase_enable': 'h==100 && v==0',
 'clock_hz': 3150000,
 'frame_hz': 60,
 'cycle_frames': 128,
 'stage_frames': [16, 16, 16, 16, 64],
 'source': 'designs/grid_power',
 'adopted': True,
 'flow_scope': 'incremental physical ECO and digital verification'}
ANIMATION_ECO = {'source_gds': 'release/ishi_vga_letter_scan_core/reproduce/static_core.gds',
 'source_sha256': '299b3203897dd4dffca7fb1a260a68dbd577c4ac4f98fb105cfe9e8579cf650c',
 'placement': 'release/ishi_vga_letter_scan_core/reproduce/static_placement.json',
 'netlist': 'release/ishi_vga_letter_scan_core/reproduce/static_netlist.v',
 'frame_end_n': '_117_',
 'clock': 'clk_row3',
 'rows': [3, 2, 1, 0],
 'grid_um': 0.9,
 'bounds_um': [-12.6, 3.6, 1774.8, 893.7],
 'via_cost_steps': 12,
 'max_expanded_nodes': 8000000,
 'target_size_um': [1800, 900],
 'seed': 17,
 'nonpreferred_cost': 5,
 'route_priority': ['h[5]',
                    'h[4]',
                    'anim_phase_0_',
                    'anim_phase_3_',
                    'anim_phase_5_',
                    'anim_phase_6_',
                    'clk_row3',
                    '_117_',
                    '_010_',
                    '_011_',
                    '_009_',
                    'anim_green_new',
                    'anim_blue_new'],
 'patch_dir': 'patch_split_toggle',
 'phase_bits': 7,
 'replacements': [['_395_', 'D', '_010_', 'anim_green_new'],
                  ['_398_', 'D', '_011_', 'anim_blue_new']],
 'port_nets': {'clk': 'clk_row3',
               'frame_end_n': '_117_',
               'h4': 'h[4]',
               'h5': 'h[5]',
               'red': '_009_',
               'green': '_010_',
               'blue': '_011_',
               'green_new': 'anim_green_new',
               'blue_new': 'anim_blue_new'},
 'placement_steps': 50000,
 'anneal_temp_start': 100000,
 'anneal_temp_end': 2,
 'pin_collision_penalty': 100000}
LOCAL_REPAIR = {'remove_boxes': [['M2', 410.5, 372.7, 413.9, 648.8]],
 'add_boxes': [['M2', 410.5, 372.7, 413.9, 644.9],
               ['M2', 411.4, 641.5, 414.8, 648.8],
               ['M2', 410.5, 641.5, 414.8, 644.9],
               ['M1', 370.7, 822.3, 371.8, 825.2],
               ['M1', 603.8, 819.0, 604.1, 819.9]]}
finalize(globals())
