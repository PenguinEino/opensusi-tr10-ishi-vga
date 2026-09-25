"""Reproducible settings for the GC/M1 crossing test array."""
import os
from pathlib import Path
ROOT=str(Path(__file__).resolve().parents[2])
TOP_CELL_NAME=CHIP_TOP_CELL="poly_probe_array"
STDCELL="v59_4"
PROBE_LENGTHS_UM=(10.0,20.0,40.0,80.0)
PROBE_WIDTHS_UM=(1.0,2.0,3.0)
PROBE_ORIGIN_X_UM=20.0
PROBE_ORIGIN_Y_UM=20.0
PROBE_PITCH_Y_UM=20.0
DEVICE_PROBE_PITCH_Y_UM=90.0
DEVICE_PROBE_ORIGIN_Y_UM=1200.0
DEVICE_PROBE_ORIGIN_X_UM=20.0
def pdk_root():
    return os.environ.get("TR1UM_PDK", str(Path(ROOT)/"tools/TR-1um"))
def show(path):
    return str(path)
