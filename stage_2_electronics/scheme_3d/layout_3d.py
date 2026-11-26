"""Thread t4 of episode 2: the 3D (three-dimensional) electrical layer on episode 1's read-only model.

Run:   python -B stage_2_electronics/scheme_3d/layout_3d.py
Writes electrical.glb, placements.csv, bundles.csv next to this file. Reads stage_1_mechanics/out only (anchors
*_anchors.json, geometry assembly.glb); needs no static_dynamic_memory file. Check: contact_check.py next to it.
Units mm, machine coordinates (X along the knife, + to the operator's right; Y + from the cutting line to the rear;
Z up, Z 0 = floor), never rescaled. Cabinet option B as built in stage 1 (X -1420..-1250).
Node names: electrical.<class>.<id>; classes dev (cabinet and console devices), mark (field-device markers),
conn (connectors XC1-XC4), mount (plate, rails, ducts), pass (glands, holes), clip, bundle (one node per segment).
Every number is listed with its source in spec/layout_3d.md; the evidence column says how sure it is.
"""
import csv, json, math
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
import contact_check as cc

HERE = Path(__file__).resolve().parent
S1OUT = cc.ROOT / "stage_1_mechanics" / "out"
TB = "static_dynamic_memory/blocks/generation_002/artifacts/tables/"
OMF = "preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/20261115_023222.jpg"
SEC22 = "17_cable_routes.csv"                       # src() adds TB to a bare .csv name


def src(*a):
    return "; ".join(f"preparatory_data_analysis/maxima_photos/20261102_{x}.jpg" if x.isdigit()
                     else (TB + x if x.endswith(".csv") and "/" not in x else x) for x in a)


A, AI = {}, {}                                      # anchor -> xyz; anchor -> (part file, entry)
for f in sorted(S1OUT.glob("*_anchors.json")):
    for k, v in json.loads(f.read_text(encoding="utf-8"))["anchors"].items():
        A.setdefault(k, np.array(v["xyz"], float))
        if k not in AI or AI[k][0].startswith("assembly"):   # prefer the part's own file over the merged one
            AI[k] = (f.name, v)


def err_txt(e):
    """stage-1 error_mm (number, {x,y,z} or [x,y,z]) -> (largest value, text)."""
    if isinstance(e, dict):
        e = [e.get(c, 0) for c in "xyz"]
    if isinstance(e, (list, tuple)):
        e = [float(x) for x in e]
        return max(e), ("±%g" % e[0] if len(set(e)) == 1 else "x ±%g, y ±%g, z ±%g" % tuple(e))
    return float(e or 0), "±%g" % float(e or 0)


def anchor_ev(anchor):
    """Evidence text and source path of a marker row from its stage-1 anchor (finding B: copy status and error)."""
    fn, v = AI[anchor]
    big, t = err_txt(v.get("error_mm"))
    txt = f"stage-1 {anchor} class {v.get('class', '?')}, error {t}"
    srcs = [f"stage_1_mechanics/out/{fn}"]
    if v.get("host_anchor"):
        hb, ht = err_txt(v.get("host_error_mm"))
        big = max(big, hb)
        txt += f", relative to host {v['host_anchor']} (error {ht})"
        if v["host_anchor"] in AI:
            srcs.append(f"stage_1_mechanics/out/{AI[v['host_anchor']][0]}")
    return f"estimated ±{big:g} ({txt}); marker exact on the model, cable entry estimated ±20", srcs
S1 = cc.bodies_s1()
MESH, ROWS, LEGS = {}, [], []
PCOLS = ("item,designation,kind,place,anchor,device_body,x_mm,y_mm,z_mm,box_x_mm,box_y_mm,box_z_mm,size_x_mm,"
         "size_y_mm,size_z_mm,fastened_to,photo_row,moves_with,passes,evidence,source_path,note").split(",")
BCOLS = ("leg,bundle,from_item,to_item,diameter_mm,length_mm,path_mm,clips,contents,moves_with,passes,evidence,"
         "source_path,note").split(",")
f1 = lambda v: f"{v:.1f}"


def bx(lo, hi):
    lo, hi = np.array(lo, float), np.array(hi, float)
    return trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix((lo + hi) / 2))


def cyl(p0, p1, r, sec=16):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    ax = int(np.argmax(np.abs(p1 - p0)))
    b, c = [k for k in range(3) if k != ax]
    pts = []
    for p in (p0, p1):
        for i in range(sec):
            q = p.copy(); q[b] += r * math.cos(2 * math.pi * i / sec); q[c] += r * math.sin(2 * math.pi * i / sec)
            pts.append(q)
    f = [[i, (i + 1) % sec, sec + (i + 1) % sec] for i in range(sec)] + [[i, sec + (i + 1) % sec, sec + i] for i in range(sec)]
    f += [[0, i + 1, i] for i in range(1, sec - 1)] + [[sec, sec + i, sec + i + 1] for i in range(1, sec - 1)]
    m = trimesh.Trimesh(np.array(pts), np.array(f), process=False)
    if m.volume < 0:
        m.invert()
    return m


def add(item, mesh, des, kind, place, ev, srcp, note="", anchor="", dev_body="", fastened="", row="", moves="",
        passes=""):
    lo, hi = mesh.bounds
    c, s = (lo + hi) / 2, hi - lo
    xyz = A[anchor] if anchor else c
    MESH["electrical." + item] = mesh
    ROWS.append(dict(zip(PCOLS, (item, des, kind, place, anchor, dev_body, *map(f1, xyz), *map(f1, c), *map(f1, s),
                                 fastened, row, moves, passes, ev, srcp, note))))
    return mesh


def mfm(mesh):
    return cc.to_mf(mesh)


def hits(mesh, skip=()):
    """Stage-1 bodies (and our placed items) that a mesh overlaps by more than 0.01 mm3."""
    m, lo, hi = mfm(mesh), *mesh.bounds
    out = [n for n, (b, blo, bhi) in S1.items() if n not in skip and cc.near(lo, hi, blo, bhi, 0.0)
           and (m ^ b).volume() > 0.01]
    out += [n for n, me in MESH.items() if n not in skip and cc.near(lo, hi, *me.bounds, 0.0)
            and (m ^ mfm(me)).volume() > 0.01]
    return out


# ---------------------------------------------------------------- cabinet (inside the shell, wall 2 mm estimated)
XB = -1252.0                      # back wall inner face (the wall shared with frame.column_left)
PLATE = (-1254.5, XB)
RAIL = (-1262.0, PLATE[0])
DUCTX = (-1314.5, PLATE[0])
CAB_ROWS = "16_cabinet_devices.csv"
add("mount.plate", bx((PLATE[0], -100, 240), (PLATE[1], 290, 1515)), "", "mounting plate", "cabinet",
    "estimated ±25 % (width), ±60 (height)", src("143021", "144309", CAB_ROWS, OMF),
    "plate about 38 cm wide (photo scale ±25 %), on the back wall's inner face", fastened="housing.cabinet")
for nm, y0, y1, z0, z1 in (("VL", 265, 290, 300, 1336), ("VR", -100, -75, 300, 1336), ("D12", -100, 290, 1336, 1376),
                           ("D23", -75, 265, 1145, 1185), ("D34", -75, 265, 996, 1036), ("D45", -75, 265, 813, 853),
                           ("D56", -75, 265, 649, 689), ("D67", -75, 265, 373, 413)):
    add(f"mount.duct.{nm}", bx((DUCTX[0], y0, z0), (DUCTX[1], y1, z1)), "", "wiring duct", "cabinet",
        "estimated ±30", src("143210", "144251", "144309"), "grey duct between rows and on both sides (photos)",
        fastened="mount.plate")

# rows top-down: (row, Z centre, rail?, first Y, [(designation, width Y, height Z, depth X, photo stem, note)])
ROWDEF = [
    ("1", 1453, False, 255.0, [("BMR1", 290, 110, 30, "143021", "plate reads BMR2, markers 1BMR1-28BMR1: one board")]),
    ("2", 1260, False, 263.0, [("PLC", 250, 110, 90, "144328", "B&R (Bernecker + Rainer) COMPACT P.L.C.")]),
    ("3", 1096, True, 264.5, [("PE", 15, 55, 50, "144309", "3 PE (protective earth) terminals, end label X10"),
                              ("X10", 225, 55, 50, "144309", "terminals 1-45"), ("PE", 15, 55, 50, "144309", "3 PE terminals"),
                              ("X11", 30, 55, 50, "144309", "terminals 1-6")]),
    ("4", 921, True, 264.5, [("KT1", 36, 80, 70, "143210", "OM Fig.10.2 also draws KT1, KT2 at row 4 right (check)"),
                             ("KT2", 36, 80, 70, "143210", ""), ("", 10, 80, 60, "143210", "grey box, no designation seen"),
                             ("QF1", 40, 85, 70, "144304", ""), ("QF2", 38, 85, 70, "144304", ""),
                             ("KM1A", 40, 80, 80, "144304", "OM lists KM1 = KM1A + KM1B: two boxes"),
                             ("KM1B", 38, 80, 80, "144304", ""), ("FA1", 18, 85, 70, "144304", ""),
                             ("FA2", 18, 85, 70, "144304", ""),
                             ("FA3", 18, 85, 70, "144304", "inverter breaker (568 2:18; OM p.41 says FA1: check)"),
                             ("", 18, 85, 70, "144304", "NOARK breaker, no designation (no FA5/FA6 invented)"),
                             ("", 18, 85, 70, "144304", "NOARK breaker, no designation (no FA5/FA6 invented)")]),
    ("5", 750, True, 264.5, [("KM2", 40, 75, 110, "144251", "front auxiliary block"),
                             ("KM3", 40, 75, 110, "144251", "front auxiliary block"), ("KM4", 40, 75, 80, "144251", ""),
                             ("KM8", 40, 75, 80, "144251", ""), ("KM6", 40, 75, 110, "144251", "front auxiliary block"),
                             ("KM7", 40, 75, 80, "144251", "")]),
    ("7", 323, True, 264.5, [("ZF1", 50, 60, 60, "144214", "filter, no plate"), ("XP", 70, 50, 50, "144214", "main terminals"),
                             ("PE", 36, 50, 50, "144214", "6 PE terminals"), ("X5", 68, 50, 50, "144214", "0 V working earth"),
                             ("XC7", 45, 90, 60, "144214", "service socket, size W (web datasheet)"),
                             ("FA4", 18, 85, 70, "144214", "")]),
]
SIZE_EV = {"BMR1": "10 %", "PLC": "15 %"}
pe_n = 0
for row, zc, rail, y, devs in ROWDEF:
    if rail:
        add(f"mount.rail.R{row}", bx((RAIL[0], -75, zc - 17.5), (RAIL[1], 265, zc + 17.5)), "", "DIN rail 35 mm",
            "cabinet", "estimated ±60 (row height from OM Fig.10.2 scaled)", src(OMF, "143210"), f"row {row}",
            fastened="mount.plate")
    for des, w, h, d, stem, note in devs:
        x1 = RAIL[0] if rail else PLATE[0]
        if des == "PE":
            pe_n += 1; item = f"dev.PE{pe_n}"
        else:
            item = "dev." + (des or f"undesignated_R{row}_{len([r for r in ROWS if r['item'].startswith('dev.undes')]) + 1}")
        add(item, bx((x1 - d, y - w, zc - h / 2), (x1, y, zc + h / 2)), des, "cabinet device", "cabinet",
            f"estimated ±{SIZE_EV.get(des, '20 %')} size, ±60 height, order sure (photo)", src(stem, CAB_ROWS, OMF), note,
            fastened=f"mount.rail.R{row}" if rail else "mount.plate", row=row)
        y -= w + 0.9
# row 1: R14 resistor tube on a bolt; row 2: K1, K2 on a short rail; row 6 plate devices (photo 143806)
add("dev.R14", bx((PLATE[0] - 60, -80, 1405), (PLATE[0], -50, 1435)), "R14", "cabinet device", "cabinet",
    "estimated ±20 %", src("143202", CAB_ROWS), "red tube resistor on a bolt", fastened="mount.plate", row="1")
add("mount.rail.R2", bx((RAIL[0], -45, 1242.5), (RAIL[1], 0, 1277.5)), "", "DIN rail 35 mm", "cabinet",
    "estimated ±30", src("144324"), "short rail right of the PLC", fastened="mount.plate")
for i, des in enumerate(("K1", "K2")):
    add(f"dev.{des}", bx((RAIL[0] - 70, -1 - 13 * i - 12, 1220), (RAIL[0], -1 - 13 * i, 1300)), des, "cabinet device",
        "cabinet", "estimated ±20 %", src("144324", CAB_ROWS), "plate reads F. Lütze; OM lists RE6-0011 (check)",
        fastened="mount.rail.R2", row="2")
for des, lo, hi, note in (("UG50", (-50, 115, 475.5), (0, 255, 570.5), "power supply, 14 x 9.5 cm ±15 %"),
                          ("X2", (-40, 40, 560), (0, 80, 590), "terminal strip X2 (N, L), plate mount [?]"),
                          ("ZF2", (-35, 32.5, 452.5), (0, 87.5, 507.5), "round filter about 5.5 cm ±25 %"),
                          ("UZ1", (-140, -72, 418), (0, -8, 628), "Lenze inverter; W 64 x 210 mm front")):
    add(f"dev.{des}", bx((PLATE[0] + lo[0], lo[1], lo[2]), (PLATE[0] + hi[0], hi[1], hi[2])), des, "cabinet device",
        "cabinet", "estimated ±20 %" + ("; W size" if des == "UZ1" else ""), src("143806", CAB_ROWS), note,
        fastened="mount.plate", row="6")
add("dev.T1", bx((-1390, -170, 2), (-1280, -20, 132)), "T1", "cabinet device", "cabinet", "estimated ±30 %",
    src("144220", CAB_ROWS, OMF), "transformer bolted to the floor, right through the door (OM Fig.10.2 centre: check)",
    fastened="housing.cabinet", row="floor")
add("dev.PE_stud", bx((-1300, 278, 50), (-1280, 298, 70)), "PE", "cabinet device", "cabinet", "estimated ±50",
    src(CAB_ROWS), "PE stud on the left wall (photo list)", fastened="housing.cabinet", row="left wall")
add("dev.door_plate", bx((-1418, 20, 1150), (-1417, 120, 1210)), "", "maker plate", "cabinet", "estimated ±100",
    src("142805", CAB_ROWS), "door plate v.č. 4794 (cabinet serial); place on the door estimated",
    fastened="housing.cabinet", row="door")
# switch blocks on the front face's inner side (shafts at the stage-1 anchors), photos 153000, 153015
# (critic finding I) each block reaches its stage-1 handle through the 2 mm wall by a shaft item, which carries the anchor
for des, xs, zs, w, h, d, rs in (("Q1", -1324.8, 1387, 64, 64, 70, 5), ("Q2", -1314.6, 1282, 48, 48, 60, 5),
                                 ("S4", -1346.9, 1143, 30, 40, 40, 11), ("S2", -1285.7, 1143, 30, 40, 40, 11)):
    add(f"dev.{des}", bx((xs - w / 2, -198, zs - h / 2), (xs + w / 2, -198 + d, zs + h / 2)), des, "switch block",
        "cabinet", "estimated ±20 % size; shaft place from stage 1", src("153000", "153015", CAB_ROWS),
        f"contact block behind the wall; the handle is the stage-1 body in front of it, reached by pass.shaft_{des}",
        fastened="housing.cabinet", row="switch plate")
    add(f"pass.shaft_{des}", cyl((xs, -198, zs), (xs, -200, zs), rs), des, "switch shaft", "cabinet wall",
        f"estimated ±20 (shaft Ø{2 * rs} assumed)", src("153000", "153015", CAB_ROWS),
        "shaft through the front wall (2 mm, estimated) from the contact block to the stage-1 handle",
        anchor=f"body.{des}", dev_body=f"safety_sensors.{des}", fastened="housing.cabinet", row="switch plate")

# ---------------------------------------------------------------- console (inner faces: cover Y -452, floor Z 1192)
CY = -452.0
for item, des, lo, hi, ev, stems, note, anc, db in (
        ("dev.TABLO", "TABLO", (103, CY, 1279), (373, CY + 45, 1429), "estimated ±30", ("151912", "151951"),
         "B&R terminal 4E0040.01-590 / 4D1084.00-590 clamped to the cover, 27 x 15 cm ±3 cm", "display.T", ""),
        ("dev.toggle", "", (-210, CY, 1351), (-180, CY + 40, 1381), "estimated ±30", ("151739",),
         "toggle switch, no designation in 568 or OM", "ref.console_toggle", ""),
        ("dev.S1", "S1", (753, CY, 1277), (793, CY + 45, 1317), "estimated ±20", ("151739",),
         "E-stop contact block behind the cover; the mushroom head is the stage-1 body in front, reached by "
         "pass.shaft_S1", "", ""),
        ("dev.white_box", "", (-740, -428, 1192), (-640, -398, 1232), "[likely] retrofit, estimated ±50", ("151755",),
         "white box, not in 568 or OM", "", ""),
        ("dev.terminal_block_1", "", (-600, -428, 1192), (-570, -408, 1232), "[likely] retrofit, estimated ±50",
         ("151755", "152007"), "terminal block on the console floor, not in 568 or OM", "", ""),
        ("dev.terminal_block_2", "", (-560, -428, 1192), (-530, -408, 1232), "[likely] retrofit, estimated ±50",
         ("151755", "152007"), "terminal block on the console floor, not in 568 or OM", "", "")):
    add(item, bx(lo, hi), des, "console device", "console", ev, src(*stems), note, anchor=anc, dev_body=db,
        fastened="housing.console")
add("pass.shaft_S1", cyl((773, CY, 1297), (773, CY - 2, 1297), 11), "S1", "switch stem", "console wall",
    "estimated ±20 (stem Ø22 assumed: 22 mm panel hole)", src("151739"),
    "E-stop stem through the cover (2 mm, estimated) from the contact block to the stage-1 mushroom head",
    anchor="body.S1", dev_body="safety_sensors.S1", fastened="housing.console")
for des, x, note in (("E1", -400, "LED bar seen instead of lamp E1 (fitted? [?])"),
                     ("E2", 377, "LED bar seen instead of lamp E2 (fitted? [?])")):
    add(f"dev.{des}", bx((x - 100, -434, 1175), (x + 100, -414, 1190)), des, "lamp (LED bar)", "console outside",
        "[?] estimated ±100", src("151822", "151755"), note, anchor=f"lamp.{des}", fastened="housing.console")
add("dev.E3", bx((-776, -470, 1459), (-760, -454, 1475)), "E3", "lamp", "console outside", "[?] estimated ±100",
    src("151739"), "lamp E3 of 568 at its stage-1 anchor; fitted? [?]", anchor="lamp.E3", fastened="housing.console")
add("dev.E4", bx((895, -410, 1466), (911, -394, 1482)), "E4", "lamp", "machine", "[?] estimated ±100",
    src("151739"), "lamp E4 of 568 at its stage-1 anchor; fitted? [?]", anchor="lamp.E4", fastened="frame.column_right")

# ---------------------------------------------------------------- connectors on the cabinet's machine-side face
for des, dx, wy, hz, ev in (("XC2", 110, 70, 100, "[?] label, estimated ±115/250/100"),
                            ("XC4", 60, 40, 40, "[?] label, estimated ±115/250/100"),
                            ("XC1", 100, 60, 80, "sure (pins), place estimated ±115/250/100"),
                            ("XC3", 100, 60, 80, "[?] label, estimated ±115/250/100")):
    a = A[f"connector.{des}"]
    add(f"conn.{des}", bx((-1250, a[1] - wy / 2, a[2] - hz / 2), (-1250 + dx, a[1] + wy / 2, a[2] + hz / 2)), des,
        "connector", "cabinet outside face", ev, src("144555", SEC22), "on the cabinet face toward the machine, low; Y and labels: check",
        anchor=f"connector.{des}", fastened="housing.cabinet")


# ---------------------------------------------------------------- field-device markers (16 mm cubes)
def marker(des, anchor, dev_body, options, ev, stems, note="", moves="", size=16.0):
    """A 16 mm cube outside the device, touching its host body; options = [(host body, [faces])]."""
    a = A[anchor]
    for host, faces in options:
        _, lo, hi = S1[host]
        for f in faces:
            ax, sg = "xyz".index(f[1]), (1 if f[0] == "+" else -1)
            opts = []                                     # cross positions: on the anchor, else flush to either side
            for k in range(3):
                if k == ax:
                    opts.append([0.0])
                elif hi[k] - lo[k] >= size:
                    opts.append([min(max(a[k], lo[k] + size / 2), hi[k] - size / 2)])
                else:
                    opts.append([(lo[k] + hi[k]) / 2, hi[k] - size / 2, lo[k] + size / 2])
            hb, m = S1[host][0], None
            for c0 in [np.array((x, y, z)) for x in opts[0] for y in opts[1] for z in opts[2]]:
                c = c0.copy(); c[ax] = (hi[ax] if sg > 0 else lo[ax]) + sg * size / 2
                for _ in range(40):                       # slide toward the host until it touches
                    m = bx(c - size / 2, c + size / 2)
                    g, ov = cc.gap_ovl(mfm(m), hb)
                    if ov > 0.01 or g <= 0.5:
                        break
                    c[ax] -= sg * max(g - 0.25, 0.25)
                if not (ov > 0.01 or g > 1.0 or hits(m)):
                    break
                m = None
            if m is None:
                continue
            d = mf.Manifold.cube((0.2, 0.2, 0.2), True).translate(tuple(a)).min_gap(mfm(m), 2000.0)
            ev, srcs = anchor_ev(anchor)
            add(f"mark.{des}", m, des, "field device", "machine", ev,
                "; ".join([x for x in (src(*stems),) if x] + srcs + ["stage_1_mechanics/out/assembly.glb"]),
                f"marker on the {f} face of {host}; anchor to marker {d:.0f} mm" + (f"; {note}" if note else ""),
                anchor=anchor, dev_body=dev_body, fastened=host, moves=moves)
            return m
    raise SystemExit(f"no free face for {des}")


SS = "safety_sensors."
for des, anc, db, opts, stems, note, mv in (
        ("S10", "body.S10", SS + "S10", [(SS + "S10", ["-z", "+x"])], ("150303",), "push face kept free", ""),
        ("S11", "body.S11", SS + "S11", [(SS + "S11", ["-z", "-x"])], ("150303",), "push face kept free", ""),
        ("SQ1", "body.SQ1", SS + "SQ1", [(SS + "SQ1", ["+x", "-x", "+z", "-z"]), ("knife.lock_cover", ["+z", "-x"])], (), "", ""),
        ("SQ2", "body.SQ2", SS + "SQ2", [(SS + "SQ2", ["+x", "-x", "+z", "-z"]), ("knife.lock_cover", ["-x", "+z"])], (), "", ""),
        ("S12", "body.S12", SS + "S12", [(SS + "S12", ["+z", "-x"])], (), "-Y face against the gear box", ""),
        ("S13", "body.S13", SS + "S13", [(SS + "S13", ["+x", "+z"])], (), "-Y face against the gear box", ""),
        ("S14", "body.S14", SS + "S14", [(SS + "S14", ["+y", "+z", "-x"]), ("knife.lock_cover", ["-x", "+z"])], (), "", ""),
        ("S5", "body.S5", SS + "S5", [(SS + "S5", ["-z", "-x"])], (), "+X face against the belt cover", ""),
        ("S19", "body.S19", SS + "S19", [(SS + "S19", ["+z", "-z"])], (), "", ""),
        ("S28", "body.S28", SS + "S28", [("clamp.bar", ["+z"])], (),
         "exception: S28 sits in its pocket in clamp.front_block; marker on the bar top above it, pocket leg B5-S28p "
         "reaches the switch body", "clamp"),
        ("S30", "body.S30", SS + "S30", [(SS + "S30", ["+z"])], (), "-Y face against clamp.bar", ""),
        ("M3", "body.M3", SS + "M3", [(SS + "M3", ["-y", "-x"])], (), "anchor at the body centre", ""),
        ("Y3", "body.Y3", SS + "Y3", [(SS + "Y3", ["-x", "-y"])], (), "anchor at the body centre", ""),
        ("M1", "motor.M1", "knife.m1_motor", [("knife.m1_motor", ["-y", "+z"])], (), "anchor inside the motor", ""),
        ("Y10", "clutch.Y10", "knife.clutch_y10", [("knife.slip_rings", ["-z", "+y"])], (),
         "exception: marker at the slip rings, Y10's electrical feed point (section 22); anchor inside the clutch", ""),
        ("Y01", "magnet.Y01", "knife.y01_magnet", [("knife.y01_magnet", ["+z", "-x"]), ("knife.lock_cover", ["+z"])], (),
         "anchor inside the magnet", ""),
        ("Y14", "brake.Y14", "clamp.brake_y14", [("clamp.brake_y14", ["+z"])], (), "anchor inside the brake", ""),
        ("Y11", "valve.Y11", "clamp.valve_block_ov2", [("clamp.valve_block_ov2", ["+z", "-y"])], (),
         "anchor inside the valve block", ""),
        ("BR40", "sensor.BR40", "backgauge.encoder_BR40", [("backgauge.encoder_BR40", ["-x", "+x", "-z"])], (),
         "anchor inside the encoder", ""),
        ("S24", "sensor.S24", "backgauge.S24", [("backgauge.S24", ["-y", "-x"])], (), "anchor inside the switch", ""),
        ("S27", "sensor.S27", "backgauge.S27", [("backgauge.S27", ["-y", "-x"])], (), "anchor inside the switch", ""),
        ("M2", "motor.M2", "backgauge.M2", [("backgauge.M2", ["-y", "-x"])], (), "anchor inside the motor", "")):
    marker(des, anc, db, opts, "sure (stage-1 anchor), cable entry estimated ±20", stems, note, mv)
ROWS.append(dict(zip(PCOLS, ("", "FF1", "light curtain", "machine", "sensor.FF1", "", *map(f1, A["sensor.FF1"]),
                             "", "", "", "", "", "", "", "", "", "", "sure", src("18_manual_device_list.csv"),
                             "not fitted (certificate —): no box, no leg"))))

# ---------------------------------------------------------------- passages (holes, grommets, glands)
for nm, p0, p1, r, ev, stems, note in (
        ("G1", (-1254.5, 200, 1165), (-1240, 200, 1165), 15, "sure (seen), place estimated ±30", ("144309",), "grey gland B1, B5"),
        ("G2", (-1254.5, 149, 1165), (-1240, 149, 1165), 15, "sure (seen), place estimated ±30", ("144309",), "grey gland B4"),
        ("H1", (-770, -402, 1270), (-770, -356, 1270), 14, "[?] estimated ±100", ("151736",),
         "console back-wall opening (seen) and the column front wall behind it (implied)"),
        ("H2", (-765, 158, 1424), (-715, 158, 1424), 12, "[?] estimated ±200", (), "implied hole, column_left inner wall"),
        ("H3a", (-400, -424, 1186), (-400, -424, 1196), 7, "[?] estimated ±100", ("151822",), "implied hole, console bottom"),
        ("H3b", (377, -424, 1186), (377, -424, 1196), 7, "[?] estimated ±100", ("151822",), "implied hole, console bottom"),
        ("H4", (-770, -456, 1467), (-770, -449, 1467), 7, "[?] estimated ±100", (), "implied hole, console cover"),
        ("H5", (838, -401, 1474), (854, -401, 1474), 7, "[?] estimated ±100", (), "implied hole, console right wall"),
        ("H6", (-490, 13, 1100), (-490, 13, 1256), 6, "[?] estimated ±20", (), "cable channel to the S28 pocket"),
        ("H8", (1542, 200, 66), (1542, 200, 78), 10, "[?] estimated ±200", (),
         "implied hole, belt pulley cover bottom plate: B4 to S5 and Y10"),
        ("H9", (895, 188, 836), (895, 188, 848), 7, "[?] estimated ±100", (), "implied hole, knife lock cover bottom: S14"),
        ("H10", (921, 352, 836), (921, 352, 848), 16, "[?] estimated ±100", (),
         "implied hole, knife lock cover bottom: SQ1, SQ2"),
        ("H11", (990, 252.5, 836), (990, 252.5, 848), 7, "[?] estimated ±100", (), "implied hole, knife lock cover bottom: Y01")):
    pm = cyl(p0, p1, r)
    walls = "; ".join(sorted(n.replace("electrical.", "") for n in hits(pm)))   # the walls it pierces (finding F)
    add(f"pass.{nm}", pm, nm, "passage", "cabinet wall" if nm[0] == "G" else "machine", ev, src(*stems, SEC22),
        note, fastened=walls, moves="clamp" if nm == "H6" else "")


# ---------------------------------------------------------------- bundles: axis-aligned legs, clips found by probing
MF = {}


def carrier(p, ax, r):
    """Every side (cross axis, sign, body) where a body lies within 1 mm of the tube at p. Bundles carry no clips."""
    others = {}
    for n, me in MESH.items():
        if n.split(".")[1] not in ("bundle", "clip", "pass"):
            if n not in MF:
                MF[n] = mfm(me)
            others[n] = (MF[n], *me.bounds)
    out = []
    for k in [k for k in range(3) if k != ax]:
        j = 3 - ax - k
        for sg in (-1, 1):
            lo, hi = p.copy(), p.copy()
            lo[ax] -= 8; hi[ax] += 8; lo[j] -= 0.4 * r; hi[j] += 0.4 * r
            lo[k], hi[k] = sorted((p[k] + sg * r, p[k] + sg * (r + 1.0)))
            pr = mfm(bx(lo, hi))
            for n, (b, blo, bhi) in list(S1.items()) + list(others.items()):
                if cc.near(lo, hi, blo, bhi, 0.0) and (pr ^ b).volume() > 0.01:
                    out.append((k, sg, n))
                    break
    return out


def leg(name, pts, r, frm, to, contents, ev, stems, note="", passes="", moves="", endclip=False, free=False):
    """One bundle leg. Probes every 25 mm; a clip goes where a body lies within 1 mm of the tube and either 150 mm
    have passed since the last fastening or the support ends at the next probe (at least 50 mm after the last one).
    A clip that would overlap anything but its own bundle is not placed. endclip=True puts a clip on the last point
    and names it as to_item (strain relief before a moving part). free=True places no clip at all: a slack loop
    between a fixed and a moving part (contact_check's SLACK rule tests its length)."""
    pts = [np.array(p, float) for p in pts]
    clips, n = [], len(pts) - 1
    pre = name.split("-")[0]

    def place_clip(q, ax, c):
        touch = {(k, sg) for k, sg, _ in c}
        lo, hi = q.copy(), q.copy()
        lo[ax] -= 8; hi[ax] += 8
        for k in [k for k in range(3) if k != ax]:   # flush on every side that touches a body
            lo[k] = q[k] - (r if (k, -1) in touch else r + 2)
            hi[k] = q[k] + (r if (k, 1) in touch else r + 2)
        box = bx(lo, hi)
        if [h for h in hits(box) if not (h.split(".")[1] in ("bundle", "clip") and h.split(".")[2].split("-")[0] == pre)]:
            return None
        cn = f"clip.{name}.c{len(clips)}"
        MESH["electrical." + cn] = box
        clips.append(f"{cn}@{c[0][2]}")
        return cn

    t0, last = 0.0, (-1e9 if frm.startswith(("junction on ", "stage-1 ")) else 0.0)
    for i in range(n):
        p0, p1 = pts[i].copy(), pts[i + 1].copy()
        d = p1 - p0; L = float(np.linalg.norm(d)); ax = int(np.argmax(np.abs(d)))
        assert L > 0 and abs(L - abs(d[ax])) < 1e-6, f"{name} segment {i} not axis-aligned"
        u = d / L
        e0 = p0 - u * r if i > 0 else p0
        e1 = p1 + u * r if i < n - 1 else p1
        MESH[f"electrical.bundle.{name}.s{i}"] = cyl(e0, e1, r, 8)
        info = []
        for s_ in (np.arange(8.0, L - 8.0 + 1e-6, 25.0) if L >= 16 else []):
            q = p0 + u * s_
            cl, ch = q - (r + 2), q + (r + 2)
            cl[ax], ch[ax] = q[ax] - 8, q[ax] + 8
            if any(cc.near(cl, ch, *me.bounds, 0.0) for k_, me in MESH.items()
                   if k_.startswith(("electrical.pass.", "electrical.mount.duct."))):
                info.append((s_, q, "hold"))           # at or in its duct or passage: held there, no clip
            else:
                info.append((s_, q, carrier(q, ax, r)))
        for j, (s_, q, c) in enumerate(info if not free else ()):
            if c == "hold":
                last = t0 + s_
                continue
            nxt = info[j + 1][2] if j + 1 < len(info) else None
            if c and (t0 + s_ - last >= 150 or (not nxt and t0 + s_ - last >= 50)) and place_clip(q, ax, c):
                last = t0 + s_
        t0 += L
    if endclip:
        q, d = pts[-1], pts[-1] - pts[-2]
        ax = int(np.argmax(np.abs(d)))
        c = carrier(q, ax, r)
        assert c, f"{name}: no body for the end clip"
        to = place_clip(q, ax, c)
        assert to, f"{name}: end clip overlaps"
    length = sum(float(np.linalg.norm(b - a)) for a, b in zip(pts[:-1], pts[1:]))
    LEGS.append(dict(zip(BCOLS, (name, name.split("-")[0], frm, to, f1(2 * r), f1(length),
                                 "; ".join(" ".join(f1(c) for c in p) for p in pts), "; ".join(clips), contents,
                                 moves, passes, ev, src(*stems, SEC22), note))))


B1C = "XC60-XC70 panel data link; supply 33X10, 45X10, PE; E-stop S1 15-16X10; lamps E1-E4 7-13X10"
leg("B1", [(-1287, 200, 1123.5), (-1287, 200, 1165), (-1240, 200, 1165), (-1240, 200, 1270), (-1240, -354, 1270),
           (-770, -354, 1270), (-770, -442, 1270), (-740, -442, 1270), (-740, -442, 1202), (773, -442, 1202),
           (773, -442, 1277)], 10, "dev.X10", "dev.S1", B1C, "estimated ±100 (console end seen, rest ±200)",
    ("151739", "151736"), "X10 -> duct D23 -> gland G1 -> up the cabinet's machine-side face inside frame.cavity.column_left "
    "-> along the column front wall -> console opening H1 -> console floor -> S1", "mount.duct.D23; mount.plate")
leg("B1-PLC", [(-1287, 200, 1205), (-1287, 200, 1165)], 8, "dev.PLC", "junction on B1", "XC60 serial link to the panel",
    "estimated ±100", ("142944",), "PLC socket down into duct D23", "mount.duct.D23")
leg("B1-T", [(238, -442, 1202), (238, -442, 1279)], 8, "junction on B1", "dev.TABLO", "XC70 panel data, panel supply",
    "estimated ±100", ("151739",), "up the cover's inner face to the B&R terminal")
leg("B1-E1", [(-400, -442, 1202), (-400, -424, 1202), (-400, -424, 1190)], 5, "junction on B1", "dev.E1",
    "lamp E1 7-13X10 (which terminals feed the LED bars? [?])", "[?] estimated ±100", ("151822",), "through hole H3a")
leg("B1-E2", [(377, -442, 1202), (377, -424, 1202), (377, -424, 1190)], 5, "junction on B1", "dev.E2",
    "lamp E2 7-13X10 (which terminals feed the LED bars? [?])", "[?] estimated ±100", ("151822",), "through hole H3b")
leg("B1-E3", [(-770, -442, 1270), (-770, -442, 1467), (-770, -454, 1467)], 5, "junction on B1", "dev.E3",
    "lamp E3 7-13X10 [?]", "[?] estimated ±100", (), "up inside the console, through hole H4")
leg("B1-E4", [(740, -442, 1202), (740, -401, 1202), (740, -401, 1474), (895, -401, 1474)], 5, "junction on B1",
    "dev.E4", "lamp E4 7-13X10 [?]", "[?] estimated ±100", (), "up the console back wall, through hole H5")
B5C = "brake Y14 20-21X10; S30 29X10; S28 30X10"
leg("B5", [(-1240, 200, 1200), (-1242, 200, 1200), (-1242, 228, 1200), (-1242, 228, 1497), (-1242, 158, 1497), (-768, 158, 1497),
           (-768, 158, 1424), (-620, 158, 1424), (-620, 158, 1496), (280, 158, 1496), (280, 158, 1281)], 8,
    "junction on B1", "mark.S30", B5C, "estimated ±200 (no photo)", (),
    "up the cabinet face in the column, under its top, hole H2 in the inner wall, crossbar rear face over Y14 to S30")
leg("B5-Y14", [(0, 158, 1496), (0, 200, 1496), (0, 200, 1476)], 6, "junction on B5", "mark.Y14", "brake Y14 20-21X10",
    "estimated ±200", (), "drop onto the brake")
# S28 lead (critic finding H): fixed part to a strain-relief clip at mid-height of the bar's stroke, a free (unclipped)
# slack loop behind the bar, then the part clipped to the bar that rides with the clamp (lift 130 mm, stage-1
# spec/clamp.md line 51; clamp.guide_left is fixed, spec/clamp.md line 94)
leg("B5-S28", [(-706, 158, 1424), (-706, 156, 1424), (-706, 156, 1190)], 6, "junction on B5", "", "S28 30X10",
    "estimated ±200", (), "fixed part: leaves B5 just after hole H2, down the crossbar's and clamp.guide_left's rear "
    "faces to its strain-relief clip at Z 1190, mid-height of the bar's 130 mm stroke", endclip=True)
leg("B5-S28s", [(-706, 156, 1190), (-706, 180, 1190), (-706, 180, 1150), (-640, 180, 1150), (-640, 180, 1235),
                (-640, 156, 1235)], 6, "junction on B5-S28", "junction on B5-S28r", "S28 30X10", "estimated ±200", (),
    "free slack loop, no clips: hangs behind the clamp bar (14 mm clear of its rear face) from the fixed clip to the "
    "first clip on the bar; drawn at rest (clamp up); stays with the fixed parts in the viewer", free=True)
leg("B5-S28r", [(-640, 156, 1235), (-458, 156, 1235), (-458, 156, 1261), (-458, 13, 1261), (-482, 13, 1261)], 6,
    "junction on B5-S28s", "mark.S28", "S28 30X10", "estimated ±200", (),
    "rides with the clamp (0..130 mm down): clipped along the bar's rear face, then over the bar top to the marker",
    moves="clamp")
leg("B5-S28p", [(-490, 13, 1255), (-490, 13, 1101)], 3, "mark.S28", "stage-1 safety_sensors.S28", "S28 30X10",
    "[?] estimated ±20", (), "down the pocket H6 to the switch body (moves with the clamp)", moves="clamp")

# B2: XC2 (+ XC4) -> gap -> down support_left's outer face -> floor in front of it -> base_front -> BR40, S10, S11;
# rear branch (S24, S27) under the clamp levers and up the support's inner wall behind their space (critic finding G)
B2C = "XC2 1-3 S24, S27; XC2 4-9 S10, S11; XC4 1-7 encoder BR40 (I, B, A, 0 V, +24 V, shield)"
UNSEEN = "estimated ±200 (no photo of the leg)"
NOT_SEC22 = ("; section 22's way through the support_left cavity and the clamp tie's window is taken by the clamp's "
             "moving parts (stage-1 envelope.clamp.*, joint.passage.clamp_tie.support_left)")
leg("B2", [(-1140, 50, 686), (-1100, 50, 686), (-1029.5, 50, 686), (-1029.5, 50, 12), (-1029.5, -226, 12),
           (-550.5, -226, 12), (-550.5, -226, 773), (-550.5, -390.5, 773), (-61, -390.5, 773), (-61, -390.5, 725),
           (-49.5, -390.5, 725)],
    12, "conn.XC2", "mark.BR40", B2C, "estimated ±200 (conduit at XC2 seen; rest no photo)", ("144555",),
    "grey corrugated conduit across the 232 mm gap to frame.support_left's outer face, down it to the floor, along the "
    "floor in front of the support, up frame.base_front's front face, table underside to the encoder" + NOT_SEC22)
leg("B2-XC4", [(-1190, 50, 612), (-1100, 50, 612), (-1100, 50, 686)], 6, "conn.XC4", "junction on B2",
    "XC4 1-7 encoder BR40", "[?] estimated ±200 (XC4 label [?])", ("144555",), "joins the XC2 conduit in the gap")
leg("B2-F", [(-550.5, -390.5, 773), (-550.5, -390.5, 779), (-550.5, -723, 779), (-290, -723, 779), (-290, -737, 779),
             (-290, -737, 813.5)], 6, "junction on B2", "mark.S10", "XC2 4-9 S10, S11", "estimated ±200",
    ("150303",), "table underside to its front edge, along the edge, up to the S10 head")
leg("B2-S11", [(-290, -723, 779), (300, -723, 779), (300, -737, 779), (300, -737, 813.5)], 6, "junction on B2-F",
    "mark.S11", "XC2 S11", "estimated ±200", ("150303",), "along the table's front edge to the S11 head")
leg("B2-R", [(-550.5, -226, 12), (-550.5, -226, 8), (-554.5, -226, 8), (-554.5, 180, 8), (-554.5, 180, 777),
             (-250, 180, 777), (-250, 1392, 777), (-250, 1392, 736.5), (-195, 1392, 736.5)], 8, "junction on B2",
    "mark.S27", "XC2 1-3 S24, S27", UNSEEN, (),
    "floor under frame.base_front (open below) and under the clamp levers, up the support's inner wall behind the "
    "levers' space (envelope.clamp.levers_tie ends at Y 160), table underside at X -250 (outside the backgauge "
    "drive) to S27" + NOT_SEC22)
leg("B2-S24", [(-250, 340, 777), (-250, 340, 779), (-163, 340, 779), (-163, 340, 736.5), (-163, 346.5, 736.5)], 6,
    "junction on B2-R", "mark.S24", "XC2 S24", UNSEEN, (), "drop to the S24 switch")
# B3: XC1 (+ XC3) -> down the cabinet face -> floor behind support_left -> up its inner wall -> table underside -> M2
B3C = "XC1 1-3 M2 U V W from UZ1 (shielded); XC3 1-3 + PE blower M3; XC3 5-6 air valve Y3"
leg("B3", [(-1200, 80, 508), (-1200, 110, 508), (-1240, 110, 508), (-1240, 110, 10), (-1240, 246, 10),
           (-552.5, 246, 10), (-552.5, 224, 10), (-552.5, 224, 775), (-330, 224, 775), (-330, 1680, 775),
           (-111, 1680, 775), (-111, 1680, 530), (-80, 1680, 530), (-80, 1555, 530), (-8.5, 1555, 530)], 10,
    "conn.XC1", "mark.M2", B3C, UNSEEN, ("144539",),
    "down the cabinet face beside the connectors, floor behind frame.support_left, up its inner wall, table underside "
    "at X -330 to the rear (the rear table is narrower, about X -355..355, from Y 1340; P-clips under the rear "
    "table seen, photo 144539), across under the rear table to X -111, down beside frame.keepout.backgauge_drive "
    "(X -100..100, Z 635..785, kept free) and along M2's -x and -y faces to the marker")
leg("B3-XC3", [(-1200, 80, 396), (-1200, 110, 396), (-1240, 110, 396)], 8, "conn.XC3", "junction on B3",
    "XC3 M3, Y3", "[?] estimated ±200 (XC3 label [?])", ("144555",), "joins B3 on the cabinet face")
leg("B3-M3", [(-600, 246, 10), (-600, 246, 6), (-600, 380, 6), (235, 380, 6), (235, 1119, 6), (235, 1119, 241.5)],
    6, "junction on B3", "mark.M3", "XC3 1-3 + PE blower M3", UNSEEN, ("144524",),
    "along the floor behind the clamp pedal link's space (envelope.clamp.pedal_link ends at Y 370) to the loose "
    "blower, up its front face")
leg("B3-Y3", [(-330, 900, 775), (-330, 900, 779), (-266, 900, 779), (-266, 900, 762), (-234, 900, 762),
              (-234, 900, 779), (-111, 900, 779), (-111, 900, 589), (-41.5, 900, 589)], 6, "junction on B3",
    "mark.Y3", "XC3 5-6 air valve Y3", "[?] estimated ±400 (Y3 place ±400)", (),
    "table underside (dips under leg B2-R at X -250), down beside frame.keepout.backgauge_drive (X -100..100, kept "
    "free) to Y3, which stage 1 placed below the keepout")
# B4: X10 -> gland G2 -> column_left -> support_left cavity -> window -> table underside -> right drive, knife sensors
B4C = ("M1 1-6X10; Y01 18-19X10; Y11 22-23X10; Y10 and S19, S5 14-15, 24-28X10; knife sensors SQ1, SQ2, S12-S14 "
       "via X8 1-6 (X8 place [?])")
leg("B4", [(-1287, 149, 1123.5), (-1287, 149, 1165), (-1238, 149, 1165), (-1238, 149, 900), (-1238, -100, 900),
           (-1238, -100, 12), (-1238, -256, 12), (-524, -256, 12), (-524, -172, 12), (-524, -172, 773),
           (-524, 26, 773), (627.5, 26, 773), (627.5, 26, 12), (627.5, 248, 12), (1205, 248, 12), (1205, 330, 12),
           (1205, 330, 166.5)], 12, "dev.X10", "mark.M1", B4C,
    UNSEEN, ("144309",), "X10 -> duct D23 -> gland G2 (seen) -> along the cabinet wall inside frame.column_left -> "
    "down the cabinet face to the floor -> floor in front of frame.support_left -> under frame.base_front (open "
    "below) -> up its rear face -> table underside at Y 26 (clear of the clamp levers' and pull rods' spaces, Y "
    "40..160) -> down frame.support_right's inner wall -> floor behind it -> up the motor's front face to M1"
    + NOT_SEC22, "mount.duct.D23; mount.plate")
leg("B4-Y11", [(321, 26, 773), (321, 26, 779), (321, 320, 779), (321, 320, 526.5)], 6, "junction on B4", "mark.Y11",
    "Y11 22-23X10", UNSEEN, (), "table underside, drop to the clamp valve")
leg("B4-R", [(1205, 248, 12), (1205, 248, 8), (1542, 248, 8), (1542, 200, 8), (1542, 200, 286)], 8,
    "junction on B4", "mark.S5", "S5, S19, Y10 14-15, 24-28X10", UNSEEN, (),
    "floor to the drive corner, hole H8 in the belt cover's bottom, up its inner face to S5", "pass.H8")
leg("B4-Y10", [(1542, 200, 100), (1544, 200, 100), (1544, 40, 100), (1544, 40, 561), (1516.5, 40, 561)], 6,
    "junction on B4-R", "mark.Y10", "clutch Y10 via the slip rings", UNSEEN, (),
    "inside the belt cover along its inner face to the slip rings")
leg("B4-S19", [(1230.5, 248, 8), (1230.5, 248, 6), (1230.5, 200, 6), (1230.5, 200, 475.5), (1375, 200, 475.5)], 6,
    "junction on B4-R", "mark.S19", "S19", UNSEEN, (), "up frame.support_right's outer face, across to the switch")
leg("B4-K", [(970, 248, 12), (970, 244, 12), (970, 244, 832), (970, 158, 832), (970, 158, 819.5)], 8,
    "junction on B4", "mark.S12", "X8 knife sensors S12, S13, S14, SQ1, SQ2; magnet Y01", "[?] " + UNSEEN, (),
    "up frame.support_right's rear face into frame.column_right (open below), under the knife lock cover to S12")
leg("B4-S13", [(970, 200, 832), (1052, 200, 832), (1052, 158, 832), (1052, 158, 803.3)], 5, "junction on B4-K",
    "mark.S13", "S13 via X8", "[?] " + UNSEEN, (), "under the lock cover to S13")
leg("B4-S14", [(970, 188, 832), (895, 188, 832), (895, 188, 856.5)], 5, "junction on B4-K", "mark.S14", "S14 via X8",
    "[?] " + UNSEEN, (), "hole H9 in the lock cover's bottom", "pass.H9")
leg("B4-SQ1", [(970, 244, 832), (970, 348.5, 832), (913, 348.5, 832), (913, 348.5, 903.5)], 5, "junction on B4-K",
    "mark.SQ1", "SQ1, SQ2 via X8", "[?] " + UNSEEN, (), "hole H10 in the lock cover's bottom", "pass.H10")
leg("B4-SQ2", [(930, 348.5, 832), (930, 356.5, 832), (930, 356.5, 932), (905.5, 356.5, 932)], 5,
    "junction on B4-SQ1", "mark.SQ2", "SQ2 via X8", "[?] " + UNSEEN, (), "hole H10, beside SQ1", "pass.H10")
leg("B4-Y01", [(970, 244, 832), (990, 244, 832), (990, 252.5, 832), (990, 252.5, 960), (943.5, 252.5, 960)], 5,
    "junction on B4-K", "mark.Y01", "Y01 18-19X10", "[?] " + UNSEEN, (), "hole H11 in the lock cover's bottom",
    "pass.H11")

# ---------------------------------------------------------------- every source path must exist (finding A)
LOCAL = ("static_dynamic_memory/", "preparatory_data_analysis/")   # local only, absent in a bare repository copy
skipped = set()
for r in ROWS + LEGS:
    assert r["source_path"], f"empty source path: {r.get('item') or r.get('leg')}"
    for sp in r["source_path"].split("; "):
        if (cc.ROOT / sp).exists():
            continue
        top = sp.split("/")[0] + "/"
        assert top in LOCAL and not (cc.ROOT / top).exists(), f"missing source path {sp} ({r.get('item') or r.get('leg')})"
        skipped.add(top)
for t in sorted(skipped):
    print(f"INFO {t} not in this copy: its source paths were not checked")

# ---------------------------------------------------------------- write
sc = trimesh.Scene()
for k in sorted(MESH):
    sc.add_geometry(MESH[k], node_name=k, geom_name=k)
sc.metadata["units"] = "mm, machine coordinates, Z up"
(HERE / "electrical.glb").write_bytes(sc.export(file_type="glb"))
for fn, cols, rows in (("placements.csv", PCOLS, ROWS), ("bundles.csv", BCOLS, LEGS)):
    with open(HERE / fn, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n"); w.writeheader(); w.writerows(rows)
print(f"electrical.glb {len(MESH)} nodes; placements.csv {len(ROWS)} rows; bundles.csv {len(LEGS)} legs")
