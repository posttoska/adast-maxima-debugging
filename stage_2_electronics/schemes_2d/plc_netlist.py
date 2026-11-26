#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Netlist of set 568-70.9001 sheet 8 (thread t3, plc_drive): PLC, console terminal TABLO,
inverter UZ1 control side, encoder BR40, backgauge positioning signals.

Run:     python -B stage_2_electronics/schemes_2d/plc_netlist.py      (from anywhere)
Writes:  ../netlist/plc_drive_devices.csv, ../netlist/plc_drive_wires.csv (UTF-8, no BOM)
Data:    the DEVICES and WIRES tables below, transcribed from the photographed paper sheet 8
         (clean copies 20261114_015721 top, 20261114_015117 bottom; annotated copy 20261113_191800
         with the table TABULKA PŘIPOJENÍ) and checked against the cabinet and console photos
         (20261102_*): PLC 144328, X10 144309, UZ1 144205, console 151912-152107.
Rules:   photos rule what is wired, else the 1998 set. Conductors that sheet 8 shares with
         power_wires.csv (t1) or control_wires.csv (t2) keep those rows' ends, direction and signal
         text, so the merge (t5) finds them by their ends. Red ink is quoted as ink, never as print.
Checks (exit 1 on a failure):
  headers and encoding; one row per designation; marks; source paths exist (skipped when
  preparatory_data_analysis/ is absent) and are relative; both ends of every wire are devices of
  this file and every device has a wire; the 14 PLC addresses of check 4 on the PLC, one signal
  each; every row of the sheet-8 paths table and of the PLC I/O table mapped to rows here and no
  wire on a PLC terminal the table leaves unused (skipped when static_dynamic_memory/ is absent);
  join with ../netlist/power_wires.csv and control_wires.csv: every conductor described there too
  is listed with each field that differs, every row of theirs that touches a device of sheet 8 is
  matched here or explained (skipped while absent); copied rows of devices of other threads equal
  their owners' rows; every [?] or estimated row keyed in the on-site list of ../spec/plc_drive.md
  (skipped while absent); every clause of a note, type, signal or function that reads a port or pin
  function (PORT_WORDS, PIN_CLAIM; quoted print left out) carries its own mark, a pin claim also a
  manual page instead.
"""
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = HERE.parent
P = S.parent
NET = S / 'netlist'
TAB = P / 'static_dynamic_memory' / 'blocks' / 'generation_002' / 'artifacts' / 'tables'
SPEC = S / 'spec' / 'plc_drive.md'
PFX = {'d': 'preparatory_data_analysis/maxima_documents/adast_guillotine_wiring_and_plc_diagrams/{}.jpg',
       'p': 'preparatory_data_analysis/maxima_photos/20261102_{}.jpg',
       'om': 'preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/{}.jpg',
       'l': 'preparatory_data_analysis/maxima_documents/operating_instructions_global_drive_frequency_inverters_8200_series/{}.jpg',
       'pm': 'preparatory_data_analysis/maxima_documents/control_panel_manual/{}.jpg',
       'w': 'static_dynamic_memory/blocks/generation_002/artifacts/web/{}',
       't': 'static_dynamic_memory/blocks/generation_002/artifacts/tables/{}'}
SH = {'power': 'same conductor as a row of power_wires.csv (thread power): keep one when merging',
      'control': 'same conductor as a row of control_wires.csv (thread control): keep one when merging'}
DEV_HDR = 'designation,kind,function_en,term_cz_ru,type_rating,place,sheet,column,evidence,source_path,note'.split(',')
WIRE_HDR = ('wire,from_device,from_terminal,to_device,to_terminal,signal,plc_address,connector,pin,'
            'cable,sheet,column,evidence,source_path,note').split(',')
OWN = ['PLC', 'TABLO', 'BR40', 'XC4', 'XC50', 'XC60', 'XC70']     # devices of sheet 8 (this thread)

# designation | kind | function_en | term_cz_ru | type_rating | place | sheet | column | evidence | sources | note
DEVICES = r"""
PLC | programmable logic controller | programmable logic controller of the cut cycle and the backgauge: clamp and cut-done inputs, encoder BR40 count, backgauge drive commands to UZ1, feed-cut interlock K2, air-cushion control, serial link to the console terminal TABLO | COMPACT PLC (ZAPOJENÍ ŘÍDÍCÍHO AUTOMATU - PLC = wiring of the control automaton); OM p.49 "BR COMP 1-0" | B&R COMPACT P.L.C.: 16 inputs 24 VDC, 14 outputs 24 VDC 1 A per terminal, max. 7 A per P.L.C., fuse 1.25 AT (photo 144328); W: BRCOMP1.0 | cabinet | 8 | 01-05 | sure | d:20261114_015117 d:20261114_015721 d:20261113_191800 p:144328 p:142944 om:20261115_023314 w:br-automation/brcomp1-0.html | terminal names as printed: OUT-0 to OUT-D; +24V twice (one node: sheet 8 joins both at a junction dot; photo labels them "Outputs +24 VDC" and "P.L.C. Input +24 VDC"); GND twice under one bracket (one node); IN-0 to IN-F; IN-GND = the two GND of the input row, named as in the sheet-8 table; ports (photo): IF1 RS232 with a plug (XC60 [?]), ANALOG OUTPUTS with a plug (XC50 [?]), IF2 RS232/RS485, IF3, IF4 ONLINE, IF5 CAN (option), ANALOG INPUTS free; program label "ADAST154.PGP v1.54 98/05/20 MK"; the five D-sub drawn without designation are not connected on sheet 8
TABLO | control panel | console operator terminal: keys and display for cut programs and backgauge positions; serial link to the PLC | OVLÁDACÍ TABLO (TABLO; POHLED ZE ZADNÍ STRANY = view from the rear) | B&R panel: 4E0040.01-590, a keypad module (estimated, by the 4E family, OM p.46), display module 4D1084.00-590, board 22511030/2 (photos); +24 V DC (sheet 6: "TABLO +24V (8:03)"; sheet 8 prints only "+") | console | 8 | 01-03 | sure | d:20261114_015721 d:20261113_191800 d:20261114_014325 p:151912 p:151951 p:151959 p:152038 p:152107 om:20261115_023023 pm:20261103_233320 | sheet 8 draws its rear: terminal block ⏚, −, + and three sockets on the right edge, the middle one XC70 "⇒ PLC"; terminal "+" is written "+24V" here, the key of the same conductor in control_wires.csv (sheet 6 prints "TABLO +24V (8:03)"), "−" is "-", ⏚ is "PE"; OM p.46 names panel controller 4C 2000.01-510 and keypads 4E 0041/0011/0021.01-590 against 4E0040.01-590 in the photo (on-site list); key legend in Latvian (control panel manual 233320)
BR40 | rotary encoder | backgauge position encoder: channels A, B and index I counted by the PLC on IN-F, IN-E, IN-D | SNÍMAČ BR40 (KONEKTOR SNÍMAČE BR40 = connector of sensor BR40); RU абсолютный ротационный датчик (absolute rotary sensor, OM p.41) | sheet 8: pins A, B, I, +, − (incremental A/B/index), +24V supply; type not printed: OM p.46 EUCHNER P39SSPPBI1000-123-24; ink on sheet 8: EUCHNER PA50/Welle 06/Imp. 1000, Ident.Nr. 075043, Volt 5-30, Ver. 24, Seriennummer 9813 12 344, PA50-06-1000-24; later ink OMRON 1000P E6B2-CW26C | machine | 8 | 04 | [?] | d:20261114_015117 d:20261113_191800 om:20261115_023023 om:20261115_022638 w:omron/rs_9200d9fd.pdf | [?] = its type: three candidates (on-site list); W: Omron E6B2-CWZ6C is NPN open collector with a cable of at most 2 m, the B&R inputs are "sink" (W); OM p.41 calls it absolute, sheet 8 wires incremental A, B, I
XC4 | connector | connector of sensor BR40 (encoder) | KONEKTOR SNÍMAČE BR40 | plug and socket, contacts 1-5 and shell (sheet 8) | cabinet | 8 | 03-04 | [?] | d:20261114_015117 d:20261113_191800 d:20261113_213530 om:20261115_011308 om:20261115_023118 om:20261115_023222 p:144555 t:17_cable_routes.csv t:18_manual_device_list.csv | [?]: photo 144555 shows a round connector beside a yellow wall label read "XC4" [?] (17_cable_routes.csv line 13); OM p.48 (023222) Fig. 10.2 view P puts XC4 second (round) on the connector plate; OM p.47 (023118), the parts list of that figure, gives its order numbers and type (18_manual_device_list.csv line 72, whose source column names p.47 only); the label reading stays unsure (t1 on-site item XC4); pins to BR40 from the sheet-8 table: 1 I, 2 B, 3 A, 4 −, 5 +; 7XC4 bonds the shells of both halves; OM p.20 writes XC40 (011308): XC4 as printed
XC50 | connector | control-system connector (PLC analog outputs to UZ1 7, 8) | KONEKTORY ŘÍDÍCÍHO SYSTÉMU (ŘÍZENÍ RYCHLOSTI SEDLA = backgauge speed control) | 9-pin D-sub (sheet 8); pins 4 and 6+9 used | cabinet | 8 | 05 | [?] | d:20261114_015117 d:20261113_191800 p:144328 p:142944 | on the PLC, arrow "UZ1" above it; photo: a plug on ANALOG OUTPUTS (legend GND * * GND over U1 I1 * U2 I2), no XC label: XC50 [?]; counted as the other PLC port legends read (4-pin row on top, wide row 5-4-3-2-1 from the left: the count that makes IF2's full legend an RS232 port and gives IF1 3 TxD, 5 GND): U1 5, I1 4, U2 2, I2 1, GND 9 and 6 (estimated); so pins 6 and 9 are the two GND and pin 4 = I1, a current output (estimated; on-site list: which pin is wired, the jumper at UZ1 terminal 8, C034)
XC60 | connector | control-system connector (PLC side of the TABLO link) | KONEKTORY ŘÍDÍCÍHO SYSTÉMU (PROPOJENÍ PLC-TABLO = PLC-TABLO link) | 9-pin D-sub (sheet 8); pins 2, 3, 5 and shell used | cabinet | 8 | 04 | [?] | d:20261114_015117 d:20261113_191800 p:144328 p:142944 | on the PLC, arrow "TABLO" above it; photo: the grey cable's plug on IF1 RS232 (legend partly hidden by the cable: GND, +5V, TxD, DSR, RTS readable), no XC label: XC60 [?]; counted as the PLC port legends read (4-pin row on top, wide row 5-4-3-2-1 from the left, the count that makes IF2's full legend an RS232 port): pin 5 GND, 4 +5V, 3 TxD, 2 RxD (hidden by the cable) (estimated)
XC70 | connector | control-system connector (TABLO side) | KONEKTORY ŘÍDÍCÍHO SYSTÉMU (XC70 ⇒ PLC) | pins 2, 3, 5 and shell used (sheet 8) | console | 8 | 03 | [?] | d:20261114_015721 d:20261113_191800 p:151959 t:22_web_b_br_connectors.csv | middle one of three sockets on the TABLO's rear edge; column 03: the table's LINIE "8:03 / 8:04" for the link puts XC70 in 03 and XC60 in 04, and the socket stands under the ruler tick 03 (the sheet-8 paths table reads 02); console photo 151959: a board with three D-sub and a power plug, no XC label seen (on-site list); W: panel controller 4C2000.01-510 IF1 RS232 has 2 RxD, 3 TxD, 5 GND (PANELWARE manual p.99, saved as 22_web_b_br_connectors.csv lines 11-15); 4C2000.01-510 is the OM's controller, not seen fitted (on-site item 16)
X10 | terminal strip | terminal strip in the cabinet (1-6 to M1) | SVORKOVNICE V ROZVADĚČI | 45 terminals + 3 PE (photo) | cabinet | 2 | 04-09 | sure | d:20261113_213049 d:20261113_213530 d:20261113_231128 p:144309 p:144314 | device of thread power; on sheet 8: 33 (TABLO +24V), 35 (PLC +24V), 45 (TABLO 0V, on to X5), PE (TABLO earth), 29 and 30 (IN-2, IN-1); photo 144309: inside markers 35X10 and 45X10, field sleeves 33 and 45, a bridge over 31-36
X5 | terminal strip | working-earth strip: 0 V of all control supplies, bonded to PE | SVORKOVNICE PRAC. ZEMĚ | 17 terminals drawn; photo about 13 | cabinet | 2 | 02 | sure | d:20261113_213049 d:20261113_213530 d:20261113_231506 p:144214 | device of thread power; on sheet 8: PLC GND and, through 45X10, TABLO −; the sheet-8 table writes "X5 2:01", the terminal labels "X5 (2:02)"
UZ1 | frequency inverter | M2 feed drive | MĚNIČ | Lenze EVF8202-E-V002; in 1/N/PE AC 230 V 9.0 A; out 3/AC 0-230 V 4.0 A 0.75 kW | cabinet | 2 | 17-26 | sure | d:20261113_210838 d:20261113_231229 p:144201 p:144205 | device of thread power; control terminals on sheet 8: 7 and 8 (to XC50), 28, E3, E4 (from PLC OUT-D, OUT-B, OUT-C), 39 (to PLC GND), K12 (to IN-8); K14 is fed from 34X10 (sheets 2 and 6); control side in spec/plc_drive.md
BMR1 | cut-control module (board) | cut-control module: two-hand start, knife lock, clutch contactors, cut-done signal | MODUL ŘÍZENÍ ŘEZU (PŘIPOJENÍ MODULU ŘÍZENÍ ŘEZU BMR1); RU релейный модуль управления реза | one relay board, plate "BMR2" (photo 143021), maker not printed or seen; terminals 1-29, 0V (-), +24V (+); OM list 10.2 "BMR.." 900 010 0714 | cabinet | 6-7 | 01-18; 01-13 | sure | d:20261114_014325 d:20261113_194606 d:20261114_014711 d:20261113_193629 d:20261113_193705 p:143021 p:144334 om:20261115_023314 | device of thread control; on sheet 8: terminal 24 to PLC IN-0 ("24BMR (7:06)")
K2 | auxiliary relay | feed-cut interlock (BLOKOVÁNÍ POSUV-ŘEZ) | POMOCNÁ RELÉ K2 – BLOKOVÁNÍ POSUV-ŘEZ | photo: F. Lütze relay as K1, changeover 11-12-14; coil voltage not read (24 V DC from the PLC, estimated); OM list 10.2: RE6-0011 | cabinet | 5-6 | 16; 17 | sure | d:20261113_234616 d:20261113_212623 d:20261113_212711 d:20261114_014325 d:20261113_194606 p:144324 p:144344 om:20261115_023314 d:20261114_014513 | device of thread control; on sheet 8: coil A1 from PLC OUT-0 ("A1K2 (5:16)")
KM8 | contactor | blower (air cushion) motor contactor | STYKAČ MOTORU DMYCHADLA KM8 | coil 50 Hz | cabinet | 4 | 12 | sure | d:20261113_232719 d:20261113_232949 d:20261113_233009 p:144247 | device of thread control (coil 4:12; poles 2:27-29 thread power); on sheet 8: auxiliary contact 13 from PLC OUT-9 ("13KM8 (5:15)")
XC2 | connector | table-cabinet interconnection | PROPOJENÍ STŮL–ROZVADĚČ | pins 1-9 used | cabinet | 5-6 | 11; 01-08 | [?] | d:20261113_234616 d:20261113_212623 d:20261113_212711 d:20261114_014325 d:20261113_194606 | device of thread control; on sheet 8: pins 2 and 3 to PLC IN-A and IN-9 ("2XC2 (5:11)", "3XC2 (5:12)")
"""

# sheet col | from dev:term | to dev:term | signal | wire | plc_address | connector:pin | evidence | sources (+ SH:power / SH:control) | note
WIRES = r"""
8 03-04 | X10:33 | TABLO:+24V | +24V | 33X10 |  |  | sure | d:20261114_015721 d:20261113_191800 p:144309 SH:control | TABLO terminal printed "+"; "(6:15)" under 33X10 leads to the +24V feed on sheet 6; photo 144309: field sleeve 33, inside fed by the bridge over 31-36
8 03-04 | X10:45 | TABLO:- | 0V | 45X10 |  |  | sure | d:20261114_015721 d:20261113_191800 p:144309 | TABLO terminal "−"; photo 144309: field sleeve 45; power_wires.csv has "X5 -> TABLO -" without 45X10 (see spec)
8 04 | X5: | X10:45 | 0V | 45X10 |  |  | sure | d:20261114_015721 d:20261113_191800 p:144309 | the arrow "X5 (2:02)" after terminal 45X10; photo 144309: inside marker 45X10 on a blue wire; X5 terminal not printed
8 03-04 | X10:PE | TABLO:PE | PE | ⏚X10 |  |  | sure | d:20261114_015721 d:20261113_191800 p:152038 | TABLO terminal printed ⏚, the X10 terminal "⏚X10" (circled earth); photo 152038: the TABLO's supply plug carries PE
8 03-04 | XC60:2 | XC70:3 | PLC-TABLO link (PROPOJENÍ PLC-TABLO) | 3XC70 |  | XC70:3 | sure | d:20261113_191800 d:20261114_015721 d:20261114_015117 | table "2 XC60 3XC70 8:03 8:04"; 2 and 3 crossed and 5 straight is the RS232 null-modem pattern (estimated, on-site items 4 and 5; no signal names printed)
8 03-04 | XC60:3 | XC70:2 | PLC-TABLO link (PROPOJENÍ PLC-TABLO) | 2XC70 |  | XC70:2 | sure | d:20261113_191800 d:20261114_015721 d:20261114_015117 p:142944 | table "3 XC60 2XC70"; at the PLC pin 3 is TxD by the count of the PLC port legends in photo 142944 (wide row 5-4-3-2-1 from the left; estimated, on-site item 4)
8 03-04 | XC60:5 | XC70:5 | PLC-TABLO link (PROPOJENÍ PLC-TABLO) | 5XC70 |  | XC70:5 | sure | d:20261113_191800 d:20261114_015721 d:20261114_015117 | table "5 XC60 5XC70"; 5 is GND on RS232 D-sub 9 (estimated, on-site items 4 and 5; see the XC60 row; no signal names printed)
8 03-04 | XC60:shell | XC70:shell | PLC-TABLO link cable shield (STÍNĚNÍ PŘIPOJENO NA KOVOVÝ PLÁŠŤ KONEKTORU) |  |  | XC70:shell | [?] | d:20261113_191800 | the table prints "shield connected to the metal shell of the connector" without saying which end; drawn here bonded at both shells [?] (on-site list)
8 01 | BMR1:24 | PLC:IN-0 | cut-done signal | 24BMR | IN-0 |  | sure | d:20261114_015117 d:20261113_191800 p:144328 SH:control | at the PLC "24BMR (7:06)"; photo marker IN-0 PLC
8 01 | X10:30 | PLC:IN-1 | S28 clamp plate | 30X10 | IN-1 |  | sure | d:20261114_015117 d:20261113_191800 p:144328 p:144309 SH:control | at the PLC "30X10 (5:14)"; photo marker IN-1 PLC; inside marker 30X10 at X10
8 01 | X10:29 | PLC:IN-2 | S30 clamp position (top per sheet 1) | 29X10 | IN-2 |  | sure | d:20261114_015117 d:20261113_191800 p:144328 p:144309 SH:control | at the PLC "29X10 (5:13)"; photo: a wire on IN-2, marker hidden; red ink right of the table at the rows IN-0 to IN-2: "короткий сто[п] – верх. пол. пр[есса]" (short st[op] – top position of the clamp [?])
8 02 | UZ1:K12 | PLC:IN-8 | drive (inverter UZ1) function signal (SIGNÁL FUNKCE POHONU) | K12UZ1 | IN-8 |  | sure | d:20261114_015117 d:20261113_191800 p:144328 p:144205 SH:power | at the PLC "K12UZ1 (2:25)"; photo: a wire on IN-8, marker hidden; red ink left of the table: "IN-8.-д. в конце хода пресса со вст." (IN-8 - sensor at the end of the clamp stroke [?]), another meaning than the print (on-site list)
8 02 | XC2:3 | PLC:IN-9 | S27 backgauge rear position | 3XC2 | IN-9 | XC2:3 | sure | d:20261114_015117 d:20261113_191800 p:144328 SH:control | at the PLC "3XC2 (5:12)"; photo marker IN-9 PLC
8 02 | XC2:2 | PLC:IN-A | S24 backgauge front position | 2XC2 | IN-A | XC2:2 | sure | d:20261114_015117 d:20261113_191800 p:144328 SH:control | at the PLC "2XC2 (5:11)"; photo marker IN-A PLC
8 04 | XC4:1 | PLC:IN-D | encoder index pulse (BR40 - INDEX (I)) | 1XC4 | IN-D | XC4:1 | sure | d:20261114_015117 d:20261113_191800 p:144328 | table "IN-D 1XC4 8:04"; photo: a thin core on IN-D
8 04 | XC4:2 | PLC:IN-E | encoder channel B (BR40 - KANÁL B) | 2XC4 | IN-E | XC4:2 | sure | d:20261114_015117 d:20261113_191800 p:144328 | table "IN-E 2XC4 8:04"; photo: a thin core on IN-E
8 04 | XC4:3 | PLC:IN-F | encoder channel A (BR40 - KANÁL A) | 3XC4 | IN-F | XC4:3 | sure | d:20261114_015117 d:20261113_191800 p:144328 | table "IN-F 3XC4 8:04"; photo marker IN-F PLC
8 04 | PLC:IN-GND | XC4:4 | encoder 0V (BR40 - GND) | 4XC4 | IN-GND | XC4:4 | sure | d:20261114_015117 d:20261113_191800 p:144328 | first GND of the input row; table "IN-GND 4XC4 8:04"; photo: a wire on it
8 03 | PLC:IN-GND | XC4:shell | encoder cable shield (BR40 - STÍNĚNÍ) | 7XC4 | IN-GND | XC4:shell | sure | d:20261114_015117 d:20261113_191800 p:144328 | second GND of the input row; sheet 8 bonds it to the shells of both halves of XC4; table "IN-GND 7XC4 8:03"; photo: a green-sleeved drain on the last GND
8 04 | PLC:+24V | XC4:5 | encoder supply +24V (BR40 - +24V) | 5XC4 | OUT +24V | XC4:5 | sure | d:20261114_015117 d:20261113_191800 p:144328 | leaves the junction over the two +24V terminals (second terminal) and runs round the left edge of the sheet into the XC4 harness; table "OUT +24V 5XC4 8:04"
8 04 | BR40:I | XC4:1 | encoder index pulse (BR40 - INDEX (I)) |  | IN-D | XC4:1 | sure | d:20261114_015117 d:20261113_191800 | machine side of XC4, no label printed; pin from the table (1XC4 = INDEX)
8 04 | BR40:B | XC4:2 | encoder channel B (BR40 - KANÁL B) |  | IN-E | XC4:2 | sure | d:20261114_015117 d:20261113_191800 | machine side of XC4, no label printed
8 04 | BR40:A | XC4:3 | encoder channel A (BR40 - KANÁL A) |  | IN-F | XC4:3 | sure | d:20261114_015117 d:20261113_191800 | machine side of XC4, no label printed
8 04 | XC4:4 | BR40:- | encoder 0V (BR40 - GND) |  | IN-GND | XC4:4 | sure | d:20261114_015117 d:20261113_191800 | machine side of XC4, no label printed
8 04 | XC4:5 | BR40:+ | encoder supply +24V (BR40 - +24V) |  | OUT +24V | XC4:5 | sure | d:20261114_015117 d:20261113_191800 | machine side of XC4, no label printed
8 01 | PLC:OUT-0 | K2:A1 | feed-cut interlock | A1K2 | OUT-0 |  | sure | d:20261114_015117 d:20261113_191800 p:144328 SH:control | at the PLC "A1K2 (5:16)"; photo marker OUT-0 PLC
8 02 | PLC:OUT-9 | KM8:13 | control of Y3 | 13KM8 | OUT-9 |  | [?] | d:20261114_015117 d:20261113_191800 p:144328 SH:control | at the PLC "13KM8 (5:15)"; photo: a blue wire on 9 (or 8), markers of the output row unreadable (on-site list)
8 02 | PLC:OUT-B | UZ1:E3 | backgauge feed forward (POSUV VPŘED) | E3UZ1 | OUT-B |  | [?] | d:20261114_015117 d:20261113_191800 p:144328 p:144205 SH:power | at the PLC "E3UZ1 (2:22)"; photo: a ferrule on B, A empty, markers unreadable; sheet 2 prints "(8:02-8:05)"
8 02 | PLC:OUT-C | UZ1:E4 | backgauge feed backward (POSUV VZAD) | E4UZ1 | OUT-C |  | [?] | d:20261114_015117 d:20261113_191800 p:144328 p:144205 SH:power | at the PLC "E4UZ1 (2:23)"; photo: a ferrule on C, markers unreadable
8 02 | PLC:OUT-D | UZ1:28 | inverter UZ1 blocking (enable input 28) (BLOKOVÁNÍ UZ1) | 28UZ1 | OUT-D |  | [?] | d:20261114_015117 d:20261113_191800 p:144328 p:144205 SH:power | at the PLC "28UZ1 (2:24)"; photo: a ferrule on D; at UZ1 the marker reads 20 or 28 (144205)
8 03 | X10:35 | PLC:+24V | PLC supply +24V | 35X10 | +24V PLC |  | sure | d:20261114_015117 d:20261113_191800 p:144328 p:144309 SH:control | at the first +24V terminal "35X10 (6:17)" (photo: "Outputs +24 VDC"); sheet 8 joins it to the second +24V ("P.L.C. Input +24 VDC") at a junction dot; photo 144309: inside marker 35X10
8 03 | UZ1:39 | PLC:GND | inverter digital ground (UZ1 - GND) | 39UZ1 | OUT-GND |  | sure | d:20261114_015117 d:20261113_191800 p:144328 p:144205 SH:power | first GND terminal "39UZ1 (2:21)"; terminal 39 is in the UZ1 photo 144205 (legend "39" under "E4" on the right-hand block, an orange ferrule, wire marker hidden); the far end of its wire is not seen (on-site item 13)
8 03 | X5: | PLC:GND | 0V | X5 | GND PLC |  | sure | d:20261114_015117 d:20261113_191800 p:144328 SH:power | second GND terminal "X5 (2:02)"; the table writes "X5 2:01" (2:01 is the PE column)
8 05 | UZ1:7 | XC50:6+9 | backgauge speed control (ŘÍZENÍ RYCHLOSTI SEDLA) | 7UZ1 |  | XC50:6+9 | sure | d:20261113_191800 d:20261114_015117 p:144205 p:142944 l:20261112_222008 SH:power | table "6+9 XC50 7UZ1 2:25"; pins 6 and 9 are the two GND of ANALOG OUTPUTS (port legend, photo 142944; estimated, on-site item 3; see the XC50 row); UZ1 7 is the inverter's ground (GND1; Lenze p.4-11)
8 05 | UZ1:8 | XC50:4 | backgauge speed control (ŘÍZENÍ RYCHLOSTI SEDLA) | 8UZ1 |  | XC50:4 | sure | d:20261113_191800 d:20261114_015117 p:144205 l:20261112_221856 l:20261112_222008 SH:power | table "4 XC50 8UZ1 2:26"; UZ1 8 is the analog setpoint input, 0-10 V, 0-5 V or 0/4-20 mA by the jumper on the control board and C034 (Lenze terminal table, terminal 8, pp.4-10 to 4-12: 221856, 222008); XC50 pin 4 = I1, current output 1 (estimated, on-site item 3; see the XC50 row); jumper and C034 on the on-site list
"""

# The sheet-8 paths table names some terminals in words; here are the names used above.
PATH_T = {('COMPACT PLC', '+24V (1st)'): ('PLC', '+24V'), ('COMPACT PLC', '+24V (2nd)'): ('PLC', '+24V'),
          ('COMPACT PLC', 'GND (1st)'): ('PLC', 'GND'), ('COMPACT PLC', 'GND (2nd)'): ('PLC', 'GND'),
          ('TABLO', '+'): ('TABLO', '+24V'), ('TABLO', '⏚'): ('TABLO', 'PE'), ('XC4', 'shells'): ('XC4', 'shell'),
          ('XC50', '6+9'): ('XC50', '6+9')}
# The PLC column of the PLC I/O table names supply and connector rows in words.
IO_T = {'IN-GND': ('PLC', 'IN-GND'), 'OUT +24V': ('PLC', '+24V'), 'OUT-GND': ('PLC', 'GND'),
        '+24V PLC': ('PLC', '+24V'), 'GND PLC': ('PLC', 'GND'), 'XC50 pins 6+9': ('XC50', '6+9'),
        'XC50 pin 4': ('XC50', '4'), 'XC60 pin 2': ('XC60', '2'), 'XC60 pin 3': ('XC60', '3'),
        'XC60 pin 5': ('XC60', '5')}
# Check 4 of the episode: the 14 addresses with a device, and the far end of their conductor(s) here.
ADDR14 = {'IN-0': {'BMR1'}, 'IN-1': {'X10'}, 'IN-2': {'X10'}, 'IN-8': {'UZ1'}, 'IN-9': {'XC2'},
          'IN-A': {'XC2'}, 'IN-D': {'XC4', 'BR40'}, 'IN-E': {'XC4', 'BR40'}, 'IN-F': {'XC4', 'BR40'},
          'OUT-0': {'K2'}, 'OUT-9': {'KM8'}, 'OUT-B': {'UZ1'}, 'OUT-C': {'UZ1'}, 'OUT-D': {'UZ1'}}
# Rows of the other threads that touch a device of sheet 8 but have no counterpart here, and why.
EXPLAINED = {('power', frozenset({('X5', ''), ('TABLO', '-')})):
             'sheet 8 (015721) routes the TABLO 0V through X10 45: "X5 -> X10 45" and "X10 45 -> TABLO -" here; '
             't5 keeps those two and drops this row'}
MARK = re.compile(r'^(sure|\[\?\]|W|estimated ±\S.*)$')


def sources(tokens):
    out = []
    for tok in tokens.split():
        if tok.startswith('SH:'):
            continue
        k, v = tok.split(':', 1)
        path = PFX[k].format(v)
        if path not in out:
            out.append(path)
    return '; '.join(out)


def end(s):
    dev, term = s.split(':', 1)
    return dev, term


def build():
    devs, wires = [], []
    for line in DEVICES.strip().splitlines():
        f = [x.strip() for x in line.split(' | ')]
        assert len(f) == 11, line
        devs.append(dict(zip(DEV_HDR, f[:9] + [sources(f[9]), f[10]])))
    for line in WIRES.strip().splitlines():
        f = [x.strip() for x in line.split(' | ')]
        assert len(f) == 10, line
        sheet, col = f[0].split()
        (fd, ft), (td, tt) = end(f[1]), end(f[2])
        conn, pin = end(f[6]) if f[6] else ('', '')
        sh = [t[3:] for t in f[8].split() if t.startswith('SH:')]
        note = f[9] + ''.join('; ' + SH[t] for t in sh)
        wires.append(dict(wire=f[4], from_device=fd, from_terminal=ft, to_device=td, to_terminal=tt,
                          signal=f[3], plc_address=f[5], connector=conn, pin=pin, cable='',
                          sheet=sheet, column=col, evidence=f[7], source_path=sources(f[8]), note=note,
                          _sh=sh))
    return devs, wires


def write(path, hdr, rows):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=hdr, lineterminator='\n', extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def rd(path):
    with open(path, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def ends(r):
    return frozenset({(r['from_device'], r['from_terminal']), (r['to_device'], r['to_terminal'])})


def wkey(r):
    a = (r['from_device'] + ' ' + r['from_terminal']).strip()
    b = (r['to_device'] + ' ' + r['to_terminal']).strip()
    return '%s -> %s' % (a, b)


# A note clause that names a port or pin function reads it from a legend or a standard, never from the print:
# it must carry its own mark. Clauses split at '; ' outside brackets; quoted print or photo text is left out.
PORT_WORDS = re.compile(r'TxD|RxD|RS232|null-modem|ANALOG|\bI1\b|\bIF1\b')
MARKED = re.compile(r'estimated|\[\?\]|\bW:|\(W\b|\bW\)')
PIN_CLAIM = re.compile(r'\b(pins?\s+\d+(\s*(and|,|\+)\s*\d+)*|\d+)\s+(is|are)\b[^;]*'
                       r'(\bGND|\bTxD|\bRxD|\bI1|\bU1|\bI2|\bU2|\+5V|\bcurrent output|\bvoltage output)')
MANUAL = re.compile(r'\bpp?\.\s?\d')    # a manual page number ("Lenze p.4-11", "pp.4-10") backs a pin claim


def clauses(note):
    note = re.sub(r'"[^"]*"', '""', note)
    out, depth, cur, i = [], 0, '', 0
    while i < len(note):
        c = note[i]
        depth += (c == '(') - (c == ')')
        if depth == 0 and note.startswith('; ', i):
            out.append(cur)
            cur, i = '', i + 2
            continue
        cur, i = cur + c, i + 1
    return out + [cur]


# Abbreviations of spec/plc_drive.md with the full name the spec gives in brackets at the first use (outside
# fenced code and quotations; an inline code span counts as text). Designations, type codes, units and the
# quoted German or Russian ink, glossed in brackets after the quote, are not in the list.
STALE = ['not saved']     # phrases that were true once and must not come back
SPEC_ABBR = [('PLC', 'programmable logic controller'), ('CSV', 'comma-separated values'),
             ('SVG', 'Scalable Vector Graphics'), ('UTF-8', 'Unicode Transformation Format, 8-bit'),
             ('I/O', 'inputs and outputs'), ('MD5', 'Message Digest 5'), ('VDC', 'volts direct current'),
             ('GND', 'ground'), ('PE', 'protective earth'), ('W', 'web source, weaker evidence'),
             ('B&R', 'Bernecker + Rainer'), ('D-sub', 'D-subminiature connector'), ('AT', 'amperes, time-lag'),
             ('IF1', 'interface 1'), ('RS232', 'Recommended Standard 232'), ('RS485', 'Recommended Standard 485'),
             ('CAN', 'Controller Area Network'), ('OM', 'operating manual MS 80/115 PS, DS'),
             ('NO', 'normally open'), ('NC', 'normally closed'), ('I1', 'current output 1'), ('CW', 'clockwise'),
             ('CCW', 'counter-clockwise'), ('QSP', 'quick stop'), ('AC', 'alternating current'),
             ('DC', 'direct current'), ('RFR', 'Reglerfreigabe'), ('STP', 'stop'), ('LU', 'undervoltage'),
             ('NPN', 'negative-positive-negative transistor'), ('TxD', 'transmit data'), ('RxD', 'receive data'),
             ('ESC', 'escape'), ('DEL', 'delete')]


def spec_abbr(text):
    """(abbreviations met, failures): each abbreviation's first use must be followed by ' (<full name>'."""
    body = re.sub(r'```.*?```', ' ', text, flags=re.S).replace('`', '')
    pats = [(a, e, re.compile(r'(?<![\w&/.\-])' + re.escape(a) + r'(?![\w&/\-])')) for a, e in SPEC_ABBR]
    met, fails = set(), []
    for line in body.split('\n'):
        quoted = [m.span() for m in re.finditer(r'"[^"]*"', line)]
        for a, e, rx in pats:
            if a in met:
                continue
            for m in rx.finditer(line):
                met.add(a)
                rest = line[m.end():]
                if any(q0 <= m.start() < q1 for q0, q1 in quoted):
                    # a first use inside a quotation: the gloss after it in the same line gives the full name
                    if not (rest.startswith(' (%s' % e) or ('%s (%s' % (a, e)) in rest):
                        fails.append('spec abbreviation %s: first use inside a quotation, and no "%s (%s" after it in '
                                     'that line: ...%s' % (a, a, e, line[m.start():m.end() + 30]))
                elif not rest.startswith(' (%s' % e):
                    fails.append('spec abbreviation %s: first use not followed by "(%s": ...%s' % (a, e, line[m.start():m.end() + 30]))
                break
    return met, fails


def main():
    devs, wires = build()
    NET.mkdir(exist_ok=True)
    write(NET / 'plc_drive_devices.csv', DEV_HDR, devs)
    write(NET / 'plc_drive_wires.csv', WIRE_HDR, wires)
    bad, info = [], []
    # headers and encoding
    for name, hdr in (('plc_drive_devices.csv', DEV_HDR), ('plc_drive_wires.csv', WIRE_HDR)):
        raw = (NET / name).read_bytes()
        if raw.startswith(b'\xef\xbb\xbf'):
            bad.append(name + ': byte order mark')
        if raw.decode('utf-8').split('\n', 1)[0] != ','.join(hdr):
            bad.append(name + ': header differs')
    # one row per designation
    names = [d['designation'] for d in devs]
    for n in sorted({n for n in names if names.count(n) > 1}):
        bad.append('designation twice: ' + n)
    dev = {d['designation']: d for d in devs}
    # marks, sources, places
    have_src = (P / 'preparatory_data_analysis').is_dir()
    for kind, rows in (('device', devs), ('wire', wires)):
        for r in rows:
            k = r['designation'] if kind == 'device' else wkey(r)
            if not MARK.match(r['evidence']):
                bad.append('%s %s: mark %r' % (kind, k, r['evidence']))
            for p in r['source_path'].split('; '):
                if not p or p.startswith('/') or ':' in p or 'Users' in p:
                    bad.append('%s %s: source path %r not relative' % (kind, k, p))
                elif have_src and not (P / p).exists():
                    bad.append('%s %s: source missing %s' % (kind, k, p))
            if kind == 'device' and r['place'] not in ('cabinet', 'console', 'machine'):
                bad.append('device %s: place %r' % (k, r['place']))
    if not have_src:
        info.append('INFO source paths not checked: preparatory_data_analysis/ absent')
    # both ends are devices; every device has a wire
    used = set()
    for r in wires:
        for d in (r['from_device'], r['to_device']):
            used.add(d)
            if d not in dev:
                bad.append('dangling end %s in %s' % (d, wkey(r)))
    for n in names:
        if n not in used:
            bad.append('device without a wire: ' + n)
    # the 14 addresses: on the PLC, one signal each, far end as read
    for a, far in ADDR14.items():
        rows = [r for r in wires if r['plc_address'] == a]
        sig = {r['signal'] for r in rows}
        on_plc = [r for r in rows if ('PLC', a) in ends(r)]
        got = {d for r in rows for d, _ in ends(r)} - {'PLC'}
        if len(on_plc) != 1 or len(sig) != 1 or got != far:
            bad.append('address %s: %d rows on the PLC, signals %s, far ends %s' % (a, len(on_plc), sorted(sig), sorted(got)))
    for a in sorted({r['plc_address'] for r in wires if re.match(r'(IN|OUT)-[0-9A-F]$', r['plc_address'])} - set(ADDR14)):
        bad.append('address not in the list of 14: ' + a)
    # sheet-8 paths table and PLC I/O table
    if TAB.is_dir():
        paths = rd(TAB / '12_568_sheet8_paths.csv')
        mapped = 0
        for i, p in enumerate(paths, 2):
            d, t = PATH_T.get((p['device'], p['terminal']), (p['device'].replace('COMPACT PLC', 'PLC'), p['terminal']))
            if p['wire']:
                hit = [r for r in wires if r['wire'] == p['wire'] and (d, t) in ends(r)]
                if not hit:     # a field device behind a connector: labelled row + unlabelled row on one pin
                    lab = [r for r in wires if r['wire'] == p['wire']]
                    far = [r for r in wires if (d, t) in ends(r)]
                    hit = [a for a in lab for b in far if ends(a) & ends(b)]
                if not hit:
                    bad.append('paths line %d (%s %s %s) not found' % (i, p['device'], p['terminal'], p['wire']))
                    continue
                cols = {r['column'] for r in hit}
                if p['column'] not in cols:
                    info.append('INFO paths line %d %s: column %s there, %s here' % (i, p['wire'], p['column'], '/'.join(sorted(cols))))
            elif p['terminal'] == 'XC70':
                if 'XC70' not in dev:
                    bad.append('paths line %d: XC70 missing' % i)
                elif p['column'] != dev['XC70']['column']:
                    info.append('INFO paths line %d XC70: column %s there, %s here (see the XC70 row note)'
                                % (i, p['column'], dev['XC70']['column']))
            elif d not in dev:
                bad.append('paths line %d: device %s missing' % (i, d))
            mapped += 1
        io = rd(TAB / '12_568_plc_io.csv')
        io_ok = 0
        for i, q in enumerate(io, 2):
            a = q['plc_address']
            if q['wire_SMER']:
                d, t = IO_T.get(a, ('PLC', a))
                hit = [r for r in wires if r['wire'] == q['wire_SMER'] and (d, t) in ends(r)]
                if not hit:
                    bad.append('PLC I/O line %d (%s %s) not found' % (i, a, q['wire_SMER']))
                    continue
            else:
                hit = [r for r in wires if ('PLC', a) in ends(r)]
                if hit:
                    bad.append('PLC I/O line %d: %s unused on sheet 8 but wired here' % (i, a))
                    continue
            io_ok += 1
        info.append('paths table: %d/%d rows mapped; PLC I/O table: %d/%d rows agree' % (mapped, len(paths), io_ok, len(io)))
    else:
        info.append('INFO paths and PLC I/O tables not checked: static_dynamic_memory/ absent')
    # join with the other threads
    shared = 0
    for th, fname in (('power', 'power'), ('control', 'control')):
        fw, fd = NET / (fname + '_wires.csv'), NET / (fname + '_devices.csv')
        if not fw.exists() or not fd.exists():
            info.append('INFO join with %s not checked: %s absent' % (th, fw.name))
            continue
        theirs = rd(fw)
        idx = {}
        for i, r in enumerate(theirs, 2):
            idx.setdefault(ends(r), []).append((i, r))
        for r in wires:
            hits = idx.get(ends(r), [])
            if th in r['_sh'] and not hits:
                bad.append('JOIN %s: tagged %s but no row there' % (wkey(r), fw.name))
            if hits and th not in r['_sh']:
                bad.append('JOIN %s: also %s line %d, not tagged' % (wkey(r), fw.name, hits[0][0]))
            for i, o in hits:
                shared += 1
                same_dir = (o['from_device'], o['from_terminal']) == (r['from_device'], r['from_terminal'])
                diff = ['%s %r here, %r there' % (k, r[k], o[k]) for k in
                        ('wire', 'signal', 'plc_address', 'connector', 'pin', 'evidence') if r[k] != o[k]]
                if not same_dir:
                    bad.append('JOIN %s: direction differs from %s line %d' % (wkey(r), fw.name, i))
                info.append('SHARED %s = %s line %d%s' % (wkey(r), fw.name, i, ('; differs: ' + '; '.join(diff)) if diff else ''))
        mine = {ends(r) for r in wires}
        for i, o in enumerate(theirs, 2):
            touch = {o['from_device'], o['to_device']} & set(OWN)
            if touch and ends(o) not in mine:
                why = EXPLAINED.get((th, ends(o)))
                if why:
                    info.append('UNMATCHED %s line %d %s: %s' % (fw.name, i, wkey(o), why))
                else:
                    bad.append('UNMATCHED %s line %d %s: touches %s, no row here' % (fw.name, i, wkey(o), ','.join(sorted(touch))))
        for o in rd(fd):
            n = o['designation']
            if n not in dev:
                continue
            mine_d = dev[n]
            fields = ('kind', 'function_en', 'term_cz_ru', 'type_rating', 'place', 'sheet', 'column', 'evidence', 'source_path')
            diff = [k for k in fields if mine_d[k] != o[k]]
            if n in OWN:
                if diff:
                    info.append('DEVICE %s (sheet 8, this thread) differs from %s in: %s' % (n, fd.name, ', '.join(diff)))
            elif ('device of thread ' + th) in mine_d['note'] and diff:
                bad.append('DEVICE %s copied from %s differs in: %s' % (n, fd.name, ', '.join(diff)))
    # on-site keys in the spec; abbreviations of the spec at their first use
    if SPEC.exists():
        text = SPEC.read_text(encoding='utf-8')
        keys_q = ['`%s`' % r['designation'] for r in devs if r['evidence'] != 'sure']
        keys_q += ['`%s`' % wkey(r) for r in wires if r['evidence'] != 'sure']
        sec11 = text.split('\n## 11.', 1)[-1].split('\n## 12.', 1)[0] if '\n## 11.' in text else ''
        rows11 = [ln for ln in sec11.splitlines() if ln.startswith('| ')]   # the rows of the on-site list only
        found = [k for k in keys_q if any(k in ln for ln in rows11)]
        for k in keys_q:
            if k not in found:
                bad.append('on-site key missing in the rows of spec section 11: %s' % k)
        info.append('INFO on-site keys of the rows not sure in spec/plc_drive.md: %d of %d'
                    % (len(found), len(keys_q)))
        for ph in STALE:
            if ph in text:
                bad.append('stale phrase %r in spec/plc_drive.md' % ph)
        met, abad = spec_abbr(text)
        bad.extend(abad)
        info.append('INFO abbreviations in spec/plc_drive.md: %d of %d in the list used, %d without their full name '
                    'at the first use' % (len(met), len(SPEC_ABBR), len(abad)))
    else:
        info.append('INFO on-site keys not checked: spec/plc_drive.md absent')
    for r in devs + wires:
        for ph in STALE:
            if any(ph in str(v) for v in r.values()):
                bad.append('stale phrase %r in row %s' % (ph, r.get('designation') or wkey(r)))
        cited = set(re.findall(r'(?<![\d.])(\d{6})(?!\d)', re.sub(r'Nr\. \d+', '', r['note'])))
        have = r['source_path']
        for st in sorted(cited):
            if st + '.jpg' not in have:
                bad.append('row %s: its note cites photo %s, its source_path does not' % (r.get('designation') or wkey(r), st))
        for fld in ('note', 'type_rating', 'signal', 'function_en'):
            for c in clauses(r.get(fld) or ''):
                if MARKED.search(c):
                    continue
                if PORT_WORDS.search(c) or (PIN_CLAIM.search(c) and not MANUAL.search(c)):
                    bad.append('row %s %s: a port or pin reading without its own mark: %s'
                               % (r.get('designation') or wkey(r), fld, c[:90]))
    marked = sum(1 for r in wires if SH['power'] in r['note'] or SH['control'] in r['note'])
    if (NET / 'power_wires.csv').exists() and (NET / 'control_wires.csv').exists() and marked != shared:
        bad.append('%d rows carry the shared-conductor note, but the join found %d shared conductors' % (marked, shared))
    q = sum(1 for r in devs + wires if r['evidence'] != 'sure')
    print('plc_drive: %d devices, %d wires, %d rows not sure, %d shared-conductor matches' % (len(devs), len(wires), q, shared))
    for line in info:
        print(line)
    for line in bad:
        print('FAIL ' + line)
    print('result: ' + ('FAIL' if bad else 'PASS'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
