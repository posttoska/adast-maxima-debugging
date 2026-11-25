"""Checks the frame's written files against spec/frame.md by reading the spec itself (run frame.py first).

It holds no numbers of its own: every expected value is parsed from the spec text.
1. "## Components": each row whose id is a frame body. Its "position" cell gives the body's box:
   "X a…b", "X ±r", "X c" (a centre: the extent comes from the "outer size" cell), "top Z v",
   "underside Z v", "over <body>" (X and Y of that body's row), "plate corners (x, y) …" (X and Y
   from the points); an axis that comes again starts a second sub-box (plate, then apron).
   The union of the sub-boxes must equal the bounds of node frame.<id> in out/frame.glb (±1 mm),
   and the node's extent must equal the "outer size" cell (±1 mm): the stage check that each part's bounding box equals its spec's outer size.
   The rows "table rear taper" and "table slot", with the table row, give the corners that the
   table's section at Z 835, cut from frame.glb, must have; the section may have no other corner.
   Likewise each "plate corners (x, y) …, Z a…b" polygon (side tables) = the corners of its node's
   section at Z (a+b)/2, and no other corner.
2. "## Derived checks": bounding box of all bodies, plan envelope, floor areas at Z 1 (nothing
   else on the floor), table top / stick / width / length, watertight, no interpenetration, and
   no body inside the keep-out box that the "Keep-out:" line names (its box from "## Anchors").
3. "## Anchors": the device-anchor table rows, every "name (x, y, z)" point, every
   "name box X a…b, Y c…d, Z e…f" box and the table.rear_outline polygon, against
   out/frame_anchors.json (±0.5 mm); every JSON anchor must be named exactly once, and no other.
Prints one line per mismatch and a summary line ending PASS or FAIL; exit code 1 on FAIL.
Run:  python check_spec.py [--spec <changed copy of frame.md>]
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

R = Path(__file__).resolve().parent.parent.parent  # stage_1_mechanics
NUM = r"[+-]?\d+(?:\.\d+)?"
TOL_BODY, TOL_ANCHOR = 1.0, 0.5
AXES = "XYZ"
POS_TOKEN = re.compile(rf"\bover\s+(?P<over>[a-z_]+)|(?<![A-Za-z_])(?P<side>top\s+|underside\s+)?(?P<ax>[XYZ])\s+"
                       rf"(?P<val>±\s*{NUM}|{NUM}\s*…\s*{NUM}|{NUM})")
PAIR = rf"\(\s*({NUM})\s*,\s*({NUM})\s*\)"
bad = []


def fail(msg):
    bad.append(msg)


def norm(s):
    """Minus sign -> '-', '...' -> '…', decimal comma -> point (digit,digit only)."""
    s = s.replace("−", "-").replace("...", "…")
    return re.sub(r"(?<=\d),(?=\d)", ".", s)


def section(text, title):
    m = re.search(r"^## " + re.escape(title) + r"[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        fail(f"spec has no section '## {title}'")
        return ""
    return m.group(1)


def table_rows(block):
    out = []
    for line in block.splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*-", line):
            out.append([c.strip() for c in line.strip().strip("|").split("|")])
    return out


def rng(v):
    """'±r' -> (-r, r); 'a…b' -> (a, b); 'c' -> c."""
    v = v.replace(" ", "")
    if v.startswith("±"):
        r = float(v[1:])
        return (-r, r)
    if "…" in v:
        a, b = v.split("…")
        return (float(a), float(b))
    return float(v)


# ---------------------------------------------------------------- the built model
def load_glb():
    scene = trimesh.load(R / "out" / "frame.glb", force="scene")
    meshes = {}
    for node in scene.graph.nodes_geometry:
        tf, gname = scene.graph[node]
        m = scene.geometry[gname].copy()
        m.apply_transform(tf)
        meshes[node] = m
    return meshes


def to_manifold(tm):
    mesh = mf.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                   tri_verts=np.asarray(tm.faces, dtype=np.uint32))
    man = mf.Manifold(mesh)
    if "NoError" not in str(man.status()):
        mesh.merge()
        man = mf.Manifold(mesh)
    return man


# ---------------------------------------------------------------- 1. components
def parse_size(cell):
    c = norm(cell).strip()
    m = re.fullmatch(rf"Ø\s*({NUM})\s*x\s*({NUM})", c)
    if m:
        d, h = float(m.group(1)), float(m.group(2))
        return [d, d, h]
    m = re.fullmatch(rf"({NUM})\s*x\s*({NUM})\s*x\s*({NUM})", c)
    return [float(g) for g in m.groups()] if m else None


def parse_position(body, cell, size, done):
    s = norm(cell)

    def corners(m):
        pts = [(float(a), float(b)) for a, b in re.findall(PAIR, m.group(1))]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return f"X {min(xs)}…{max(xs)}, Y {min(ys)}…{max(ys)}"

    s = re.sub(rf"plate corners\s*((?:{PAIR}\s*)+)", corners, s)
    s = re.sub(r"\([^)]*\)", " ", s)  # remarks such as (centre +932) or (y_A −220…+230)
    boxes, cur = [], {}
    for m in POS_TOKEN.finditer(s):
        if m.group("over"):
            src = done.get(m.group("over"))
            if src is None:
                fail(f"body {body}: 'over {m.group('over')}' names no earlier body row")
                continue
            slots = {"Xlo": src[0][0], "Xhi": src[1][0], "Ylo": src[0][1], "Yhi": src[1][1]}
        else:
            ax, v, side = m.group("ax"), rng(m.group("val")), (m.group("side") or "").strip()
            if side == "top":
                slots = {ax + "hi": v}
            elif side == "underside":
                slots = {ax + "lo": v}
            elif isinstance(v, tuple):
                slots = {ax + "lo": v[0], ax + "hi": v[1]}
            else:
                slots = {ax + "c": v}
        if any(k in cur for k in slots):
            boxes.append(cur)
            cur = {}
        cur.update(slots)
    if cur:
        boxes.append(cur)
    lo_all, hi_all = [np.inf] * 3, [-np.inf] * 3
    for b in boxes:
        for i, ax in enumerate(AXES):
            lo, hi, c = b.get(ax + "lo"), b.get(ax + "hi"), b.get(ax + "c")
            if lo is not None and hi is not None:
                pass
            elif c is not None and size:
                lo, hi = c - size[i] / 2.0, c + size[i] / 2.0
            elif hi is not None and size:
                lo = hi - size[i]
            elif lo is not None and size:
                hi = lo + size[i]
            else:
                fail(f"body {body}: position cell gives no {ax}")
                return None
            lo_all[i], hi_all[i] = min(lo_all[i], lo), max(hi_all[i], hi)
    if not boxes:
        fail(f"body {body}: position cell has no coordinates")
        return None
    return lo_all, hi_all


def check_components(text, meshes):
    rows = table_rows(section(text, "Components"))
    done, sub, plates = {}, {}, {}
    node_ids = {n.split(".", 1)[1] for n in meshes if n.startswith("frame.")}
    for cells in rows[1:]:  # rows[0] = header
        bid = cells[0]
        if bid in ("table rear taper", "table slot"):
            sub[bid] = norm(cells[4])
            continue
        if bid not in node_ids:
            fail(f"component row '{bid}' has no node frame.{bid} in frame.glb")
            continue
        size = parse_size(cells[3])
        if size is None:
            fail(f"body {bid}: outer size cell '{cells[3]}' not understood")
        mp = re.search(rf"plate corners\s*(?P<pts>(?:{PAIR}\s*)+),\s*Z\s+(?P<z0>{NUM})\s*…\s*(?P<z1>{NUM})",
                       norm(cells[4]))
        if mp:
            plates[bid] = ([(float(a), float(b)) for a, b in re.findall(PAIR, mp.group("pts"))],
                           float(mp.group("z0")), float(mp.group("z1")))
        elif "plate corners" in cells[4]:
            fail(f"body {bid}: 'plate corners' not followed by 'Z a…b'")
        box = parse_position(bid, cells[4], size, done)
        if box is None:
            continue
        done[bid] = box
        got = meshes["frame." + bid].bounds
        if np.any(np.abs(got[0] - box[0]) > TOL_BODY) or np.any(np.abs(got[1] - box[1]) > TOL_BODY):
            fail(f"body {bid}: spec box {np.round(box[0], 1).tolist()}..{np.round(box[1], 1).tolist()}, "
                 f"glb {got.round(1).tolist()}")
        ext = got[1] - got[0]
        if size and np.any(np.abs(ext - np.array(size)) > TOL_BODY):
            fail(f"body {bid}: outer size {size}, glb extent {ext.round(1).tolist()}")
    for n in sorted(node_ids - set(done)):
        fail(f"glb node frame.{n} has no (readable) row in the component table")
    return done, sub, plates


def corners_only(p):
    """Drop the points of a section polygon that lie on a straight edge (left there by the mesh's triangles)."""
    keep = []
    for i in range(len(p)):
        e1, e2 = p[i] - p[i - 1], p[(i + 1) % len(p)] - p[i]
        n1, n2 = np.hypot(*e1), np.hypot(*e2)
        if n1 > 1e-6 and n2 > 1e-6 and abs(e1[0] * e2[1] - e1[1] * e2[0]) > 1e-6 * n1 * n2:
            keep.append(p[i])
    return np.array(keep).reshape(-1, 2)


def check_table_section(done, sub, meshes):
    """Corners of the table's section at Z 835 = the table, taper and slot rows, and nothing else."""
    if "table" not in done or "table rear taper" not in sub or "table slot" not in sub:
        fail("table, 'table rear taper' or 'table slot' row missing")
        return
    (x0, y0, _), (x1, _, _) = done["table"]
    t = sub["table rear taper"]
    mt = re.search(rf"taper Y ({NUM})\s*…\s*({NUM})", t)
    mb = re.search(rf"block Y ({NUM})\s*…\s*({NUM}),\s*X\s*±\s*({NUM})", t)
    ms = [m for m in POS_TOKEN.finditer(re.sub(r"\([^)]*\)", " ", sub["table slot"])) if m.group("ax")]
    sl = {m.group("ax"): rng(m.group("val")) for m in ms}
    if not (mt and mb and isinstance(sl.get("X"), tuple) and isinstance(sl.get("Y"), tuple)):
        fail("taper or slot row not understood")
        return
    ta, tb = float(mt.group(1)), float(mt.group(2))
    ba, bb, bw = float(mb.group(1)), float(mb.group(2)), float(mb.group(3))
    if abs(tb - ba) > TOL_ANCHOR:
        fail(f"taper ends at Y {tb} but the block starts at Y {ba}")
    want = [(x0, y0), (x1, y0), (x1, ta), (x0, ta), (bw, ba), (-bw, ba), (bw, bb), (-bw, bb)]
    (sx0, sx1), (sy0, sy1) = sl["X"], sl["Y"]
    want += [(sx0, sy0), (sx1, sy0), (sx0, sy1), (sx1, sy1)]
    polys = to_manifold(meshes["frame.table"]).slice(835.0).to_polygons()
    got = np.vstack([corners_only(np.asarray(p, dtype=float)) for p in polys]) if polys else np.zeros((0, 2))
    for w in want:
        if got.size == 0 or np.min(np.hypot(got[:, 0] - w[0], got[:, 1] - w[1])) > TOL_BODY:
            fail(f"table section at Z 835 has no corner at {w}")
    for g in got:
        if min(np.hypot(g[0] - w[0], g[1] - w[1]) for w in want) > TOL_BODY:
            fail(f"table section at Z 835 has a corner {np.round(g, 1).tolist()} that no row gives")


def check_plate_sections(plates, meshes):
    """Each "plate corners" polygon = the corners of its node's section at the plate's mid Z, and nothing else."""
    for bid, (want, z0, z1) in plates.items():
        zm = (z0 + z1) / 2.0
        polys = to_manifold(meshes["frame." + bid]).slice(zm).to_polygons()
        got = np.vstack([corners_only(np.asarray(p, dtype=float)) for p in polys]) if polys else np.zeros((0, 2))
        for w in want:
            if got.size == 0 or np.min(np.hypot(got[:, 0] - w[0], got[:, 1] - w[1])) > TOL_BODY:
                fail(f"{bid} section at Z {zm} has no corner at {w}")
        for g in got:
            if min(np.hypot(g[0] - w[0], g[1] - w[1]) for w in want) > TOL_BODY:
                fail(f"{bid} section at Z {zm} has a corner {np.round(g, 1).tolist()} that its plate corners do not give")


# ---------------------------------------------------------------- 2. derived checks
def check_derived(text, meshes, mans):
    s = re.sub(r"\([^)]*\)", " ", norm(section(text, "Derived checks")))
    allb = np.array([m.bounds for m in meshes.values()])
    lo, hi = allb[:, 0, :].min(axis=0), allb[:, 1, :].max(axis=0)
    m = re.search(rf"Bounding box of all frame bodies:\s*X ({NUM})…({NUM}),\s*Y ({NUM})…({NUM}),\s*Z ({NUM})…({NUM})", s)
    if not m:
        fail("derived: bounding-box line not found")
    else:
        v = [float(g) for g in m.groups()]
        if np.any(np.abs(lo - v[0::2]) > TOL_BODY) or np.any(np.abs(hi - v[1::2]) > TOL_BODY):
            fail(f"derived bbox {v}, glb {lo.round(1).tolist()}..{hi.round(1).tolist()}")
    m = re.search(rf"Plan envelope[^:]*:\s*X ({NUM})…({NUM})\s*,\s*Y ({NUM})…({NUM})", s)
    if not m:
        fail("derived: plan-envelope line not found")
    else:
        ex0, ex1, ey0, ey1 = (float(g) for g in m.groups())
        if not (lo[0] >= ex0 and hi[0] <= ex1 and lo[1] >= ey0 and hi[1] <= ey1):
            fail(f"plan envelope X {ex0}…{ex1}, Y {ey0}…{ey1}; glb X {lo[0]}…{hi[0]}, Y {lo[1]}…{hi[1]}")
    names = {"right foot": "foot_right", "left foot": "foot_left", "rear ring": "foot_rear"}
    areas = {n: mans[n].slice(1.0).area() / 100.0 for n in mans}
    on_floor = {n.split(".", 1)[1] for n, a in areas.items() if a > 0}
    printed = dict(re.findall(rf"(right foot|left foot|rear ring)\s+({NUM})\s*cm²", s))
    if set(printed) != set(names):
        fail("derived: floor-area line not found or incomplete")
    for k, v in printed.items():
        got = areas.get("frame." + names[k], 0.0)
        if abs(got - float(v)) > 0.01 * float(v) + 0.2:
            fail(f"floor area {k}: spec {v} cm2, glb {got:.2f} cm2")
    if on_floor != set(names.values()):
        fail(f"bodies on the floor at Z 1: {sorted(on_floor)}")
    m = re.search(rf"Table top Z ({NUM}); cutting stick top Z ({NUM}) at Y ({NUM}); table width ({NUM}) at "
                  rf"X ({NUM})…({NUM}); table length ({NUM})", s)
    if not m:
        fail("derived: table line not found")
    else:
        tt, st, sy, tw, tx0, tx1, tl = (float(g) for g in m.groups())
        tb, sb = meshes["frame.table"].bounds, meshes["frame.cutting_stick"].bounds
        for what, a, b in (("table top", tb[1][2], tt), ("stick top", sb[1][2], st),
                           ("stick centre Y", (sb[0][1] + sb[1][1]) / 2, sy), ("table width", tb[1][0] - tb[0][0], tw),
                           ("table X0", tb[0][0], tx0), ("table X1", tb[1][0], tx1), ("table length", tb[1][1] - tb[0][1], tl)):
            if abs(a - b) > TOL_BODY:
                fail(f"derived {what}: spec {b}, glb {round(float(a), 2)}")
    if "watertight" in s:
        for n, tm in meshes.items():
            if not (tm.is_watertight and tm.is_volume):
                fail(f"{n} is not a watertight volume")
    else:
        fail("derived: watertight line not found")
    if "do not interpenetrate" in s:
        ns = sorted(mans)
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                v = (mans[ns[i]] ^ mans[ns[j]]).volume()
                if v > 1.0:
                    fail(f"{ns[i]} and {ns[j]} overlap by {v:.1f} mm3")
    else:
        fail("derived: interpenetration line not found")
    m = re.search(r"Keep-out:\s*no frame body enters\s+([a-z]\w*(?:\.\w+)+)", s)
    if not m:
        fail("derived: keep-out line not found")
        return
    kname = m.group(1)
    mb = re.search(rf"(?<![\w.]){re.escape(kname)}\s+box\s+X\s+({NUM})…({NUM}),\s*Y\s+({NUM})…({NUM}),"
                   rf"\s*Z\s+({NUM})…({NUM})", norm(section(text, "Anchors")))
    if not mb:
        fail(f"derived: keep-out {kname} has no box in the Anchors section")
        return
    v = [float(g) for g in mb.groups()]
    kb = mf.Manifold.cube([v[1] - v[0], v[3] - v[2], v[5] - v[4]]).translate([v[0], v[2], v[4]])
    for n, mm in mans.items():
        iv = (mm ^ kb).volume()
        if iv > 1.0:
            fail(f"{n} enters keep-out {kname} by {iv:.1f} mm3")


# ---------------------------------------------------------------- 3. anchors
def check_anchors(text):
    anc = json.loads((R / "out" / "frame_anchors.json").read_text(encoding="utf-8"))["anchors"]
    block = norm(section(text, "Anchors"))
    seen, pts, boxes = [], {}, {}
    for cells in table_rows(block):
        nums = re.findall(NUM, cells[1]) if len(cells) > 1 else []
        if len(nums) == 3 and re.fullmatch(r"[a-z]\w*(?:\.\w+)+", cells[0]):
            pts[cells[0]] = [float(v) for v in nums]
            seen.append(cells[0])
    for m in re.finditer(rf"(?<![\w.])([a-z]\w*(?:\.\w+)*)\s+\(\s*({NUM})\s*,\s*({NUM})\s*,\s*({NUM})\s*\)", block):
        pts[m.group(1)] = [float(m.group(k)) for k in (2, 3, 4)]
        seen.append(m.group(1))
    for m in re.finditer(rf"(?<![\w.])([a-z]\w*(?:\.\w+)+)\s+box\s+X\s+({NUM})…({NUM}),\s*Y\s+({NUM})…({NUM}),"
                         rf"\s*Z\s+({NUM})…({NUM})", block):
        v = [float(m.group(k)) for k in range(2, 8)]
        boxes[m.group(1)] = (v[0::2], v[1::2])
        seen.append(m.group(1))
    for n in sorted({n for n in seen if seen.count(n) > 1}):
        fail(f"anchor {n} is named {seen.count(n)} times in the spec")
    for n in sorted(set(seen) - set(anc)):
        fail(f"anchor {n} is in the spec but not in frame_anchors.json")
    for n in sorted(set(anc) - set(seen)):
        fail(f"anchor {n} is in frame_anchors.json but has no value in the spec")
    for n, v in pts.items():
        got = anc.get(n, {}).get("xyz")
        if got is not None and any(abs(g - e) > TOL_ANCHOR for g, e in zip(got, v)):
            fail(f"anchor {n}: spec {v}, json {got}")
    for n, (lo, hi) in boxes.items():
        a = anc.get(n, {})
        if n in anc and ("min" not in a or any(abs(g - e) > TOL_ANCHOR for g, e in zip(a["min"] + a["max"], lo + hi))):
            fail(f"anchor box {n}: spec {lo}..{hi}, json {a.get('min')}..{a.get('max')}")
    m = re.search(rf"table\.rear_outline\s+\([^)]*\)\s+with the plan polygon\s+((?:{PAIR}\s*)+)", block)
    poly = [[float(a), float(b)] for a, b in re.findall(PAIR, m.group(1))] if m else None
    gp = anc.get("table.rear_outline", {}).get("polygon_xy")
    if poly is None or gp is None or len(poly) != len(gp) or \
            any(abs(a - b) > TOL_ANCHOR for p, q in zip(poly, gp) for a, b in zip(p, q)):
        fail(f"table.rear_outline polygon: spec {poly}, json {gp}")
    return len(seen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(R / "spec" / "frame.md"))
    spec = Path(ap.parse_args().spec)
    text = spec.read_text(encoding="utf-8")
    meshes = load_glb()
    mans = {n: to_manifold(m) for n, m in meshes.items()}
    for n, m in mans.items():
        if "NoError" not in str(m.status()):
            fail(f"{n}: not a manifold when read back from frame.glb ({m.status()})")
    done, sub, plates = check_components(text, meshes)
    check_table_section(done, sub, meshes)
    check_plate_sections(plates, meshes)
    check_derived(text, meshes, mans)
    n_anchors = check_anchors(text)
    for line in bad:
        print("MISMATCH", line)
    print(f"spec {spec.name} | bodies read {len(done)} of {len(meshes)} glb nodes | plate polygons read "
          f"{len(plates)} | anchors read {n_anchors} | "
          + ("PASS" if not bad else f"FAIL ({len(bad)})"))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
