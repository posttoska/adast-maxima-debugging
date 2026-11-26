"""Thread t1 power: writes netlist/power_devices.csv and netlist/power_wires.csv
from set 568-70.9001 sheets 1-3, checked against the cabinet photos.
Run from anywhere:  python stage_2_electronics/schemes_2d/power_netlist.py
Source codes (expanded to paths relative to the project folder P):
 w=wiring set 20261113_, v=wiring set 20261114_, c=cabinet photos 20261102_,
 m=operating manual 20261115_, n=operating manual 20261114_, o=schemes_folder_1 20261103_,
 t=block tables (static_dynamic_memory/.../tables/<name>.csv).
The script stops with an error on a bad evidence mark, a missing source file or a dangling wire end.
The sources stay local: static_dynamic_memory/ and preparatory_data_analysis/ never go to GitHub. Where one
of them is absent (a clone), the checks that need it are skipped and the script prints a line saying so;
the CSV output is the same either way."""
import csv, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.normpath(os.path.join(HERE, '..', '..'))
NET = os.path.join(P, 'stage_2_electronics', 'netlist')
TAB = 'static_dynamic_memory/blocks/generation_002/artifacts/tables/'
PRE = {'w': 'preparatory_data_analysis/maxima_documents/adast_guillotine_wiring_and_plc_diagrams/20261113_{}.jpg',
       'v': 'preparatory_data_analysis/maxima_documents/adast_guillotine_wiring_and_plc_diagrams/20261114_{}.jpg',
       'c': 'preparatory_data_analysis/maxima_photos/20261102_{}.jpg',
       'm': 'preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/20261115_{}.jpg',
       'n': 'preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/20261114_{}.jpg',
       'o': 'preparatory_data_analysis/maxima_documents/schemes_folder_1/20261103_{}.jpg',
       't': TAB + '{}.csv'}


def src(codes):
    return '; '.join(PRE[c[0]].format(c[1:]) for c in codes.split())


S1 = 'w213049 w213216'          # sheet 1, table 1
S1B = 'w213049 w213530'         # sheet 1, tables 2 and 3
S1C = 'w213049 w213823'         # sheet 1, components table
S2 = 'w214644'                  # sheet 2, clean full view
S3 = 'w232117'                  # sheet 3

# designation, kind, function_en, term_cz_ru, type_rating, place, sheet, column, evidence, sources, note
D = [
 # --- sheet 1, table 1 (switches and controls); drawn on sheets 4-8 ---
 ('S30', 'sensor', 'clamp position sensor (top position)', 'SNÍMAČ POLOHY LISOVADLA (HORNÍ POLOHA)', '', 'machine', '1', '', 'sure', S1, 'sheet 1 table 1; drawn on sheets 6-8 (threads control, plc_drive)'),
 ('S28', 'sensor', 'clamp plate sensor', 'SNÍMAČ PLECHU LISOVADLA; red ink (RU) "– Д. пресса с пластиной"', '', 'machine', '1', '', 'sure', S1 + ' w192726', 'sheet 1 table 1; red ink quoted from the annotated copy, not print'),
 ('S27', 'reference switch', 'saddle position reference switch, rear position', 'REFERENČNÍ SPÍNAČ POLOHY SEDLA – ZADNÍ POLOHA', '', 'machine', '1', '', 'sure', S1, 'sheet 1 table 1; drawn on sheets 5-8'),
 ('S24', 'limit switch', 'saddle position limit switch, front position', 'KONCOVÝ SPÍNAČ POLOHY SEDLA – PŘEDNÍ POLOHA', '', 'machine', '1', '', 'sure', S1, 'sheet 1 table 1; drawn on sheets 5-8'),
 ('S19', 'switch', 'cut clutch switch (for knife change)', 'SPÍNAČ SPOJKY ŘEZU (PRO VÝMĚNU NOŽE); red ink (RU) "(у маховика)"', '', 'machine', '1', '', 'sure', S1 + ' w192726', 'sheet 1 table 1; drawn on sheet 5 (5:09)'),
 ('S12', 'sensor on cam', 'knife position sensor on the cam of the cutting mechanism', 'SNÍMAČE NA VAČCE ŘEZOVÉHO ÚSTROJÍ (POLOHA NOŽE)', '', 'machine', '1', '', 'sure', S1, 'sheet 1 table 1 group "S12, S13, S14"; via strip X8'),
 ('S13', 'sensor on cam', 'knife position sensor on the cam of the cutting mechanism', 'SNÍMAČE NA VAČCE ŘEZOVÉHO ÚSTROJÍ (POLOHA NOŽE)', '', 'machine', '1', '', 'sure', S1, 'sheet 1 table 1 group "S12, S13, S14"'),
 ('S14', 'sensor on cam', 'knife position sensor on the cam of the cutting mechanism', 'SNÍMAČE NA VAČCE ŘEZOVÉHO ÚSTROJÍ (POLOHA NOŽE)', '', 'machine', '1', '', 'sure', S1, 'sheet 1 table 1 group "S12, S13, S14"'),
 ('S10', 'pushbutton', 'cut start button', 'TLAČÍTKA SPOUŠTĚNÍ ŘEZU', '', 'machine', '1', '', 'sure', S1, 'sheet 1 table 1 group "S10, S11"; drawn on sheet 6'),
 ('S11', 'pushbutton', 'cut start button', 'TLAČÍTKA SPOUŠTĚNÍ ŘEZU', '', 'machine', '1', '', 'sure', S1, 'sheet 1 table 1 group "S10, S11"; drawn on sheet 6'),
 ('SQ1', 'sensor', 'knife lock sensor', 'SNÍMAČE ZAJIŠTĚNÍ NOŽE; red ink (RU) "(на оси стопора)"', '', 'machine', '1', '', 'sure', S1 + ' w192726', 'sheet 1 table 1 group "SQ1, SQ2"; via strip X8'),
 ('SQ2', 'sensor', 'knife lock sensor', 'SNÍMAČE ZAJIŠTĚNÍ NOŽE; red ink (RU) beside the group "(на оси стопора)"', '', 'machine', '1', '', 'sure', S1 + ' w192726', 'sheet 1 table 1 group "SQ1, SQ2"; via strip X8'),
 ('S5', 'limit switch', 'belt-pulley cover interlock', 'KONCOVÝ SPÍNAČ – BLOKOVÁNÍ KRYTU ŘEMENICE; red ink (RU) "(у маховика)"', '', 'machine', '1', '', 'sure', S1 + ' w192726', 'sheet 1 table 1; drawn on sheets 4-5'),
 ('S4', 'switch', 'air-cushion blower motor switch (energises KM8)', 'SPÍNAČ MOTORU VZDUCHOVÉHO POLŠTÁŘE', '', 'cabinet', '1', '', 'sure', S1 + ' c153000 c144344', 'sheet 1 table 1; drawn 4:12; contact block on the cabinet switch plate (photo), not the console'),
 ('S2', 'selector', 'work lighting / cut-line indication selector', 'PŘEPÍNAČ OSVĚTLENÍ – NÁZNAK ŘEZU', '', 'cabinet', '1', '', 'sure', S1 + ' c153000 c144344', 'sheet 1 table 1; drawn 4:01-05; contact block on the cabinet switch plate (photo)'),
 ('S1', 'emergency stop', 'emergency stop switch (only MS 115 PS, DS)', 'SPÍNAČ NOUZOVÉHO ZASTAVENÍ (POUZE MS 115 PS, DS)', '', 'console', '1', '', 'sure', S1 + ' c151739', 'sheet 1 table 1; drawn 4:10; contact block behind the console cover'),
 # --- sheet 1, table 2 (terminal strips and connectors) ---
 ('PE', 'earthing terminal strip', 'earthing (protective earth) strip: XC3 T1 X10 X11 XC7 UZ1', 'UZEMŇOVACÍ SVORKOVNICE', '6 terminals drawn (2:01-02); photo: 3 PE on row 3, 6 PE on row 7', 'cabinet', '2', '01-02', 'sure', S1B + ' w231506 c144214 c144309', 'sheet 1 prints the earth symbol in place of a designation; PE is our join key for that row'),
 ('X11', 'terminal strip', 'terminal strip in the cabinet: T1 tap links, FF1 feed', 'SVORKOVNICE V ROZVADĚČI', '1 2 3 4 + earth drawn; photo 6 terminals', 'cabinet', '3', '01', 'sure', S1B + ' ' + S3 + ' c144309', 'photo bridges 3-4, 5-6 and yellow 1-4 [?] vs print 1-2, 3-4 (on-site list)'),
 ('X10', 'terminal strip', 'terminal strip in the cabinet (1-6 to M1)', 'SVORKOVNICE V ROZVADĚČI', '45 terminals + 3 PE (photo)', 'cabinet', '2', '04-09', 'sure', S1B + ' w231128 c144309 c144314', 'also sheets 4-7'),
 ('X8', 'terminal strip', 'terminal strip of sensors S12, SQ1, SQ2', 'SVORKOVNICE SNÍMAČŮ S12,SQ1,SQ2', '', 'machine', '1', '', '[?]', S1B, 'sheet 1 table 2; not drawn on sheets 1-4; not seen in the cabinet; place [?]'),
 ('X5', 'terminal strip', 'working-earth strip: 0 V of all control supplies, bonded to PE', 'SVORKOVNICE PRAC. ZEMĚ', '17 terminals drawn; photo about 13', 'cabinet', '2', '02', 'sure', S1B + ' w231506 c144214', 'terminal count [?] (photo)'),
 ('XC7', 'socket', 'service socket 230 V (110 V), live with Q1 off', 'ZÁSUVKA 230V (110V)', 'photo: DIN-rail socket ZS 20, 10/16 A 250 V', 'cabinet', '2', '14-16', 'sure', S1B + ' w210815 c144214 m004236', 'fed upstream of Q1 via FA4 (OM p.12)'),
 ('XC4', 'connector', 'connector of sensor BR40 (encoder)', 'KONEKTOR SNÍMAČE BR40', '', 'cabinet', '1', '', '[?]', S1B, 'sheet 1 table 2; drawn on sheet 8 (thread plc_drive); label not seen'),
 ('XC3', 'connector', 'blower motor connector (M3; pins 5-6 Y3)', 'KONEKTOR MOTORU DMYCHADLA', 'pins 1 2 3 PE 5 6', 'cabinet', '2', '27-32', 'sure', S1B + ' w210838', 'cabinet machine-side wall; label not seen [?]'),
 ('XC2', 'connector', 'table-cabinet interconnection', 'PROPOJENÍ STŮL–ROZVADĚČ', '', 'cabinet', '1', '', '[?]', S1B, 'sheet 1 table 2; drawn on sheets 5-6 (thread control); label not seen'),
 ('XC1', 'connector', 'feed (saddle) motor connector (M2), shielded', 'KONEKTOR MOTORU POSUVU', 'pins 1 2 3 PE; cables on both sides shielded', 'cabinet', '2', '17-20', 'sure', S1B + ' w210838 w231229', 'cabinet machine-side wall'),
 ('XP', 'terminal strip', 'mains connection terminal strip', 'SVORKOVNICE PŘIPOJENÍ SÍTĚ', 'L1 L2 L3 two terminals each, N three bridged, PE; photo: 7 yellow L terminals, 3 blue N; cabinet door plate: Ue 400/230 V, f 50 Hz', 'cabinet', '2', '01', 'sure', S1B + ' w210810 c144214 c142805', 'markers L1: XP, L2: XP, L3: XP, N: XP (photo)'),
 ('XC50', 'connector', 'control-system connector (PLC analog outputs to UZ1 7, 8)', 'KONEKTORY ŘÍDÍCÍHO SYSTÉMU', '', 'cabinet', '2', '25-26', '[?]', S1B + ' w210838 c142944', 'photo: plug on PLC ANALOG OUTPUTS, no XC label'),
 ('XC60', 'connector', 'control-system connector (PLC side of the TABLO link)', 'KONEKTORY ŘÍDÍCÍHO SYSTÉMU', '', 'cabinet', '1', '', '[?]', S1B + ' c142944', 'sheet 1 table 2; drawn on sheet 8; photo: plug on IF1 RS232, no XC label'),
 ('XC70', 'connector', 'control-system connector (TABLO side)', 'KONEKTORY ŘÍDÍCÍHO SYSTÉMU', '', 'console', '1', '', '[?]', S1B, 'sheet 1 table 2; drawn on sheet 8 (thread plc_drive); not seen in any photo [?] (on-site list)'),
 # --- sheet 1, table 3 (variants) and sheets 2-3 ---
 ('M1', 'motor 3~ star-delta', 'knife drive and hydraulics motor', 'MOTOR PRO POHON NOŽE A HYDRAULIKY', '3x380V (380 V 50 Hz column); OM: 4 kW', 'machine', '2', '04-05', 'sure', S1B + ' w231128 n215113', 'kW from the OM p.7, not the 568'),
 ('M2', 'motor 3~', 'saddle (backgauge) feed motor', 'MOTOR PRO POSUV SEDLA', 'table 3x380V; fed by UZ1 3/AC 0-230 V; OM list: 550 W', 'machine', '2', '19', 'sure', S1B + ' w210838 c144201 m022802', 'conflict: table "3x380V" vs UZ1 output 0-230 V (on-site list)'),
 ('M3', 'motor 3~', 'air-cushion blower motor', 'MOTOR A ELEKTROMAGNET VZDUCHOVÉHO POLŠTÁŘE (DMYCHADLO)', '3x380V; OM list: 370 W', 'machine', '2', '28', 'sure', S1B + ' w210838 m022802', ''),
 ('QF1', 'motor circuit breaker 3-pole + aux 43-44', 'M1 protection; aux 43-44 in the control chain', 'jistič motoru', '568: 10-16A; photo: EP1-M10 6-10 A, aux 43-44 NO; OM: GV2-M14 6-10A', 'cabinet', '2', '07-10', 'sure', S1B + ' w231128 c144259 m023118', 'range differs 568 vs photo (on-site list); setting not read'),
 ('QF2', 'motor circuit breaker 3-pole', 'M3 protection', 'jistič motoru', '568: 1.6-2.5A; photo: EP1-M1.6 1-1.6 A; OM: GV2-M06 1-1,6A', 'cabinet', '2', '27-29', 'sure', S1B + ' w210838 c144255 m023118', 'range differs 568 vs photo (on-site list)'),
 ('FA1', 'circuit breaker 1-pole', 'T1 primary protection (from V)', 'jistič', '568: 12A; photo: GB2-CB20 12 A', 'cabinet', '3', '01', 'sure', S1B + ' ' + S3 + ' c144304', ''),
 ('FA2', 'circuit breaker 1-pole', 'T1 primary protection (from U)', 'jistič', '568: 12A; photo: GB2-CB20 12 A', 'cabinet', '3', '01', 'sure', S1B + ' ' + S3 + ' c144304', ''),
 ('FA3', 'circuit breaker 2-pole (L 1-2, N 3-4)', 'UZ1 supply', 'jistič', '568: 12A; photo: GB2-CD20 12 A', 'cabinet', '2', '18', 'sure', S1B + ' w210838 c144304 m022638', 'OM p.41 calls it "FA1"; dashed variant "FA3 A,B" (2:24-25) for 230 V mains: printed, not fitted on this 400 V machine, so kept out of power_wires.csv; drawn dashed on power_sheet2.svg from the VARIANT table of power_draw.py'),
 ('FA4', 'circuit breaker 1-pole', 'socket XC7 supply, upstream of Q1', 'jistič', '568: 6A; photo: GB2-CB12 6 A', 'cabinet', '2', '14', 'sure', S1B + ' w210815 c144220', 'live with Q1 off (warning triangle)'),
 ('KM1A', 'contactor', 'main contactor (in series with KM1B)', 'HLAVNÍ STYKAČE KM1A; KM1B', 'coil 24 V AC 50 Hz; photo: family EP1C093 [?]; OM: EP1-C123 B', 'cabinet', '2', '04', 'sure', S1B + ' w210810 c144255 c144247 m023118', 'coil 4:09; photo type read beside KM6 (c144247); aux 13-14 (photo 13KM1A x2)'),
 ('KM1B', 'contactor', 'main contactor (in series with KM1A)', 'HLAVNÍ STYKAČE KM1A; KM1B', 'coil 24 V AC 50 Hz; OM: EP1-C123 B', 'cabinet', '2', '06', 'sure', S1B + ' w210810 c144255 m023118', 'coil 4:11; drawn mirrored: in 2/4/6, out 1/3/5 to the bus'),
 ('KM2', 'contactor', 'M1 line contactor (U2 V2 W2)', 'STYKAČE MOTORU PRO POHON NOŽE A HYDRAULIKY', 'coil 50 Hz; OM: EP1-C123 B', 'cabinet', '2', '04-06', 'sure', S1B + ' w231128 c144247 m023118', 'coil 4:13'),
 ('KM3', 'contactor', 'M1 delta contactor (V1 W1 U1)', 'STYKAČE MOTORU PRO POHON NOŽE A HYDRAULIKY', 'coil 50 Hz; OM: EP1-C123 B', 'cabinet', '2', '07-09', 'sure', S1B + ' w231128 c144247 m023118', 'coil 4:14'),
 ('KM4', 'contactor', 'M1 star contactor (shorts X10 4-5-6)', 'STYKAČE MOTORU PRO POHON NOŽE A HYDRAULIKY', 'coil 50 Hz; OM: EP1-C099 B', 'cabinet', '2', '11-12', 'sure', S1B + ' w231128 c144247 m023118', 'coil 4:15'),
 ('KM6', 'contactor', 'cut clutch contactor', 'STYKAČE SPOJKY ŘEZU', 'coil 50 Hz; OM: EP1-C099 B', 'cabinet', '1', '', 'sure', S1B + ' m023118', 'sheet 1 table 3 row KM6-8; drawn on sheets 4-5 (thread control)'),
 ('KM7', 'contactor', 'cut clutch contactor', 'STYKAČE SPOJKY ŘEZU', 'coil 50 Hz; OM: EP1-C099 B', 'cabinet', '1', '', 'sure', S1B + ' m023118', 'sheet 1 table 3 row KM6-8; drawn on sheets 4-5 (thread control)'),
 ('KM8', 'contactor', 'blower (air cushion) motor contactor', 'STYKAČ MOTORU DMYCHADLA', 'coil 50 Hz; OM: EP1-C093 B', 'cabinet', '2', '27-29', 'sure', S1B + ' w210838 c144247 m023118', 'coil 4:12'),
 # --- sheet 1, components table ---
 ('C3', 'capacitor', 'suppression capacitor across Y3 (XC3 pins 5-6)', '', '2µ2/230V', 'machine', '2', '31-32', '[?]', S1C + ' w210838', 'drawn below XC3 beside Y3: machine side [?]; not the board silk C3 of UG50 (photo c144231)'),
 ('RC...', 'RC suppressors (group as printed)', 'coil suppressors of sheet 4 (RC1-RC8)', '', '2µ2 + 220R', 'cabinet', '1', '', 'sure', S1C, 'sheet-box 4 entry "RC..."; the single names RC1 RC2 RC3 RC4 RC6 RC7 RC8 are drawn on sheet 4 (thread control)'),
 ('V20', 'diode', 'free-wheel diode across the KT2 coil', '', '1N 4002', 'cabinet', '1', '', 'sure', S1C, 'sheet-box 4; drawn 4:20 (thread control)'),
 ('V01', 'diode', 'diode of sheet 5', '', '1N 4002', '', '1', '', '[?]', S1C + ' m023023', 'sheet-box 5 "V01, V14"; [?] because the type differs (568 1N 4002, OM list p.46 BY 399) and the place is not printed (at Y01 on the machine or at X10 18-19; on-site list, entry 8); name "V01" as printed, the OM list gives the same name; drawn on sheet 5 (thread control)'),
 ('V14', 'diode', 'diode of sheet 5 (the V14 printed on board UG50, sheet 3, is another part: UG50/V14)', '', '1N 4002', '', '1', '', 'sure', S1C, 'sheet-box 5; drawn on sheet 5 (thread control); bare name kept for this part, the board part is UG50/V14'),
 ('V10', 'Zener diodes', 'Zener diode pair of sheet 5 (across Y10)', '', '2x KZ 751', '', '1', '', 'sure', S1C, 'sheet-box 5; drawn on sheet 5 (thread control)'),
 ('R10', 'resistor', 'resistor of sheet 5 (across Y10)', '', '100R/6W', '', '1', '', 'sure', S1C, 'sheet-box 5; drawn on sheet 5 (thread control)'),
 ('RC11', 'RC suppressor', 'RC suppressor of sheet 5 (across Y11)', '', '2µ2 + 220R', '', '1', '', 'sure', S1C, 'sheet-box 5; drawn on sheet 5 (thread control)'),
 ('R14', 'resistor', 'series resistor of sheet 7 (Y14 supply; the R14 printed on board UG50, sheet 3, is another part: UG50/R14)', '', '11R/25W; OM 11R-25W', 'cabinet', '1', '', 'sure', S1C + ' c143202 m023314', 'sheet-box 7; red tube on a bolt in the cabinet (photo); drawn 7:07 (thread control); bare name kept for this part, the board part is UG50/R14'),
 ('V1', 'bridge rectifier', 'UG50 +27 V rectifier', '', 'PBU 802', 'cabinet', '3', '03', 'sure', S1C + ' ' + S3, 'on board UG50'),
 ('V2', 'bridge rectifier', 'UG50 +24 V rectifier', '', 'PBU 802', 'cabinet', '3', '03', 'sure', S1C + ' ' + S3, 'on board UG50'),
 ('V4', 'bridge rectifier', 'UG50 +33 V rectifier', '', 'CM2506 [?]', 'cabinet', '3', '03', '[?]', S1C + ' ' + S3, 'on board UG50; second letter M or W [?]'),
]
for i in range(11, 18):
    D.append(('UG50/V14' if i == 14 else 'V%d' % i, 'diode', 'fuse-output indicator diode, UG50', '', '1N 4002', 'cabinet', '3', '03',
              'sure', S1C + ' ' + S3, 'range "V11-V17" printed; not drawn (winding III has no fuse)' if i == 13 else
              'on board UG50; anti-parallel to V%d' % (i + 10) + ('; printed "V14" on board UG50 (sheet 3); qualified UG50/V14 because V14 of sheet-box 5 is another part' if i == 14 else '')))
for i in range(21, 28):
    D.append(('V%d' % i, 'LED', 'fuse-output indicator LED, UG50', '', 'TLUG 2400', 'cabinet', '3', '03',
              'sure', S1C + ' ' + S3, 'range "V21-V27" printed; not drawn (winding III has no fuse)' if i == 23 else 'on board UG50'))
D += [
 ('C1', 'electrolytic capacitor', '+27 V filter, UG50', '', '2200µF/50V', 'cabinet', '3', '03', 'sure', S1C + ' ' + S3, 'on board UG50'),
 ('C2', 'electrolytic capacitor', '+24 V filter, UG50', '', '2200µF/50V', 'cabinet', '3', '03', 'sure', S1C + ' ' + S3, 'on board UG50'),
 ('C4', 'electrolytic capacitor', '+33 V filter, UG50', '', '1000µF/63V', 'cabinet', '3', '03', '[?]', S1C + ' ' + S3 + ' c144231', 'photo: blue SAMWHA 4700µF 63V over the empty board places C3/C4, repair [?]'),
 ('R11', 'resistor', 'indicator resistor (V11, V21)', '', '1k5/0.6W', 'cabinet', '3', '03', 'sure', S1C + ' ' + S3, 'on board UG50'),
 ('R12', 'resistor', 'indicator resistor (V12, V22)', '', '1k5/0.6W', 'cabinet', '3', '03', 'sure', S1C + ' ' + S3, 'on board UG50'),
 ('UG50/R14', 'resistor', 'indicator resistor (UG50/V14, V24) on board UG50', '', '1k2/0.6W', 'cabinet', '3', '03', 'sure', S1C + ' ' + S3, 'printed "R14" on board UG50 (sheet 3); qualified UG50/R14 because R14 of sheet 7 (11R/25W) is another part: a join on designation cannot mix them'),
 ('R15', 'resistor', 'indicator resistor (V15, V25)', '', '1k2/0.6W', 'cabinet', '3', '03', 'sure', S1C + ' ' + S3, 'on board UG50'),
 ('R16', 'resistor', 'indicator resistor (V16, V26)', '', '3k3/W', 'cabinet', '3', '03', '[?]', S1C + ' ' + S3, 'on board UG50; wattage digit missing in print'),
 ('R17', 'resistor', 'indicator resistor (V17, V27)', '', '3k3/W', 'cabinet', '3', '03', '[?]', S1C + ' ' + S3, 'on board UG50; wattage digit missing in print'),
 ('FU21', 'fuse', 'winding I fuse (+27 V)', '', '6.3A', 'cabinet', '3', '03', 'sure', S3, 'on board UG50'),
 ('FU22', 'fuse', 'winding II fuse (+24 V)', '', '3.15A', 'cabinet', '3', '03', 'sure', S3, 'on board UG50'),
 ('FU24', 'fuse', 'winding IV fuse (+33 V)', '', 'T4A', 'cabinet', '3', '03', 'sure', S3, 'on board UG50'),
 ('FU25', 'fuse', 'winding V fuse (~24 V)', '', '4A', 'cabinet', '3', '03', 'sure', S3, 'on board UG50'),
 ('FU26', 'fuse', 'winding VI fuse (~48 V, output 18)', '', '2A', 'cabinet', '3', '03', 'sure', S3, 'on board UG50'),
 ('FU27', 'fuse', 'winding VI fuse (~48 V, output 19 to Y3)', '', '2A', 'cabinet', '3', '03', 'sure', S3, 'on board UG50'),
 # --- drawn on sheets 2-3, not in the sheet-1 tables ---
 ('Q1', 'main switch 3-pole', 'main switch, positions 0/1', 'HLAVNÍ VYPÍNAČ', 'photo: UL General Use 25 A 600 V AC', 'cabinet', '2', '02-03', 'sure', 'w210810 c144340', 'body on the cabinet switch plate (front face), handle outside'),
 ('Q2', 'rotary cam switch', 'M1 run switch; contacts 1-2..7-8 closed in 0, 9-10 closed in 1', '', 'photo: 16 A 660 V AC, IEC 947-3', 'cabinet', '2', '01-02', 'sure', 'w231128 w210810 c144344', 'contact table 2:01-02 (LINIE 4:08 4:17 5:09 6:14 4:16); contacts drawn on sheets 4-6'),
 ('ZF1', 'mains interference filter', 'filter on the supply side of Q1 (live with Q1 off)', '', 'L1 L2 L3 N PE; photo: brown box, type not read', 'cabinet', '2', '01', 'sure', 'w210810 c144214 m004236', 'type [?]'),
 ('ZF2', 'single-phase mains filter', 'UZ1 input filter', 'SÍŤ N L / SPOTŘEBIČ 1N 1L (photo label)', 'round, about 5-6 cm', 'cabinet', '2', '18', 'sure', 'w210815 c143806', ''),
 ('X2', 'terminal block', 'N and L between FA3 and ZF2', '', 'photo: 3-pole block PE N L marked 400V', 'cabinet', '2', '18', 'sure', 'w210815 c143806', 'not in the sheet-1 tables; PE seen in photo only'),
 ('UZ1', 'frequency inverter', 'M2 feed drive', 'MĚNIČ', 'Lenze EVF8202-E-V002; in 1/N/PE AC 230 V 9.0 A; out 3/AC 0-230 V 4.0 A 0.75 kW', 'cabinet', '2', '17-26', 'sure', 'w210838 w231229 c144201 c144205', '+UG/-UG unwired [?] (c144205); type not printed on the 568; top edge as printed (w231229): N, L, two unlabeled circles (shield terminals in the paths table of sheet 2; the 3rd takes the UZ1-XC1 cable shield, the 4th the earth of ZF2), then the earth terminal PE (on-site list, entry 21)'),
 ('T1', 'control transformer', 'supply transformer: primary taps -40V -20V 0V 20V 230V 400V, secondaries I-VI', 'TRANSFORMÁTOR T1', 'I 21V 120VA; II 19V 50VA; III unused; IV 24V 120VA; V 24V 100VA; VI 48V 180VA; OM JOC-U 4056-130', 'cabinet', '3', '02', 'sure', S3 + ' w231949 c144220 m023314', 'on the cabinet floor; no plate seen; tap table 200V 20-230, 230V 0-230, 380V 20-400, 400V 0-400, 415V 0-415 (no 415 tap drawn)'),
 ('UG50', 'power-supply board', 'rectified and AC control supplies +27V +24V +33V ~24V ~48V', 'PLOŠNÝ SPOJ SE ZDROJI UG50', 'terminals 1-32', 'cabinet', '3', '03-04', 'sure', S3 + ' c144227 c144231', 'outputs 3, 8, 9, 15, 16 drawn without destination'),
 ('FF1', 'light curtain (option)', 'consumer fed ~230 V from T1 via X11 (dashed); light curtain per OM', 'FF1; RU "предохранительная диафрагма"', '~230 V', 'machine', '3', '01', '[?]', S3 + ' m004647 w195028', 'drawn dashed, no cross-reference; certificate "—", not seen in photos: printed option, not fitted [?]; its three dashed feeds (X11 3, X11 1, X11 earth) kept out of power_wires.csv, drawn dashed on power_sheet3.svg from the OPTION table of power_draw.py'),
 ('K1', 'auxiliary relay', 'switches ~48 V to Y3', '', 'photo: F. Lütze relay, 1 changeover 11-12-14; OM: RE6-0011', 'cabinet', '2', '30-31', 'sure', 'w210838 w231229 c144324 m023118', 'coil 5:15; print contact 13-14, hand "11" over "13" on the clean copy; photo markers 11K1 14K1'),
 ('Y3', 'electromagnet ~48 V', 'air-cushion electromagnet (valve)', 'ELEKTROMAGNET VZDUCHOVÉHO POLŠTÁŘE', '~48 V AC', 'machine', '2', '31-32', 'sure', 'w210838 m022721', 'OM p.42 says Y3 is controlled by UZ1 (conflict; 568 rules: K1 at ~48 V)'),
]

# from_dev, from_term, to_dev, to_term, signal, plc_address, connector, pin, sheet, column, evidence, sources, note
W = []
def w(*r):
    W.append(r)

for ph in ('L1', 'L2', 'L3'):
    w('XP', ph, 'Q1', ph, ph, '', '', '', '2', '01-02', 'sure', S2 + ' w210810 c144214', 'mains feed')
for ph in ('L1', 'L2', 'L3', 'N'):
    w('XP', ph, 'ZF1', ph, ph, '', '', '', '2', '01', 'sure', S2 + ' w210810', 'ZF1 on the supply side of Q1: live with Q1 off')
w('ZF1', 'PE', 'PE', '', 'PE', '', '', '', '2', '01', 'sure', S2 + ' w210810', 'earth symbol at ZF1')
w('XP', 'L3', 'FA4', '1', 'L3', '', '', '', '2', '01-14', 'sure', S2 + ' w210810 w210815', '"1FA4 (2:14)"; upstream of Q1: live with Q1 off')
w('XP', 'N', 'FA3', '3', 'N', '', '', '', '2', '01-18', 'sure', S2 + ' w210810 w210815 c144304', '"3FA3 (2:18)"; photo marker 3FA3')
w('XP', 'N', 'XC7', 'N', 'N', '', '', '', '2', '01-16', 'sure', S2 + ' w210815', '"N (2:01)" at 2:16')
w('XP', 'PE', 'PE', '', 'PE', '', '', '', '2', '01', 'sure', S2 + ' w231506', 'main earth terminal to the earthing strip')
w('PE', '', 'X5', '', 'PE', '', '', '', '2', '02', 'sure', S2 + ' w231506', 'working earth bonded to PE')
for dev in ('XC3', 'T1', 'X10', 'X11', 'XC7', 'UZ1'):
    w('PE', '', dev, 'PE', 'PE', '', '', '', '2', '01-02', 'sure', S2 + ' w231128', 'earthing strip list')
X5L = [('K1', 'A2', 'w212711', 'K1 coil return (5:15)'), ('KM1A', 'A2', 'w232949', 'KM1A coil return (4:09)'), ('XC3', '6', 'w210838', 'Y3 return'),
       ('UG50', '4', S3, '+27V return; also 3:04'), ('UG50', '7', S3, '+24V return; also 3:04'),
       ('UG50', '9', S3, 'CONFLICT: sheet 3 draws UG50 8 and 9 unused; no 9UG50 marker in photo c144227'),
       ('UG50', '11', S3, '+33V return; also 3:04'), ('UG50', '17', S3, '~24V return; also 3:04'),
       ('UG50', '20', S3, '~48V return; also 3:04'), ('X10', '12', 'w232949', 'lighting return (4:03)'),
       ('X10', '19', 'w212623', 'Y01 return (5:02)'), ('X10', '21', 'w212623', 'Y14 return (5:04)'),
       ('X10', '23', 'w212623', 'Y11 return (5:07)'),
       ('X10', '28', 'w212623', 'Y10 return (5:10); full-resolution crop reads 28X10 (table row said 26X10)'),
       ('BMR1', '0V', 'w193629', 'BMR1 supply 0V (7:12)'), ('PLC', 'GND', 'v015117', 'PLC supply 0V (8:03); sheet 8 table says 2:01'),
       ('TABLO', '-', 'v015721', 'TABLO supply 0V (8:03-04)')]
for dev, term, s, note in X5L:
    ev = '[?]' if term == '9' and dev == 'UG50' else 'sure'
    w('X5', '', dev, term, '0V', 'GND PLC' if dev == 'PLC' else '', '', '', '2', '02', ev,
      S2 + ' w231128 ' + s + (' c144227' if dev == 'UG50' else ''), 'X5 list at 2:02; ' + note)
for a, b, ph in (('U', '1', 'L1'), ('V', '3', 'L2'), ('W', '5', 'L3')):
    w('Q1', a, 'KM1A', b, ph, '', '', '', '2', '02-04', 'sure', S2 + ' w210810 c144340 c144255', 'photo markers U: Q1, W: Q1')
w('KM1A', '1', 'FA2', '1', 'L1 (U)', '', '', '', '2', '03', 'sure', S2 + ' ' + S3 + ' c144255 c144304', 'T1 feed taken before the main contactors; print: junction on U (2:03) to "1FA2 (3:01)"; photo: second wire on KM1A 1')
w('KM1A', '3', 'FA1', '1', 'L2 (V)', '', '', '', '2', '03', 'sure', S2 + ' ' + S3 + ' c144255 c144304', 'print: junction on V (2:03) to "1FA1 (3:01)"; photo: second wire on KM1A 3')
for a, b, ph in (('2', '2', 'L1'), ('4', '4', 'L2'), ('6', '6', 'L3')):
    w('KM1A', a, 'KM1B', b, ph, '', '', '', '2', '04-06', 'sure', S2 + ' w210810', 'main contactors in series; KM1B drawn mirrored')
for dev, col in (('QF1', '06-07'), ('QF2', '06-27')):
    for a, ph in (('1', 'L1'), ('3', 'L2'), ('5', 'L3')):
        w('KM1B', a, dev, a, ph, '', '', '', '2', col, 'sure', S2 + ' w210810 w210838', 'bus L1-L3 after KM1B; daisy chain order not seen')
w('KM1B', '5', 'FA3', '1', 'L3', '', '', '', '2', '06-18', 'sure', S2 + ' w210838 c144304', 'bus L3 to the UZ1 supply; photo marker 1FA3')
for dev, col in (('KM2', '07-04'), ('KM3', '07-09')):
    for a, b, ph in (('2', '1', 'L1'), ('4', '3', 'L2'), ('6', '5', 'L3')):
        w('QF1', a, dev, b, ph, '', '', '', '2', col, 'sure', S2 + ' w231128', 'KM2 and KM3 in parallel after QF1')
for a, b, ph in (('2', '1', 'U2'), ('4', '2', 'V2'), ('6', '3', 'W2')):
    w('KM2', a, 'X10', b, ph, '', '', '', '2', '04-06', 'sure', S2 + ' w231128', 'M1 line')
for a, b, ph in (('2', '4', 'V1'), ('4', '5', 'W1'), ('6', '6', 'U1')):
    w('KM3', a, 'X10', b, ph, '', '', '', '2', '07-09', 'sure', S2 + ' w231128', 'M1 delta')
KM4N = '; photo markers 1KM4 3KM4 5KM4 5KM4 (top) 6KM4 (bottom) suggest a 3-pole star bridge (on-site list)'
w('X10', '6', 'KM4', '1', 'U1', '', '', '', '2', '11-12', '[?]', S2 + ' w231128 c144247', 'star point: KM4 1 and 3 bridged to the X10 6 line' + KM4N)
w('KM4', '1', 'KM4', '3', 'U1', '', '', '', '2', '11-12', '[?]', S2 + ' w231128 c144247', 'bridge 1-3 as drawn' + KM4N)
w('KM4', '2', 'X10', '4', 'V1', '', '', '', '2', '11-12', '[?]', S2 + ' w231128 c144247', 'shorts X10 4-5-6 when KM4 closes' + KM4N)
w('KM4', '4', 'X10', '5', 'W1', '', '', '', '2', '11-12', '[?]', S2 + ' w231128 c144247', 'shorts X10 4-5-6 when KM4 closes' + KM4N)
for a, b in (('1', 'U2'), ('2', 'V2'), ('3', 'W2'), ('4', 'V1'), ('5', 'W1'), ('6', 'U1'), ('PE', 'PE')):
    w('X10', a, 'M1', b, b, '', '', '', '2', '04-09', 'sure', S2 + ' w231128', 'field cable to M1 (bundle B4 of the 3D thread); crop sheet2_col04-09_M1_terminal_pairing')
w('UG50', '13', 'QF1', '43', '~24V', '', '', '', '3', '04', 'sure', S3 + ' w232949 c144259', 'arrow "4:01"; far end per sheet 4 col 10 (T/11_568_sheet4_paths.csv)')
w('QF1', '44', 'BMR1', '19', '~24V', '', '', '', '2', '10', 'sure', S2 + ' w232949 w193629 c144259', 'aux 43-44 "(4:10)"; far end per sheet 7 col 01; the second 44QF1 wire feeds the sheet-4 control bus (thread control)')
w('FA4', '2', 'XC7', 'L', 'L3', '', '', '', '2', '14-16', 'sure', S2 + ' w210815 c144214', 'socket live with Q1 off')
w('FA3', '2', 'X2', 'L', 'L3', '', '', '', '2', '18', 'sure', S2 + ' w210815 c144304', '')
w('FA3', '4', 'X2', 'N', 'N', '', '', '', '2', '18', 'sure', S2 + ' w210815 c144304', '')
for t in ('L', 'N'):
    w('X2', t, 'ZF2', t, t, '', '', '', '2', '18', 'sure', S2 + ' w210815 c143806', 'photo markers N: ZF2, L: ZF2')
w('X2', 'PE', 'ZF2', 'PE', 'PE', '', '', '', '2', '18', 'sure', 'c143806', 'seen in photo only (green-yellow); 568 draws X2 with N L')
w('ZF2', 'PE', 'UZ1', 'PE', 'PE', '', '', '', '2', '18-20', '[?]', S2 + ' w210838', 'printed earth of ZF2 to UZ1; it lands on the 4th circle of the UZ1 top edge (unlabeled; a shield terminal in the paths table of sheet 2), beside the earth terminal: taken as UZ1 PE [?] (on-site list, entry 21)')
for t in ('L', 'N'):
    w('ZF2', '1' + t, 'UZ1', t, t, '', '', '', '2', '18', 'sure', S2 + ' w210815', 'filtered side (SPOTŘEBIČ)')
for i, t in enumerate(('U', 'V', 'W')):
    w('UZ1', t, 'XC1', str(i + 1), 'M2 ' + t, '', 'XC1', str(i + 1), '2', '17-20', 'sure', S2 + ' w210838', 'shielded cable')
    w('XC1', str(i + 1), 'M2', t + '1', 'M2 ' + t, '', 'XC1', str(i + 1), '2', '17-20', 'sure', S2 + ' w210838', 'shielded field cable (bundle B3)')
w('UZ1', 'PE', 'XC1', 'PE', 'PE', '', 'XC1', 'PE', '2', '17-20', 'sure', S2 + ' w210838 w231229', 'from the earth terminal of UZ1 (5th circle of its top edge, earth symbol) to the XC1 earth pin; the UZ1-XC1 cable shield ends on the 3rd circle (unlabeled), not on this terminal (print)')
w('XC1', 'PE', 'M2', 'PE', 'PE', '', 'XC1', 'PE', '2', '17-20', 'sure', S2 + ' w210838 w231229', 'the XC1-M2 cable shield joins this earth line at a dot (print) (bundle B3)')
PIO = ' t12_568_plc_io w191800'
w('UZ1', '39', 'PLC', 'GND', 'inverter digital ground (UZ1 - GND)', 'OUT-GND', '', '', '2', '21', 'sure', S2 + ' w231229' + PIO, 'shielded control cable; print "PLC GND (8:02-8:05)"')
w('PLC', 'OUT-B', 'UZ1', 'E3', 'backgauge feed forward (POSUV VPŘED)', 'OUT-B', '', '', '2', '22', 'estimated ±1 column', S2 + ' w231229' + PIO, 'print "PLC OUT B (8:02-8:05)"; photo marker E3: UZ1 [?]')
w('PLC', 'OUT-C', 'UZ1', 'E4', 'backgauge feed backward (POSUV VZAD)', 'OUT-C', '', '', '2', '23', 'estimated ±1 column', S2 + ' w231229' + PIO, 'print "PLC OUT C (8:02-8:05)"; photo marker E4: UZ1')
w('PLC', 'OUT-D', 'UZ1', '28', 'inverter UZ1 blocking (enable input 28) (BLOKOVÁNÍ UZ1)', 'OUT-D', '', '', '2', '24', 'estimated ±1 column', S2 + ' w231229' + PIO, 'print "PLC OUT D (8:02-8:05)"')
w('UZ1', '7', 'XC50', '6+9', 'backgauge speed control (ŘÍZENÍ RYCHLOSTI SEDLA)', '', 'XC50', '6+9', '2', '25', 'estimated ±1 column', S2 + ' w231229' + PIO, 'shielded pair (photo: 7, 8 red/grey)')
w('UZ1', '8', 'XC50', '4', 'backgauge speed control (ŘÍZENÍ RYCHLOSTI SEDLA)', '', 'XC50', '4', '2', '26', 'estimated ±1 column', S2 + ' w231229' + PIO, 'shielded pair')
w('UZ1', 'K12', 'PLC', 'IN-8', 'drive (inverter UZ1) function signal (SIGNÁL FUNKCE POHONU)', 'IN-8', '', '', '2', '25', 'sure', S2 + ' w231229' + PIO, 'print "PLC IN-8 (8:02)"; K12/K14 hand-lettered on the clean copy (print); photo marker K12: UZ1')
w('X10', '34', 'UZ1', 'K14', '+24V', '', '', '', '2', '26', 'sure', S2 + ' w231229 w194606 c144205', '"34X10 (6:16)"; photo marker K14: UZ1')
# The dashed variant "FA3 A,B" (2:24-25, 230 V mains) is printed but not fitted: not in this netlist
# (it would tie ZF2 N to L2); power_draw.py draws it dashed from its own VARIANT table.
for a, b, ph in (('2', '1', 'L1'), ('4', '3', 'L2'), ('6', '5', 'L3')):
    w('QF2', a, 'KM8', b, ph, '', '', '', '2', '27-29', 'sure', S2 + ' w210838 c144247', '')
for a, b in (('2', '1'), ('4', '2'), ('6', '3')):
    w('KM8', a, 'XC3', b, 'M3', '', 'XC3', b, '2', '27-29', 'sure', S2 + ' w210838 c144247', 'photo markers 2KM8 4KM8 6KM8')
for a, b in (('1', 'U1'), ('2', 'V1'), ('3', 'W1'), ('PE', 'PE')):
    w('XC3', a, 'M3', b, 'M3', '', 'XC3', a, '2', '28', 'sure', S2 + ' w210838', 'field cable (bundle B3)')
w('XC3', 'PE', 'Y3', 'PE', 'PE', '', 'XC3', 'PE', '2', '30-31', 'sure', S2 + ' w210838', 'earth of Y3, joined at a dot with the earth of M3 below the XC3 earth pin (print)')
w('UG50', '19', 'K1', '11', '~48V', '', '', '', '2', '30', 'sure', S2 + ' ' + S3 + ' w231229 c144324', 'print K1 13; hand "11" over "13" on the clean copy; photo markers 11K1 14K1 (photo rules); arrow "2:30" on sheet 3')
w('K1', '14', 'XC3', '5', '~48V', '', 'XC3', '5', '2', '31', 'sure', S2 + ' w210838 c144324', '')
END = 'end names 1/2 not printed (naming rule of spec/power.md: 1 = end at XC3 5, 2 = end at XC3 6)'
w('XC3', '5', 'Y3', '1', '~48V', '', 'XC3', '5', '2', '31-32', 'sure', S2 + ' w210838', 'Y3 coil end; ' + END)
w('Y3', '2', 'XC3', '6', '0V', '', 'XC3', '6', '2', '31-32', 'sure', S2 + ' w210838', 'Y3 other coil end; XC3 6 to X5; ' + END)
w('XC3', '5', 'C3', '1', '~48V', '', 'XC3', '5', '2', '31-32', '[?]', S2 + ' w210838', 'C3 across Y3, drawn below XC3 (machine side [?]); ' + END)
w('C3', '2', 'XC3', '6', '0V', '', 'XC3', '6', '2', '31-32', '[?]', S2 + ' w210838', 'C3 across Y3, drawn below XC3 (machine side [?]); ' + END)
# --- sheet 3 ---
w('FA1', '2', 'X11', '2', 'L2', '', '', '', '3', '01', 'sure', S3 + ' c144309', 'photo marker 2X11')
w('X11', '2', 'X11', '1', 'L2', '', '', '', '3', '01', '[?]', S3 + ' c144309', 'bridge 1-2 as drawn; photo bridges 3-4, 5-6, yellow 1-4 [?] (on-site list)')
w('X11', '1', 'T1', '0V', 'L2', '', '', '', '3', '01-02', 'sure', S3, 'tap 0V (400 V mains)')
w('FA2', '2', 'T1', '400V', 'L1', '', '', '', '3', '01-02', 'sure', S3 + ' c144304', 'tap 400V (400 V mains)')
w('T1', '230V', 'X11', '3', '~230V', '', '', '', '3', '01-02', 'sure', S3 + ' c144309', 'photo marker 3X11')
w('X11', '3', 'X11', '4', '~230V', '', '', '', '3', '01', '[?]', S3 + ' c144309', 'bridge 3-4 as drawn; photo bridges 3-4, 5-6, yellow 1-4 [?] (on-site list)')
# FF1's three dashed feeds (X11 3, X11 1, X11 earth) are a printed option, not fitted (certificate "—"):
# not in this netlist; power_draw.py draws them dashed from its own OPTION table.
for wd, hi, t1, t2, va in (('I', '21V', '21', '22', '120VA'), ('II', '19V', '23', '24', '50VA'), ('IV', '24V', '27', '28', '120VA'),
                           ('V', '24V', '29', '30', '100VA'), ('VI', '48V', '31', '32', '180VA')):
    w('T1', wd + ' ' + hi, 'UG50', t1, '~' + hi, '', '', '', '3', '02-03', 'sure', S3 + ' c144220 c144231', 'winding ' + wd + ' ' + va + '; photo markers on T1 and UG50')
    w('T1', wd + ' 0V', 'UG50', t2, '0V', '', '', '', '3', '02-03', 'sure', S3 + ' c144220 c144231', 'winding ' + wd + ' ' + va)
# --- inside board UG50 (sheet 3, col 03): every printed connection, one row per conductor.
# End names are not printed; naming rule (spec/power.md): fuse, resistor, indicator diode and LED:
# 1 = upper or left end as drawn, 2 = lower or right end (no polarity claimed for V11-V27);
# bridge: ~1 upper AC input, ~2 lower AC input, + and - as printed; capacitor + and - (+ printed).
BRD = 'printed trace inside board UG50; end names by the naming rule of spec/power.md (not printed)'
REP = '; board repaired: blue SAMWHA 4700µF 63V over the empty places C3/C4 (c144231), real wiring [?]'


def brd(fd, ft, td, tt, sig, col='03', ev='sure', s=S3, note=''):
    w(fd, ft, td, tt, sig, '', '', '', '3', col, ev, s, BRD + note)


def indicator(fuse, d, led, r, zero):
    for x in (d, led):
        brd(fuse, '2', x, '1', 'indicator')
        brd(x, '2', r, '1', 'indicator')
    brd(r, '2', 'UG50', zero, '0V')


for sig, tin, t0, fuse, br, cap, d, led, r, plus, outs, minus in (
        ('~21V', '21', '22', 'FU21', 'V1', 'C1', 'V11', 'V21', 'R11', '+27V', ('1', '2', '3'), '4'),
        ('~19V', '23', '24', 'FU22', 'V2', 'C2', 'V12', 'V22', 'R12', '+24V', ('5', '6'), '7'),
        ('~24V', '27', '28', 'FU24', 'V4', 'C4', 'UG50/V14', 'V24', 'UG50/R14', '+33V', ('10',), '11')):
    brd('UG50', tin, fuse, '1', sig)
    brd(fuse, '2', br, '~1', sig)
    indicator(fuse, d, led, r, t0)
    brd('UG50', t0, br, '~2', '0V')
    ev, s, n = ('[?]', S3 + ' c144231', REP) if cap == 'C4' else ('sure', S3, '')
    brd(br, '+', cap, '+', plus, ev=ev, s=s, note=n)
    for o in outs:
        brd(cap, '+', 'UG50', o, plus, '03-04', ev, s, n)
    brd(br, '-', cap, '-', '0V', ev=ev, s=s, note=n)
    brd(cap, '-', 'UG50', minus, '0V', '03-04', ev, s, n)
brd('UG50', '29', 'FU25', '1', '~24V')                     # winding V: ~24 V AC, outputs 12 13 14 bridged
for o in ('12', '13', '14'):
    brd('FU25', '2', 'UG50', o, '~24V', '03-04', note='; outputs 12 13 14 bridged')
indicator('FU25', 'V15', 'V25', 'R15', '30')
brd('UG50', '30', 'UG50', '17', '0V', '03-04')
for fuse, o, d, led, r in (('FU26', '18', 'V16', 'V26', 'R16'), ('FU27', '19', 'V17', 'V27', 'R17')):
    brd('UG50', '31', fuse, '1', '~48V')                   # winding VI: two fuses from 31
    brd(fuse, '2', 'UG50', o, '~48V', '03-04')
    indicator(fuse, d, led, r, '32')
brd('UG50', '32', 'UG50', '20', '0V', '03-04')
OUT = [('1', 'BMR1', '21', '+27V', '7:03', 'w193629', 'sheet 7 col 03', ''),
       ('2', 'R14', '1', '+27V', '7:07', 'w193629', 'sheet 7 col 07', 'to R14 of sheet 7 (11R/25W), not the board part UG50/R14; R14 end names not printed: 1 = this 2UG50 end, 2 = the BMR1 25 end (naming rule, spec/power.md)'),
       ('5', 'X10', '36', '+24V', '6:18', 'w194606', 'sheet 6 col 18', ''),
       ('6', 'KM6', '1', '+24V', '4:20', 'w233009', 'sheet 4 col 20', 'then KT2 1'),
       ('10', 'KM6', '5', '+33V', '5:10', 'w212623', 'sheet 5 col 10', 'the +33V node also feeds Q2 5 (5:09)'),
       ('12', 'S2', '3A', '~24V', '4:01', 'w232949', 'sheet 4 col 01', 'S2 3A and 4B joined (lighting)'),
       ('14', 'BMR1', '27', '~24V', '7:09', 'w193629', 'sheet 7 col 09', ''),
       ('18', 'KM6', '3', '~48V', '5:07', 'w212623', 'sheet 5 col 07', 'then X10 22, Y11')]
for t, dev, term, sig, arrow, s, where, note in OUT:
    w('UG50', t, dev, term, sig, '', '', '', '3', '04', 'sure', S3 + ' ' + s + ' c144227',
      'arrow "%s"; far end per %s (T/1x_568 paths table)%s' % (arrow, where, '; ' + note if note else ''))

DH = 'designation,kind,function_en,term_cz_ru,type_rating,place,sheet,column,evidence,source_path,note'.split(',')
WH = 'wire,from_device,from_terminal,to_device,to_terminal,signal,plc_address,connector,pin,cable,sheet,column,evidence,source_path,note'.split(',')
EV = re.compile(r'^(sure|\[\?\]|W|estimated ±.+)$')


def check_and_write():
    bad = []
    dev_rows = [dict(zip(DH, r[:8] + (r[8], src(r[9]), r[10]))) for r in D]
    wire_rows = []
    for r in W:
        fd, ft, td, tt, sig, pa, con, pin, sh, col, ev, s, note = r
        wire_rows.append(dict(zip(WH, ('', fd, ft, td, tt, sig, pa, con, pin, '', sh, col, ev, src(s), note))))
    names = {}
    for d in dev_rows:
        names.setdefault(d['designation'], []).append(d['sheet'])
    for n, sheets in names.items():                  # the R14/V14 clashes are qualified (UG50/R14, UG50/V14)
        if len(sheets) > 1:
            bad.append('repeated designation ' + n)
    for r in W:                                      # an unnamed end on both sides of a part would merge two nets
        for d, t in ((r[0], r[1]), (r[2], r[3])):    # any unnamed end, also one whose other wire is another thread's
            if t == '' and d not in ('PE', 'X5'):    # only the earth bars PE and X5 are one node each
                bad.append('unnamed terminal %s' % d)
    absent = [a for a in ('preparatory_data_analysis', 'static_dynamic_memory')   # local only: absent in a clone
              if not os.path.isdir(os.path.join(P, a))]
    allowed_far = None if 'static_dynamic_memory' in absent else set()   # None: far ends cannot be checked
    if allowed_far is not None:
        for f in ('11_568_devices', '11_568_sheet4_paths', '12_568_sheet5_paths', '12_568_sheet6_paths',
                  '12_568_sheet7_paths', '12_568_sheet8_paths'):
            with open(os.path.join(P, TAB + f + '.csv'), encoding='utf-8') as fh:
                allowed_far |= set(re.findall(r'[A-Z][A-Z0-9]*', fh.read()))
    n_paths = n_skip = 0
    for kind, rows in (('device', dev_rows), ('wire', wire_rows)):
        for r in rows:
            if not EV.match(r['evidence']):
                bad.append('%s evidence %r' % (kind, r['evidence']))
            for p in r['source_path'].split('; '):
                n_paths += 1
                if p.split('/')[0] in absent:
                    n_skip += 1
                elif not os.path.exists(os.path.join(P, p)):
                    bad.append('%s missing source %s' % (kind, p))
            if re.search(r'[A-Za-z]:[\\/]+Users', ''.join(r.values())):
                bad.append('user path')
            if kind == 'device' and r['place'] not in ('cabinet', 'console', 'machine', ''):
                bad.append('place ' + r['place'])
    for r in wire_rows:
        for end in ('from_device', 'to_device'):
            d = r[end]
            if d not in names and allowed_far is not None and d not in allowed_far:
                bad.append('dangling %s %s' % (end, d))
            if d not in names:
                r['note'] = (r['note'] + '; ' if r['note'] else '') + d + ' is a device of another thread'
        for t in ('from_terminal', 'to_terminal'):
            if ' ' in r[t].strip() and not re.match(r'^(I|II|IV|V|VI) (\d+V|0V)$|^[AB] [12]$', r[t]):
                bad.append('terminal field %r' % r[t])
    if bad:
        sys.exit('NETLIST CHECK FAILED:\n' + '\n'.join(sorted(set(bad))))
    os.makedirs(NET, exist_ok=True)
    for name, head, rows in (('power_devices.csv', DH, dev_rows), ('power_wires.csv', WH, wire_rows)):
        with open(os.path.join(NET, name), 'w', encoding='utf-8', newline='') as f:
            wr = csv.DictWriter(f, fieldnames=head, lineterminator='\n')
            wr.writeheader()
            wr.writerows(rows)
    ext = sorted({r[e] for r in wire_rows for e in ('from_device', 'to_device')} - set(names))
    if absent:
        print('local sources absent (%s): source-file check skipped for %d of %d paths%s'
              % (' '.join(a + '/' for a in absent), n_skip, n_paths,
                 '; far-end check skipped' if allowed_far is None else ''))
    print('power_devices.csv %d rows, power_wires.csv %d rows, bad 0; far-end devices of other threads: %s'
          % (len(dev_rows), len(wire_rows), ' '.join(ext)))


if __name__ == '__main__':
    check_and_write()
