"""Checks the knife part against its spec (thread 2). Exit 0 = all PASS, 1 = a FAIL.

Reads spec/knife.md (component table: geometry AND outer-size columns; kinematics; anchors),
out/knife.glb, out/knife_anchors.json, all out/*_anchors.json, out/frame.glb.
Bounding boxes are computed here from the geometry text (not by knife.py's builder).
Section 8: a knife body may meet the frame only inside a passage box of a knife anchor whose
name the frame's anchors file also carries at the same point (within 1 mm). Inside
frame.cavity.right_support (room of the hydraulic box, P36) the knife may sit only within its claim
space.knife.drive_unit, which must equal its extent there (rest and stroke) within 1 mm and leave
at least the 35 dm3 of tank OZ1 below it.
Run:  python stage_1_mechanics/parts/knife/check_spec.py [--spec <copy of knife.md>] [--no-sweep]
                                                         [--frame-anchors <copy of frame_anchors.json>]
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import knife as K                                     # noqa: E402  (table parser, solid builder for the sweep)

R = HERE.parents[1]
DEVICES = ["sensor.S12", "sensor.S13", "sensor.S14", "sensor.SQ1", "sensor.SQ2", "magnet.Y01",
           "clutch.Y10", "sensor.S19", "sensor.S5", "motor.M1"]
KINDS = ("fixed", "rot", "trans", "planar", "state")
fails = []


def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)


def bbox_of_geometry(g):
    kind, kv = K.parse_geometry(g)
    if kind in ("box", "shell", "knife", "holder"):
        return np.array([K.rng(kv["x"]), K.rng(kv["y"]), K.rng(kv["z"])])
    if kind == "cyl":
        c, r, s = K.vec(kv["c"]), float(kv["d"]) / 2, K.rng(kv["s"])
        axes = "xyz"
        out, others = [], iter(c)
        for a in axes:
            out.append(s if a == kv["ax"] else (lambda v: (v - r, v + r))(next(others)))
        return np.array(out)
    if kind == "rod":
        p1, p2, r = np.array(K.vec(kv["p1"])), np.array(K.vec(kv["p2"])), float(kv["d"]) / 2
        a = (p2 - p1) / np.linalg.norm(p2 - p1)
        ext = r * np.sqrt(np.clip(1 - a ** 2, 0, None))
        return np.array([[min(p1[i], p2[i]) - ext[i], max(p1[i], p2[i]) + ext[i]] for i in range(3)])
    if kind == "belt":
        s = K.rng(kv["s"])
        (c1, d1), (c2, d2) = (K.vec(kv["c1"]), float(kv["d1"])), (K.vec(kv["c2"]), float(kv["d2"]))
        lo = [min(c1[i] - d1 / 2, c2[i] - d2 / 2) for i in (0, 1)]
        hi = [max(c1[i] + d1 / 2, c2[i] + d2 / 2) for i in (0, 1)]
        return np.array([s, (lo[0], hi[0]), (lo[1], hi[1])])
    raise ValueError(kind)


def bbox_of_outer(text):
    t = text.replace("−", "-").split()
    return np.array([K.rng(t[t.index(a) + 1]) for a in ("X", "Y", "Z")])


def load_scene(path):
    s = trimesh.load(path, force="scene")
    out = {}
    for node in s.graph.nodes_geometry:
        tf, g = s.graph[node]
        m = s.geometry[g].copy()
        m.apply_transform(tf)
        out[node] = m
    return out


def to_manifold(tm):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                               tri_verts=np.asarray(tm.faces, dtype=np.uint32)))


def bb(m):
    b = np.array(m.bounding_box()).reshape(2, 3)
    return b


def overlap(b1, b2):
    return bool(np.all(b1[0] < b2[1]) and np.all(b2[0] < b1[1]))


def unit(v):
    return v is not None and len(v) == 3 and abs(float(np.linalg.norm(v)) - 1) < 1e-6


def moved(p, m, val):
    """Point p after the motion m ('trans' by val mm along axis, 'rot' by val deg right-handed about axis at pivot)."""
    p = np.array(p, dtype=float)
    if m.get("kind") == "trans" and unit(m.get("axis")):
        return p + np.array(m["axis"]) * val
    if m.get("kind") == "rot" and unit(m.get("axis")) and len(m.get("pivot", [])) == 3:
        k, c, t = np.array(m["axis"]), np.array(m["pivot"]), math.radians(val)
        v = p - c
        return c + v * math.cos(t) + np.cross(k, v) * math.sin(t) + k * np.dot(k, v) * (1 - math.cos(t))
    return np.full(3, np.nan)


def main(argv):
    spec = Path(argv[argv.index("--spec") + 1]) if "--spec" in argv else R / "spec" / "knife.md"
    bodies, arows, kin = K.read_spec(spec)
    rows = {r[0]: r for r in bodies}
    geo = {b: K.parse_geometry(r[2])[1] for b, r in rows.items()}

    # 1. table rows complete
    for b, r in rows.items():
        check(len(r) == 8 and all(r[i] for i in (1, 2, 3, 4, 5, 6, 7)), f"row {b}: 8 cells, term, source, class, error filled")

    # 2.-3. outer size column = bbox(geometry) = GLB node bbox; watertight volumes; names
    glb = load_scene(R / "out" / "knife.glb")
    check(sorted(glb) == sorted("knife." + b for b in rows), f"GLB nodes = spec ids ({len(glb)} vs {len(rows)})")
    for b, r in rows.items():
        gb, ob = bbox_of_geometry(r[2]), bbox_of_outer(r[3])
        check(np.abs(gb - ob).max() <= 1.0, f"{b}: outer size column = geometry bbox (max dev {np.abs(gb - ob).max():.3f})")
        m = glb.get("knife." + b)
        if m is None:
            continue
        nb = m.bounds.T
        check(np.abs(nb - ob).max() <= 1.0, f"{b}: GLB bbox = outer size (max dev {np.abs(nb - ob).max():.3f})")
        check(m.is_watertight and m.is_volume and m.volume > 0, f"{b}: watertight volume {m.volume:.0f} mm3")
    allb = np.array([bbox_of_outer(r[3]) for r in bodies])
    check(allb[:, 0, 1].max() <= 1553, f"part max X {allb[:, 0, 1].max()} <= 1553 (Fig. 4.2.2 overall width)")

    # 4. kinematics
    cx, cz, hx, hz, s = kin["crank_x"], kin["crank_z"], kin["pin_x"], kin["pin_z_rest"], kin["stroke"]
    y = kin["rod_plane_y"]
    A, B = math.hypot(cx - hx, hz - cz), math.hypot(cx - hx, hz - s - cz)
    L, r = (A + B) / 2, (A - B) / 2
    check(abs(L - kin["rod_length"]) < 0.01 and abs(r - kin["crank_radius"]) < 0.01,
          f"rod length {L:.3f} and crank radius {r:.3f} = stated {kin['rod_length']} / {kin['crank_radius']}")
    check(L - r > abs(cx - hx), f"full turn possible: L - r = {L - r:.1f} > dX {abs(cx - hx):.1f}")
    ut = np.array([hx - cx, hz - cz]) / A
    ub = np.array([hx - cx, hz - s - cz]) / B
    pt, pb = np.array([cx, cz]) + r * ut, np.array([cx, cz]) - r * ub
    eb, er = kin["edge_z_bottom"], kin["edge_z_rest"]
    check(abs(er - (eb + s)) < 0.01 and er >= 1015, f"edge at rest {er} = bottom + stroke, >= 1015 (table 885 + 130)")
    check(884.8 <= eb <= 884.9, f"edge at the bottom {eb} in 884.8..884.9 (0.1-0.2 into the stick top 885)")
    kz = K.rng(geo["knife"]["z"])
    check(abs(kz[0] - er) < 0.01 and abs(kz[1] - kz[0] - 150) < 0.01, f"knife Z {kz} = edge at rest .. +150")
    p1, p2 = np.array(K.vec(geo["conrod"]["p1"])), np.array(K.vec(geo["conrod"]["p2"]))
    check(np.abs(p1 - [pt[0], y, pt[1]]).max() < 0.5 and np.abs(p2 - [hx, y, hz]).max() < 0.5,
          f"conrod ends = crank pin at TDC {pt.round(2)} and holder pin ({hx}, {hz}), plane Y {y}")
    check(abs(np.linalg.norm(p2 - p1) - L) < 1, f"rod length at rest {np.linalg.norm(p2 - p1):.2f} = L {L:.2f}")
    hb = np.array([hx, hz - s])
    check(abs(np.linalg.norm(hb - pb) - L) < 1, f"rod length at the bottom {np.linalg.norm(hb - pb):.2f} = L (+-1)")
    check(np.abs(np.array(K.vec(geo["crank_pin"]["c"])) - pt).max() < 0.5, "crank pin on the crank circle at TDC")
    for b in ("crank_disc", "cam_disc", "crank_shaft", "worm_wheel", "flange_2"):
        check(geo[b]["ax"] == "y" and np.abs(np.array(K.vec(geo[b]["c"])) - [cx, cz]).max() < 0.01, f"{b} on the crank axis")
    check(np.abs(np.array(K.vec(geo["holder_pin"]["c"])) - [hx, hz]).max() < 0.01, "holder pin at the rod small end")

    # 5. holder in the opening, under the crossbar, above the table at the bottom
    hbb = bbox_of_geometry(rows["holder"][2])
    check(hbb[2, 1] < 1415 and hbb[0, 0] >= -720 and hbb[0, 1] <= 720 and hbb[2, 0] - s > 885,
          f"holder: top {hbb[2, 1]} < 1415, X {hbb[0]} inside +-720, bottom at stroke end {hbb[2, 0] - s} > 885")
    # 5b. guides 12 (front) and 13 (rear) act on the holder: over its ends in X, 1 mm off its faces in Y,
    #     covering it in Z from rest to the bottom; guides stay in front of the cutting line (Y 0, clamp side)
    for side, sgn in (("left", -1), ("right", 1)):
        for g, face in ((f"guide_12_{side}", "front"), (f"guide_13_{side}", "rear")):
            gb = bbox_of_geometry(rows[g][2])
            ov = (min(gb[0, 1], hbb[0, 1]) - max(gb[0, 0], hbb[0, 0]))
            gap = hbb[1, 0] - gb[1, 1] if face == "front" else gb[1, 0] - hbb[1, 1]
            check(ov >= 10 and abs(gap - 1) < 0.01 and gb[2, 0] <= hbb[2, 0] - s and gb[2, 1] >= hbb[2, 1]
                  and gb[1, 1] <= -1 and gb[0, 1] < 720 and gb[0, 0] > -720,
                  f"{g}: over the holder's {side} end by {ov:.1f} in X, {gap:.2f} off its {face} face, "
                  f"Z {gb[2]} covers rest and bottom, Y max {gb[1, 1]} <= -1, inside the cheeks")
    for g in ("guide_15_left", "guide_15_right"):
        check(bbox_of_geometry(rows[g][2])[1, 1] <= -1, f"{g}: in front of the cutting line (Y max <= -1)")

    # 6. worm mesh, coaxial drive, belt plane, lock
    w, ww = geo["worm"], geo["worm_wheel"]
    wc = K.vec(w["c"])
    dist = cz - wc[1]
    check(abs(dist - (float(ww["d"]) + float(w["d"])) / 2) < 0.5 and abs(wc[0] - sum(K.rng(ww["s"])) / 2) < 0.5
          and K.rng(w["s"])[0] < cx < K.rng(w["s"])[1],
          f"worm meshes: centre distance {dist} = wheel r + worm r, worm in the wheel plane, under the wheel")
    for b in ("worm_shaft", "clutch_y10", "flywheel_2", "slip_rings"):
        check(geo[b]["ax"] == "x" and K.vec(geo[b]["c"]) == wc, f"{b} coaxial with the worm (shaft 14)")
    for b in ("m1_shaft", "m1_pulley"):
        check(geo[b]["c"] == geo["m1_motor"]["c"], f"{b} on the M1 axis")
    fm, pm = sum(K.rng(geo["flywheel_2"]["s"])) / 2, sum(K.rng(geo["m1_pulley"]["s"])) / 2
    bs = K.rng(geo["belt"]["s"])
    check(abs(fm - pm) <= 1 and K.rng(geo["flywheel_2"]["s"])[0] <= bs[0] and bs[1] <= K.rng(geo["m1_pulley"]["s"])[1]
          and geo["belt"]["c1"] == geo["flywheel_2"]["c"] and geo["belt"]["c2"] == geo["m1_pulley"]["c"],
          f"belt plane: flywheel mid X {fm} = M1 pulley mid X {pm}; belt on both pulleys")
    lp, ym = geo["lock_pin_1"], geo["y01_magnet"]
    rad = math.dist(K.vec(lp["c"]), [cx, cz])
    check(lp["c"] == ym["c"] and K.rng(lp["s"])[0] == K.rng(geo["flange_2"]["s"])[1] and rad < float(geo["flange_2"]["d"]) / 2,
          f"lock pin 1 coaxial with Y01, at flange 2's rear face, r {rad:.0f} inside the flange")
    sh, cd_, cm_ = K.rng(geo["crank_shaft"]["s"]), K.rng(geo["crank_disc"]["s"]), K.rng(geo["cam_disc"]["s"])
    check(sh == (cd_[0], cm_[1]) and K.rng(geo["worm_wheel"]["s"])[0] >= cd_[1] - 0.01
          and K.rng(geo["flange_2"]["s"])[1] <= cm_[0] and K.rng(geo["y01_magnet"]["s"])[1] <= 375,
          f"compact unit (F62, conflict 6): shaft Y {sh} from the front hub to the cam disc, wheel and flange 2 "
          f"between them, Y01 ends at {K.rng(geo['y01_magnet']['s'])[1]} (column rear plate Y 376)")

    # 7. anchors: JSON = table (xyz, motion, passage); motion cells; devices once; shared joints within 1 mm
    aj = json.loads((R / "out" / "knife_anchors.json").read_text(encoding="utf-8"))["anchors"]
    at = {a[0]: K.vec(a[1]) for a in arows}
    mt = {a[0]: K.parse_motion(a[5]) for a in arows}              # name -> (motion dict, passage box or None)
    sp = {a[0]: K.parse_space(a[5]) for a in arows}               # name -> claimed space box or None
    jbox = lambda n: [[a, b] for a, b in zip(aj[n]["min"], aj[n]["max"])] if "min" in aj[n] else None  # noqa: E731
    check(set(aj) == set(at) and all(np.abs(np.array(aj[n]["xyz"]) - at[n]).max() < 1e-6
                                     and aj[n]["motion"] == mt[n][0] and aj[n].get("passage") == mt[n][1]
                                     and jbox(n) == sp[n] for n in at),
          f"knife_anchors.json = anchors table: xyz, motion, passage, space ({len(at)} anchors)")
    check(all(aj[n].get("class") and aj[n].get("source") and "error_mm" in aj[n] for n in aj), "every anchor has class, error, source")
    for n, (m, p) in mt.items():
        k, rg = m["kind"], m.get("range")
        ok = k in KINDS and (rg is None or rg[0] < rg[1]) and (p is None or k == "fixed")
        if k in ("rot", "trans"):
            ok = ok and unit(m.get("axis")) and rg is not None and (k == "trans" or len(m.get("pivot", [])) == 3)
        elif k == "planar":
            nv, ends = m.get("normal"), m.get("ends", [])
            ok = ok and unit(nv) and "plane" in m and len(ends) == 2 and all(e in at for e in ends) and all(
                abs(float(np.dot(nv, at[q])) - m["plane"]) < 0.01 for q in [n] + ends)
        elif k == "state":
            of = mt.get(m.get("of"), ({}, None))[0]
            ofr = of.get("range", [1, 0])
            ok = ok and of.get("kind") in ("rot", "trans") and "at" in m and ofr[0] <= m["at"] <= ofr[1] \
                and np.abs(moved(at[m["of"]], of, m["at"]) - at[n]).max() < 0.5
        if p is not None:
            ok = ok and all(p[i][0] <= at[n][i] <= p[i][1] for i in range(3))
        sq = sp[n]
        if sq is not None:
            ok = ok and k == "fixed" and p is None and all(sq[i][0] < sq[i][1] and sq[i][0] <= at[n][i] <= sq[i][1]
                                                           for i in range(3))
        keys = " ".join(f"{q}={m[q]}" for q in ("axis", "pivot", "range", "normal", "plane", "ends", "of", "at") if q in m)
        check(ok, f"motion {n}: {k} {keys}" + (f" passage {p}" if p else "") + (f" space {sq}" if sq else ""))
    mc = mt["crank.centre"][0]
    sense = -mc["axis"][1] if unit(mc.get("axis")) else 0              # +1 = counter-clockwise seen from the front
    th_t, th_b = math.degrees(math.atan2(ut[1], ut[0])), math.degrees(math.atan2(-ub[1], -ub[0]))
    want = ((th_b - th_t) * sense) % 360
    cc, mp = at["crank.centre"], mt["crank.pin.tdc"][0]
    check(np.abs(np.array(cc) - [cx, y, cz]).max() < 0.01 and mc.get("pivot") == cc and mp.get("pivot") == cc
          and mp.get("axis") == mc.get("axis") and mc.get("axis") in ([0, -1, 0], [0, 1, 0])
          and np.abs(np.array(at["crank.pin.tdc"]) - [pt[0], y, pt[1]]).max() < 0.5
          and np.abs(np.array(at["crank.pin.bottom"]) - [pb[0], y, pb[1]]).max() < 0.5
          and abs(mt["crank.pin.bottom"][0].get("at", -1) - want) < 0.5,
          f"crank anchors = kinematics: centre, pin at TDC and BDC; BDC after {want:.2f} deg about axis {mc.get('axis')}")
    for n, z in (("knife.edge.rest", er), ("holder.pin.rest", hz)):
        m = mt[n][0]
        check(m.get("axis") == [0, 0, -1] and m.get("range") == [0, s] and abs(at[n][2] - z) < 0.01
              and (n != "holder.pin.rest" or np.abs(np.array(at[n]) - [hx, y, hz]).max() < 0.01),
              f"{n}: translates down 0..{s} (the stroke) from Z {z}")
    mid, mm = (np.array(at["crank.pin.tdc"]) + at["holder.pin.rest"]) / 2, mt["conrod.mid.rest"][0]
    check(np.abs(mid - at["conrod.mid.rest"]).max() < 0.5 and mm.get("plane") == y
          and mm.get("ends") == ["crank.pin.tdc", "holder.pin.rest"],
          f"conrod.mid.rest = midpoint of the rod ends at rest {mid.round(2)}, in the rod plane Y {y}")
    check(mt["lock.pin_1"][0].get("axis") == mt["magnet.Y01"][0].get("axis")
          and mt["lock.pin_1"][0].get("range") == mt["magnet.Y01"][0].get("range"),
          "lock pin 1 and the Y01 plunger: same axis and stroke")
    counts = {d: 0 for d in DEVICES}
    others = {}
    for f in sorted((R / "out").glob("*_anchors.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))["anchors"] if f.name != "knife_anchors.json" else at
        for n in doc:
            if n in counts:
                counts[n] += 1
        if f.name != "knife_anchors.json":
            others.update({n: (v["xyz"] if isinstance(v, dict) else v) for n, v in doc.items()})
    check(all(c == 1 for c in counts.values()), f"10 devices exactly once across all anchors files: {counts}")
    for n in at:
        if n in others:
            dev = float(np.abs(np.array(others[n]) - at[n]).max())
            check(dev <= 1, f"shared anchor {n} agrees with the other part within 1 mm (dev {dev:.2f})")
    for n, ang in (("sensor.S12", th_b), ("sensor.S13", th_b + 15 * sense), ("sensor.S14", th_t)):
        p = np.array(at[n])
        rr, aa = math.hypot(p[0] - cx, p[2] - cz), math.degrees(math.atan2(p[2] - cz, p[0] - cx))
        check(abs(rr - 90) < 1 and abs((aa - ang + 180) % 360 - 180) < 1 and cm_[0] - 10 <= p[1] <= cm_[1] + 10,
              f"{n} on the vane circle r 90 at crank angle {ang:.2f}, at the cam disc (Y {p[1]})")

    # 7b. lock: SQ1/SQ2 read the flag on y01_tail, fixed to pin 1 and moving with it (F62 view P); conrod range
    aerr = {a[0]: float(a[3]) for a in arows}
    if "y01_tail" in geo:
        tc, ts = K.vec(geo["y01_tail"]["c"]), K.rng(geo["y01_tail"]["s"])
        pc, ps = K.vec(geo["lock_pin_1"]["c"]), K.rng(geo["lock_pin_1"]["s"])
        st = mt["lock.pin_1"][0].get("range", [0, 0])[1]
        ends = [np.array([tc[0], ts[1] + d, tc[1]]) for d in (0, st)]
        ds = [float(np.linalg.norm(np.array(at[n]) - e)) for n in ("sensor.SQ1", "sensor.SQ2") for e in ends]
        lim = min(aerr["sensor.SQ1"], aerr["sensor.SQ2"])
        q1, q2 = np.array(at["sensor.SQ1"]), np.array(at["sensor.SQ2"])
        ok = (np.abs(np.array(tc) - pc).max() < 0.01 and abs(ts[0] - ps[1]) < 0.01 and max(ds) <= lim
              and abs(q1[1] - ends[0][1]) <= 1 and abs(q2[1] - ends[1][1]) <= 1 and np.abs((q1 - q2)[[0, 2]]).max() <= 1)
        check(ok, f"SQ1, SQ2 within {lim:.0f} of the flag on y01_tail (coaxial with pin 1, from its Y01 end, moves 0..{st:g}): "
                  f"{min(ds):.1f}..{max(ds):.1f} mm; SQ1 at the modelled pin-in station Y {ends[0][1]:g}, SQ2 at the modelled pin-out station Y {ends[1][1]:g} (which sensor reads which state is not printed, M10)")
    else:
        check(False, "SQ1, SQ2 within their error of the flag on y01_tail (body y01_tail missing)")
    angs = []
    for kk in range(720):
        th = math.radians(kk / 2)
        px = cx + r * math.cos(th)
        angs.append(math.degrees(math.atan2(math.sqrt(L * L - (hx - px) ** 2), px - hx)))
    crg = mt["conrod.mid.rest"][0].get("range")
    check(crg is not None and abs(crg[0] - min(angs)) < 0.1 and abs(crg[1] - max(angs)) < 0.1,
          f"conrod.mid.rest range = the rod's angle to the horizontal over one turn {min(angs):.2f}..{max(angs):.2f} deg")

    # 9. the spec's own rules (testers' round 1): term, source key, ranges, measure rows, class of absolute Z on an E base
    text = spec.read_text(encoding="utf-8")
    srckeys = set(re.findall(r"^\| ([A-Z][A-Z0-9]*) \| ", text.split("## Sources", 1)[1].split("\n## ", 1)[0], re.M))
    noterm = [b for b, rr in rows.items() if not re.search(r"[\u0400-\u04FF]|CZ |no term", rr[1])]
    check(not noterm, f"every model row names its Russian or Czech term or says no term is printed (missing: {noterm})")
    nosrc = [b for b, rr in rows.items() if not (set(re.findall(r"[A-Z][A-Z0-9]*", rr[5])) & srckeys)]
    check(not nosrc, f"every model row cites a key of the sources table, i.e. a file and page (missing: {nosrc})")
    # 9c. source keys over the whole spec (soft critic t2 g13): a cited key has a row in the Sources table (cited in any
    #     section, or in another row's cells), and every row's key is cited outside that table (no orphans)
    keyre = re.compile(r"(?<![A-Za-z0-9_])(P\d+|F\d+|W\d+|PH\d+|HL|PL|OLD|FR)(?![A-Za-z0-9_])")
    s_head, s_rest = text.split("## Sources", 1)
    s_table, s_tail = s_rest.split("\n## ", 1)
    cited_out = set(keyre.findall(s_head + "\n## " + s_tail))
    cited_any = cited_out | set(keyre.findall(re.sub(r"^\| [A-Z][A-Z0-9]* \| ", "| ", s_table, flags=re.M)))
    offgram = sorted(k for k in srckeys if not keyre.fullmatch(k))
    check(not offgram, f"every key of the Sources table fits the key pattern P/F/W/PH + number, HL, PL, OLD, FR (off: {offgram})")
    undef = sorted(cited_any - srckeys)
    check(not undef, f"every source key cited in the spec has a row in the Sources table ({len(cited_any)} cited; undefined: {undef})")
    orphan = sorted(srckeys - cited_out)
    check(not orphan, f"every key of the Sources table is cited outside it, no orphans ({len(srckeys)} rows; orphans: {orphan})")
    norange = [n for n, (m, _) in mt.items() if m["kind"] in ("rot", "trans", "planar") and "range" not in m]
    check(not norange, f"every moving anchor has a range (missing: {norange})")
    mrows = re.findall(r"^\| (M\d+) \|", text, re.M)
    hdr = re.search(r"\(M1-M(\d+) below", text)
    check(mrows == [f"M{i}" for i in range(1, len(mrows) + 1)] and hdr is not None and int(hdr.group(1)) == len(mrows),
          f"measure rows M1..M{len(mrows)} in order; line 6 says M1-M{hdr.group(1) if hdr else '?'}")
    mark = "Measure rows per body (checked):"
    cov = dict(re.findall(r"(\w+) (M\d+)[;.]", text.split(mark, 1)[1].split("\n", 1)[0])) if mark in text else {}
    miss = [b for b in rows if cov.get(b) not in mrows]
    check(not miss, f"every model row maps to an existing measure row (missing: {miss})")
    kincls = dict(re.findall(r"^\| (edge_z_\w+) \| [^|]+ \| [^|]+ \| (\w+) \|", text, re.M))
    ebase = {**kincls, **{a[0]: a[2] for a in arows if a[0].startswith("knife.edge.")}}
    check(len(ebase) == 4 and all(c == "E" for c in ebase.values()),
          f"absolute knife-edge Z on the frame's E base (stick top Z 885, E +-100) is class E: {ebase}")

    # 9b. round 7 (tester 3 round 2 N1; soft critic t2 g9-g10): the JSON's class, error and source = the table;
    #     the [?] marks that must stay; no page credited for the SQ1/SQ2 assignment; M2, M4 and the prose = kinematics
    tab = {a[0]: (a[2], float(a[3]), a[4]) for a in arows}
    drift = [n for n in tab if n in aj and (aj[n].get("class"), aj[n].get("error_mm"), aj[n].get("source")) != tab[n]]
    check(not drift, f"knife_anchors.json = anchors table: class, error, source ({len(tab)} anchors; drift: {drift})")
    acell = {a[0]: (a[4], a[5]) for a in arows}
    noq = [n for n in ("sensor.S12", "sensor.S13", "sensor.S14") if not all("[?]" in c for c in acell[n])]
    noq += [n for n in ("sensor.SQ1", "sensor.SQ2") if "[?]" not in acell[n][0]]
    noq += [b for b in ("flywheel_2", "lever_7_left", "lever_7_right") if "[?]" not in " ".join(rows[b])]
    check(not noq, f"must stay [?]: S12-S14 place and function, SQ1/SQ2 assignment, flywheel = pulley, levers 7 (missing: {noq})")
    sqsrc = [n for n in ("sensor.SQ1", "sensor.SQ2") if "not printed" not in acell[n][0]]
    m10 = re.search(r"^\| M10 \|.*$", text, re.M)
    check(not sqsrc and m10 is not None and "not printed" in m10.group(0),
          f"no page credited for the SQ1/SQ2 assignment: both anchors and M10 say not printed (missing: {sqsrc})")
    num = lambda s: float(s.replace(",", "."))  # noqa: E731
    m2 = re.search(r"^\| M2 \|[^|]*\|[^|]*\| ([\d,]+); [^;]*; ([\d,]+); ([\d,]+);", text, re.M)
    check(m2 is not None and abs(num(m2.group(1)) - kin["stroke"]) < 0.05 and abs(num(m2.group(2)) - kin["crank_radius"]) < 0.05
          and abs(num(m2.group(3)) - kin["rod_length"]) < 0.05,
          f"M2 stroke, crank radius, rod length = kinematics {kin['stroke']:.0f}, {kin['crank_radius']:.1f}, {kin['rod_length']:.1f}")
    dia = lambda b: float(re.search(r"\bd=([\d.]+)", rows[b][2]).group(1))  # noqa: E731
    r14, r18 = (n * dia("m1_pulley") / dia("flywheel_2") / 42 for n in (1420, 1800))
    m4 = re.search(r"ratio ≈ (\d+) \(([\d,]+) at 1420/min, ([\d,]+) at 1800/min", text)
    check(m4 is not None and abs(num(m4.group(2)) - r14) < 0.05 and abs(num(m4.group(3)) - r18) < 0.05
          and r14 <= float(m4.group(1)) <= r18,
          f"M4 worm ratio = M1 speed x pulley Ø / flywheel Ø / 42 cuts per min (P7): {r14:.2f} at 1420/min, {r18:.2f} at 1800/min")
    pr = re.search(r"crank pin at TDC \(([-−\d.]+), ([-−\d.]+), ([-−\d.]+)\), at the bottom \(([-−\d.]+), ([-−\d.]+), ([-−\d.]+)\)", text)
    pv = [float(g.replace("−", "-")) for g in pr.groups()] if pr else []
    check(len(pv) == 6 and np.abs(np.array(pv[:3]) - at["crank.pin.tdc"]).max() < 0.01
          and np.abs(np.array(pv[3:]) - at["crank.pin.bottom"]).max() < 0.01,
          "prose 'Derived points': crank pin at TDC and at the bottom = anchors crank.pin.tdc and crank.pin.bottom")
    m9 = re.search(r"^\| M9 \|.*$", text, re.M)
    m9v = {s: (re.search(s + r" \(([-−\d.]+), ([-−\d.]+), ([-−\d.]+)\) at ([-−\d,]+)°", m9.group(0)) if m9 else None)
           for s in ("S12", "S13", "S14")}
    m9a = {"S12": th_b, "S13": th_b + 15 * sense, "S14": th_t}
    f9 = lambda g: num(g.replace("−", "-"))  # noqa: E731
    check(all(m9v.values()) and all(
        np.abs(np.array([f9(g) for g in m9v[s].groups()[:3]]) - at["sensor." + s]).max() < 1
        and abs((f9(m9v[s].group(4)) - m9a[s] + 180) % 360 - 180) < 0.1 for s in m9v),
          "M9: S12, S13, S14 places (±1 mm) and switching angles (±0,1°) = anchors; S13 15° after S12 in the turn")

    # 8. frame: passages named by both parts; zero intersection outside them at rest and over one crank turn
    if "--no-sweep" in argv:
        return finish()
    fpath = Path(argv[argv.index("--frame-anchors") + 1]) if "--frame-anchors" in argv else R / "out" / "frame_anchors.json"
    fan = json.loads(fpath.read_text(encoding="utf-8"))["anchors"]
    allowed = None
    for n, (m, p) in mt.items():
        if p is None:
            continue
        fx = fan.get(n)
        fx = fx["xyz"] if isinstance(fx, dict) else fx
        dev = float(np.abs(np.array(fx) - at[n]).max()) if fx is not None else None
        named = dev is not None and dev <= 1
        check(named, f"passage {n} named in {fpath.name} at the same point"
              + (f" (dev {dev:.2f})" if dev is not None else " - not yet") + f"; box x {p[0]} y {p[1]} z {p[2]}")
        if named:
            lo, hi = np.array(p)[:, 0], np.array(p)[:, 1]
            box = mf.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())
            allowed = box if allowed is None else allowed + box
    frame = {n.split(".", 1)[1]: to_manifold(m) for n, m in load_scene(R / "out" / "frame.glb").items()}
    fbb = {n: bb(m) for n, m in frame.items()}
    rest = {b: K.build_body(rows[b][2]) for b in rows}
    worst, outside = {}, {}
    # room of the hydraulic box (P36): the knife may enter frame.cavity.right_support only inside its space claim
    cav = fan.get("frame.cavity.right_support")
    cbb = np.array([cav["min"], cav["max"]], dtype=float) if isinstance(cav, dict) and "min" in cav else None
    cbox = mf.Manifold.cube((cbb[1] - cbb[0]).tolist()).translate(cbb[0].tolist()) if cbb is not None else None
    claim = sp.get("space.knife.drive_unit")
    clbox = mf.Manifold.cube([b - a for a, b in claim]).translate([a for a, _ in claim]) if claim else None
    cav_lo = cav_hi = rest_in = None
    cav_out = 0.0
    th0 = math.atan2(ut[1], ut[0])
    steps = 120
    maxstep = 0.0
    prev = 0.0
    th_bdc = math.atan2(-ub[1], -ub[0]) % (2 * math.pi)        # exact bottom position added to the steps
    angles = sorted([th0 + 2 * math.pi * k / steps for k in range(steps + 1)]
                    + [th0 + ((th_bdc - th0) % (2 * math.pi))])
    for k, th in enumerate(angles):
        P = np.array([cx, cz]) + r * np.array([math.cos(th), math.sin(th)])
        Hz = P[1] + math.sqrt(L * L - (hx - P[0]) ** 2)
        dz = hz - Hz
        maxstep, prev = max(maxstep, abs(dz - prev)), dz
        state = dict(rest)
        for b in ("knife", "holder", "holder_pin"):
            state[b] = rest[b].translate([0, 0, -dz])
        state["conrod"] = K.rod([P[0], y, P[1]], [hx, y, Hz], float(geo["conrod"]["d"]))
        state["crank_pin"] = K.cylinder("y", [P[0], P[1]], float(geo["crank_pin"]["d"]), *K.rng(geo["crank_pin"]["s"]))
        moving = list(rest) if k == 0 else ["knife", "holder", "holder_pin", "conrod", "crank_pin"]
        for b in moving:
            mb = bb(state[b])
            if cbox is not None and overlap(mb, cbb):
                ib = state[b] ^ cbox
                if ib.volume() > 0.5:
                    q2 = bb(ib)
                    cav_lo = q2[0] if cav_lo is None else np.minimum(cav_lo, q2[0])
                    cav_hi = q2[1] if cav_hi is None else np.maximum(cav_hi, q2[1])
                    if k == 0:
                        rest_in = ib if rest_in is None else rest_in + ib
                    cav_out = max(cav_out, (ib - clbox).volume() if clbox is not None else ib.volume())
            for fn, fm_ in frame.items():
                if not overlap(mb, fbb[fn]):
                    continue
                inter = state[b] ^ fm_
                v = inter.volume()
                if v <= 0.5:
                    continue
                worst[(b, fn)] = max(worst.get((b, fn), 0), v)
                out_ = inter - allowed if allowed is not None else inter
                ov_ = out_.volume()
                if ov_ > outside.get((b, fn), (0.0, None))[0]:
                    outside[(b, fn)] = (ov_, bb(out_))
    check(maxstep <= 10, f"sweep: one crank turn in {steps} steps, holder moves <= {maxstep:.1f} mm per step")
    cut = worst.pop(("knife", "cutting_stick"), 0.0)
    outside.pop(("knife", "cutting_stick"), None)
    check(cut <= 1150 * 0.2 * 2, f"knife into the cutting stick at the bottom: {cut:.1f} mm3 (edge 0.15 deep, allowed)")
    bad = []
    for pair, v in sorted(worst.items()):
        ov_, q = outside.get(pair, (0.0, None))
        if ov_ > 0.5:
            bad.append(pair)
            check(False, f"collision {pair[0]} x frame.{pair[1]}: {v:.1f} mm3, of it {ov_:.1f} mm3 outside named passages "
                         f"in X {q[0, 0]:.0f}..{q[1, 0]:.0f} Y {q[0, 1]:.0f}..{q[1, 1]:.0f} Z {q[0, 2]:.0f}..{q[1, 2]:.0f}")
        else:
            print(f"NOTE {pair[0]} x frame.{pair[1]}: {v:.0f} mm3, all inside named passages")
    check(not bad, f"no intersection with the frame outside named passages at rest or over the stroke "
                   f"({len(worst) - len(bad)} pairs meet only inside passages)")
    tank_dm3 = 35.0                                     # OZ1 tank 593-05.1100, 35 dm3 (HL p.25, 231704)
    if cbb is None or claim is None:
        check(False, "frame.cavity.right_support (frame) and space.knife.drive_unit (knife) both exist")
        return finish()
    ext = np.array([cav_lo, cav_hi]) if cav_lo is not None else None
    txt = (f"X {ext[0, 0]:.1f}..{ext[1, 0]:.1f} Y {ext[0, 1]:.1f}..{ext[1, 1]:.1f} Z {ext[0, 2]:.1f}..{ext[1, 2]:.1f}"
           if ext is not None else "none")
    vol = rest_in.volume() / 1000 if rest_in is not None else 0.0
    check(cav_out <= 0.5, f"knife in frame.cavity.right_support (room of the hydraulic box, P36) only inside "
                          f"space.knife.drive_unit: {vol:.0f} cm3 at rest, extent over the stroke {txt}, "
                          f"{cav_out:.1f} mm3 outside the claim")
    cl = np.array(claim, dtype=float).T                 # rows: min, max
    check(ext is not None and np.abs(cl - ext).max() <= 1.0,
          f"space.knife.drive_unit {claim} = the knife's extent in that cavity within 1 mm")
    free = float(np.prod(cbb[1, :2] - cbb[0, :2]) * (cl[0, 2] - cbb[0, 2])) / 1e6
    check(free >= tank_dm3, f"room below the claim for the hydraulic tank OZ1 ({tank_dm3:.0f} dm3, HL p.25): {free:.1f} dm3 "
                            f"(cavity Z {cbb[0, 2]:.0f}..{cl[0, 2]:.0f}); front strip Y {cbb[0, 1]:.1f}..{cl[0, 1]:.1f} "
                            f"free at all heights for the filler (P36)")
    return finish()


def finish():
    print(f"\n{'ALL PASS' if not fails else 'FAILED: ' + str(len(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
