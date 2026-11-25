"""Frame of the Adast Maxima MS 115 PS, serial 578.0009 (thread 1, frame).

Builds every frame body from values copied by hand from ../../spec/frame.md (their only
source; check_spec.py reads the spec itself and checks the files written here),
runs its own checks and writes, under stage_1_mechanics/out/:
  frame.glb, frame.stl          the frame bodies, mm, machine coordinates, Z up
  frame_anchors.json            device anchors, joints, reference points
  frame_report.json             the checks and their results
Machine coordinates: X along the knife, + to the operator's right; Y + from the
cutting line toward the backgauge; Z up; X 0 cut centre, Y 0 cutting line, Z 0 floor.
Run:  python frame.py   (any working folder; paths come from this file's place)
Exit code 0 = all checks pass, 1 = a check failed (see frame_report.json).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # stage_1_mechanics
OUT = ROOT / "out"

# ---------------------------------------------------------------- values (spec/frame.md)
Y_A = 6.0                    # anchor line A, Y = y_A + 6 (E +-80, M1)
E_Y_A = 80.0                 # error of Y_A (E, spec Datum, measure row M1)
Z_FRAME_TOP = 1535.0         # frame top (T p.7, D Fig. 4.1.2)
Z_TABLE_TOP = 885.0          # table top (E +-100, P19 scaled)
TABLE_DEPTH = 100.0          # table envelope depth (E +-40)
Z_TABLE_UNDER = Z_TABLE_TOP - TABLE_DEPTH   # 785
H_FOOT = 20.0                # foot pad height (E +-10)

# feet (D Fig. 4.2.2 unless noted)
FOOT_Y0, FOOT_Y1 = Y_A - 220.0, Y_A + 230.0     # right foot 220 + 230 = 450 (D); left the same (P)
FOOT_R_CX, FOOT_R_W, FOOT_R_AREA = 932.0, 585.0, 1460.0e2   # width P +-30, area 1460 cm2
FOOT_L_CX, FOOT_L_W, FOOT_L_AREA = -790.0, 455.0, 1130.0e2  # width P +-30, area 1130 cm2
REAR_X, REAR_Y = 0.0, Y_A + 1130.0              # ring foot S3
REAR_D_OUT, REAR_D_IN = 165.0, 150.0            # 37.1 cm2

# side frames (columns), body
X_BODY_L, X_BODY_R = -1250.0, 1400.0            # body lines (D)
Y_BODY0, Y_BODY1 = Y_A - 400.0, Y_A + 400.0     # 800 band (D, centred on A)
X_IN = 720.0                 # half of opening O = 1440 (E +-60 per face)
T_CHEEK = 40.0               # cheek (inner plate) thickness (E +-20)
T_PLATE = 30.0               # front / rear / top plate thickness (E +-20)

# crossbar
CB_Y0, CB_Y1, CB_Z0 = -150.0, 150.0, 1415.0      # E

# base front member between the supports (a rear member was dropped in r5: no source shows it, M19)
BASE_Z0, T_BASE = 150.0, 30.0                    # E

# table
TB_X = 575.0                 # half width, 1150 (T)
TB_LEN = 2630.0              # length incl. rear block (D Fig. 4.1.2)
TB_YR = Y_A + 1895.0         # rear end = rear block end = plan rear apex y_A +1895 (D) -> +1901
TB_YF = TB_YR - TB_LEN       # front edge -729 (D-derived; error +-20 to line A, +-100 to Y 0); losers: plan centre front line -711, W 710
Y_PLAN_FRONT_CL = Y_A - 717.0   # plan centre front line, 900 - 183 in front of A (D) -> -711 (side-table chamfer start)
TAPER_Y = 1334.0             # taper start: mean of F412 (front + 2088 = 1359) and PLAN (y_A +1303 = 1309), P +-50
BLOCK_W, BLOCK_D = 185.0, 95.0   # rear block (P +-30)
SLOT_HW = 20.0                                   # slot 40 wide (E)
# slot ends (P): the backgauge link sits 414...690 behind the pusher face (pusher depth 0,4-0,6 x face
# 1035-1150, P, photos 20261102_150809, PH-cross1 144601, PH-rear 150836) and the face
# runs Y 25...1150 (T p.7), so the link runs Y 439...1840; ends = that travel -/+ half the link (20).
# Rear end: PH-rear 150836 shows the slot running from the link back to a block at the table's rear edge.
SLOT_Y0, SLOT_Y1 = 420.0, 1860.0                 # front end +-300 (link's nearest point 439...715), rear +-40
# keep-out for the backgauge drive (E): spindle on X 0 under the rear table (Fig.3.1 p.14), carriage
# under the table plate with its neck through the slot (Fig.6.3 p.31): no frame body may enter
KO_HW, KO_Y0, KO_Z0 = 100.0, 236.0, 635.0
STICK_W, STICK_H = 20.0, 20.0                    # cutting stick section (E, W hint)

# side tables: the plan's front-most line y_A -900 runs only outside the table width;
# the front view (P19) shows them as one band with the table front, out to X +-1200, 85 high
ST_X_IN, ST_X_OUT = 575.0, 1200.0                # inner = table side (T); outer P +-75
ST_T = 25.0                                      # plate (E +-15)
ST_APRON_Z0, ST_APRON_T = 800.0, 25.0            # front face Z 800..885 (P +-30, front view); apron 25 deep (E)
ST_Y0, ST_Y1 = Y_A - 900.0, Y_BODY0              # front -894 (D, plan), rear -394 = column front (E)
ST_CHAMFER_DX = 98.0                             # inner front corner: 98 across over 183 deep (P +-30)

# rear stand (r5, re-read r7): closed triangle in a Y-Z plane (PH-stand 144524, PH-under 144539; plane P, camera
# at X < 0): both tops behind the foot, at REAR_Y + 65 (near-vertical leg) and REAR_Y + 210 (diagonal leg), P +-60;
# top plane X -180 (E, side from 144539, offset = nearest place keeping the backgauge keep-out free; +-360);
# legs 60 x 60, bar 60 x 30 (E); the third upright in front of the foot is not modelled (place unknown, M11)
RS_X_TOP, RS_DY_NEAR, RS_DY_DIAG = -180.0, 65.0, 210.0
RS_LEG, RS_PLATE_T, RS_BAR_T = 60.0, 10.0, 30.0
M3_DY = 114.0                    # blower M3 centre behind the stand's foot (PH-stand, ~120 px at ~1 mm/px), P +-250

# passages cut for the knife thread (meta orc decision 1 on signal REQUEST_meta_frame_passages_from_t2; E: the
# knife thread's geometry, no frame source): a window through the right cheek where the connecting rod's sweep
# crosses it, and a bore along X through the right support's right wall for worm shaft 14
WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1 = -77.0, -27.0, 870.0, 1110.0
BORE_D, BORE_Y, BORE_Z = 50.0, 40.0, 629.0
KNIFE_REQ = ("stage_1_mechanics/out/knife_anchors.json and spec/knife.md (knife thread t2), asked for in signal "
             "REQUEST_meta_frame_passages_from_t2, taken by meta orc decision 1")

# lifting points (D Fig. 4.1.2): 1505 apart, centre line -> right one 828, eye 152 above the top
LIFT_XR, LIFT_SPAN, LIFT_DZ = 828.0, 1505.0, 152.0


# ---------------------------------------------------------------- solids
def box(x0, x1, y0, y1, z0, z1):
    return mf.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def ring_wall(a, b, area):
    """Wall t of a rectangular ring a x b whose ring area is `area`: a*b - (a-2t)(b-2t) = area."""
    s = a + b
    u = (s - math.sqrt(s * s - 4.0 * area)) / 2.0   # u = 2t
    return u / 2.0


def rect_ring(x0, x1, y0, y1, z0, z1, t):
    outer = box(x0, x1, y0, y1, z0, z1)
    inner = box(x0 + t, x1 - t, y0 + t, y1 - t, z0 - 1.0, z1 + 1.0)
    return outer - inner


def annulus(cx, cy, d_out, d_in, z0, z1, seg=96):
    h = z1 - z0
    o = mf.Manifold.cylinder(h, d_out / 2.0, d_out / 2.0, seg)
    i = mf.Manifold.cylinder(h + 2.0, d_in / 2.0, d_in / 2.0, seg).translate([0, 0, -1.0])
    return (o - i).translate([cx, cy, z0])


def disc(cx, cy, d, z0, z1, seg=96):
    return mf.Manifold.cylinder(z1 - z0, d / 2.0, d / 2.0, seg).translate([cx, cy, z0])


def x_cylinder(x0, x1, cy, cz, d, seg=96):
    """Cylinder of diameter d along X from x0 to x1, axis at (Y cy, Z cz)."""
    c = mf.Manifold.cylinder(x1 - x0, d / 2.0, d / 2.0, seg, True).rotate([0.0, 90.0, 0.0])
    return c.translate([(x0 + x1) / 2.0, cy, cz])


def prism(poly_xy, z0, z1):
    cs = mf.CrossSection([poly_xy])
    return mf.Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])


def column(side):
    """U-shaped side frame: cheek at the opening, front and rear plates, top plate; open outside."""
    if side < 0:
        xo, xi = X_BODY_L, -X_IN
        cheek = box(xi - T_CHEEK, xi, Y_BODY0, Y_BODY1, Z_TABLE_UNDER, Z_FRAME_TOP)
    else:
        xo, xi = X_BODY_R, X_IN
        cheek = box(xi, xi + T_CHEEK, Y_BODY0, Y_BODY1, Z_TABLE_UNDER, Z_FRAME_TOP)
        cheek = cheek - box(xi - 1.0, xi + T_CHEEK + 1.0, WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1)   # rod window (decision 1)
    xa, xb = min(xo, xi), max(xo, xi)
    front = box(xa, xb, Y_BODY0, Y_BODY0 + T_PLATE, Z_TABLE_UNDER, Z_FRAME_TOP)
    rear = box(xa, xb, Y_BODY1 - T_PLATE, Y_BODY1, Z_TABLE_UNDER, Z_FRAME_TOP)
    top = box(xa, xb, Y_BODY0, Y_BODY1, Z_FRAME_TOP - T_PLATE, Z_FRAME_TOP)
    return cheek + front + rear + top


def table():
    hb = BLOCK_W / 2.0
    yb = TB_YR - BLOCK_D
    poly = [(-TB_X, TB_YF), (TB_X, TB_YF), (TB_X, TAPER_Y), (hb, yb), (hb, TB_YR),
            (-hb, TB_YR), (-hb, yb), (-TB_X, TAPER_Y)]
    t = prism(poly, Z_TABLE_UNDER, Z_TABLE_TOP)
    groove = box(-TB_X - 1.0, TB_X + 1.0, -STICK_W / 2.0, STICK_W / 2.0,
                 Z_TABLE_TOP - STICK_H, Z_TABLE_TOP + 1.0)
    slot = box(-SLOT_HW, SLOT_HW, SLOT_Y0, SLOT_Y1, Z_TABLE_UNDER - 1.0, Z_TABLE_TOP + 1.0)
    return t - groove - slot, poly


def side_table(side):
    """Plate with a chamfered inner front corner (plan) and a front apron (front view); side +1 right, -1 left."""
    xc = ST_X_IN + ST_CHAMFER_DX
    poly = [(xc, ST_Y0), (ST_X_OUT, ST_Y0), (ST_X_OUT, ST_Y1), (ST_X_IN, ST_Y1), (ST_X_IN, Y_PLAN_FRONT_CL)]
    if side < 0:
        poly = [(-x, y) for x, y in reversed(poly)]   # mirror and keep the polygon counter-clockwise
    plate = prism(poly, Z_TABLE_TOP - ST_T, Z_TABLE_TOP)
    xa, xb = sorted((side * xc, side * ST_X_OUT))
    apron = box(xa, xb, ST_Y0, ST_Y0 + ST_APRON_T, ST_APRON_Z0, Z_TABLE_TOP - ST_T)
    return plate + apron


def rear_stand():
    h = RS_LEG / 2.0
    z_plate = H_FOOT + RS_PLATE_T                  # 30
    plate = disc(REAR_X, REAR_Y, REAR_D_OUT, H_FOOT, z_plate)
    bottom = box(REAR_X - h, REAR_X + h, REAR_Y - h, REAR_Y + h, z_plate, z_plate + h)
    parts = [plate]
    for dy in (RS_DY_NEAR, RS_DY_DIAG):
        yt = REAR_Y + dy
        topb = box(RS_X_TOP - h, RS_X_TOP + h, yt - h, yt + h, Z_TABLE_UNDER - RS_LEG, Z_TABLE_UNDER)
        parts.append(mf.Manifold.batch_hull([bottom, topb]))
    parts.append(box(RS_X_TOP - h, RS_X_TOP + h, REAR_Y + RS_DY_NEAR - h, REAR_Y + RS_DY_DIAG + h,
                     Z_TABLE_UNDER - RS_BAR_T, Z_TABLE_UNDER))    # flat bar joining the tops, under the table
    out = parts[0]
    for q in parts[1:]:
        out = out + q
    return out


def build():
    wr = ring_wall(FOOT_R_W, FOOT_Y1 - FOOT_Y0, FOOT_R_AREA)
    wl = ring_wall(FOOT_L_W, FOOT_Y1 - FOOT_Y0, FOOT_L_AREA)
    xr0, xr1 = FOOT_R_CX - FOOT_R_W / 2.0, FOOT_R_CX + FOOT_R_W / 2.0
    xl0, xl1 = FOOT_L_CX - FOOT_L_W / 2.0, FOOT_L_CX + FOOT_L_W / 2.0
    tbl, tbl_poly = table()
    bodies = {
        "foot_right": rect_ring(xr0, xr1, FOOT_Y0, FOOT_Y1, 0.0, H_FOOT, wr),
        "foot_left": rect_ring(xl0, xl1, FOOT_Y0, FOOT_Y1, 0.0, H_FOOT, wl),
        "foot_rear": annulus(REAR_X, REAR_Y, REAR_D_OUT, REAR_D_IN, 0.0, H_FOOT),
        "support_right": rect_ring(xr0, xr1, FOOT_Y0, FOOT_Y1, H_FOOT, Z_TABLE_UNDER, wr)
        - x_cylinder(xr1 - wr - 1.0, xr1 + 1.0, BORE_Y, BORE_Z, BORE_D),    # worm-shaft bore (decision 1)
        "support_left": rect_ring(xl0, xl1, FOOT_Y0, FOOT_Y1, H_FOOT, Z_TABLE_UNDER, wl),
        "base_front": box(xl1, xr0, FOOT_Y0, FOOT_Y0 + T_BASE, BASE_Z0, Z_TABLE_UNDER),
        "column_left": column(-1),
        "column_right": column(+1),
        "crossbar": box(-X_IN, X_IN, CB_Y0, CB_Y1, CB_Z0, Z_FRAME_TOP),
        "table": tbl,
        "cutting_stick": box(-TB_X, TB_X, -STICK_W / 2.0, STICK_W / 2.0,
                             Z_TABLE_TOP - STICK_H, Z_TABLE_TOP),
        "side_table_left": side_table(-1),
        "side_table_right": side_table(+1),
        "rear_stand": rear_stand(),
    }
    geo = {"wall_right": wr, "wall_left": wl, "xr": (xr0, xr1), "xl": (xl0, xl1),
           "table_poly": tbl_poly}
    return bodies, geo


# ---------------------------------------------------------------- anchors
def anchors(geo):
    wr, wl = geo["wall_right"], geo["wall_left"]
    xr0, xr1 = geo["xr"]
    xl0, xl1 = geo["xl"]
    OM = "preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/"
    PH = "preparatory_data_analysis/maxima_photos/"
    PLAN = OM + "20261115_011021.jpg (OM p.19 Fig. 4.2.2)"
    F412 = OM + "20261115_005319.jpg (OM p.17 Fig. 4.1.2)"

    def a(xyz, cls, err, src, **kw):
        d = {"xyz": [round(float(v), 1) for v in xyz], "class": cls, "error_mm": err, "source": src}
        d.update(kw)
        return d

    def box_a(lo, hi, cls, err, src, **kw):
        c = [(l + h) / 2.0 for l, h in zip(lo, hi)]
        return a(c, cls, err, src, min=[round(v, 1) for v in lo], max=[round(v, 1) for v in hi], **kw)

    zwin0, zwin1 = Z_TABLE_TOP, CB_Z0
    A = {
        # ---- device anchors, host F (device list OM p.44-46: 20261115_022802, 20261115_023023;
        # wiring set 568-70.9001): exactly five
        "button.S10": a([-290, TB_YF, 845], "P/E", {"x": 100, "y": 20, "z": 100},
                        OM + "20261114_215242.jpg (Fig. 2.1); " + PH + "20261102_144447.jpg; " + PLAN,
                        note="two-hand button, front-table apron, left of centre"),
        "button.S11": a([300, TB_YF, 845], "P/E", {"x": 100, "y": 20, "z": 100},
                        OM + "20261114_215242.jpg (Fig. 2.1); " + PH + "20261102_144447.jpg; " + PLAN,
                        note="two-hand button, front-table apron, right of centre"),
        "sensor.FF1": a([-700, -700, Z_TABLE_TOP], "E", 200, OM + "20261115_004719.jpg (Fig. 3.1)",
                        note="light curtain, option; certificate '-', none in photos: probably not fitted; packing "
                             "list PL2 item 25 'svetelna clona (dle varianty)', 1: listed per variant"),
        "motor.M3": a([0, REAR_Y + M3_DY, 250], "P", {"x": 350, "y": 250, "z": 150},
                      PH + "20261102_144524.jpg (blower ~120 px behind the stand's foot, camera at X < 0 looking +X); "
                      + OM + "20261115_022423.jpg (p.37 Fig. 7.1 pos 26, under the rear table, centre line); "
                      "preparatory_data_analysis/maxima_documents/adast_guillotine_packing_list/20261114_202913.jpg "
                      "(PL1 item 13 'dmychadlo s elektromotorem', its own item with 13.1 cap and 13.2 two rubber "
                      "hoses: a loose unit)",
                      note="air-table blower on a loose block on the floor; the stand's diagonal leg passes in front "
                           "of it (X about -50 near Z 250); y error covers the mirrored camera side (Y 1016)"),
        "valve.Y3": a([0, 900, 600], "E", 400, OM + "20261115_022909.jpg; " + OM + "20261115_022935.jpg (p.45 Fig. "
                      "10.1, undimensioned; leader ends outside the rear-table outline [?])",
                      note="air valve EVJ 2112 of the air table; place not shown"),
        # ---- joints for other threads
        "joint.knife_guides.left": a([-X_IN, 0, (zwin0 + zwin1) / 2], "E", 60, PLAN + "; " + OM + "20261115_022159.jpg, "
                                     "20261115_022253.jpg (p.35-37, holder guides pos 12, 13, 15)",
                                     face={"normal": [1, 0, 0], "y": [Y_BODY0, Y_BODY1], "z": [zwin0, zwin1]}),
        "joint.knife_guides.right": a([X_IN, 0, (zwin0 + zwin1) / 2], "E", 60, PLAN + "; " + OM + "20261115_022159.jpg, "
                                      "20261115_022253.jpg (p.35-37, holder guides pos 12, 13, 15)",
                                      face={"normal": [-1, 0, 0], "y": [Y_BODY0, Y_BODY1], "z": [zwin0, zwin1]}),
        "joint.clamp_guides.left": a([-X_IN, 100, (zwin0 + zwin1) / 2], "E", 60, PLAN,
                                     face={"normal": [1, 0, 0], "y": [Y_BODY0, Y_BODY1], "z": [zwin0, zwin1]},
                                     note="same cheek face as the knife guides; clamp behind the knife line"),
        "joint.clamp_guides.right": a([X_IN, 100, (zwin0 + zwin1) / 2], "E", 60, PLAN,
                                      face={"normal": [-1, 0, 0], "y": [Y_BODY0, Y_BODY1], "z": [zwin0, zwin1]}),
        "frame.cavity.right_support": box_a([xr0 + wr, FOOT_Y0 + wr, H_FOOT], [xr1 - wr, FOOT_Y1 - wr, Z_TABLE_UNDER],
                                            "E", 50, OM + "20261115_022221.jpg (p.36, hydraulic box in the right support)"),
        "frame.cavity.left_support": box_a([xl0 + wl, FOOT_Y0 + wl, H_FOOT], [xl1 - wl, FOOT_Y1 - wl, Z_TABLE_UNDER],
                                           "E", 50, PLAN),
        "frame.cavity.column_right": box_a([X_IN + T_CHEEK, Y_BODY0 + T_PLATE, Z_TABLE_UNDER],
                                           [X_BODY_R, Y_BODY1 - T_PLATE, Z_FRAME_TOP - T_PLATE], "E", 60, PLAN,
                                           note="open to X+ (side panel = housing); worm gear, crank (knife thread)"),
        "frame.cavity.column_left": box_a([X_BODY_L, Y_BODY0 + T_PLATE, Z_TABLE_UNDER],
                                          [-X_IN - T_CHEEK, Y_BODY1 - T_PLATE, Z_FRAME_TOP - T_PLATE], "E", 60, PLAN,
                                          note="open to X-"),
        "frame.cavity.base": box_a([xl1, FOOT_Y0 + T_BASE, BASE_Z0], [xr0, FOOT_Y1, Z_TABLE_UNDER],
                                   "E", 100, OM + "20261114_215031.jpg (p.6, base with M1 and pump)",
                                   note="between the supports, under the table; open below Z 150 and at the rear "
                                        "(no rear member in any source, r5; measure row M19)"),
        "joint.knife_bearing_seat.right_column": a([X_IN + T_CHEEK, 0, 1100], "E", 150, OM + "20261115_004647.jpg "
                                                   "(Fig. 3.1); " + OM + "20261115_012035.jpg (p.21 Fig. 4.3): worm "
                                                   "gear upper right, as drawn",
                                                   note="inner face of the right cheek; the bearing seat itself has no source"),
        "joint.crossbar.underside": a([0, 0, CB_Z0], "E", 50, PH + "20261102_144601.jpg; " + PH + "20261102_150825.jpg",
                                      y=[CB_Y0, CB_Y1], x=[-X_IN, X_IN]),
        # ---- passages cut for the knife thread (meta orc decision 1): names and xyz as the knife thread asked
        "joint.window.conrod.right_cheek": a([X_IN + T_CHEEK / 2.0, (WIN_Y0 + WIN_Y1) / 2.0, (WIN_Z0 + WIN_Z1) / 2.0],
                                             "E", 60, KNIFE_REQ + ": the connecting rod's sweep crosses the right "
                                             "cheek X 720...760 at Y -77...-27, Z 870...1110",
                                             passage=[[X_IN, X_IN + T_CHEEK], [WIN_Y0, WIN_Y1], [WIN_Z0, WIN_Z1]],
                                             note="window cut through the right cheek; it lies inside the guide "
                                                  "face region, so the guide strips must leave it free"),
        "joint.bore.worm_shaft.support_right": a([xr1 - geo["wall_right"] / 2.0, BORE_Y, BORE_Z], "E", 100,
                                                 KNIFE_REQ + ": worm shaft 14 runs along X through the right "
                                                 "support's right wall",
                                                 passage=[[1135.0, 1230.0], [10.0, 70.0], [599.0, 659.0]],
                                                 bore_d=BORE_D, axis=[1, 0, 0],
                                                 note="bore cut through the right support's right wall only; "
                                                      "passage = the knife thread's box around it"),
        "table.top": a([0, 0, Z_TABLE_TOP], "E", 100, OM + "20261115_010448.jpg (p.19 scaled); W 900 pressdepo"),
        "table.underside": a([0, 0, Z_TABLE_UNDER], "E", 110, "table top - envelope depth 100 (E)"),
        "table.front_edge": a([0, TB_YF, Z_TABLE_TOP], "D/E", {"x": 10, "y": 20, "z": 100},
                              PLAN + " (rear apex y_A +1895); " + F412 + " (table length 2630)",
                              note="rear end - 2630; losers: plan centre front line y_A -717 = Y -711 (900 - 183), "
                                   "W 710 (MAXIMAMS115BPa.htm, later variant); spec conflict 5"),
        "table.rear_end": a([0, TB_YR, Z_TABLE_TOP], "D", {"x": 10, "y": 20, "z": 100}, PLAN + " (rear apex y_A +1895 = rear block end, as "
                            + F412 + ")", note="Y through line A: Y_A itself is E +-80 (M1)"),
        "cutting_line": a([0, 0, Z_TABLE_TOP], "D", 0, "definition: Y 0, knife edge meets the stick",
                          x=[-TB_X, TB_X]),
        "cutting_stick.top": a([0, 0, Z_TABLE_TOP], "E", 100, OM + "20261115_013519.jpg (p.23, knife 0,1-0,2 into the stick)",
                               section=[STICK_W, STICK_H], x=[-TB_X, TB_X]),
        "table.slot": box_a([-SLOT_HW, SLOT_Y0, Z_TABLE_UNDER], [SLOT_HW, SLOT_Y1, Z_TABLE_TOP], "P/E",
                            {"width": 20, "front_end": 300, "rear_end": 40},
                            PH + "20261102_150836.jpg (slot from the pusher link back to a block at the table's "
                            "rear edge); ends = link travel Y 439...1840 (face 25...1150, T p.7; link 414...690 "
                            "behind the face: pusher depth 0,4-0,6 of the face, P, photos 20261102_150809.jpg, "
                            "20261102_144601.jpg, 20261102_150836.jpg) -/+ 20",
                            note="width E; the link drops through it to the carriage"),
        "frame.keepout.backgauge_drive": box_a([-KO_HW, KO_Y0, KO_Z0], [KO_HW, TB_YR, Z_TABLE_UNDER], "E",
                                               {"x": 50, "z": 100},
                                               OM + "20261115_004719.jpg (Fig.3.1 p.14, spindle on X 0 under the rear "
                                               "table); 20261115_021648.jpg (Fig.6.3 p.31, carriage under the table "
                                               "plate, neck through the slot)",
                                               note="space kept free for the backgauge spindle, nut, carriage and "
                                               "guide strips; no frame body enters it (checked)"),
        "table.rear_outline": a([0, TAPER_Y, Z_TABLE_TOP], "D/P", 50, F412 + "; " + PLAN,
                                polygon_xy=[[round(x, 1), round(y, 1)] for x, y in geo["table_poly"]]),
        "frame.envelope": box_a([X_BODY_L, Y_BODY0, 0.0], [X_BODY_R, Y_BODY1, Z_FRAME_TOP], "D", 10, PLAN + "; " + F412,
                                note="body lines and 800 band; overall 2860 (-1307 ... +1553) includes housing and drive"),
        "plan.pedal": box_a([-200, Y_A - 617, 0], [200, Y_A - 577, 150], "D/P/E", {"y": 40, "x": 100, "z": 150},
                            PLAN + " (hatched bar: printed chain 50 from the 932 dimension line, y_A -527 by scale, to "
                            "the bar, then 40 = the bar's depth; scaled depth 70 loses to the printed 40, r5)",
                            note="for the clamp thread; X, Z not printed; r1 had y_A -450...-490 (chain misread from "
                                 "the body front), corrected in r2; depth 40 printed (r5)"),
        "lift.eye_left": a([LIFT_XR - LIFT_SPAN, Y_A, Z_FRAME_TOP + LIFT_DZ], "D (X, Z); E (Y)", {"x": 10, "y": 200, "z": 10},
                           F412, note="M36x3 eye bolt (PL 2.5), not modelled; Y placeholder on line A (F412 gives X only)"),
        "lift.eye_right": a([LIFT_XR, Y_A, Z_FRAME_TOP + LIFT_DZ], "D (X, Z); E (Y)", {"x": 10, "y": 200, "z": 10}, F412,
                            note="Y placeholder on line A (F412 gives X only)"),
        "foot.S1": a([FOOT_R_CX, Y_A + 5, 0], "D", 10, PLAN, area_cm2=1460, load_daN=1850),
        "foot.S2": a([FOOT_L_CX, Y_A + 5, 0], "D", 30, PLAN, area_cm2=1130, load_daN=1250),
        "foot.S3": a([REAR_X, REAR_Y, 0], "D", 10, PLAN, area_cm2=37, load_daN=150),
        "side_table_right.pivot": a([ST_X_OUT, (ST_Y0 + ST_Y1) / 2, Z_TABLE_TOP - ST_T], "E", 150,
                                    OM + "20261115_013741.jpg (p.24 §5.1.13: for MS 115 the right side table and "
                                    "the right cover are tipped over, RU опрокинутие, to change the connecting "
                                    "rod's safety screws; MS 80: removed; no hinge, axis or angle on the page)",
                                    motion={"type": "rotate", "axis": [0, 1, 0], "range_deg": [0, 90], "class": "E",
                                            "error": {"pivot_mm": 150, "axis": "Y or X [?]", "range_end_deg": 90},
                                            "basis": "placeholders: P24 gives only 'tipped over'; pivot at the "
                                                     "outer edge, axis along Y, turned until the plate stands "
                                                     "vertical"},
                                    note="tipping T (P24); pivot place, axis direction and range E, not on the "
                                         "page (spec measure row M10)"),
    }
    pl = "preparatory_data_analysis/maxima_documents/adast_guillotine_packing_list/20261114_202935.jpg (PL 21.1, M20x200)"
    for nm, cx, cls in (("left", FOOT_L_CX, "D/P"), ("right", FOOT_R_CX, "D")):
        A[f"anchor_bolt.{nm}_front"] = a([cx, FOOT_Y0, 0], cls, 15, PLAN + " (90x90 pocket drawn centred on the pad's "
                                         "front edge y_A -220; pockets 441 apart by scale); " + pl)
        A[f"anchor_bolt.{nm}_rear"] = a([cx, FOOT_Y1, 0], cls, 15, PLAN + " (pocket drawn centred on the pad's rear "
                                        "edge y_A +230); " + pl)
    # r5: anchors whose Y is computed from Y_A carry Y_A's own error (E +-80, spec Datum, M1) in error_mm;
    # the error relative to line A stays in error_rel_line_A_mm (value = that anchor's y error relative to A)
    via_a = {"foot.S1": 10, "foot.S2": 30, "foot.S3": 10, "frame.envelope": 10,
             "frame.cavity.right_support": 50, "frame.cavity.left_support": 50, "frame.cavity.column_right": 60,
             "frame.cavity.column_left": 60, "frame.cavity.base": 100, "table.front_edge": 20, "table.rear_end": 20,
             "table.rear_outline": 50, "frame.keepout.backgauge_drive": 10, "plan.pedal": 40, "lift.eye_left": 200,
             "lift.eye_right": 200, "side_table_right.pivot": 150, "button.S10": 20, "button.S11": 20,
             "motor.M3": 250}
    via_a.update({f"anchor_bolt.{s}_{e}": 15 for s in ("left", "right") for e in ("front", "rear")})
    for nm, rel_y in via_a.items():
        e = A[nm]["error_mm"]
        rel = dict(e) if isinstance(e, dict) else {"x": e, "y": e, "z": e}
        rel["y"] = rel_y
        A[nm]["error_rel_line_A_mm"] = dict(rel)
        rel["y"] = rel_y + E_Y_A
        A[nm]["error_mm"] = rel
    return A


# ---------------------------------------------------------------- checks
def to_trimesh(m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3]
    f = np.asarray(mesh.tri_verts, dtype=np.int64)
    return trimesh.Trimesh(vertices=v, faces=f, process=False)


def checks(bodies):
    rep, ok = {"bodies": {}, "pairs_overlapping": [], "checks": {}}, True
    meshes = {}
    for n, m in bodies.items():
        tm = to_trimesh(m)
        meshes[n] = tm
        rep["bodies"][n] = {"watertight": bool(tm.is_watertight), "is_volume": bool(tm.is_volume),
                            "volume_mm3": round(float(m.volume()), 1),
                            "bounds": [[round(float(x), 2) for x in r] for r in tm.bounds]}
        if not (tm.is_watertight and tm.is_volume and m.volume() > 0):
            ok = False
    allb = np.array([meshes[n].bounds for n in meshes])
    lo, hi = allb[:, 0, :].min(axis=0), allb[:, 1, :].max(axis=0)
    exp_lo, exp_hi = [X_BODY_L, min(TB_YF, ST_Y0), 0.0], [X_BODY_R, TB_YR, Z_FRAME_TOP]
    bb_ok = bool(np.all(np.abs(lo - exp_lo) <= 1.0) and np.all(np.abs(hi - exp_hi) <= 1.0))
    rep["checks"]["bounding_box"] = {"got": [lo.round(2).tolist(), hi.round(2).tolist()],
                                     "spec": [exp_lo, exp_hi], "pass": bb_ok}
    ok &= bb_ok
    # plan envelope (D Fig. 4.2.2, +-10): X -1307 ... +1553, y_A -900 ... +1895
    env_lo, env_hi = [-1317.0, Y_A - 910.0], [1563.0, Y_A + 1905.0]
    env_ok = bool(lo[0] >= env_lo[0] and lo[1] >= env_lo[1] and hi[0] <= env_hi[0] and hi[1] <= env_hi[1])
    rep["checks"]["plan_envelope"] = {"got_xy": [lo[:2].round(2).tolist(), hi[:2].round(2).tolist()],
                                      "limits_xy": [env_lo, env_hi], "pass": env_ok}
    ok &= env_ok
    areas = {}
    for n in bodies:
        a = bodies[n].slice(1.0).area()
        if a > 0:
            areas[n] = round(a / 100.0, 2)   # cm2
    exp = {"foot_right": 1460.0, "foot_left": 1130.0, "foot_rear": 37.0}
    a_ok = set(areas) == set(exp) and all(abs(areas[k] - v) <= 0.01 * v + 0.2 for k, v in exp.items())
    rep["checks"]["floor_contact_cm2_at_z1"] = {"got": areas, "printed": exp, "pass": a_ok}
    ok &= a_ok
    tt = meshes["table"].bounds[1][2]
    st = meshes["cutting_stick"].bounds
    t_ok = abs(tt - Z_TABLE_TOP) < 0.01 and abs(st[1][2] - Z_TABLE_TOP) < 0.01 and abs(st[0][1] + st[1][1]) < 0.01
    tw = meshes["table"].bounds
    t_ok &= abs(tw[1][0] - tw[0][0] - 1150.0) < 0.01 and abs(tw[1][1] - tw[0][1] - TB_LEN) < 0.01
    rep["checks"]["table_and_stick"] = {"table_bounds": tw.round(2).tolist(), "stick_bounds": st.round(2).tolist(),
                                        "pass": bool(t_ok)}
    ok &= bool(t_ok)
    names = list(bodies)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            v = (bodies[names[i]] ^ bodies[names[j]]).volume()
            if v > 1.0:
                rep["pairs_overlapping"].append([names[i], names[j], round(v, 1)])
    rep["checks"]["no_interpenetration"] = {"pass": not rep["pairs_overlapping"]}
    ko = box(-KO_HW, KO_HW, KO_Y0, TB_YR, KO_Z0, Z_TABLE_UNDER)
    ko_in = {n: round(float((m ^ ko).volume()), 1) for n, m in bodies.items() if (m ^ ko).volume() > 1.0}
    rep["checks"]["keepout_backgauge_drive_free"] = {"box": [[-KO_HW, KO_Y0, KO_Z0], [KO_HW, TB_YR, Z_TABLE_UNDER]],
                                                     "bodies_inside_mm3": ko_in, "pass": not ko_in}
    ok &= not ko_in
    # passages for the knife thread (decision 1): no frame body inside the rod window or the worm-shaft bore
    xr1 = FOOT_R_CX + FOOT_R_W / 2.0
    wr = ring_wall(FOOT_R_W, FOOT_Y1 - FOOT_Y0, FOOT_R_AREA)
    pas = {"window_conrod_right_cheek": box(X_IN, X_IN + T_CHEEK, WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1),
           "bore_worm_shaft_support_right": x_cylinder(xr1 - wr, xr1, BORE_Y, BORE_Z, BORE_D - 0.5)}
    p_in = {p: {n: round(float((m ^ pm).volume()), 1) for n, m in bodies.items() if (m ^ pm).volume() > 1.0}
            for p, pm in pas.items()}
    p_ok = not any(p_in.values())
    rep["checks"]["knife_passages_free"] = {"bodies_inside_mm3": p_in, "pass": p_ok}
    ok &= p_ok
    ok &= not rep["pairs_overlapping"]
    rep["pass"] = bool(ok)
    return rep, meshes


COLORS = {"foot": [70, 70, 70, 255], "support": [150, 160, 145, 255], "base": [150, 160, 145, 255],
          "column": [190, 195, 180, 255], "crossbar": [190, 195, 180, 255], "table": [120, 125, 130, 255],
          "cutting": [240, 240, 235, 255], "side": [185, 200, 160, 255], "rear": [150, 160, 145, 255]}


def main():
    bodies, geo = build()
    rep, meshes = checks(bodies)
    rep["walls_mm"] = {"foot_right": round(geo["wall_right"], 2), "foot_left": round(geo["wall_left"], 2)}
    OUT.mkdir(parents=True, exist_ok=True)
    scene = trimesh.Scene()
    for n, tm in meshes.items():
        rgba = [c / 255.0 for c in COLORS[n.split("_")[0]]]
        mat = trimesh.visual.material.PBRMaterial(name="frame." + n, baseColorFactor=rgba,
                                                  metallicFactor=0.2, roughnessFactor=0.8)
        tm.visual = trimesh.visual.TextureVisuals(material=mat)   # material colour; no scipy needed
        scene.add_geometry(tm, node_name="frame." + n, geom_name="frame." + n)
    scene.metadata["units"] = "mm, machine coordinates, Z up"
    (OUT / "frame.glb").write_bytes(scene.export(file_type="glb"))
    trimesh.util.concatenate(list(meshes.values())).export(OUT / "frame.stl")
    anc = {"meta": {"part": "frame", "units": "mm", "coordinates": "X along knife +right, Y +rear from cutting line, Z up, Z0 floor",
                    "y_anchor_line_A": Y_A, "y_anchor_line_A_error": E_Y_A,
                    "errors": "error_mm = error to the machine axes (Y 0 = cutting line). Anchors that carry "
                              "error_rel_line_A_mm have their Y placed through line A: error_mm.y = "
                              "error_rel_line_A_mm.y + 80 (Y_A = +6, E +-80, spec Datum, measure row M1)",
                    "spec": "spec/frame.md", "script": "parts/frame/frame.py"},
           "anchors": anchors(geo)}
    (OUT / "frame_anchors.json").write_text(json.dumps(anc, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT / "frame_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("bodies", len(bodies), "| bbox", rep["checks"]["bounding_box"]["got"],
          "| floor cm2", rep["checks"]["floor_contact_cm2_at_z1"]["got"],
          "| overlaps", rep["pairs_overlapping"], "| walls", rep["walls_mm"], "| PASS" if rep["pass"] else "| FAIL")
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
