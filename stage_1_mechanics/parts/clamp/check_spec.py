"""Checks of the clamp part (thread 3) against its spec and the delivered frame, knife and backgauge files.

Run: python stage_1_mechanics/parts/clamp/check_spec.py [--spec <md>] [--out <dir with clamp outputs>]
Partners are always read from R/out. Prints PASS/FAIL lines, then ALL PASS (exit 0) or FAIL n (exit 1).
Checks (block section 04): 4 lift, 7 bounding boxes, 8 rest interference, 9 sweeps (clamp top -> bottom
vs frame, knife at rest, backgauge at face 1150 and 25; knife sweep vs clamp at bottom; pedal), 10 device
anchors once, 11 spec rows; joints, passages (DECISION 2), hydraulic fit, corridors, envelopes.
Round 2 (critic findings F1, F2, F6): S28 on the beam at the false plate with its pocket zone, S30 fixed at the bar's
top edge; source numbers read back from the model rows, one line per value naming its key (HC, P11, P7, HL).
Round 4 (critics g5 and g6, H1-H3): each envelope touches what its touches= names and the linkage chains are closed
(pedal 5 to OV2, pull rods to the bar and the OA1 rod); prose positions of the component rows equal the model table;
device anchors lie on their bodies; S28 and S30 at their F101 readings; the data dwell equals the conflict 11 winner.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clamp as C  # noqa: E402

R = C.R
TOL_VOL = 1.0                                    # mm3 of numerical noise
fails = []


def say(ok, name, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" | " + detail if detail else ""))
    if not ok:
        fails.append(name)


def to_mf(tm):
    m = mf.Manifold(mf.Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                            tri_verts=np.asarray(tm.faces, np.uint32)))
    return m


def load_glb(path):
    s = trimesh.load(path)
    out = {}
    for node in s.graph.nodes_geometry:
        T, g = s.graph[node]
        tm = s.geometry[g].copy()
        tm.apply_transform(T)
        out[node] = tm
    return out


def aabb(m):
    b = m.bounding_box()
    return np.array([[b[0], b[1], b[2]], [b[3], b[4], b[5]]])


def overlap(b1, b2, eps=1e-6):
    return bool(np.all(b1[0] < b2[1] - eps) and np.all(b2[0] < b1[1] - eps))


def inter_vol(a, b):
    if not overlap(aabb(a), aabb(b)):
        return 0.0
    return float((a ^ b).volume())


def boxm(bx):
    return C.box(*[tuple(v) for v in bx])


def expected_bounds(geometry):
    """Bounds from the geometry string alone (independent of the mesh)."""
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for g in geometry.split(" + "):
        kind, *rest = g.split()
        kv = C.kv_of(rest)
        if kind == "box":
            b = np.array([C.rng(kv[a]) for a in "xyz"]).T
        elif kind in ("cyl", "tube"):
            ax, c, r, s = kv["ax"], C.vec(kv["c"]), float(kv["d"]) / 2, C.rng(kv["s"])
            i = "xyz".index(ax)
            others = [k for k in range(3) if k != i]
            b = np.zeros((2, 3))
            b[:, i] = s
            for k, cc in zip(others, c):
                b[:, k] = (cc - r, cc + r)
        elif kind == "fingers":
            x0, p, t, n = float(kv["x0"]), float(kv["pitch"]), float(kv["t"]), int(kv["n"])
            b = np.array([(x0 - t / 2, x0 + (n - 1) * p + t / 2), C.rng(kv["y"]), C.rng(kv["z"])]).T
        lo, hi = np.minimum(lo, b[0]), np.maximum(hi, b[1])
    return np.array([lo, hi])


def main(argv):
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else R / "out"
    spec = Path(argv[argv.index("--spec") + 1]) if "--spec" in argv else C.SPEC
    text = spec.read_text(encoding="utf-8")
    rows, anchor_rows, outer = C.read_spec(spec)
    groups = {r[0]: r[2] for r in rows}
    A = json.loads((out / "clamp_anchors.json").read_text(encoding="utf-8"))["anchors"]
    # r3 (tester 3 NOTE a, critic g5): the JSON anchors must equal the spec's anchors table, else the outputs are stale
    want = json.loads(json.dumps(C.anchors_json(anchor_rows), ensure_ascii=False))
    stale = sorted(set(want) ^ set(A)) + sorted(n for n in set(want) & set(A) if want[n] != A[n])
    say(not stale, "outputs match the spec's anchors table (if not: stale outputs, run clamp.py)", ", ".join(stale[:6]))
    FA = json.loads((R / "out" / "frame_anchors.json").read_text(encoding="utf-8"))["anchors"]
    KA = json.loads((R / "out" / "knife_anchors.json").read_text(encoding="utf-8"))["anchors"]
    BA = json.loads((R / "out" / "backgauge_anchors.json").read_text(encoding="utf-8"))
    bg_groups = {k: v.get("group") for k, v in BA["meta"]["bodies"].items()}
    BA = BA["anchors"]

    # ---- bodies: nodes, watertight, check 7
    G = load_glb(out / "clamp.glb")
    say(sorted(G) == sorted("clamp." + r[0] for r in rows), "nodes one per model row", f"{len(G)} nodes")
    M = {}
    for bid, comp, grp, geo in (r[:4] for r in rows):
        tm = G.get("clamp." + bid)
        if tm is None:
            continue
        M[bid] = to_mf(tm)
        eb = expected_bounds(geo)
        d = float(np.abs(tm.bounds - eb).max())
        ok = tm.is_watertight and tm.volume > 0 and d <= 1.0 and M[bid].status() == mf.Error.NoError
        say(ok, f"check7 body {bid}", f"watertight {tm.is_watertight} vol {tm.volume:.0f} max bbox dev {d:.3f}")
    allb = np.array([[min(t.bounds[0][i] for t in G.values()) for i in range(3)],
                     [max(t.bounds[1][i] for t in G.values()) for i in range(3)]])
    ob = np.array([[outer[a][0] for a in "xyz"], [outer[a][1] for a in "xyz"]])
    say(float(np.abs(allb - ob).max()) <= 1.0, "check7 part outer size", f"{np.round(allb, 1).tolist()}")

    # ---- check 4 / 6: lift
    face, table = A["clamp.face"]["xyz"][2], FA["table.top"]["xyz"][2]
    low = min(G["clamp." + b].bounds[0][2] for b in groups if groups[b] == "beam")
    mo = A["clamp.face"]["motion"]
    say(abs(face - table - 130) <= 10 and abs(low - face) <= 1 and mo.get("axis") == [0, 0, -1]
        and mo.get("range") == [0, 130], "check4 lift 130 and beam motion",
        f"face {face} - table {table} = {face - table}; lowest beam surface {low}")

    # ---- anchors: fields, check 10, joints, motion
    bad = [n for n, a in A.items() if not all(k in a for k in ("xyz", "class", "error_mm", "source", "motion"))]
    say(not bad, "anchors carry xyz/class/error/source/motion", ",".join(bad))
    files = sorted((R / "out").glob("*_anchors.json"))
    if out != R / "out":
        files = [f for f in files if f.name != "clamp_anchors.json"] + [out / "clamp_anchors.json"]
    allnames = []
    for f in files:
        allnames += list(json.loads(f.read_text(encoding="utf-8"))["anchors"])
    for dev in ("sensor.S28", "sensor.S30", "valve.Y11", "brake.Y14", "motor.M1"):
        n_all, n_own = allnames.count(dev), int(dev in A)
        want_own = 0 if dev == "motor.M1" else 1
        say(n_all == 1 and n_own == want_own, f"check10 {dev} once", f"all files {n_all}, clamp {n_own}")
    say(A["sensor.S28"]["xyz"][0] < 0 < A["sensor.S30"]["xyz"][0], "check10 S28 left, S30 right of centre")
    # F1: S28 = clamp plate switch (P46) on the beam at the false plate; S30 = clamp position switch (P46, P41), fixed
    fp = G["clamp.false_plate"].bounds
    s28 = np.array(A["sensor.S28"]["xyz"], float)
    d28 = float(np.linalg.norm(np.maximum(0.0, np.maximum(fp[0] - s28, s28 - fp[1]))))
    m28 = A["sensor.S28"]["motion"]
    say(d28 <= 25 and m28.get("kind") == "trans" and m28.get("axis") == [0, 0, -1] and m28.get("range") == [0, 130],
        "S28 on the beam at the false plate (P46 clamp plate switch)",
        f"{d28:.1f} mm from the plate, motion {m28.get('kind')} {m28.get('axis')} {m28.get('range')}")
    bar = G["clamp.bar"].bounds
    s30 = np.array(A["sensor.S30"]["xyz"], float)
    say(A["sensor.S30"]["motion"]["kind"] == "fixed" and abs(s30[1] - bar[1][1]) <= 10
        and bar[0][0] <= s30[0] <= bar[1][0] and 0 < bar[1][2] - s30[2] <= 10,
        "S30 fixed at the bar's rear face just below its top edge (P46; P41 clamp up)",
        f"S30 {s30.tolist()}, bar y max {bar[1][1]:.0f}, z max {bar[1][2]:.0f}")
    for name in A:
        for other, OA in (("frame", FA), ("knife", KA), ("backgauge", BA)):
            if name in OA:
                d = float(np.linalg.norm(np.array(A[name]["xyz"]) - np.array(OA[name]["xyz"])))
                say(d <= 1.0, f"joint {name} = {other}", f"{d:.2f} mm")
    moving = [n for n, a in A.items() if a["motion"]["kind"] in ("trans", "rot")]
    say(all("range" in A[n]["motion"] and "axis" in A[n]["motion"] for n in moving), "moving anchors carry axis and range",
        f"{len(moving)} moving")

    # ---- partners
    F = {k: to_mf(v) for k, v in load_glb(R / "out" / "frame.glb").items()}
    Kt = load_glb(R / "out" / "knife.glb")
    K = {k: to_mf(v) for k, v in Kt.items()}
    B = {k: to_mf(v) for k, v in load_glb(R / "out" / "backgauge.glb").items()}
    B25 = {k: (m.translate([0, -1125.0, 0]) if bg_groups.get(k) == "moving" else m) for k, m in B.items()}
    say(all(m.status() == mf.Error.NoError for m in list(F.values()) + list(K.values()) + list(B.values())),
        "partner bodies are manifolds", f"frame {len(F)} knife {len(K)} backgauge {len(B)}")
    passages = {n: a for n, a in A.items() if "passage" in a}
    for n, a in passages.items():
        tgt = a.get("cut_from", "")
        ok = a.get("cut_at") == "assembly" and tgt in F and inter_vol(boxm(a["passage"]), F[tgt]) > 0
        say(ok, f"passage {n} cuts {tgt} at assembly (DECISION 2)")

    def clash(mine, theirs, label, allow_frame=True):
        """volume of mine x theirs outside the passages that name that frame body."""
        worst = (0.0, "")
        for bn, bm in mine.items():
            for on, om in theirs.items():
                v = inter_vol(bm, om)
                if v > TOL_VOL and allow_frame and on in F:
                    for a in passages.values():
                        if a.get("cut_from") == on:
                            v = float(((bm ^ om) - boxm(a["passage"])).volume())
                if v > worst[0]:
                    worst = (v, f"{bn} x {on}")
        return worst

    # ---- check 8 rest
    for label, P in (("frame", F), ("knife", K), ("backgauge face 1150", B), ("backgauge face 25", B25)):
        v, w = clash(M, P, label)
        say(v <= TOL_VOL, f"check8 rest clamp x {label}", f"worst {v:.1f} mm3 {w}")
    own = clash({b: m for b, m in M.items() if groups[b] != "fixed"}, {b: m for b, m in M.items() if groups[b] == "fixed"},
                "own", allow_frame=False)
    say(own[0] <= TOL_VOL, "check8 rest moving x own fixed bodies", f"worst {own[0]:.1f} {own[1]}")

    # ---- check 9: clamp sweep top -> bottom, steps of 10
    steps = list(np.arange(0, 130, 10.0)) + [130.0]
    fixed = {b: m for b, m in M.items() if groups[b] == "fixed"}
    for label, P in (("frame", F), ("knife at rest", K), ("backgauge face 1150", B), ("backgauge face 25", B25),
                     ("own fixed", fixed)):
        worst = (0.0, "", 0)
        for d in steps:
            mv = {b: M[b].translate([0, 0, -d]) for b in M if groups[b] == "beam"}
            mv.update({b: M[b].translate([0, 0, d]) for b in M if groups[b] == "piston"})
            v, w = clash(mv, P, label, allow_frame=(label == "frame"))
            if v > worst[0]:
                worst = (v, w, d)
        say(worst[0] <= TOL_VOL, f"check9 clamp sweep x {label}", f"{len(steps)} steps, worst {worst[0]:.1f} {worst[1]} at {worst[2]}")
    # interleave, analytic: every plate inside a backgauge gap
    zi = BA["interface.clamp.comb_interleave"]["motion"]
    fr = next(r for r in rows if r[0] == "fingers")[3].split()
    kv = C.kv_of(fr[1:])
    x0, p, t, n = float(kv["x0"]), float(kv["pitch"]), float(kv["t"]), int(kv["n"])
    gaps = [(-550 + k * zi["pitch"] + zi["finger_w"], -550 + (k + 1) * zi["pitch"]) for k in range(30)]
    inside = all(any(g0 <= x0 + k * p - t / 2 and x0 + k * p + t / 2 <= g1 for g0, g1 in gaps) for k in range(n))
    say(inside, "interleave: each comb plate inside a backgauge gap", f"{n} plates t {t} pitch {p}")
    # knife sweep vs clamp at bottom
    low = {b: (M[b].translate([0, 0, -130.0]) if groups[b] == "beam" else
               M[b].translate([0, 0, 130.0]) if groups[b] == "piston" else M[b]) for b in M}
    kn = {k: K[k] for k in ("knife.knife", "knife.holder", "knife.holder_pin") if k in K}
    worst = (0.0, "", 0)
    for d in list(np.arange(0, 150, 10.0)) + [150.0]:
        v, w = clash(low, {k: m.translate([0, 0, -d]) for k, m in kn.items()}, "knife", allow_frame=False)
        if v > worst[0]:
            worst = (v, w, d)
    say(worst[0] <= TOL_VOL and len(kn) == 3, "check9 knife sweep x clamp at bottom", f"worst {worst[0]:.1f} {worst[1]} at {worst[2]}")
    # pedal sweep
    pa = A["pedal.5"]["motion"]
    pv = np.array(pa["pivot"])
    worst = (0.0, "", 0)
    for ang in np.arange(pa["range"][0], pa["range"][1] + 0.01, 1.0):
        pm = {"pedal_5": M["pedal_5"].translate(-pv).rotate([float(ang), 0, 0]).translate(pv)}
        for label, P in (("frame", F), ("backgauge", B), ("backgauge25", B25)):
            v, w = clash(pm, P, label, allow_frame=False)
            if v > worst[0]:
                worst = (v, w, ang)
    say(worst[0] <= TOL_VOL, "pedal sweep 0..15 deg x frame, backgauge", f"worst {worst[0]:.1f} {worst[1]} at {worst[2]}")
    pb = np.array([FA["plan.pedal"]["min"], FA["plan.pedal"]["max"]], float)
    tb = G["clamp.pedal_5"].bounds
    say(bool(np.all(tb[0] >= pb[0] - 1) and np.all(tb[1] <= pb[1] + 1)), "pedal inside frame plan.pedal", f"{np.round(tb, 1).tolist()}")

    # ---- corridors and envelopes
    for cn in ("corridor.front_table_centre", "corridor.base_cavity_centre"):
        cb = boxm(list(zip(BA[cn]["min"], BA[cn]["max"])))
        v = max(inter_vol(m, cb) for m in M.values())
        v2 = max(inter_vol(m.translate([0, 0, -130.0]), cb) for b, m in M.items() if groups[b] == "beam")
        say(v <= TOL_VOL and v2 <= TOL_VOL, f"no clamp body in {cn}", f"rest {v:.1f}, bottom {v2:.1f}")
    for en, a in A.items():
        if a.get("box_kind") != "envelope":
            continue
        eb = boxm(list(zip(a["min"], a["max"])))
        worst = (0.0, "")
        for label, P in (("frame", F), ("knife", K), ("backgauge", B), ("backgauge25", B25)):
            for on, om in P.items():
                v = inter_vol(eb, om)
                if v > worst[0]:
                    worst = (v, on)
        for cn in ("corridor.front_table_centre", "corridor.base_cavity_centre"):
            v = inter_vol(eb, boxm(list(zip(BA[cn]["min"], BA[cn]["max"]))))
            if v > worst[0]:
                worst = (v, cn)
        say(worst[0] <= TOL_VOL, f"envelope {en} free of partner bodies and corridors", f"worst {worst[0]:.1f} {worst[1]}")

    # r4 (critic g5 H1): each envelope touches every body (clamp.<body>) and box (anchor) that its touches= names,
    # and the linkage forms closed chains: pedal 5 to OV2, and each pull rod to the bar and to the OA1 rod
    def box_of(nm):
        if nm in G:
            return np.asarray(G[nm].bounds, float)
        a = A.get(nm, {})
        if "min" in a:
            return np.array([a["min"], a["max"]], float)
        if "passage" in a:
            return np.array(a["passage"], float).T
        return None

    def box_gap(b1, b2):
        return float(np.linalg.norm(np.maximum(0.0, np.maximum(b1[0] - b2[1], b2[0] - b1[1]))))

    links = {}
    for en, a in A.items():
        if a.get("box_kind") != "envelope":
            continue
        eb = np.array([a["min"], a["max"]], float)
        names = [s for s in str(a["motion"].get("touches", "")).split(",") if s]
        far = []
        for nm in names:
            bb = box_of(nm)
            g = float("inf") if bb is None else box_gap(eb, bb)
            if g > 1.0:
                far.append(f"{nm} gap {g:.0f}")
            else:
                links.setdefault(en, set()).add(nm)
                links.setdefault(nm, set()).add(en)
        say(bool(names) and not far, f"envelope {en} touches what it names",
            ",".join(names) + ("; " + "; ".join(far) if far else ""))

    def reach(s):
        seen, todo = {s}, [s]
        while todo:
            for m in links.get(todo.pop(), ()):
                if m not in seen:
                    seen.add(m)
                    todo.append(m)
        return seen
    chains = (("clamp.pedal_5", "clamp.valve_block_ov2"), ("envelope.clamp.pull_rod_right", "clamp.bar"),
              ("envelope.clamp.pull_rod_right", "clamp.oa1_piston_rod"), ("envelope.clamp.pull_rod_left", "clamp.bar"),
              ("envelope.clamp.pull_rod_left", "clamp.oa1_piston_rod"))
    broken = [f"{s} - {t}" for s, t in chains if t not in reach(s)]
    say(not broken, "linkage chains closed: pedal 5 to OV2; each pull rod to the bar and to the OA1 rod", "; ".join(broken))

    # ---- hydraulic fit
    cav = FA["frame.cavity.right_support"]
    tk = G["clamp.tank_oz1"].bounds
    inside = bool(np.all(tk[0] >= np.array(cav["min"]) - 1e-6) and np.all(tk[1] <= np.array(cav["max"]) + 1e-6))
    ks = KA["space.knife.drive_unit"]
    v_k = inter_vol(M["tank_oz1"], boxm(list(zip(ks["min"], ks["max"]))))
    strip = boxm([(cav["min"][0], cav["max"][0]), (cav["min"][1], ks["min"][1]), (cav["min"][2], cav["max"][2])])
    v_s = max(inter_vol(m, strip) for m in M.values())
    vol = float(M["tank_oz1"].volume())
    say(inside and v_k <= TOL_VOL and v_s <= TOL_VOL and vol >= 35e6, "hydraulic box: tank in the right support",
        f"inside {inside}, in knife space {v_k:.1f}, clamp in filler strip {v_s:.1f}, tank {vol / 1e6:.2f} dm3")
    pe = np.array(A["joint.M1.pump_end"]["xyz"])
    pb = G["clamp.pump_op1"].bounds
    say(abs(pb[1][0] - pe[0]) <= 1 and abs((pb[0][1] + pb[1][1]) / 2 - pe[1]) <= 1 and abs((pb[0][2] + pb[1][2]) / 2 - pe[2]) <= 1,
        "pump flange on joint.M1.pump_end", f"pump {np.round(pb, 1).tolist()}")

    # ---- F1 (critic g4): S28 pocket zone inside clamp.front_block, on the plate's top, holding S28, moving with
    # the beam and free of every other body (own, frame, knife, backgauge at 1150 and 25) at rest and at the bottom
    zb = A["sensor.S28"].get("zone")
    worst, inside, on_plate, s28_in = (0.0, ""), False, False, False
    if zb:
        zm = boxm(zb)
        for d in (0.0, 130.0):
            zd = zm.translate([0, 0, -d])
            own_d = {b: (m.translate([0, 0, -d]) if groups[b] == "beam" else
                         m.translate([0, 0, d]) if groups[b] == "piston" else m) for b, m in M.items() if b != "front_block"}
            for label, P in (("clamp", own_d), ("frame", F), ("knife", K), ("backgauge", B), ("backgauge25", B25)):
                for on, om in P.items():
                    v = inter_vol(zd, om)
                    if v > worst[0]:
                        worst = (v, f"{label} {on} at {d:.0f}")
        inside = abs(float((zm ^ M["front_block"]).volume()) - float(zm.volume())) <= TOL_VOL
        on_plate = abs(zb[2][0] - G["clamp.false_plate"].bounds[1][2]) <= 1.0
        s28_in = all(zb[i][0] - 1e-6 <= A["sensor.S28"]["xyz"][i] <= zb[i][1] + 1e-6 for i in range(3))
    say(bool(zb) and inside and on_plate and s28_in and worst[0] <= TOL_VOL,
        "S28 pocket zone in clamp.front_block on the plate's top, holds S28, free of other bodies at rest and bottom",
        f"zone {zb}, inside {inside}, on plate {on_plate}, holds S28 {s28_in}, worst {worst[0]:.1f} {worst[1]}")

    # ---- F2: source numbers read back from the model rows; each line names its source key
    geo = {r[0]: [g.strip() for g in r[3].split(" + ")] for r in rows}

    def kvb(body, i=0):
        return C.kv_of(geo[body][i].split()[1:]) if body in geo and i < len(geo[body]) else {}

    def fl(d, k):
        try:
            return float(d[k])
        except (KeyError, ValueError):
            return float("nan")

    tube, pis, rod = kvb("oa1_body"), kvb("oa1_piston_rod", 0), kvb("oa1_piston_rod", 1)
    say(abs(fl(tube, "di") - 70) <= 1, "HC bore Ø70 (cylinder Ø70x130)", f"di {tube.get('di')}")
    say(69 <= fl(pis, "d") <= 70, "HC piston Ø69..70 in the Ø70 bore", f"d {pis.get('d')}")
    say(abs(fl(rod, "d") - 25) <= 1, "HC rod Ø25 (rod Ø25x130)", f"d {rod.get('d')}")
    po = A["piston.OA1"]["motion"]
    st = po.get("range", [0, 0])
    ts, ps, rs = C.rng(tube["s"]), C.rng(pis["s"]), C.rng(rod["s"])
    ok = (po.get("axis") == [0, 0, 1] and st == [0, 130] and groups.get("oa1_piston_rod") == "piston"
          and ts[0] <= ps[0] and ps[1] + st[1] <= ts[1] and rs[0] + st[1] < ts[0])
    say(ok, "HC stroke 130: piston inside the tube at rest and at +130, rod end below the tube at both ends",
        f"tube {ts}, piston {ps}, rod {rs}, piston.OA1 axis {po.get('axis')} range {st}")
    k3, k4, pd = kvb("knob_3"), kvb("knob_4"), kvb("pedal_5")
    say(abs(fl(k3, "d") - 40) <= 1, "P11 knob 3 Ø40", f"d {k3.get('d')}")
    say(abs(fl(k4, "d") - 30) <= 1, "P11 knob 4 Ø30", f"d {k4.get('d')}")
    px, py = C.rng(pd["x"]), C.rng(pd["y"])
    say(abs(px[1] - px[0] - 300) <= 10 and abs(py[1] - py[0] - 40) <= 10,
        "P11 pedal 300 long; 40 deep (Fig. 4.2.2 wins over P11 50, conflict 6)", f"{px[1] - px[0]:.0f} x {py[1] - py[0]:.0f}")
    for b in ("false_plate", "front_block"):
        x = C.rng(kvb(b)["x"])
        say(abs(x[1] - x[0] - 1150) <= 10, f"P7 {b} spans the cutting width 1150", f"{x[1] - x[0]:.0f}")
    cm = A["clamp.face"]["motion"]
    say(cm.get("axis") == [0, 0, -1] and cm.get("range") == [0, 130], "P7 lift 130 (clamp.face motion)", f"{cm.get('range')}")
    tv = float(M["tank_oz1"].volume()) / 1e6
    say(tv >= 35, "HL tank OZ1 holds 35 dm3", f"{tv:.2f} dm3")
    gz = kvb("gauge_oz13")
    say(abs(fl(gz, "d") - 60) <= 5, "HL OZ13 manometer B 60: case Ø60", f"d {gz.get('d')}")
    # r3 (critic g5): the ports are unknown, so each hose must reach between the nearest faces of its end bodies
    def gap(a, b):
        ba, bb = G["clamp." + a].bounds, G["clamp." + b].bounds
        return float(np.linalg.norm(np.maximum(0, np.maximum(ba[0] - bb[1], bb[0] - ba[1]))))
    for hose, ln, a, b in (("OZ4", 500, "valve_block_ov2", "oa1_body"), ("OZ6", 630, "pump_op1", "valve_block_ov2"),
                           ("OZ12", 1400, "oa1_body", "knob_3"), ("OZ14", 1400, "knob_3", "tank_oz1")):
        g = gap(a, b)
        say(g <= ln, f"HL hose {hose} 10x{ln} reaches {a} to {b} (nearest faces)", f"{g:.1f}")
    # r3 (tester 3 F1a, critic g5): instrument panel and OV2 at their F101 readings, by the drawing's own scale
    pan = {"gauge_oz13": (937, 1377), "knob_4": (937, 1309), "knob_3": (937, 1244)}
    got = {b: [float(v) for v in kvb(b)["c"].split(",")] for b in pan}
    say(all(abs(got[b][0] - x) <= 20 and abs(got[b][1] - z) <= 20 for b, (x, z) in pan.items()),
        "F101 front view: gauge, knob 4, knob 3 at X 937, Z 1377 / 1309 / 1244 (+-20)", str(got))
    ovx = float(G["clamp.valve_block_ov2"].bounds[:, 0].mean())
    say(abs(ovx - 321) <= 20 and abs(A["valve.Y11"]["xyz"][0] - 321) <= 20, "F101 plan: OV2 and valve.Y11 at X 321 (+-20)",
        f"OV2 {ovx:.0f}, Y11 {A['valve.Y11']['xyz'][0]}")

    # ---- r3 (tester 3 NOTE b, critic g5): sizes and strokes written in the component rows equal the model table
    sol = {}
    for r in rows:
        for g in r[3].split(" + "):
            w = g.split()
            kv = C.kv_of(w[1:])
            ext = {a: round(C.rng(kv[a])[1] - C.rng(kv[a])[0], 1) for a in "xyz" if a in kv}
            if w[0] == "box":
                sol.setdefault(r[1], []).append(("box", *sorted(ext.values())))
            elif w[0] in ("cyl", "tube"):
                s = C.rng(kv["s"])
                sol.setdefault(r[1], []).append((w[0], float(kv["d"]), float(kv.get("di", 0)), round(s[1] - s[0], 1)))
            elif w[0] == "fingers":
                sol.setdefault(r[1], []).append(("fingers", int(kv["n"]), float(kv["t"]), ext["y"], ext["z"], float(kv["pitch"])))
    nf = lambda s: float(s.replace(",", "."))  # noqa: E731
    lift = want["clamp.face"]["motion"]["range"][1]
    bad, nread = [], 0
    for r in C.table(text, "## Components (position at rest)", "Not modelled as solids"):
        have = sol.get(r[0], []) + (sol.get("guide", []) if r[0].startswith("guides") else [])
        for m in re.finditer(r"tube Ø(\d+) / bore Ø(\d+) x (\d+)", r[2]):
            nread += 1
            if ("tube", nf(m[1]), nf(m[2]), nf(m[3])) not in have:
                bad.append(f"{r[0]}: {m[0]}")
        for m in re.finditer(r"Ø(\d+(?:,\d+)?) x (\d+(?:,\d+)?)", re.sub(r"tube Ø\d+ / bore Ø\d+ x \d+", "", r[2])):
            nread += 1
            if not any(h[0] == "cyl" and h[1] == nf(m[1]) and h[3] == nf(m[2]) for h in have):
                bad.append(f"{r[0]}: {m[0]}")
        for m in re.finditer(r"(\d+(?:,\d+)?) x (\d+(?:,\d+)?) x (\d+(?:,\d+)?)", r[2]):
            nread += 1
            if ("box", *sorted(nf(v) for v in m.groups())) not in have:
                bad.append(f"{r[0]}: {m[0]}")
        m = re.search(r"(\d+) plates (\d+) \(X\) x (\d+) \(Y\) x (\d+) \(Z\), pitch (\d+(?:,\d+)?)", r[2])
        if m:
            nread += 1
            if ("fingers", int(m[1]), nf(m[2]), nf(m[3]), nf(m[4]), nf(m[5])) not in have:
                bad.append(f"{r[0]}: {m[0]}")
        for m in re.finditer(r"\b(?:lift|down|up) (\d+)\b", r[3] + " " + r[4]):
            nread += 1
            if nf(m[1]) != lift:
                bad.append(f"{r[0]}: {m[0]} vs lift {lift}")
    say(not bad and nread >= 20, "prose sizes and strokes of the component rows equal the model table",
        f"{nread} numbers read; " + "; ".join(bad[:4]))

    # ---- r4 (critic g5 H2): positions written in the component rows equal the model table. A range a..b must equal
    # the bounds of the component's body or of one of its solids; a single value their centre (or, right after "end",
    # a bound); ±a is the range -a..a; ±a..±b both sides; "(centre c)" the middle of the range before it.
    pos = {}
    for r in rows:
        pos.setdefault(r[1], []).extend([expected_bounds(r[3])] + [expected_bounds(g) for g in r[3].split(" + ")])
    beam_low = min(expected_bounds(r[3])[0][2] for r in rows if r[2] == "beam")
    pn = lambda s: float(s.replace("−", "-").replace("±", "").replace(",", "."))  # noqa: E731
    nre = r"±?[−-]?\d+(?:,\d+)?"
    bad, nread = [], 0
    for r in C.table(text, "## Components (position at rest)", "Not modelled as solids"):
        cand = pos.get(r[0], []) + (pos.get("guide", []) if r[0].startswith("guides") else [])
        for m in re.finditer(rf"(?<![\w.])([XYZ]) ({nre})(?:\.\.({nre}))?(?: \(centre ({nre})\))?", r[3]):
            i, a, b, c = "XYZ".index(m[1]), m[2], m[3], m[4]
            nread += 1
            if r[0] == "lowest clamp surface":
                ok = b is None and abs(pn(a) - beam_low) <= 1
            elif b is None and a.startswith("±"):
                ok = any(abs(k[0][i] + pn(a)) <= 1 and abs(k[1][i] - pn(a)) <= 1 for k in cand)
            elif b is None:
                at_end = "end" in r[3][max(0, m.start() - 6):m.start()]
                ok = any(abs((k[0][i] + k[1][i]) / 2 - pn(a)) <= 1
                         or (at_end and min(abs(k[0][i] - pn(a)), abs(k[1][i] - pn(a))) <= 1) for k in cand)
            else:
                lo, hi = pn(a), pn(b)
                wants = [(lo, hi), (-hi, -lo)] if a.startswith("±") and b.startswith("±") else [(lo, hi)]
                ok = all(any(abs(k[0][i] - w0) <= 1 and abs(k[1][i] - w1) <= 1 for k in cand) for w0, w1 in wants)
                # r5 (critic g6's survivor): a one-sided X range whose mirror is another solid of the same body
                # names only half of the body; such a range must be written ±a..±b
                if ok and i == 0 and not (a.startswith("±") and b.startswith("±")) and abs(lo + hi) > 1 \
                        and any(abs(k[0][0] + hi) <= 1 and abs(k[1][0] + lo) <= 1 for k in cand):
                    ok = False
                if c is not None:
                    ok = ok and abs((lo + hi) / 2 - pn(c)) <= 1
            if not ok:
                bad.append(f"{r[0]}: {m[0]}")
    say(not bad and nread >= 45, "prose positions of the component rows equal the model table",
        f"{nread} positions read; " + "; ".join(bad[:4]))
    # the device anchors lie on their bodies; S28 and S30 at their F101 front-view readings
    onb = {"clamp.face": "false_plate", "brake.Y14": "brake_y14", "gear.8": "gear_8", "valve.Y11": "valve_block_ov2",
           "cylinder.OA1": "oa1_body", "piston.OA1": "oa1_piston_rod", "pump.OP1": "pump_op1", "tank.OZ1": "tank_oz1",
           "gauge.OZ13": "gauge_oz13", "knob.3": "knob_3", "knob.4": "knob_4", "pedal.5": "pedal_5"}
    off = []
    for an, b in onb.items():
        p = np.array(A[an]["xyz"], float)
        g = box_gap(np.array([p, p]), np.asarray(G["clamp." + b].bounds, float))
        if g > 1.0:
            off.append(f"{an} {g:.0f} off {b}")
    say(not off, "device anchors lie on their bodies", f"{len(onb)} anchors; " + "; ".join(off))
    x28, x30 = A["sensor.S28"]["xyz"][0], A["sensor.S30"]["xyz"][0]
    say(abs(x28 + 488) <= 20 and abs(x30 - 282) <= 20, "F101 front view: S28 at X -488, S30 at X +282 (+-20)",
        f"S28 {x28}, S30 {x30}")
    # ---- r4 (critic g5 H3): the dwell given as data equals the winner of conflict 11 (timer KT2, P49)
    win = re.search(r"timer KT2 (\d+-\d+(?:,\d+)?) s wins", text)
    dw = re.findall(r"\bdwell (\d+-\d+(?:,\d+)?) s", text)
    say(bool(win) and bool(dw) and all(d == win[1] for d in dw), "data dwell equals the winner of conflict 11 (KT2)",
        f"winner {win[1] if win else None}, data {dw}")

    # ---- r5 (critics g7 and g8, G7-1): no clamp body above the printed overall height; rack, gear 8 and Y14 as F71
    p7h = re.search(r"^\| P7 \|.*?overall height (\d+)", text, re.M)
    say(bool(p7h) and allb[1][2] <= float(p7h[1]) + 1,
        "no clamp body above the overall height (P7) at rest; the beam only moves down from there",
        f"top {allb[1][2]:.1f}, P7 {p7h[1] if p7h else None}")
    rk = np.asarray(G["clamp.rack"].bounds, float)
    gb = np.asarray(G["clamp.gear_8"].bounds, float)
    gx, gz, gr = (gb[0][0] + gb[1][0]) / 2, (gb[0][2] + gb[1][2]) / 2, (gb[1][0] - gb[0][0]) / 2
    mesh = (abs(rk[1][0] - (gx - gr)) <= 1 and rk[0][1] < gb[1][1] and rk[1][1] > gb[0][1]
            and rk[0][2] <= gz - 10 and rk[1][2] - lift >= gz + 10)
    say(mesh, "rack meshes with gear 8 on its -X side (F71) over the whole stroke, 10 past the centre at both ends",
        f"rack x {rk[0][0]:.0f}..{rk[1][0]:.0f} z {rk[0][2]:.0f}..{rk[1][2]:.0f} (bottom top {rk[1][2] - lift:.0f}); "
        f"gear 8 centre x {gx:.0f} z {gz:.0f} r {gr:.0f}")
    f71 = re.search(r"^\| F71 \|.*?pinion centre is at Z ≈ (\d+)", text, re.M)
    yb = np.asarray(G["clamp.brake_y14"].bounds, float)
    yz = (yb[0][2] + yb[1][2]) / 2
    say(bool(f71) and abs(gz - float(f71[1])) <= 20 and abs(yz - float(f71[1])) <= 20,
        "gear 8 and Y14 at F71's pinion reading (+-20)", f"F71 {f71[1] if f71 else None}, gear 8 {gz:.0f}, Y14 {yz:.0f}")
    # ---- r6 (tester 2 r3 check 7, critic g9): gear 8 turns with the rack, worked out from the files: the rack's side
    # of the pivot, the mesh point r = side * (Ø/2, 0, 0) from the pivot, w = axis * sign(range); (w x r) . beam travel
    # > 0; the range is the stroke's turn, stroke / (π Ø) * 360 +-0.5 deg; the pivot is the gear's centre; one axis in
    # the anchor, the spec's groups line and the JSON groups (clamp.py)
    gm, fm = A["gear.8"]["motion"], A["clamp.face"]["motion"]
    ax, pv = np.asarray(gm.get("axis", [0, 0, 0]), float), np.asarray(gm.get("pivot", [0, 0, 0]), float)
    g0, g1 = (list(gm.get("range", [])) + [0.0, 0.0])[:2]
    g8 = expected_bounds({r[0]: r[3] for r in rows}["gear_8"].split(" + ")[0])
    dia = float(g8[1][0] - g8[0][0])
    side = -1.0 if (rk[0][0] + rk[1][0]) / 2 < pv[0] else 1.0
    w = np.sign(g1 - g0) * ax / (np.linalg.norm(ax) or 1.0)
    travel = np.asarray(fm["axis"], float) * np.sign(fm["range"][1] - fm["range"][0])
    sense = float(np.dot(np.cross(w, [side * dia / 2, 0.0, 0.0]), travel))
    stroke = abs(fm["range"][1] - fm["range"][0])
    turn = stroke / (np.pi * dia) * 360.0
    sl = re.search(r"gear = turns about \(([^)]*)\)", text)
    jl = re.search(r"turns about \(([^)]*)\)",
                   json.loads((out / "clamp_anchors.json").read_text(encoding="utf-8"))["meta"]["groups"].get("gear", ""))
    axes = [C.vec(m[1]) for m in (sl, jl) if m]
    same = len(axes) == 2 and all(len(a) == 3 and np.allclose(a, ax) for a in axes)
    ok = (gm.get("kind") == "rot" and sense > 0 and abs(abs(g1 - g0) - turn) <= 0.5 and same
          and abs(pv[0] - gx) <= 1 and abs(pv[2] - gz) <= 1)
    say(ok, "gear 8 turns with the rack (its mesh point moves with the beam) by the stroke's turn about its own centre; "
            "one axis in the anchor, the groups line and the JSON groups (tester 2 r3, critic g9)",
        f"axis {ax.tolist()} range {g0:g}..{g1:g} pivot {pv.tolist()}; rack side {side:+.0f}, mesh point {sense:+.1f} "
        f"along the beam travel per rad; turn {turn:.1f} deg for stroke {stroke:g} at Ø{dia:g}; "
        f"groups line ({sl[1] if sl else None}), JSON groups ({jl[1] if jl else None})")
    # ---- r6 (tester 3 NOTE A, critic g9): the spec's mutant count equals the mutation test's
    import mutation_test as MT  # noqa: E402
    nm = len(MT.MUTANTS)
    mk, mc = re.search(r"makes (\d+) broken copies", text), re.search(r"MUTANTS caught (\d+)/(\d+)", text)
    say(bool(mk and mc) and int(mk[1]) == nm and int(mc[1]) == nm and int(mc[2]) == nm,
        "the spec's mutant count equals the mutation test's (tester 3 NOTE A, critic g9)",
        f"spec makes {mk[1] if mk else None}, {mc[0] if mc else None}; mutation_test.py {nm}")
    # ---- r5 (tester 2, check 4): OA1's outer size and the piston and rod lengths on M3 with errors; knob length on M6
    m3 = (re.search(r"^\| M3 \|.*$", text, re.M) or [""])[0]
    v = re.search(r"OA1 outer Ø(\d+) x (\d+), piston length (\d+), rod length (\d+)", m3)
    e = re.search(r"OA1 outer Ø ±(\d+), length ±(\d+); piston length ±(\d+); rod length ±(\d+)", m3)
    geo = {r[0]: r[3] for r in rows}
    ob = expected_bounds(geo["oa1_body"])
    ps = [expected_bounds(g) for g in geo["oa1_piston_rod"].split(" + ")]
    have = [ob[1][0] - ob[0][0], ob[1][2] - ob[0][2], ps[0][1][2] - ps[0][0][2], ps[1][1][2] - ps[1][0][2]]
    r60 = [r for r in C.table(text, "## Components (position at rest)", "Not modelled as solids")
           if r[0] == "cylinder OA1 body"]
    ok = bool(v and e and r60) and all(abs(float(x) - y) <= 1 for x, y in zip(v.groups(), have))
    ok = ok and re.search(rf"outer Ø ±{e[1]}, length ±{e[2]} \(M3\)", r60[0][7]) is not None
    say(ok, "M3 gives OA1's outer size and the piston and rod lengths of the model, each with an error (tester 2)",
        f"M3 {v.groups() if v else None}, errors {e.groups() if e else None}; model {[round(h) for h in have]}")
    ph = re.search(r"^\| PH150610 \|.*?knobs (\d+)-(\d+) in front of the plate", text, re.M)
    m6 = (re.search(r"^\| M6 \|.*$", text, re.M) or [""])[0]
    kl, ke = re.search(r"knob length (\d+) = ", m6), re.search(r"knob length ±(\d+)", m6)
    kn = {b: round(float(np.ptp(np.asarray(G["clamp." + b].bounds, float)[:, 1])), 1) for b in ("knob_3", "knob_4")}
    ok = bool(ph and kl and ke)
    if ok:
        L, er = float(kl[1]), float(ke[1])
        ok = L - er <= float(ph[1]) and L + er >= float(ph[2]) and all(abs(x - L) <= 1 for x in kn.values())
    say(ok, "M6 knob length and its error cover PH150610's reading; the knobs are modelled that long (tester 2)",
        f"PH150610 {ph.groups() if ph else None}, M6 {kl[1] if kl else None} +-{ke[1] if ke else None}, model {kn}")

    # ---- check 11: spec rows
    comp = C.table(text, "## Components (position at rest)", "Not modelled as solids")
    meas = set(re.findall(r"^\| (M\d+) \|", text, re.M))
    badrows = []
    for r in comp:
        src, cls, err = r[5], r[6], r[7]
        if not src or not cls or not err:
            badrows.append(r[0] + " (empty)")
        elif ("E" in cls or "P" in cls):
            refs = re.findall(r"M\d+", err)
            if not refs or not set(refs) <= meas:
                badrows.append(r[0] + " (no measure row)")
    say(not badrows and {f"M{i}" for i in range(1, 8)} <= meas, "check11 component rows: source, class, error, measure row",
        f"{len(comp)} rows, measure rows {len(meas)}; " + ", ".join(badrows))
    srcs = set(re.findall(r"^\| ([A-Z0-9-]+(?: / [A-Z0-9-]+)*|P8, P10, P41, P49, PL23, CERT) \|", text, re.M))
    keys = set()
    for s in srcs:
        keys |= {k.strip() for k in re.split(r"[,/]", s)}
    used = set()
    for r in comp:
        used |= set(re.findall(r"\b(P\d+|F\d+|HS\d|HC|HL|PH\d+|OLD-[IVX]+|FR|KN|BG|REQ|D2|PL23|CERT)\b", r[5]))
    say(used <= keys, "check11 every source key used in a row is in the source table", ",".join(sorted(used - keys)))

    print("ALL PASS" if not fails else f"FAIL {len(fails)}: " + "; ".join(fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
