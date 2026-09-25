"""Transistor checks of the adopted 128-frame letter animation, from its GDS."""
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
SPICE_CHECK = {
    'gds': 'release/ishi_vga_letter_scan_core/ishi_vga.gds',
    'gds_sha256': '4a56593ff8f9d61112e69780ed80f04ef276713d3f8fa88901554c8dbbbee22b',
    'extracted': 'release/ishi_vga_letter_scan_core/ishi_vga.extracted',
    'placement': 'release/ishi_vga_letter_scan_core/verification/placement.json',
    'top': 'ishi_vga_core',
    'clock_hz': 3150000,
    'temperature_c': 27,
    'voltage_v': 5.0,
    'output_load_pf': 1.0,
    'max_step_ns': 1.0,
    'sample_offset_ns': 150,
    'workers': 4,
    'stage_phases': [0, 16, 32, 48, 64],
    'transition_phases': [0, 1, 3, 7, 15, 31, 47, 63, 79, 95, 111, 127],
}
finalize(globals())
