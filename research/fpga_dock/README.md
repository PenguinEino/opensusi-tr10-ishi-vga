# Tang Primer 20K Dock: safe 8-GPIO header evidence

## Recommended header: J5

For the resistor-DAC wiring, use Dock header **J5** (2×6, `Conn_02x06_Odd_Even`) with its attached RGB-LCD cable/header J7 left disconnected. J5 has eight FPGA signals and a separate two-pin +3V3 supply and two-pin GND. The signals are otherwise the RGB-LCD interface, so do not attach or drive an RGB LCD at J7 at the same time.

| J5 schematic pin | Net | FPGA package ball | Bank |
|---:|---|---|---:|
| 1 | +3V3 | — | supply |
| 2 | +3V3 | — | supply |
| 3 | GND | — | ground |
| 4 | GND | — | ground |
| 5 | RGB_LCD_R0 | L9 | 3 |
| 6 | RGB_LCD_R1 | N8 | 3 |
| 7 | RGB_LCD_R2 | N9 | 3 |
| 8 | RGB_LCD_R3 | N7 | 3 |
| 9 | RGB_LCD_R4 | N6 | 3 |
| 10 | RGB_LCD_G0 | D11 | 7 |
| 11 | RGB_LCD_G1 | A11 | 7 |
| 12 | RGB_LCD_G2 | B11 | 7 |

The Dock PDF's J5 pins are drawn as odd/even columns. These are the **schematic designator pin numbers**, not an assumption about how a generic Pmod cable numbers a connector when viewed from either side. Wire using J5's physical orientation and pin-1 marker, and preserve the explicit supply/ground assignments above. No conclusion about generic Pmod mechanical/electrical compatibility is made here.

## Voltage and drive evidence

The official Tang Primer 20K SOM-3961 schematic shows Bank 3 `VCCO3` tied to `+3V3`. It also shows `VCCO7` powered from `+3V3` through the default 0-ohm option R13; Sipeed's Primer 20K wiki states Bank 7 defaults to 3.3 V. The official Sipeed TangPrimer-20K example configures the same RGB nets and balls as `IO_TYPE=LVCMOS33`. Thus J5's five Bank 3 and three Bank 7 signals are intended for 3.3 V I/O with the normal SOM/Dock configuration.

The Sipeed Primer 20K datasheet specifies FPGA I/O drive capabilities including 4, 8, 16, and 24 mA. `DRIVE=8` is therefore an available setting for these output pins. The official RGB example sets `LVCMOS33` but leaves its drive field at default; the drive-strength claim comes from the datasheet, not that example.

## Revision check

Sipeed's latest posted Dock PDF is 3714 (schematic Rev 1.3, dated 2026-05-20 in its revision history). The prior 3713 PDF is Rev 1.1 dated 2023-09-12 and records the fix for PMOD connector spacing. Page 4 (`/P006_LCD/`) is text-identical between the two PDFs, including the J5 pin assignments above. The 3714 history says its additional change is DVI optimization and a SW0/KEY4 pin swap. The physical board revision is not established by the product URL; if the board is earlier than 3713, verify connector spacing and silkscreen before fabrication. J5 electrical mapping is the same in the two posted revisions compared here.

## Primary sources and evidence files

All PDFs are downloaded from Sipeed's official file service and saved alongside this note. SHA-256 values identify the local bytes used for inspection.

| Source | Revision / location | SHA-256 |
|---|---|---|
| [Tang Primer 20K Dock schematic 3714](https://dl.sipeed.com/shareURL/TANG/Primer_20K/02_Schematic) | Current file `Tang_Primer_20K_Dock_3714_Schematics.pdf`, pages 1 and 4; J5 pin/net assignment; history | `284aed9a243dcbe4cf5e6dbb2366faa17936a62c922f378cbda347c285925188` |
| [Tang Primer 20K Dock schematic 3713](https://dl.sipeed.com/shareURL/TANG/Primer_20K/02_Schematic) | Prior file `Tang_Primer_20K_Dock-3713_Schematics.pdf`, page 4 compared with 3714 | `17c2d75551e59294937f362d6c7a04a7a752ead754465a4be8ddabbd1f7cf2ae` |
| [Tang Primer 20K SOM schematic](https://dl.sipeed.com/shareURL/TANG/Primer_20K/02_Schematic) | `Tang_Primer_20K_SOM-3961_Schematic.pdf`, FPGA Bank 3/7 supply evidence | `b5110caa0508d1d80513ca28978b0836e9b2aec92fc889f850a5a43ec03e6ce8` |
| [Tang Primer 20K datasheet](https://dl.sipeed.com/shareURL/TANG/Primer_20K/01_Specification) | V1.0, I/O drive-strength statement, p.3 | `7ec2ada4c37cce6ec9601e96812ccd1c86ebd0ecef73b676e0e6bc61db0a8da7` |
| [Sipeed example repository](https://github.com/sipeed/TangPrimer-20K-example/tree/e469df4c0c9c41824f405a8515decf24ef1e8e6f) | exact HEAD `e469df4c0c9c41824f405a8515decf24ef1e8e6f` | — |
| [Official 800×480 RGB CST](https://github.com/sipeed/TangPrimer-20K-example/blob/e469df4c0c9c41824f405a8515decf24ef1e8e6f/RGB_lcd/800x480_5inch_lcd/src/lcd.cst) | `IO_LOC` / `IO_TYPE=LVCMOS33` for the listed RGB signal balls | `17b53f806cbc0cdb5bf63a8af8625a85f3e23f1afc1523ab44ad5e4e48969607` |
| [Sipeed Primer 20K wiki](https://en.wiki.sipeed.com/hardware/en/tang/tang-primer-20k/primer-20k.html) | Bank 0/1/7 3.3 V default, Pmod count, hardware links | web source |

Schematic PDFs were downloaded through the official file endpoint, for example:

```text
https://api.dl.sipeed.com/file/download?file_url=TANG/Primer_20K/02_Schematic/Tang_Primer_20K_Dock_3714_Schematics.pdf
https://api.dl.sipeed.com/file/download?file_url=TANG/Primer_20K/02_Schematic/Tang_Primer_20K_Dock-3713_Schematics.pdf
https://api.dl.sipeed.com/file/download?file_url=TANG/Primer_20K/02_Schematic/Tang_Primer_20K_SOM-3961_Schematic.pdf
https://api.dl.sipeed.com/file/download?file_url=TANG/Primer_20K/01_Specification/Sipeed%20Tang%20Primer%2020K%20Datasheet%20V1.0.pdf
```

Files: `Tang_Primer_20K_Dock_3714_Schematics.pdf`, `Tang_Primer_20K_Dock_3713_Schematics.pdf`, `Tang_Primer_20K_SOM-3961_Schematic.pdf`, and `Sipeed_Tang_Primer_20K_Datasheet_V1.0.pdf`. The official example CST was checked out read-only from the exact repository commit above; no design or code files in the working tree were changed for this research task.
