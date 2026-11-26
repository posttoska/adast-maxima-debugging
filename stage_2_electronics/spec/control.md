# Control circuits of the Adast Maxima MS 115 PS: set 568-70.9001, sheets 4-7

Thread t2 (control) of episode 2. It redraws sheets 4-7 of the 1998 wiring set 568-70.9001 (SCHÉMA ZAPOJENÍ, MS 80 PS, DS, MS 115 PS, DS): sheet 4 lighting and contactor control, sheet 5 electromagnets and the PLC (programmable logic controller) field signals, sheet 6 inputs 1-18 of the cut-control module BMR1 (MODUL ŘÍZENÍ ŘEZU), sheet 7 its outputs 19-29 and supply. The power side (sheets 1-3) is thread t1's (`spec/power.md`), the PLC and inverter (sheet 8) thread t3's, the merge thread t5's.

Rules of this thread: the cabinet photos rule what is wired; where they cannot tell, the 1998 print rules; red and blue ink on the annotated copy is a later technician's remark, quoted as ink and never taken as print. Every device and wire row carries a mark: `sure`, `[?]` (unclear), `estimated ±<error>` or `W` (web, weaker evidence), and its source paths. Every `[?]` or estimated row has an entry in the on-site list (section 11).

Abbreviations: OM = operating manual MS 80/115 PS, DS (folder `adast_guillotine_operating_manual`); NO / NC = normally open / normally closed contact; AC / DC = alternating / direct current; PE = protective earth; RC = resistor-capacitor suppressor; UG50 = power-supply board of the cabinet (rectified and AC control voltages); CSV = comma-separated values; SVG = Scalable Vector Graphics; LED = light-emitting diode; IEC = International Electrotechnical Commission (contact numbering); (5:09) = sheet 5, column 09 as printed; "line n" = line n of `netlist/control_wires.csv` (line 1 is the header).

## 1. Files and rebuild

| File | What it holds |
|---|---|
| `schemes_2d/control_netlist.py` | the data (DEVICES and WIRES text blocks with sources and notes) and its self-checks; writes the two CSV files |
| `netlist/control_devices.csv` | 63 device rows: `designation,kind,function_en,term_cz_ru,type_rating,place,sheet,column,evidence,source_path,note` |
| `netlist/control_wires.csv` | 207 wire rows: `wire,from_device,from_terminal,to_device,to_terminal,signal,plc_address,connector,pin,cable,sheet,column,evidence,source_path,note` |
| `schemes_2d/control_draw.py` | reads only the two CSV files; draws the four sheets and checks them |
| `schemes_2d/control_sheet4.svg` ... `control_sheet7.svg` | the redrawn sheets 4-7 with the printed column rulers, zone titles (English, Czech in brackets), notes, device legend and title block |
| `spec/control.md` | this text |

Rebuild from the project folder, netlist first:

```
python -B stage_2_electronics/schemes_2d/control_netlist.py
python -B stage_2_electronics/schemes_2d/control_draw.py
```

Expected output of the netlist script (exit 0):

```
devices 63, wires 207, shared with power 20, open rows (on-site) 8
INFO place filled here, empty in power_devices.csv: V01
INFO place filled here, empty in power_devices.csv: V14
INFO place filled here, empty in power_devices.csv: RC11
INFO place filled here, empty in power_devices.csv: V10
INFO place filled here, empty in power_devices.csv: R10
INFO power row touching sheets 4-7, not here: ('M1', 'PE') -> ('X10', 'PE')
INFO paths rows mapped: 121
INFO on-site keys in the on-site list of spec/control.md: 8 of 8
result: PASS
```

It checks: both headers exact, UTF-8 without byte order mark; one row per designation; one conductor per wire row; marks valid; every source path exists (skipped when `preparatory_data_analysis/` is absent); no absolute or user path; both ends of every wire are device rows (dangling 0) and every device has a wire; the seven PLC addresses of this thread carry the signal texts of the script's PLC_IO list (taken from the PLC I/O table of sheet 8), none on two signals, none missing; the 20 conductors shared with `power_wires.csv` have the same ends; each of the 121 rows of the paths tables of sheets 4-7 maps to existing wire rows (skipped when `static_dynamic_memory/` is absent); the key of every non-`sure` row stands in section 11 of this file; every 6-digit stamp a note names (a photo or a page) is in that row's `source_path` (check 6b), so a quoted photo marker always points at a cited file.

Expected output of the drawing script (exit 0):

```
sheet 4: wire rows 83/83 drawn, cross-references 0, pins 110, junction dots 40, texts 313, overlaps 0, terminal pins side-checked 13, side faults 0, height 1281 px
sheet 5: wire rows 59/59 drawn, cross-references 0, pins 85, junction dots 11, texts 222, overlaps 0, terminal pins side-checked 28, side faults 0, height 1253 px
sheet 6: wire rows 59/59 drawn, cross-references 1, pins 79, junction dots 8, texts 216, overlaps 0, terminal pins side-checked 26, side faults 0, height 1233 px
sheet 7: wire rows 6/6 drawn, cross-references 8, pins 20, junction dots 0, texts 95, overlaps 0, terminal pins side-checked 1, side faults 0, height 688 px
printed labels (PRINTED_LABELS) checked in their columns: sheet 4 7, 5 13, 6 4, 7 7
printed references compared with the paths tables: sheet 4 14, 5 12, 6 8, 7 10; label pairs 67; contact lists 12; differences 0
devices 63 checked on sheets 4-7
result: PASS
```

It checks: every wire row of a sheet drawn; every column of the ruler printed; every printed wire label on its sheet; no two text boxes overlap; each cross-reference arrow matches exactly one row of another sheet; every device designation printed on each sheet it belongs to; at every terminal or connector pin, rows to a cabinet device and rows to a machine or console device leave the pin in different directions, so the sheet never joins the two sides of a terminal; no line passes over a terminal pin it does not end at, nor over a pin of another node; every (sheet:column) reference the sheets print is, per sheet and paired with the label it stands by, a reference of the paths tables of sheets 4-7 read off the scans, and none of theirs is missing (skipped when `static_dynamic_memory/` is absent); the contact list drawn under each coil (sheets 4 and 5) equals the list in that coil's rating field of the paths tables, its NO and NC groups and their order included (same skip); every printed label of the PRINTED_LABELS list (section 3: voltages, the X5 and UG50 references, POUZE MS115, START, the sheet numbers) is drawn in its printed column of the drawing body, as often as the scan prints it. References that differ from the device row are kept as printed: QF1 (2:10) and BMR1 (7:01) on sheet 4, KM6 (4:16) on sheet 5, 13KM3 (4:17) on sheet 7. A copy of the two scripts alone (and this file), without `static_dynamic_memory/`, `preparatory_data_analysis/` and the power CSV files, rebuilds the two CSV files and the four SVG files byte for byte; each script then prints one INFO line for each check it skips. Its whole output in such a copy (`python -I -B`, run from the copy's root, exit 0):

```
devices 63, wires 207, shared with power 20, open rows (on-site) 8
INFO preparatory_data_analysis/ absent: source-path check skipped
INFO power_*.csv absent: agreement check skipped
INFO static_dynamic_memory/ absent: paths coverage skipped
INFO on-site keys in the on-site list of spec/control.md: 8 of 8
result: PASS
```

The drawing script prints the same lines as above, with `INFO static_dynamic_memory/ absent: printed references not compared` in place of the references line.

## 2. Netlist conventions

- Wire label (`wire`): the label 568 prints on that conductor: the terminal name at a strip (37X10, 2X8, 5XC2), the outer strip's name for a strip-to-strip conductor, else the label of a sheet-7 arrow or of the SMER (SMĚR, direction) column of sheet 8 (44QF1, 13KM3, 53KM3, 24BMR, A1K2, 13KM8, 1UG50 ... 18UG50). Empty where 568 prints none. One exception, noted in its row: 61KM6 (line 153) is the photo marker.
- End names: as printed (KM6 61, S10 3A, Y01 +). Where 568 prints none, this thread names them 1 = feed end, 2 = return end: lamps E1-E4, RC1-RC8, RC11, V01, V14, V20, V10, R10, Y11. Y01, Y14, Y10 are printed + and -. The X5 terminal is left empty (568 prints no terminal numbers on X5); the earthing strip is `PE`.
- Node order: 568 never prints in which order the wires of one node run from terminal to terminal. Rows chain in the drawn order or to fit the photo's marker counts; their notes say "order not seen".
- Photo against print: where a cabinet photo read as sure differs from the print, the row follows the photo and its note names the printed value and the photo (the cabinet photos are the main evidence; rule settled on 2026-11-25). Rows: KM7 21-22 for the printed 62-61 (lines 154-155; photos 144205, 144251); 5X11 and 6X11 for the printed 3X11 and 4X11 (lines 144-146; photo 144309; also hand-corrected on the clean sheet 6); K2 11 for the printed 13 (line 198; photo 144324; also hand-corrected). The device rows KM7, K2 and X11 say the same.
- Place: `cabinet`, `console`, `machine`, or empty when the print does not tell. Parts that 568 draws on the field side of the X10 terminals are `machine` (the lamps, magnets and their diodes, the sensors, X8).
- A device on several sheets has one row: sheets joined with "-" and columns with "; " in sheet order (S5 `4-5`, `10; 09`).
- Sources are paths relative to the project folder, several joined with "; ". In the notes a bare 6-digit stamp is the time part of a file name (a cabinet photo or a page); the row's `source_path` holds the full paths. In this text "photo 144259" is `preparatory_data_analysis/maxima_photos/20261102_144259.jpg`, and pages carry their full stem (section 12).

## 3. What each sheet holds (lines of control_wires.csv)

- Sheet 4 (83 rows, lines 2-84): lighting 2-18; main-contactor chain and KM1A/KM1B 19-38; blower contactor KM8 39-42; M1 star-delta (KM2, KM3, KM4, KT1) 43-65; cut contactors KM6, KM7 and delay KT2 66-84. Zones (9)-(15) as printed; pencil "ZN" (KT1) and "ZR" (KT2) on the clean copy shown as ink.
- Sheet 5 (59 rows, lines 85-143): Y01 85-92, Y14 93-98, Y11 99-106, Y10 with the knife-change branch 107-122, PLC field signals and K1, K2 123-143.
- Sheet 6 (59 rows, lines 144-202): BMR1 inputs 1-18 and the +24V bus 33-36X10; timing diagram of the knife sensors (drawn from the clean copy, bar ends estimated ±10 % of the stroke).
- Sheet 7 (6 rows, lines 203-208): BMR1 supplies 21, 25, 27, 0V and output 24; the other outputs (19, 20, 22, 23, 26, 28, 29) and +24V are rows of sheets 4-6 and show on sheet 7 as cross-reference arrows.
- Zone borders on sheets 5-7 follow the columns of each zone's devices; the printed borders were not measured.
- Sheets 4 and 5 end their lines as the scans print them: sheet 4 takes the lamp and coil supplies from the left arrows "12UG50 (3:04)" and "13UG50 (3:04)" with "~24V" at column 01, and every 0V return ends in a printed "(2:02) X5" arrow (sheet 4 columns 01 and 07; sheet 5 columns 02, 04, 07, 10, and 16 from the joined K1/K2 A2). No 0V rail is drawn: 568 prints none.
- Photo stems in the notes: each photo clause names the photo that shows it ("photo 144314: inside wire (red) on 8, bridge 7-8"); where two photos show the same thing the note says so ("also on 144314"). Check 6b of the netlist script (section 1) fails on any stamp a note names that the row does not cite.
- Printed labels: the texts the scans print besides designations, terminal and wire numbers (`PRINTED_LABELS` in `control_draw.py`), each read on the scan named. The drawing script checks each in its printed column of the drawing body (section 1); "drawn at" is the centre x and the lower edge y of the drawn text box, in SVG px.

| Sheet | Printed text | Column | Scan | Drawn at (x, y) |
|---|---|---|---|---|
| 4 | `4:` | 01 | `20261113_232949.jpg` | 39, 52 |
| 4 | `~24V` | 01 | `20261113_232949.jpg` | 93, 159 |
| 4 | `~24V` | 01 | `20261113_232949.jpg` | 93, 189 |
| 4 | `(2:02)` | 01 | `20261113_232949.jpg` | 61, 745 |
| 4 | `(2:02)` | 07 | `20261113_232949.jpg` | 524, 745 |
| 4 | `POUZE MS115` | 09 | `20261113_232949.jpg` | 713, 475 |
| 4 | `+24V` | 20 | `20261113_233009.jpg` | 1534, 163 |
| 5 | `5:` | 01 | `20261113_234959.jpg` | 39, 52 |
| 5 | `+14V` | 04 | `20261113_234616.jpg` | 398, 242 |
| 5 | `~48V` | 07 | `20261113_234616.jpg` | 688, 163 |
| 5 | `+33V` | 10 | `20261113_234616.jpg` | 992, 163 |
| 5 | `⏚` | 01 | `20261113_234959.jpg` | 81, 720 |
| 5 | `⏚` | 02 | `20261113_234959.jpg` | 153, 480 |
| 5 | `⏚` | 06 | `20261113_234959.jpg` | 587, 720 |
| 5 | `⏚` | 07 | `20261113_234959.jpg` | 659, 480 |
| 5 | `(2:02)` | 02 | `20261113_234959.jpg` | 182, 729 |
| 5 | `(2:02)` | 04 | `20261113_234959.jpg` | 384, 729 |
| 5 | `(2:02)` | 07 | `20261113_234959.jpg` | 688, 729 |
| 5 | `(2:02)` | 10 | `20261113_234959.jpg` | 992, 729 |
| 5 | `(2:02)` | 16 | `20261113_235017.jpg` | 1599, 609 |
| 6 | `6:` | 01 | `20261114_014439.jpg` | 39, 52 |
| 6 | `START` | 05 | `20261114_014537.jpg` | 445, 558 |
| 6 | `+24V PLC` | 17 | `20261114_014513.jpg` | 1515, 709 |
| 6 | `+24V` | 18 | `20261114_014325.jpg` | 1605, 718 |
| 7 | `7:` | 01 | `20261114_014711.jpg` | 39, 52 |
| 7 | `+27V` | 03 | `20261114_014711.jpg` | 342, 368 |
| 7 | `+27V` | 07 | `20261114_014711.jpg` | 840, 368 |
| 7 | `11R/25W` | 07 | `20261114_014751.jpg` | 864, 276 |
| 7 | `~24V` | 09 | `20261114_014711.jpg` | 1089, 368 |
| 7 | `+24V` | 13 | `20261114_014711.jpg` | 1588, 192 |
| 7 | `+24V` | 13 | `20261114_014834.jpg` | 1588, 368 |

"POUZE MS115" (only MS 115) belongs to S1, which stands in path 10, but the scan prints it left of S1's mushroom, before the ruler tick 09 (20261113_232949: ticks 08, 09, 10 at about 1709, 1895, 2070 scan px, the text at 1674-1848): column 09, as drawn. The column rulers of 568 are not evenly spaced. `⏚` is the printed earth symbol at the X10 PE terminals of sheet 5.

## 4. Cut cycle as wired

Each contact carries its place on the sheets as (sheet:column), the notation of the print, followed by the lines of `control_wires.csv` that wire it.

1. Main contactors (sheet 4). Q2 in position 0 closes Q2 1-2 (4:08; lines 30, 34) and pulls in KM1A (4:09) and KM1B (4:11) (lines 32-33, returns 37-38) through the chain 13UG50 ~24V → QF1 43-44 → BMR1 19-20 → 14X10 → S5 21-22 → 15X10 → S1 21-22 → 16X10 → 17X10, all in column 4:10 (lines 19-29); KM1A 13-14 with KM1B 14-13 (4:10; lines 29-34) hold them once Q2 leaves 0. Q2 in position 1 closes Q2 9-10 (4:16), fed from QF1 44 over the S4 node (4:12; lines 21-22), and starts M1 star-delta through KT1 (4:16; lines 43-65): the KT1 output closes 4-5 (4:15; IEC 15-18, NO) → KM3 61-62 (4:15) → KM4 (4:15, star); KM4 5-6 (4:13) pulls in KM2 (4:13), which holds through its 13-14 (4:13); KM2 62-61 (4:16) opens the KT1 start input B1-B2 (4:16; lines 63-64); after the set time 4-5 opens and 12-14 (4:14; IEC 25-26) closes → KM4 21-22 (4:14) → KM3 (4:14, delta). Contact types from the maker's face legend (photo 144259); the dial setting is not read (on-site `KT1`).
2. Start (sheet 6). Both buttons within 0,5 s (OM p.7; fault 5.1.6 а): S10 common to BMR1 1 (6:01; lines 144-148), its NC 1A-2A to BMR1 2 (6:02; 149-150), its NO 3A-4A to BMR1 3 (6:03; 151-152); S11 the same on BMR1 6, 7, 8 (6:06-08; 156-162). The other inputs must stand as in section 7.
3. Knife lock. BMR1 21-22 (7:03-04), fed +27V from 1UG50 (line 203), energizes Y01 (5:02) through 18X10 → Y01 → 19X10 → X5 (lines 87-92): the lock pin is pulled; SQ1 (6:09) and SQ2 (6:10) change (BMR1 9-10; lines 163-170).
4. Clamping. BMR1 29 (7:11), whose AC common is terminal 27 (7:09; 14UG50 ~24V, line 207), drives 13KM3 → KM3 13-14 (4:17) → node N1 (lines 66, 68); Q2 3-4 (4:17) bridges KM3 13-14 (lines 67-68). Q2 3-4 is closed in position 0, where M1 is off, and open in position 1, where M1 runs (contact table 2:01-02, 20261113_231128, sure; the whole coil bus of KT1, KM2, KM3 and KM4 hangs on Q2 10, lines 43-65): in position 0 BMR1 29 reaches KM6 without KM3, in position 1 only through KM3 13-14. N1 = KM3 14, Q2 4, KM6 A1, KT2 4, KM3 54, wired in the order Q2 4 - KM3 14 - KT2 4 - KM3 54 - KM6 A1 (lines 68, 70, 75, 69): the order is not seen; it is chosen to fit the photo's marker counts 14KM3 x2, 54KM3 x2 (144247) and 4KT2 x2 (144259). KM6 (4:17) pulls in (line 69; RC6 lines 71-72; return 73): KM6 3-4 (5:07) switches 18UG50 ~48V → 22X10 → Y11 (5:07) → 23X10 (lines 100-106), the hydraulics clamp; KM6 1-2 (4:20) switches 6UG50 +24V to the KT2 coil (4:20; lines 80-84, V20 across it): the cut delay starts.
5. Cut. BMR1 28 (7:10) → 53KM3 → KM3 53-54 (4:19) → N1 (lines 74-75); after the delay KT2 4-5 (4:19; lines 70, 76) energizes KM7 (4:19; RC7 77-78, return 79). KM6 5-6 and KM7 6-5 (both 5:10) in series switch 10UG50 +33V → 27X10 → Y10 (5:10; lines 107-110, 117-122; V10 with R10 in series across Y10): the clutch engages and the knife runs.
6. One button (S10 or S11; 6:01-03, 6:06-08; lines as in step 2) released before the bottom: BMR1 drops 28 and 29 (7:10-11; lines 74, 66), KM6 (4:17) and KM7 (4:19) drop, Y10 (5:10) releases, the knife stops (reaction max. 200 ms, OM p.7).
7. At the bottom S12 (6:11) and S13 (6:12) change (BMR1 11-12; lines 171-179): BMR1 holds the cut alone. S14 (6:13) at the top (BMR1 13; lines 180-183) ends it: outputs off, Y01 drops and the pin locks; BMR1 23-24 (7:05-06), fed +24V from 32X10 (5:13; line 123), reports the cut done to PLC IN-0 (7:06; line 204).

Not printed: the module's internal logic (when it closes each output); when BMR1 25-26 energizes Y14. The OM (p.40, p.42) says Y14 is released at the top by a BMR output driven by S14 and held by KM6; 568 feeds Y14 (5:04) only from BMR1 25-26 (7:07-08; lines 93-98, 205-206): on-site entry 13.

## 5. Interlocks

- Motors. QF1 43-44, BMR1 19-20, S5 21-22 and S1 21-22 (all 4:10) lie in series in the KM1A/KM1B coil chain (lines 19-29): opening any one drops KM1A and KM1B, so M1, UZ1 and M3 lose their supply (power side: `spec/power.md`). The coils of KM2, KM3, KM4 (4:13-15, via Q2 9-10, 4:16) and KM8 (4:12, via S4 3-4, 4:12, line 39) are fed from QF1 44 ahead of BMR1 19-20, S5 and S1 (lines 21-22). No S1 contact reaches BMR1, KM6, KM7 or the magnets; UG50 and BMR1 stay fed (estimated from the print).
- Cut. BMR1 inputs (sheet 6, lines 144-202): S10, S11 two-hand (1-3, 6-8; 6:01-03, 6:06-08), KM6/KM7 feedback NC (4-5; 6:04), SQ1, SQ2 lock pin (9-10; 6:09-10), S12, S13, S14 knife cam (11-13; 6:11-13), Q2 7-8 loop (14-15; 6:14-15; closed only in position 0, M1 off; what BMR1 does with it is not printed [?], on-site entry 22), S30 21-22 clamp at top (16; 6:16), K2 11-14 from PLC OUT-0 (17; 6:17), S19 21-22 knife-change clutch (18; 6:18). The cut contactors get the BMR1 outputs only through KM3 13-14 (4:17) and 53-54 (4:19), i.e. with M1 in delta, or through Q2 3-4 (4:17) in position 0 (M1 off). Whether +24V on input 17 allows or blocks the cut is not printed [?].
- Feed (backgauge; the PLC side is t3's). S30 13-14 (5:13) on IN-2 (lines 127, 135-136): no feed unless the clamp is at the top (OM p.41, 20261115_022638); S24 (5:11) and S27 (5:12) NC on IN-A and IN-9 (lines 129-134): backgauge end positions; PLC OUT-0 → K2 (5:16; lines 142-143) → BMR1 17 (6:17; lines 198-199): feed-cut blocking (BLOKOVÁNÍ POSUV-ŘEZ); OUT-D blocks the inverter UZ1 (sheet 8, t3).

## 6. Safety devices: what each switches off, how a fault shows

Fault items are those of the OM fault list (chapter 5; pages 20261115_013519, 013741, 013757). Neither 568 nor the OM gives a lamp or a code; the PLC input LEDs show the IN states (photo 144328).

| Device (place) | Contact, lines | What it switches off | How a fault shows (OM item) |
|---|---|---|---|
| S1 emergency stop (console; POUZE MS115, MS 115 only) | NC 21-22, lines 26-27 | KM1A, KM1B: M1, UZ1, M3 | no item names S1 |
| S5 belt-pulley cover | NC 21-22, lines 24-25; NO 13-14 in the Y10 knife-change branch, 113-115 | KM1A, KM1B; closes the branch to Y10 for a knife change | M1 will not start: check that the clutch control on the belt-pulley cover is pushed in (5.2.3) |
| S19 knife-change clutch switch | NC 21-22 → BMR1 18, lines 200-202; NO 13-14 in the Y10 branch, 111-113 | the cut, through BMR1 18 | not listed |
| S10, S11 two-hand buttons (front table) | BMR1 1-3, 6-8, lines 144-162 | the cut (KM6, KM7, Y10) when released before the bottom | pressed more than 0,5 s apart: no cut (5.1.6 а); released early: knife stuck in the pile, turn it up by hand (5.1.7 а); after a mains loss both buttons finish the cut (5.2.1) |
| KM6, KM7 feedback | NC 61-62 + KM7 21-22 [?] → BMR1 4-5, lines 153-155 | the next cut, if a contactor hangs | faulty KM6, KM7 or module BMR (5.1.6 в) |
| SQ1, SQ2 lock-pin sensors | BMR1 9-10, lines 163-170 | the cut | lock does not work (5.1.6 г, with Y01) |
| S12, S13, S14 knife cam sensors | BMR1 11-13, lines 171-183 | ends the stroke at the top | vane of S12 badly set: knife stops past the top, no new cut (5.1.8 в) |
| S30 clamp at top | NC 21-22 → BMR1 16, lines 195-197; NO 13-14 → IN-2, 135-136 | the cut (input 16); the backgauge feed (IN-2) | backgauge will not move by motor: check that the clamp is at the top (5.2.4) |
| S28 clamp plate | NO 13-14 → IN-1, lines 137-138 | not printed [?] | not listed |
| K2 feed-cut blocking | 11-14 → BMR1 17, lines 198-199; coil from OUT-0, 142 | the cut while the PLC feeds (allow or block [?]) | not listed |
| Q2 cam switch (M1 run switch) | 7-8 → BMR1 14-15, lines 193-194: closed in position 0 (M1 off), open in position 1 (M1 runs); contact table 2:01-02 (20261113_231128), sure | not printed [?]: BMR1 sees 14-15 closed only with M1 off, the position in which Q2 3-4 lets BMR1 29 reach KM6 (lines 67-69) and Q2 5-6 feeds the knife-change branch to Y10 (lines 108-117); on-site entry 22 | transient mains loss: Q2 to 0, start M1 again (5.2.1) |
| KT2 cut delay | 4-5 in KM7's line, 70, 76 | delays the clutch after clamping | top sheets pulled out of the pile: lengthen the delay (5.1.5 в) |
| Y14 clamp brake | BMR1 25-26, lines 205-206, 93-98 | holds the clamp over the knife edge after an interrupted cut (OM p.42; Supplement 1 check 5) | does not brake: worn lining or gear play (5.1.11) |
| Y10 cut clutch | KM6 5-6 + KM7 6-5, lines 107-122 | the knife drive | no current in Y10: fuses and clutch brushes (5.1.6 б); worn or oily lining (5.1.7 г, д; 5.1.8 б); clutch Y10 not adjusted (5.1.8 а) |
| FF1 light curtain | none | not fitted: certificate "—" (20261113_195028); X11 5-6 likely its bridged place (estimated) | - |

## 7. BMR1 terminals

BMR1 is one relay board with the plate "BMR2" (photo 143021); its maker is neither printed nor seen. Every terminal 1-29, 0V and +24V carries a wire; red (AC) wires on 19, 20, 27, 28, 29 (each seen on photo 143021 and again on photo 144334). Inputs are switched +24V from the bus 33-36X10, fed by 5UG50 (lines 185-189).

| Terminal | Wire label | Wired to | Lines | Sheet:column | Meaning |
|---|---|---|---|---|---|
| 1 | 5X11 | X11 5 → bridge → X11 6 → 4XC2 → S10 3A-1A | 144-148 | 6:01 | S10 common; print 3X11/4X11, wired 5X11/6X11 by the photo |
| 2 | 5XC2 | S10 2A (NC 1A-2A) | 149-150 | 6:02 | S10 at rest |
| 3 | 6XC2 | S10 4A (NO 3A-4A) | 151-152 | 6:03 | S10 pressed |
| 4 | 61KM6 | KM6 61-62 → KM7 22-21 [?] | 153-154 | 6:04 | contactor feedback loop |
| 5 | - | KM7 21 [?] | 155 | 6:05 | end of the loop |
| 6 | 7XC2 | S11 3A-1A | 156-158 | 6:06 | S11 common |
| 7 | 8XC2 | S11 2A (NC) | 159-160 | 6:07 | S11 at rest |
| 8 | 9XC2 | S11 4A (NO) | 161-162 | 6:08 | S11 pressed |
| 9 | 37X10, 2X8 | SQ1 4-1, drawn NO; 1 on 1X8 (+24V) | 163-166 | 6:09 | lock pin |
| 10 | 38X10, 3X8 | SQ2 4-1, drawn NO | 167-170 | 6:10 | lock pin |
| 11 | 39X10, 4X8 | S12 2-1, drawn NC | 171-174 | 6:11 | knife at the bottom |
| 12 | 41X10, 5X8 | X10 41 → X10 42 → S13 2-1, drawn NC | 175-179 | 6:12 | knife at the bottom |
| 13 | 40X10, 6X8 | S14 2-1, drawn NC | 180-183 | 6:13 | knife at the top; 1X8 → 33X10 line 184 |
| 14 | - | Q2 7 | 193 | 6:14 | Q2 loop, closed only in position 0 (M1 off); its use in BMR1 not printed [?] |
| 15 | - | Q2 8 | 194 | 6:15 | end of the loop |
| 16 | 43X10 | S30 21-22 → 34X10 (+24V) | 195-197 | 6:16 | clamp at the top |
| 17 | 35X10 | K2 11-14 → 35X10 (+24V) | 198-199 | 6:17 | feed-cut blocking; print K2 13-14 |
| 18 | 44X10 | S19 21-22 → 36X10 (+24V) | 200-202 | 6:18 | knife-change clutch |
| 19 | 44QF1 | QF1 44 (13UG50 ~24V through QF1 43-44) | 19-20 | 4:10 | contact 19-20 in the KM1A/KM1B chain |
| 20 | 14X10 | X10 14 → S5 21 | 23-24 | 4:10 | |
| 21 | 1UG50 | UG50 1, +27V | 203 | 7:03 | supply of output 22 |
| 22 | 18X10 | Y01 + | 87-88 | 5:02 | knife lock |
| 23 | 32X10 | X10 32, +24V | 123 | 5:13 | supply of output 24 |
| 24 | 24BMR | PLC IN-0 | 204 | 7:06 | cut done (SIGNÁL PROVEDENÍ ŘEZU) |
| 25 | - | R14 2; R14 1 ← 2UG50 +27V; R14 11R/25W | 205-206 | 7:07 | supply of output 26 (line "+14V") |
| 26 | 20X10 | Y14 + | 93-94 | 5:04 | clamp brake (BRZDA LISOVADLA) |
| 27 | 14UG50 | UG50 14, ~24V | 207 | 7:09 | common of outputs 28, 29 |
| 28 | 53KM3 | KM3 53-54 → N1 | 74-75 | 4:19 | KM7 line (through KT2 4-5) |
| 29 | 13KM3 | KM3 13-14 → N1 (Q2 3-4 across) | 66-68 | 4:17-18 | KM6 coil |
| 0V | - | X5 | 208 | 7:12 | |
| +24V | 34X10 | X10 34 (bus 33-36X10) | 191 | 6:16 | |

## 8. PLC inputs and outputs of this thread

Addresses as in the table of sheet 8 (t3); inputs take switched +24V. The PLC is a B&R (Bernecker + Rainer) COMPACT P.L.C., 16 inputs and 14 outputs 24 V DC (photo 144328).

| Address | Wire label | From / to | Lines | Sheet:column | Signal | Mark |
|---|---|---|---|---|---|---|
| IN-0 | 24BMR | BMR1 23-24, +24V from 32X10 | 123, 204 | 7:06 | cut done (SIGNÁL PROVEDENÍ ŘEZU) | sure |
| IN-1 | 30X10 | S28 13-14 NO, clamp plate (PLECH LISOVADLA) | 137-138 | 5:14 | effect not printed | sure; effect [?] |
| IN-2 | 29X10 | S30 13-14 NO, clamp position (POLOHA LISOVADLA) | 135-136 | 5:13 | clamp at the top | sure |
| IN-9 | 3XC2 | S27 21-22 NC, saddle rear (POLOHA SEDLA ZADNÍ) | 133-134 | 5:12 | backgauge rear end | sure |
| IN-A | 2XC2 | S24 21-22 NC, saddle front (POLOHA SEDLA PŘEDNÍ) | 131-132 | 5:11 | backgauge front end | sure |
| OUT-0 | A1K2 | K2 coil A1-A2 → K1 A2 → X5 | 142-143, 141 | 5:16 | feed-cut blocking (BLOKOVÁNÍ POSUV-ŘEZ) | sure |
| OUT-9 | 13KM8 | KM8 13-14 → K1 coil A1-A2 → X5 | 139-141 | 5:15 | control of Y3, air cushion (ŘÍZENÍ Y3) | [?]: output position on the PLC not read |
| +24V | 35X10 | X10 35, bus 33-36X10 | 192 | 6:17 | PLC supply | sure |

The field signals take +24V from 33X10 → 32X10 → 31X10 (lines 124-125) to 1XC2 (126) and S30 (127), and from 32X10 to S28 (128). K1 pulls in only while KM8 (blower) is on; its contact switches Y3 on sheet 2 (t1).

## 9. Conflicts between sources

| # | Item | 568 print | Other source | Taken here | On-site |
|---|---|---|---|---|---|
| 1 | BMR1 1 line | 3X11/4X11 (20261113_194606) | hand "5X11/6X11" on the clean sheet 6 (20261114_014439); photo 144309: blue wires on 5X11, 6X11, bridges X11 3-4, 5-6 (±1) | the photo: lines 144-146 | 9 |
| 2 | K2 contact at BMR1 17 | 13-14 (6:17) | hand "11" over "13" (20261114_014513); photo 144324: marker 11K2, Lütze relay with one changeover 11-12-14 | 11-14: lines 198-199 | 10 |
| 3 | KM7 in the feedback loop | KM7 61-62 (6:04) | photo 144251: KM7 has only its built-in NC 21-22 (markers 21KM7, 22KM7) | 21-22, which end faces which not seen: lines 154-155 [?] | 6 |
| 4 | Control of the air cushion Y3 | PLC OUT-9 → KM8 13-14 → K1; K1 switches Y3 (2:31) | OM p.42 (20261115_022721): "управляется преобразователем частоты UZ1" (controlled by the inverter UZ1); set 567-70.9006 drives its air-cushion relay from UZ1 relay K14 (schemes_folder_1/20261103_215009, 215146; reading aid only) | the print (no photo shows it) | 12 |
| 5 | Release of the clamp brake Y14 | only BMR1 25-26 | OM p.40, p.42 (20261115_022623, 022721): released at the top by a BMR output driven by S14, held by KM6 | the print | 13 |
| 6 | Column of X5 | terminal label "X5 (2:02)" everywhere | the PLC table of sheet 8 writes "X5 2:01" (2:01 is the PE column) | 2:02 | 15 |
| 7 | 32X10 | printed at 5:13 (from BMR1 23) and 5:14 (from 33X10) | photo 144309: copper bridge 31-36 (±1) | two conductors on terminal 32: lines 123-124 | 16 |
| 8 | 34X10 reference | sheet 7 arrow "34X10 (6:16)" on the clean copies 20261114_014711 and 20261114_014834 and on the annotated 20261113_193629 (20261113_193705 is a second photo of that annotated sheet) | 34X10 is drawn at 6:16 | no conflict: an earlier low-resolution reading of 193629 as (5:16) was wrong | - |
| 9 | KM6 contacts on sheet 5 | cross-reference "(4:16)" | the KM6 coil is at 4:17 | slip kept as printed, noted on sheet 5 | - |
| 10 | KT1 contacts | NO/NC not readable | maker's face legend (photo 144259): 4-5 = 15-18 NO, 12-14 = 25-26 NC; OM list 10.2: TX 320 ZN, 24 V DC, 1-10 s (p.49) | the face legend | 7 |
| 11 | KT2 range | - | OM p.7 and p.9: 0-3 s; OM p.49: 0-2,5 s (TX 320 ZR) | both quoted | 8 |
| 12 | PLC OUT-9 | OUT-9 (8:02) | photo 144328: about four output wires among OUT-8 ... D, positions not read | the print [?] | 5 |
| 13 | RC8 | label above KM8 reads RC8, could read RC6 (20261113_232949) | - | RC8 [?] | 1 |
| 14 | V10 and R10 | sheet 5 crop (20261113_212623): R10 in series with V10, the pair across Y10 | the paths table had them in parallel | series | - |
| 15 | S19 | NC 21-22 at BMR1 18 (6:18) | set 567-70.9006 has S19 21-22 in the KM1 chain (schemes_folder_1/20261103_215146; reading aid only) | the print | 20 |
| 16 | Later ink | - | red on sheet 7 (20261113_193629): "сигнал на резку A1K2" (signal for cutting A1K2) at IN-0, "Y14 гидро распр. магнит." (Y14 hydraulic distributor magnet) at 20X10, "A1 KM1A KM1B" at 14X10, "~24V" at 19/20, "Y01 блокир. шестерни" (Y01 gear blocking) at 18X10, a tick at IN-0 (the same ink on 20261113_193705); red on sheet 6: "26 „0“" at BMR1 1, "+26" at 4 and 6, "?+24 (не взим.)" (last word read [?]) above BMR1 3-5, triangles above 37X10, 41X10, 40X10 (outlined) and 38X10 (filled), none above 39X10, dotted triangles on the BMR1 4 line above KM6 61 and on the BMR1 14 line (20261113_194606), "Норм „ON“" (normally ON) by SQ1 (20261113_194843); blue on sheet 5 (20261113_212552): "Блокир. шестерни" (gear blocking) under Y01, "гидрораспр." (hydraulic distributor) under Y11, "сцепление" (clutch) under Y10; red on sheet 8 (20261113_191800): IN-8 as clamp end-of-travel sensor, against the printed UZ1 signal (t3) | quoted as ink on the sheets, never as print | 14 |
| 17 | Knife sensor timing | timing diagram of the clean sheet 6 (20261114_014537) | - | bar ends estimated ±10 % of the stroke; what a bar means (contact closed or sensor actuated) [?] | 18 |

## 10. Differences with t1 (for t5)

t1 = `netlist/power_devices.csv`, `power_wires.csv`; t2 = `control_devices.csv`, `control_wires.csv`. Both files name every shared device the same way, and the 20 shared conductors have the same ends in both (the netlist script checks it). Thread 1 has no other row touching a wire end of this thread, except the board traces inside UG50, X10 PE → M1 PE (sheet 2) and 17 rows ending on the PE bar or the X5 0V bar, which this thread also uses (power_wires.csv lines 9-37: PE to ZF1, XP, X5, XC3, T1, X11, XC7 and UZ1; X5 to XC3 6, UG50 4, 7, 9, 11, 17 and 20, PLC GND and TABLO −); all of them are thread 1's own conductors.

| # | Item | t1 value | t2 value | t5 takes | Why |
|---|---|---|---|---|---|
| 1 | `wire` label of the 20 shared conductors: control lines 2, 18, 19, 20, 37, 80, 86, 92, 98, 100, 106, 107, 122, 141, 189, 190, 203, 205, 207, 208 = power lines 205, 30, 76, 77, 22, 203, 17, 31, 32, 207, 33, 204, 34, 21, 202, 102, 200, 201, 206, 35 | empty on all 20 | the printed label on 16: 12UG50, 12X10, 13UG50, 44QF1, 6UG50, 19X10, 21X10, 18UG50, 23X10, 10UG50, 28X10, 5UG50, 34X10, 1UG50, 2UG50, 14UG50; empty on 4 (KM1A A2 → X5, X10 PE → PE, K1 A2 → X5, BMR1 0V → X5) | t2's label | 568 prints these labels at the sheet 4-7 end of each conductor (the arrow "12UG50 (3:04)" at 4:01, the terminal 19X10 at 5:02); the sheet 2-3 end carries none |
| 2 | `sheet`, `column` of the same 20 conductors | the sheet 2-3 end (3:04, 2:02, 2:10, 2:26) | the sheet 4-7 end | both, sheet order: e.g. sheet `3; 4`, column `04; 01` | one conductor drawn on two sheets; each sheet must find it |
| 3 | V01 `evidence` | `[?]` ("V01" as printed [?]) | `sure` | `sure` | the crop `static_dynamic_memory/blocks/generation_002/artifacts/crops/12_wpd_568_b/s5_ann_212623_cols01-03_Y01_bottom.jpg` reads "VØ1" (slashed zero) beside Y01, as the sheet-box list "V01, V14" |
| 4 | `place` of V01, V14, V10, R10, RC11 | empty | `machine` | `machine` | 568 draws each across its magnet on the field side of the X10 terminals (V01 at Y01 between 18X10 and 19X10, V14 at Y14, RC11 at Y11, V10 and R10 at Y10), the side where every machine device is drawn; the exact spot is on-site entry 19 |
| 5 | `sheet`, `column` of shared devices | sheet 1 with empty column (S1, S2, S4, S5, S10-S14, S19, S24, S27, S28, S30, SQ1, SQ2, KM6, KM7, V01, V14, V10, R10, RC11, V20, R14, X8, XC2), or the sheet 2 power contacts (KM1A 2:04, KM1B 2:06, KM2 2:04-06, KM3 2:07-09, KM4 2:11-12, KM8 2:27-29, K1 2:30-31, Q2 2:01-02) | where 568 draws the coil or contact on sheets 4-7 (KM1A 4:09, S5 `4-5` / `10; 09`, ...) | both, sheet order (KM1A sheet `2; 4`, column `04; 09`); t2's alone where t1 has only sheet 1 with empty column | sheet 1 of t1 is its device-list row, not a drawn place |
| 6 | `type_rating` of shared devices | ratings and OM types (KM1A "coil 24 V AC 50 Hz; photo: family EP1C093 [?]; OM: EP1-C123 B"; QF1, X5, X11, PE, UZ1, K1) | contact use on sheets 4-7 (S5 "NC 21-22 (4:10), NO 13-14 (5:09)", QF1 "aux contact 43-44 NO used at 4:10") | both texts joined | no value contradicts the other (compared field by field) |
| 7 | PLC, TABLO, UZ1 rows | UZ1: Lenze EVF8202-E-V002 with ratings | rows list only the terminals used on sheets 4-7 | t3's and t1's rows for kind, rating and place; t2's sheet 4-7 references | these devices belong to t3 (sheet 8) and t1 (UZ1 power) |
| 8 | `term_cz_ru` of QF1 and UZ1 | "jistič motoru", "MĚNIČ" | "-" | t1's | the terms stand on t1's sheets; sheets 4-7 print none for these two devices |

## 11. On-site list

Safety first. **Q1 off does not make the cabinet dead.** With the main switch Q1 at 0, the socket XC7, the breaker FA4 and the mains filter ZF1 stay live (OM p.12, chapter 3: "находятся под напряжением и в состоянии выключенного главного выключателя Q1", are live also with the main switch Q1 off; 20261115_004236), and so does XP (main terminal strip, hlavní svorkovnice) ahead of Q1; the NOARK pair may stay live too, its supply being unknown (`spec/power.md` section 9, entry 24). The UG50 supplies (+24V, +27V, +33V, ~24V, ~48V), BMR1, the PLC and the transformer T1 stay live when KM1A and KM1B are open and when S1 is pressed: T1 is fed between Q1 and the main contactors. Before any check in the cabinet, isolate the machine upstream (the wall isolator, or the distribution-board breaker or fuses that feed XP), lock it off, and prove XP and the terminals to be touched dead with a tester. The inverter UZ1 keeps its DC bus (+UG/-UG) charged for a while after isolation: wait for the time its label or manual gives, then measure before touching (`spec/power.md` section 9, entry 35). Checks marked LIVE need control voltage on: done only by an electrically trained person (OM 5.2.2), with a meter and test leads rated for mains work (measurement category III or higher), and always in this order ("hands clear" below): while isolated, fix the meter leads and set what the check needs (a plate, the knife position); clamp at the top, nobody at the table; switch on with hands out of the cabinet and away from the knife and the clamp, start machine motion only from the console or the two-hand buttons, read, and isolate again before touching anything. "Control voltage only" below means Q2 set to 0 and the emergency stop S1 pressed while isolated, and only then Q1 switched on: KM1A and KM1B stay out, so M1 (knife drive and hydraulic pump), the inverter UZ1 (backgauge drive) and the blower M3 have no supply, while the UG50 supplies, BMR1, the PLC and the sensors stay fed (section 5) and nothing can start. Q2 at 0 alone is not enough: it pulls in KM1A and KM1B (section 4, step 1). BMR1 and UZ1 are not opened or repaired on site: the OM allows that only to a person the maker trained and authorized (OM p.12, chapter 3).

Places (the Where column). Cabinet, as photographed through the open door, rows top down: row 1 plate with the BMR1 board, R14 beside it (photos 143021, 143202); row 2 plate with the PLC, K1 and K2 on a short rail beside it (144328, 144324); row 3 terminal rail PE, X10 1-45, PE, X11 1-6 (144309, 144314); row 4 rail KT1, KT2, a grey box, QF1, QF2, KM1A, KM1B, FA1-FA3, two NOARK breakers (143210, 144304); row 5 contactor rail KM2, KM3, KM4, KM8, KM6, KM7 (144251, 144247); row 6 plate UG50, UZ1 (143806); row 7 bottom rail ZF1, XP, PE, X5, XC7, FA4 (144214). Q1, Q2, S2 and S4 sit on the switch plate inside the cabinet's front face (153000, 153015); the connectors XC1-XC4 stand in a column low on the cabinet's machine-side face, near its rear-bottom corner [?] (144555). Machine places are as drawn in the undimensioned OM figures: Fig.10.1 (p.45; 20261115_022909, 20261115_022935), Fig.3.1 (20261115_004705, 20261115_004719), Fig.6.1 (20261115_021157) and Fig.6.2 (20261115_021353). No source gives them in millimetres: note each place found in mm from a frame edge.

| # | Key | What to check | Where | How |
|---|---|---|---|---|
| 1 | `RC8` | the label of the RC part across KM8's coil: RC8 or RC6 (20261113_232949) | cabinet row 5: KM8, fourth on the contactor rail, at its coil terminals A1-A2 (photo 144247) | dead: read the label |
| 2 | `KM8 A1 -> RC8 1`, `RC8 2 -> KM8 A2` | that this RC part sits across KM8 A1-A2 (20261113_232949) | cabinet row 5: KM8's coil terminals A1-A2 (photo 144247) | dead: look |
| 3 | `XC2` | the table-cable connector: its label and pins 1-9 (S24, S27 on 1-3, S10, S11 on 4-9); not seen in the photos (sheets 5-6: 20261113_234616, 20261114_014439; photos 143021, 144309) | outside the cabinet: the top connector [?] of the column low on its machine-side face (photo 144555); inside, the pin wires end on X10 31, X11 6 (row 3), BMR1 2, 3, 6-8 (row 1) and PLC IN-9, IN-A (row 2) | dead: read, continuity pin to terminal |
| 4 | `X8` | the sensor strip on the machine (terminals 1-6, 1 = +24V common), not seen in the cabinet; its place (sheet 6: 20261114_014439; cabinet photo 143021) | on the machine, not seen: look near the sensors it feeds, SQ1, SQ2 (at Y01: frame top, rear, right of centre) and S12-S14 (knife cam, right side) (estimated); its wires leave the cabinet at X10 37-42 (row 3) | dead: find it, note the place in mm from a frame edge |
| 5 | `PLC OUT-9 -> KM8 13` | which output terminal carries the wire 13KM8 (photo 144328: about four wires among OUT-8 ... D, positions not read) | cabinet row 2: the PLC's output terminal row OUT 0-D (photo 144328); KM8 13 in row 5 (photo 144247) | dead: read the markers; LIVE alternative, hands clear: OUT-9 LED with the blower on, read from outside the cabinet |
| 6 | `KM6 62 -> KM7 22`, `KM7 21 -> BMR1 5` | which KM7 terminals carry the feedback loop (print 61-62, photo 21-22; KM6 62 is seen wired, marker 62KM6 on photo 144251, its pairing with KM7 22 is not seen) and which end faces BMR1 5 (print 20261114_014439; photo 144251) | cabinet row 5: KM6 and KM7, the two right-hand contactors of the rail (photo 144251); BMR1 4-5 in row 1 (photo 143021) | dead: continuity BMR1 4 → BMR1 5 closed with KM6 and KM7 at rest |
| 7 | `KT1` | the contact types on the face (4-5 = 15-18 NO, 12-14 = 25-26 NC) and the dial setting (OM: 1-10 s) (photo 144259; OM list 10.2 p.49: 20261115_023314) | cabinet row 4: the timers KT1, KT2 at the left end of the rail as photographed (photos 143210, 144259; OM Fig.10.2, 20261115_023222, draws them at the right end) | dead: read |
| 8 | KT2 | the dial setting; OM range 0-3 s (p.7, p.9) or 0-2,5 s (p.49) (photo 144259; OM p.49: 20261115_023314) | cabinet row 4, beside KT1 (photo 144259) | dead: read |
| 9 | `BMR1 1 -> X11 5` | the S10 common runs BMR1 1 → 5X11 → bridge → 6X11 → 4XC2 (print 3X11/4X11); bridges X11 3-4 and 5-6; whether 5-6 is the bridged place of the light curtain FF1 (not fitted; estimated) (20261113_194606, 20261114_014439, photo 144309) | cabinet row 3: X11 1-6 at the right end of the terminal rail (photo 144309); BMR1 1 in row 1 (photo 143021) | dead: markers and bridges |
| 10 | `BMR1 17 -> K2 11` | K2 contact 11-14 (print 13-14, hand "11" over "13": 20261114_014513); photo 144324 shows the marker 11K2 on 11, the wire on 14 is not readable (a blue wire with its sleeve turned away); whether +24V on BMR1 17 allows or blocks the cut [?] | cabinet row 2: K2 on the short rail beside the PLC (photo 144324); BMR1 17 in row 1 (photo 143021) | dead: read the marker on K2 14; LIVE, hands clear: meter on BMR1 17 to 0V (fixed while isolated), read with the PLC feeding and at rest |
| 11 | K1, K2 coils | coil voltage (24 V DC from the PLC, estimated) (photo 144324; OM list 10.2: 20261115_023314) | cabinet row 2: K1, K2 on the short rail beside the PLC (photo 144324) | dead: read the relay label |
| 12 | Y3 | does K1 (PLC OUT-9 through KM8) switch the air cushion Y3 (568), or the inverter UZ1 (OM p.42)? (20261115_022721; sheet 5: 20261113_234616) | K1 in cabinet row 2 (photo 144324); Y3, the air-table valve, on the machine: OM Fig.10.1's leader ends outside the rear-table outline [?], place not known: find it, note it in mm from a frame edge | dead: trace K1's contact to Y3; LIVE, hands clear: K1 state (its LED, or a meter fixed while isolated) when the air cushion switches |
| 13 | Y14 | does Y14 get voltage only from BMR1 25-26 (568), or is it released at the top by an S14-driven output and held by KM6 (OM p.40, p.42)? (20261115_022623, 20261115_022721; sheet 7: 20261113_193629) | cabinet row 3: X10 terminal 20 (photo 144314); X5 on the bottom rail, row 7 (photo 144214); Y14 itself in the middle of the frame band's rear edge (OM Fig.10.1) | LIVE, hands clear: meter on 20X10 to X5 (fixed while isolated) over one cut started from the two-hand buttons |
| 14 | Ink | what the later red and blue notes refer to: IN-0 "сигнал на резку A1K2"; 20X10 "Y14 гидро распр. магнит." (is Y14 a hydraulic valve magnet rather than the clamp brake?); 14X10 "A1 KM1A KM1B"; "~24V" at BMR1 19/20; 18X10 (7:04) "Y01 блокир. шестерни" (does Y01 lock a gear rather than the knife?); the tick above PLC IN-0 (7:06); "26 „0“" at BMR1 1, "+26" at 4 and 6; "?+24 (не взим.)" above BMR1 3-5 (6:03-05; last word read [?]); the triangles above 37X10, 38X10 (filled), 41X10, 40X10 (BMR1 9, 10, 12, 13; 6:09-13; none at 11) and the dotted ones on the BMR1 4 line (KM6/KM7 feedback, 6:04) and on the BMR1 14 line (Q2 loop, 6:14): look at those inputs, the sensors SQ1, SQ2, S13, S14, the feedback contacts and the Q2 loop for changed wires, bridges or added parts; "Норм „ON“" by SQ1; blue notes under Y01, Y11, Y10 (20261113_193629, 20261113_193705, 20261113_194606, 20261113_194843, 20261113_212552; sheet 8: 20261113_191800) | cabinet: BMR1 (row 1), PLC IN-0 (row 2), X10 14, 18, 20, 37-41 (row 3), KM6, KM7 (row 5), Q2 (switch plate); machine: SQ1, SQ2, S13, S14 and the magnets Y01, Y10, Y11, Y14 (places as in entries 18 and 19) | dead: follow the wires; LIVE, hands clear, control voltage only, for the voltages (meter fixed while isolated) |
| 15 | X5 | that the 0V strip is the X5 of column 2:02 (the sheet 8 table writes 2:01) (20261114_015117) | cabinet row 7: the bottom rail ZF1, XP, PE, X5, XC7, FA4 (photo 144214) | dead: look |
| 16 | 32X10 | two conductors on terminal 32 (from BMR1 23 and from 33X10) and the copper bridge 31-36 (±1) (20261113_234616, photo 144309) | cabinet row 3: X10 terminals 31-36 (photos 144309, 144314) | dead: count wires and bridges |
| 17 | S28 | which state of the clamp plate (plech lisovadla) closes S28 13-14 (NO), and what the machine does with PLC IN-1: not printed (20261113_234616) | cabinet row 3: X10 terminals 30 and 32 (photo 144314); the PLC IN-1 LED in row 2 (photo 144328); S28 on the machine at the clamp band, left of centre (OM Fig.10.1) | dead (isolated): with the plate fitted, then removed, measure continuity 32X10 → 30X10 (S28 13-14) in the cabinet in each state; this works for the mechanical switch of OM list 10.1 (Telemecanique XCK-A 110), while a proximity switch (the print's diamond symbol) shows its state only live. LIVE, hands clear, the plate set while isolated: first with control voltage only, read the IN-1 LED and any console message; then, only for what that leaves open, with S1 released and M1 started as in normal work, see whether the backgauge feed or a cut from the two-hand buttons is blocked; isolate, change the plate, repeat. The PLC program itself is episode 3's. |
| 18 | SQ1, SQ2, S12, S13, S14 | where in the stroke each switches (timing diagram, bar ends ±10 %, bar meaning [?]) (20261114_014537) | machine: SQ1, SQ2 on a bracket at the Y01 end, frame top, rear, right of centre (OM Fig.6.2, Fig.3.1); S12 in the right column below table level, S13, S14 on the right side [?] (OM Fig.10.1); the meter at BMR1 9-13, cabinet row 1 (photo 143021) | LIVE, hands clear, control voltage only (Q2 at 0 and S1 pressed, as defined above): while isolated, turn the knife by hand to the next point as OM item 4.6 prescribes (named in fault 5.1.7 а) and step back; switch on and note the sensor LEDs or a meter on BMR1 9-13 to 0V (fixed while isolated); isolate before the next turn |
| 19 | V01, V14, V10, R10, RC11 | that they sit at their magnets (terminal boxes of Y01, Y14, Y10, Y11) and not in the cabinet (20261113_234616) | machine, at each magnet's terminal box: Y01 frame top, rear, right of centre (OM Fig.3.1); Y14 in the middle and Y11 right of centre of the frame band's rear edge (OM Fig.10.1); Y10 outside the right frame (OM Fig.6.1) | dead: look |
| 20 | S19 | 44X10 → S19 21-22 → 36X10 at BMR1 18 (568), not in the KM1 chain (set 567-70.9006) (20261114_014439; schemes_folder_1/20261103_215146) | machine: S19 at the flywheel (у маховика, 568), far right, low, above M1 (OM Fig.10.1); 44X10 and 36X10 in cabinet row 3 (photos 144309, 144314) | dead: follow the wires |
| 21 | S10, S11 response | the run-down test of OM §9.3 (20261115_022743): meter in the opened BMR1 1 or 6 line, reaction max. 200 ms (OM p.7) | BMR1 1 and 6, cabinet row 1 (photo 143021); the buttons S10, S11 on the front table's front edge, left and right of centre (photo 144447) | LIVE, hands clear, as the OM prescribes: the meter fixed in the opened line while isolated, the cut started from the two-hand buttons only |
| 22 | Q2, BMR1 14-15 | what BMR1 does with the Q2 7-8 loop on its inputs 14-15, closed only in position 0 (M1 off) and open in position 1 (contact table 2:01-02: 20261113_231128; sheet 6: 20261114_014439): not printed [?] | BMR1 14-15, cabinet row 1 (photo 143021); Q2 on the switch plate inside the cabinet's front face (photos 153000, 153015) | dead: continuity BMR1 14 → 15 with Q2 at 0 (closed) and at 1 (open); find the module's maker and manual from its plate ("BMR2", photo 143021); the module is not opened (OM p.12) |

## 12. Sources

Folders: photos `preparatory_data_analysis/maxima_photos/20261102_<stamp>.jpg`; wiring set `preparatory_data_analysis/maxima_documents/adast_guillotine_wiring_and_plc_diagrams/<stem>.jpg`; OM `preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/<stem>.jpg`; wiring sets of other machines, reading aids only: `preparatory_data_analysis/maxima_documents/schemes_folder_1/<stem>.jpg`; tables `static_dynamic_memory/blocks/generation_002/artifacts/tables/` (local working files).

| Figure or fact | Source |
|---|---|
| Sheet 4, clean copy: main-contactor chain, star-delta, cut contactors | `adast_guillotine_wiring_and_plc_diagrams/20261113_232949.jpg`; pencil ZN, ZR: `20261113_233009.jpg`; annotated copy: `20261113_194230.jpg` |
| Sheet 5: magnets, PLC signals, K1, K2 | `20261113_234616.jpg`; annotated crops `20261113_212623.jpg`, `20261113_212711.jpg`; blue ink `20261113_212552.jpg` |
| Sheet 6: BMR1 inputs; hand corrections 5X11/6X11 and K2 "11" | clean `20261114_014439.jpg`, `20261114_014513.jpg`; timing diagram `20261114_014537.jpg`; order of the +24V-bus arrows `20261114_014325.jpg`; red ink `20261113_194606.jpg`, `20261113_194843.jpg` |
| Sheet 7: BMR1 outputs; 34X10 (6:16); red ink | clean `20261114_014711.jpg`, `20261114_014834.jpg`; red ink `20261113_193629.jpg`, again on `20261113_193705.jpg` |
| Sheet 8: PLC table, X5 "2:01", IN-8 ink (t3) | `20261114_015117.jpg`, `20261113_191800.jpg` |
| Sheet 3: dashed FF1 | `20261113_232117.jpg`; certificate FF1 "—": `20261113_195028.jpg` |
| Part list of sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK): box 4 "RC... 2µ2 + 220R" (RC1-RC4, RC6-RC8), "V20 1N 4002"; box 5 "V01, V14 1N 4002", "V10 2x KZ 751", "R10 100R/6W", "RC11 2µ2 + 220R"; box 7 "R14 11R/25W" | `20261113_213823.jpg` (close-up of the table), `20261113_213049.jpg` (whole sheet 1); both show every entry |
| Reading aids only: set 567-70.9006 (Y3 relay, S19, KZH2-XS); set 581-70.9009 (curtain at 5X11-6X11, two-hand relay K10); set 551-82.0170 | `schemes_folder_1/20261103_215009.jpg`, `20261103_215146.jpg`, `20261103_215317.jpg`; `20261103_220402.jpg`, `20261103_220058.jpg`; `20261103_204857.jpg` |
| BMR1 plate "BMR2", one board, wires on 1-29, red AC wires | photo 143021; the same again on photo 144334 |
| X11 bridges, blue wires on 5X11, 6X11; copper comb 31-36X10, bridge 41-42X10; inside wires on X10 17-24, 27-32, 34-41, 43, 44 | photo 144309 |
| X10 terminals 7-16: inside wires (red) on 8, 9, 12, 14, none on 7, 10, 11, 13, 15, 16; copper bridges 7-8, 9-10, 11-13, 16-17 | photo 144314 |
| K1, K2: Lütze, changeover 11-12-14, markers 11K2, 11K1, 14K1 | photo 144324 |
| Markers A1K1, A1K2, A2K2 | photo 144344 |
| Markers 54KM3 x2, 13KM3 x2, 14KM3 x2 (order of node N1) | photo 144247 |
| Markers 61KM6, 62KM6, A1KM7 (RC), 5KM7, 21KM7, 22KM7 | photo 144251 (22KM7 also on 144205) |
| Contact lists under the coils (sheets 4 and 5) | rating fields of `11_568_sheet4_paths.csv`, `12_568_sheet5_paths.csv`, read off `20261113_232949.jpg`, `20261113_233009.jpg`, `20261113_212711.jpg` |
| PLC front: B&R COMPACT P.L.C., 14 outputs and 16 inputs 24 VDC, fuse 1.25 AT, label ADAST154.PGP 98/05/20 | photo 142944 |
| PLC terminals: input markers, OUT-0 marker, about four output wires among OUT-8 ... D | photo 144328 |
| KT1, KT2: ZN, ZR, dial 4-10, face legend 15-16-18, 25-26-28 | photo 144259 |
| KM6 side label EP1C093 | photo 144247 |
| KM7 markers 21KM7, 22KM7 | photo 144251 |
| Q2 cam label and markers 2Q2, 6Q2, 8Q2, 9Q2, 10Q2; S2 and S4 bodies | photo 144344 |
| Places of section 11: cabinet rows, switch plate, connector column; machine places | photos 143021, 143202, 143210, 144304, 144328, 144324, 144309, 144314, 144251, 144247, 143806, 144214, 153000, 153015, 144555, 144447; OM Fig.10.1 (20261115_022909, 20261115_022935), Fig.3.1 (20261115_004705, 20261115_004719), Fig.6.1 (20261115_021157), Fig.6.2 (20261115_021353), Fig.10.2 (20261115_023222) |
| OM fault list 5.1.5-5.2.4 | `adast_guillotine_operating_manual/20261115_013519.jpg`, `20261115_013741.jpg`, `20261115_013757.jpg` |
| OM p.40, p.41, p.42 (Y14, S30, Y3) | `20261115_022623.jpg`, `20261115_022638.jpg`, `20261115_022721.jpg` |
| OM §9.3 run-down test; S1 parts | `20261115_022743.jpg`; `20261115_022802.jpg` |
| OM lists 10.1 and 10.2 (types, KT1 and KT2 ranges p.49); Supplement 1 | `20261115_023023.jpg`, `20261115_023314.jpg`; `20261115_023443.jpg` |
| OM p.11 (panel messages in a separate manual), p.12 (XC7, FA4, ZF1 live with Q1 off; BMR and inverter repairs only by a person the maker authorized), p.14 (FF1 option) | `20261115_003733.jpg`, `20261115_004236.jpg`, `20261115_004647.jpg` |
| Q2 contact table 2:01-02 (1-2, 3-4, 5-6, 7-8 closed in position 0; 9-10 closed in position 1) | `adast_guillotine_wiring_and_plc_diagrams/20261113_231128.jpg` |
| Paths tables of sheets 4-7, PLC I/O table, device table, fault table | `11_568_sheet4_paths.csv`, `12_568_sheet5_paths.csv`, `12_568_sheet6_paths.csv`, `12_568_sheet7_paths.csv`, `12_568_plc_io.csv`, `11_568_devices.csv`, `18_manuals_electrical_faults.csv` |
| Counts of section 1 (63 devices, 207 wires, 20 shared, 8 open, 121 paths rows, 12 contact lists; per-sheet rows, dots, pins, texts) | the two command outputs of section 1 |
