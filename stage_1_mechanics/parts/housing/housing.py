"""Housing of the Adast Maxima MS 115 PS, serial 578.0009 (thread 5, housing).

Builds every housing body from values copied by hand from ../../spec/housing.md (their only
source; check_spec.py reads the spec itself and checks the files written here), runs its own
checks against the published neighbours (out/frame.glb, knife.glb, clamp.glb, backgauge.glb)
and writes, under stage_1_mechanics/out/:
  housing.glb, housing.stl     the housing bodies, mm, machine coordinates, Z up
  housing_anchors.json         device anchors (button.S1, switch.Q1 ...), cabinet, reference points
  housing_report.json          the checks and their results
Machine coordinates: X along the knife, + to the operator's right; Y + from the cutting line
toward the backgauge; Z up; X 0 cut centre, Y 0 cutting line, Z 0 floor.
Run:  python housing.py [--option A|B]   (default B, meta orc DECISION 3)
Exit code 0 = all checks pass, 1 = a check failed (see housing_report.json).
"""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # stage_1_mechanics
OUT = ROOT / "out"

# ---------------------------------------------------------------- values (spec/housing.md)
CABINET_OPTION = "B"          # DECISION 3: B = X -1420..-1250 (model); A = X -1307..-1137 (loser)
Z_TOP = 1535.0                # frame top (T, OM7)
T_SHEET = 3.0                 # sheet thickness of covers and panels (E)

# console (middle cover): trapezoid in X-Z, 60 deep (PH152550 ratios x O; depth E)
CON_Y0, CON_Y1 = -454.0, -394.0
CON_Z0, CON_Z1 = 1190.0, Z_TOP
CON_BOT_X0, CON_BOT_X1 = -778.0, 830.0
CON_TOP_X0, CON_TOP_X1 = -835.0, 850.0

# instrument panel plate (PH150610), holes for the clamp's gauge OZ13 and knobs 4, 3 (clamp X 937)
IP = (860.0, 997.0, -397.0, -394.0, 1189.0, 1454.0)
IP_HOLES = [(937.0, 1377.0, 62.0), (937.0, 1309.0, 32.0), (937.0, 1244.0, 42.0)]

# right front cover (PH150616; OM24 tipped over: rot X about its bottom front edge, E)
RFC = (720.0, 997.0, -397.0, -394.0, 1030.0, 1177.0)
RFC_HOLE = (867.0, 1076.0, 75.0)
RFC_KNOB = (881.0, 1146.0)
RFC_PIVOT = ((RFC[0] + RFC[1]) / 2.0, RFC[2], RFC[4])   # (858.5, -397, 1030)
RFC_MAX_DEG = 90.0

# belt-pulley cover: 5-sided shell open toward the column (X 1400) (F31f, F422)
BPC = (1400.0, 1553.0, -394.0, 545.0, 70.0, 1000.0)

# side panels (E)
RSP = (1400.0, 1403.0, -394.0, 406.0, 1000.0, Z_TOP)
LSP_X0, LSP_X1, LSP_Y0, LSP_Y1, LSP_Z0, LSP_Z1 = -1253.0, -1250.0, -394.0, 406.0, 785.0, Z_TOP

# cabinet (PL 2.8; F102; F422 plan; PH142830): X per option, Y plan (conflict 2), Z floor..top
CAB_X = {"B": (-1420.0, -1250.0), "A": (-1307.0, -1137.0)}
CAB_Y0, CAB_Y1, CAB_Z0, CAB_Z1 = -200.0, 300.0, 0.0, Z_TOP
CAB_SWITCHES = {   # fraction of the front-face width from its left edge (F102), Z (F102 y px x 1.744)
    "switch.Q1": (0.56, 1387.0, 'main switch ("INTER PRINCIPAL")', "F102 (y 180, fraction 0.56); PH142747 (0.58); OM19 (Q1 Z 1380)"),
    "switch.Q2": (0.62, 1282.0, 'M1 switch ("MOTOR M1")', "F102 (y 240, 0.62); PH142747 (0.63)"),
    "switch.S4": (0.43, 1143.0, "blower switch (section 10), left of S2", "F102 (y 320, 0.43); PH142747 (0.54)"),
    "switch.S2": (0.79, 1143.0, "light selector (section 10) [?], right of S4", "F102 (y 320, 0.79); PH142747 (0.82)"),
}

# cover 11: cap over the frame-top opening of the clamp-brake rack (F71, P36 7.4)
C11 = (-80.0, 55.0, 60.0, 150.0, Z_TOP, Z_TOP + 30.0)
PASSAGE_XY = (-70.0, 45.0, 70.0, 150.0)       # DECISION 2 passage footprint (clamp anchors)

# right-support front cover (P36 7.2: the hydraulic box is filled through an opening once the cover in the
# front part of the right support is removed): plate on frame.support_right's front face (Y -214) over the
# support cavity's X span; Z band around the tank OZ1 top (Z 470) and its front filler strip (E, M17)
RSFC = (724.0, 1140.0, -217.0, -214.0, 350.0, 650.0)

# right side table tipping (frame anchor side_table_right.pivot; OM24): information-only sweeps (conflict 15)
ST_NAME = "frame.side_table_right"
ST_READINGS = {
    "frame_published_axis_Y_at_outer_edge": {"axis": (0.0, 1.0, 0.0), "pivot": (1200.0, -644.0, 860.0)},
    "alternative_axis_X_at_front_edge": {"axis": (1.0, 0.0, 0.0), "pivot": (887.5, -894.0, 860.0)},
}

# lamps E1-E4 (F101 front view by its own scale: X 0 at the centre line, 5.10 mm/px from the body lines
# -1250 / +1400; Z 4.52 mm/px from the floor to the frame top); anchors only, class E (M15, conflict 16).
# Each lamp keeps the surface F101 draws it on (r3): E1/E2 keep the drawn X and sit on the model console's
# bottom edge; E3/E4 keep the drawn offset from the console's side edge (11 px = 56 mm at the lamp's height),
# because the model console (photo) is wider than the drawn one (x 355..615 = X -732..594): E3 56 inside the
# left edge on the console face, E4 56 right of the right edge on frame.column_right's front face (Y -394).
LAMP_EDGE_OFFSET = 56.0
LAMPS = {
    "lamp.E1": ((-400.0, -424.0, 1190.0), "under the console's bottom edge, left of the centre (drawn at Z 1248)"),
    "lamp.E2": ((377.0, -424.0, 1190.0), "under the console's bottom edge, right of the centre (drawn at Z 1253)"),
    "lamp.E3": ((-768.0, -454.0, 1467.0), "console front face near its upper left corner, 56 inside the left edge "
                "(drawn 11 px inside; the drawing's own X -675)"),
    "lamp.E4": ((903.0, -394.0, 1474.0), "right column front face just right of the console's upper right corner, "
                "56 right of its edge, above the instrument panel (drawn 11 px outside; the drawing's own X 650)"),
}


# cabinet connectors (F102 side strip, view P: stacked XC2, XC4 round, XC1, XC3 rectangular; Z from the strip's
# y centres 582 / 624 / 684 / 748 by Z = 1535 - (y - 95) x 1.744, rechecked by check_spec F); jobs from OM20
# (p.20 4.5, which prints the encoder's as XC40; XC4 of F102 and OM41 wins, conflict 18); on the cabinet's +X
# face (PH144555), X moves with CABINET_OPTION, Y open along the face (E, M18, conflict 18)
CONNECTORS = {
    "connector.XC2": (686.0, "round, small (view P, top); job (OM20): the machine-to-cabinet link"),
    "connector.XC4": (612.0, "round, larger (view P); job (OM20, OM41 8.3, spec/backgauge.md): the backgauge "
                             "position sensor BR40; OM20 prints it XC40 (conflict 18)"),
    "connector.XC1": (508.0, "rectangular multi-pin (view P); job (OM20): the feed motor, the backgauge motor M2 [?]"),
    "connector.XC3": (396.0, "rectangular multi-pin (view P, bottom); job (OM20): the air-cushion motor, "
                             "the air-table blower M3"),
}


def con_edge_x(z, side):
    """X of the console's left (side 0) or right (side 1) edge at height z (trapezoid, CON_Z0..CON_Z1)."""
    f = (z - CON_Z0) / (CON_Z1 - CON_Z0)
    return (CON_BOT_X0 + f * (CON_TOP_X0 - CON_BOT_X0)) if side == 0 else (CON_BOT_X1 + f * (CON_TOP_X1 - CON_BOT_X1))

# frame cavities' open faces (frame spec): Y -364..376, Z 785..1505 at X -1250 and X 1400
CAVITY_Y, CAVITY_Z = (-364.0, 376.0), (785.0, 1505.0)

# moving groups of the neighbours (rest positions as published)
KNIFE_MOVING = ["knife.holder", "knife.knife"]                       # stroke 0..-150 in Z
CLAMP_MOVING = ["clamp.bar", "clamp.fingers", "clamp.front_block", "clamp.false_plate", "clamp.rack"]  # 0..-130
BG_MOVING = ["backgauge.pusher_body", "backgauge.comb_strip", "backgauge.comb_fingers", "backgauge.link_bar",
             "backgauge.apex_link", "backgauge.apex_bracket", "backgauge.neck", "backgauge.carriage",
             "backgauge.nut"]                                         # face Y 1150 -> 25
KNIFE_STROKE, CLAMP_STROKE, BG_TRAVEL = 150.0, 130.0, 1125.0


def expected_bounds(option):
    cx0, cx1 = CAB_X[option]
    return {
        "console": (CON_TOP_X0, CON_TOP_X1, CON_Y0, CON_Y1, CON_Z0, CON_Z1),
        "instrument_panel": IP,
        "right_front_cover": RFC,
        "belt_pulley_cover": BPC,
        "right_side_panel": RSP,
        "left_side_panel_front": (LSP_X0, LSP_X1, LSP_Y0, CAB_Y0, LSP_Z0, LSP_Z1),
        "left_side_panel_rear": (LSP_X0, LSP_X1, CAB_Y1, LSP_Y1, LSP_Z0, LSP_Z1),
        "cabinet": (cx0, cx1, CAB_Y0, CAB_Y1, CAB_Z0, CAB_Z1),
        "cover_11": C11,
        "right_support_front_cover": RSFC,
    }


# ---------------------------------------------------------------- solids
def box(x0, x1, y0, y1, z0, z1):
    return mf.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def y_cylinder(cx, cz, d, y0, y1, seg=96):
    """Cylinder of diameter d along Y from y0 to y1, axis at (X cx, Z cz)."""
    c = mf.Manifold.cylinder(y1 - y0, d / 2.0, d / 2.0, seg, True).rotate([90.0, 0.0, 0.0])
    return c.translate([cx, (y0 + y1) / 2.0, cz])


def xz_prism(poly_xz, y0, y1):
    """Polygon in the X-Z plane (counter-clockwise seen from -Y), extruded from y0 to y1."""
    m = mf.Manifold.extrude(mf.CrossSection([poly_xz]), y1 - y0).rotate([90.0, 0.0, 0.0])
    b = m.bounding_box()            # (xmin, ymin, zmin, xmax, ymax, zmax); rotation maps local z to -Y
    return m.translate([0.0, y0 - b[1], 0.0])


def open_shell(x0, x1, y0, y1, z0, z1, t, open_side):
    """Box shell of wall t with one face left open: open_side in {'x0', 'z0'}."""
    outer = box(x0, x1, y0, y1, z0, z1)
    if open_side == "x0":
        inner = box(x0 - 1.0, x1 - t, y0 + t, y1 - t, z0 + t, z1 - t)
    else:
        inner = box(x0 + t, x1 - t, y0 + t, y1 - t, z0 - 1.0, z1 - t)
    return outer - inner


def build(option=CABINET_OPTION):
    B = {}
    B["console"] = xz_prism([[CON_BOT_X0, CON_Z0], [CON_BOT_X1, CON_Z0], [CON_TOP_X1, CON_Z1], [CON_TOP_X0, CON_Z1]],
                            CON_Y0, CON_Y1)
    ip = box(*IP)
    for cx, cz, d in IP_HOLES:
        ip = ip - y_cylinder(cx, cz, d, IP[2] - 1.0, IP[3] + 1.0)
    B["instrument_panel"] = ip
    B["right_front_cover"] = box(*RFC) - y_cylinder(RFC_HOLE[0], RFC_HOLE[1], RFC_HOLE[2], RFC[2] - 1.0, RFC[3] + 1.0)
    B["belt_pulley_cover"] = open_shell(*BPC, T_SHEET, "x0")
    B["right_side_panel"] = box(*RSP)
    B["left_side_panel_front"] = box(LSP_X0, LSP_X1, LSP_Y0, CAB_Y0, LSP_Z0, LSP_Z1)
    B["left_side_panel_rear"] = box(LSP_X0, LSP_X1, CAB_Y1, LSP_Y1, LSP_Z0, LSP_Z1)
    cx0, cx1 = CAB_X[option]
    B["cabinet"] = box(cx0, cx1, CAB_Y0, CAB_Y1, CAB_Z0, CAB_Z1)
    B["cover_11"] = open_shell(*C11, T_SHEET, "z0")
    B["right_support_front_cover"] = box(*RSFC)
    return B


def rotate_rfc(m, deg):
    """Right front cover turned forward by deg about the X axis through its bottom front edge."""
    p = RFC_PIVOT
    return m.translate([-p[0], -p[1], -p[2]]).rotate([deg, 0.0, 0.0]).translate([p[0], p[1], p[2]])


# ---------------------------------------------------------------- anchors (spec/housing.md, anchors table)
def anchors(option=CABINET_OPTION):
    cx0, cx1 = CAB_X[option]
    w = cx1 - cx0
    A = {}

    def put(name, xyz, cls, err, src, note, **kw):
        A[name] = {"xyz": [round(float(v), 2) for v in xyz], "class": cls, "error_mm": err, "source": src, "note": note}
        A[name].update(kw)

    put("button.S1", (773.0, CON_Y0, 1297.0), "P", [60, 40, 60],
        "PH152550 (plate centre x 1060 = 1.037 O from the left inner face, 0.69 down); F31f", "E-stop (emergency stop), console front face, right end; M3")
    put("display.T", (238.0, CON_Y0, 1354.0), "P", [60, 40, 60],
        "PH152550 (centre x 725.6 = 0.665 O, 0.525 down); OM19 (Z 1260-1420)", "PANELWARE display, not a section-10 device; M3")
    put("ref.console_toggle", (-195.0, CON_Y0, 1366.0), "P", [60, 40, 60], "PH152550 (nut x 455 = 0.364 O)",
        "toggle switch on the console, designation unknown [?]; M3")
    for name, (frac, z, note, src) in CAB_SWITCHES.items():
        put(name, (cx0 + frac * w, CAB_Y0, z), "P", [115, 40, 30], src, note + "; cabinet front face; M12")
    put("cabinet.578-20.0000", ((cx0 + cx1) / 2.0, (CAB_Y0 + CAB_Y1) / 2.0, (CAB_Z0 + CAB_Z1) / 2.0), "P/E",
        [115, 40, 30], "PL 2.8; F102; F422; PH142830",
        "electrical cabinet (электрораспределитель; CZ elektrorozvaděč 578-20.0000), centre of the outer box; option "
        + option + " (DECISION 3); door on the -X face, no door body; M9, M10, M11",
        min=[cx0, CAB_Y0, CAB_Z0], max=[cx1, CAB_Y1, CAB_Z1])
    put("knob.8", (BPC[1], 40.0, 815.0), "P/E", [3, 150, 40], "F31f (Z 810); F422 front view (Z 826); OM11 (Ø60)",
        "knob 8 on the belt-pulley cover's outer face, Y = flywheel axis (E); anchor only; M6")
    put("hole.crank", (BPC[1], 40.0, 629.0), "E", [3, 50, 50], "OM11; NB (knife worm-shaft axis Y 40, Z 629)",
        "hand-crank hole in the belt-pulley cover; place inferred on the worm-shaft axis, not drawn; M6")
    put("hole.right_front_cover", (RFC_HOLE[0], RFC[2], RFC_HOLE[1]), "P", [30, 2, 30], "PH150616",
        "round hole Ø75; inspection hole 6 or another hole [?] (conflict 11); M5")
    put("knob.right_front_cover", (RFC_KNOB[0], RFC[2], RFC_KNOB[1]), "P", [30, 2, 30], "PH150616",
        "black knob on the right front cover [?]; M5")
    put("right_front_cover.pivot", RFC_PIVOT, "E", [30, 2, 30], "OM24",
        "hinge axis along X at the cover's bottom front edge; M5",
        motion={"type": "rotation", "axis": [1, 0, 0], "pivot": list(RFC_PIVOT), "range_deg": [0, RFC_MAX_DEG],
                "direction": "positive about +X: top edge forward (-Y)", "body": "housing.right_front_cover"})
    put("cover.pedal", (0.0, -571.0, 95.0), "E", [260, 100, 95], "F31f (outline X +-216..262, Z 0..190); F31p; PL 15",
        "pedal cover, NOT modelled (depth unknown; inside = clamp pedal-link keep-out); M14")
    put("cover.right_support_front", ((RSFC[0] + RSFC[1]) / 2.0, RSFC[2], (RSFC[4] + RSFC[5]) / 2.0), "E", [200, 3, 100],
        "P36 7.2 (MS 115 PS, DS: the hydraulic box is filled through an opening once the cover in the front part of the right support is removed); "
        "NB (frame.support_right front face Y -214, cavity X 723.7..1140.3)",
        "removable cover on the right support's front face; behind it the filler of the clamp's tank OZ1 (front strip Y -129.8..-77); "
        "size and place E: the placeholder spans the whole cavity X 724..1140, the real cover can sit anywhere along it (X +-200); M17")
    for name, (xyz, note) in LAMPS.items():
        put(name, xyz, "E", [450, 60, 100], "F101 (Fig.10.1 front view, own scale)",
            "lamp " + name.split(".")[1] + ", " + note + "; fitted state open, PH151822 shows two light bars (conflict 16); M15")
    for name, (z, note) in CONNECTORS.items():
        src = "F102 (side strip and view P, Z by its scale); PH144555; OM20 (p.20 4.5: the job)"
        if name == "connector.XC4":
            src += "; OM41 (p.41 8.3: the encoder's outputs through XC4); BGS (sensor.BR40: connector XC4, p41 8.3)"
        put(name, (CAB_X[option][1], (CAB_Y0 + CAB_Y1) / 2.0, z), "E", [115, 250, 100], src,
            "cabinet connector " + name.split(".")[1] + ", " + note + "; on the cabinet's face toward the machine (PH144555), "
            "in the open space before frame.support_left (X -1017.5); place along Y open; conflict 18; M18")
    return A


# ---------------------------------------------------------------- neighbours
def to_trimesh(m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3]
    f = np.asarray(mesh.tri_verts, dtype=np.int64)
    return trimesh.Trimesh(vertices=v, faces=f, process=False)


def tm_to_mf(tm):
    tm = tm.copy()
    tm.merge_vertices()
    mesh = mf.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                   tri_verts=np.asarray(tm.faces, dtype=np.uint32))
    m = mf.Manifold(mesh)
    return None if m.is_empty() or m.volume() <= 0 else m


def load_neighbours():
    """All bodies of out/<part>.glb except the housing's and the assembly's: name -> (Manifold, bounds)."""
    nb, bad = {}, []
    for f in sorted(OUT.glob("*.glb")):
        if f.stem in ("housing", "assembly"):
            continue
        s = trimesh.load(f, force="scene")
        for node in s.graph.nodes_geometry:
            tf, g = s.graph[node]
            tm = s.geometry[g].copy()
            tm.apply_transform(tf)
            m = tm_to_mf(tm)
            if m is None:
                bad.append(node)
                continue
            nb[node] = m
    return nb, bad


def bb(m):
    b = m.bounding_box()
    return np.array(b[:3]), np.array(b[3:])


def bb_touch(a, b, eps=0.5):
    (alo, ahi), (blo, bhi) = a, b
    return bool(np.all(alo < bhi - eps) and np.all(blo < ahi - eps))


def overlap(a, b):
    return float((a ^ b).volume())


# ---------------------------------------------------------------- checks
def checks(bodies, nb, bad, option):
    rep, ok = {"option": option, "checks": {}}, True
    exp = expected_bounds(option)
    # 1. bounds, watertight
    res = {}
    for n, m in bodies.items():
        tm = to_trimesh(m)
        lo, hi = bb(m)
        e = exp[n]
        got = [lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]]
        good = bool(tm.is_watertight and tm.is_volume and m.volume() > 0 and all(abs(g - x) <= 1.0 for g, x in zip(got, e)))
        res[n] = {"bounds": [round(float(g), 2) for g in got], "spec": list(e), "watertight": bool(tm.is_watertight),
                  "volume_mm3": round(float(m.volume()), 1), "pass": good}
        ok &= good
    rep["checks"]["1_bounds_watertight"] = {"pass": all(r["pass"] for r in res.values()), "bodies": res}
    # 2. own pairs
    names, own = list(bodies), []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            v = overlap(bodies[names[i]], bodies[names[j]])
            if v > 1.0:
                own.append([names[i], names[j], round(v, 1)])
    rep["checks"]["2_no_overlap_own"] = {"pass": not own, "pairs": own}
    ok &= not own
    # 3. neighbours at rest
    nbb = {k: bb(m) for k, m in nb.items()}
    rest = []
    for n, m in bodies.items():
        mb = bb(m)
        for k, o in nb.items():
            if bb_touch(mb, nbb[k]):
                v = overlap(m, o)
                if v > 1.0:
                    rest.append([n, k, round(v, 1)])
    r3 = not rest and not bad and len(nb) > 0
    rep["checks"]["3_no_overlap_neighbours_at_rest"] = {"pass": r3, "pairs": rest, "neighbour_bodies": len(nb),
                                                        "unreadable_neighbour_meshes": bad}
    ok &= r3
    # 4. swept motions
    sweeps = {}

    def sweep(group, vectors, label):
        hits, steps, missing = [], 0, [g for g in group if g not in nb]
        for vec in vectors:
            steps += 1
            for g in group:
                if g not in nb:
                    continue
                mv = nb[g].translate(list(vec))
                mvb = bb(mv)
                for n, m in bodies.items():
                    if bb_touch(mvb, bb(m)):
                        v = overlap(mv, m)
                        if v > 1.0:
                            hits.append([g, n, [round(c, 1) for c in vec], round(v, 1)])
        sweeps[label] = {"steps": steps, "hits": hits[:20], "n_hits": len(hits), "missing": missing,
                         "pass": not hits and not missing}

    def steps_to(total, step=10.0):
        s = list(np.arange(0.0, total, step)) + [total]
        return s

    sweep(KNIFE_MOVING, [(0, 0, -d) for d in steps_to(KNIFE_STROKE)], "knife_0_to_-150")
    sweep(CLAMP_MOVING, [(0, 0, -d) for d in steps_to(CLAMP_STROKE)], "clamp_0_to_-130")
    sweep(BG_MOVING, [(0, -d, 0) for d in steps_to(BG_TRAVEL)], "backgauge_face_1150_to_25")
    # right front cover turned 0..90 deg against every other body (own and neighbours)
    others = {**{k: v for k, v in nb.items()}, **{"housing." + n: m for n, m in bodies.items() if n != "right_front_cover"}}
    obb = {k: bb(m) for k, m in others.items()}
    hits, angs = [], list(np.arange(0.0, RFC_MAX_DEG, 5.0)) + [RFC_MAX_DEG]
    for a in angs:
        mv = rotate_rfc(bodies["right_front_cover"], float(a))
        mvb = bb(mv)
        for k, o in others.items():
            if bb_touch(mvb, obb[k]):
                v = overlap(mv, o)
                if v > 1.0:
                    hits.append([k, float(a), round(v, 1)])
    end = bb(rotate_rfc(bodies["right_front_cover"], RFC_MAX_DEG))
    dir_ok = bool(abs(end[0][1] - (RFC[2] - (RFC[5] - RFC[4]))) < 1.0 and end[1][2] < RFC[4] + T_SHEET + 1.0)
    sweeps["right_front_cover_0_to_90deg"] = {"steps": len(angs), "hits": hits[:20], "n_hits": len(hits),
                                              "end_bounds": [end[0].round(1).tolist(), end[1].round(1).tolist()],
                                              "turns_forward": dir_ok, "pass": not hits and dir_ok}
    s_ok = all(s["pass"] for s in sweeps.values())
    rep["checks"]["4_swept_motions"] = {"pass": s_ok, "sweeps": sweeps}
    ok &= s_ok
    # 5. belt-pulley cover: knife bodies inside keep >= 5 from its walls
    x0, x1, y0, y1, z0, z1 = BPC
    inner = (x1 - T_SHEET, y0 + T_SHEET, y1 - T_SHEET, z0 + T_SHEET, z1 - T_SHEET)
    gaps, c_ok = {}, True
    for k, m in nb.items():
        if not k.startswith("knife."):
            continue
        lo, hi = nbb[k]
        if hi[0] <= x0 + 0.5:
            continue                               # wholly at the column side of the open face
        g = min(inner[0] - hi[0], lo[1] - inner[1], inner[2] - hi[1], lo[2] - inner[3], inner[4] - hi[2])
        gaps[k] = round(float(g), 1)
        c_ok &= g >= 5.0
    rep["checks"]["5_belt_cover_clearance_ge_5"] = {"pass": bool(c_ok and gaps), "min_gap_mm": gaps}
    ok &= bool(c_ok and gaps)
    # 6. cover 11 over the DECISION 2 passage, standing on the frame top
    c = C11
    c6 = c[0] <= PASSAGE_XY[0] and c[1] >= PASSAGE_XY[1] and c[2] <= PASSAGE_XY[2] and c[3] >= PASSAGE_XY[3] and c[4] == Z_TOP
    rep["checks"]["6_cover_11_over_passage"] = {"pass": bool(c6), "cover": list(c), "passage_xy": list(PASSAGE_XY)}
    ok &= bool(c6)
    # 6b. the frame cavities' open faces are covered (grid every 10 mm in Y and Z)
    # from the BUILT bodies that lie on the open face's plane (left X -1250, right X 1400)
    rects = {"left": [], "right": []}
    for n, m in bodies.items():
        lo, hi = bb(m)
        if abs(hi[0] - LSP_X1) <= 1.0 and lo[0] < LSP_X1:
            rects["left"].append((lo[1], hi[1], lo[2], hi[2]))
        if abs(lo[0] - RSP[0]) <= 1.0 and hi[0] > RSP[0]:
            rects["right"].append((lo[1], hi[1], lo[2], hi[2]))
    unc = {}
    for side, rr in rects.items():
        miss = 0
        for y in np.arange(CAVITY_Y[0], CAVITY_Y[1] + 0.1, 10.0):
            for z in np.arange(CAVITY_Z[0], CAVITY_Z[1] + 0.1, 10.0):
                if not any(r[0] <= y <= r[1] and r[2] <= z <= r[3] for r in rr):
                    miss += 1
        unc[side] = miss
    rep["checks"]["6b_cavity_faces_covered"] = {"pass": not any(unc.values()), "uncovered_grid_points": unc}
    ok &= not any(unc.values())
    # 10. each lamp anchor on the surface F101 draws it on (conflict 16): E1/E2 on the console's bottom edge,
    # E3 on the console face 56 inside its left edge, E4 56 right of its right edge on frame.column_right's front face
    lamps = {}
    for n, (p, _note) in LAMPS.items():
        x, y, z = p
        if n in ("lamp.E1", "lamp.E2"):
            rel = "console bottom edge"
            good = abs(z - CON_Z0) <= 0.5 and con_edge_x(z, 0) <= x <= con_edge_x(z, 1) and CON_Y0 <= y <= CON_Y1
        elif n == "lamp.E3":
            d = x - con_edge_x(z, 0)
            rel = "console face, %.1f inside the left edge" % d
            good = abs(y - CON_Y0) <= 0.5 and CON_Z0 <= z <= CON_Z1 and abs(d - LAMP_EDGE_OFFSET) <= 2.0
        else:
            d = x - con_edge_x(z, 1)
            col = nb.get("frame.column_right")
            on_col = False
            if col is not None:
                lo, hi = bb(col)
                on_col = bool(abs(y - lo[1]) <= 1.0 and lo[0] <= x <= hi[0] and lo[2] <= z <= hi[2])
            rel = "%.1f right of the console's right edge, on frame.column_right's front face: %s" % (d, on_col)
            good = on_col and abs(d - LAMP_EDGE_OFFSET) <= 2.0 and z >= IP[5]
        lamps[n] = {"xyz": list(p), "relation": rel, "pass": bool(good)}
    l_ok = all(v["pass"] for v in lamps.values())
    rep["checks"]["10_lamps_on_their_F101_surface"] = {"pass": l_ok, "lamps": lamps}
    ok &= l_ok
    rep["pass"] = bool(ok)
    return rep


def side_table_info(bodies, nb):
    """Information only (conflict 15): frame.side_table_right turned 5..90 deg (steps of 5) about each reading's
    axis, against every housing body and every other neighbour body at rest; first angle of contact per body."""
    if ST_NAME not in nb:
        return {"note": ST_NAME + " not in out/frame.glb"}
    others = {**{k: v for k, v in nb.items() if k != ST_NAME}, **{"housing." + n: m for n, m in bodies.items()}}
    obb = {k: bb(m) for k, m in others.items()}
    out = {}
    for label, r in ST_READINGS.items():
        p, ax = r["pivot"], r["axis"]

        def turned(a):
            return nb[ST_NAME].translate([-p[0], -p[1], -p[2]]).rotate([ax[0] * a, ax[1] * a, ax[2] * a]).translate(list(p))
        first = {}
        for a in list(np.arange(5.0, 90.0, 5.0)) + [90.0]:
            mv = turned(float(a))
            mvb = bb(mv)
            for k, o in others.items():
                if k not in first and bb_touch(mvb, obb[k]) and overlap(mv, o) > 1.0:
                    first[k] = float(a)
        end = bb(turned(90.0))
        out[label] = {"axis": list(ax), "pivot": list(p), "positive": "right-hand rule about the axis",
                      "first_contact_deg": first, "clear": not first,
                      "end_bounds_90deg": [end[0].round(1).tolist(), end[1].round(1).tolist()]}
    return out


def check_anchor_uniqueness(rep):
    need = ["button.S1", "switch.Q1", "switch.Q2", "switch.S2", "switch.S4", "lamp.E1", "lamp.E2", "lamp.E3", "lamp.E4",
            "connector.XC1", "connector.XC2", "connector.XC3", "connector.XC4"]
    count, cab, mine = {n: [] for n in need}, [], {}
    for f in sorted(OUT.glob("*_anchors.json")):
        a = json.loads(f.read_text(encoding="utf-8"))["anchors"]
        if f.name == "housing_anchors.json":
            mine = a
        for n in a:
            if n in count:
                count[n].append(f.name)
            if n.startswith("cabinet."):
                cab.append(f.name + ":" + n)
    once = all(len(v) == 1 for v in count.values()) and len(cab) == 1
    not_mine = [n for n in ("sensor.S5", "sensor.S19") if n in mine]
    good = bool(once and not not_mine)
    rep["checks"]["7_anchors_once"] = {"pass": good, "where": count, "cabinet": cab, "knife_anchors_wrongly_here": not_mine}
    rep["pass"] = bool(rep["pass"] and good)


COLORS = {"console": [175, 180, 175, 255], "instrument_panel": [215, 205, 170, 255], "right_front_cover": [225, 215, 180, 255],
          "belt_pulley_cover": [225, 215, 180, 255], "right_side_panel": [225, 215, 180, 255],
          "left_side_panel_front": [225, 215, 180, 255], "left_side_panel_rear": [225, 215, 180, 255],
          "cabinet": [205, 200, 185, 255], "cover_11": [225, 215, 180, 255],
          "right_support_front_cover": [225, 215, 180, 255]}


def main():
    option = CABINET_OPTION
    if "--option" in sys.argv:
        option = sys.argv[sys.argv.index("--option") + 1].upper()
    bodies = build(option)
    nb, bad = load_neighbours()
    rep = checks(bodies, nb, bad, option)
    # 8. the other option, built for information only
    other = "A" if option == "B" else "B"
    alt = build(other)["cabinet"]
    rep["checks"]["8_cabinet_other_option_info"] = {
        "option": other, "overlap_with_frame_column_left_mm3": round(overlap(alt, nb["frame.column_left"]), 1)
        if "frame.column_left" in nb else None, "note": "information only (DECISION 3): A needs the frame's left column face near -1117"}
    # 9. the right side table's tipping, both axis readings, for information (conflict 15; frame thread closed)
    rep["checks"]["9_side_table_tipping_info"] = {"readings": side_table_info(bodies, nb),
                                                  "note": "information only (conflict 15, M5): OM24 gives no axis"}
    OUT.mkdir(parents=True, exist_ok=True)
    scene, meshes = trimesh.Scene(), []
    for n, m in bodies.items():
        tm = to_trimesh(m)
        mat = trimesh.visual.material.PBRMaterial(name="housing." + n, baseColorFactor=[c / 255.0 for c in COLORS[n]],
                                                  metallicFactor=0.1, roughnessFactor=0.8)
        tm.visual = trimesh.visual.TextureVisuals(material=mat)
        scene.add_geometry(tm, node_name="housing." + n, geom_name="housing." + n)
        meshes.append(tm)
    scene.metadata["units"] = "mm, machine coordinates, Z up"
    (OUT / "housing.glb").write_bytes(scene.export(file_type="glb"))
    trimesh.util.concatenate(meshes).export(OUT / "housing.stl")
    anc = {"meta": {"part": "housing", "units": "mm", "coordinates": "X along knife +right, Y +rear from cutting line, Z up, Z0 floor",
                    "cabinet_option": option, "errors": "error_mm = [X, Y, Z] to the machine axes",
                    "spec": "spec/housing.md", "script": "parts/housing/housing.py"},
           "anchors": anchors(option)}
    (OUT / "housing_anchors.json").write_text(json.dumps(anc, indent=1, ensure_ascii=False), encoding="utf-8")
    check_anchor_uniqueness(rep)
    (OUT / "housing_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    for k, v in rep["checks"].items():
        extra = ""
        if k.startswith("4_"):
            extra = " " + ", ".join(f"{s}: {d['steps']} steps, {d['n_hits']} hits" for s, d in v["sweeps"].items())
        elif k.startswith("3_"):
            extra = f" neighbours {v['neighbour_bodies']}, pairs {v['pairs']}, unreadable {v['unreadable_neighbour_meshes']}"
        elif k.startswith("5_"):
            extra = f" min gap {min(v['min_gap_mm'].values()) if v['min_gap_mm'] else None}"
        elif k.startswith("8_"):
            extra = f" option {v['option']} overlap with frame.column_left {v['overlap_with_frame_column_left_mm3']} mm3"
        elif k.startswith("9_"):
            extra = " " + "; ".join(f"{s}: " + ("clear" if d.get("clear") else ", ".join(f"{b} {a:g}" for b, a in sorted(
                d.get("first_contact_deg", {}).items(), key=lambda t: t[1]))) for s, d in v["readings"].items())
        elif k.startswith("1_"):
            extra = " " + ", ".join(n for n, r in v["bodies"].items() if not r["pass"])
        elif k.startswith("10_"):
            extra = " " + "; ".join(f"{n.split('.')[1]} {d['relation']}" for n, d in v["lamps"].items())
        print(k, "INFO" if k[0] in "89" else ("PASS" if v.get("pass", True) else "FAIL"), extra)
    print("housing option", option, "|", len(bodies), "bodies |", "ALL PASS" if rep["pass"] else "FAIL")
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
