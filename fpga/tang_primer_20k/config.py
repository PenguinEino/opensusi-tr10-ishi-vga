"""Reproducible FPGA settings; independent of the pinned ASIC toolchain."""
SUITE_VERSION = "20260925"
SUITE_ARCHIVE_SHA256 = "c8cabe35a3d0719aeebf59bf7049d77918f0e61afc13f50c761cfeb122f802fd"
DEVICE = "GW2A-LV18PG256C8/I7"
FAMILY = "GW2A-18"
SEED = 1
INPUT_MHZ = 27
TARGETS = {
    "led": {
        "top": "led_top",
        "sources": ["fpga/tang_primer_20k/led_top.v"],
        "cst": "fpga/tang_primer_20k/led.cst",
        "sdc": "fpga/tang_primer_20k/ishi_vga_tang.sdc",
        "pack_options": [],
    },
    "vga": {
        "top": "ishi_vga_tang_top",
        "sources": [
            "fpga/tang_primer_20k/ishi_vga_tang_top.v",
            "fpga/tang_primer_20k/gowin_pll_315.v",
            "designs/grid_power/ishi_vga_core.v",
            "designs/grid_power/ishi_logo.v",
        ],
        "cst": "fpga/tang_primer_20k/ishi_vga_tang.cst",
        "sdc": "fpga/tang_primer_20k/nextpnr.sdc",
        # N9 (blue) is shared with SSPI_CS_N; enable its GPIO function.
        "pack_options": ["--sspi_as_gpio"],
    },
}

# Animated B keeps the proven board wrapper, PLL and GPIO assignment.
TARGETS["vga_animation"] = {
    **TARGETS["vga"],
    "sources": [
        "fpga/tang_primer_20k/ishi_vga_tang_top.v",
        "fpga/tang_primer_20k/gowin_pll_315.v",
        "experiments/a_wire_scan_eco/ishi_vga_core.v",
        "experiments/a_wire_scan_eco/ishi_logo.v",
    ],
}

# Current choice: I -> S -> H -> I -> unchanged logo, 16 frames per letter, 64 idle.
TARGETS["vga_letter_animation"] = {
    **TARGETS["vga"],
    "sources": [
        "fpga/tang_primer_20k/ishi_vga_tang_top.v",
        "fpga/tang_primer_20k/gowin_pll_315.v",
        "experiments/a_letter_scan_eco/ishi_vga_core.v",
        "experiments/a_letter_scan_eco/ishi_logo.v",
    ],
}
