#!/usr/bin/env python3
"""Netlist of set 568-70.9001 sheets 4-7 (thread t2, control).

Run:     python -B stage_2_electronics/schemes_2d/control_netlist.py
Writes:  ../netlist/control_devices.csv, ../netlist/control_wires.csv (UTF-8, no BOM)
Data:    the DEVICES and WIRES tables below, transcribed from the photographed paper
         sheets 4-7 (clean copies 20261113_232719, 20261113_234616, 20261114_014325,
         20261114_014711; annotated copies 20261113_194230, 212623, 212711, 194606,
         193629) and checked against the cabinet photos (20261102_*).
Rules:   photos rule what is wired; else the 1998 set. Print values that a photo or a
         hand correction overrides are quoted in the note. Red/blue ink is quoted with
         its place and colour, never taken as print.
Checks (exit 1 on a failure):
  headers; one row per designation; evidence marks; source paths exist (skipped when
  preparatory_data_analysis/ is absent); both ends of every wire are devices of this
  file; PLC addresses; agreement with ../netlist/power_*.csv (thread power) on shared
  designations and shared conductors; every row of the four 568 paths tables mapped
  to wire rows (skipped when static_dynamic_memory/ is absent); every [?] or
  estimated row keyed in the on-site list of ../spec/control.md (skipped while absent).
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
D = 'preparatory_data_analysis/maxima_documents/adast_guillotine_wiring_and_plc_diagrams/'
PH = 'preparatory_data_analysis/maxima_photos/20261102_'
OM = 'preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/'
SRC = {4: [D + '20261113_232719.jpg', D + '20261113_232949.jpg', D + '20261113_233009.jpg'],
       5: [D + '20261113_234616.jpg', D + '20261113_212623.jpg', D + '20261113_212711.jpg'],
       6: [D + '20261114_014325.jpg', D + '20261113_194606.jpg'],
       7: [D + '20261114_014711.jpg', D + '20261113_193629.jpg', D + '20261113_193705.jpg'],
       2: [D + '20261113_231128.jpg'], 3: [D + '20261113_232117.jpg'], 8: [D + '20261114_015117.jpg']}
SH = 'same conductor as a row of power_wires.csv (thread power): keep one when merging'
DEV_HDR = 'designation,kind,function_en,term_cz_ru,type_rating,place,sheet,column,evidence,source_path,note'.split(',')
WIRE_HDR = ('wire,from_device,from_terminal,to_device,to_terminal,signal,plc_address,connector,pin,'
            'cable,sheet,column,evidence,source_path,note').split(',')

# designation | kind | function_en | term_cz_ru | type_rating | place | sheet | column | evidence | extra sources | note
DEVICES = r"""
UG50 | power-supply board | rectified and AC control supplies +27V +24V +33V ~24V ~48V | PLOŠNÝ SPOJ SE ZDROJI UG50 | terminals 1-32 | cabinet | 3 | 03-04 | sure | 144227 | device of thread power; on sheets 4-7 only its outputs 1, 2, 5, 6, 10, 12, 13, 14, 18 as arrows "nUG50 (3:04)"; photo markers 1 2 5 6 10 12 13 14 18 UG50 (144227)
QF1 | motor circuit breaker 3-pole + aux 43-44 | M1 protection; aux 43-44 in the control chain | - | aux contact 43-44 NO used at 4:10 | cabinet | 2 | 07-10 | sure | 144259 | device of thread power; aux 43-44 feeds the sheet-4 chain; photo markers 43QF1, 44QF1 x2 (144259)
X10 | terminal strip | terminal strip in the cabinet (1-6 to M1) | SVORKOVNICE V ROZVADĚČI | 45 terminals + 3 PE (photo) | cabinet | 2 | 04-09 | sure | 144309 144314 | device of thread power; terminals 7-44 and PE used on sheets 4-7; photo 144314 (PE, terminals 1 to about 38): inside wires on 8 9 12 14 17 18-24 27-32 34-38, none on 7 10 11 13 15 16 25 26 33, copper bridges 7-8, 9-10, 11-13, 16-17, 26-27, 31-36, yellow core sleeves carry the terminal numbers; photo 144309 (terminals 17-45, PE): inside wires on 17-24 27-32 34-41 43 44, none on 25 26 33 42, copper bridges 31-36, 41-42; bridge positions ±1
X5 | terminal strip | working-earth strip: 0 V of all control supplies, bonded to PE | SVORKOVNICE PRAC. ZEMĚ | terminal numbers not printed | cabinet | 2 | 02 | sure | 144214 | device of thread power; every coil return of sheets 4-5 ends at "(2:02) X5"; terminal field left empty (not printed)
PE | earthing terminal strip | earthing (protective earth) strip: XC3 T1 X10 X11 XC7 UZ1 | UZEMŇOVACÍ SVORKOVNICE (earth symbol) | earth symbol "(2:01)" | cabinet | 2 | 01-02 | sure |  | device of thread power; Y01 and Y11 reach it through X10 PE (5:01, 5:06)
S2 | selector | work lighting / cut-line indication selector | PŘEPÍNAČ OSVĚTLENÍ – NÁZNAK ŘEZU; RU выключатель освещения и назначения реза | contacts 3A-4A (work light), 4B-3B (cut line); OM list 10.1: BACO head V22MA03, adapter 233E, block 23E10 | cabinet | 4 | 02-05 | sure | 144344 om:20261115_022802 om:20261115_023023 | pictogram work light <- 0 -> cut-line light; OM: left E1+E2, middle off, right E3+E4; photo 144344: body on the cabinet switch plate, red-brown block seen from inside, moulded "Ba..." [?], marker read "3BS2" [?]
E1 | lamp | work-surface lighting lamp | OSVĚTLENÍ PRACOVNÍ PLOCHY E1, E2 | ~24 V AC | machine | 4 | 01 | sure |  | place: field side of X10 (print); end names 1 (feed, from X10) and 2 (return) are ours, not printed
E2 | lamp | work-surface lighting lamp | OSVĚTLENÍ PRACOVNÍ PLOCHY E1, E2 | ~24 V AC | machine | 4 | 02 | sure |  | place: field side of X10 (print); end names 1/2 ours
E3 | lamp | cut-line indication lamp | NÁZNAK ŘEZU E3, E4 | ~24 V AC | machine | 4 | 03-05 | sure |  | place: field side of X10 (print); end names 1/2 ours
E4 | lamp | cut-line indication lamp | NÁZNAK ŘEZU E3, E4 | ~24 V AC | machine | 4 | 03-05 | sure |  | place: field side of X10 (print); end names 1/2 ours
BMR1 | cut-control module (board) | cut-control module: two-hand start, knife lock, clutch contactors, cut-done signal | MODUL ŘÍZENÍ ŘEZU (PŘIPOJENÍ MODULU ŘÍZENÍ ŘEZU BMR1); RU релейный модуль управления реза | one relay board, plate "BMR2" (photo 143021), maker not printed or seen; terminals 1-29, 0V (-), +24V (+); OM list 10.2 "BMR.." 900 010 0714 | cabinet | 6-7 | 01-18; 01-13 | sure | 143021 144334 om:20261115_023314 | inputs 1-18 on sheet 6, outputs 19-29 and supply on sheet 7; photo 143021/144334: every terminal 1-29, -, + carries a wire, red (AC) wires on 19 20 27 28 29, markers 1-4, 6-12, 14-28 BMR1 read; board about 29 x 11 cm (estimated ±10 %); internal circuit not printed
S5 | limit switch | belt-pulley cover interlock | KONCOVÝ SPÍNAČ – BLOKOVÁNÍ KRYTU ŘEMENICE; red ink on sheet 1 "у маховика" (at the flywheel) | NC 21-22 (4:10), NO 13-14 (5:09) | machine | 4-5 | 10; 09 | sure |  | NC 21-22 in the KM1A/KM1B chain; NO 13-14 in the knife-change branch of Y10; fault: M1 will not start (OM 5.2.3)
S1 | emergency stop | emergency stop switch (only MS 115 PS, DS) | SPÍNAČ NOUZOVÉHO ZASTAVENÍ; "POUZE MS115" printed at 4:10 | NC 21-22; OM list 10.1: BACO V22E01 + 231E + 23E01 | console | 4 | 10 | sure | om:20261115_022802 | opens the KM1A/KM1B chain: M1, UZ1, M3 stop; the UG50 supplies, BMR1 and the PLC stay live
KM1A | contactor | main contactor (in series with KM1B) | HLAVNÍ STYKAČE KM1A, KM1B | coil 24 V AC 50 Hz | cabinet | 4 | 09 | sure | 144255 144304 | coil 4:09, aux 13-14 in the self-hold (4:10), poles 2:04 (thread power); photo 144255: markers 13KM1A x2 (144304: one clear, the second partly hidden)
KM1B | contactor | main contactor (in series with KM1A) | HLAVNÍ STYKAČE KM1A, KM1B | coil 24 V AC 50 Hz | cabinet | 4 | 11 | sure | 144255 144304 | coil 4:11, aux 14-13 (4:10), poles 2:06 (thread power); photo marker 13KM1B (on 144255 and on 144304)
Q2 | rotary cam switch | M1 run switch; contacts 1-2..7-8 closed in 0, 9-10 closed in 1 | - | photo: 16 A 660 V AC, IEC 947-3 | cabinet | 4-6 | 08; 17; 16; 09; 14-15 | sure | 144344 | contact table 2:01-02 (thread power); contacts drawn open as printed: 1-2 (4:08), 3-4 (4:17), 9-10 (4:16), 5-6 (5:09), 7-8 (6:14-15); photo 144344 cam label, markers 2Q2 6Q2 8Q2 9Q2 10Q2 (Q read as 0)
RC1 | RC suppressor | coil suppressor across KM1A and KM1B | - | 2µ2 + 220R (sheet-box 4) | cabinet | 4 | 10 | sure | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 4: "RC... 2µ2 + 220R" (213823, 213049); across both coils (A1s joined, A2s joined); end names 1 (A1 side), 2 (A2 side) ours
S4 | switch | air-cushion blower motor switch (energises KM8) | SPÍNAČ MOTORU VZDUCHOVÉHO POLŠTÁŘE | contact 3-4 (latching symbol); OM list 10.1: BACO head V22KA03, adapter 231E, block 23E10 | cabinet | 4 | 12 | sure | 144344 om:20261115_022802 om:20261115_023023 | photo 144344: body on the cabinet switch plate, red-brown block seen from inside; marker 3S4 (x2 [?])
KM8 | contactor | blower (air cushion) motor contactor | STYKAČ MOTORU DMYCHADLA KM8 | coil 50 Hz | cabinet | 4 | 12 | sure | 144247 | coil 4:12; aux 13-14 at 5:15 (PLC OUT-9 to K1); poles 2:27-29 (thread power); photo markers A1KM8 (RC), 13KM8, 14KM8
RC8 | RC suppressor | coil suppressor across KM8 | - | 2µ2 + 220R (sheet-box 4) | cabinet | 4 | 12 | [?] | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 4: "RC... 2µ2 + 220R" (213823, 213049); label above KM8 read RC8, could read RC6 (232949): on-site list
KM2 | contactor | M1 line contactor (U2 V2 W2) | STYKAČE MOTORU PRO POHON NOŽE A HYDRAULIKY KM2, KM3, KM4 | coil 50 Hz | cabinet | 4 | 13 | sure | 144247 | coil 4:13; contacts 14-13 (self-hold 4:13), 62-61 (KT1 9-10, 4:16); photo markers 13KM2 x2, 62KM2
RC2 | RC suppressor | coil suppressor across KM2 | - | 2µ2 + 220R (sheet-box 4) | cabinet | 4 | 13 | sure | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 4: "RC... 2µ2 + 220R" (213823, 213049); end names 1/2 ours
KM3 | contactor | M1 delta contactor (V1 W1 U1) | STYKAČE MOTORU PRO POHON NOŽE A HYDRAULIKY KM2, KM3, KM4 | coil 50 Hz | cabinet | 4 | 14 | sure | 144247 | coil 4:14; contacts 62-61 (4:15), 13-14 (4:17), 53-54 (4:19); photo markers 53KM3, 54KM3 x2, 61KM3, 62KM3, 13KM3 x2, 14KM3 x2
RC3 | RC suppressor | coil suppressor across KM3 | - | 2µ2 + 220R (sheet-box 4) | cabinet | 4 | 14 | sure | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 4: "RC... 2µ2 + 220R" (213823, 213049); end names 1/2 ours
KM4 | contactor | M1 star contactor (shorts X10 4-5-6) | STYKAČE MOTORU PRO POHON NOŽE A HYDRAULIKY KM2, KM3, KM4 | coil 50 Hz | cabinet | 4 | 15 | sure | 144247 | coil 4:15; contacts 5-6 (4:13), 21-22 NC (4:14); photo markers 5KM4 x2, 6KM4, 21KM4, 22KM4
RC4 | RC suppressor | coil suppressor across KM4 | - | 2µ2 + 220R (sheet-box 4) | cabinet | 4 | 15 | sure | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 4: "RC... 2µ2 + 220R" (213823, 213049); end names 1/2 ours
KT1 | time relay | M1 star-delta timer (run-up of M1) | no own zone title (zone 13); RU временное реле разгона двигателя M1 | OM list 10.2: TX 320 ZN, 24 V DC, 1-10 s (p.49); photo: letters ZN, dial 4-10, range x, s/min, setting not read; terminal face 4(15) 6(16) 5(18), 12(25) 14(26) 13(28), 1(A1) 2(A2) 3(A3), 10(B1) 9(B2) | cabinet | 4 | 16 | sure | 144259 om:20261115_023314 om:20261115_023222 | NO/NC not readable on the print; by the maker's face legend (photo 144259, IEC numbering 15-16-18, 25-26-28): 4-5 = 15-18 NO (KM4 star line, 4:15), 12-14 = 25-26 NC (KM3 delta line, 4:14), which fits the star-delta sequence (B1-B2 = 10-9 bridged by KM2 62-61); pencil "ZN" under its contact list on the clean sheet 4 (233009); on-site: confirm the contact types, read the dial setting
KM6 | contactor | cut clutch contactor | STYKAČE SPOJKY ŘEZU KM6, KM7 | coil 50 Hz | cabinet | 4 | 17 | sure | 144247 144251 | coil 4:17 (sheet 5 prints "KM6 (4:16)"); contacts 1-2 (4:20), 3-4 (5:07), 5-6 (5:10), 61-62 (6:04); photo 144247: type label "EP1C093" beside KM6, front block, markers 1KM6 3KM6 5KM6 2KM6 4KM6; photo 144251: 61KM6, 62KM6
RC6 | RC suppressor | coil suppressor across KM6 | - | 2µ2 + 220R (sheet-box 4) | cabinet | 4 | 17 | sure | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 4: "RC... 2µ2 + 220R" (213823, 213049); end names 1/2 ours
KM7 | contactor | cut clutch contactor | STYKAČE SPOJKY ŘEZU KM6, KM7 | coil 50 Hz | cabinet | 4 | 19 | sure | 144205 144251 | coil 4:19; contacts 6-5 (5:10), feedback NC printed 62-61 (6:04); photo 144251: built-in auxiliary 01 (21-22 NC) only, markers A1KM7 (RC), 5KM7, 21KM7; photo 144205: 22KM7: the feedback is wired on 21-22 (see the wire rows)
RC7 | RC suppressor | coil suppressor across KM7 | - | 2µ2 + 220R (sheet-box 4) | cabinet | 4 | 19 | sure | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 4: "RC... 2µ2 + 220R" (213823, 213049); end names 1/2 ours
KT2 | time relay | cut delay after clamping (delays KM7) | ČASOVÉ RELÉ ZPOŽDĚNÍ ŘEZU ZA LISOVÁNÍM KT2; RU временное реле опоздания реза за прижимом | OM list 10.2: TX 320 ZR, 24 V DC, 0-2,5 s (p.49); OM p.7 and p.9: 0-3 s (conflict); photo: letters ZR, LED U, dial 4-10, s/min, setting not read | cabinet | 4 | 20 | sure | 144259 om:20261115_023314 om:20261114_215113 | coil 1-2 from 6UG50 +24V through KM6 1-2; contact 4-5 in KM7's coil line (4:19); pencil "ZR" above its contact list (233009); fault "top sheets pulled out": lengthen it (OM 5.1.5 в)
V20 | diode | free-wheel diode across the KT2 coil | - | 1N 4002 (sheet-box 4) | cabinet | 4 | 20 | sure | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 4: "V20 1N 4002" (213823, 213049); end names 1 (KT2 1 side), 2 (KT2 2 side) ours; polarity not read
Y01 | electromagnet | knife-lock magnet: withdraws the locking pin | ELEKTROMAGNET ZAJIŠTĚNÍ NOŽE Y01; RU электромагнит фиксации ножа; blue ink on sheet 5 "Блокир. шестерни" (gear blocking) | +27 V DC switched by BMR1 21-22; OM list 10.1: EVS 4217-PO | machine | 5 | 02 | sure | om:20261115_023023 | terminals +, - and PE as printed; diode V01 across; red ink on sheet 7 at BMR1 22 "Y01 блокир. шестерни"
V01 | diode | diode across Y01 | - | 1N 4002 (sheet-box 5) | machine | 5 | 02 | sure | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 5: "V01, V14 1N 4002" (213823, 213049); sheet 5 prints "V01" at 5:02 (234616); drawn across the coil on the field side of X10 (at the magnet); end names 1 (+ side), 2 (- side) ours; power_devices.csv leaves place empty
Y14 | electromagnet | clamp brake: released while energized | BRZDA LISOVADLA Y14; RU тормоз прижима | "+14V" printed on its line: 2UG50 +27V through R14 11R/25W and BMR1 25-26; OM list 10.1: 556-15.0000 (MS 115) | machine | 5 | 04 | sure | om:20261115_023023 | no PE drawn; diode V14 across; red ink on sheet 7 at BMR1 26 "Y14 гидро распр. магнит." (hydraulic distributor magnet) and on sheet 5 blue "гидрораспр." under Y11
V14 | diode | diode across Y14 | - | 1N 4002 (sheet-box 5) | machine | 5 | 04 | sure | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 5: "V01, V14 1N 4002" (213823, 213049); the V14 on board UG50 is UG50/V14 (thread power); drawn on the field side at the magnet; end names 1 (+), 2 (-) ours
Y11 | electromagnet | hydraulics magnet (clamping) | ELEKTROMAGNETY HYDRAULIKY Y11; RU электромагнит гидравлики | ~48 V AC from 18UG50 through KM6 3-4; OM list 10.1: EVJ 4132 | machine | 5 | 07 | sure | om:20261115_023023 | PE through X10 PE (5:06); RC11 across; end names 1 (from 22X10), 2 (to 23X10) ours
RC11 | RC suppressor | RC suppressor across Y11 | - | 2µ2 + 220R (sheet-box 5) | machine | 5 | 07 | sure | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 5: "RC11 2µ2 + 220R" (213823, 213049); drawn on the field side at the magnet; end names 1/2 ours
Y10 | electromagnet clutch | cut clutch (with brake) | SPOJKA ŘEZU Y10; RU электромагнитная муфта реза; blue ink on sheet 5 "сцепление" | +33 V DC from 10UG50 through KM6 5-6 and KM7 6-5; OM list 10.1: 591-04.0000 (MS 115) | machine | 5 | 10 | sure | om:20261115_023023 | V10 and R10 in series across the coil (crop s5_ann_212623_cols09-10_Y10_bottom; the paths table says "in parallel"); no PE drawn
V10 | Zener diodes | Zener diode pair across Y10 (in series with R10) | - | 2x KZ 751 (sheet-box 5) | machine | 5 | 10 | sure | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 5: "V10 2x KZ 751" (213823, 213049); two Zener diodes back to back; end names 1 (+ side), 2 (R10 side) ours
R10 | resistor | resistor across Y10 (in series with V10) | - | 100R/6W (sheet-box 5) | machine | 5 | 10 | sure | d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 5: "R10 100R/6W" (213823, 213049); end names 1 (V10 side), 2 (- side) ours
S19 | switch | cut clutch switch (for knife change) | SPÍNAČ SPOJKY ŘEZU (PRO VÝMĚNU NOŽE); red ink on sheet 1 "у маховика" | NO 13-14 (5:09), NC 21-22 (6:18); diamond actuator symbol | machine | 5-6 | 09; 18 | sure |  | NO in the knife-change branch of Y10; NC to BMR1 18 via 44X10 / 36X10
S24 | limit switch | saddle position limit switch, front position | KONCOVÝ SPÍNAČ POLOHY SEDLA – PŘEDNÍ POLOHA | NC 21-22, roller lever; OM list 10.1: Telemecanique XCK-A 102 | machine | 5 | 11 | sure | om:20261115_023023 | to PLC IN-A through XC2 2
S27 | reference switch | saddle position reference switch, rear position | REFERENČNÍ SPÍNAČ POLOHY SEDLA – ZADNÍ POLOHA | NC 21-22, roller lever; OM list 10.1: Telemecanique XCK-A 102 | machine | 5 | 12 | sure | om:20261115_023023 | to PLC IN-9 through XC2 3
S30 | sensor | clamp position sensor (top position) | SNÍMAČ POLOHY LISOVADLA (HORNÍ POLOHA); sheet 6: SPÍNAČ POLOHY LISOVADLA | NO 13-14 (5:13), NC 21-22 (6:16); roller lever | machine | 5-6 | 13; 16 | sure |  | NO to PLC IN-2 (29X10); NC to BMR1 16 (43X10 / 34X10); fault: no backgauge feed (OM 5.2.4)
S28 | sensor | clamp plate sensor | SNÍMAČ PLECHU LISOVADLA; red ink on sheet 1 "– Д. пресса с пластиной" | NO 13-14, diamond (proximity) actuator; OM list 10.1: Telemecanique XCK-A 110 | machine | 5 | 14 | sure | om:20261115_023023 | to PLC IN-1 (30X10); what the PLC does with it is not printed [?] (on-site list)
XC2 | connector | table-cabinet interconnection | PROPOJENÍ STŮL–ROZVADĚČ | pins 1-9 used | cabinet | 5-6 | 11; 01-08 | [?] |  | pins 1-3 S24/S27 (5:11-12), 4-9 S10/S11 (6:01-08); label not seen in the photos (thread power marks it [?])
PLC | programmable logic controller | COMPACT PLC: inputs and outputs of sheet 8 | COMPACT PLC | B&R COMPACT P.L.C., 16 inputs / 14 outputs 24 V DC (photo 144328) | cabinet | 8 | 01-05 | sure | 144328 | device of thread plc_drive (sheet 8); used here: IN-0, IN-1, IN-2, IN-9, IN-A, OUT-0, OUT-9, +24V
K1 | auxiliary relay | switches ~48 V to Y3 (air cushion) | POMOCNÁ RELÉ K1 – ŘÍZENÍ Y3 | photo: F. Lütze relay, 1 changeover 11-12-14; coil voltage not read (24 V DC from the PLC, estimated); OM list 10.2: RE6-0011 | cabinet | 5 | 15 | sure | 144324 om:20261115_023314 | coil A1 from PLC OUT-9 through KM8 13-14, so only while KM8 (blower) runs; contact at 2:31 (thread power); photo markers A1K1, 11K1, 14K1
K2 | auxiliary relay | feed-cut interlock (BLOKOVÁNÍ POSUV-ŘEZ) | POMOCNÁ RELÉ K2 – BLOKOVÁNÍ POSUV-ŘEZ | photo: F. Lütze relay as K1, changeover 11-12-14; coil voltage not read (24 V DC from the PLC, estimated); OM list 10.2: RE6-0011 | cabinet | 5-6 | 16; 17 | sure | 144324 144344 om:20261115_023314 d:20261114_014513 | coil from PLC OUT-0 (5:16); contact to BMR1 17 (6:17): print 13-14, hand "11" over "13" on the clean sheet 6 (014513), photo 144324: marker 11K2 on 11; the wire on 14 is not readable (a blue wire with its sleeve turned away leaves the K1/K2 bottom); whether +24V on BMR1 17 allows or blocks the cut is not printed [?] (on-site list)
X11 | terminal strip | terminal strip in the cabinet | SVORKOVNICE V ROZVADĚČI | 6 terminals (1-6) (photo) | cabinet | 3 | 01 | sure | 144309 | device of thread power; on sheet 6 the BMR1 1 line runs through 5X11 and 6X11 (print 3X11, 4X11 hand-corrected); photo 144309: black wires on 2X11 3X11, blue on 5X11 6X11, copper bridges 3-4 and 5-6
S10 | pushbutton | cut start button (two-hand, left) | TLAČÍTKA SPOUŠTĚNÍ ŘEZU S10, S11; RU кнопки пуска реза | NC 1A-2A, NO 3A-4A; OM list 10.1: BACO head V22AH20, adapter 233E, block 23E10 | machine | 6 | 01-03 | sure | om:20261115_022802 | common 1A+3A from BMR1 1 through 5X11, 6X11, 4XC2; NC to BMR1 2 (5XC2), NO to BMR1 3 (6XC2); two-hand with S11 within 0,5 s, release before bottom stops the knife (OM)
S11 | pushbutton | cut start button (two-hand, right) | TLAČÍTKA SPOUŠTĚNÍ ŘEZU S10, S11 | NC 1A-2A, NO 3A-4A | machine | 6 | 06-08 | sure |  | common 1A+3A from BMR1 6 (7XC2); NC to BMR1 7 (8XC2), NO to BMR1 8 (9XC2); red ink "+26" at BMR1 6 (194606)
X8 | terminal strip | terminal strip of sensors S12, SQ1, SQ2 (S13, S14 too on sheet 6) | SVORKOVNICE SNÍMAČŮ S12, SQ1, SQ2 | terminals 1-6 used | machine | 6 | 09-13 | [?] |  | not seen in the cabinet; place on the machine estimated (thread power marks it [?]); 1X8 = common +24V
SQ1 | sensor | knife lock sensor | SNÍMAČE ZAJIŠTĚNÍ NOŽE SQ1, SQ2 (SNÍMAČ POLOHY ZAJIŠTĚNÍ NOŽE); red ink on sheet 1 "(на оси стопора)" | contact 4-1 drawn NO | machine | 6 | 09 | sure | d:20261113_194843 | to BMR1 9 (37X10, 2X8); red ink "Норм „ON“" by SQ1 and a red outline triangle (194606, 194843)
SQ2 | sensor | knife lock sensor | SNÍMAČE ZAJIŠTĚNÍ NOŽE SQ1, SQ2 | contact 4-1 drawn NO | machine | 6 | 10 | sure |  | to BMR1 10 (38X10, 3X8); red filled triangle (194606)
S12 | sensor on cam | knife position sensor on the cam of the cutting mechanism | SNÍMAČE NA VAČCE ŘEZOVÉHO ÚSTROJÍ (SNÍMAČ POLOHY NOŽE) | contact 2-1 drawn NC; cam ("G") actuator | machine | 6 | 11 | sure |  | to BMR1 11 (39X10, 4X8)
S13 | sensor on cam | knife position sensor on the cam of the cutting mechanism | SNÍMAČE NA VAČCE ŘEZOVÉHO ÚSTROJÍ | contact 2-1 drawn NC | machine | 6 | 12 | sure |  | to BMR1 12 (41X10, 42X10, 5X8); red outline triangle (194606)
S14 | sensor on cam | knife position sensor on the cam of the cutting mechanism | SNÍMAČE NA VAČCE ŘEZOVÉHO ÚSTROJÍ | contact 2-1 drawn NC | machine | 6 | 13 | sure |  | to BMR1 13 (40X10, 6X8); red outline triangle (194606)
TABLO | control panel | console control panel (B&R operator terminal) | TABLO | +24V from 33X10 (6:15) | console | 8 | 03-05 | sure |  | device of thread plc_drive (sheet 8); here only its +24V feed "TABLO +24V (8:03)"
UZ1 | frequency inverter | M2 feed drive | - | Lenze, relay terminals K12 K14 | cabinet | 2 | 17-26 | sure | 144201 144205 | device of thread power; here only K14 fed from 34X10 "UZ1 K14 (2:26)"
R14 | resistor | series resistor of sheet 7 (Y14 supply) | - | 11R/25W; OM 11R-25W | cabinet | 7 | 07 | sure | 143202 144340 d:20261113_213823 d:20261113_213049 | part list on sheet 1 (TABULKA POUŽITÝCH SOUČÁSTEK) box 7: "R14 11R/25W" (213823, 213049); between 2UG50 and BMR1 25 (7:07); end names 1 (UG50 2 side), 2 (BMR1 25 side) as in power_wires.csv; photos 143202 and 144340 (each): red tube on a bolt, both leads marked R14 (blue); the R14 on board UG50 is UG50/R14 (thread power)
"""

# sheet col | from | to | signal | wire label | evidence | extra sources (photo stems; d:/om: stems; SH) | note
WIRES = r"""
4 01 | UG50:12 | S2:3A | ~24V | 12UG50 | sure | 144227 SH | arrow "12UG50 (3:04)"
4 02-05 | S2:3A | S2:4B | ~24V |  | sure | 144344 | 3A and 4B joined at the selector as printed; photo marker read "3BS2" [?]
4 02 | S2:4A | X10:8 | ~24V work light | 8X10 | sure | 144314 | print joins 4A to 7X10 and 8X10; photo 144314: the inside wire (red) is on 8, bridge 7-8
4 01-02 | X10:8 | X10:7 | ~24V work light |  | sure | 144314 | print joins 7X10 and 8X10; photo 144314: copper bridge 7-8 (position ±1), no inside wire on 7
4 01 | X10:7 | E1:1 | ~24V work light | 7X10 | sure |  | field wire to the lamp
4 02 | X10:8 | E2:1 | ~24V work light | 8X10 | sure |  | field wire to the lamp
4 01 | E1:2 | X10:11 | 0V | 11X10 | sure |  | E1 and E2 returns joined above 11X10 as printed; where the join is made is not printed
4 02 | E2:2 | X10:11 | 0V | 11X10 | sure |  | see E1 2
4 03-05 | S2:3B | X10:9 | ~24V cut-line light | 9X10 | sure | 144314 | print joins 3B to 9X10 and 10X10; photo 144314: inside wire (red) on 9, bridge 9-10
4 03-05 | X10:9 | X10:10 | ~24V cut-line light |  | sure | 144314 | print joins 9X10 and 10X10; photo 144314: copper bridge 9-10 (±1)
4 03-05 | X10:9 | E3:1 | ~24V cut-line light | 9X10 | sure |  | field wire
4 03-05 | X10:10 | E4:1 | ~24V cut-line light | 10X10 | sure |  | field wire
4 03-05 | E3:2 | X10:13 | 0V | 13X10 | sure |  | E3 and E4 returns joined above 13X10 as printed
4 03-05 | E4:2 | X10:13 | 0V | 13X10 | sure |  | see E3 2
4 03 | X10:11 | X10:12 | 0V |  | sure | 144314 | print joins 11X10 and 13X10 into 12X10; photo 144314: copper bridge 11-13 (±1)
4 03 | X10:13 | X10:12 | 0V |  | sure | 144309 144314 | see X10 11
4 03 | X10:12 | X5: | 0V | 12X10 | sure | 144314 SH | "(2:02) X5"; photo 144314: inside wire (red) on 12
4 10 | UG50:13 | QF1:43 | ~24V | 13UG50 | sure | 144259 SH | arrow "13UG50 (3:04)" at column 01, line to QF1 43 at column 10
4 10 | QF1:44 | BMR1:19 | ~24V | 44QF1 | sure | 144259 143021 SH | sheet 7 column 01 "44QF1 (4:10)"; photo 144259: 44QF1 x2; photo 143021: 19BMR1 red
4 10-12 | QF1:44 | S4:3 | ~24V |  | sure | 144259 144344 | sheet-4 control bus after QF1 44 (feeds S4 3 and Q2 9); photo 144259: 44QF1 x2; photo 144344: 3S4 x2 [?] (one clear, the second sleeve shows only "..S4")
4 12-16 | S4:3 | Q2:9 | ~24V |  | sure | 144344 | same bus; photo 144344: 9Q2; order of the bus wires not seen
4 10 | BMR1:20 | X10:14 | ~24V | 14X10 | sure | 143021 144309 144314 d:20261113_193629 | sheet 7 column 02 "14X10 (4:10)"; red ink on sheet 7 "~24V" arrows at 19 and 20 and "A1 KM1A KM1B" (193629); photo 143021: 20BMR1 red; photo 144314: inside wire (red) on 14 (its 14X10 sleeve also hangs into the left edge of 144309)
4 10 | X10:14 | S5:21 | ~24V | 14X10 | sure |  | field wire
4 10 | S5:22 | X10:15 | ~24V | 15X10 | sure |  | field wire
4 10 | X10:15 | S1:21 | ~24V | 15X10 | sure | 144314 | field to field through X10 15; photo 144314: no inside wire on 15
4 10 | S1:22 | X10:16 | ~24V | 16X10 | sure |  | field wire from the console
4 10 | X10:16 | X10:17 | ~24V |  | sure | 144309 144314 | 16X10 and 17X10 in series as printed; photo 144314: copper bridge 16-17 (on 144309 only its end at 17, at the left edge)
4 10 | X10:17 | KM1A:13 | ~24V | 17X10 | sure | 144309 144255 | photo 144309: inside wire (red) on 17; photo 144255: 13KM1A x2
4 08-10 | KM1A:13 | Q2:1 | ~24V |  | sure | 144255 | Q2 1-2 parallel to KM1A 13-14 + KM1B 14-13
4 10 | KM1A:14 | KM1B:14 | ~24V |  | sure |  | KM1A and KM1B self-hold contacts in series
4 09-10 | KM1B:13 | KM1A:A1 | ~24V |  | sure |  | node KM1B 13, Q2 2, KM1A A1, KM1B A1 as printed; order of the wires not seen
4 10-11 | KM1B:13 | KM1B:A1 | ~24V |  | sure |  | see KM1B 13
4 08-10 | Q2:2 | KM1B:13 | ~24V |  | sure | 144344 | photo marker 2Q2
4 10 | KM1A:A1 | RC1:1 | ~24V |  | sure |  | RC1 across the coils
4 09-10 | RC1:2 | KM1A:A2 | 0V |  | sure |  | RC1 across the coils
4 09 | KM1A:A2 | X5: | 0V |  | sure | SH | coil-return bus 4:08-20 to "(2:02) X5"; X5 list 2:02 names KM1A A2
4 09-11 | KM1B:A2 | KM1A:A2 | 0V |  | sure |  | coil-return bus 4:08-20; order of the bus wires not seen (drawn order)
4 12 | S4:4 | KM8:A1 | ~24V |  | sure | 144247 | marker A1KM8 (RC)
4 12 | KM8:A1 | RC8:1 | ~24V |  | [?] |  | RC8 label could read RC6 (232949)
4 12 | RC8:2 | KM8:A2 | 0V |  | [?] |  | RC8 label could read RC6 (232949)
4 11-12 | KM8:A2 | KM1B:A2 | 0V |  | sure |  | coil-return bus
4 16 | Q2:10 | KT1:1 | ~24V |  | sure | 144344 | M1 bus from Q2 9-10 (closed in position 1); photo 10Q2
4 15-16 | Q2:10 | KT1:4 | ~24V |  | sure | 144259 | M1 bus; photo 4KT1 x2 (bus in and out)
4 14-15 | KT1:4 | KM4:5 | ~24V |  | sure | 144247 144259 | M1 bus; photo 144247: 5KM4 x2
4 13-14 | KM4:5 | KM2:14 | ~24V |  | sure | 144247 | KM2 14-13 parallel to KM4 5-6
4 13-14 | KM2:13 | KM4:6 | ~24V |  | sure | 144247 | node KM2 13, KM4 6, KT1 12, KM2 A1 as printed; photo 13KM2 x2, 6KM4
4 13-14 | KM2:13 | KT1:12 | ~24V |  | sure | 144259 | photo 12KT1 x2; wire order chosen to fit the marker counts (not seen)
4 13 | KT1:12 | KM2:A1 | ~24V |  | sure |  | KM2 coil fed from the node
4 13 | KM2:A1 | RC2:1 | ~24V |  | sure |  | RC2 across KM2
4 13 | RC2:2 | KM2:A2 | 0V |  | sure |  | RC2 across KM2
4 12-13 | KM2:A2 | KM8:A2 | 0V |  | sure |  | coil-return bus
4 14 | KT1:14 | KM4:21 | ~24V |  | sure | 144259 144247 | KT1 12-14 = 25-26 NC by the face legend (device row KT1); photo 144259: 14KT1; photo 144247: 21KM4
4 14 | KM4:22 | KM3:A1 | ~24V |  | sure | 144247 | KM4 21-22 NC: KM3 (delta) only while KM4 (star) is off
4 14 | KM3:A1 | RC3:1 | ~24V |  | sure |  | RC3 across KM3
4 14 | RC3:2 | KM3:A2 | 0V |  | sure |  | RC3 across KM3
4 13-14 | KM3:A2 | KM2:A2 | 0V |  | sure |  | coil-return bus
4 15 | KT1:5 | KM3:62 | ~24V |  | sure | 144259 144247 | KT1 4-5 = 15-18 NO by the face legend (device row KT1); photo 144259: 5KT1; photo 144247: 62KM3
4 15 | KM3:61 | KM4:A1 | ~24V |  | sure | 144247 | KM3 61-62 NC: KM4 (star) only while KM3 (delta) is off
4 15 | KM4:A1 | RC4:1 | ~24V |  | sure |  | RC4 across KM4
4 15 | RC4:2 | KM4:A2 | 0V |  | sure |  | RC4 across KM4
4 14-15 | KM4:A2 | KM3:A2 | 0V |  | sure |  | coil-return bus
4 16 | KM2:61 | KT1:9 | ~24V |  | sure | 144247 | KM2 62-61 NC bridges KT1 9-10 (control input) while KM2 is off
4 16 | KM2:62 | KT1:10 | ~24V |  | sure | 144247 144259 | black block printed at KT1 10; photo 144247: 62KM2; photo 144259: 10KT1
4 15-16 | KT1:2 | KM4:A2 | 0V |  | sure |  | coil-return bus
4 17-18 | BMR1:29 | KM3:13 | ~24V | 13KM3 | sure | 143021 144334 144247 | sheet 7 column 11 "13KM3 (4:17)"; photo 143021, 144334: BMR1 29 wired (red), marker hidden; photo 144247: 13KM3 x2
4 17-18 | KM3:13 | Q2:3 | ~24V |  | sure |  | Q2 3-4 (closed in 0) parallel to KM3 13-14
4 17-18 | Q2:4 | KM3:14 | ~24V |  | sure | 144247 144259 | node N1 as printed: Q2 4, KM3 14, KM6 A1, KM3 54, KT2 4; order chosen to fit the photo counts 14KM3 x2, 54KM3 x2 (144247) and 4KT2 x2 (144259): Q2 4 - KM3 14 - KT2 4 - KM3 54 - KM6 A1 (order not seen)
4 17-19 | KM3:54 | KM6:A1 | ~24V |  | sure | 144247 | node N1 (order: see line 68); photo 54KM3 x2
4 17-19 | KM3:14 | KT2:4 | ~24V |  | sure | 144259 | node N1: the column-17 node joined to column 19
4 17 | KM6:A1 | RC6:1 | ~24V |  | sure |  | RC6 across KM6
4 17 | RC6:2 | KM6:A2 | 0V |  | sure |  | RC6 across KM6
4 16-17 | KM6:A2 | KT1:2 | 0V |  | sure |  | coil-return bus
4 19 | BMR1:28 | KM3:53 | ~24V | 53KM3 | sure | 143021 144247 | sheet 7 column 10 "53KM3 (4:19)"; photo 143021: 28BMR1 red; photo 144247: 53KM3
4 19 | KM3:54 | KT2:4 | ~24V |  | sure | 144247 144259 | KM3 53-54 then node N1; photo 54KM3 x2 (144247), 4KT2 x2 (144259)
4 19 | KT2:5 | KM7:A1 | ~24V |  | sure | 144259 144251 | KT2 4-5 delays KM7; photo 5KT2 (144259), A1KM7 (RC) (144251)
4 19 | KM7:A1 | RC7:1 | ~24V |  | sure |  | RC7 across KM7
4 19 | RC7:2 | KM7:A2 | 0V |  | sure |  | RC7 across KM7
4 17-19 | KM7:A2 | KM6:A2 | 0V |  | sure |  | coil-return bus
4 20 | UG50:6 | KM6:1 | +24V | 6UG50 | sure | 144227 144247 SH | arrow "6UG50 (3:04)"; photo 144247: 1KM6
4 20 | KM6:2 | KT2:1 | +24V |  | sure | 144247 | KT2 runs once KM6 closes; photo 2KM6
4 20 | KT2:1 | V20:1 | +24V |  | sure |  | V20 across the KT2 coil
4 20 | V20:2 | KT2:2 | 0V |  | sure |  | V20 across the KT2 coil
4 19-20 | KT2:2 | KM7:A2 | 0V |  | sure |  | coil-return bus (right end)
5 01 | Y01:PE | X10:PE | PE | ⏚X10 | sure |  | printed "⏚X10" then "⏚ (2:01)"
5 01 | X10:PE | PE: | PE |  | sure | SH | "⏚ (2:01)"
5 02 | BMR1:22 | X10:18 | +27V | 18X10 | sure | 143021 144309 | sheet 7 column 04 "18X10 (5:02)"; red ink there "Y01 блокир. шестерни"; photo 143021: 22BMR1; photo 144309: inside wire (blue) on 18
5 02 | X10:18 | Y01:+ | +27V | 18X10 | sure |  | field wire to the magnet
5 02 | Y01:+ | V01:1 | +27V |  | sure |  | V01 across the coil
5 02 | V01:2 | Y01:- | 0V |  | sure |  | V01 across the coil
5 02 | Y01:- | X10:19 | 0V | 19X10 | sure |  | field wire
5 02 | X10:19 | X5: | 0V | 19X10 | sure | 144309 SH | "(2:02) X5"
5 04 | BMR1:26 | X10:20 | +14V | 20X10 | sure | 143021 144309 d:20261113_193629 | sheet 7 column 08 "20X10 (5:04)"; "+14V" printed on the line; red ink at BMR1 26 "Y14 гидро распр. магнит." (193629)
5 04 | X10:20 | Y14:+ | +14V | 20X10 | sure |  | field wire
5 04 | Y14:+ | V14:1 | +14V |  | sure |  | V14 across the coil
5 04 | V14:2 | Y14:- | 0V |  | sure |  | V14 across the coil
5 04 | Y14:- | X10:21 | 0V | 21X10 | sure |  | field wire; no PE drawn for Y14
5 04 | X10:21 | X5: | 0V | 21X10 | sure | 144309 SH | "(2:02) X5"
5 06 | Y11:PE | X10:PE | PE | ⏚X10 | sure |  | printed "⏚X10" then "⏚ (2:01)" at column 06, the second ⏚X10 of this sheet: one terminal X10 PE in this netlist (conductor X10 PE -> PE: line 86), drawn twice as printed
5 07 | UG50:18 | KM6:3 | ~48V | 18UG50 | sure | 144227 144247 SH | arrow "18UG50 (3:04)"; sheet 5 prints "KM6 (4:16)", the coil is drawn at 4:17
5 07 | KM6:4 | X10:22 | ~48V | 22X10 | sure | 144247 144309 | photo 144247: 4KM6; photo 144309: inside wire on 22
5 07 | X10:22 | Y11:1 | ~48V | 22X10 | sure |  | field wire
5 07 | Y11:1 | RC11:1 | ~48V |  | sure |  | RC11 across the coil
5 07 | RC11:2 | Y11:2 | 0V |  | sure |  | RC11 across the coil
5 07 | Y11:2 | X10:23 | 0V | 23X10 | sure |  | field wire
5 07 | X10:23 | X5: | 0V | 23X10 | sure | 144309 SH | "(2:02) X5"
5 10 | UG50:10 | KM6:5 | +33V | 10UG50 | sure | 144227 144247 SH | arrow "10UG50 (3:04)"; photo 144247: 5KM6
5 09-10 | KM6:5 | Q2:5 | +33V |  | sure |  | the +33V node feeds KM6 5 and the knife-change branch Q2 5
5 10 | KM6:6 | KM7:6 | +33V |  | sure |  | KM6 5-6 and KM7 6-5 in series (cut branch)
5 10 | KM7:5 | X10:27 | +33V | 27X10 | sure | 144251 144309 | photo 5KM7 (144251), inside wire on 27 (144309)
5 09 | Q2:6 | X10:24 | +33V | 24X10 | sure | 144344 144309 | Q2 5-6 (closed in 0) starts the knife-change branch; photo 144344: 6Q2; photo 144309: inside wire on 24
5 09 | X10:24 | S19:13 | +33V | 24X10 | sure |  | field wire
5 09 | S19:14 | X10:25 | +33V | 25X10 | sure |  | field wire
5 09 | X10:25 | S5:13 | +33V | 25X10 | sure | 144309 | field to field through X10 25 (no inside wire seen)
5 09 | S5:14 | X10:26 | +33V | 26X10 | sure |  | field wire
5 09-10 | X10:26 | X10:27 | +33V |  | sure | 144309 144314 | 26X10 joined to 27X10 as printed; photo 144314: bridge 26-27, no inside wire on 26 (144309: a two-pole bridge in the 26-28 area, oblique view, no 26X10)
5 10 | X10:27 | Y10:+ | +33V | 27X10 | sure |  | field wire to the clutch
5 10 | Y10:+ | V10:1 | +33V |  | sure |  | V10 and R10 in series across the coil
5 10 | V10:2 | R10:1 | +33V |  | sure |  | V10 and R10 in series
5 10 | R10:2 | Y10:- | 0V |  | sure |  | V10 and R10 in series across the coil
5 10 | Y10:- | X10:28 | 0V | 28X10 | sure |  | field wire
5 10 | X10:28 | X5: | 0V | 28X10 | sure | 144309 SH | "(2:02) X5"
5 13 | BMR1:23 | X10:32 | +24V | 32X10 | sure | 143021 144309 | sheet 7 column 05 "32X10 (5:13)"; on sheet 5 the BMR1 23 (7:05) arrow joins the 33X10 (6:15) line at 31X10/32X10
5 14 | X10:33 | X10:32 | +24V |  | sure | 144309 144314 | printed as "33X10 (6:15)" on sheet 5 and "32X10 (5:14)" on sheet 6; photo 144309: copper comb 31-36 (±1), no inside wire on 33 (144314 shows both too)
5 13-14 | X10:32 | X10:31 | +24V |  | sure | 144309 | 31X10 and 32X10 joined as printed; photo: bridge 31-36
5 11-13 | X10:31 | XC2:1 | +24V | 1XC2 | sure |  | field cable to the table
5 13 | X10:31 | S30:13 | +24V | 31X10 | sure |  | field wire
5 14 | X10:32 | S28:13 | +24V | 32X10 | sure |  | field wire
5 11 | XC2:1 | S24:21 | +24V | 1XC2 | sure |  | 1XC2 feeds S24 21 and S27 21
5 12 | XC2:1 | S27:21 | +24V | 1XC2 | sure |  | see XC2 1
5 11 | S24:22 | XC2:2 | S24 backgauge front position | 2XC2 | sure |  | NC
5 11 | XC2:2 | PLC:IN-A | S24 backgauge front position | 2XC2 | sure | 144328 | "PLC IN-A (8:02)"; photo marker IN-A PLC
5 12 | S27:22 | XC2:3 | S27 backgauge rear position | 3XC2 | sure |  | NC
5 12 | XC2:3 | PLC:IN-9 | S27 backgauge rear position | 3XC2 | sure | 144328 | "PLC IN-9 (8:02)"; photo marker IN-9 PLC
5 13 | S30:14 | X10:29 | S30 clamp position (top per sheet 1) | 29X10 | sure |  | NO
5 13 | X10:29 | PLC:IN-2 | S30 clamp position (top per sheet 1) | 29X10 | sure | 144328 | "PLC IN-2 (8:01)"; photo: wire on IN-2 (marker hidden)
5 14 | S28:14 | X10:30 | S28 clamp plate | 30X10 | sure |  | NO
5 14 | X10:30 | PLC:IN-1 | S28 clamp plate | 30X10 | sure | 144328 | "PLC IN-1 (8:01)"; photo marker IN-1 PLC
5 15 | PLC:OUT-9 | KM8:13 | control of Y3 | 13KM8 | [?] | 144328 144247 | "PLC OUT-9 (8:02)"; photo 144328: about four output wires among OUT-8..D, positions not read: on-site list; photo 144247: 13KM8
5 15 | KM8:14 | K1:A1 | control of Y3 |  | sure | 144247 144324 | KM8 13-14: K1 only while KM8 (blower) is on; photo 144247: 14KM8; photo 144324: A1K1
5 15 | K1:A2 | X5: | 0V |  | sure | SH | "(2:02) X5"; K1 contact at 2:31 (thread power)
5 16 | PLC:OUT-0 | K2:A1 | feed-cut interlock | A1K2 | sure | 144328 144324 144344 d:20261113_191800 | "PLC OUT-0 (8:01)"; label printed in the sheet 8 table: OUT-0, A1K2, 5:16 (20261113_191800); red ink on sheet 7 at IN-0 "сигнал на резку A1K2"; photo OUT-0 P.L.C (144328), A1K2 (144324, 144344)
5 15-16 | K2:A2 | K1:A2 | 0V |  | sure | 144324 144344 | K1 A2 and K2 A2 joined to "(2:02) X5" as printed; photo A2K2 (144344)
6 01 | BMR1:1 | X11:5 | S10 common (BMR1 1) | 5X11 | sure | 144309 143021 d:20261114_014439 | print "3X11" (194606), hand-corrected to "5X11" on the clean sheet 6 (014439); photo 144309: blue wire on 5X11 - wired as corrected; red ink "26 „0“" at BMR1 1 (194606)
6 01 | X11:5 | X11:6 | S10 common (BMR1 1) |  | sure | 144309 d:20261114_014439 | print "3X11 / 4X11" in series, hand-corrected 5X11 / 6X11; photo 144309: copper bridge 5-6 (±1). FF1 (light curtain) not fitted (certificate "—"); a reading, not part of this row: 5-6 is likely a bridged curtain place (estimated, on-site entry 9)
6 01 | X11:6 | XC2:4 | S10 common (BMR1 1) | 4XC2 | sure | 144309 d:20261114_014439 | print "4X11", hand "6X11"; photo 144309: blue wire on 6X11
6 01 | XC2:4 | S10:3A | S10 common (BMR1 1) | 4XC2 | sure |  | machine side of XC2
6 01 | S10:3A | S10:1A | S10 common (BMR1 1) |  | sure |  | 3A and 1A joined as printed
6 02 | S10:2A | XC2:5 | S10 NC (BMR1 2) | 5XC2 | sure |  | NC 1A-2A
6 02 | XC2:5 | BMR1:2 | S10 NC (BMR1 2) | 5XC2 | sure | 143021 | photo 2BMR1
6 03 | S10:4A | XC2:6 | S10 NO (BMR1 3) | 6XC2 | sure |  | NO 3A-4A
6 03 | XC2:6 | BMR1:3 | S10 NO (BMR1 3) | 6XC2 | sure | 143021 | photo 3BMR1
6 04 | BMR1:4 | KM6:61 | KM6/KM7 feedback | 61KM6 | sure | 143021 144251 | red ink "+26" at BMR1 4 and a dotted red triangle on this line above KM6 61 (194606); photo 4BMR1 (143021), 61KM6 (144251)
6 04 | KM6:62 | KM7:22 | KM6/KM7 feedback |  | [?] | 144247 144205 144251 | print "KM7 62" (6:04); photo 144251: 62KM6 at KM6 62 (this end seen), KM7 has only its built-in NC 21-22 (marker 21KM7); photo 144205: 22KM7; the pairing KM6 62 - KM7 22 is not seen (22 faces KM6 by number order)
6 04-05 | KM7:21 | BMR1:5 | KM6/KM7 feedback |  | [?] | 144251 143021 | print "KM7 61" (6:04); photo 144251: marker 21KM7; 21 faces BMR1 5 by number order, not seen; photo 143021: BMR1 5 wired, marker hidden
6 06 | BMR1:6 | XC2:7 | S11 common (BMR1 6) | 7XC2 | sure | 143021 | red ink "+26" at BMR1 6 (194606); photo 6BMR1
6 06 | XC2:7 | S11:3A | S11 common (BMR1 6) | 7XC2 | sure |  | machine side of XC2
6 06 | S11:3A | S11:1A | S11 common (BMR1 6) |  | sure |  | 3A and 1A joined as printed
6 07 | S11:2A | XC2:8 | S11 NC (BMR1 7) | 8XC2 | sure |  | NC 1A-2A
6 07 | XC2:8 | BMR1:7 | S11 NC (BMR1 7) | 8XC2 | sure | 143021 | photo 7BMR1
6 08 | S11:4A | XC2:9 | S11 NO (BMR1 8) | 9XC2 | sure |  | NO 3A-4A
6 08 | XC2:9 | BMR1:8 | S11 NO (BMR1 8) | 9XC2 | sure | 143021 | photo 8BMR1
6 09 | BMR1:9 | X10:37 | SQ1 knife lock | 37X10 | sure | 143021 144309 | photo 143021: 9BMR1; photo 144309: inside wire on 37
6 09 | X10:37 | X8:2 | SQ1 knife lock | 2X8 | sure | 144309 | field cable to X8; red outline triangle at BMR1 9 (194606)
6 09 | X8:2 | SQ1:4 | SQ1 knife lock | 2X8 | sure | d:20261113_194843 | contact 4-1 drawn NO; red ink "Норм „ON“" by SQ1 (194843)
6 09 | SQ1:1 | X8:1 | +24V | 1X8 | sure |  | common 1 of SQ1 SQ2 S12 S13 S14 on 1X8
6 10 | BMR1:10 | X10:38 | SQ2 knife lock | 38X10 | sure | 143021 144309 | photo 143021: 10BMR1; photo 144309: inside wire on 38
6 10 | X10:38 | X8:3 | SQ2 knife lock | 3X8 | sure |  | field cable; red filled triangle at BMR1 10 (194606)
6 10 | X8:3 | SQ2:4 | SQ2 knife lock | 3X8 | sure |  | contact 4-1 drawn NO
6 10 | SQ2:1 | X8:1 | +24V | 1X8 | sure |  | common on 1X8
6 11 | BMR1:11 | X10:39 | S12 knife position | 39X10 | sure | 143021 144309 | photo 143021: 11BMR1; photo 144309: inside wire on 39
6 11 | X10:39 | X8:4 | S12 knife position | 4X8 | sure |  | field cable
6 11 | X8:4 | S12:2 | S12 knife position | 4X8 | sure |  | contact 2-1 drawn NC
6 11 | S12:1 | X8:1 | +24V | 1X8 | sure |  | common on 1X8
6 12 | BMR1:12 | X10:41 | S13 knife position | 41X10 | sure | 143021 144309 | photo 143021: 12BMR1; photo 144309: inside wire on 41; red outline triangle (194606)
6 12 | X10:41 | X10:42 | S13 knife position |  | sure | 144309 | 41X10 and 42X10 in series as printed; photo 144309: bridge 41-42, no inside wire on 42
6 12 | X10:42 | X8:5 | S13 knife position | 5X8 | sure |  | field cable
6 12 | X8:5 | S13:2 | S13 knife position | 5X8 | sure |  | contact 2-1 drawn NC
6 12 | S13:1 | X8:1 | +24V | 1X8 | sure |  | common on 1X8
6 13 | BMR1:13 | X10:40 | S14 knife position | 40X10 | sure | 143021 144309 | photo 143021: BMR1 13 wired, marker hidden; photo 144309: inside wire on 40; red outline triangle (194606)
6 13 | X10:40 | X8:6 | S14 knife position | 6X8 | sure |  | field cable
6 13 | X8:6 | S14:2 | S14 knife position | 6X8 | sure |  | contact 2-1 drawn NC
6 13 | S14:1 | X8:1 | +24V | 1X8 | sure |  | common on 1X8
6 13-15 | X8:1 | X10:33 | +24V | 1X8 | sure | 144309 | sensor common 1X8 fed from 33X10 (field side; no inside wire on 33)
6 14-15 | X10:33 | TABLO:+24V | +24V | 33X10 | sure |  | "TABLO +24V (8:03)"
6 15-16 | X10:33 | X10:34 | +24V |  | sure | 144309 144314 | 33X10-36X10 joined as printed; photo 144309: copper comb 31-36 (±1) (also on 144314)
6 16-17 | X10:34 | X10:35 | +24V |  | sure | 144309 144314 | see X10 33
6 17-18 | X10:35 | X10:36 | +24V |  | sure | 144309 144314 | see X10 33
6 18 | X10:36 | UG50:5 | +24V | 5UG50 | sure | 144227 144309 SH | "5UG50 (3:04)"
6 13-16 | X10:34 | UZ1:K14 | +24V | 34X10 | sure | 144205 SH | "UZ1 K14 (2:26)"; photo K14: UZ1
6 16 | X10:34 | BMR1:+24V | +24V | 34X10 | sure | 143021 144309 d:20261114_014711 d:20261114_014834 d:20261113_193629 | sheet 7 column 13 "34X10 (6:16)", the same on the clean copies (20261114_014711, 20261114_014834) and on the annotated copy (20261113_193629)
6 17 | X10:35 | PLC:+24V | PLC supply +24V | 35X10 | sure | 144328 | "PLC +24V PLC (8:03)"
6 14 | BMR1:14 | Q2:7 | Q2 loop (BMR1 14-15) |  | sure | 143021 | red dotted triangle at BMR1 14 (194606); photo 14BMR1
6 15 | Q2:8 | BMR1:15 | Q2 loop (BMR1 14-15) |  | sure | 144344 143021 | Q2 7-8 drawn open, closed in 0 (thread power); photo 144344: 8Q2; photo 143021: 15BMR1
6 16 | BMR1:16 | X10:43 | S30 clamp top (BMR1 16) | 43X10 | sure | 143021 144309 | photo 143021: 16BMR1; photo 144309: inside wire on 43
6 16 | X10:43 | S30:21 | S30 clamp top (BMR1 16) | 43X10 | sure |  | field wire
6 16 | S30:22 | X10:34 | +24V | 34X10 | sure |  | NC 21-22 returns to the +24V terminal 34X10
6 17 | BMR1:17 | K2:11 | feed-cut interlock (BMR1 17) |  | sure | 143021 144324 d:20261114_014513 | print "K2 13" (6:17, 194606), hand "11" over "13" on the clean sheet 6 (014513); photo 144324: marker 11K2 (Lütze changeover 11-12-14), wired on 11
6 17 | K2:14 | X10:35 | +24V | 35X10 | sure | 144324 | no 14K2 marker seen
6 18 | BMR1:18 | X10:44 | S19 knife change (BMR1 18) | 44X10 | sure | 143021 144309 | photo 143021: 18BMR1; photo 144309: inside wire on 44
6 18 | X10:44 | S19:21 | S19 knife change (BMR1 18) | 44X10 | sure |  | field wire
6 18 | S19:22 | X10:36 | +24V | 36X10 | sure |  | NC 21-22 returns to 36X10
7 03 | UG50:1 | BMR1:21 | +27V | 1UG50 | sure | 144227 143021 SH | "1UG50 (3:04)"; photo 143021: 21BMR1
7 06 | BMR1:24 | PLC:IN-0 | cut-done signal | 24BMR | sure | 143021 144328 d:20261113_191800 | "PLC IN-0 (8:01)"; at the PLC "24BMR (7:06)", and in the sheet 8 table: IN-0, 24BMR, 7:06 (20261113_191800); red ink at IN-0 "сигнал на резку A1K2" (signal for cutting) and a red tick above the arrow (193629); photo 143021: 24BMR1; photo 144328: IN-0 PLC
7 07 | UG50:2 | R14:1 | +27V | 2UG50 | sure | 144227 144340 SH | "2UG50 (3:04)"; R14 11R/25W in series
7 07 | R14:2 | BMR1:25 | +27V |  | sure | 144340 143021 | photo 144340: R14 on both leads (blue); photo 143021: 25BMR1
7 09 | UG50:14 | BMR1:27 | ~24V | 14UG50 | sure | 144227 143021 SH | "14UG50 (3:04)"; photo 143021: 27BMR1 red
7 12 | BMR1:0V | X5: | 0V |  | sure | 143021 SH | "X5 (2:02)"; photo: BMR1 - wired
"""

# Coverage of the paths tables, one entry per data row in file order: conductor keys
# "A:t|B:t" joined by "; ", or "text:<where it is covered>".
COVER = {
    4: ['text:zone header of control_sheet4.svg (zones 9-15)',
        'UG50:12|S2:3A; S2:3A|S2:4B',
        'S2:4A|X10:8; S2:3B|X10:9',
        'X10:8|X10:7; X10:7|E1:1; X10:8|E2:1; E1:2|X10:11; E2:2|X10:11; X10:11|X10:12',
        'X10:9|X10:10; X10:9|E3:1; X10:10|E4:1; E3:2|X10:13; E4:2|X10:13; X10:13|X10:12',
        'X10:12|X5:',
        'UG50:13|QF1:43',
        'QF1:44|BMR1:19; QF1:44|S4:3',
        'BMR1:20|X10:14',
        'X10:14|S5:21; S5:22|X10:15',
        'X10:15|S1:21; S1:22|X10:16; X10:16|X10:17',
        'X10:17|KM1A:13; KM1A:14|KM1B:14; KM1B:13|KM1A:A1; KM1B:13|KM1B:A1',
        'KM1A:13|Q2:1; Q2:2|KM1B:13',
        'KM1A:A1|RC1:1; RC1:2|KM1A:A2; KM1A:A2|X5:',
        'KM1B:A2|KM1A:A2',
        'S4:4|KM8:A1; S4:3|Q2:9',
        'KM8:A1|RC8:1; RC8:2|KM8:A2; KM8:A2|KM1B:A2',
        'Q2:10|KT1:1; Q2:10|KT1:4',
        'KT1:4|KM4:5; KM4:5|KM2:14; KM2:13|KM4:6; KM2:13|KT1:12; KT1:12|KM2:A1; KM2:A1|RC2:1; RC2:2|KM2:A2; KM2:A2|KM8:A2',
        'KT1:14|KM4:21; KM4:22|KM3:A1; KM3:A1|RC3:1; RC3:2|KM3:A2; KM3:A2|KM2:A2',
        'KT1:5|KM3:62; KM3:61|KM4:A1; KM4:A1|RC4:1; RC4:2|KM4:A2; KM4:A2|KM3:A2',
        'Q2:10|KT1:1; KM2:61|KT1:9; KM2:62|KT1:10; KT1:2|KM4:A2',
        'BMR1:29|KM3:13; KM3:13|Q2:3; Q2:4|KM3:14; KM3:54|KM6:A1',
        'KM6:A1|RC6:1; RC6:2|KM6:A2; KM6:A2|KT1:2',
        'BMR1:28|KM3:53; KM3:54|KT2:4; KM3:14|KT2:4; KT2:5|KM7:A1',
        'KM7:A1|RC7:1; RC7:2|KM7:A2; KM7:A2|KM6:A2',
        'UG50:6|KM6:1; KM6:2|KT2:1',
        'KT2:1|V20:1; V20:2|KT2:2; KT2:2|KM7:A2',
        'KM1A:A2|X5:; KM1B:A2|KM1A:A2; KT2:2|KM7:A2',
        'text:pencil ZN/ZR noted on control_sheet4.svg and in the KT1, KT2 device rows'],
    5: ['Y01:PE|X10:PE; X10:PE|PE:', 'BMR1:22|X10:18', 'X10:18|Y01:+',
        'Y01:+|V01:1; V01:2|Y01:-; Y01:-|X10:19', 'X10:19|X5:', 'BMR1:26|X10:20', 'X10:20|Y14:+',
        'Y14:+|V14:1; V14:2|Y14:-; Y14:-|X10:21', 'X10:21|X5:', 'Y11:PE|X10:PE', 'UG50:18|KM6:3',
        'KM6:4|X10:22', 'X10:22|Y11:1', 'Y11:1|RC11:1; RC11:2|Y11:2; Y11:2|X10:23', 'X10:23|X5:',
        'UG50:10|KM6:5', 'KM6:6|KM7:6', 'KM7:5|X10:27', 'KM6:5|Q2:5; Q2:6|X10:24', 'X10:24|S19:13',
        'S19:14|X10:25', 'X10:25|S5:13', 'S5:14|X10:26', 'X10:26|X10:27', 'X10:27|Y10:+',
        'Y10:+|V10:1; V10:2|R10:1; R10:2|Y10:-; Y10:-|X10:28', 'X10:28|X5:', 'BMR1:23|X10:32',
        'X10:33|X10:32', 'X10:32|X10:31; X10:31|XC2:1; X10:31|S30:13', 'X10:32|S28:13',
        'XC2:1|S24:21; XC2:1|S27:21', 'S24:22|XC2:2', 'XC2:2|PLC:IN-A', 'S27:22|XC2:3',
        'XC2:3|PLC:IN-9', 'S30:14|X10:29', 'X10:29|PLC:IN-2', 'S28:14|X10:30', 'X10:30|PLC:IN-1',
        'PLC:OUT-9|KM8:13', 'KM8:14|K1:A1', 'K1:A2|X5:', 'PLC:OUT-0|K2:A1', 'K2:A2|K1:A2'],
    6: ['BMR1:1|X11:5; X11:5|X11:6; X11:6|XC2:4; XC2:4|S10:3A; S10:3A|S10:1A',
        'S10:2A|XC2:5; XC2:5|BMR1:2', 'S10:4A|XC2:6; XC2:6|BMR1:3', 'BMR1:4|KM6:61',
        'KM6:62|KM7:22', 'KM7:21|BMR1:5', 'BMR1:6|XC2:7; XC2:7|S11:3A; S11:3A|S11:1A',
        'S11:2A|XC2:8; XC2:8|BMR1:7', 'S11:4A|XC2:9; XC2:9|BMR1:8',
        'BMR1:9|X10:37; X10:37|X8:2; X8:2|SQ1:4', 'SQ1:1|X8:1',
        'BMR1:10|X10:38; X10:38|X8:3; X8:3|SQ2:4', 'SQ2:1|X8:1',
        'BMR1:11|X10:39; X10:39|X8:4; X8:4|S12:2', 'S12:1|X8:1',
        'BMR1:12|X10:41; X10:41|X10:42; X10:42|X8:5; X8:5|S13:2', 'S13:1|X8:1',
        'BMR1:13|X10:40; X10:40|X8:6; X8:6|S14:2', 'S14:1|X8:1', 'BMR1:14|Q2:7', 'Q2:8|BMR1:15',
        'BMR1:16|X10:43; X10:43|S30:21', 'S30:22|X10:34', 'BMR1:17|K2:11', 'K2:14|X10:35',
        'BMR1:18|X10:44; X10:44|S19:21', 'S19:22|X10:36', 'X8:1|X10:33',
        'X10:33|X10:32; X10:33|TABLO:+24V; X10:33|X10:34',
        'X10:34|BMR1:+24V; X10:34|UZ1:K14; X10:34|X10:35', 'X10:35|PLC:+24V; X10:35|X10:36',
        'X10:36|UG50:5', 'text:timing diagram on control_sheet6.svg'],
    7: ['QF1:44|BMR1:19', 'BMR1:20|X10:14', 'UG50:1|BMR1:21', 'BMR1:22|X10:18', 'BMR1:23|X10:32',
        'BMR1:24|PLC:IN-0', 'UG50:2|R14:1; R14:2|BMR1:25', 'BMR1:26|X10:20', 'UG50:14|BMR1:27',
        'BMR1:28|KM3:53', 'BMR1:29|KM3:13', 'BMR1:0V|X5:', 'X10:34|BMR1:+24V'],
}
PATH_TABLES = {4: '11_568_sheet4_paths.csv', 5: '12_568_sheet5_paths.csv',
               6: '12_568_sheet6_paths.csv', 7: '12_568_sheet7_paths.csv'}
PLC_IO = {'IN-0': ('BMR1', 'cut-done signal'), 'IN-1': ('X10', 'S28 clamp plate'),
          'IN-2': ('X10', 'S30 clamp position (top per sheet 1)'),
          'IN-9': ('XC2', 'S27 backgauge rear position'), 'IN-A': ('XC2', 'S24 backgauge front position'),
          'OUT-0': ('K2', 'feed-cut interlock'), 'OUT-9': ('KM8', 'control of Y3')}
STAMP = re.compile(r'(?<!\d)(\d{6})(?!\d)')  # a photo or scan stamp named in a note
MARK = re.compile(r'^(sure|\[\?\]|W|estimated ±\S.*)$')


def sources(extra, sheets):
    out = []
    for s in sheets:
        out += SRC[s]
    for tok in extra.split():
        if tok == 'SH':
            continue
        if re.fullmatch(r'\d{6}', tok):
            out.append(PH + tok + '.jpg')
        elif tok.startswith('d:'):
            out.append(D + tok[2:] + '.jpg')
        elif tok.startswith('om:'):
            out.append(OM + tok[3:] + '.jpg')
        else:
            raise SystemExit('bad source token ' + tok)
    seen = []
    for p in out:
        if p not in seen:
            seen.append(p)
    return '; '.join(seen)


def end(s):
    dev, term = s.split(':', 1)
    return dev, term


def key(a, b):
    return frozenset([a, b])


def build():
    devs, wires = [], []
    for line in DEVICES.strip().splitlines():
        f = [x.strip() for x in line.split(' | ')]
        assert len(f) == 11, line
        sheets = [int(x) for x in re.findall(r'\d', f[6])]
        devs.append(dict(zip(DEV_HDR, f[:9] + [sources(f[9], sheets[:1] if len(sheets) == 1 else
                                                       sorted(set(sheets))), f[10]])))
    for line in WIRES.strip().splitlines():
        f = [x.strip() for x in line.split(' | ')]
        assert len(f) == 8, line
        sheet, col = f[0].split()
        (fd, ft), (td, tt) = end(f[1]), end(f[2])
        plc = next((t for d, t in ((fd, ft), (td, tt)) if d == 'PLC' and re.match(r'(IN|OUT)-', t)), '')
        conn = next(((d, t) for d, t in ((fd, ft), (td, tt)) if d == 'XC2'), ('', ''))
        note = f[7] + ('; ' + SH if 'SH' in f[6].split() else '')
        wires.append(dict(wire=f[4], from_device=fd, from_terminal=ft, to_device=td, to_terminal=tt,
                          signal=f[3], plc_address=plc, connector=conn[0], pin=conn[1], cable='',
                          sheet=sheet, column=col, evidence=f[5],
                          source_path=sources(f[6], [int(sheet)]), note=note))
    return devs, wires


def write(path, hdr, rows):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=hdr, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def onsite_key(r, dev=False):
    if dev:
        return '`%s`' % r['designation']
    a = (r['from_device'] + ' ' + r['from_terminal']).strip()
    b = (r['to_device'] + ' ' + r['to_terminal']).strip()
    return '`%s -> %s`' % (a, b)


def main():
    devs, wires = build()
    NET.mkdir(exist_ok=True)
    write(NET / 'control_devices.csv', DEV_HDR, devs)
    write(NET / 'control_wires.csv', WIRE_HDR, wires)
    bad = []
    # 1-2 headers and encoding
    for name, hdr in (('control_devices.csv', DEV_HDR), ('control_wires.csv', WIRE_HDR)):
        raw = (NET / name).read_bytes()
        if raw.startswith(b'\xef\xbb\xbf') or raw.decode('utf-8').split('\n', 1)[0] != ','.join(hdr):
            bad.append('header ' + name)
    # 3 one row per designation
    names = [d['designation'] for d in devs]
    bad += ['repeated designation ' + n for n in set(names) if names.count(n) > 1]
    # 4 one row per conductor; single terminals
    keys = {}
    for i, w in enumerate(wires):
        k = key((w['from_device'], w['from_terminal']), (w['to_device'], w['to_terminal']))
        if k in keys:
            bad.append('conductor twice: %s / line %d' % (sorted(k), i + 2))
        keys[k] = w
        for t in (w['from_terminal'], w['to_terminal']):
            if re.search(r'[/,;]| or ', t):
                bad.append('several terminals in one field: line %d' % (i + 2))
    # 6 evidence marks and sources
    have_src = (P / 'preparatory_data_analysis').is_dir()
    for r in devs + wires:
        if not MARK.match(r['evidence']):
            bad.append('mark: %r' % r['evidence'])
        if 'C:/' in ''.join(r.values()) or 'Users' in ''.join(r.values()):
            bad.append('absolute path in a row')
        if have_src:
            for p in r['source_path'].split('; '):
                if not (P / p).is_file():
                    bad.append('missing source ' + p)
        # 6b every stamp a note names is in the row's source_path
        for st in STAMP.findall(r['note']):
            if '_' + st + '.jpg' not in r['source_path']:
                rid = r.get('designation') or '%s:%s -> %s:%s' % (
                    r['from_device'], r['from_terminal'], r['to_device'], r['to_terminal'])
                bad.append('note names %s, source_path lacks it: %s' % (st, rid))
    # 18 dangling ends
    dset = set(names)
    for w in wires:
        for d in (w['from_device'], w['to_device']):
            if d not in dset:
                bad.append('dangling end ' + d)
    used = {w['from_device'] for w in wires} | {w['to_device'] for w in wires}
    bad += ['device without a wire: ' + n for n in names if n not in used]
    # 17 PLC addresses
    seen = {}
    for w in wires:
        a = w['plc_address']
        if not a:
            continue
        seen.setdefault(a, set()).add(w['signal'])
        if a in PLC_IO and w['signal'] != PLC_IO[a][1]:
            bad.append('PLC signal text ' + a)
    bad += ['PLC address on two signals: ' + a for a, s in seen.items() if len(s) > 1]
    bad += ['PLC address missing: ' + a for a in PLC_IO if a not in seen]
    # 19 agreement with thread power
    info = []
    if not have_src:
        info.append('preparatory_data_analysis/ absent: source-path check skipped')
    pw, pd = NET / 'power_wires.csv', NET / 'power_devices.csv'
    if pw.is_file() and pd.is_file():
        with open(pd, encoding='utf-8') as fh:
            pdev = {r['designation']: r for r in csv.DictReader(fh)}
        for d in devs:
            o = pdev.get(d['designation'])
            if o and (o['kind'] != d['kind'] or (o['place'] and o['place'] != d['place'])):
                bad.append('device differs from power_devices.csv: %s (%s/%s vs %s/%s)' % (
                    d['designation'], d['kind'], d['place'], o['kind'], o['place']))
            if o and not o['place'] and d['place']:
                info.append('place filled here, empty in power_devices.csv: ' + d['designation'])
        with open(pw, encoding='utf-8') as fh:
            prow = list(csv.DictReader(fh))
        pkeys = {key((r['from_device'], r['from_terminal']), (r['to_device'], r['to_terminal'])): r for r in prow}
        for k, w in keys.items():
            shared = SH in w['note']
            o = pkeys.get(k)
            if shared and not o:
                bad.append('marked shared but not in power_wires.csv: %s' % sorted(k))
            if o and not shared:
                bad.append('in power_wires.csv but not marked shared: %s' % sorted(k))
            if o and o['signal'] != w['signal']:
                bad.append('signal differs from power_wires.csv: %s %s/%s' % (sorted(k), w['signal'], o['signal']))
        # conductors of thread power that touch an end used here but are not shared
        ends = {(w['from_device'], w['from_terminal']) for w in wires} | {(w['to_device'], w['to_terminal']) for w in wires}
        mine = set(names) - {'UG50', 'QF1', 'X5', 'PE', 'UZ1', 'X11', 'PLC', 'TABLO', 'Q2', 'KM1A', 'KM1B', 'KM2', 'KM3', 'KM4', 'KM8', 'K1', 'X10'}
        for k, r in pkeys.items():
            if k in keys:
                continue
            for e in k:
                if e[0] in mine or (e in ends and e[0] not in ('X5', 'PE', 'UG50')):
                    info.append('power row touching sheets 4-7, not here: %s -> %s' % tuple(sorted(k)))
                    break
    else:
        info.append('power_*.csv absent: agreement check skipped')
    # 8 coverage of the paths tables
    if TAB.is_dir():
        n = 0
        for sh, fname in PATH_TABLES.items():
            with open(TAB / fname, encoding='utf-8') as fh:
                rows = list(csv.DictReader(fh))
            if len(rows) != len(COVER[sh]):
                bad.append('sheet %d: %d path rows, %d coverage entries' % (sh, len(rows), len(COVER[sh])))
            for i, cov in enumerate(COVER[sh]):
                n += 1
                if cov.startswith('text:'):
                    continue
                for c in cov.split('; '):
                    a, b = c.split('|')
                    if key(end(a), end(b)) not in keys:
                        bad.append('sheet %d path row %d: no wire %s' % (sh, i + 1, c))
        info.append('paths rows mapped: %d' % n)
    else:
        info.append('static_dynamic_memory/ absent: paths coverage skipped')
    # 33 on-site keys
    spec = S / 'spec' / 'control.md'
    open_rows = [onsite_key(d, True) for d in devs if d['evidence'] != 'sure'] + \
                [onsite_key(w) for w in wires if w['evidence'] != 'sure']
    if spec.is_file():
        # the keys must stand inside the section "## <n>. On-site list", not anywhere in the text
        m = re.search(r'^## \d+\. On-site list\n.*?(?=^## |\Z)', spec.read_text(encoding='utf-8'), re.M | re.S)
        if not m:
            bad.append('spec/control.md has no section "## <n>. On-site list"')
        else:
            miss = [k for k in open_rows if k not in m.group(0)]
            bad += ['on-site list lacks ' + k for k in miss]
            info.append('on-site keys in the on-site list of spec/control.md: %d of %d' % (len(open_rows) - len(miss), len(open_rows)))
    else:
        info.append('spec/control.md absent: on-site keys not checked')
    print('devices %d, wires %d, shared with power %d, open rows (on-site) %d' % (
        len(devs), len(wires), sum(SH in w['note'] for w in wires), len(open_rows)))
    for line in info:
        print('INFO', line)
    for line in bad:
        print('FAIL', line)
    print('result:', 'FAIL %d' % len(bad) if bad else 'PASS')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
