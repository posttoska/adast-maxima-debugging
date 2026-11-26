# Programmable logic controller and drive control of the Adast Maxima MS 115 PS: set 568-70.9001, sheet 8

Thread t3 (plc_drive) of episode 2 redraws sheet 8 of the 1998 wiring set 568-70.9001 (SCHÉMA ZAPOJENÍ, MS 80 PS.DS, MS 115 PS.DS). The sheet has two parts: (39) the wiring of the PLC (programmable logic controller) (ZAPOJENÍ ŘÍDÍCÍHO AUTOMATU - PLC) and (40) the connection table of the PLC and the control panel (TABULKA PŘIPOJENÍ ŘÍDÍCÍHO AUTOMATU - PLC A OVLÁDACÍHO TABLA). Its devices are the PLC, the console terminal TABLO (OVLÁDACÍ TABLO, control panel), the control side of the frequency inverter UZ1 (MĚNIČ), the backgauge encoder BR40 (SNÍMAČ BR40) and the connectors XC4, XC50, XC60 and XC70. The power side of UZ1 is thread t1's (spec/power.md); the field signals that reach the PLC through sheets 5-7 are thread t2's (spec/control.md).

Rules of this thread: the cabinet photos rule what is wired; where they cannot tell, the 1998 print rules. Red and blue ink on the annotated copy of the sheet is a later technician's remark, quoted as ink and never taken as print. Every device and wire row carries a mark: `sure`, `[?]` (unclear), `estimated ±<error>` or `W` (web source, weaker evidence), and its source paths. Every row that is not `sure` has an entry in the on-site list (section 11) with its key in backticks, and `plc_netlist.py` checks that each key stands in a row of that list.

## 1. Files and rebuild

| File | What it holds |
|---|---|
| `schemes_2d/plc_netlist.py` | the data (DEVICES and WIRES tables, each row with its sources and a note) and the self-checks; writes the two CSV (comma-separated values) files |
| `netlist/plc_drive_devices.csv` | 14 device rows: `designation,kind,function_en,term_cz_ru,type_rating,place,sheet,column,evidence,source_path,note` |
| `netlist/plc_drive_wires.csv` | 35 wire rows: `wire,from_device,from_terminal,to_device,to_terminal,signal,plc_address,connector,pin,cable,sheet,column,evidence,source_path,note` |
| `schemes_2d/plc_draw.py` | the layout (measured on the sheet photo) and the printed texts that are no netlist data; reads the two CSV files, and `power_wires.csv`, `control_wires.csv`, `power_devices.csv` for the references of the shared conductors; draws sheet 8 and checks it |
| `schemes_2d/plc_sheet8.svg` | the redrawn sheet 8 as SVG (Scalable Vector Graphics): drawing (39) under the printed ruler 01-05, table (40), the later ink quoted in grey italic, notes, device block and title block |
| `spec/plc_drive.md` | this text |

Rebuild from the project folder, netlist first:

```
python -B stage_2_electronics/schemes_2d/plc_netlist.py
python -B stage_2_electronics/schemes_2d/plc_draw.py
```

Expected output of the netlist script in the project folder (exit 0; line numbers of power_wires.csv and control_wires.csv as of 2026-11-26 02:51):

```
plc_drive: 14 devices, 35 wires, 11 rows not sure, 17 shared-conductor matches
INFO paths line 2 33X10: column 01-03 there, 03-04 here
INFO paths line 5 XC70: column 02 there, 03 here (see the XC70 row note)
INFO paths line 19 3XC70: column 04-05 there, 03-04 here
INFO paths line 20 2XC70: column 04-05 there, 03-04 here
INFO paths line 21 5XC70: column 04-05 there, 03-04 here
paths table: 21/21 rows mapped; PLC I/O table: 41/41 rows agree
SHARED UZ1 K12 -> PLC IN-8 = power_wires.csv line 101; differs: wire 'K12UZ1' here, '' there
SHARED PLC OUT-B -> UZ1 E3 = power_wires.csv line 96; differs: wire 'E3UZ1' here, '' there; evidence '[?]' here, 'estimated ±1 column' there
SHARED PLC OUT-C -> UZ1 E4 = power_wires.csv line 97; differs: wire 'E4UZ1' here, '' there; evidence '[?]' here, 'estimated ±1 column' there
SHARED PLC OUT-D -> UZ1 28 = power_wires.csv line 98; differs: wire '28UZ1' here, '' there; evidence '[?]' here, 'estimated ±1 column' there
SHARED UZ1 39 -> PLC GND = power_wires.csv line 95; differs: wire '39UZ1' here, '' there
SHARED X5 -> PLC GND = power_wires.csv line 36; differs: wire 'X5' here, '' there
SHARED UZ1 7 -> XC50 6+9 = power_wires.csv line 99; differs: wire '7UZ1' here, '' there; evidence 'sure' here, 'estimated ±1 column' there
SHARED UZ1 8 -> XC50 4 = power_wires.csv line 100; differs: wire '8UZ1' here, '' there; evidence 'sure' here, 'estimated ±1 column' there
UNMATCHED power_wires.csv line 37 X5 -> TABLO -: sheet 8 (015721) routes the TABLO 0V through X10 45: "X5 -> X10 45" and "X10 45 -> TABLO -" here; t5 keeps those two and drops this row
DEVICE XC4 (sheet 8, this thread) differs from power_devices.csv in: type_rating, sheet, column, source_path
DEVICE XC50 (sheet 8, this thread) differs from power_devices.csv in: term_cz_ru, type_rating, sheet, column, source_path
DEVICE XC60 (sheet 8, this thread) differs from power_devices.csv in: term_cz_ru, type_rating, sheet, column, source_path
DEVICE XC70 (sheet 8, this thread) differs from power_devices.csv in: term_cz_ru, type_rating, sheet, column, source_path
SHARED X10 33 -> TABLO +24V = control_wires.csv line 185
SHARED BMR1 24 -> PLC IN-0 = control_wires.csv line 204
SHARED X10 30 -> PLC IN-1 = control_wires.csv line 138
SHARED X10 29 -> PLC IN-2 = control_wires.csv line 136
SHARED XC2 3 -> PLC IN-9 = control_wires.csv line 134
SHARED XC2 2 -> PLC IN-A = control_wires.csv line 132
SHARED PLC OUT-0 -> K2 A1 = control_wires.csv line 142
SHARED PLC OUT-9 -> KM8 13 = control_wires.csv line 139
SHARED X10 35 -> PLC +24V = control_wires.csv line 192; differs: plc_address '+24V PLC' here, '' there
DEVICE PLC (sheet 8, this thread) differs from control_devices.csv in: function_en, term_cz_ru, type_rating, source_path
DEVICE TABLO (sheet 8, this thread) differs from control_devices.csv in: function_en, term_cz_ru, type_rating, column, source_path
INFO on-site keys of the rows not sure in spec/plc_drive.md: 11 of 11
INFO abbreviations in spec/plc_drive.md: 34 of 34 in the list used, 0 without their full name at the first use
result: PASS
```

It checks: both headers exact, UTF-8 (Unicode Transformation Format, 8-bit) without byte order mark; one row per designation; marks valid; every source path exists (skipped when `preparatory_data_analysis/` is absent) and is relative; both ends of every wire are device rows and every device has a wire; the 14 PLC addresses of check 4 each on their device, one signal per address; every row of the sheet-8 paths table (`12_568_sheet8_paths.csv`, 21 rows) and of the PLC I/O (inputs and outputs) table (`12_568_plc_io.csv`, 41 rows) mapped here, and no wire on a terminal that table leaves unused (skipped when `static_dynamic_memory/` is absent); the join with `power_wires.csv` and `control_wires.csv`: each conductor described there too is listed with every field that differs (SHARED), each row of theirs that touches a device of sheet 8 is matched or explained (UNMATCHED), and the device rows copied from those threads equal their owners' rows (skipped while those files are absent); every row that is not `sure` keyed in a row of the on-site list (section 11), not merely somewhere in this text; no phrase of an earlier state (the script's list of stale phrases) in a row or in this text; every 6-digit photo stamp that a note cites also in that row's source paths; every clause of a note, type, signal or function that reads the function of a port or a pin (the script's port words, or a pin said to be a ground, a data line or an output; quoted print left out) with its own mark (estimated, [?] or W), a pin claim also with a manual page number ("p." or "pp.") instead; as many rows carry the shared-conductor note as the join finds shared conductors (17); every abbreviation of its list (34) followed by its full name in brackets at its first use in this text, outside code blocks; a first use inside a quotation passes only when the same line gives that full name in brackets after it.

Expected output of the drawing script (exit 0; the second line is one long line):

```
sheet 8: wire rows 35/35 drawn, pins 69, junction dots 2, texts 315, table (40) rows 25, height 1629 px
references beside leads (18): X5 arrow (2:02) (power_devices.csv row X5); 33X10 (6:15) (printed; control_wires.csv line 185 gives (6:14-15)); 24BMR (7:06) (control_wires.csv line 204); 30X10 (5:14) (control_wires.csv line 138); 29X10 (5:13) (control_wires.csv line 136); K12UZ1 (2:25) (power_wires.csv line 101); 3XC2 (5:12) (control_wires.csv line 134); 2XC2 (5:11) (control_wires.csv line 132); A1K2 (5:16) (control_wires.csv line 142); 13KM8 (5:15) (control_wires.csv line 139); E3UZ1 (2:22) (power_wires.csv line 96); E4UZ1 (2:23) (power_wires.csv line 97); 28UZ1 (2:24) (power_wires.csv line 98); 35X10 (6:17) (control_wires.csv line 192); 39UZ1 (2:21) (power_wires.csv line 95); X5 (2:02) (power_wires.csv line 36); 7UZ1 (2:25) (power_wires.csv line 99); 8UZ1 (2:26) (power_wires.csv line 100)
abbreviations: 20 of 20 in the list used, each with its full name in brackets at its first use
wire ends: 72/72 on a terminal circle, a junction dot, a box edge, a shell outline, an arrow or the open end of a lead
open lead ends: 16/16 bound to the label of their own row (2-8 px past it, or on a junction dot)
table (40) vs 12_568_plc_io.csv: 41/41 rows agree
wrote stage_2_electronics/schemes_2d/plc_sheet8.svg
result: PASS
```

It checks: every wire row drawn once with both ends on placed pins; every end of a drawn wire on a terminal circle or a junction dot, on an edge of a box or an arrow or on the outline of an XC4 shell (not merely inside one of them), or at the open end of a lead; every open lead end closes the line of its own row and stands 2 to 8 pixels past that row's label (and past its red [?] where the row has one), which runs beside the lead between its pin and its end with no other text there, or, where the lead meets a drawn line (the lead of 35X10 on the +24V line), on a junction dot; every designation of the devices file and every wire label printed; the ruler 01-05 printed; no two text boxes overlap; every reference beside a lead taken from the same conductor's row of the other threads (the one kept as printed, "(6:15)" at 33X10, must lie in that row's columns); table (40) holds every row of a PLC, XC50 or XC60 terminal once, in the printed order, and agrees with `12_568_plc_io.csv` (41 of 41); the 14 PLC addresses drawn at their terminals; no text box cut by an edge of the PLC box, and no drawn line (polyline segment, polygon or rect edge) through the core of any text (the band its glyph strokes fill); every [?] drawn red, and the name of each drawn device whose row is not `sure` (BR40, XC4, XC50, XC60, XC70) followed by its mark; the printed remark split over rows 3 and 5 XC60 given in English in those rows and equal to the Czech of the shell row's signal; no phrase of an earlier state (the script's list of stale phrases) in any text; each abbreviation of its list has its full name in brackets at its first use in the prose of the sheet (header line, notes, device block, title block), and no prose line bypasses that pass.

A copy of `stage_2_electronics/` alone (without `preparatory_data_analysis/` and `static_dynamic_memory/`) rebuilds the same three files byte for byte; the scripts then skip the checks that need those folders and say so:

Netlist script: the same lines as above, except that the five "INFO paths line" lines and the "paths table" line are replaced by these two:

```
INFO source paths not checked: preparatory_data_analysis/ absent
INFO paths and PLC I/O tables not checked: static_dynamic_memory/ absent
```

Drawing script: the same lines as above, except that the "table (40) vs" line reads:

```
INFO table (40) not compared with 12_568_plc_io.csv: static_dynamic_memory/ absent
```

Without `power_wires.csv` and `control_wires.csv` the netlist script skips the join (INFO line) and the drawing script stops with `FAIL input missing`, because the references beside the leads come from those files.

MD5 (Message Digest 5) of the outputs of this version:

```
f87ad930448e9b247870ffba9a358345  stage_2_electronics/netlist/plc_drive_devices.csv
fe6397cf16dcce09d6c42718ed34b374  stage_2_electronics/netlist/plc_drive_wires.csv
5618b5669ca3c3e96a7d0adb3c94c3be  stage_2_electronics/schemes_2d/plc_sheet8.svg
```

Render check used for this version: Microsoft Edge headless, `msedge --headless --disable-gpu --screenshot=<file>.png --window-size=1680,1650 file:///<project>/stage_2_electronics/schemes_2d/plc_sheet8.svg` (the window is 21 pixels taller than the 1680 × 1629 pixel sheet, so nothing is cut) with `--force-device-scale-factor` 3; viewed as 3x crops of what this version changed: the leads above and below the PLC box and the two XC50 leads (each ends just past its own label, none of the labels touches an edge of the PLC box), the XC70 contacts (circles right of the arrow "XC70 ⇒ PLC", their numbers clear of the circles) and the TABLO line of the device block (its keypad module now marked "estimated"). The earlier version was also viewed as 2x crops of the five device names with their red [?] (XC70, XC60, XC50, XC4, BR40), of table (40) rows 2-5 XC60 and of the device block.

## 2. Netlist conventions

- Devices of this thread: PLC, TABLO (console operator terminal), BR40 (backgauge position encoder), XC4 (connector of BR40), XC50 (PLC connector of the analog outputs to UZ1), XC60 and XC70 (the two connectors of the serial link PLC-TABLO, PLC side and TABLO side). Rows of other threads' devices that sheet 8 touches are copied from their owners in every field except `note`, which is this thread's own, and the script checks those fields: X10 (terminal strip in the cabinet), X5 (working-earth strip: 0 V of all control supplies, bonded to PE (protective earth)) and UZ1 (frequency inverter, the feed drive of the backgauge motor M2) from `power_devices.csv` (t1); BMR1 (cut-control module), K2 (auxiliary relay of the feed-cut interlock), KM8 (blower (air cushion) motor contactor) and XC2 (table-cabinet interconnection connector, which carries the backgauge end switches S24 and S27) from `control_devices.csv` (t2).
- PLC terminals: OUT-0 to OUT-D and IN-0 to IN-F as printed. `+24V` is one node for the two printed +24V terminals, which sheet 8 joins with a junction dot (the photo labels them, in VDC (volts direct current), "Outputs +24 VDC" and "P.L.C. Input +24 VDC"). `GND` (ground) is one node for the two GND terminals of the output row (a bracket on the paper); `IN-GND` is the two GND terminals of the input row, named as in table (40).
- TABLO terminals: printed ⏚, − and +; here `PE` (protective earth), `-` and `+24V`. `+24V` is the key that `control_wires.csv` gives the same conductor (sheet 6 prints "TABLO +24V (8:03)", control_wires.csv line 185), so the merge finds it.
- Connectors: XC4 contacts 1-5 and `shell` (both halves of the plug and socket, bonded by 7XC4); XC50 contacts `4` and `6+9` (pins 6 and 9 bridged, one terminal, as table (40) prints "6+9 XC50"); XC60 and XC70 contacts 2, 3, 5 and `shell`. BR40 pins `A`, `B`, `I`, `+`, `-` (printed −). UZ1 control terminals keep t1's names: 7, 8, 28, E3, E4, 39, K12.
- Wire label (`wire`): the label at the PLC terminal or in the SMĚR (direction) column of table (40) (24BMR, A1K2, 13KM8, E3UZ1, 3XC70, 4XC4 ...), the terminal name at X10 (33X10, 45X10, ⏚X10), else empty (the BR40 side of XC4, the link shield).
- `plc_address`: the PLC column of table (40): IN-x and OUT-x, and as printed `OUT +24V`, `OUT-GND`, `IN-GND`, `+24V PLC`, `GND PLC`.
- `sheet`, `column`: 8 and the ruler column of the conductor on sheet 8. The paper marks 01-05 by five ticks at irregular places, each over the current path it names; a conductor between two ticks gets both ("03-04"). Where table (40) prints a LINIE for the conductor, that printed column comes first: 1XC4 to 5XC4 carry 04 as printed (LINIE 8:04), though their PLC ends stand under tick 03; 7XC4 carries 03 (LINIE 8:03); and the link rows take 03-04 from "8:03 / 8:04".
- Shared conductors: 17 rows describe the same conductor as a row of `power_wires.csv` (8) or `control_wires.csv` (9) and are marked in `note` by the text "same conductor as a row of power_wires.csv (thread power): keep one when merging" (or the same with control_wires.csv, thread control). The tags `SH:power` and `SH:control` live only in the script's data, not in the CSV files; the script checks that the marked rows are as many as the shared-conductor matches. They keep that row's ends, direction and signal text, so the merge finds them by their ends; the fields that differ are printed by the netlist script and explained in section 9.
- Rows not `sure`: 11. Devices `BR40`, `XC4`, `XC50`, `XC60`, `XC70` and t2's `XC2`; wires `PLC OUT-9 -> KM8 13`, `PLC OUT-B -> UZ1 E3`, `PLC OUT-C -> UZ1 E4`, `PLC OUT-D -> UZ1 28` and `XC60 shell -> XC70 shell`. Each is on the on-site list.
- Source paths: each row names the sheet photos, cabinet photos, manual pages and web copies it rests on, as paths from the project folder.

## 3. The PLC

- Print (sheet 8, photos 20261114_015117 and 20261113_191800): "COMPACT PLC", no maker and no modules; top row OUT 0-D, +24V twice, GND twice; bottom row IN 0-F, GND twice; seven 9-pin D-sub (D-subminiature connector) sockets, of which two are named: XC60 under the arrow "TABLO" and XC50 under the arrow "UZ1". The other five carry nothing on sheet 8.
- Photos (20261102_144328, 142944): B&R (Bernecker + Rainer) "COMPACT P.L.C."; "AUSGÄNGE" (outputs) "14 outputs 24 VDC 1A per terminal, max. 7A per P.L.C."; "EINGÄNGE" (inputs) "16 inputs 24 VDC"; a fuse of 1.25 AT (amperes, time-lag) ("Fuse: 1.25 AT"); ports IF1 (interface 1) RS232 (Recommended Standard 232), IF2 RS232 or RS485 (Recommended Standard 485), IF3, IF4 ONLINE, IF5 CAN (Controller Area Network, option), ANALOG OUTPUTS, ANALOG INPUTS: seven ports, as the print draws seven sockets. Plugs sit only on IF1 and ANALOG OUTPUTS, which is why XC60 = IF1 and XC50 = ANALOG OUTPUTS (estimated, on-site list). Program label "ADAST154.PGP v1.54 98/05/20 MK".
- OM (operating manual MS 80/115 PS, DS) p.49 (20261115_023314) lists it as "BR COMP 1-0"; the B&R data page of BRCOMP1.0 (W, `static_dynamic_memory/blocks/generation_002/artifacts/web/br-automation/brcomp1-0.html`) calls its inputs "sink": they read a switched +24 V, which is how sheet 8 wires every used input.
- Supply: +24V from 35X10 (6:17) on the first +24V terminal; the second +24V feeds the encoder (5XC4). 0 V: the first GND goes to UZ1 39 (2:21), the second to X5. Table (40) writes "GND PLC X5 2:01" while the terminal label and the X5 strip say 2:02, and column 01 of sheet 2 is PE: on the on-site list (also t1's item 40).
- Wired terminals in photo 144328: inputs 0, 1, 2, 8, 9, A, D, E, F, the same as the print. Outputs: a blue wire on 9 (or 8), ferrules on B, C and D, none on A; the markers of the output row cannot be read, so OUT-9, B, C and D are `[?]`.

## 4. PLC inputs and outputs: all rows of table (40)

The 41 rows of the extract `12_568_plc_io.csv`, in its order: the 25 rows table (40) prints, plus the 16 terminals that have no lead and no row on the paper. SMĚR (direction) is the wire label, LINIE (line) the (sheet:column) of the far end; the Czech column is the printed text, written here with its diacritics (the plotter font prints none: "SIGNAL PROVEDENI REZU"). The far end is the conductor's other end on sheet 8. This table was generated from the drawing script's table (40) and compared row by row with the extract (41 of 41 agree, as the drawing script prints).

| # | PLC | SMĚR | LINIE | Czech (table (40)) | English (netlist signal) | Far end | Mark |
|---|---|---|---|---|---|---|---|
| 1 | IN-0 | 24BMR | 7:06 | SIGNÁL PROVEDENÍ ŘEZU | cut-done signal | BMR1 24 | sure |
| 2 | IN-1 | 30X10 | 5:14 | S28 - PLECH LISOVADLA | S28 clamp plate | X10 30 | sure |
| 3 | IN-2 | 29X10 | 5:13 | S30 - POLOHA LISOVADLA | S30 clamp position (top per sheet 1) | X10 29 | sure |
| 4 | IN-3 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 5 | IN-4 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 6 | IN-5 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 7 | IN-6 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 8 | IN-7 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 9 | IN-8 | K12UZ1 | 2:25 | SIGNÁL FUNKCE POHONU | drive (inverter UZ1) function signal (SIGNÁL FUNKCE POHONU) | UZ1 K12 | sure |
| 10 | IN-9 | 3XC2 | 5:12 | S27 - ZADNÍ POLOHA SEDLA | S27 backgauge rear position | XC2 3 | sure |
| 11 | IN-A | 2XC2 | 5:11 | S24 - PŘEDNÍ POLOHA SEDLA | S24 backgauge front position | XC2 2 | sure |
| 12 | IN-B | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 13 | IN-C | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 14 | IN-D | 1XC4 | 8:04 | BR40 - INDEX (I) | encoder index pulse (BR40 - INDEX (I)) | XC4 1 | sure |
| 15 | IN-E | 2XC4 | 8:04 | BR40 - KANÁL "B" | encoder channel B (BR40 - KANÁL B) | XC4 2 | sure |
| 16 | IN-F | 3XC4 | 8:04 | BR40 - KANÁL "A" | encoder channel A (BR40 - KANÁL A) | XC4 3 | sure |
| 17 | IN-GND | 4XC4 | 8:04 | BR40 - GND | encoder 0V (BR40 - GND) | XC4 4 | sure |
| 18 | IN-GND | 7XC4 | 8:03 | BR40 - STÍNĚNÍ | encoder cable shield (BR40 - STÍNĚNÍ) | XC4 shell | sure |
| 19 | OUT-0 | A1K2 | 5:16 | BLOKOVÁNÍ POSUV - ŘEZ | feed-cut interlock | K2 A1 | sure |
| 20 | OUT-1 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 21 | OUT-2 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 22 | OUT-3 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 23 | OUT-4 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 24 | OUT-5 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 25 | OUT-6 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 26 | OUT-7 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 27 | OUT-8 | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 28 | OUT-9 | 13KM8 | 5:15 | OVLÁDÁNÍ Y3 | control of Y3 | KM8 13 | `[?]` |
| 29 | OUT-A | - | - | - | not used on the paper (no lead, no row in table (40)) | - | sure |
| 30 | OUT-B | E3UZ1 | 2:22 | POSUV VPŘED | backgauge feed forward (POSUV VPŘED) | UZ1 E3 | `[?]` |
| 31 | OUT-C | E4UZ1 | 2:23 | POSUV VZAD | backgauge feed backward (POSUV VZAD) | UZ1 E4 | `[?]` |
| 32 | OUT-D | 28UZ1 | 2:24 | BLOKOVÁNÍ UZ1 | inverter UZ1 blocking (enable input 28) (BLOKOVÁNÍ UZ1) | UZ1 28 | `[?]` |
| 33 | OUT +24V | 5XC4 | 8:04 | BR40 - +24V | encoder supply +24V (BR40 - +24V) | XC4 5 | sure |
| 34 | OUT-GND | 39UZ1 | 2:21 | UZ1 - GND | inverter digital ground (UZ1 - GND) | UZ1 39 | sure |
| 35 | +24V PLC | 35X10 | 6:17 | NAPÁJENÍ PLC | PLC supply +24V | X10 35 | sure |
| 36 | GND PLC | X5 | 2:01 [?] | NAPÁJENÍ PLC | 0V | X5 | sure |
| 37 | XC50 pins 6+9 | 7UZ1 | 2:25 | ŘÍZENÍ RYCHLOSTI SEDLA | backgauge speed control (ŘÍZENÍ RYCHLOSTI SEDLA) | UZ1 7 | sure |
| 38 | XC50 pin 4 | 8UZ1 | 2:26 | ŘÍZENÍ RYCHLOSTI SEDLA | backgauge speed control (ŘÍZENÍ RYCHLOSTI SEDLA) | UZ1 8 | sure |
| 39 | XC60 pin 2 | 3XC70 | 8:03 / 8:04 | PROPOJENÍ PLC-TABLO | PLC-TABLO link (PROPOJENÍ PLC-TABLO) | XC70 3 | sure |
| 40 | XC60 pin 3 | 2XC70 | 8:03 / 8:04 | "(STÍNĚNÍ PŘIPOJENO" = first half of the printed remark "shield connected to the metal shell of the connector" (it belongs to the link shield, the shell row, not to this pin) | PLC-TABLO link (PROPOJENÍ PLC-TABLO) | XC70 2 | sure |
| 41 | XC60 pin 5 | 5XC70 | 8:03 / 8:04 | "NA KOVOVÝ PLÁŠŤ KONEKTORU)" = second half of that remark | PLC-TABLO link (PROPOJENÍ PLC-TABLO) | XC70 5 | sure |

The 16 unused rows are `sure` by the print; photo 20261102_144328 shows no wire on the unused inputs and on outputs 1-7, and about four wires among outputs 8-D whose markers it cannot read (hence the `[?]` of OUT-9, OUT-B, OUT-C and OUT-D).

The field devices behind the far ends (sheets 5-7, thread t2): S28 13-14 behind 30X10 and S30 13-14 behind 29X10, both NO (normally open); S27 21-22 behind XC2 3 and S24 21-22 behind XC2 2, both NC (normally closed); BMR1 23-24 is the cut-control module's cut-done contact; KM8 13-14 then the coil of K1, which switches the air-cushion valve Y3. Inputs read a switched +24 V. Photo 20261102_144328 against these rows: section 3.

## 5. Backgauge positioning as wired

What sheet 8 lets the PLC do, step by step. The program (ADAST154.PGP) is not read in this episode, so the order in which it uses these signals is an estimate; each step names its wires and its mark.

1. Enable the drive: OUT-D → 28UZ1 → UZ1 terminal 28, the controller enable (wire `[?]`: output marker unreadable, and at UZ1 the marker reads 20 or 28). Terminal 28 HIGH (12-30 V) lets the inverter run, LOW inhibits it (Lenze manual p.4-11, sure). The printed name BLOKOVÁNÍ UZ1 (blocking of UZ1) therefore means: the drive is blocked while OUT-D is off (estimated, the print read against that page). With C142 at its factory value -1- (Lenze p.7-9, sure; the machine's value is unread, on-site item 12) the motor starts as soon as 28 goes HIGH and a direction is given; a LOW edge on 28 also resets a fault if C170 is -0- (Lenze p.7-9, sure for the manual; its factory column is empty for C170, and the machine's value is unread, on-site item 12).
2. Direction: OUT-B → E3UZ1 → E3 forward (POSUV VPŘED), OUT-C → E4UZ1 → E4 back (POSUV VZAD) (wires `[?]`, the same unreadable markers). This works only if UZ1's C007 is set to one of -14- to -22-, where E3 means CW (clockwise) and E4 CCW (counter-clockwise), each also a QSP (quick stop) input. With the factory value -0- E3 would brake the motor (direct current injection) and E4 would only choose the direction (estimated; read C007 on site). Which turning direction moves the backgauge forward depends on how M2 is connected, which sheet 8 does not show.
3. Speed: the PLC's ANALOG OUTPUTS port (that XC50 is the plug on it: estimated, on-site item 3) → XC50 pin 4 → 8UZ1 → UZ1 terminal 8, the setpoint; XC50 pins 6+9 → 7UZ1 → terminal 7, its reference (wires sure, table (40); spec/power.md: a shielded pair). Pin 4 is I1 (current output 1) by the port legend (estimated), so UZ1's setpoint jumper would sit at 5-6 (0-20 or 4-20 mA) with C034 choosing between the two; a voltage output would need jumper 1-2 (0-10 V) or 3-4 (0-5 V). Not seen: on the on-site list. The console has keys for a fast and a slow feed (section 8), so the PLC sets at least two speeds (estimated).
4. Position: BR40 channel A → 3XC4 → IN-F, channel B → 2XC4 → IN-E, index → 1XC4 → IN-D; BR40 + from the PLC's +24V (5XC4), − to IN-GND (4XC4), cable shield to IN-GND (7XC4) (wiring sure; encoder type `[?]`). The PLC counts the A/B pulses, 1000 per turn by all three type candidates ("P39SSPPBI1000", "Imp. 1000", "1000P"; the 1000 of the OM's type code read as pulses per turn is estimated; section 7); the step from pulses to millimetres (spindle pitch) is not on sheet 8.
5. Reference: not printed. The index (IN-D) marks one point per encoder turn (estimated: what an index channel gives; the encoder type is `[?]`, section 7); the console key legend has a calibration key ("SD KALBRĒšanas po…"), so a reference run exists, but which switch or mark it uses is the program's (estimated, episode 3). The OM p.41 §8.4 (20261115_022638, Fig. 8.1) sets the zero by hand: with the backgauge at a measured distance from the cut line, loosen the screws 2 of the encoder coupling 1, turn the encoder shaft until the display shows that distance and tighten the screws (sure for the OM; section 7).
6. End positions: S24 front → 2XC2 → IN-A and S27 rear → 3XC2 → IN-9, both NC contacts 21-22 (sure): the input is high while the backgauge is away from that end and drops at the end, or on a broken wire. Sheet 8 shows them only on PLC inputs, so stopping there is the program's task; the OM p.41 §8.3 (20261115_022638) says so: the feed is limited by software at the end positions and secured by the limit switches S24 (front) and S27 (rear) (sure for the OM).
7. Clamp: S30 (clamp position, top) → 29X10 → IN-2 and S28 (clamp plate) → 30X10 → IN-1 (sure). The OM p.41 (20261115_022638) says the backgauge does not move unless the clamp is at the top (sure for the OM; how the program enforces it is not read).
8. Feed-cut interlock: OUT-0 → A1K2 → K2 coil (sure); K2's contact feeds +24V from 35X10 to BMR1 terminal 17 (6:17), so the cut-control module knows when a feed is under way (estimated). Whether +24V on 17 allows or blocks the cut is not printed (`[?]`, spec/control.md, section 5).
9. Drive state: UZ1 relay K1, common K12 → K12UZ1 → IN-8, normally open contact K14 fed +24V from 34X10 (sure): IN-8 is high while K1 is switched. With C008 at its factory value -1- (Lenze p.7-4, sure; the machine's value is unread, on-site item 12) that means a fault (TRIP); the printed name SIGNÁL FUNKCE POHONU (drive function signal) reads more like ready or running, and the red ink names a sensor at the end of the clamp stroke instead (`[?]`, sections 6 and 10).
10. Cut done: BMR1 23-24 → 24BMR → IN-0 (sure) tells the PLC that the cut has ended, presumably so that the next position of a cut program can follow (estimated).

## 6. Inverter UZ1, control side

Lenze EVF8202-E-V002 (8200 series; plate photo 20261102_144201: input "1/N/PE AC 230V 9.0A 50/60Hz", one phase, neutral and protective earth, AC (alternating current); output "3/AC 0-230V 4.0A 0.75kW 0-480Hz"). It drives the backgauge motor M2; power side in spec/power.md. Terminal functions from the Lenze manual p.4-11 and 4-12 (`preparatory_data_analysis/maxima_documents/operating_instructions_global_drive_frequency_inverters_8200_series/20261112_222008.jpg`, `20261112_221856.jpg`) and its parameter pages; tables `15_lenze_terminals.csv` and `15_lenze_parameters.csv` in `static_dynamic_memory/blocks/generation_002/artifacts/tables/`.

| Terminal | Lenze function | Sheet 8 | Factory setting and what the machine needs |
|---|---|---|---|
| 7 | GND1, reference of the analog signals | ← XC50 6+9 (7UZ1, 2:25) | - |
| 8 | setpoint input against 7: 0-10 V (jumper 1-2), 0-5 V (3-4), 0-20 or 4-20 mA (5-6) | ← XC50 4 (8UZ1, 2:26), backgauge speed (ŘÍZENÍ RYCHLOSTI SEDLA) | C034 -0- (0-20 mA, 0-5 V, 0-10 V), -1- 4-20 mA. If XC50 pin 4 is the PLC's current output I1 (estimated), the jumper sits at 5-6 |
| 28 | controller enable RFR (Reglerfreigabe): HIGH 12-30 V, LOW 0-3 V; a LOW edge resets a fault (with C170 -0-, p.7-9) | ← OUT-D (28UZ1, 2:24), inverter blocking | C142 -1-: starts by itself when 28 goes HIGH |
| E3 | factory: DC (direct current) injection brake, HIGH = active | ← OUT-B (E3UZ1, 2:22), forward | C007 -0- gives E3 = brake, E4 = direction. Forward on E3 and back on E4 need C007 -14- to -22- (E3 = R/QSP: right, CW, or quick stop; E4 = L/QSP: left, CCW, or quick stop; the print runs the two together, split `[?]`) |
| E4 | factory: direction, LOW = CW, HIGH = CCW | ← OUT-C (E4UZ1, 2:23), back | see E3 |
| 39 | GND2, reference of the digital inputs; minus of an external 12-30 V supply | → PLC GND (39UZ1, 2:21) | the PLC's 24 V outputs drive E3, E4 and 28 against 39 |
| K12 | relay K1, common contact | → IN-8 (K12UZ1, 2:25) | K14 (normally open) takes +24V from 34X10 (sheets 2 and 6), so IN-8 is high while K1 is switched. C008 -1-: K1 switches on TRIP (a fault). The print names the signal "drive function", which reads like -0- ready or -2- motor running: read C008 |

Not used on sheet 8: 9 (5.2 V setpoint supply), 20 (12 V supply of the inputs), 62 (analog output), E1 and E2 (the fixed frequencies JOG1 to JOG3), K11 (normally closed contact). The manual's table on p.4-11 prints "K 22" and "K 24" where its figures print K12 and K14; sheet 8 writes K12UZ1. Relay rating: 24 V AC 3.0 A or 60 V DC 0.5 A.

With the factory C007 -0-, OUT-B would brake the motor instead of driving it forward, so the machine's C007 is most likely not the factory value (estimated); C001 -0- (factory) takes the setpoint from terminal 8 and the commands from the terminals, which fits sheet 8. Values to read on the unit with the keypad: C001, C007, C008, C034, C142, C170 (on-site item 12).

Faults the unit shows (Lenze manual p.8-3 to 8-6, photos 20261112_233441, 233856, 234023; table `15_lenze_faults.csv`): LU (undervoltage); OC1 (short circuit); OC2 (earth fault); OC3 and OC4 (overload while accelerating or braking); OC5 "I x t – Überlast" (I x t overload) and OC6 "Überlast Motor" (motor overload) on p.8-3, the two texts swapped on p.8-6; OH and OH4 (overheating); OU and OUE (overvoltage). A fault is reset with the STP (stop) key, a LOW edge on terminal 28 (OUT-D off and on again) or by switching the mains off; the key and the LOW edge work with C170 -0- (Lenze p.7-9).

Photo 20261102_144205 shows the markers 7, 8, K12, K14, E4, E3 `[?]` and one that reads 20 or 28 on the control terminals. Terminal 39 is in the picture too: its legend stands below E4 and a wire with an orange ferrule enters it, but that wire's marker is hidden and its far end is not seen (on-site item 13).

## 7. Encoder BR40 and connector XC4

- Print: BR40 has the pins A, B, I (index), + and −; the harness runs through XC4 (contacts 1 I, 2 B, 3 A, 4 −, 5 +) to the PLC: A on IN-F, B on IN-E, I on IN-D, − on IN-GND, + from the PLC's second +24V terminal. 7XC4 bonds the cable shields of both halves of XC4 to IN-GND. Sheet 8 thus wires an incremental encoder with two channels and an index.
- OM p.41 (20261115_022638) calls the sensor absolute (абсолютный ротационный датчик, absolute rotary sensor): sheet 8 and the wired inputs D, E, F (photo 144328) rule; on the on-site list. Its §8.4 calibration (turn the encoder shaft in its coupling until the display shows the measured distance, section 5 step 5) fits an absolute sensor and equally an incremental one whose index fixes the zero of a reference run, so it does not settle the type.
- Type, not printed on sheet 8. Three candidates:
  1. OM p.46 (20261115_023023): "EUCHNER P39SSPPBI1000-123-24".
  2. Blue ink above the title block, bracketed with a handwritten "BR40" (20261113_191800): "EUCHNER PA50/Welle 06/Imp. 1000", "Ident.Nr. 075043 Volt 5-30 Ver. 24", "Seriennummer: 9813 12 344", and "PA50-06-1000-24": read like a nameplate copied by hand (Welle = shaft, 6 mm; Imp. = pulses per turn, 1000; Ident.Nr. = identification number; Volt 5-30 = supply range; Ver. = version `[?]`).
  3. Blue ink at the top right of the sheet, under the title of table (40), not at BR40 (20261113_191800): "OMRON 1000P E6B2-CW26C" (1000P = 1000 pulses per turn). Omron sells no E6B2-CW26C; the E6B2-CWZ6C has an NPN (negative-positive-negative transistor) open-collector output and a cable of at most 2 m (W, `static_dynamic_memory/blocks/generation_002/artifacts/web/omron/rs_9200d9fd.pdf`). An open collector pulls to 0 V, while the B&R inputs need a switched +24 V ("sink", W): without pull-up resistors such an encoder could not drive them. If an Omron is fitted, it is a later replacement and its wiring has to be checked.
- XC4 against XC40: the OM p.20 (20261115_011308) writes XC40; sheet 8, sheet 1's connector table and the OM p.41 and p.47 write XC4. XC4 is used.
- Place: photo 20261102_144555 shows on the cabinet face, just above and right of the row of three heavy-duty connectors (XC2 top, XC1, XC3 lowest; `17_cable_routes.csv` lines 10-12), a round connector with a knurled brass nut and a thin white cable, beside a yellow wall label read "XC4" [?] (`17_cable_routes.csv` line 13: seen; label and function [?]). The OM p.48 (20261115_023222) Fig. 10.2, view P, puts XC4 second (round) on the connector plate (`18_manual_device_list.csv` line 72, whose source column names only p.47, 20261115_023118, the parts list of that figure with XC4's order numbers and type). Photo: above and right of the row; OM: second in the plate's order. Whether these are one place is on-site item 2, with the label and the contacts.

## 8. Console terminal TABLO and the serial link

- Print (sheet 8 top, photo 20261114_015721): TABLO = OVLÁDACÍ TABLO, control panel in the console, drawn from its rear (POHLED ZE ZADNÍ STRANY). Its terminal block: ⏚ from ⏚X10, − from 45X10 (which X5 feeds), + from 33X10, printed "(6:15)" (the +24V feed of sheet 6; control_wires.csv gives 6:14-15). Sheet 8 prints no voltage there; the "+24 V DC" of the TABLO device row comes from sheet 6, which prints "TABLO +24V (8:03)" (photo 20261114_014325). Three sockets on its right edge, the middle one XC70 with the arrow "XC70 ⇒ PLC".
- Photos (20261102_151912 to 152107): B&R "4E0040.01-590", a keypad module (estimated, by the 4E family, OM p.46), display module "4D1084.00-590", board "22511030/2", a supply plug with PE (152038). Console photo 151959: a board with three D-sub sockets and a power plug, no XC label. The OM p.46 (20261115_023023; extract `18_manual_device_list.csv` line 40) names the same display, 4D 1084.00-590, for the PS machines, which agrees with the photo; its panel controller 4C 2000.01-510 is not seen, and its keypads 4E 0041/0011/0021.01-590 differ from the 4E module seen: on the on-site list (item 16).
- Link (table (40)): 2 XC60 → 3XC70, 3 XC60 → 2XC70, 5 XC60 → 5XC70, and "(STÍNĚNÍ PŘIPOJENO NA KOVOVÝ PLÁŠŤ KONEKTORU)" (shield connected to the metal shell of the connector) without saying at which end: `XC60 shell -> XC70 shell` is drawn bonded at both shells and marked `[?]`.
- Reading of the link (estimated): XC60 is the PLC's IF1 RS232 port (a plug sits there, photo 142944). Its legend, counted like the full legend of IF2, gives 3 TxD (transmit data) and 5 GND, so 2 RxD (receive data). The B&R panel controller 4C2000.01-510 has on its IF1 2 RxD, 3 TxD, 5 GND (W: PANELWARE manual p.99, saved as `static_dynamic_memory/blocks/generation_002/artifacts/tables/22_web_b_br_connectors.csv` lines 11-15); that is the controller the OM names, not one seen fitted (on-site item 16), so the reading stays estimated. Pins 2 and 3 crossed and 5 to 5 then make a null-modem link: the PLC sends on 3 to the panel's 2 and receives on 2 from the panel's 3.
- Keys (control panel manual sheet 20261103_233320, a Latvian key legend, no parameter table): MANUAL "Rokas režīms" (manual mode); SERVICE with F1 (function key 1; F2 to F4 likewise) "Izdzēst visas programm[as]" (delete all programs); F1 "Programmas sākums" `[?]` (program start); F2 "Ailes [?] izdzēšana" (entry deletion); F3, F4 to the program start and end; "ĀTRĀ PADOŠ[ana]" and "LĒNĀ PAD" (fast and slow feed); "PROD. IZSTUMŠ" (push-out); "KOMPRESORA VAD. ar pārtraukumiem" (compressor control, intermittent); "SD KALBRĒšanas po…" (calibration); ESC (escape) "IZEJA NO UZDEVUMA" (exit task); NEXT "TURPINĀŠANA / Apstiprināšana" (continue, confirm); DEL (delete) "IZDZĒŠANA"; ENTER "Apstiprināšanas pog[a]" (confirm key).

## 9. Differences with t1 and t2 (for t5, the merge)

1. TABLO 0 V: `power_wires.csv` line 37 "X5 -> TABLO -" skips 45X10. Sheet 8 (20261114_015721) routes it X5 → 45X10 → TABLO −, and photo 20261102_144309 shows the field sleeve 45 on X10: the rows `X5 -> X10 45` and `X10 45 -> TABLO -` here describe it. t5 keeps these two and drops line 37 (the netlist script prints it as UNMATCHED with this reason).
2. Wire labels: the 8 conductors shared with `power_wires.csv` (lines 36, 95-101) have an empty `wire` there; here they carry the label sheet 8 prints (X5, 39UZ1, E3UZ1, E4UZ1, 28UZ1, 7UZ1, 8UZ1, K12UZ1). t5 takes the label from here.
3. Marks of the shared conductors: OUT-B, OUT-C and OUT-D to UZ1 are `[?]` here (output markers unreadable in photo 144328) and "estimated ±1 column" in t1's rows (the column on sheet 2); UZ1 7 and 8 to XC50 are `sure` here (table (40) names the pins) and "estimated ±1 column" there. Each mark is right for its own sheet: t5 keeps the weaker mark for the conductor and both columns.
4. `plc_address` of `X10 35 -> PLC +24V`: "+24V PLC" here (table (40)), empty in control_wires.csv line 192.
5. Device rows of this thread that t1 or t2 also wrote: PLC and TABLO in `control_devices.csv` (t2's copies, TABLO in column 03-05 there, 01-03 here), XC4, XC50, XC60 and XC70 in `power_devices.csv` (t1's rows from sheet 1's connector table, without sheet-8 data). Rows from here win for these seven devices.
6. Columns against the sheet-8 paths table (`12_568_sheet8_paths.csv`): 33X10 01-03 there, 03-04 here; XC70 02 there, 03 here; 3XC70, 2XC70, 5XC70 04-05 there, 03-04 here. Here each column is the ruler tick the conductor stands under (measured on photo 20261113_191800); the netlist script prints these as INFO.
7. Printed references kept as printed: "(6:15)" at 33X10 (control_wires.csv: 6:14-15); "GND PLC X5 2:01" in table (40) (X5 is at 2:02).
8. Lines drawn that the paper does not draw (stated in the sheet's notes): the four conductors of the link XC60-XC70, the two from XC50 to UZ1 7 and 8, and the harness XC4-BR40 as five parallel conductors (the paper prints one bus line).
9. Copied device rows keep their owner's text: K2's row is t2's, and its type_rating says "coil voltage not read (24 V DC from the PLC, estimated)" in a row marked `sure`. That estimate is t2's (spec/control.md); t5 takes it with the row from `control_devices.csv`.

## 10. Conflicts between sources

| # | Point | Print (rules unless a photo shows otherwise) | Other source | Handling |
|---|---|---|---|---|
| 1 | IN-8 | K12UZ1, drive function signal (2:22-25) | red ink left of the table (20261113_191800): "IN-8.-д. в конце хода пресса со вст." (IN-8 - sensor (д. = датчик) at the end of the clamp stroke; "со вст." not resolved) `[?]` | print kept; ink quoted; on-site list |
| 2 | IN-0 to IN-2 | cut done, S28, S30 | red ink right of those rows: "короткий сто[п] – верх. пол. пр[есса]" (short st[op] – top position of the clamp) `[?]` | quoted only |
| 3 | Y3, air cushion | OUT-9 → 13KM8 → K1 → Y3 | OM p.42 (20261115_022721): "управляется преобразователем частоты UZ1" (controlled by the inverter UZ1); set 567-70.9006 drives its air-cushion relay from UZ1's relay K14, so the OM likely follows that set (estimated) | print kept (t2's rows) |
| 4 | BR40 type | not printed | three candidates (section 7) | on-site list |
| 5 | BR40 kind | incremental A, B, index | OM p.41: absolute | print and photo kept |
| 6 | Outputs 9, B, C, D | OUT-9, B, C, D | photo 144328: a wire on 9 or 8, ferrules on B, C, D, markers unreadable | `[?]` |
| 7 | UZ1 terminal of OUT-D | 28 | photo 144205: marker reads 20 or 28 | `[?]`, on-site list |
| 8 | TABLO modules | not printed | photos 4E0040.01-590, 4D1084.00-590 against OM 4C 2000.01-510 and 4E 0041/0011/0021.01-590 (the OM's display 4D 1084.00-590 agrees) | photos win for what is fitted; on-site list |
| 9 | X5 reference | terminal label "X5 (2:02)" | table (40): "X5 2:01" | table text kept as printed with `[?]`; on-site list |
| 10 | XC4 | XC4 | OM p.20: XC40 | XC4 |

## 11. On-site list

Each `[?]` or estimated row of this thread has its key in backticks; the other items are checks of the same weight that have no row of their own.

| # | Key | What to check | Where | Why |
|---|---|---|---|---|
| 1 | `BR40` | read the encoder's label: maker, type, pulses per turn, output (push-pull or NPN open collector), supply; measure the cable length to XC4 | backgauge drive at the machine | type not printed; three candidates (OM p.46, blue ink twice); NPN output against the "sink" inputs (section 7); OM p.41 "absolute" |
| 2 | `XC4` | find XC4, read its label and pin count, follow contacts 1-5 and the shield; whether the round connector above and right of the heavy-duty row (photo 144555) is the second one on the connector plate (OM p.48 Fig. 10.2 view P) | cabinet wall to the machine (also t1's on-site item 2) | photo 20261102_144555: a round connector beside a yellow wall label read "XC4" [?] (`17_cable_routes.csv` line 13); OM p.20 writes XC40 |
| 3 | `XC50` | confirm that the plug on ANALOG OUTPUTS is XC50; which pin carries UZ1 8 (4 = I1, a current output, or a voltage pin); the jumper at UZ1 terminal 8 (1-2, 3-4 or 5-6) and C034 | PLC front; UZ1 control board | pin read from the legend count (estimated); no XC label in photo 142944 (also t1's item 4) |
| 4 | `XC60` | confirm that the plug on IF1 RS232 is XC60 and that pins 2, 3, 5 and the shell are wired; which of pins 2 and 3 sends (TxD) | PLC front | no XC label in photo 142944; TxD on pin 3 is counted from the port legend (estimated, section 8; notes of 2XC70 and 3XC70) |
| 5 | `XC70` | find XC70 behind the console: the middle of three sockets; pins 2, 3, 5 and shell; which of pins 2 and 3 sends (TxD) | console, rear of the panel | photo 20261102_151959: a board with three D-sub sockets and a power plug, no XC label; that the panel sends on 3 is the crossed reading of section 8 (XC60 2 → XC70 3, XC60 3 → XC70 2; estimated) |
| 6 | `XC60 shell -> XC70 shell` | at which end the link shield is bonded to the shell (one end or both) | both plugs of the link cable | table (40) does not say |
| 7 | `XC2` | t2's device: label and pins 1-9 of the table-cabinet connector | cabinet entry (spec/control.md, on-site list) | t2's `[?]` row, copied here |
| 8 | `PLC OUT-9 -> KM8 13` | which output carries 13KM8: 9 or 8 | PLC output row, wire markers | markers unreadable in photo 144328 |
| 9 | `PLC OUT-B -> UZ1 E3` | marker of the wire on output B and at UZ1 E3 | PLC output row; UZ1 | markers unreadable (144328, 144205) |
| 10 | `PLC OUT-C -> UZ1 E4` | marker of the wire on output C and at UZ1 E4 | PLC output row; UZ1 | markers unreadable |
| 11 | `PLC OUT-D -> UZ1 28` | marker of the wire on output D; at UZ1 whether it lands on 28 (enable) or 20 | PLC output row; UZ1 | photo 144205 reads 20 or 28 |
| 12 | UZ1 parameters | read C001, C007, C008, C034, C142, C170 with the keypad | UZ1 | E3/E4 as forward/back needs C007 -14- to -22- (factory -0-); C008 decides what IN-8 reports; C170 whether a LOW edge on 28 resets a fault |
| 13 | 39UZ1 | that the wire in UZ1 terminal 39 runs to the PLC's GND | UZ1 | photo 144205: a wire with an orange ferrule in terminal 39, its marker hidden, its far end not seen |
| 14 | IN-8 | what the wire on IN-8 comes from: UZ1 K12 (print) or a sensor at the end of the clamp stroke (red ink) | PLC IN-8 and its far end | ink against print (section 10) |
| 15 | X5 reference | that both references (2:01 in table (40), 2:02 on the terminal label) mean the one strip X5 | X5 | paper only (also t1's item 40) |
| 16 | TABLO modules | read the module labels and the panel controller behind the console | console | photos against OM p.46 |
| 17 | +24V at X10 | that the bridge over X10 31-36 feeds 33X10 (TABLO) and 35X10 (PLC) | X10 | photo 144309 shows the bridge, not each feed |

## 12. Sources

Paths from the project folder. Sheet photos are in `preparatory_data_analysis/maxima_documents/adast_guillotine_wiring_and_plc_diagrams/`, cabinet and console photos in `preparatory_data_analysis/maxima_photos/` (stems 20261102_), OM pages in `preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/`, Lenze pages in `preparatory_data_analysis/maxima_documents/operating_instructions_global_drive_frequency_inverters_8200_series/`.

| Figure or number in this text | Source |
|---|---|
| sheet 8 bottom: PLC rows, D-sub sockets, XC50, XC4, BR40 | 20261114_015117.jpg |
| XC4 seen: round connector beside a yellow wall label read "XC4" [?] | maxima_photos/20261102_144555.jpg; `static_dynamic_memory/blocks/generation_002/artifacts/tables/17_cable_routes.csv` line 13 |
| XC4 second (round) on the connector plate, Fig. 10.2 view P | OM 20261115_023222.jpg (p.48; the parts list on p.47, 20261115_023118.jpg, gives XC4's order numbers and type); `static_dynamic_memory/blocks/generation_002/artifacts/tables/18_manual_device_list.csv` line 72 |
| sheet 8 top: TABLO, its terminals, XC70, 33X10 "(6:15)", 45X10 | 20261114_015721.jpg |
| TABLO supply +24 V DC: sheet 6 prints "TABLO +24V (8:03)" | 20261114_014325.jpg (sheet 6); `control_wires.csv` line 185 |
| table (40), the ruler ticks, the red and blue ink | 20261113_191800.jpg |
| B&R COMPACT P.L.C., 16 inputs, 14 outputs, 1 A, 7 A, fuse 1.25 AT, wired terminals | maxima_photos/20261102_144328.jpg |
| ports IF1-IF5, ANALOG OUTPUTS and INPUTS, plugs on IF1 and ANALOG OUTPUTS, program label | maxima_photos/20261102_142944.jpg |
| X10 markers 29-45, bridge 31-36, field sleeves 33 and 45 | maxima_photos/20261102_144309.jpg |
| UZ1 plate: EVF8202-E-V002, 230 V, 9.0 A, 4.0 A, 0.75 kW | maxima_photos/20261102_144201.jpg |
| UZ1 control terminal markers; a wire in terminal 39 | maxima_photos/20261102_144205.jpg |
| TABLO modules 4E0040.01-590, 4D1084.00-590, board 22511030/2, plug with PE | maxima_photos/20261102_151912.jpg to 20261102_152107.jpg (151937, 151951, 151959, 152038) |
| "BR COMP 1-0" | OM 20261115_023314.jpg (p.49) |
| EUCHNER P39SSPPBI1000-123-24; display 4D 1084.00-590, controller 4C 2000.01-510, keypads 4E 0041/0011/0021.01-590 | OM 20261115_023023.jpg (p.46); `18_manual_device_list.csv` line 40 |
| absolute rotary sensor; no feed unless the clamp is at the top; feed limited by software, S24 and S27 at the ends (§8.3); zero set by turning the encoder shaft in its coupling (§8.4, Fig. 8.1) | OM 20261115_022638.jpg (p.41) |
| Y3 "controlled by the inverter UZ1" | OM 20261115_022721.jpg (p.42) |
| XC40 | OM 20261115_011308.jpg (p.20) |
| UZ1 terminals 7, 8, 9, 20, 28, 39, 62, E1-E4, K11, K12, K14 | Lenze 20261112_222008.jpg, 20261112_221856.jpg (p.4-10 to 4-12); `15_lenze_terminals.csv` |
| C001, C007, C008, C034, C142, C170 with their factory values (C170: none printed) | Lenze 20261112_223857.jpg, 232414, 232729, 232907, 233119; `15_lenze_parameters.csv` |
| fault codes LU to OUE | Lenze 20261112_233441.jpg, 233856, 234023; `15_lenze_faults.csv` |
| key legend of the console | `preparatory_data_analysis/maxima_documents/control_panel_manual/20261103_233320.jpg` |
| BRCOMP1.0 inputs "sink" | `static_dynamic_memory/blocks/generation_002/artifacts/web/br-automation/brcomp1-0.html` (W) |
| E6B2-CWZ6C open collector, cable ≤ 2 m | `static_dynamic_memory/blocks/generation_002/artifacts/web/omron/rs_9200d9fd.pdf` (W) |
| IF1 of the panel controller 4C2000.01-510 (the OM's controller, not seen fitted: on-site item 16): 2 RxD, 3 TxD, 5 GND | PANELWARE manual p.99 (W), saved as `static_dynamic_memory/blocks/generation_002/artifacts/tables/22_web_b_br_connectors.csv` lines 11-15 |
| 41 rows of the PLC table, 21 rows of the paths table | `static_dynamic_memory/blocks/generation_002/artifacts/tables/12_568_plc_io.csv`, `12_568_sheet8_paths.csv` |
| 14 devices, 35 wires, 11 rows not sure, 17 shared | netlist script output, line 1 (section 1) |
| counts of the drawing (wire rows drawn, pins, junction dots, texts, table (40) rows) | drawing script output, line 1 (section 1) |

What a report on this sheet has to mention: that sheet 8 wires an incremental encoder whose type is unknown (three candidates, one of them unfit for these inputs as wired); that UZ1 needs a non-factory C007 for the forward and back commands and that its parameters were not read; that four of the five output wires (9, B, C, D) are read from the print, not from the photo; and that the red ink on IN-8 names another signal than the print.
