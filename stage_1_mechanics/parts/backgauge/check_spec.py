"""Checks of the backgauge part (thread 4, episode 1) against its spec and the other parts.

Run:  python stage_1_mechanics/parts/backgauge/check_spec.py [--spec <md>] [--out <dir>] [--frame-anchors <json>]
                                                            [--require-frame-names]
With --spec or --out it first builds the model from that spec into that folder (mutation_test.py uses this).
The other parts are read from stage_1_mechanics/out. One PASS or FAIL line per check, then ALL PASS or
FAILED: n; exit 0 only when all pass.
 7  outer size: backgauge.stl and .glb bounds = OUTER table +-1 mm; GLB nodes = MODEL TABLE bodies; each node =
    its geometry cell rebuilt (bounds 0.01 mm, volume 0.1 %) and closed.
 7b the Components cells (position at rest) = the built bodies +-1 mm, five lines: the union of each axis' ranges;
    each ";" part = one body's extent; single values (axis lines, "(centre n)", "front at"); relations (gear left
    of the knob, carriage on the nut, eye on the shaft axis, frame anchors table.front_edge and table.underside);
    every number of a cell used by one of these.
 8  passages: each is named in the frame anchors file at the same point within 1 mm (then it may meet any frame
    body), or it is marked cut_at=assembly with the DECISION 2 mark and lies in the frame body cut_from names
    (then it may meet that body only). A bore passage is its cylinder (bore_d along the axis), else the box.
    --require-frame-names: only the first way counts (the rule before DECISION 2). Each space box free of other
    parts' bodies. At rest no backgauge body meets a body of another part (every out/<part>.glb but backgauge
    and assembly) outside the passages allowed for that body.
 9  sweep face 1150 -> 25 (d = 0..1125 in steps of 10 and the end): the moving group against the other parts as
    in 8; each passage cut at assembly is used by some body; the neck's part in the table slab inside table.slot
    + joint.slot.front_extension, the apex link's inside table.slot; the moving group clear of the backgauge's
    own other bodies; all above the table inside table.rear_outline.
 10 anchors: out file = ANCHORS table; sensor.S24, sensor.S27, sensor.BR40, motor.M2 exactly once over all
    out/*_anchors.json; a name shared with another part is a joint (no device kind, same point within 1 mm; --parts-dir <dir> reads the other parts' anchors from a copy); anchors at their bodies;
    travel ends; switch trips.
 11 spec: each component has term, source, class, error; components = model-table components; each class with
    E has a measure row (MEASURE MAP), each map row names known components, G1..G10 have measure lines, each
    line gives where, what, model value and error; each map component is named (its words) on a measure line
    of its row; the prose travel line equals the anchors.
 12 space: the SPACE table names each body once; the bodies that leave frame.keepout.backgauge_drive at face
    1150 or 25 are exactly those it lists outside it; each body lies inside its listed rooms (none = no claim).
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
sys.path.insert(0, str(HERE))
import backgauge as B                                    # noqa: E402

FAILS = []
DEVICES = ("sensor.S24", "sensor.S27", "sensor.BR40", "motor.M2")
DEVICE_KINDS = ("sensor.", "motor.", "valve.", "button.", "switch.", "magnet.", "clutch.", "brake.")


def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        FAILS.append(msg)
    return ok


def arg(argv, name, default):
    return Path(argv[argv.index(name) + 1]) if name in argv else default


def scene_meshes(path):
    sc = trimesh.load(path, force="scene")
    out = {}
    for n in sc.graph.nodes_geometry:
        T, g = sc.graph[n]
        tm = sc.geometry[g].copy()
        tm.apply_transform(T)
        out[n] = tm
    return out


def to_manifold(tm):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                               tri_verts=np.asarray(tm.faces, dtype=np.uint32)))


def bounds_of(m):
    v = np.asarray(m.to_mesh().vert_properties)[:, :3]
    return np.array([v.min(0), v.max(0)]) if len(v) else None


def cube(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return mf.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def overlap(a, b):
    return bool(np.all(a[0] < b[1]) and np.all(b[0] < a[1]))


def in_poly(p, poly, tol=0.5):
    x, y = p
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / ((dx * dx + dy * dy) or 1.0)))
        if (x1 + t * dx - x) ** 2 + (y1 + t * dy - y) ** 2 <= tol * tol:
            return True
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * dx / dy:
            c = not c
    return c


def fmt_box(q):
    return f"X {q[0, 0]:.0f}..{q[1, 0]:.0f} Y {q[0, 1]:.0f}..{q[1, 1]:.0f} Z {q[0, 2]:.0f}..{q[1, 2]:.0f}"


def passage_solid(a):
    """A passage anchor as a solid: a bore along Y = cylinder bore_d about the anchor's X, Z over the box's Y;
    any other passage = its box."""
    p = np.array(a["passage"], float)
    if "bore_d" in a and [abs(v) for v in a["axis"]] == [0.0, 1.0, 0.0]:
        return B.cyl_y((a["xyz"][0], a["xyz"][2]), float(a["bore_d"]), p[1, 0], p[1, 1])
    return cube(p[:, 0], p[:, 1])


def main(argv):
    spec = arg(argv, "--spec", B.SPEC)
    out = arg(argv, "--out", R / "out")
    if "--spec" in argv or "--out" in argv:
        B.main(["--spec", str(spec), "--out", str(out)])
    text = spec.read_text(encoding="utf-8")
    bodies, arows, outer = B.read_spec(spec)
    rows = {r[0]: r for r in bodies}
    group = {r[0]: r[2] for r in bodies}

    # ---------------------------------------------------------------- 7 outer size and bodies
    ob = np.array([[outer[a][0] for a in "xyz"], [outer[a][1] for a in "xyz"]])
    stl = trimesh.load(out / "backgauge.stl")
    dev = float(np.abs(stl.bounds - ob).max())
    check(dev <= 1, f"7 outer size: STL bounds {stl.bounds.round(2).tolist()} = OUTER {ob.tolist()} (dev {dev:.3f})")
    glb = scene_meshes(out / "backgauge.glb")
    gb = np.array([np.min([m.bounds[0] for m in glb.values()], 0), np.max([m.bounds[1] for m in glb.values()], 0)])
    check(float(np.abs(gb - ob).max()) <= 1, f"7 outer size: GLB bounds {gb.round(2).tolist()}")
    names = {"backgauge." + b for b in rows}
    check(set(glb) == names, f"7 GLB nodes = model table bodies ({len(glb)} nodes, {len(names)} rows)"
          + (f"; differ {sorted(set(glb) ^ names)}" if set(glb) != names else ""))
    rest, off = {}, []
    for b in rows:
        rest[b] = B.build_body(rows[b][3])
        tm = glb.get("backgauge." + b)
        if tm is None:
            off.append(b + " (missing)")
            continue
        if (np.abs(tm.bounds - bounds_of(rest[b])).max() > 0.01 or not tm.is_watertight
                or abs(tm.volume - rest[b].volume()) > 1e-3 * rest[b].volume()):
            off.append(b)
    check(not off, f"7 each GLB body = its geometry cell rebuilt, closed: {len(rows) - len(off)} of {len(rows)}"
          + (f"; off: {off}" if off else ""))
    rb = {b: bounds_of(m) for b, m in rest.items()}
    # 7b the Components cells "position at rest" (where a reader looks positions up) = the built bodies, +-1 mm.
    #    Ranges: critic t4 g10 after tester 3 r2. Segments, single values, relations, number count: critic t4 g11
    #    on r6. f = face Y at rest 1150; "X ±550" and "X ±(60..92)" are mirrored. Per component cell:
    #    ranges    the union of every X/Y/Z range = the union of its bodies' bounds;
    #    segments  in each ";" part every range is the extent of one body (both mirror bodies for "±(a..b)"), so
    #              a range nested inside the union cannot drift either;
    #    values    a single "<axis> <n>" (axis line) and "(centre n)" after a range = the centre of the
    #              component's bodies on that axis; "front at Y n" = their Y minimum;
    #    relations "(centre n left of the knob centre)", "(centred on the nut)", "<body> Øn on the shaft axis",
    #              "n behind <frame anchor> m", "hung from the table underside" ("(as S24)" takes S24's) against
    #              those bodies and the frame anchors file;
    #    numbers   every number of a cell is used by one of the above (S24, BR40, M2 are names, not numbers).
    def check_7b():
        csec = text.split("## Components", 1)[1].split("\n## ", 1)[0]
        num = r"[−-]?\d+(?:[.,]\d+)?"
        term = rf"(?:f\s*[+−-]\s*\d+(?:[.,]\d+)?|f|{num})"
        named = {"knob": "handwheel_1", "nut": "nut", "shaft": "handwheel_shaft"}
        fa = json.loads(arg(argv, "--frame-anchors", R / "out" / "frame_anchors.json")
                        .read_text(encoding="utf-8"))["anchors"]
        underside = "hung from the table underside"

        def val(v):
            v = v.replace("−", "-").replace(",", ".").replace(" ", "")
            return 1150.0 + (float(v[1:]) if len(v) > 1 else 0.0) if v.startswith("f") else float(v)

        def take(s, pat):          # the matches of pat in s, and s with them blanked out (they are checked)
            ms = list(re.finditer(pat, s))
            for m in ms:
                s = s[:m.start()] + "#" * (m.end() - m.start()) + s[m.end():]
            return ms, s

        cpos = {}
        for line in csec.splitlines():
            cc = [x.strip() for x in line.strip().strip("|").split("|")]
            if line.startswith("|") and len(cc) >= 8 and cc[0] != "id" and not set(cc[0]) <= set("-: "):
                cpos[cc[0]] = cc[3]
        cb = {cid: {b: rb[b] for b in rows if rows[b][1] == cid} for cid in cpos}

        def union(cid):
            bl = list(cb[cid].values())
            return np.array([np.min([x[0] for x in bl], 0), np.max([x[1] for x in bl], 0)])

        def centre(cid, i):
            u = union(cid)
            return (u[0][i] + u[1][i]) / 2

        def ref_of(word):
            r = named.get(word, word)
            return r if cb.get(r) else None

        def near(p, q):
            return abs(p - q) <= 1.0

        def fits(bb, s):           # s = (segment, axis, lo, hi, kind); "pmr" = a..b on either side
            _, i, lo, hi, kind = s
            if kind == "pmr":
                return (near(bb[0][i], lo) and near(bb[1][i], hi)) or (near(bb[0][i], -hi) and near(bb[1][i], -lo))
            return near(bb[0][i], lo) and near(bb[1][i], hi)

        keys = ("ranges", "segments", "values", "relations", "numbers")
        bad, cnt = {k: [] for k in keys}, {k: 0 for k in keys}
        nleft = 0
        for cid, cell in cpos.items():
            if not cb[cid]:
                continue
            U = union(cid)
            cnt["numbers"] += len(re.findall(num, re.sub(r"\b[A-Za-z][A-Za-z_.]*\d\w*", " ", cell)))
            work = cell
            # relations
            ms, work = take(work, rf"\(centre\s+({num})\s+(left|right) of the (\w+) centre\)")
            for m in ms:
                cnt["relations"] += 1
                r, d = ref_of(m.group(3)), val(m.group(1)) * (-1 if m.group(2) == "left" else 1)
                if r is None or not near(centre(cid, 0), centre(r, 0) + d):
                    bad["relations"].append(f"{cid}: '{m.group(0)}' but its X centre {centre(cid, 0):.1f}, " + (
                        f"{r} X centre {centre(r, 0):.1f}" if r else f"'{m.group(3)}' unknown"))
            ms, work = take(work, rf"\b(\w+)\s+Ø\s*({num})\s+on the (\w+) axis")
            for m in ms:
                cnt["relations"] += 1
                r, body = ref_of(m.group(3)), f"{cid}_{m.group(1)}"
                if r is None or body not in cb[cid]:
                    bad["relations"].append(f"{cid}: '{m.group(0)}': body {body} or '{m.group(3)}' unknown")
                    continue
                ru, bb, dia = union(r), cb[cid][body], val(m.group(2))
                ax = int(np.argmax(ru[1] - ru[0]))
                for j in (j for j in range(3) if j != ax):
                    if not near(bb[1][j] - bb[0][j], dia) or not near((bb[0][j] + bb[1][j]) / 2, centre(r, j)):
                        bad["relations"].append(f"{cid}: '{m.group(0)}' but {body} {'XYZ'[j]} {bb[0][j]:.1f}.."
                                                f"{bb[1][j]:.1f}, {r} axis at {'XYZ'[j]} {centre(r, j):.1f}")
            ms, work = take(work, rf"({num})\s+behind\s+([a-z_]+\.[a-z_.]+)\s+({num})")
            for m in ms:
                cnt["relations"] += 1
                a = fa.get(m.group(2))
                if a is None or not near(a["xyz"][1], val(m.group(3))) or not near(U[0][1] - a["xyz"][1],
                                                                                    val(m.group(1))):
                    bad["relations"].append(f"{cid}: '{m.group(0)}' but " + (
                        f"{m.group(2)} not in the frame anchors" if a is None else
                        f"{m.group(2)} Y {a['xyz'][1]:g}, front of its bodies Y {U[0][1]:.1f}"))
            for m in re.finditer(rf"\b([XYZ])\s*{term}\s*\.\.\s*{term}\s*\(centred on the (\w+)\)", cell):
                cnt["relations"] += 1
                i, r = "XYZ".index(m.group(1)), ref_of(m.group(2))
                if r is None or not near(centre(cid, i), centre(r, i)):
                    bad["relations"].append(f"{cid}: '{m.group(0)}' but its {m.group(1)} centre {centre(cid, i):.1f}, "
                                            + (f"{r} {centre(r, i):.1f}" if r else f"'{m.group(2)}' unknown"))
            hung = underside in cell
            ms, work = take(work, r"\(as ([A-Za-z]+\d+\w*)\)")
            for m in ms:
                if m.group(1) not in cpos:
                    cnt["relations"] += 1
                    bad["relations"].append(f"{cid}: '{m.group(0)}': no component {m.group(1)}")
                hung = hung or underside in cpos.get(m.group(1), "")
            if hung:
                cnt["relations"] += 1
                a = fa.get("table.underside")
                if a is None or not near(U[1][2], a["xyz"][2]):
                    bad["relations"].append(f"{cid}: {underside}, but top Z {U[1][2]:.1f}, table.underside "
                                            + (f"Z {a['xyz'][2]:g}" if a else "not in the frame anchors"))
            # single values: "front at"
            ms, work = take(work, rf"\bfront at ([XYZ])\s*({num})")
            for m in ms:
                cnt["values"] += 1
                i = "XYZ".index(m.group(1))
                if not near(U[0][i], val(m.group(2))):
                    bad["values"].append(f"{cid}: front at {m.group(1)} {val(m.group(2)):g} vs minimum of its bodies "
                                         f"{U[0][i]:.1f}")
            # ranges: mirrored, then plain (with "(centre n)")
            specs = []
            ms, work = take(work, rf"\b([XYZ])\s*±\s*\(?({num})(?:\s*\.\.\s*({num}))?\)?")
            for m in ms:
                i, k = "XYZ".index(m.group(1)), cell[:m.start()].count(";")
                if m.group(3):
                    a, b = sorted([abs(val(m.group(2))), abs(val(m.group(3)))])
                    specs.append((k, i, a, b, "pmr"))
                else:
                    specs.append((k, i, -abs(val(m.group(2))), abs(val(m.group(2))), "pm"))
            ms, work = take(work, rf"\b([XYZ])\s*({term})\s*\.\.\s*({term})(?:\s*\(centre\s+({num})\))?")
            for m in ms:
                i = "XYZ".index(m.group(1))
                specs.append((cell[:m.start()].count(";"), i, val(m.group(2)), val(m.group(3)), "plain"))
                if m.group(4):
                    cnt["values"] += 1
                    if not near(centre(cid, i), val(m.group(4))):
                        bad["values"].append(f"{cid}: (centre {val(m.group(4)):g}) on {m.group(1)} vs centre of its "
                                             f"bodies {centre(cid, i):.1f}")
            for i, ax in enumerate("XYZ"):
                got = [(-s[3], s[3]) if s[4] == "pmr" else (s[2], s[3]) for s in specs if s[1] == i]
                if got:
                    cnt["ranges"] += 1
                    a, b2 = min(g[0] for g in got), max(g[1] for g in got)
                    d = max(abs(a - U[0][i]), abs(b2 - U[1][i]))
                    if d > 1.0:
                        bad["ranges"].append(f"{cid} {ax}: cell {a:g}..{b2:g} vs bodies {U[0][i]:.1f}..{U[1][i]:.1f} "
                                             f"(dev {d:.1f})")
            for k in sorted({s[0] for s in specs}):
                ss = [s for s in specs if s[0] == k]
                cnt["segments"] += 1
                hit = [b for b, bb in cb[cid].items() if all(fits(bb, s) for s in ss)]
                ok = bool(hit) and all(any(near(cb[cid][b][0][s[1]], s[2]) for b in hit)
                                       and any(near(cb[cid][b][1][s[1]], -s[2]) for b in hit)
                                       for s in ss if s[4] == "pmr")
                if not ok:
                    bad["segments"].append(f"{cid}: '{cell.split(';')[k].strip()}' is no body's extent (bodies: "
                                           + "; ".join(f"{b} {fmt_box(bb)}" for b, bb in cb[cid].items()) + ")")
            # single values: axis lines
            ms, work = take(work, rf"\b([XYZ])\s*({num})")
            for m in ms:
                cnt["values"] += 1
                i = "XYZ".index(m.group(1))
                if not near(centre(cid, i), val(m.group(2))):
                    bad["values"].append(f"{cid}: {m.group(1)} {val(m.group(2)):g} vs centre of its bodies "
                                         f"{centre(cid, i):.1f}")
            ms, work = take(work, r"\b[A-Za-z][A-Za-z_.]*\d\w*")      # names such as S24, BR40, M2
            left = re.findall(num, work)
            if left:
                nleft += len(left)
                bad["numbers"].append(f"{cid}: {left} in '{cell}'")

        def tail(k):
            return f"; off: {bad[k]}" if bad[k] else ""
        check(not bad["ranges"] and cnt["ranges"] > 0, f"7b Components positions at rest = built bodies +-1 mm "
              f"({cnt['ranges']} axis ranges, {len(cpos)} components)" + tail("ranges"))
        check(not bad["segments"] and cnt["segments"] > 0, f"7b Components segments: in each ';' part every range is "
              f"one body's extent (both mirror bodies for ±(a..b)) +-1 mm ({cnt['segments']} parts)" + tail("segments"))
        check(not bad["values"] and cnt["values"] > 0, f"7b Components single values: axis lines and (centre n) = "
              f"centre of the bodies, 'front at' = their minimum, +-1 mm ({cnt['values']} values)" + tail("values"))
        check(not bad["relations"] and cnt["relations"] > 0, f"7b Components relations hold +-1 mm (gear left of the "
              f"knob, carriage on the nut, eye on the shaft axis, knob behind table.front_edge, S24/S27 at "
              f"table.underside: {cnt['relations']})" + tail("relations"))
        check(not bad["numbers"] and cnt["numbers"] > 0, f"7b Components numbers all checked ({cnt['numbers']} numbers "
              f"in {len(cpos)} cells, {nleft} unchecked)" + tail("numbers"))
    check_7b()

    # ---------------------------------------------------------------- 8 at rest, passages, spaces
    fpath = arg(argv, "--frame-anchors", R / "out" / "frame_anchors.json")
    strict = "--require-frame-names" in argv           # the rule before DECISION 2: the frame names every passage
    fan = json.loads(fpath.read_text(encoding="utf-8"))["anchors"]
    mine = json.loads((out / "backgauge_anchors.json").read_text(encoding="utf-8"))["anchors"]
    others = {}
    for g in sorted((R / "out").glob("*.glb")):
        if g.stem not in ("backgauge", "assembly"):
            others.update({n: to_manifold(tm) for n, tm in scene_meshes(g).items()})
    obb = {n: bounds_of(m) for n, m in others.items()}
    print(f"NOTE other parts' bodies read: {len(others)} ({', '.join(sorted({n.split('.')[0] for n in others}))})")
    allowed, cutp = {}, {}       # other body ("*" = any) -> solid where meeting it is allowed; passages cut at assembly
    for n, a in mine.items():
        if "passage" not in a:
            continue
        ps = passage_solid(a)
        shape = f"bore Ø{a['bore_d']:g} in box {a['passage']}" if "bore_d" in a else f"box {a['passage']}"
        fx = fan.get(n)
        d_ = float(np.abs(np.array(fx["xyz"]) - a["xyz"]).max()) if isinstance(fx, dict) else None
        named = d_ is not None and d_ <= 1
        if named or strict:
            check(named, f"8 passage {n} named in {fpath.name} at the same point"
                  + (f" (dev {d_:.2f})" if d_ is not None else " - not yet") + f"; {shape}")
            if named:
                allowed["*"] = ps if "*" not in allowed else allowed["*"] + ps
            continue
        body = a.get("cut_from", "")
        cut = (ps ^ others[body]).volume() if body in others else 0.0
        marked = a.get("cut_at") == "assembly" and a.get("mark") == B.CUT_MARK["assembly"]
        check(marked and cut > 0.5,
              f"8 passage {n}: " + (a["mark"] if marked else "not named by the frame and not marked cut_at=assembly")
              + f", cut out of {body or '(no cut_from)'}" + ("" if body in others else " (no such body)")
              + f": {cut:.0f} mm3 of its material in the {shape}")
        if marked and body in others:
            allowed[body] = ps if body not in allowed else allowed[body] + ps
            cutp[n] = (body, ps)
    for n, a in mine.items():
        if "min" in a:
            box, bx = cube(a["min"], a["max"]), np.array([a["min"], a["max"]], float)
            hits = {o: round((box ^ m).volume(), 1) for o, m in others.items() if overlap(bx, obb[o])}
            hits = {o: v for o, v in hits.items() if v > 0.5}
            check(not hits, f"8 space {n} free of other parts' bodies" + (f": {hits}" if hits else ""))

    # ---------------------------------------------------------------- 9 sweep (d = 0 is the rest state of 8)
    steps = list(range(0, 1125, 10)) + [1125]
    moving = [b for b in rows if group[b] == "moving"]
    worst, outside, selfhit, used = {}, {}, {}, {}
    slab = obb.get("frame.table")
    slot = fan.get("table.slot")
    ext = mine.get("joint.slot.front_extension")
    poly = fan.get("table.rear_outline", {}).get("polygon_xy")
    slab_box = cube(*slab) if slab is not None else None
    slot_box = cube(slot["min"], slot["max"]) if slot else None
    ext_box = cube(*np.array(ext["passage"], float).T) if ext else None
    neck_out = link_out = (0.0, None)
    above = [b for b in moving if rb[b][0][2] >= 885]
    foot_bad = []
    for d in steps:
        sh = np.array([0.0, -float(d), 0.0])
        state = {b: rest[b].translate(sh.tolist()) for b in moving}
        for b in (list(rows) if d == 0 else moving):
            m, mb = state.get(b, rest[b]), rb[b] + (sh if b in state else 0)
            for o, om in others.items():
                if not overlap(mb, obb[o]):
                    continue
                inter = m ^ om
                v = inter.volume()
                if v <= 0.5:
                    continue
                worst[(b, o)] = max(worst.get((b, o), 0.0), v)
                remv = inter
                for k in (o, "*"):
                    if k in allowed:
                        remv = remv - allowed[k]
                rv = remv.volume()
                if rv > outside.get((b, o), (0.0,))[0]:
                    outside[(b, o)] = (rv, bounds_of(remv), 1150 - d)
                for n, (body, ps) in cutp.items():
                    if body == o:
                        u = (inter ^ ps).volume()
                        if u > 0.5:
                            used.setdefault(n, [0.0, set()])
                            used[n][0] = max(used[n][0], u)
                            used[n][1].add(b)
        for b in moving:
            for s in rows:
                if group[s] != "moving" and overlap(rb[b] + sh, rb[s]):
                    selfhit[(b, s)] = max(selfhit.get((b, s), 0.0), (state[b] ^ rest[s]).volume())
        if slab_box is not None and slot_box is not None and ext_box is not None:
            r_ = (state["neck"] ^ slab_box) - slot_box - ext_box
            if r_.volume() > neck_out[0]:
                neck_out = (r_.volume(), 1150 - d)
            r_ = (state["apex_link"] ^ slab_box) - slot_box
            if r_.volume() > link_out[0]:
                link_out = (r_.volume(), 1150 - d)
        if poly:
            for b in above:
                v = np.asarray(state[b].to_mesh().vert_properties)[:, :2]
                if not all(in_poly(p, poly) for p in np.unique(v.round(3), axis=0)):
                    foot_bad.append((b, 1150 - d))
    stepmax = max(np.diff(steps))
    check(steps[0] == 0 and steps[-1] == 1125 and stepmax <= 10,
          f"9 sweep: face 1150 -> 25 in {len(steps) - 1} steps of at most {stepmax} mm")
    bad = []
    for pair, v in sorted(worst.items()):
        rv, q, face = outside.get(pair, (0.0, None, None))
        if rv > 0.5:
            bad.append(pair)
            check(False, f"9 collision {pair[0]} x {pair[1]}: {v:.0f} mm3, {rv:.0f} mm3 outside the passages allowed "
                         f"for {pair[1]}, worst at face Y {face}, in {fmt_box(q)}")
        else:
            print(f"NOTE {pair[0]} x {pair[1]}: {v:.0f} mm3, all inside the passages allowed for {pair[1]}")
    tot_out = sum(outside[p][0] for p in bad)
    check(not bad, f"8/9 no intersection with other parts outside the allowed passages at rest or over the travel "
                   f"({len(worst) - len(bad)} pairs meet only inside passages; {len(bad)} pairs meet outside them, "
                   f"{tot_out:.0f} mm3 summed over each pair's worst step)")
    for n, (body, ps) in cutp.items():
        u, who = used.get(n, (0.0, set()))
        check(u > 0.5, f"9 passage {n} (cut at assembly, DECISION 2) is used: "
                       f"{', '.join(sorted(who)) or 'no backgauge body'} pass(es) through it, up to {u:.0f} mm3 "
                       f"of {body} inside it at one step")
    check(slab_box is not None and slot_box is not None and ext_box is not None,
          "9 frame.table body, table.slot anchor and joint.slot.front_extension exist")
    check(neck_out[0] <= 0.5, f"9 neck inside table.slot + joint.slot.front_extension at every step "
                              f"(max outside {neck_out[0]:.1f} mm3" + (f" at face Y {neck_out[1]})" if neck_out[1] is not None else ")"))
    check(link_out[0] <= 0.5, f"9 apex link inside table.slot at every step (max outside {link_out[0]:.1f} mm3)")
    sh_bad = {k: round(v, 1) for k, v in selfhit.items() if v > 0.5}
    check(not sh_bad, f"9 moving group clear of the backgauge's fixed, spindle and handwheel bodies "
                      f"({len(selfhit)} pairs checked)" + (f": {sh_bad}" if sh_bad else ""))
    check(bool(poly) and not foot_bad, f"9 bodies above the table ({', '.join(above)}) inside table.rear_outline at every step"
          + (f": out {foot_bad[:4]}" if foot_bad else ""))

    # ---------------------------------------------------------------- 10 anchors
    same = json.dumps(B.anchors_json(arows), sort_keys=True) == json.dumps(mine, sort_keys=True)
    check(same, f"10 backgauge_anchors.json = ANCHORS table ({len(mine)} anchors)")
    files = {f.name.replace("_anchors.json", ""): json.loads(f.read_text(encoding="utf-8"))["anchors"]
             for f in arg(argv, "--parts-dir", R / "out").glob("*_anchors.json")
             if f.name != "backgauge_anchors.json"}
    files["backgauge"] = mine
    for dv in DEVICES:
        cnt = sum(dv in a for a in files.values())
        check(cnt == 1, f"10 {dv} exactly once over all anchors files ({cnt}, files {sorted(files)})")
    # a name another part also publishes is a joint (section 05: both export it, same point within 1 mm), whatever
    # its prefix (meta orc ruling in TESTERS_RESULT_t4_r5: interface.clamp.comb_interleave); a device anchor never
    # (section 04 check 10: one anchor per designation over all files; critic t4 g10)
    shared = sorted((n, p) for p, a in files.items() if p != "backgauge" for n in a if n in mine)
    sb = []
    for n, p in shared:
        dv = float(np.abs(np.array(files[p][n]["xyz"], float) - np.array(mine[n]["xyz"], float)).max())
        if n in DEVICES or n.startswith(DEVICE_KINDS) or dv > 1:
            sb.append(f"{n} ({p}, dev {dv:.1f}{', a device' if n in DEVICES or n.startswith(DEVICE_KINDS) else ''})")
    check(not sb, f"10 names shared with other parts are joints (no device, same point within 1 mm): "
          f"{[n for n, _ in shared] or 'none'}" + (f"; bad {sb}" if sb else ""))
    ctr = {b: rb[b].mean(0) for b in rows}
    expect = {"sensor.S24": ctr["S24"], "sensor.S27": ctr["S27"], "sensor.BR40": ctr["encoder_BR40"],
              "motor.M2": ctr["M2"], "handwheel.1": ctr["handwheel_disc"], "backgauge.nut": ctr["nut"],
              "backgauge.face": [0.0, rb["comb_fingers"][0][1], fan["table.top"]["xyz"][2]],
              "backgauge.neck.slot": [ctr["neck"][0], ctr["neck"][1], (slot["min"][2] + slot["max"][2]) / 2],
              "backgauge.apex_link.slot": [ctr["apex_link"][0], ctr["apex_link"][1],
                                           (rb["apex_link"][0][2] + fan["table.top"]["xyz"][2]) / 2],
              "spindle.front_end": [ctr["journal"][0], rb["journal"][0][1], ctr["journal"][2]],
              "spindle.rear_end": [ctr["spindle"][0], rb["spindle"][1][1], ctr["spindle"][2]]}
    for n, e in expect.items():
        d_ = float(np.abs(np.array(mine[n]["xyz"]) - e).max())
        check(d_ <= 1, f"10 {n} at its body {np.round(e, 1).tolist()} (dev {d_:.2f})")
    f_ = mine["backgauge.face"]
    fm = f_["motion"]
    end = np.array(f_["xyz"]) + fm["range"][1] * np.array(fm["axis"])
    check(f_["xyz"][1] == 1150 and fm["range"] == [0.0, 1125.0] and fm["axis"] == [0.0, -1.0, 0.0]
          and float(np.abs(end - mine["backgauge.face.front_end"]["xyz"]).max()) <= 1,
          f"10 travel: face Y 1150 at rest, -Y 0..1125 -> front end {end.round(1).tolist()} (p7: 25..1150)")
    for n, a in mine.items():
        if a["motion"]["kind"] == "trans" and n != "backgauge.face":
            check(a["motion"].get("range") == fm["range"] and a["motion"].get("axis") == fm["axis"],
                  f"10 {n} moves with the face")
    front_y, rear_y = end[1], f_["xyz"][1]               # software limits = travel ends (p7, p41 8.3)
    for n, sgn, lim in (("sensor.S24", -1, front_y), ("sensor.S27", 1, rear_y)):
        m = mine[n]["motion"]
        t, (r0, r1), e = m["trips_at_face_y"], m["trips_range"], m["trips_error"]
        beyond = (sgn * (r0 - lim) >= -1e-6) if sgn > 0 else (sgn * (r1 - lim) >= -1e-6)
        dog = mine[n]["xyz"][1] - t
        check(beyond and r0 <= t <= r1 and e >= max(t - r0, r1 - t) - 1e-6 and abs(m["dog_offset"] - dog) <= 1,
              f"10 {n} trips at face Y {t:g} in {r0:g}..{r1:g}, at or beyond its software limit {lim:g} (p41 8.3), "
              f"error {e:g} covers the band, dog at face + {dog:.0f} (= {m['dog_offset']:g})")
    for n, a in mine.items():
        if "passage" in a:
            p = np.array(a["passage"], float)
            ok = bool(np.all(p[:, 0] <= a["xyz"]) and np.all(np.array(a["xyz"]) <= p[:, 1]))
            if "bore_d" in a:
                ax = int(np.argmax(np.abs(a["axis"])))
                ok = ok and all(p[i, 1] - p[i, 0] >= a["bore_d"] for i in range(3) if i != ax)
            check(ok, f"10 passage {n}: point inside its box" + (", box holds the bore" if "bore_d" in a else ""))
    miss = [n for n, a in mine.items() if not (a.get("class") and a.get("source") and a.get("error_mm") not in (None, ""))]
    check(not miss, "10 every anchor has class, error and source" + (f"; missing {miss}" if miss else ""))

    # ---------------------------------------------------------------- 11 spec rows
    sec = text.split("## Components", 1)[1].split("\n## ", 1)[0]
    comp = {}
    for line in sec.splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(c) >= 8 and c[0] not in ("id",) and not set(c[0]) <= set("-: "):
            comp[c[0]] = c
    cls_ok = re.compile(r"^[DTPEW](/[DTPEW])*$")
    badc = [k for k, c in comp.items() if not (c[1] and c[5] and c[7] and cls_ok.match(c[6]))]
    check(not badc, f"11 each of {len(comp)} components has term, source, class and error" + (f"; bad {badc}" if badc else ""))
    mc = {r[1] for r in bodies}
    check(set(comp) == mc, "11 components table = model table components" + (f"; differ {sorted(set(comp) ^ mc)}" if set(comp) != mc else ""))
    mrows = B.table(text, "<!-- MEASURE MAP START -->", "<!-- MEASURE MAP END -->")
    mmap = {r[0]: [x.strip() for x in r[1].split(",") if x.strip() not in ("", "-")] for r in mrows}
    covered = {x for v in mmap.values() for x in v}
    ecomp = [k for k, c in comp.items() if "E" in c[6]]
    check(all(k in covered for k in ecomp), f"11 each E component ({len(ecomp)}) has a measure row"
          + (f"; without: {[k for k in ecomp if k not in covered]}" if any(k not in covered for k in ecomp) else ""))
    check(covered <= set(comp), "11 measure map names only known components" + (f"; unknown {sorted(covered - set(comp))}" if not covered <= set(comp) else ""))
    gaps = text.split("## Gaps", 1)[1].split("<!-- MEASURE MAP START -->", 1)[0] if "## Gaps" in text else ""
    mlines = [[x.strip() for x in ln.strip().strip("|").split("|")] for ln in gaps.splitlines()
              if re.match(r"^\| G\d+[a-z]? \|", ln)]
    gm = [g for g in (f"G{i}" for i in range(1, 11))
          if not any(re.fullmatch(rf"{g}[a-z]?", c[0]) for c in mlines) or g not in mmap]
    check(not gm, f"11 measure rows G1..G10 have measure lines ({len(mlines)}) in the gaps section and a map row"
          + (f"; missing {gm}" if gm else ""))
    thin = [c[0] for c in mlines if len(c) != 5 or not all(c)]
    check(not thin, "11 each measure line gives where, what, model value with class, and error" + (f"; thin {thin}" if thin else ""))
    # the map's third column names, per component in order, the line of its row whose where/what cell names it
    ltext = {cc[0]: (cc[1] + " " + cc[2]).lower() for cc in mlines if len(cc) >= 3}
    unnamed = []
    for r in mrows:
        comps = mmap.get(r[0], [])
        ents = [e.strip() for e in (r[2] if len(r) > 2 else "").split(";") if e.strip() not in ("", "-")]
        if len(ents) != len(comps):
            unnamed.append(f"{r[0]}: {len(comps)} components, {len(ents)} entries")
            continue
        for k, e in zip(comps, ents):
            ln, _, words = e.partition(":")
            ln, words = ln.strip(), words.strip().lower()
            if not re.fullmatch(rf"{r[0]}[a-z]", ln) or not words or words not in ltext.get(ln, ""):
                unnamed.append(f"{k} ({e})")
    check(not unnamed, f"11 each map component is named on a measure line of its row ({sum(len(v) for v in mmap.values())})"
          + (f"; not named: {unnamed}" if unnamed else ""))
    tp = re.search(r"Face Y (\d+) \(front end\) \.\. (\d+) \(rear end\)", text)
    fe = mine.get("backgauge.face.front_end", {}).get("xyz", [0, 0, 0])[1]
    check(bool(tp) and (float(tp.group(1)), float(tp.group(2))) == (25.0, 1150.0) == (fe, f_["xyz"][1]),
          "11 travel line of the prose = p7 25..1150 = anchors backgauge.face.front_end / backgauge.face"
          + (f" (prose {tp.group(1)}..{tp.group(2)}, anchors {fe}..{f_['xyz'][1]})" if tp else " (line not found)"))

    # ---------------------------------------------------------------- 12 space: where each body lives
    kp = fan.get("frame.keepout.backgauge_drive")
    rooms = {"table.above": cube([-575.0, -729.0, 885.0], [575.0, 1901.0, 1200.0])}
    if kp:
        rooms["keepout"] = cube(kp["min"], kp["max"])
    if slot:
        rooms["table.slot"] = cube(slot["min"], slot["max"])
    for n, a in mine.items():
        if "min" in a:
            rooms[n] = cube(a["min"], a["max"])
        elif "passage" in a:
            rooms[n] = cube(*np.array(a["passage"], float).T)
    where = {}
    for r in B.table(text, "<!-- SPACE START -->", "<!-- SPACE END -->"):
        for b in (x.strip() for x in r[0].split(",")):
            where.setdefault(b, []).append([x.strip() for x in r[1].split(",")])
    twice = sorted(b for b, v in where.items() if len(v) > 1)
    check(set(where) == set(rows) and not twice, f"12 space table names each of the {len(rows)} bodies once"
          + (f"; differ {sorted(set(where) ^ set(rows))}" if set(where) != set(rows) else "")
          + (f"; twice {twice}" if twice else ""))
    unknown = sorted({x for v in where.values() for x in v[0] if x not in rooms and x != "none"})
    check("keepout" in rooms and not unknown, "12 space rooms known: keepout (frame), table.slot, table.above, "
          "this part's spaces and passages" + (f"; unknown {unknown}" if unknown else ""))
    leaves, outr = [], {}
    for b in rows:
        poses = [rest[b]] + ([rest[b].translate([0.0, -1125.0, 0.0])] if group[b] == "moving" else [])
        if "keepout" in rooms and max((p - rooms["keepout"]).volume() for p in poses) > 0.5:
            leaves.append(b)
        rl = where.get(b, [["none"]])[0]
        if "none" in rl:
            continue
        u = None
        for x in rl:
            if x in rooms:
                u = rooms[x] if u is None else u + rooms[x]
        ov = max((p - u).volume() for p in poses) if u is not None else float("inf")
        if ov > 0.5:
            outr[b] = round(ov, 1)
    listed = sorted(b for b, v in where.items() if v[0] != ["keepout"])
    check(sorted(leaves) == listed,
          f"12 bodies leaving frame.keepout.backgauge_drive at face 1150 or 25 ({len(leaves)}) = those the space table "
          f"lists outside it ({len(listed)})"
          + (f"; leave, listed as keepout only: {sorted(set(leaves) - set(listed))}" if set(leaves) - set(listed) else "")
          + (f"; listed outside, stay in: {sorted(set(listed) - set(leaves))}" if set(listed) - set(leaves) else ""))
    check(not outr, "12 each body inside its listed rooms at face 1150 and 25 (no claim: "
          + ", ".join(sorted(b for b, v in where.items() if "none" in v[0])) + ")"
          + (f"; outside: {outr}" if outr else ""))

    print("ALL PASS" if not FAILS else f"FAILED: {len(FAILS)}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
