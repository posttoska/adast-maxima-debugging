# Three-dimensional (3D) electric scheme on the mechanical model (thread t4, layout_3d)

The same read-only model as episode 1 (stage_1_mechanics, commit f52cc8e), with one more layer on it: the electrical parts of the Adast Maxima MS 115 PS guillotine in 3D. Field devices sit on their episode-1 anchors, cabinet (Czech rozvaděč; Russian электрошкаф) and console devices are boxes at their photographed places, and cables are bundles along routes marked "estimated", with no single wires (the user's order 1, question 4).

Sizes are in mm (millimetres). Every row of the two tables carries evidence marks drawn only from these four: sure, [?] (unclear), estimated ±<likely error>, or W (web, weaker evidence). One cell may combine them: then it names what each mark covers ("estimated ±10 % size, ±60 height, order sure (photo)"), or it starts with [?] ("[?] estimated ±100": the item, or a fact named in brackets or in the note, is unclear, and its place or route is estimated ±100). "[likely]" inside a note means probable, not proven; it is not a mark. Stage-1 anchor classes, quoted as "class E", "class P/E" and so on in the field-device rows (stage_1_mechanics/spec/frame.md line 6): D (drawing), T (table or text), P (photo or drawing proportion), E (estimate), W (web, counts as E). Short forms used below: photo <stem> = preparatory_data_analysis/maxima_photos/20261102_<stem>.jpg; OM (operating manual) = preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual; T = static_dynamic_memory/blocks/generation_002/artifacts/tables; WEB = static_dynamic_memory/blocks/generation_002/artifacts/web; section 22 = static_dynamic_memory/blocks/generation_002/sections/22_cables_terminals_routes.md, the exploring agents' route plan for the cables B1-B5 (connectors, glands, via points), built from T/17_cable_routes.csv, the photos and the stage-1 anchors, and cited in the source_path of every bundle and passage row. These five stay on the user's computer and never go to GitHub; the repository keeps only the paths. Designation letters (set 568-70.9001, sheet 1): S switch or sensor, SQ knife-lock sensor, K relay, KM contactor (Czech stykač), KT time relay (Czech časové relé), Y electromagnet, Q manual switch, FA and QF breakers (Czech jistič; Russian защитный автомат), T transformer, M motor, UZ inverter (Czech měnič; Russian преобразователь частоты), UG supply unit, ZF filter, BR encoder, XC connector, X terminal strip (Czech svorkovnice; Russian клеммник), E lamp, BMR cut-control board, R resistor. Other short forms: PE (protective earth), PLC (programmable logic controller), LED (light-emitting diode), DIN (Deutsches Institut für Normung) rail, E-stop (emergency stop), B&R (Bernecker + Rainer, maker of the PLC and the console's panel terminal), TABLO (Czech tablo: operator panel, the name set 568-70.9001 uses for the console terminal).

## 1. Files

| file | what it is | written by |
|---|---|---|
| scheme_3d/layout_3d.py | builds the layer | - |
| scheme_3d/electrical.glb | the layer as GLB (binary glTF: Graphics Library Transmission Format): one node per item, per clip and per bundle segment | layout_3d.py |
| scheme_3d/placements.csv | one row per device, marker, connector, mounting part and hole (CSV, comma-separated values; UTF-8 (8-bit Unicode Transformation Format) without BOM (byte order mark)) | layout_3d.py |
| scheme_3d/bundles.csv | one row per bundle leg (same format) | layout_3d.py |
| scheme_3d/contact_check.py | check 9 (contact) and the rules of findings G, H and I | - |
| scheme_3d/contact_report.txt | its report: one line per item, per leg end, per leg span, per marker | contact_check.py |
| scheme_3d/render_views.py, scheme_3d/renders/*.png | six PNG (Portable Network Graphics) views of the layer on the model | render_views.py |
| scheme_3d/spec_tables.py | writes every table of this text that sits between `BEGIN`/`END` marker comments | - |
| spec/layout_3d.md | this text | partly spec_tables.py |

## 2. How to run and check

From the repository root, with Python 3.15, numpy, trimesh and manifold3d (PIL (Python Imaging Library) for the renders). The `-B` switch keeps `__pycache__` folders out of the repository.

```
python -B stage_2_electronics/scheme_3d/layout_3d.py              # electrical.glb, placements.csv, bundles.csv (seconds)
python -B stage_2_electronics/scheme_3d/contact_check.py          # contact_report.txt; exit 1 when FAIL > 0
python -B stage_2_electronics/scheme_3d/contact_check.py --selftest   # eight broken copies of the layer, each must FAIL
python -B stage_2_electronics/scheme_3d/render_views.py           # renders/*.png (about 2 s)
python -B stage_2_electronics/scheme_3d/spec_tables.py            # the generated tables of this text
git diff --quiet f52cc8e -- stage_1_mechanics                     # exit 0: stage 1 untouched (check 10)
```

- contact_check.py also takes its files as arguments: `contact_check.py [glb] [placements] [bundles] [report]` (thread t5 reruns it on the merged layer).
- layout_3d.py reads two inputs: stage_1_mechanics/out (the anchor files *_anchors.json and assembly.glb) and the netlists of threads t1-t3, stage_2_electronics/netlist/*_wires.csv (thread t5's merged_wires.csv is skipped), from which it builds the contents of every cable leg (section 9). When no such netlist is there, it stops with a message naming that folder, so a copy needs the whole stage_2_electronics. A change to those netlists means a rebuild: layout_3d.py, then contact_check.py and spec_tables.py. It asserts that every source path it writes exists, with one exception: a path under static_dynamic_memory/ or preparatory_data_analysis/ (local only) may be missing when its own folder is missing too (a partial copy); then it prints one INFO line naming the highest absent folder and builds the same files. A missing file in a folder that is present (a typo, a renamed file) stops the build.
- The build is deterministic: rerun, or run in a copy, it writes byte-identical electrical.glb, placements.csv, bundles.csv and contact_report.txt (section 12).

## 3. Coordinates and units

As in episode 1 (stage_1_mechanics/spec/frame.md lines 15-19): mm, machine coordinates; X along the knife, + to the operator's right; Y + from the cutting line toward the backgauge (rear); Z up. X 0 = middle of the cutting width (±20, stage-1 measure row frame.M2: every X value depends on it), Y 0 = cutting line, Z 0 = floor, and the floor is the plane Z 0. electrical.glb carries the scene metadata units "mm, machine coordinates, Z up", has no root transform and is never rescaled; trimesh calls its units "meters", which is wrong, as for stage 1. It loads with the stage-1 loop of stage_1_mechanics/assembly/assembly.py lines 276-282. Node names: `electrical.<class>.<id>` with the classes dev (cabinet and console devices), mark (markers on field devices), conn (connectors XC1-XC4), mount (plate, rails, ducts), pass (glands, holes, shafts), clip and bundle (one node per straight segment, `.s<i>`); clips are `electrical.clip.<leg>.c<i>`.

## 4. Counts of this build

<!-- BEGIN COUNTS -->
- electrical.glb: 489 nodes = 112 items + 217 clips + 160 bundle segments; items by class: dev 54, mark 22, conn 4, mount 14, pass 18.
- placements.csv: 113 rows (112 with a drawn item; FF1 without); by place: cabinet 58, machine 35, cabinet wall 6, console 6, cabinet outside face 4, console outside 3, console wall 1.
- bundles.csv: 34 legs in bundles B1, B2, B3, B4, B5; total length 32301 mm.
- contact_report.txt: FAIL 0; 459 PASS lines, 15 PASS-THROUGH lines, 4 INFO lines; 68 END lines, largest end gap 0.4 mm; longest free span 276 mm (leg B3) of the 300 mm allowed; 27 MARKER lines.
- SLACK: B5-S28s -> B5-S28r (moves with clamp, stroke 130 mm down): loop 239 mm >= straight distance between the loop's ends at rest 80 + stroke 130 = 210 mm; straight distance between the loop's ends at full stroke 108 mm.
<!-- END COUNTS -->

## 5. Decisions

- **Photos rule** (order 1, question 2; DECISION 1): the cabinet photos decide what is wired and where it sits; where they cannot tell, the 1998 set 568-70.9001 is taken as unchanged. Where photo and print differ, the photo wins, the row's note names the print's value, and the row is on the on-site list (section 11). Rows of this kind:

<!-- BEGIN PHOTO_PRINT -->
| item | evidence | note (photo against print) |
|---|---|---|
| dev.BMR1 | estimated ±10 % size, ±60 height, order sure (photo) | plate reads BMR2, markers 1BMR1-28BMR1: one board; BMR1 against plate BMR2 (check) |
| dev.KT1 | estimated ±20 % size, ±60 height, order sure (photo) | OM Fig.10.2 also draws KT1, KT2 at row 4 right (check) |
| dev.undesignated_R4_1 | estimated ±20 % size, ±60 height, order sure (photo) | grey box, no designation seen; not in set 568-70.9001 sheets 1-4 or the OM list (check) |
| dev.KM1A | estimated ±20 % size, ±60 height, order sure (photo) | OM lists KM1 = KM1A + KM1B: two boxes; family EP1C093 [?] assumed from the side label read on KM6 (photo 144247); OM p.47 lists KM1A, KM1B EP1-C123 B (check) |
| dev.FA3 | estimated ±20 % size, ±60 height, order sure (photo) | inverter breaker (568 2:18; OM p.41 says FA1: check) |
| dev.undesignated_R4_2 | estimated ±20 % size, ±60 height, order sure (photo) | NOARK breaker, no designation (no FA5/FA6 invented); not in set 568-70.9001 sheets 1-4 or the OM list, added later [likely] (check) |
| dev.undesignated_R4_3 | estimated ±20 % size, ±60 height, order sure (photo) | NOARK breaker, no designation (no FA5/FA6 invented); not in set 568-70.9001 sheets 1-4 or the OM list, added later [likely] (check) |
| dev.KM6 | estimated ±20 % size, ±60 height, order sure (photo) | front auxiliary block; side label EP1C093 on this unit (photo 144247); OM p.47 lists KM6 EP1-C099 B (EP1-C093 B is KM8 there) (check) |
| dev.K1 | estimated ±20 % | plate reads F. Lütze; OM lists RE6-0011 (check) |
| dev.K2 | estimated ±20 % | plate reads F. Lütze; OM lists RE6-0011 (check) |
| dev.T1 | estimated ±30 % | transformer bolted to the floor, right through the door (OM Fig.10.2 centre: check) |
| dev.TABLO | estimated ±30 | B&R terminal 4E0040.01-590 / 4D1084.00-590 clamped to the cover, 270 x 150 mm ±30 mm; OM p.46 lists the panel controller as 4C 2000.01-510 (check) |
| dev.toggle | estimated ±30 | toggle switch, no designation in 568 or OM (check) |
| dev.white_box | estimated ±50 | white box, [likely] retrofit: not in 568 or OM (check) |
| dev.terminal_block_1 | estimated ±50 | terminal block on the console floor, [likely] retrofit: not in 568 or OM (check) |
| dev.terminal_block_2 | estimated ±50 | terminal block on the console floor, [likely] retrofit: not in 568 or OM (check) |
| dev.E1 | [?] estimated ±100 | LED bar seen where lamp E1 is drawn, [likely] retrofit (not factory); lamp E1 fitted? [?] |
| dev.E2 | [?] estimated ±100 | LED bar seen where lamp E2 is drawn, [likely] retrofit (not factory); lamp E2 fitted? [?] |
| conn.XC2 | [?] label, estimated ±115/250/100 | on the cabinet face toward the machine, low; Y and labels: check |
| conn.XC4 | [?] label, estimated ±115/250/100 | on the cabinet face toward the machine, low; Y and labels: check |
| conn.XC1 | sure (pins), place estimated ±115/250/100 | on the cabinet face toward the machine, low; Y and labels: check |
| conn.XC3 | [?] label, estimated ±115/250/100 | on the cabinet face toward the machine, low; Y and labels: check |
<!-- END PHOTO_PRINT -->

- **Cabinet option B** (DECISION 3 of episode 1, as built in stage 1, stage_1_mechanics/spec/housing.md lines 12 and 63): the cabinet stands against the left column's outer face, X -1420..-1250. If the site shows option A (stage-1 measure rows housing.M9, assembly.A3), the cabinet and everything on it moves +113 X:

<!-- BEGIN OPTION_A -->
- 68 placements rows (place cabinet, cabinet outside face, cabinet wall): mount.plate, mount.duct.VL, mount.duct.VR, mount.duct.D12, mount.duct.D23, mount.duct.D34, mount.duct.D45, mount.duct.D56, mount.duct.D67, dev.BMR1, dev.PLC, mount.rail.R3, dev.PE1, dev.X10, dev.PE2, dev.X11, mount.rail.R4, dev.KT1, dev.KT2, dev.undesignated_R4_1, dev.QF1, dev.QF2, dev.KM1A, dev.KM1B, dev.FA1, dev.FA2, dev.FA3, dev.undesignated_R4_2, dev.undesignated_R4_3, mount.rail.R5, dev.KM2, dev.KM3, dev.KM4, dev.KM8, dev.KM6, dev.KM7, mount.rail.R7, dev.ZF1, dev.XP, dev.PE3, dev.X5, dev.XC7, dev.FA4, dev.R14, mount.rail.R2, dev.K1, dev.K2, dev.UG50, dev.X2, dev.ZF2, dev.UZ1, dev.T1, dev.PE_stud, dev.door_plate, dev.Q1, pass.shaft_Q1, dev.Q2, pass.shaft_Q2, dev.S4, pass.shaft_S4, dev.S2, pass.shaft_S2, conn.XC2, conn.XC4, conn.XC1, conn.XC3, pass.G1, pass.G2.
- 7 bundle legs with points on or inside the cabinet (X <= -1250 + 1 mm) or an end at one of those rows: those points and ends move with the cabinet, the rest of each route stretches: B1 (2 of 11 points; end at dev.X10), B1-PLC (2 of 2 points; end at dev.PLC), B2 (0 of 11 points; end at conn.XC2), B2-XC4 (0 of 3 points; end at conn.XC4), B3 (0 of 15 points; end at conn.XC1), B3-XC3 (0 of 3 points; end at conn.XC3), B4 (2 of 17 points; end at dev.X10).
<!-- END OPTION_A -->

- **Bundles, not wires**: one bundle per route (B1-B5) with branch legs; the contents column lists what each leg carries. No single wire is drawn.
- **Nothing in the air** (meta orc (meta orchestrator) decision, check 9): every item touches, or is fastened to, a stage-1 body, the cabinet, the console or the floor; contact_check.py proves it (section 10).
- **Stage 1 read-only**: nothing under stage_1_mechanics is written. Stage-1 bodies that themselves touch no other body (INFO lines, section 10) stay as built, and our items attach to them anyway.
- **Field devices** sit on their stage-1 anchors; a marker (mark.*, a 16 mm cube) sits on the face of the device's stage-1 body where its cable reaches it.
- **Cabinet devices** are boxes in their photographed row and order. Through the door (the cabinet's -X face) left to right = Y decreasing; the machine-side face is X -1250.
- **Console devices** sit on the inner face of the console's front cover (the cover the operator faces; its inside was photographed, photo 151739) at the stage-1 anchors ref.console_toggle, display.T and button.S1 (front photo 152550).
- **Not drawn, with reasons**: XC50, XC60, XC70 (568 names these plugs; the photo shows plugs only on the PLC (programmable logic controller) sockets "IF1 RS232" (RS232: Recommended Standard 232 serial port) and "ANALOG OUTPUTS", with no XC label, photo 142944; leg B1-PLC carries the XC60 link); the RC (resistor-capacitor) suppressors (coil markers "(RC)" only); controller 4C 2000.01-510 (OM page 46) and the keyboards (OM photo 20261115_023023), never seen on this machine; FF1, the light curtain: not fitted (certificate "—"), so its row has no item and no leg. The two NOARK breakers and the grey box in row 4 are drawn without an invented designation (no FA5 or FA6). dev.door_plate is not electrical: it is the maker plate on the door's inner face with the cabinet serial "v.č. 4794" (Czech výrobní číslo, serial number), kept as a landmark.

## 6. Table columns

<!-- BEGIN COLUMNS -->
placements.csv header (exactly):

```
item,designation,kind,place,anchor,device_body,x_mm,y_mm,z_mm,box_x_mm,box_y_mm,box_z_mm,size_x_mm,size_y_mm,size_z_mm,fastened_to,photo_row,moves_with,passes,evidence,source_path,note
```

| column | meaning |
|---|---|
| `item` | name of the drawn item in electrical.glb without the prefix "electrical.": dev.<designation> (device box), mark.<designation> (marker on a field device), conn.<designation> (connector), mount.* (plate, rails, ducts), pass.* (gland, hole or shaft through a wall); empty when nothing is drawn (FF1) |
| `designation` | designation as in set 568-70.9001 or as read on the photos; empty for mounting parts and holes |
| `kind` | what the item is: cabinet device, console device, field device, connector, DIN rail 35 mm, wiring duct, passage, switch block, switch shaft, lamp, ... |
| `place` | cabinet or console (inside the enclosure: the only two values check 7 bounds), cabinet wall, cabinet outside face, console wall, console outside, machine |
| `anchor` | stage-1 anchor the row stands on (<kind>.<designation> or body.<designation>); empty for boxes placed from the photos |
| `device_body` | stage-1 body that is the device itself (field devices, switch handles); empty otherwise |
| `x_mm` | X of the anchor when the row has one, else X of the box centre |
| `y_mm` | Y, as x_mm |
| `z_mm` | Z, as x_mm |
| `box_x_mm` | X of the centre of the item's axis-aligned box |
| `box_y_mm` | Y of that centre |
| `box_z_mm` | Z of that centre |
| `size_x_mm` | size of that box along X |
| `size_y_mm` | size along Y |
| `size_z_mm` | size along Z |
| `fastened_to` | what holds the item: a stage-1 body, housing.cabinet or housing.console (2 mm shells), floor.Z0, or one of our mount.* items; a pass names every wall it goes through, separated by "; " |
| `photo_row` | cabinet row 1-7 or floor as photographed (inside the cabinet only) |
| `moves_with` | clamp for the items that ride the clamp beam (the viewer's clamp group), else empty |
| `passes` | pass items the row goes through; empty in every placements row of this build (bundles use it) |
| `evidence` | marks drawn only from these four, with their reasons: sure, [?] (unclear), estimated ±<likely error>, W (web, weaker); a cell may combine them, either naming what each covers ("estimated ±10 % size, ±60 height, order sure (photo)") or starting with [?] ("[?] estimated ±100": the item, or a fact named in brackets or in the note, is unclear, and its place or route is estimated); "[likely]" appears only in notes and means probable, not proven |
| `source_path` | repository-relative source paths, separated by "; " |
| `note` | free text: reasons, photo-against-print differences, exceptions |

bundles.csv header (exactly):

```
leg,bundle,from_item,to_item,diameter_mm,length_mm,path_mm,clips,contents,moves_with,passes,evidence,source_path,note
```

| column | meaning |
|---|---|
| `leg` | leg name: B1-B5 for a trunk, B<n>-<end> for a branch; <end> is the designation the branch ends at, or a leg letter (list below this table) |
| `bundle` | bundle B1-B5 (routes of section 22) |
| `from_item` | start: an item of placements.csv, or "junction on <leg>" (a point on that leg's path) |
| `to_item` | end, as from_item |
| `diameter_mm` | bundle diameter (estimated) |
| `length_mm` | length along path_mm |
| `path_mm` | via points "x y z; x y z; ..." in mm; each segment runs along one axis and is one node <leg>.s<i> |
| `clips` | clips as clip.<leg>.c<i>@<carrier body>, separated by "; " |
| `contents` | what the bundle carries; terminal first: 14X10 = terminal 14 of strip X10 |
| `moves_with` | clamp for the legs that ride the clamp beam, else empty |
| `passes` | our items the leg runs through (ducts, glands, holes, the plate), separated by "; " |
| `evidence` | mark with its reason, as in placements.csv |
| `source_path` | repository-relative source paths, separated by "; " |
| `note` | free text: deviations from the section-22 route and why |

Leg letters, used in B<n>-<end> where <end> is not a designation (K, R and T here are not the designation letters listed at the top of this text):

- `PLC`: the PLC socket (B1-PLC, from the PLC down into duct D23).
- `T`: TABLO, the B&R terminal in the console (B1-T).
- `F`: front table (B2-F to S10, then B2-S11).
- `R`: rear table (B2-R to S27, then B2-S24); drive corner on the right (B4-R to S5, then B4-Y10 and B4-S19).
- `K`: knife-lock area: sensors S12-S14, SQ1 and SQ2, wired through terminal strip X8, and magnet Y01 (B4-K to S12, then B4-S13, B4-S14, B4-SQ1 with B4-SQ2, and B4-Y01).
- `s`, `r`, `p` after S28: the S28 lead's slack loop (B5-S28s), its part that rides the clamp (B5-S28r) and its pocket lead (B5-S28p).
<!-- END COLUMNS -->

Check 7 bounds only two place values: cabinet (inside X -1420..-1250, Y -200..300, Z 0..1535) and console (inside X -835..850, Y -454..-394, Z 1190..1535). Items on or through the walls carry their own place values (cabinet wall, cabinet outside face, console wall, console outside) and are bound by check 9 instead.

## 7. Cabinet and console

Cabinet, option B, all estimated: inner space X -1418..-1252, Y -198..298, Z 2..1533 (2 mm walls); mounting plate on the back wall's inner face, X -1254.5..-1252; DIN (Deutsches Institut für Normung) rails 35 mm, X -1262..-1254.5; wiring ducts VL and VR at the sides and D12..D67 between the rows. Row centres Z, from OM Fig. 10.2 scaled (±60): R1 1453, R2 1260, R3 1096, R4 921, R5 750, R6 523 (plate devices), R7 323. T1 is bolted to the floor, right through the door (Y -95); the PE (protective earth) stud sits on the left wall (Y 288). The switch blocks of Q1, Q2, S4 and S2 sit on the inner face of the front wall (Y -198), their shafts (pass.shaft_*) go through the wall to the stage-1 handles. Connectors XC2, XC4, XC1, XC3, top down, on the machine-side face at X -1250, Y 50, Z 686, 612, 508, 396 (stage-1 anchors, estimated; the photo puts them further to the rear [?]).

Console (Czech tablo, operator panel), against the inner face of the front cover (Y -452, 2 mm wall estimated), left to right as seen from the front: toggle switch (X -195), the B&R (Bernecker + Rainer) terminal dev.TABLO (X 103..373, Z 1279..1429; modules 4E0040.01-590 and 4D1084.00-590 printed on it), the E-stop (emergency stop) S1 contact block (X 773) with its stem pass.shaft_S1 through the cover. The white box and the two terminal blocks on the console floor are probably retrofits, not proven ("[likely]" in their notes; photos 151755, 152007; on the on-site list). Under the console hang two LED (light-emitting diode) bars where the print draws lamps E1 and E2: probably a retrofit ("[likely]" in their notes), lamp fitted? [?] (photos 151822, 151755); E3 sits on the console front and E4 on frame.column_right's front, both at their stage-1 anchors, fitted? [?].

## 8. Field devices and check 6

Check 6 asks that each device sits on body.<designation>, else <kind>.<designation>, within 1 mm. It is read as agreed with the soft critic (finding I): (a) the stage-1 anchor point lies in or on the device's own stage-1 body; (b) our item for the device (marker, shaft or box) lies at most 1 mm from that device body and at most 1 mm from the body it is fastened to; (c) the distance from the anchor point to our item is printed for information only, since an anchor is a point inside a body while our item sits on the body's face where the cable arrives. contact_check.py prints one MARKER line per fitted field device; this table is generated from those lines:

<!-- BEGIN MARKER -->
| result | designation | anchor | device body | anchor to body (mm) | item | item to body (mm) | carrier | item to carrier (mm) | anchor to item (mm, info) | exception |
|---|---|---|---|---|---|---|---|---|---|---|
| PASS | Q1 | body.Q1 | safety_sensors.Q1 | 0.0 | pass.shaft_Q1 | 0.0 | housing.cabinet | 0.0 | 49.9 |  |
| PASS | Q2 | body.Q2 | safety_sensors.Q2 | 0.0 | pass.shaft_Q2 | 0.0 | housing.cabinet | 0.0 | 39.9 |  |
| PASS | S4 | body.S4 | safety_sensors.S4 | 0.0 | pass.shaft_S4 | 0.0 | housing.cabinet | 0.0 | 29.9 |  |
| PASS | S2 | body.S2 | safety_sensors.S2 | 0.0 | pass.shaft_S2 | 0.0 | housing.cabinet | 0.0 | 29.9 |  |
| PASS | S1 | body.S1 | safety_sensors.S1 | 0.0 | pass.shaft_S1 | 0.0 | housing.console | 0.0 | 37.9 |  |
| PASS | S10 | body.S10 | safety_sensors.S10 | 0.0 | mark.S10 | 0.0 | safety_sensors.S10 | 0.0 | 14.9 |  |
| PASS | S11 | body.S11 | safety_sensors.S11 | 0.0 | mark.S11 | 0.0 | safety_sensors.S11 | 0.0 | 14.9 |  |
| PASS | SQ1 | body.SQ1 | safety_sensors.SQ1 | 0.0 | mark.SQ1 | 0.0 | safety_sensors.SQ1 | 0.0 | 0.0 |  |
| PASS | SQ2 | body.SQ2 | safety_sensors.SQ2 | 0.0 | mark.SQ2 | 0.0 | safety_sensors.SQ2 | 0.0 | 11.9 |  |
| PASS | S12 | body.S12 | safety_sensors.S12 | 0.0 | mark.S12 | 0.0 | safety_sensors.S12 | 0.0 | 8.9 |  |
| PASS | S13 | body.S13 | safety_sensors.S13 | 0.0 | mark.S13 | 0.0 | safety_sensors.S13 | 0.0 | 24.4 |  |
| PASS | S14 | body.S14 | safety_sensors.S14 | 0.0 | mark.S14 | 0.0 | safety_sensors.S14 | 0.0 | 24.9 |  |
| PASS | S5 | body.S5 | safety_sensors.S5 | 0.0 | mark.S5 | 0.0 | safety_sensors.S5 | 0.0 | 47.4 |  |
| PASS | S19 | body.S19 | safety_sensors.S19 | 0.0 | mark.S19 | 0.0 | safety_sensors.S19 | 0.0 | 0.0 |  |
| PASS | S28 | body.S28 | safety_sensors.S28 | 0.0 | mark.S28 | 154.0 | clamp.bar | 0.0 | 233.9 | S28 sits in its pocket in clamp.front_block; marker on the bar top above it, pocket leg B5-S28p reaches the switch body |
| PASS | S30 | body.S30 | safety_sensors.S30 | 0.0 | mark.S30 | 0.0 | safety_sensors.S30 | 0.0 | 14.9 |  |
| PASS | M3 | body.M3 | safety_sensors.M3 | 0.0 | mark.M3 | 0.0 | safety_sensors.M3 | 0.0 | 124.9 |  |
| PASS | Y3 | body.Y3 | safety_sensors.Y3 | 0.0 | mark.Y3 | 0.0 | safety_sensors.Y3 | 0.0 | 24.9 |  |
| PASS | M1 | motor.M1 | knife.m1_motor | 0.0 | mark.M1 | 0.0 | knife.m1_motor | 0.0 | 112.4 |  |
| PASS | Y10 | clutch.Y10 | knife.clutch_y10 | 0.0 | mark.Y10 | 100.0 | knife.slip_rings | 0.0 | 156.8 | marker at the slip rings, Y10's electrical feed point in the route plan (sections/22_cables_terminals_routes.md); anchor inside the clutch |
| PASS | Y01 | magnet.Y01 | knife.y01_magnet | 0.0 | mark.Y01 | 0.0 | knife.y01_magnet | 0.0 | 39.9 |  |
| PASS | Y14 | brake.Y14 | clamp.brake_y14 | 0.0 | mark.Y14 | 0.0 | clamp.brake_y14 | 0.0 | 79.9 |  |
| PASS | Y11 | valve.Y11 | clamp.valve_block_ov2 | 0.0 | mark.Y11 | 0.0 | clamp.valve_block_ov2 | 0.0 | 59.9 |  |
| PASS | BR40 | sensor.BR40 | backgauge.encoder_BR40 | 0.0 | mark.BR40 | 0.0 | backgauge.encoder_BR40 | 0.0 | 32.9 |  |
| PASS | S24 | sensor.S24 | backgauge.S24 | 0.0 | mark.S24 | 0.0 | backgauge.S24 | 0.0 | 14.9 |  |
| PASS | S27 | sensor.S27 | backgauge.S27 | 0.0 | mark.S27 | 0.0 | backgauge.S27 | 0.0 | 15.4 |  |
| PASS | M2 | motor.M2 | backgauge.M2 | 0.0 | mark.M2 | 0.0 | backgauge.M2 | 0.0 | 114.9 |  |
<!-- END MARKER -->

Two exceptions to (b), named in their rows' notes:
- S28 (clamp switch): it sits in a pocket of clamp.front_block, where nothing can be fastened from outside. Its marker sits on the clamp bar's top face above it, 154 mm from the switch body, and the pocket leg B5-S28p runs down hole H6 to the switch body itself (end gap 0.0 mm).
- Y10 (cut clutch magnet; Czech spojka řezu, Russian муфта реза): the magnet is inside the clutch and is fed through the slip rings, so its marker sits on knife.slip_rings, the feed point of section 22, 100 mm from the clutch body.

## 9. Bundles

Routes after section 22 and T/17_cable_routes.csv; every unseen leg is estimated ±200, and each deviation from section 22 is named in the leg's note. The contents of a leg (its X10 terminals and signals) are built from the netlists of threads t1-t3 (stage_2_electronics/netlist/*_wires.csv, read by layout_3d.py's function x10()), so they cannot drift from them; the build asserts that every X10 terminal of a branch is also in the contents of the leg it branches from, so a trunk carries the union of its branches.
- B1, cabinet to console: X10, duct D23, gland G1, up frame.column_left, console opening H1, console; branches to S1, the PLC, TABLO and E1-E4. Carries the XC60-XC70 panel data link, supply 33X10, 45X10 and PE, E-stop S1 15-16X10, lamps E1-E4 7-13X10.
- B2, connectors XC2 and XC4 to the front and the rear table: down frame.support_left's outer face, along the floor in front of it, up base_front to BR40, S10 and S11; B2-R along the floor at X -554.5 to Y 180, up the support's inner wall and along the rear table's underside to S27 and S24.
- B3, connectors XC1 and XC3 to the rear: under the base, up the support's inner wall, along the rear table's underside at X -330 to M2 (P-clips seen under the rear table, photo 144539); branches B3-XC3, B3-M3, B3-Y3. The trunk lies on the table's underside only as far as about Y 1580: the rear table tapers from full width at Y 1334 to X -92.5..92.5 at Y 1806 (stage_1_mechanics/spec/frame.md, row "table rear taper"), so from there round the corner at Y 1680 to about X -228 the trunk runs free for about 200 mm, up to 67 mm from the table, before it meets the underside again. B3-M3 leaves the trunk on the floor, runs along the floor to the front of frame.rear_stand (the route plan's way, section 22) and rises free to M3. The rise (X 76, Y 1047.5, Z 6 to 160) stands 28 to 89 mm in front of the stand, 28 mm near its foot (Z 21) and 89 mm at its top (Z 160): near the leg the stand has only two inclined struts and no face to clip to, and the leg meets only the stand's bounding box (Y 1053.5), not its mesh. So no clip lands on the stand; the leg is held by its clips on the floor and on safety_sensors.M3 alone, and its longest free span is 249 mm (contact_report.txt; limit 300 mm). Whether the blower cable really rises with the trunk at frame.support_left or at the rear stand, and whether it is clipped to the stand, is not seen; it is on the on-site list.
- B4, X10 to the right drive: gland G2, frame.column_left, floor, base_front's rear face, underside, frame.support_right, M1; branches to Y11, S5, Y10, S19, S12-S14, SQ1, SQ2, Y01 (no photo). Its last rise (X 1205, Y 330, Z 12 to 166.5) stands free in front of M1: the motor is round (axis along X), so the rise is 81 mm from it at its foot and 8 mm at Z 132, and meets it only at the marker (0.9 mm at the top); its longest free span is 170 mm (contact_report.txt). All gaps given for B3, B3-M3 and B4 are closest-point distances from points on the leg's axis to the named body's mesh in stage_1_mechanics/out/assembly.glb (manifold min_gap), minus the bundle radius.
- B5, X10 to the clamp band: off B1 through H2, along frame.crossbar's rear face to S30 and Y14, and the S28 lead.

<!-- BEGIN BUNDLES -->
| leg | from | to | diameter (mm) | length (mm) | clips | longest free span (mm) | end gaps from / to (mm) | moves with | evidence |
|---|---|---|---|---|---|---|---|---|---|
| B1 | dev.X10 | dev.S1 | 20 | 2991.5 | 21 | 160 | 0.0 / 0.0 |  | estimated ±100 (console end seen, rest ±200) |
| B1-PLC | dev.PLC | junction on B1 | 16 | 40 | 0 | 15 | 0.0 / 0.0 |  | estimated ±100 |
| B1-T | junction on B1 | dev.TABLO | 16 | 77 | 0 | 77 | 0.0 / 0.0 |  | estimated ±100 |
| B1-E1 | junction on B1 | dev.E1 | 10 | 30 | 0 | 30 | 0.0 / 0.0 |  | [?] estimated ±100 |
| B1-E2 | junction on B1 | dev.E2 | 10 | 30 | 0 | 30 | 0.0 / 0.0 |  | [?] estimated ±100 |
| B1-E3 | junction on B1 | dev.E3 | 10 | 209 | 0 | 193 | 0.0 / 0.0 |  | [?] estimated ±100 |
| B1-E4 | junction on B1 | dev.E4 | 10 | 468 | 3 | 131 | 0.0 / 0.0 |  | [?] estimated ±100 |
| B5 | junction on B1 | mark.S30 | 16 | 2279 | 17 | 156 | 0.0 / 0.0 |  | estimated ±200 (no photo) |
| B5-Y14 | junction on B5 | mark.Y14 | 12 | 62 | 0 | 67 | 0.0 / 0.0 |  | estimated ±200 |
| B5-S28 | junction on B5 | clip.B5-S28.c3 | 12 | 236 | 4 | 132 | 0.0 / 0.0 |  | estimated ±200 |
| B5-S28s | junction on B5-S28 | junction on B5-S28r | 12 | 239 | 0 | 242 | 0.0 / 0.0 |  | estimated ±200 |
| B5-S28r | junction on B5-S28s | mark.S28 | 12 | 375 | 3 | 149 | 0.0 / 0.0 | clamp | estimated ±200 |
| B5-S28p | mark.S28 | stage-1 safety_sensors.S28 | 6 | 154 | 0 | 0 | 0.0 / 0.0 | clamp | [?] estimated ±20 |
| B2 | conn.XC2 | mark.BR40 | 24 | 3014 | 20 | 166 | 0.0 / 0.4 |  | estimated ±200 (conduit at XC2 seen; rest no photo) |
| B2-XC4 | conn.XC4 | junction on B2 | 12 | 164 | 0 | 169 | 0.0 / 0.0 |  | [?] estimated ±200 (XC4 label [?]) |
| B2-F | junction on B2 | mark.S10 | 12 | 647.5 | 5 | 145 | 0.0 / 0.4 |  | estimated ±200 |
| B2-S11 | junction on B2-F | mark.S11 | 12 | 638.5 | 5 | 130 | 0.0 / 0.4 |  | estimated ±200 |
| B2-R | junction on B2 | mark.S27 | 16 | 2795 | 19 | 157 | 0.0 / 0.4 |  | estimated ±200 (no photo of the leg) |
| B2-S24 | junction on B2-R | mark.S24 | 12 | 138 | 2 | 75 | 0.0 / 0.4 |  | estimated ±200 (no photo of the leg) |
| B3 | conn.XC1 | mark.M2 | 20 | 4548.5 | 31 | 276 | 0.0 / 0.4 |  | estimated ±200 (no photo of the leg) |
| B3-XC3 | conn.XC3 | junction on B3 | 16 | 70 | 0 | 75 | 0.0 / 0.0 |  | [?] estimated ±200 (XC3 label [?]) |
| B3-M3 | junction on B3 | mark.M3 | 12 | 1947.5 | 15 | 249 | 0.0 / 0.4 |  | estimated ±200 (no photo of the leg) |
| B3-Y3 | junction on B3 | mark.Y3 | 12 | 516.5 | 3 | 275 | 0.0 / 0.4 |  | [?] estimated ±400 (Y3 place ±400) |
| B4 | dev.X10 | mark.M1 | 24 | 6354 | 44 | 170 | 0.0 / 0.4 |  | estimated ±200 (no photo of the leg) |
| B4-Y11 | junction on B4 | mark.Y11 | 12 | 552.5 | 3 | 258 | 0.0 / 0.4 |  | estimated ±200 (no photo of the leg) |
| B4-R | junction on B4 | mark.S5 | 16 | 667 | 6 | 131 | 0.0 / 0.4 |  | estimated ±200 (no photo of the leg) |
| B4-Y10 | junction on B4-R | mark.Y10 | 12 | 650.5 | 5 | 145 | 0.0 / 0.4 |  | estimated ±200 (no photo of the leg) |
| B4-S19 | junction on B4-R | mark.S19 | 12 | 664 | 4 | 175 | 0.0 / 0.4 |  | estimated ±200 (no photo of the leg) |
| B4-K | junction on B4 | mark.S12 | 16 | 922.5 | 7 | 130 | 0.0 / 0.4 |  | [?] estimated ±200 (no photo of the leg) |
| B4-S13 | junction on B4-K | mark.S13 | 10 | 152.7 | 0 | 163 | 0.0 / 0.4 |  | [?] estimated ±200 (no photo of the leg) |
| B4-S14 | junction on B4-K | mark.S14 | 10 | 99.5 | 0 | 71 | 0.0 / 0.4 |  | [?] estimated ±200 (no photo of the leg) |
| B4-SQ1 | junction on B4-K | mark.SQ1 | 10 | 233 | 0 | 177 | 0.0 / 0.4 |  | [?] estimated ±200 (no photo of the leg) |
| B4-SQ2 | junction on B4-SQ1 | mark.SQ2 | 10 | 132.5 | 0 | 110 | 0.0 / 0.4 |  | [?] estimated ±200 (no photo of the leg) |
| B4-Y01 | junction on B4-K | mark.Y01 | 10 | 203 | 0 | 159 | 0.0 / 0.4 |  | [?] estimated ±200 (no photo of the leg) |
<!-- END BUNDLES -->

Holes, glands and shafts (pass items). Seen: G1 and G2 (grey glands in the plate behind X10, photo 144309) and H1 (console opening, 150 x 160 mm, photo 151736). Implied [?], because a cable must cross there and no photo shows the crossing: H2-H6 and H8-H11. H7 (through frame.support_left) was dropped with finding G. A pass may overlap only the bodies its fastened_to column names and the legs whose passes column names it; any other overlap is a FAIL (section 10, rule 1).

<!-- BEGIN PASSES -->
| item | designation | goes through (fastened_to) | size x, y, z (mm) | evidence | note |
|---|---|---|---|---|---|
| pass.shaft_Q1 | Q1 | housing.cabinet | 10 x 2 x 10 | estimated ±20 (shaft Ø10 assumed) | shaft through the front wall (2 mm, estimated) from the contact block to the stage-1 handle |
| pass.shaft_Q2 | Q2 | housing.cabinet | 10 x 2 x 10 | estimated ±20 (shaft Ø10 assumed) | shaft through the front wall (2 mm, estimated) from the contact block to the stage-1 handle |
| pass.shaft_S4 | S4 | housing.cabinet | 22 x 2 x 22 | estimated ±20 (shaft Ø22 assumed) | shaft through the front wall (2 mm, estimated) from the contact block to the stage-1 handle |
| pass.shaft_S2 | S2 | housing.cabinet | 22 x 2 x 22 | estimated ±20 (shaft Ø22 assumed) | shaft through the front wall (2 mm, estimated) from the contact block to the stage-1 handle |
| pass.shaft_S1 | S1 | housing.console | 22 x 2 x 22 | estimated ±20 (stem Ø22 assumed: 22 mm panel hole) | E-stop stem through the cover (2 mm, estimated) from the contact block to the stage-1 mushroom head |
| pass.G1 | G1 | housing.cabinet; mount.plate | 14.5 x 30 x 30 | sure (seen), place estimated ±30 | grey gland B1, B5 |
| pass.G2 | G2 | housing.cabinet; mount.plate | 14.5 x 30 x 30 | sure (seen), place estimated ±30 | grey gland B4 |
| pass.H1 | H1 | frame.column_left; housing.console | 28 x 46 x 28 | [?] estimated ±100 | console back-wall opening (seen) and the column front wall behind it (implied) |
| pass.H2 | H2 | frame.column_left; frame.crossbar | 50 x 24 x 24 | [?] estimated ±200 | implied hole, column_left inner wall |
| pass.H3a | H3a | dev.E1; housing.console | 14 x 14 x 10 | [?] estimated ±100 | implied hole, console bottom |
| pass.H3b | H3b | dev.E2; housing.console | 14 x 14 x 10 | [?] estimated ±100 | implied hole, console bottom |
| pass.H4 | H4 | dev.E3; housing.console | 14 x 7 x 14 | [?] estimated ±100 | implied hole, console cover |
| pass.H5 | H5 | housing.console | 16 x 14 x 14 | [?] estimated ±100 | implied hole, console right wall |
| pass.H6 | H6 | clamp.bar; clamp.front_block; mark.S28; safety_sensors.S28 | 12 x 12 x 156 | [?] estimated ±20 | cable channel to the S28 pocket |
| pass.H8 | H8 | housing.belt_pulley_cover | 20 x 20 x 12 | [?] estimated ±200 | implied hole, belt pulley cover bottom plate: B4 to S5 and Y10 |
| pass.H9 | H9 | knife.lock_cover | 14 x 14 x 12 | [?] estimated ±100 | implied hole, knife lock cover bottom: S14 |
| pass.H10 | H10 | knife.lock_cover | 32 x 32 x 12 | [?] estimated ±100 | implied hole, knife lock cover bottom: SQ1, SQ2 |
| pass.H11 | H11 | knife.lock_cover | 14 x 14 x 12 | [?] estimated ±100 | implied hole, knife lock cover bottom: Y01 |
<!-- END PASSES -->

**The S28 lead and the clamp group** (finding H). The clamp beam moves 0..130 mm down (stage_1_mechanics/spec/clamp.md line 51). B5-S28 is fixed: it runs from (-706, 158, 1424) down the rear faces of frame.crossbar and clamp.guide_left to its end clip at Z 1190. B5-S28s is a free slack loop with no clips, from (-706, 156, 1190) to (-640, 156, 1235), 239 mm long. B5-S28r rides the clamp: clipped only to clamp.bar's rear face at Z 1235 up to X -458, then over the bar's top to mark.S28; B5-S28p goes down hole H6 to the switch. The SLACK rule (section 10) proves the loop long enough: 239 mm ≥ straight distance between the loop's ends at rest 80 + stroke 130 = 210 mm. For thread t5's viewer, these nodes form the clamp group and move with clamp.bar:

<!-- BEGIN CLAMP_GROUP -->
10 nodes (items mark.S28, pass.H6; legs B5-S28r, B5-S28p):

- `electrical.bundle.B5-S28p.s0`
- `electrical.bundle.B5-S28r.s0`
- `electrical.bundle.B5-S28r.s1`
- `electrical.bundle.B5-S28r.s2`
- `electrical.bundle.B5-S28r.s3`
- `electrical.clip.B5-S28r.c0`
- `electrical.clip.B5-S28r.c1`
- `electrical.clip.B5-S28r.c2`
- `electrical.mark.S28`
- `electrical.pass.H6`
<!-- END CLAMP_GROUP -->

B5-S28s stays fixed in the viewer, because a bending loop has no single rigid motion. Two distances belong to it and are not the same thing. In the viewer, at full stroke, B5-S28r's start drops 130 mm (the stroke) away from the loop's drawn end. On the real machine the loop bends instead, and the straight distance between its ends grows from 80 mm at rest to 108 mm at full stroke (contact report, SLACK line), well within its 239 mm length.

## 10. Contact check (check 9)

contact_check.py loads all 125 stage-1 bodies of stage_1_mechanics/out/assembly.glb (mm, never rescaled) and every node of electrical.glb, and measures real mesh-to-mesh geometry: manifold3d minimum gap and intersection volume, with bounding boxes only to skip far pairs. Rules:
1. Each item (box, marker, mounting part, pass, clip) lies at most 1 mm from a stage-1 body, the cabinet or console wall, the floor (a slab Z -50..0) or another item of ours, and overlaps no body by more than 0.5 mm³. Allowed overlaps: a pass overlaps only the bodies its fastened_to column names and the segments and clips of the legs whose passes column names it, and anything else that overlaps a pass fails; a leg may overlap the items its passes column names; the legs of one bundle, and a branch with the leg it branches from, may overlap each other (they share their junctions).
2. Every connected group of our items reaches stage 1 or the floor; a group that touches only itself or a cable fails (finding C).
3. housing.cabinet and housing.console are solid blocks in stage 1. They are checked as shells with 2 mm walls (estimated ±1 mm), so an item inside the solid does not count as touching.
4. Bundles: each clip lies at most 1 mm from a body that is not a bundle; along each leg, the free span between held points (clip, pass, duct or mounting box +1 mm, end item) is at most 300 mm; both ends of each leg lie at most 1 mm from their item or parent path (END lines; check 8).
5. RESERVED (finding G): no item in a space stage 1 keeps free for moving or mechanical parts, with exact mesh-and-box intersection. Reserved are the stage-1 anchors envelope.*, space.*, joint.passage.*, joint.bore.*, joint.slot.*, joint.window.*, table.slot*, plan.pedal* and every *.keepout.*:

<!-- BEGIN RESERVED -->
15 boxes:

| stage-1 anchor | min x, y, z (mm) | max x, y, z (mm) |
|---|---|---|
| envelope.clamp.levers_tie | -562.5, 40, 150 | 635, 160, 655 |
| envelope.clamp.pedal_link | -150, -611, 0 | 401, 370, 150 |
| envelope.clamp.pedal_link_rise | 241, 270, 150 | 401, 370, 390 |
| envelope.clamp.pull_rod_left | -690, 40, 400 | -637.3, 160, 1155 |
| envelope.clamp.pull_rod_right | 580, 40, 400 | 635, 160, 1155 |
| frame.keepout.backgauge_drive | -100, 236, 635 | 100, 1901, 785 |
| joint.bore.spindle.base_front | -15, -214, 710 | 15, -184, 740 |
| joint.bore.worm_shaft.support_right | 1135, 10, 599 | 1230, 70, 659 |
| joint.passage.clamp_brake.crossbar | -70, 70, 1415 | 45, 150, 1535 |
| joint.passage.clamp_tie.support_left | -637.3, 40, 500 | -562.5, 160, 655 |
| joint.slot.front_extension | -20, 235, 785 | 20, 420, 885 |
| joint.window.conrod.right_cheek | 720, -77, 870 | 760, -27, 1110 |
| plan.pedal | -200, -611, 0 | 200, -571, 150 |
| space.knife.drive_unit | 785, -77, 575 | 1140.3, 150, 785 |
| table.slot | -20, 420, 785 | 20, 1860, 885 |
<!-- END RESERVED -->

   Not reserved, on purpose: corridor.*, frame.cavity.* and cabinet.*. Stage 1 marks these as free room inside the frame and the cabinet, which is exactly where section 22 puts the cables: B2 reaches BR40 through corridor.base_cavity_centre and corridor.front_table_centre, and B4.s10 crosses a corridor. Reserving them would forbid the only routes the sources give. The crossings stay clear of moving parts: B4.s10 runs 12 mm from the guide ribs and 18 mm above the spindle, in front of the backgauge carriage (Y 63). The soft critic accepted this (finding G).
6. SLACK (finding H): a leg that moves with the clamp while its parent is fixed must start at the end of an unclipped parent loop at least as long as the straight distance between the loop's ends at rest plus the stroke (clamp 130 mm).
7. MARKER (check 6, finding I): as in section 8.

INFO lines name the stage-1 bodies our items attach to that touch no other stage-1 body: backgauge.M2, clamp.valve_block_ov2, safety_sensors.M3, safety_sensors.Y3. They stay as built.

Result (section 4): FAIL 0. The check can fail: `--selftest` breaks a copy of the layer eight ways, and each must FAIL. Run of 2026-11-27, eight of eight caught: a device box moved 50 mm up (FAIL 1); all clips of the leg with the most clips removed (FAIL 1); a marker sunk 10 mm into its body (FAIL 2); a 16 mm cube hanging on bundle B1 (FAIL 1); a cube on the floor inside envelope.clamp.pedal_link (FAIL 1); the slack loop pulled straight (FAIL 1); pass.G1 no longer fastened to mount.plate, which it overlaps (FAIL 2); pass.G1 dropped from the passes column of leg B1, which runs through it (FAIL 3).

## 11. On-site check list

Every row whose evidence is not plain "sure" is measured or looked at on site. The related stage-1 measure rows are the ids of T/19_stage1_model_measure_rows.csv; frame.M2 (the X zero) applies to every machine X. Generated from placements.csv and bundles.csv:

<!-- BEGIN ONSITE -->
146 rows: every placements and bundles row whose evidence is not plain "sure" (not listed: FF1).

| # | row | designation or bundle | place or ends | evidence | what to check on site | related stage-1 measure rows |
|---|---|---|---|---|---|---|
| 1 | mount.plate |  | cabinet | estimated ±25 % (width), ±60 (height) | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 2 | mount.duct.VL |  | cabinet | estimated ±30 | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 3 | mount.duct.VR |  | cabinet | estimated ±30 | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 4 | mount.duct.D12 |  | cabinet | estimated ±30 | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 5 | mount.duct.D23 |  | cabinet | estimated ±30 | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 6 | mount.duct.D34 |  | cabinet | estimated ±30 | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 7 | mount.duct.D45 |  | cabinet | estimated ±30 | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 8 | mount.duct.D56 |  | cabinet | estimated ±30 | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 9 | mount.duct.D67 |  | cabinet | estimated ±30 | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 10 | dev.BMR1 | BMR1 | cabinet | estimated ±10 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text; note: plate reads BMR2, markers 1BMR1-28BMR1: one board; BMR1 against plate BMR2 (check) | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 11 | dev.PLC | PLC | cabinet | estimated ±15 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 12 | mount.rail.R3 |  | cabinet | estimated ±60 (row height from OM Fig.10.2 scaled) | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 13 | dev.PE1 | PE | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 14 | dev.X10 | X10 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 15 | dev.PE2 | PE | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 16 | dev.X11 | X11 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 17 | mount.rail.R4 |  | cabinet | estimated ±60 (row height from OM Fig.10.2 scaled) | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 18 | dev.KT1 | KT1 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text; note: OM Fig.10.2 also draws KT1, KT2 at row 4 right (check) | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 19 | dev.KT2 | KT2 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 20 | dev.undesignated_R4_1 |  | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text; note: grey box, no designation seen; not in set 568-70.9001 sheets 1-4 or the OM list (check) | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 21 | dev.QF1 | QF1 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 22 | dev.QF2 | QF2 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 23 | dev.KM1A | KM1A | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text; note: OM lists KM1 = KM1A + KM1B: two boxes; family EP1C093 [?] assumed from the side label read on KM6 (photo 144247); OM p.47 lists KM1A, KM1B EP1-C123 B (check) | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 24 | dev.KM1B | KM1B | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 25 | dev.FA1 | FA1 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 26 | dev.FA2 | FA2 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 27 | dev.FA3 | FA3 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text; note: inverter breaker (568 2:18; OM p.41 says FA1: check) | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 28 | dev.undesignated_R4_2 |  | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text; note: NOARK breaker, no designation (no FA5/FA6 invented); not in set 568-70.9001 sheets 1-4 or the OM list, added later [likely] (check) | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 29 | dev.undesignated_R4_3 |  | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text; note: NOARK breaker, no designation (no FA5/FA6 invented); not in set 568-70.9001 sheets 1-4 or the OM list, added later [likely] (check) | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 30 | mount.rail.R5 |  | cabinet | estimated ±60 (row height from OM Fig.10.2 scaled) | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 31 | dev.KM2 | KM2 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 32 | dev.KM3 | KM3 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 33 | dev.KM4 | KM4 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 34 | dev.KM8 | KM8 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 35 | dev.KM6 | KM6 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text; note: front auxiliary block; side label EP1C093 on this unit (photo 144247); OM p.47 lists KM6 EP1-C099 B (EP1-C093 B is KM8 there) (check) | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 36 | dev.KM7 | KM7 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 37 | mount.rail.R7 |  | cabinet | estimated ±60 (row height from OM Fig.10.2 scaled) | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 38 | dev.ZF1 | ZF1 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 39 | dev.XP | XP | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 40 | dev.PE3 | PE | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 41 | dev.X5 | X5 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 42 | dev.XC7 | XC7 | cabinet | estimated ±20 % size, ±60 height, order sure (photo); W size | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 43 | dev.FA4 | FA4 | cabinet | estimated ±20 % size, ±60 height, order sure (photo) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 44 | dev.R14 | R14 | cabinet | estimated ±20 % | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 45 | mount.rail.R2 |  | cabinet | estimated ±30 | height, length and depth of the plate, rail or duct | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 46 | dev.K1 | K1 | cabinet | estimated ±20 % | row, order, size (width x height x depth), plate text; note: plate reads F. Lütze; OM lists RE6-0011 (check) | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 47 | dev.K2 | K2 | cabinet | estimated ±20 % | row, order, size (width x height x depth), plate text; note: plate reads F. Lütze; OM lists RE6-0011 (check) | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 48 | dev.UG50 | UG50 | cabinet | estimated ±20 % | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 49 | dev.X2 | X2 | cabinet | estimated ±20 % | row, order, size (width x height x depth), plate text; note: terminal strip X2 with N (neutral) and L (line), plate mount [?] | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 50 | dev.ZF2 | ZF2 | cabinet | estimated ±20 % | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 51 | dev.UZ1 | UZ1 | cabinet | estimated ±60 height (row 6, order sure, photo 143806); size sure (plate EVF8202-E-V002, Lenze manual page 4-3) | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 52 | dev.T1 | T1 | cabinet | estimated ±30 % | row, order, size (width x height x depth), plate text; note: transformer bolted to the floor, right through the door (OM Fig.10.2 centre: check) | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 53 | dev.PE_stud | PE | cabinet | estimated ±50 | row, order, size (width x height x depth), plate text | housing.M9 housing.M10 housing.M11 assembly.A3 |
| 54 | dev.door_plate |  | cabinet | estimated ±100 | row, order, size (width x height x depth), plate text | housing.M16 |
| 55 | dev.Q1 | Q1 | cabinet | estimated ±20 % size; shaft place from stage 1 | row, order, size (width x height x depth), plate text | housing.M12 housing.M10 |
| 56 | pass.shaft_Q1 | Q1 | cabinet wall | estimated ±20 (shaft Ø10 assumed) | is the hole or shaft there; place and diameter | housing.M12 housing.M10 |
| 57 | dev.Q2 | Q2 | cabinet | estimated ±20 % size; shaft place from stage 1 | row, order, size (width x height x depth), plate text | housing.M12 housing.M10 |
| 58 | pass.shaft_Q2 | Q2 | cabinet wall | estimated ±20 (shaft Ø10 assumed) | is the hole or shaft there; place and diameter | housing.M12 housing.M10 |
| 59 | dev.S4 | S4 | cabinet | estimated ±20 % size; shaft place from stage 1 | row, order, size (width x height x depth), plate text | housing.M12 housing.M10 |
| 60 | pass.shaft_S4 | S4 | cabinet wall | estimated ±20 (shaft Ø22 assumed) | is the hole or shaft there; place and diameter | housing.M12 housing.M10 |
| 61 | dev.S2 | S2 | cabinet | estimated ±20 % size; shaft place from stage 1 | row, order, size (width x height x depth), plate text | housing.M12 housing.M10 |
| 62 | pass.shaft_S2 | S2 | cabinet wall | estimated ±20 (shaft Ø22 assumed) | is the hole or shaft there; place and diameter | housing.M12 housing.M10 |
| 63 | dev.TABLO | TABLO | console | estimated ±30 | fitted? place and size; note: B&R terminal 4E0040.01-590 / 4D1084.00-590 clamped to the cover, 270 x 150 mm ±30 mm; OM p.46 lists the panel controller as 4C 2000.01-510 (check) | housing.M2 housing.M3 |
| 64 | dev.toggle |  | console | estimated ±30 | fitted? place and size; note: toggle switch, no designation in 568 or OM (check) | housing.M2 housing.M3 |
| 65 | dev.S1 | S1 | console | estimated ±20 | fitted? place and size | housing.M2 housing.M3 |
| 66 | dev.white_box |  | console | estimated ±50 | fitted? place and size; note: white box, [likely] retrofit: not in 568 or OM (check) | housing.M2 housing.M3 |
| 67 | dev.terminal_block_1 |  | console | estimated ±50 | fitted? place and size; note: terminal block on the console floor, [likely] retrofit: not in 568 or OM (check) | housing.M2 housing.M3 |
| 68 | dev.terminal_block_2 |  | console | estimated ±50 | fitted? place and size; note: terminal block on the console floor, [likely] retrofit: not in 568 or OM (check) | housing.M2 housing.M3 |
| 69 | pass.shaft_S1 | S1 | console wall | estimated ±20 (stem Ø22 assumed: 22 mm panel hole) | is the hole or shaft there; place and diameter | housing.M2 housing.M3 |
| 70 | dev.E1 | E1 | console outside | [?] estimated ±100 | fitted? place and size; note: LED bar seen where lamp E1 is drawn, [likely] retrofit (not factory); lamp E1 fitted? [?] | housing.M15 housing.M1 |
| 71 | dev.E2 | E2 | console outside | [?] estimated ±100 | fitted? place and size; note: LED bar seen where lamp E2 is drawn, [likely] retrofit (not factory); lamp E2 fitted? [?] | housing.M15 housing.M1 |
| 72 | dev.E3 | E3 | console outside | [?] estimated ±100 | fitted? place and size; note: lamp E3 of 568 at its stage-1 anchor; fitted? [?] | housing.M15 housing.M1 |
| 73 | dev.E4 | E4 | machine | [?] estimated ±100 | fitted? place on the machine; note: lamp E4 of 568 at its stage-1 anchor; fitted? [?] | housing.M15 housing.M1 |
| 74 | conn.XC2 | XC2 | cabinet outside face | [?] label, estimated ±115/250/100 | label, height Z and place Y on the face; note: on the cabinet face toward the machine, low; Y and labels: check | housing.M18 housing.M10 |
| 75 | conn.XC4 | XC4 | cabinet outside face | [?] label, estimated ±115/250/100 | label, height Z and place Y on the face; note: on the cabinet face toward the machine, low; Y and labels: check | housing.M18 housing.M10 |
| 76 | conn.XC1 | XC1 | cabinet outside face | sure (pins), place estimated ±115/250/100 | label, height Z and place Y on the face; note: on the cabinet face toward the machine, low; Y and labels: check | housing.M18 housing.M10 |
| 77 | conn.XC3 | XC3 | cabinet outside face | [?] label, estimated ±115/250/100 | label, height Z and place Y on the face; note: on the cabinet face toward the machine, low; Y and labels: check | housing.M18 housing.M10 |
| 78 | mark.S10 | S10 | machine | estimated ±100 (stage-1 body.S10 class E, error ±5, relative to host button.S10 (error ±100)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | frame.M1 frame.M4 frame.M14 safety_sensors.SS9 |
| 79 | mark.S11 | S11 | machine | estimated ±100 (stage-1 body.S11 class E, error ±5, relative to host button.S11 (error ±100)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | frame.M1 frame.M4 frame.M14 safety_sensors.SS9 |
| 80 | mark.SQ1 | SQ1 | machine | estimated ±100 (stage-1 body.SQ1 class E, error x ±25, y ±7, z ±10, relative to host sensor.SQ1 (error ±100)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | knife.M10 knife.M15 safety_sensors.SS3 |
| 81 | mark.SQ2 | SQ2 | machine | estimated ±100 (stage-1 body.SQ2 class E, error x ±25, y ±7, z ±10, relative to host sensor.SQ2 (error ±100)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | knife.M10 knife.M15 safety_sensors.SS3 |
| 82 | mark.S12 | S12 | machine | estimated ±100 (stage-1 body.S12 class E, error x ±49, y ±15, z ±61, relative to host sensor.S12 (error ±100)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | knife.M9 knife.M15 safety_sensors.SS2 assembly.A4 |
| 83 | mark.S13 | S13 | machine | estimated ±100 (stage-1 body.S13 class E, error x ±10, y ±15, z ±40, relative to host sensor.S13 (error ±100)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | knife.M9 knife.M15 safety_sensors.SS2 assembly.A4 |
| 84 | mark.S14 | S14 | machine | estimated ±100 (stage-1 body.S14 class E, error x ±27, y ±20, z ±10, relative to host sensor.S14 (error ±100)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | knife.M9 knife.M15 safety_sensors.SS2 assembly.A4 |
| 85 | mark.S5 | S5 | machine | estimated ±200 (stage-1 body.S5 class E, error ±15, relative to host sensor.S5 (error ±200)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | knife.M11 safety_sensors.SS4 safety_sensors.SS6 housing.M6 |
| 86 | mark.S19 | S19 | machine | estimated ±200 (stage-1 body.S19 class E, error ±15, relative to host sensor.S19 (error ±200)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | knife.M11 safety_sensors.SS5 safety_sensors.SS6 |
| 87 | mark.S28 | S28 | machine | estimated ±100 (stage-1 body.S28 class E, error x ±5, y ±8, z ±15, relative to host sensor.S28 (error x ±80, y ±10, z ±100)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | clamp.M1 clamp.M7 safety_sensors.SS6 |
| 88 | mark.S30 | S30 | machine | estimated ±100 (stage-1 body.S30 class E, error ±15, relative to host sensor.S30 (error x ±80, y ±50, z ±100)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | clamp.M1 clamp.M7 safety_sensors.SS6 |
| 89 | mark.M3 | M3 | machine | estimated ±350 (stage-1 body.M3 class E, error x ±300, y ±60, z ±60, relative to host motor.M3 (error x ±350, y ±330, z ±150)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | frame.M15 safety_sensors.SS7 assembly.A1 |
| 90 | mark.Y3 | Y3 | machine | estimated ±400 (stage-1 body.Y3 class E, error x ±20, y ±20, z ±41, relative to host valve.Y3 (error ±400)); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | frame.M15 safety_sensors.SS8 assembly.A1 |
| 91 | mark.M1 | M1 | machine | estimated ±200 (stage-1 motor.M1 class E, error ±200); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | knife.M8 |
| 92 | mark.Y10 | Y10 | machine | estimated ±100 (stage-1 clutch.Y10 class E, error ±100); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | knife.M5 |
| 93 | mark.Y01 | Y01 | machine | estimated ±100 (stage-1 magnet.Y01 class E, error ±100); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | knife.M10 knife.M15 safety_sensors.SS3 |
| 94 | mark.Y14 | Y14 | machine | estimated ±100 (stage-1 brake.Y14 class P/E, error x ±50, y ±50, z ±100); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | clamp.M7 safety_sensors.SS6 |
| 95 | mark.Y11 | Y11 | machine | estimated ±150 (stage-1 valve.Y11 class P/E, error x ±100, y ±150, z ±150); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | clamp.M4 assembly.A2 |
| 96 | mark.BR40 | BR40 | machine | estimated ±80 (stage-1 sensor.BR40 class P/E, error x ±15, y ±80, z ±60); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | backgauge.G2c backgauge.G6a backgauge.G6b backgauge.G6c assembly.A2 |
| 97 | mark.S24 | S24 | machine | estimated ±160 (stage-1 sensor.S24 class P/E, error x ±100, y ±160, z ±60); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | backgauge.G4a backgauge.G4b backgauge.G4d backgauge.G4e |
| 98 | mark.S27 | S27 | machine | estimated ±120 (stage-1 sensor.S27 class P/E, error x ±100, y ±120, z ±60); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | backgauge.G4c backgauge.G4d backgauge.G4e |
| 99 | mark.M2 | M2 | machine | estimated ±100 (stage-1 motor.M2 class T/P/E, error x ±50, y ±100, z ±60); marker exact on the model, cable entry estimated ±20 | device place x, y, z on the machine; where its cable enters | backgauge.G3a backgauge.G3b backgauge.G3c |
| 100 | pass.G1 | G1 | cabinet wall | sure (seen), place estimated ±30 | is the hole or shaft there; place and diameter | housing.M9 housing.M10 assembly.A3 |
| 101 | pass.G2 | G2 | cabinet wall | sure (seen), place estimated ±30 | is the hole or shaft there; place and diameter | housing.M9 housing.M10 assembly.A3 |
| 102 | pass.H1 | H1 | machine | [?] estimated ±100 | is the hole or shaft there; place and diameter; note: console back-wall opening (seen) and the column front wall behind it (implied) | housing.M1 housing.M2 |
| 103 | pass.H2 | H2 | machine | [?] estimated ±200 | is the hole or shaft there; place and diameter; note: implied hole, column_left inner wall | housing.M1 |
| 104 | pass.H3a | H3a | machine | [?] estimated ±100 | is the hole or shaft there; place and diameter; note: implied hole, console bottom | housing.M1 |
| 105 | pass.H3b | H3b | machine | [?] estimated ±100 | is the hole or shaft there; place and diameter; note: implied hole, console bottom | housing.M1 |
| 106 | pass.H4 | H4 | machine | [?] estimated ±100 | is the hole or shaft there; place and diameter; note: implied hole, console cover | housing.M2 |
| 107 | pass.H5 | H5 | machine | [?] estimated ±100 | is the hole or shaft there; place and diameter; note: implied hole, console right wall | housing.M1 |
| 108 | pass.H6 | H6 | machine | [?] estimated ±20 | is the hole or shaft there; place and diameter; note: cable channel to the S28 pocket | clamp.M7 |
| 109 | pass.H8 | H8 | machine | [?] estimated ±200 | is the hole or shaft there; place and diameter; note: implied hole, belt pulley cover bottom plate: B4 to S5 and Y10 | housing.M6 knife.M5 |
| 110 | pass.H9 | H9 | machine | [?] estimated ±100 | is the hole or shaft there; place and diameter; note: implied hole, knife lock cover bottom: S14 | knife.M9 knife.M15 safety_sensors.SS2 |
| 111 | pass.H10 | H10 | machine | [?] estimated ±100 | is the hole or shaft there; place and diameter; note: implied hole, knife lock cover bottom: SQ1, SQ2 | knife.M10 knife.M15 safety_sensors.SS3 |
| 112 | pass.H11 | H11 | machine | [?] estimated ±100 | is the hole or shaft there; place and diameter; note: implied hole, knife lock cover bottom: Y01 | knife.M10 knife.M15 safety_sensors.SS3 |
| 113 | B1 | B1 | dev.X10 -> dev.S1 | estimated ±100 (console end seen, rest ±200) | route along path_mm, clip places, length and diameter; which cores it carries | housing.M2 housing.M3 housing.M1 |
| 114 | B1-PLC | B1 | dev.PLC -> junction on B1 | estimated ±100 | route along path_mm, clip places, length and diameter; which cores it carries | housing.M1 housing.M2 |
| 115 | B1-T | B1 | junction on B1 -> dev.TABLO | estimated ±100 | route along path_mm, clip places, length and diameter; which cores it carries | housing.M2 housing.M3 housing.M1 |
| 116 | B1-E1 | B1 | junction on B1 -> dev.E1 | [?] estimated ±100 | route along path_mm, clip places, length and diameter; which cores it carries; note: through hole H3a | housing.M15 housing.M1 housing.M2 |
| 117 | B1-E2 | B1 | junction on B1 -> dev.E2 | [?] estimated ±100 | route along path_mm, clip places, length and diameter; which cores it carries; note: through hole H3b | housing.M15 housing.M1 housing.M2 |
| 118 | B1-E3 | B1 | junction on B1 -> dev.E3 | [?] estimated ±100 | route along path_mm, clip places, length and diameter; which cores it carries; note: up inside the console, through hole H4 | housing.M15 housing.M1 housing.M2 |
| 119 | B1-E4 | B1 | junction on B1 -> dev.E4 | [?] estimated ±100 | route along path_mm, clip places, length and diameter; which cores it carries; note: up the console back wall, through hole H5 | housing.M15 housing.M1 housing.M2 |
| 120 | B5 | B5 | junction on B1 -> mark.S30 | estimated ±200 (no photo) | route along path_mm, clip places, length and diameter; which cores it carries | clamp.M1 clamp.M7 safety_sensors.SS6 |
| 121 | B5-Y14 | B5 | junction on B5 -> mark.Y14 | estimated ±200 | route along path_mm, clip places, length and diameter; which cores it carries | clamp.M7 safety_sensors.SS6 |
| 122 | B5-S28 | B5 | junction on B5 -> clip.B5-S28.c3 | estimated ±200 | route along path_mm, clip places, length and diameter; which cores it carries |  |
| 123 | B5-S28s | B5 | junction on B5-S28 -> junction on B5-S28r | estimated ±200 | route along path_mm, clip places, length and diameter; which cores it carries |  |
| 124 | B5-S28r | B5 | junction on B5-S28s -> mark.S28 | estimated ±200 | route along path_mm, clip places, length and diameter; which cores it carries | clamp.M1 clamp.M7 safety_sensors.SS6 |
| 125 | B5-S28p | B5 | mark.S28 -> stage-1 safety_sensors.S28 | [?] estimated ±20 | route along path_mm, clip places, length and diameter; which cores it carries; note: down the pocket H6 to the switch body (moves with the clamp) |  |
| 126 | B2 | B2 | conn.XC2 -> mark.BR40 | estimated ±200 (conduit at XC2 seen; rest no photo) | route along path_mm, clip places, length and diameter; which cores it carries | backgauge.G2c backgauge.G6a backgauge.G6b backgauge.G6c assembly.A2 |
| 127 | B2-XC4 | B2 | conn.XC4 -> junction on B2 | [?] estimated ±200 (XC4 label [?]) | route along path_mm, clip places, length and diameter; which cores it carries; note: joins the XC2 conduit in the gap |  |
| 128 | B2-F | B2 | junction on B2 -> mark.S10 | estimated ±200 | route along path_mm, clip places, length and diameter; which cores it carries | frame.M1 frame.M4 frame.M14 safety_sensors.SS9 |
| 129 | B2-S11 | B2 | junction on B2-F -> mark.S11 | estimated ±200 | route along path_mm, clip places, length and diameter; which cores it carries | frame.M1 frame.M4 frame.M14 safety_sensors.SS9 |
| 130 | B2-R | B2 | junction on B2 -> mark.S27 | estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries | backgauge.G4c backgauge.G4d backgauge.G4e |
| 131 | B2-S24 | B2 | junction on B2-R -> mark.S24 | estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries | backgauge.G4a backgauge.G4b backgauge.G4d backgauge.G4e |
| 132 | B3 | B3 | conn.XC1 -> mark.M2 | estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries; note: down the cabinet face beside the connectors, floor behind frame.support_left, up its inner wall, table underside at X -330 to the rear (P-clips under the rear table seen, photo 144539) as far as about Y 1580, where the rear table's taper (full width at Y 1334 to X -92.5..92.5 at Y 1806, stage-1 frame spec) leaves the leg; from there round the corner at Y 1680 to about X -228 it runs free, up to 67 mm from the table, then across under the rear table to X -111, down beside frame.keepout.backgauge_drive (X -100..100, Z 635..785, kept free) and along M2's -x and -y faces to the marker; of the route plan's way via frame.rear_stand only the blower branch B3-M3 is kept, and it rises free in front of the stand (no clip on it); the trunk reaches the P-clips seen under the rear table along the table underside, and whether it rises at frame.support_left or at the rear stand is not seen (check) | backgauge.G3a backgauge.G3b backgauge.G3c frame.M19 |
| 133 | B3-XC3 | B3 | conn.XC3 -> junction on B3 | [?] estimated ±200 (XC3 label [?]) | route along path_mm, clip places, length and diameter; which cores it carries; note: joins B3 on the cabinet face | frame.M19 |
| 134 | B3-M3 | B3 | junction on B3 -> mark.M3 | estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries; note: along the floor behind the clamp pedal link's space (envelope.clamp.pedal_link ends at Y 370) to the front of frame.rear_stand, then up free, 28 to 89 mm in front of the stand (near the leg it has only two inclined struts, no face to clip to), held by the floor clips and the blower's clips alone; past the stand's +x side and along the loose blower's front face to the marker; where the real cable rises is not seen (check) | frame.M15 safety_sensors.SS7 assembly.A1 frame.M19 |
| 135 | B3-Y3 | B3 | junction on B3 -> mark.Y3 | [?] estimated ±400 (Y3 place ±400) | route along path_mm, clip places, length and diameter; which cores it carries; note: table underside (dips under leg B2-R at X -250), down beside frame.keepout.backgauge_drive (X -100..100, kept free) to Y3, which stage 1 placed below the keepout | frame.M15 safety_sensors.SS8 assembly.A1 frame.M19 |
| 136 | B4 | B4 | dev.X10 -> mark.M1 | estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries | knife.M8 |
| 137 | B4-Y11 | B4 | junction on B4 -> mark.Y11 | estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries | clamp.M4 assembly.A2 |
| 138 | B4-R | B4 | junction on B4 -> mark.S5 | estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries | knife.M11 safety_sensors.SS4 safety_sensors.SS6 housing.M6 |
| 139 | B4-Y10 | B4 | junction on B4-R -> mark.Y10 | estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries | knife.M5 |
| 140 | B4-S19 | B4 | junction on B4-R -> mark.S19 | estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries | knife.M11 safety_sensors.SS5 safety_sensors.SS6 |
| 141 | B4-K | B4 | junction on B4 -> mark.S12 | [?] estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries; note: up frame.support_right's rear face into frame.column_right (open below), under the knife lock cover to S12; the knife-sensor terminal strip X8 (set 568-70.9001 sheet 1) is not seen in the cabinet: X8 place [?] | knife.M9 knife.M15 safety_sensors.SS2 assembly.A4 |
| 142 | B4-S13 | B4 | junction on B4-K -> mark.S13 | [?] estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries; note: under the lock cover to S13 | knife.M9 knife.M15 safety_sensors.SS2 assembly.A4 |
| 143 | B4-S14 | B4 | junction on B4-K -> mark.S14 | [?] estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries; note: hole H9 in the lock cover's bottom | knife.M9 knife.M15 safety_sensors.SS2 assembly.A4 |
| 144 | B4-SQ1 | B4 | junction on B4-K -> mark.SQ1 | [?] estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries; note: hole H10 in the lock cover's bottom | knife.M10 knife.M15 safety_sensors.SS3 |
| 145 | B4-SQ2 | B4 | junction on B4-SQ1 -> mark.SQ2 | [?] estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries; note: hole H10, beside SQ1 | knife.M10 knife.M15 safety_sensors.SS3 |
| 146 | B4-Y01 | B4 | junction on B4-K -> mark.Y01 | [?] estimated ±200 (no photo of the leg) | route along path_mm, clip places, length and diameter; which cores it carries; note: hole H11 in the lock cover's bottom | knife.M10 knife.M15 safety_sensors.SS3 |
<!-- END ONSITE -->

## 12. Rebuild in a bare copy

On 2026-11-27, after the round-4 changes, four copies were built in empty folders. In each, electrical.glb, placements.csv, bundles.csv and contact_report.txt were deleted first; then layout_3d.py, contact_check.py and spec_tables.py were run there.
- Copy A, what GitHub holds: stage_1_mechanics, stage_2_electronics and .gitignore, without static_dynamic_memory and preparatory_data_analysis. layout_3d.py printed two INFO lines, one per absent folder ("INFO preparatory_data_analysis/ not in this copy: the cited files in it were not checked", and the same for static_dynamic_memory/), and spec_tables.py one for the absent measure-row table; contact_check gave FAIL 0.
- Copy B, a partial copy: copy A plus static_dynamic_memory/blocks/generation_002/artifacts/tables and artifacts/anchors_index.csv. The build exited 0 with three INFO lines, naming the highest absent folders preparatory_data_analysis/, static_dynamic_memory/blocks/generation_002/artifacts/web/ and static_dynamic_memory/blocks/generation_002/sections/; spec_tables.py checked the measure ids against the table; contact_check gave FAIL 0.
- Copy C: copy B plus an empty folder artifacts/web/oez/, so that one cited file (the XC7 datasheet) is missing while its folder is present. The build stopped with "missing source path ... (dev.XC7)", as the rule of section 2 asks.
- Copy D: copy A without stage_2_electronics/netlist. The build stopped with "no thread netlist stage_2_electronics/netlist/*_wires.csv in this copy: the contents of the cable legs are built from it", as section 2 says.

In copies A and B the four rebuilt files and this text, with its regenerated tables, were byte-identical to the repository's (cmp).

## 13. Renders

render_views.py draws both GLB files with PIL (painter's algorithm, orthographic views). The model is drawn faded ("X-ray"), so that bundles inside the frame stay visible, and the electrical layer is drawn on top. Colours: bundles B1-B5 one colour each, clips black, cabinet and console devices orange, field-device markers red, connectors XC1-XC4 purple, passes cyan, plate, rails and ducts blue-grey. These are renders of the real files, not drawings.
- renders/cabinet.png: the cabinet through the door (from -X) and from the front (-Y);
- renders/console.png: the console from the front (-Y), cover faded;
- renders/front.png (from -Y), renders/side_right.png (from +X), renders/top.png (from above): the whole machine with the bundles on their routes;
- renders/overview_oblique.png: from front-left-above (azimuth 35°, elevation 28°).

## 14. Sources of the figures and numbers

| figure or number | source (file and line, table row or photo) | mark |
|---|---|---|
| coordinates, units, X 0 | stage_1_mechanics/spec/frame.md lines 15-19; measure row frame.M2 | sure (X 0 ±20) |
| cabinet X -1420..-1250, Y -200..300, Z 0..1535 (option B) | bodies housing.cabinet of stage_1_mechanics/out/assembly.glb; stage_1_mechanics/spec/housing.md lines 12, 63 | estimated |
| option A: +113 X | T/19_stage1_model_measure_rows.csv rows housing.M9, assembly.A3 | open |
| console X -835..850, Y -454..-394, Z 1190..1535 | body housing.console of assembly.glb | estimated |
| wall thickness 2 mm | contact_check.py, constant WALL (own estimate, ±1) | estimated |
| clamp stroke 130 mm | stage_1_mechanics/spec/clamp.md line 51 (OM page 7: "Подъем штампа 130", clamp lift 130) | sure |
| loop 239 mm; straight distance between the loop's ends 80 mm at rest, 108 mm at full stroke | contact_report.txt SLACK line | computed |
| row centres Z R1-R7 | OM 20261115_023222.jpg (Fig. 10.2) scaled; layout_3d.py ROWDEF | estimated ±60 |
| devices per row and their order | T/16_cabinet_devices.csv (43 rows); photos 143021, 143202, 143210, 143806, 144214, 144220, 144251, 144304, 144309, 144324, 144328 | sure (order) |
| photo against print (section 5): contactor family label EP1C093 on KM6 against OM p.47 (KM6 EP1-C099 B, KM1A and KM1B EP1-C123 B, KM8 EP1-C093 B); K1, K2 plate F. Lütze against OM RE6-0011; panel terminal 4E0040.01-590 / 4D1084.00-590 against OM p.46 controller 4C 2000.01-510; devices in no print: grey box, NOARK pair, toggle switch, white box, two console terminal blocks | photos 144247, 144324, 151912, 151951, 143210, 144304, 151739, 151755, 152007; T/16_cabinet_devices.csv; T/18_manual_device_list.csv (OM pages 46, 47, 49 = OM photos 20261115_023023, 023118, 023314); T/11_568_devices.csv | sure (what is read); each one on the on-site list (check) |
| BMR1 290 x 110 mm, PLC 250 x 110 mm, UG50 140 x 95 mm, ZF2 about 55 mm across, T1 130-180 mm wide | photos 143021, 144328, 143806, 143806, 144220 | estimated ±10/15/15/25/30 % |
| UZ1 64 x 210 x 158 mm | plate "EVF8202-E-V002" on photo 144201 (T/16_cabinet_devices.csv row UZ1) -> the user's Lenze 8200 manual, page 4-3 (preparatory_data_analysis/maxima_documents/operating_instructions_global_drive_frequency_inverters_8200_series/20261112_221036.jpg, rotated), row 8202-V002, columns a, b, e (a plain 8202 is 198 deep). Secondary: WEB/lenze/all4sps_EMZ8201BB.pdf; its text copy shifts the row labels by one, so read the page, not the text | sure (size); place estimated ±60 |
| XC7 45 x 90 x 60 mm | WEB/oez/oez_3243-Z01-06_ZS20.pdf, dimension drawing (text copy oez_3243-Z01-06_ZS20.txt lines 47-62); type ZS 20 read on photo 144214 | W |
| connectors X -1250, Y 50, Z 686, 612, 508, 396 | anchors connector.XC1-XC4 of stage_1_mechanics/out/housing_anchors.json (stage_1_mechanics/spec/housing.md line 118); photo 144555 | estimated ±115 / 250 / 100 |
| console devices X -195, 238, 773 | anchors ref.console_toggle, display.T, button.S1 of housing_anchors.json; photo 152550 | estimated |
| TABLO 270 x 150 mm | photos 151912, 151951 | estimated ±30 mm |
| console opening 150 x 160 mm at about (-770, -394, 1270) | photo 151736; measure rows housing.M1, housing.M2 | estimated ±100 |
| field-device anchors | stage_1_mechanics/out/*_anchors.json; T/19_stage1_model_device_anchors.csv | per anchor |
| gap ≤ 1 mm, overlap ≤ 0.5 mm³, free span ≤ 300 mm | meta orc decision (check 9); contact_check.py, constants GAP, OVL, SPAN | rule |
| a clip where a body lies within 1 mm of the bundle and 150 mm have passed since the last fastening (50 mm where the support ends) | layout_3d.py, function leg() and its docstring (own rule) | rule |
| routes B1-B5, contents | section 22 (route plan); T/17_cable_routes.csv (29 rows); photos 144524, 144534, 144539, 150303, 151736, 151739; set 568-70.9001 sheets 2-8 terminal lists; leg contents read from stage_2_electronics/netlist/*_wires.csv by layout_3d.py, function x10() | estimated ±200 where unseen |
| counts, FAIL 0, spans, end gaps | contact_report.txt line 1 and its PASS lines (section 4, generated) | computed |
| eight of eight mutations caught | output of `contact_check.py --selftest`, 2026-11-27 (lines "selftest ...: FAIL n -> caught") | computed |
