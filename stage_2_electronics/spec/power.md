# Power circuits of the Adast Maxima MS 115 PS: set 568-70.9001, sheets 1-3

Same as the 1998 paper set 568-70.9001 (here "568") of this guillotine (serial 578.0009), but as data: every device and every conductor of the sheet-1 tables and of sheets 2-3 is one row of a CSV (comma-separated values) netlist, and the three sheets are drawn again as SVG (Scalable Vector Graphics) files from those rows. This is thread t1 (power) of episode 2; thread t5 (integration) merges it with the threads control (t2), PLC (programmable logic controller) and drive (t3), and the 3D (three-dimensional) layout (t4).

- Marks, in every row and below: sure; [?] = unclear; estimated ±error; W = web (weaker evidence).
- s:cc = sheet:column of the 568. OM = operating manual of the machine. "Ink" = later handwritten marks on the paper set (the red notes are a later technician's, in Russian); ink is quoted with its place and never taken as print. Hand-lettered terminal labels of the original drawing count as print.
- The cabinet photos rule what is wired; where they cannot tell, the 568 is assumed unchanged. Every difference is on the on-site list (section 9).
- Paths are relative to the project folder (the repository root). Source files are named by short stems; section 11 gives each stem's file.
- T = static_dynamic_memory/blocks/generation_002/artifacts/tables: the local working tables (transcriptions of the 568 and of the OM) that the netlist was checked against. Like the source photos in preparatory_data_analysis/, they stay local and are not in the repository.

## 1. Files and rebuild

| File | What it holds |
|---|---|
| stage_2_electronics/schemes_2d/power_netlist.py | the transcription itself: device and conductor tables, each row with its mark, source and note; writes both CSV files and checks them |
| stage_2_electronics/netlist/power_devices.csv | 99 device rows: 86 sure, 13 [?] |
| stage_2_electronics/netlist/power_wires.csv | 206 conductor rows: 187 sure, 14 [?], 5 estimated ±1 column |
| stage_2_electronics/schemes_2d/power_draw.py | reads the two CSV files (Python standard library only) and draws the three sheets |
| stage_2_electronics/schemes_2d/power_sheet1.svg | sheet 1: table 1 (switches and controls), table 2 (terminal strips and connectors), table 3 (variant grid, 13 rows x 5 mains variants), components table, notes 1-3, sheet list, title block |
| stage_2_electronics/schemes_2d/power_sheet2.svg | sheet 2, columns 01-32: feed (01-03), M1 (04-16), M2 with inverter UZ1 (17-26), M3 and Y3 (27-32) |
| stage_2_electronics/schemes_2d/power_sheet3.svg | sheet 3, columns 01-04: transformer T1 (01-02), power-supply board UG50 (03-04) |

Headers (format of section 05 of the plan, shared by all threads):
- devices: `designation,kind,function_en,term_cz_ru,type_rating,place,sheet,column,evidence,source_path,note`
- wires: `wire,from_device,from_terminal,to_device,to_terminal,signal,plc_address,connector,pin,cable,sheet,column,evidence,source_path,note`

Rebuild from the project folder or from a clone of the repository (Python 3, no package needed), first the netlist, then the sheets:

```
python -B stage_2_electronics/schemes_2d/power_netlist.py
python -B stage_2_electronics/schemes_2d/power_draw.py
```

In the project folder the last lines must read as below. BMR1 (board drawn on sheet 7), the PLC and TABLO (the console control panel, as printed) are devices of other threads at the far end of some conductors.

```
power_devices.csv 99 rows, power_wires.csv 206 rows, bad 0; far-end devices of other threads: BMR1 PLC TABLO
power_sheet1-3.svg written; wire rows of sheets 2-3 drawn on their sheet 206/206; not-sure rows marked once on their sheet 32/32; texts 279/337/167 (overlap-checked; all text elements 279/337/182); wire segments 211/162; junction dots 50/38; paths-table columns checked 85; bad 0
```

In a clone, the local folders preparatory_data_analysis/ and static_dynamic_memory/ are absent. Each script then skips the checks that need them, says so in one line, and writes the same files byte for byte:

```
local sources absent (preparatory_data_analysis/ static_dynamic_memory/): source-file check skipped for 761 of 761 paths; far-end check skipped
power_devices.csv 99 rows, power_wires.csv 206 rows, bad 0; far-end devices of other threads: BMR1 PLC TABLO
local sources absent (static_dynamic_memory/): paths-table column check skipped
power_sheet1-3.svg written; wire rows of sheets 2-3 drawn on their sheet 206/206; not-sure rows marked once on their sheet 32/32; texts 279/337/167 (overlap-checked; all text elements 279/337/182); wire segments 211/162; junction dots 50/38; paths-table columns checked 0; bad 0
```

"Texts" counts the texts under the overlap check; the polarity signs (+ ~ -) inside the capacitor and bridge symbols are drawn without it, so all text elements number more.

- What "bad 0" covers in power_netlist.py: a repeated designation, an unnamed terminal, a mark outside the four, a missing source file (only where its local folder exists), a user path, a place outside cabinet/machine/console, a conductor end that is no device (devices of other threads excepted, and checked against the T tables only where they exist), several terminals in one field. Any of them stops the script with an error.
- What "bad 0" covers in power_draw.py: every designation printed on its sheet (sheet 1 for names drawn on sheets 4-8), every conductor of sheets 2-3 drawn, complete column rulers, every column of the 568 paths tables of sheets 2-3 printed (only where the T tables exist), no text over another text or over a wire, and each of the 32 not-sure rows showing its mark ("[?]", or "est. ±1 col" for "estimated ±1 column") exactly once on its own sheet and at most once on another (rule in section 10).
- A rerun gives byte-identical files, in the project folder and in a clone.

To look at a sheet, render it to a PNG (Portable Network Graphics) file outside stage_2_electronics, with the window size equal to the SVG size (sheet 1: 1800,980; sheet 2: 2070,1450; sheet 3: 1700,1010):

```
"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless --disable-gpu --hide-scrollbars --screenshot=<folder outside the repository>/power_sheet2.png --window-size=2070,1450 file:///<project folder>/stage_2_electronics/schemes_2d/power_sheet2.svg
```

## 2. From the mains to the loads (sheet 2)

Mains: three-phase AC (alternating current), L1 L2 L3 with N (neutral) and PE (protective earth), on XP (main terminal strip, hlavní svorkovnice), 2:01. The print gives two terminals per phase, three bridged N terminals and PE (w210810); the photo shows 7 yellow phase terminals and 3 blue N (c144214).
- Door plate: "Ue 400/230 V", "f 50 Hz" (c142805).
- OM p.20 (m011308) for this machine size: 380-440 V, 12 A per phase, supply fuse at most T 16 A (T = time-lag); for 200-230 V mains 20 A, T 25 A. OM p.7 (n215113): 5.5 kVA (kilovolt-ampere). These are OM figures, not 568 figures.

Live while the main switch Q1 is off (OM p.12, m004236):
- XP itself;
- ZF1 (mains interference filter, on L1 L2 L3 N PE, 2:01);
- FA4 (6 A, from XP L3, 2:14) and the socket XC7 (ZÁSUVKA, 230 V, 2:14-16), whose N comes from XP ("N (2:01)" at 2:16).

Q1 (main switch, hlavní vypínač, 2:02-03, positions 0/1) switches L1 L2 L3 to U V W, which go to KM1A 1/3/5.

T1 (control transformer) takes its feed between Q1 and the main contactors, from KM1A's input terminals (2:03, 3:01):
- U (KM1A 1) → FA2 → T1 tap 400V;
- V (KM1A 3) → FA1 → X11 2, bridged to X11 1 → T1 tap 0V.
- So T1 and every control voltage are live as soon as Q1 is on, with KM1A and KM1B open.

Main contactors KM1A (2:04) and KM1B (2:06) in series (KM1B drawn mirrored: in 2/4/6, out 1/3/5) give the bus L1 L2 L3; their coils sit at 4:09 and 4:11 (thread control). The bus feeds:

1. M1, main drive of knife and hydraulic pump, star-delta (OM p.7: 4 kW, kilowatt):
   - QF1 (2:07-10) → KM2 (line) → X10 1/2/3 → M1 U2/V2/W2;
   - QF1 → KM3 (delta) → X10 4/5/6 → M1 V1/W1/U1;
   - KM4 (star, 2:11-12) shorts X10 4-5-6; star-delta timer KT1 at 4:16 (thread control);
   - QF1's auxiliary contact 43-44 NO (normally open) is in the control chain: ~24 V from UG50 13 → QF1 43 (sheet 4, column 10); QF1 44 → BMR1 19 (7:01) and the sheet-4 control bus.
2. M2, backgauge drive (Czech sedlo, "saddle"; OM list 10.1: 550 W, m022802), 2:17-26:
   - bus L3 → FA3 1-2 and XP N → FA3 3-4 (2:18) → X2 L, N → ZF2 (single-phase mains filter; in L N, out 1L 1N) → UZ1 L, N;
   - UZ1 = frequency inverter, plate Lenze "EVF8202-E-V002", input "1/N/PE AC 230V 9.0A", output "3/AC 0-230V 4.0A 0.75kW" (c144201); the 568 prints no type;
   - UZ1 U V W → XC1 1-3 → M2 U1 V1 W1; PE through XC1; both cable pieces shielded: the UZ1-XC1 shield ends on the 3rd circle of UZ1's top edge (unlabeled; a shield terminal in the paths table of sheet 2; on-site entry 21), the XC1-M2 shield joins the earth line to M2 at a dot (2:17-20, w231229).
   - UZ1 control side (2:21-26), PLC addresses as in the PLC input/output table:
     - UZ1 39 → PLC GND (ground), OUT-GND (2:21);
     - PLC OUT-B → UZ1 E3, feed forward (POSUV VPŘED);
     - PLC OUT-C → UZ1 E4, feed backward (POSUV VZAD);
     - PLC OUT-D → UZ1 28, inverter enable (BLOKOVÁNÍ UZ1);
     - UZ1 K12 → PLC IN-8, drive status (SIGNÁL FUNKCE POHONU);
     - X10 34 (+24 V) → UZ1 K14;
     - UZ1 7 → XC50 pins 6+9 and UZ1 8 → XC50 pin 4: speed setpoint, shielded pair (ŘÍZENÍ RYCHLOSTI SEDLA).
     - The rows of 2:22-26 are "estimated ±1 column" (see section 9).
3. M3, air-cushion blower (OM list 10.1: 370 W): QF2 (2:27-29) → KM8 (coil 4:12) → XC3 1-3 → M3; PE through XC3.
4. Y3, air-cushion magnet, ~48 V AC, 2:30-32: UG50 19 (fuse FU27) → K1 11-14 (coil 5:15) → XC3 5 → Y3 → XC3 6 → X5 (0 V). C3 (2µ2/230V) lies across XC3 5-6. Y3's earth joins M3's at XC3 PE (section 6).

The earthing strip and X5 follow in section 6.

## 3. Control voltages (sheet 3)

T1: OM type JOC-U 4056-130 (OM p.49, m023314); no plate seen (c144220).
- Primary taps -40V -20V 0V 20V 230V 400V.
- Drawn for 400 V mains: FA2 → 400V; FA1 → X11 2-1 → 0V; the 230V tap → X11 3, bridged to X11 4; the dashed ~230 V feed of the light curtain FF1 (not fitted, section 7) starts at X11 3.
- Tap table printed beside it (w231949):

| Mains | Taps used |
|---|---|
| 200 V | 20-230 |
| 230 V | 0-230 |
| 380 V | 20-400 |
| 400 V | 0-400 |
| 415 V | 0-415 (no 415 tap is drawn; section 8) |

The secondary windings feed UG50 (power-supply board, plošný spoj se zdroji, 3:03-04). VA = volt-ampere, DC = direct current. "→ s:cc" is the printed arrow; the device after it is the far end found in that sheet's paths table.

| Winding | V | VA | UG50 in | Fuse | Rectifier, capacitor | Output | UG50 out → target | Return to X5 |
|---|---|---|---|---|---|---|---|---|
| I | 21 | 120 | 21, 22 | FU21 6.3A | V1 PBU 802, C1 2200µF/50V | +27 V DC | 1 → 7:03 BMR1 21; 2 → 7:07 R14 1 (then BMR1 25); 3 has no destination | 4 |
| II | 19 | 50 | 23, 24 | FU22 3.15A | V2 PBU 802, C2 2200µF/50V | +24 V DC | 5 → 6:18 X10 36; 6 → 4:20 KM6 1 (then KT2 1) | 7 |
| III | - | - | 25, 26 | none | none | unused | - | - |
| IV | 24 | 120 | 27, 28 | FU24 T4A | V4 CM2506 [?], C4 1000µF/63V [?] | +33 V DC | 10 → 5:10 KM6 5 (the node also feeds Q2 5, 5:09) | 11 |
| V | 24 | 100 | 29, 30 | FU25 4A | none | ~24 V AC | 12 → 4:01 S2 3A (lighting); 13 → "4:01" as printed, far end QF1 43 at 4:10 (control chain); 14 → 7:09 BMR1 27 | 17 (joined to 30) |
| VI | 48 | 180 | 31, 32 | FU26 2A; FU27 2A | none | ~48 V AC | 18 (FU26) → 5:07 KM6 3 (then X10 22, Y11); 19 (FU27) → 2:30 K1 11 (Y3) | 20 (joined to 32) |

- UG50 outputs 3, 8, 9, 15 and 16 are drawn without a destination; X5's list still names 9UG50 (conflict, section 6).
- Board parts besides the fuses, rectifiers and capacitors: indicator LEDs (light-emitting diodes) and diodes V11-V17, V21-V27 with resistors R11-R17 (names qualified where they clash, section 10). V13 and V23 are printed in the ranges but not drawn, since winding III has no fuse: device rows with a note, no conductor.
- Photo of the board (c144231): a blue "SAMWHA 4700µF 63V" capacitor sits over the empty places C3/C4, a repair [?] (on-site list).

## 4. Switches, breakers and fuses: 568 | photo | OM

568 = sheet-1 grid, the same in all mains columns (w213530). OM = device list 10.1 for Q1 and Q2 (p.44, m022802) and device list 10.2 for the breakers and fuses (p.47, m023118), as transcribed in T/18_manual_device_list.csv; Fig. 10.2 (p.48, m023222) gives places only. UL = Underwriters Laboratories; IEC = International Electrotechnical Commission.

| Device | Protects or switches | 568 | Photo | OM |
|---|---|---|---|---|
| Q1 | main switch, 3-pole, 2:02-03 | not in the grid | UL "General Use 25A-600 Vac" (c144340) | PR25 FS 3EV 73, 25 A, BACO |
| Q2 | rotary cam switch; contact table at 2:01-02 points to 4:08, 4:17, 5:09, 6:14, 4:16 | not in the grid | "16 A 660 Vac", IEC 947-3, "08 98" (c144344) | PR12 26123 A4, 12 A, BACO |
| QF1 | M1, motor breaker 3-pole with auxiliary 43-44 NO | 10-16A | "EP1-M10 6-10A", auxiliary 43-44 (c144259); setting not read | GV2-M14 + GV2-AN11, 6-10A |
| QF2 | M3, motor breaker 3-pole | 1.6-2.5A | "EP1-M1.6 1-1.6A" (c144255) | GV2-M06, 1-1,6A |
| FA1, FA2 | T1 primary, 1-pole each | 12A | GB2-CB20 12 A (c144304) | GB2-CB20, 12A |
| FA3 | UZ1, 2-pole (L 1-2, N 3-4) | 12A | GB2-CD20 12 A (c144304) | GB2-CD20, 12A; OM p.41 calls it "FA1" (m022638) |
| FA4 | socket XC7, 1-pole | 6A | GB2-CB12 6 A (c144220) | GB2-CB12, 6A |
| XC7 | socket | ZÁSUVKA | DIN (Deutsches Institut für Normung, German standards body) rail socket ZS 20, 10/16 A 250 V (c144214) | "as actually built" (Russian: по настоящему выполнению) |
| (none) | two NOARK "Ex9BN C1" 1-pole MCBs (miniature circuit breakers) | not printed | rail 4, right end, unmarked wires (c144304) | not listed |

## 5. Contactors and relay

Coils 24 V AC (OM; the coils are drawn on sheet 4, w232949, w233009). OM types from p.47 (m023118); for KM4 and KM8 the OM adds "24В_ст/9А" (Russian, as transcribed).

| Device | Function | Coil | OM type | Photo |
|---|---|---|---|---|
| KM1A, KM1B | main contactors, in series | 4:09, 4:11 | EP1-C123 B | "EP1C093" is read beside KM6 only (c144247) |
| KM2 | M1 line | 4:13 | EP1-C123 B | type not read (c144247) |
| KM3 | M1 delta | 4:14 | EP1-C123 B | type not read (c144247) |
| KM4 | M1 star | 4:15 | EP1-C099 B | markers 1KM4 3KM4 5KM4 5KM4 (top), 6KM4 (bottom) (c144247) |
| KM6, KM7 | clutch (sheet-1 table 3 row; drawn on sheets 4-5, thread control) | sheet 4 | EP1-C099 B | type "EP1C093" beside KM6 (c144247) |
| KM8 | M3 | 4:12 | EP1-C093 B | type not read (c144247) |
| K1 | switches Y3 at ~48 V | 5:15 | RE6-0011 (p.49) | F. Lütze relay, one changeover 11-12-14, markers 11K1 14K1 (c144324) |

Grid (w213530, w193408): KM2-KM4 print "60Hz" in the 200 V 50 Hz column, while KM1A, KM1B and KM6-KM8 print 50Hz (section 8).

## 6. Earthing and X5

Earthing strip, 2:01-02. Sheet 1 prints an earth symbol in place of a designation, so "PE" is our join key for it.
- XP PE and ZF1 PE → PE.
- PE → XC3, T1, X10, X11, XC7, UZ1: the printed earthing list (w231128). Further earths: M1 through X10 PE, M2 through UZ1 PE and XC1 PE (lines 93-94; the XC1-M2 shield joins this line, the UZ1-XC1 shield ends on an unlabeled UZ1 circle, entry 21), M3 through XC3 PE (line 112).
- Y3 through XC3 PE (line 113, sure): Y3's printed earth joins M3's at a dot under the XC3 earth pin (2:30-31, w210838, w214644).
- ZF2 from X2 PE (line 83: green-yellow wire, photo only, c143806), on to UZ1 (line 84, [?]): the print ends ZF2's earth on the 4th circle of UZ1's top edge (unlabeled) beside the earth terminal; read as UZ1 PE (2:18-20, w210838; on-site entry 21). The 4th circle and the earth terminal stand in the print's wide column 20, left of the 21 tick (w231229), so sheet 2 draws UZ1 PE in column 20 and the earthing list names it "UZ1 PE (2:20)". UZ1's top edge as printed: N, L, two unlabeled circles (shield terminals in the paths table of sheet 2), earth terminal; sheet 2 keeps that order, draws the 3rd circle unlabeled with the UZ1-XC1 shield on it, and ends ZF2's earth on UZ1 PE as line 84 reads it.
- PE → X5: working earth bonded to PE (w231506).
- Photos: 3 PE terminals on rail 3 beside X10/X11 (c144309), 6 on rail 7 (c144214); 6 are drawn.

X5 (working earth, 0 V, 2:02) lists 17 terminals; each is one row of power_wires.csv:

| Group | Terminals | Return of (s:cc) |
|---|---|---|
| coils | K1 A2; KM1A A2 | 5:15; 4:09 |
| Y3 | XC3 6 | 2:31-32 |
| board UG50 | 4, 7, 9 [?], 11, 17, 20 | returns of section 3 |
| X10 | 12; 19; 21; 23; 28 | lighting (4:03); Y01 (5:02); Y14 (5:04); Y11 (5:07); Y10 (5:10) |
| other threads | BMR1 0V; PLC GND; TABLO - | 7:12; 8:03; 8:03-04 |

Conflicts and readings (all on the on-site list):
- 9UG50: X5 names it, but sheet 3 draws UG50 8 and 9 unused, and the board photo shows no 9UG50 marker (c144227). The row is kept as [?].
- 28X10: the full-resolution crop reads 28X10; the T paths table of sheet 2 had 26X10. The netlist follows the crop.
- Sheet 8's table places X5 at "2:01" (v015117); the list sits at 2:02.
- The photo shows about 13 X5 terminals (c144214); 17 are printed.

## 7. Printed, not fitted, or not in the netlist

- **Variant "FA3 A,B"** (2:24-25, dashed, "ZAPOJENÍ MĚNIČE PRO 230V", inverter wiring for 230 V mains, w210838): for 3 x 230 V mains, FA3's poles A, B take L2 and L3 instead of L3 and N.
  - This machine runs on 400 V with N, so the variant is not fitted.
  - Its conductors are left out of power_wires.csv; with them in, ZF2's N would join L2.
  - Drawn dashed on power_sheet2.svg from the VARIANT table of power_draw.py.
- **FF1, light curtain** (~230 V from X11 3, 0 V from X11 1, and PE; dashed at 3:01 with no cross-reference; the dashed line ends on 3X11, while 4X11 hangs below it): OM p.14 places FF1 (Fig. 3.1, m004647); the certificate shows "—" for it (w195028); not seen in any photo.
  - Device row FF1 [?]; its three feeds are left out of power_wires.csv.
  - Drawn dashed on power_sheet3.svg from the OPTION table of power_draw.py.
- **Two NOARK MCBs** at the right end of rail 4 (c144304): in no 568 sheet and no OM list, no designation, unmarked wires. Likely added after 1998; load unknown.
  - Not in the netlist; no name such as FA5/FA6 is invented.
- **Grey box** on rail 4 between KT2 and QF1 (c143210): unidentified, in no 568 sheet or OM list; not in the netlist.
- **No conductor on sheets 2-3, by design:**
  - FF1 (option);
  - Q2, whose contacts are drawn on sheets 4-6;
  - V13 and V23 (section 3).
- **Unused:** winding III; UG50 outputs 3, 8, 9, 15, 16 have no printed destination.

## 8. Conflicts between sources, as printed

1. M2: grid "3x380V" (w213530), but UZ1 takes 230 V single phase (L3 + N through FA3) and gives 3/AC 0-230 V (c144201).
2. KM2-KM4: "60Hz" in the 200V 50Hz column of the grid (w213530, w193408); sheet 1 shows it as printed with " [?]".
3. T1 (w231949, w232117):
   - the table names 0-415, but no 415 tap is drawn;
   - the taps -40V and -20V are drawn but used in no row;
   - sets 567 and 581 draw a 415V tap (o215057, o220210).
4. Y3:
   - OM p.42 (m022721) says UZ1 controls Y3;
   - the 568 switches Y3 with K1 at ~48 V (2:30-32).
5. Inverter breaker:
   - OM p.41 (m022638) calls it "FA1";
   - the 568 (2:18), OM p.47 and photo rail 4 (c144304) call it FA3.
6. K1 contact:
   - the print has 13-14 (2:30);
   - ink "11" is written over "13" on the clean copy (w231229);
   - the photo markers read 11K1, 14K1 (c144324). The netlist follows the photo: 11-14.
7. X5: "2:01" in sheet 8's table (v015117) vs the list at 2:02; 9UG50 vs sheet 3 (section 6).
8. Mains: the grid of sheet 1 prints 5 mains variants, 380V 50Hz, 415V 50Hz, 220V 50Hz, 220V 60Hz and 200V 50Hz (w213530); the T1 tap table of sheet 3 has rows for 200, 230, 380, 400 and 415 V mains (w231949); the door plate gives Ue 400/230 V, f 50 Hz (c142805); sheet 3 is drawn for 400 V.

## 9. On-site list

**Before any entry: Q1 off does not make the cabinet dead.** With Q1 at 0, XP, the mains filter ZF1, the breaker FA4 and the socket XC7 stay live (OM p.12, m004236; section 2). The NOARK pair may stay live too, since its supply is unknown (entry 24). Isolate the machine upstream (the wall isolator, or the distribution-board breaker or fuses that feed XP), lock it off, and test for dead at XP before any work in the cabinet. The inverter UZ1 keeps its DC bus (+UG/-UG, entry 35) charged for a while after isolation: wait for the time its label or manual gives, then measure before touching. Entry 29 is the only measurement on live parts. It is for a qualified electrician with a meter and test leads rated for mains work (measurement category III or higher).

The netlist marks 32 rows as not sure: 13 device rows [?]; 14 wire rows [?] and 5 wire rows estimated ±1 column. On the sheets each of them shows its mark once ("[?]", or "est. ±1 col"; section 10). Keys:
- devices: the designation;
- wires: `from_device from_terminal -> to_device to_terminal`, with the line in power_wires.csv (header = line 1).

The other entries come from photo differences and source conflicts. Every entry says what to look at or measure, where, and what raised it.

| # | Key | Look at or measure | Where | Raised by |
|---|---|---|---|---|
| 1 | `X8` | find a terminal strip marked X8; note its terminals and place | cabinet, console, machine base | sheet-1 table 2 lists it (w213530); not drawn on sheets 1-4, not in any photo |
| 2 | `XC4` | read the label and pin count of each connector | cabinet wall to the machine; OM Fig. 10.2 shows XC2, XC4, XC1, XC3 top down (m023222) | sheet-1 table 2 (w213530); drawn on sheet 8; label not seen |
| 3 | `XC2` | as entry 2 | as entry 2 | sheet-1 table 2 (w213530); drawn on sheets 5-6; label not seen |
| 4 | `XC50` | confirm that the plug on the PLC's "ANALOG OUTPUTS" is XC50; UZ1 7 on pins 6+9, UZ1 8 on pin 4 | PLC front, cabinet plate row 2 | 2:25-26; plug without XC label (c142944) |
| 5 | `XC60` | confirm the name of the plug on the PLC's serial port IF1 (RS232, Recommended Standard 232) | PLC front | sheet-1 table 2, drawn on sheet 8; no XC label (c142944) |
| 6 | `XC70` | find the connector and read its label | cabinet, console | sheet-1 table 2 (w213530), drawn on sheet 8; not seen |
| 7 | `C3` | find the 2µ2/230V capacitor across Y3: at Y3 on the machine, or at XC3 5-6 in the cabinet; read its value | air-cushion magnet Y3; connector XC3 | drawn below XC3 beside Y3 at 2:31-32 (w210838) |
| 8 | `V01` | read the name and the type of the diode across the Y01 coil: 568 1N 4002, OM BY 399 | across the coil of the knife-lock magnet Y01 (5:02, w212623): at the magnet on the machine, or at X10 18-19 in the cabinet | components table reads "V01" [?] (w213823); OM list 10.1 p.46 names V01, V14 as the suppression diodes of Y01 and of the brake Y14 (m023023) |
| 9 | `V4` | read the type on the bridge rectifier: CM2506 or CW2506 | board UG50, cabinet plate row 6 | print unclear at 3:03 (w232117) |
| 10 | `C4` | read the fitted capacitor (print: 1000µF/63V); check that it sits between V4 + and - and UG50 10/11 | board UG50 | blue "SAMWHA 4700µF 63V" over the empty places C3/C4 (c144231) |
| 11 | `R16` | read the wattage of the 3k3 resistor | board UG50 | wattage digit missing in the print (w232117) |
| 12 | `R17` | as entry 11 | board UG50 | as entry 11 |
| 13 | `FF1` | confirm no light curtain is fitted and nothing leaves X11 3 or X11 1 towards one | machine front; X11 in the cabinet | dashed at 3:01, from 3X11 (w232117); certificate "—" (w195028); OM p.14 places FF1 (Fig. 3.1, m004647) |
| 14 | `X5 -> UG50 9` (line 26) | is a wire on UG50 terminal 9, and does it go to X5? Also look for wires on UG50 3, 8, 15, 16 | board UG50 terminals; X5 | X5 list 2:02 vs sheet 3 "8, 9 unused"; no 9UG50 marker (c144227) |
| 15 | `X10 6 -> KM4 1` (line 65), `KM4 1 -> KM4 3` (66), `KM4 2 -> X10 4` (67), `KM4 4 -> X10 5` (68) | read every wire marker on KM4; note which poles form the star bridge and which go to X10 4, 5, 6 | contactor KM4, rail 5 | print 2:11-12 bridges 1-3 only; photo markers 1KM4 3KM4 5KM4 5KM4 (top), 6KM4 (bottom) suggest a 3-pole bridge (c144247) |
| 16 | `PLC OUT-B -> UZ1 E3` (line 96), `PLC OUT-C -> UZ1 E4` (97), `PLC OUT-D -> UZ1 28` (98) | follow the wires from UZ1 E3, E4 and 28 to PLC outputs B, C, D; read the E3 marker | UZ1 control terminals; PLC outputs | paper: column read ±1 at 2:22-24 (w214644, w231229); E3 marker [?] |
| 17 | `UZ1 7 -> XC50 6+9` (line 99), `UZ1 8 -> XC50 4` (100) | follow the shielded pair (red, grey in the photo) to XC50 pins 6+9 and 4 | UZ1; XC50 at the PLC | paper: column read ±1 at 2:25-26 (w214644, w231229) |
| 18 | `XC3 5 -> C3 1` (line 118), `C3 2 -> XC3 6` (119) | with entry 7: where C3's two leads land | XC3; Y3 | 2:31-32 (w210838) |
| 19 | `X11 2 -> X11 1` (line 121), `X11 3 -> X11 4` (125) | read the bridges on X11; which terminal takes the FA1 wire (marker 2X11) and the wire to T1 0V | X11, rail 3 | print bridges 1-2 and 3-4 (3:01, w232117); photo bridges 3-4, 5-6 and a yellow 1-4 [?] (c144309) |
| 20 | `V4 + -> C4 +` (line 171), `C4 + -> UG50 10` (172), `V4 - -> C4 -` (173), `C4 - -> UG50 11` (174) | trace V4 + and - to the fitted capacitor and on to UG50 10, 11 | board UG50 | printed traces (3:03, w232117); board repaired (c144231) |
| 21 | `X2 PE -> ZF2 PE` (line 83), `ZF2 PE -> UZ1 PE` (line 84) | confirm the green-yellow wire from X2 PE to ZF2; follow ZF2's earth on and read where it lands on UZ1 (its earth terminal?); read what UZ1's two unlabeled top-edge terminals are and whether they are on PE: the 4th takes ZF2's earth, the 3rd the shield of the UZ1-XC1 cable | plate row 6: X2, ZF2, UZ1 | X2 PE: photo only (c143806), the 568 draws X2 with N and L only (2:18); ZF2 to UZ1: the print ends the earth on the 4th circle of UZ1's top edge (N, L, two unlabeled circles, earth terminal) and the UZ1-XC1 cable shield on the 3rd; the paths table of sheet 2 calls the two circles shield terminals (2:17-20, w210838, w231229) |
| 22 | QF1 | read the fitted type and the current setting; read M1's rated current on its plate | rail 4; motor M1 | 568 10-16A vs photo EP1-M10 6-10A (c144259) vs OM GV2-M14 6-10A |
| 23 | QF2 | read type and setting; read M3's rated current | rail 4; blower M3 | 568 1.6-2.5A vs photo EP1-M1.6 1-1.6A (c144255) vs OM GV2-M06 1-1,6A |
| 24 | NOARK pair | trace the supply and the loads of both NOARK "Ex9BN C1" breakers; read any label | rail 4, right end | in no 568 sheet or OM list (c144304) |
| 25 | Grey box | identify the box and its wiring | rail 4, between KT2 and QF1 | not in any list (c143210) |
| 26 | K1 contact | read the terminal numbers used on K1: 11-14 or 13-14 | relay K1, plate row 2 | print 13 vs ink "11" (2:30, w231229) vs markers 11K1 14K1 (c144324) |
| 27 | K1, K2 type | read the relay plates | plate row 2 | photo F. Lütze (c144324) vs OM RE6-0011 (m023314) |
| 28 | Contactor types | read type, coil voltage and coil frequency of KM1A, KM1B, KM2-KM4, KM6-KM8 (also settles entry 31) | rails 4 and 5 | photo type "EP1C093" read beside KM6 only (c144247) vs OM p.47 types (m023118) |
| 29 | Mains | live, see "Before any entry": measure L1-L2, L2-L3, L3-L1 and L-N at XP; then, isolated again, confirm FA2 → tap 400V and FA1 → tap 0V | XP; T1 | door plate Ue 400/230 V, f 50 Hz (c142805); sheet 3 drawn for 400 V |
| 30 | T1 plate | read the plate: tap voltages (is there a 415 tap? what are the -40V and -20V taps for?), secondary voltages, VA | T1 on the cabinet floor | no plate seen (c144220); OM JOC-U 4056-130 (m023314); tap table conflict (w231949): it names 0-415 with no 415 tap drawn, and the drawn taps -40V and -20V are in no row of it |
| 31 | KM2-KM4 coils | read the coil frequency | rail 5 | grid "60Hz" in the 200 V 50 Hz column (w213530, w193408) |
| 32 | M2 plate | read rated voltage and the star/delta link of M2 | backgauge motor M2 | grid "3x380V" (w213530) vs UZ1 output 3/AC 0-230 V (c144201) |
| 33 | Y3 control | follow Y3's wire from XC3 5 back to K1, or to UZ1 | XC3; K1; UZ1 | OM p.42 Y3 via UZ1 (m022721) vs 568 K1 at ~48 V (2:30-32) |
| 34 | Inverter breaker label | read the label on the 2-pole breaker that feeds X2 | rail 4 | OM p.41 "FA1" (m022638) vs 568 2:18 and photo "FA3" (c144304) |
| 35 | UZ1 +UG/-UG | confirm no brake resistor or other wire on +UG/-UG, the inverter's DC bus terminals (after the wait in "Before any entry") | UZ1 power terminals | unwired [?] (c144205) |
| 36 | ZF1 type | read the plate of the filter | bottom rail 7 | photo: brown box, type not read (c144214); OM 3F+N K4510410 (m023314) |
| 37 | Q2 rating | read the plate: 16 A or 12 A | switch plate, front face | plate "16 A 660 Vac" (c144344) vs OM list 10.1 p.44: PR12 26123 A4, 12 A (m022802) |
| 38 | X5 terminals | count the terminals; read the marker of the wire to X10: 28X10 or 26X10 | X5, bottom rail 7 | 17 printed (2:02) vs about 13 in the photo (c144214); crop 28X10 vs paths table 26X10 (w231128) |
| 39 | PE count | count the PE terminals; confirm the earth of XC3, T1, X10, X11, XC7, UZ1 | rails 3 and 7 | 6 drawn (2:01-02) vs 3 + 6 in the photos (c144309, c144214) |
| 40 | X5 column | paper only: both references point to the one strip X5; confirm there is one X5 | X5 | sheet 8 table "2:01" (v015117) vs list at 2:02 |
| 41 | XP terminals | count the phase terminals and read their markers | XP, bottom rail 7 | 6 printed (two per phase, w210810) vs 7 yellow in the photo (c144214) |
| 42 | Red ink on sheet 1 | confirm each place the red notes give: S28 a clamp sensor with the plate ("– Д. пресса с пластиной"); S19 and S5 at the flywheel ("(у маховика)"); SQ1, SQ2 on the axle of the knife lock ("(на оси стопора)") | machine: clamp beam (S28); flywheel side (S19, S5); knife lock (SQ1, SQ2) | later red ink in Russian beside table 1 of the annotated copy (w192726), not print; quoted in power_devices.csv term_cz_ru |

## 10. Rules for joining (t5) and for the drawing

Names and keys:
- Designations are as printed. "PE" stands for the earthing strip that sheet 1 marks only with a symbol.
- Board parts keep their printed names with the note "on board UG50". The two names that clash with other sheets are qualified:
  - UG50/R14 (1k2) vs R14 of sheet 7 (OM 11R-25W, m023314; its ends: 1 = UG50 2 end, 2 = BMR1 25 end);
  - UG50/V14 (indicator) vs V14 of sheet-box 5.
  - With that, a join on designation is safe: the bare names R14 and V14 stay with the sheet-7 resistor and the sheet-box-5 diode.
- The 568 C3 (2µ2/230V across Y3) is not the board's empty silk place C3 (c144231).
- "RC..." is the group row of the RC (resistor-capacitor) suppressors of sheet-box 4; their single names RC1-RC4 and RC6-RC8 are drawn on sheet 4 (thread control).

Rows:
- One row per conductor; three-phase runs are split per phase. T1 terminals are named winding + tap: "I 21V", "I 0V" ... "VI 0V".
- Unprinted end names:
  - fuse, resistor, indicator diode or LED: 1 = upper or left end as drawn, 2 = lower or right end;
  - bridge rectifier: ~1 upper AC end, ~2 lower AC end, + and -; capacitor: + and -;
  - Y3 and C3: 1 = XC3 5 side, 2 = XC3 6 side;
  - no diode polarity is claimed (indicator pairs are drawn anti-parallel).
- Wire and cable columns are empty: the 568 prints no wire numbers. Connector and pin are filled only for XC1, XC3 and XC50.
- Devices of the sheet-1 tables that are drawn on sheets 4-8 get sheet 1, an empty column and the note "drawn on sheet N (thread ...)".
- Empty place: V01, V14, V10, R10 and RC11 (sheet-box 5 parts drawn on sheet 5) have an empty place, because the 568 does not print where they sit. t5 takes their place from thread t2 if it has one, else leaves it empty.
- Off-sheet ends are resolved to the far device in the paths tables of sheets 4-8 (T/11_568_sheet4_paths.csv, T/12_568_sheet5_paths.csv to T/12_568_sheet8_paths.csv). The printed arrow stays in the note. Never "4:01" as an end.
- Far ends in other threads: PLC (6 rows), BMR1 (4), TABLO (1).
- K1: the photo rules (11-14); the print and the ink are quoted in the note.

Drawing (power_draw.py):
- Both ends on the same sheet: a routed line.
- Otherwise, or for the printed cross-references 1FA4, 3FA3, N → XC7, the earthing list, the X5 list and XC3 6: a stub arrow labelled "<device> <terminal> (s:cc)".
  - s:cc comes from the note's printed arrow, else from a quoted print label naming the far device, else from the far stub's column.
  - One fixed label: QF1 44 → "BMR1 19 (7:01)".
- Marks: each not-sure row shows its mark exactly once on its own sheet (the row's sheet field) and at most once on another sheet: "[?]", or "est. ±1 col" for "estimated ±1 column".
  - The mark stands on the row's stub label, beside its routed line (X11 bridges, ZF2 earth to UZ1), or after its designation (sheet-1 tables put it after each not-sure name of a group: "XC50 [?], XC60 [?], XC70 [?]").
  - Rows of one reason share one text: KM4 "terminals [?]" (the 4 KM4 rows), "C3 [?]" (C3 and its 2 wires), "C4 [?]" (C4 and its 4 board traces), "E3, E4, 28: est. ±1 col", "7, 8: est. ±1 col".
  - A text that shows the mark of rows names them in its attribute data-rows="D:<designation>|W:<from> <terminal> -> <to> <terminal>"; the self-check of power_draw.py counts them ("not-sure rows marked once on their sheet 32/32", part of its bad 0).
  - Other "[?]" texts are notes on source conflicts, not row marks: "60Hz [?]" (sheet 1 grid), "0 - 415 [?] no 415V tap drawn", "-20V, -40V: in no row [?]", "UZ1 +UG/-UG unwired [?]".
- Dashed = printed variant or option, not fitted (section 7); thin dashed = a pole link or a cable shield.
- Ratings and plate data on the sheets come from type_rating of power_devices.csv, never from literals in the script.

## 11. Sources

Numbers of section 1:
- row counts: the output line of power_netlist.py;
- drawing counts: the output line of power_draw.py;
- the clone lines: both scripts run in a copy that holds only the stage_2_electronics files (761 = all source paths of the CSV rows);
- the 32 not-sure rows: the evidence column of both CSV files (rows whose mark is not "sure").

Each stem below is one file:
- w = preparatory_data_analysis/maxima_documents/adast_guillotine_wiring_and_plc_diagrams/20261113_<stem>.jpg; v = the same folder, 20261114_<stem>.jpg;
- c = preparatory_data_analysis/maxima_photos/20261102_<stem>.jpg;
- m = preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/20261115_<stem>.jpg; n = the same folder, 20261114_<stem>.jpg;
- o = preparatory_data_analysis/maxima_documents/schemes_folder_1/20261103_<stem>.jpg;
- T = static_dynamic_memory/blocks/generation_002/artifacts/tables (local working tables).

| Stem | Shows | Used for |
|---|---|---|
| w213049, w213216 | sheet 1: tables 1-3 (w213049), table 1 (w213216) | device list, functions |
| w213530 | sheet 1, tables 2-3, variant grid | breaker ratings, "3x380V", "60Hz", X8, XC2, XC4, XC70 |
| w193408 | variant grid, second copy | "60Hz" |
| w213823 | sheet 1, components table | board parts, V01, sheet-box 4-5 parts |
| w192726 | sheet 1, copy with ink | ink only, quoted: red notes at S28, S19, S5, SQ1/SQ2 (on-site entry 42) |
| w214644 | sheet 2, clean copy | all of sheet 2 |
| w210810 | sheet 2, feed | XP, ZF1, Q1, KM1A, KM1B, T1 feed |
| w210815 | sheet 2 | FA4, XC7, FA3, X2, ZF2 |
| w210838 | sheet 2 | UZ1, M2, M3, Y3, C3, variant FA3 A,B |
| w231128 | sheet 2, close-up | M1 star-delta, Q2 contact table, earthing list, X5 entries |
| w231229 | sheet 2, close-up | K1 ink "11", UZ1 control |
| w231506 | sheet 2, close-up | X5, working earth |
| w232117 | sheet 3 | T1, UG50, FF1 option |
| w231949 | sheet 3, tap table | T1 taps per mains voltage |
| w232949, w233009 | sheet 4 | contactor coils |
| w212623, w212711; w194606; w193629; w191800, v015117, v015721 | sheets 5; 6; 7; 8 | far ends of off-sheet arrows; X5 "2:01" (v015117) |
| w195028 | machine certificate | FF1 "—" |
| c142805 | door plate | Ue 400/230 V, f 50 Hz (also on the XP row) |
| c142944 | PLC plugs | XC50, XC60 without label |
| c143210 | rail 4 | grey box |
| c143806 | plate row 6 | UG50, X2, ZF2, UZ1; X2 PE → ZF2 |
| c144201, c144205 | UZ1 plate, terminals | Lenze data; +UG/-UG unwired |
| c144214 | bottom rail 7 | ZF1, XP, PE x6, X5, XC7 socket data |
| c144220 | cabinet floor | T1 without plate; FA4 GB2-CB12 |
| c144227, c144231 | board UG50 | no 9UG50 marker; SAMWHA repair |
| c144247, c144251 | contactor rails | "EP1C093" beside KM6 (the family reading on the KM1A row); KM4 markers |
| c144255, c144259 | QF2, QF1 | EP1-M1.6, EP1-M10, auxiliary 43-44 |
| c144304 | rail 4 | FA1-FA3 GB2 types, NOARK pair |
| c144309, c144314 | rail 3 | X10, X11 bridges, PE x3 |
| c144324 | plate row 2 | K1, K2 F. Lütze, markers 11K1 14K1 |
| c144340, c144344 | switch plate | Q1 UL plate; Q2 plate |
| m004236 | OM p.12 | live with Q1 off |
| m004647 | OM p.14 | places FF1 (Fig. 3.1) |
| m011308 | OM p.20 | mains data |
| n215113 | OM p.7 | M1 4 kW; 5.5 kVA |
| m022638 | OM p.41 | "FA1" for the inverter breaker |
| m022721 | OM p.42 | Y3 via UZ1 |
| m022802 | OM p.44, list 10.1 | Q1, Q2 types (PR25 FS 3EV 73 25 A, PR12 26123 A4 12 A); M2 550 W, M3 370 W |
| m023023 | OM p.46, list 10.1 | V01, V14: suppression diodes of Y01 and of the brake Y14, BY 399 |
| m023118 | OM p.47 | breaker and contactor types |
| m023222 | OM p.48, Fig. 10.2 | places only: connector order XC2, XC4, XC1, XC3 on the cabinet wall |
| m023314 | OM p.49 | T1, K1/K2, UZ1, ZF1, ZF2 types; R14 11R-25W |
| o215057, o220210 | sets 567, 581, sheet 3 | 415V tap drawn |
| T: 11_568_devices.csv, 11_568_sheet1_variants.csv, 11_568_sheet2_paths.csv, 11_568_sheet3_paths.csv, 11_568_sheet4_paths.csv, 12_568_sheet5_paths.csv to 12_568_sheet8_paths.csv, 12_568_plc_io.csv, 18_manual_device_list.csv | transcription tables | device list, grid, paths per column, PLC addresses, OM list |
