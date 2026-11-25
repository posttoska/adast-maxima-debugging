"""Backgauge part of the Adast Maxima MS 115 PS (thread 4, episode 1).

Builds every body from the model table of spec/backgauge.md and the anchors from its anchors
table; nothing else holds a number. Writes out/backgauge.glb, out/backgauge.stl and
out/backgauge_anchors.json. Millimetres, machine coordinates (X along the knife, + right;
Y + from the cutting line to the rear; Z up, Z 0 floor), at rest = pusher face at Y 1150.
Run:  python stage_1_mechanics/parts/backgauge/backgauge.py   (paths come from __file__)
"""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

R = Path(__file__).resolve().parents[2]          # stage_1_mechanics
SPEC = R / "spec" / "backgauge.md"
SEG = 64                                         # circle segments, divisible by 4: exact extents


def table(text, start, end):
    """Rows of the markdown table between two HTML comment markers, as lists of cells."""
    block = text.split(start, 1)[1].split(end, 1)[0]
    rows = []
    for line in block.strip().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    return rows[1:]                              # drop the header row


def rng(s):
    a, b = s.replace("−", "-").split("..")
    return float(a), float(b)


def vec(s):
    return [float(v) for v in s.replace("−", "-").split(",")]


def kv_of(tokens):
    return dict(t.split("=", 1) for t in tokens if "=" in t)


def read_spec(path=SPEC):
    text = Path(path).read_text(encoding="utf-8")
    bodies = table(text, "<!-- MODEL TABLE START -->", "<!-- MODEL TABLE END -->")
    anchors = table(text, "<!-- ANCHORS START -->", "<!-- ANCHORS END -->")
    outer = {r[0]: (float(r[1]), float(r[2])) for r in table(text, "<!-- OUTER START -->", "<!-- OUTER END -->")}
    return bodies, anchors, outer


# ---------------------------------------------------------------- solids
def box(x, y, z):
    (x0, x1), (y0, y1), (z0, z1) = x, y, z
    return mf.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_y(c, d, s0, s1):
    """Cylinder along +Y from s0 to s1; c = (x, z) of the axis."""
    m = mf.Manifold.cylinder(s1 - s0, d / 2.0, d / 2.0, SEG)        # along +Z from 0
    return m.rotate([-90, 0, 0]).translate([c[0], s0, c[1]])        # Z -> +Y


def cyl_x(c, d, s0, s1):
    """Cylinder along +X from s0 to s1; c = (y, z) of the axis."""
    m = mf.Manifold.cylinder(s1 - s0, d / 2.0, d / 2.0, SEG)        # along +Z from 0
    return m.rotate([0, 90, 0]).translate([s0, c[0], c[1]])         # Z -> +X


def build_body(geometry):
    kind, *rest = geometry.split()
    kv = kv_of(rest)
    if kind == "box":
        return box(rng(kv["x"]), rng(kv["y"]), rng(kv["z"]))
    if kind == "fingers":                        # n plates w wide, first at x0, last ending at x1
        (x0, x1), n, w = rng(kv["x"]), int(kv["n"]), float(kv["w"])
        pitch = (x1 - x0 - w) / (n - 1)
        parts = [box((x0 + k * pitch, x0 + k * pitch + w), rng(kv["y"]), rng(kv["z"])) for k in range(n)]
        return mf.Manifold.batch_boolean(parts, mf.OpType.Add)
    if kind == "prism":                          # convex polygon in XY extruded over z
        z0, z1 = rng(kv["z"])
        pts = [vec(p) for p in kv["xy"].split(";")]
        return mf.Manifold.hull_points([[x, y, z] for x, y in pts for z in (z0, z1)])
    if kind == "cyl":
        s0, s1 = rng(kv["s"])
        return cyl_y(vec(kv["c"]), float(kv["d"]), s0, s1)
    if kind == "tube":
        s0, s1 = rng(kv["s"])
        c = vec(kv["c"])
        return cyl_y(c, float(kv["d"]), s0, s1) - cyl_y(c, float(kv["di"]), s0 - 1, s1 + 1)
    if kind == "cylx":                           # along X: c = y,z of the axis, s = x range; di makes it a tube
        s0, s1 = rng(kv["s"])
        c = vec(kv["c"])
        m = cyl_x(c, float(kv["d"]), s0, s1)
        if "di" in kv:
            m = m - cyl_x(c, float(kv["di"]), s0 - 1, s1 + 1)
        return m
    if kind == "diamond":                        # square turned 45 deg about Y: |x-cx|+|z-cz| <= r
        (cx, cz), r, (s0, s1) = vec(kv["c"]), float(kv["r"]), rng(kv["s"])
        pts = [[cx + dx, y, cz + dz] for dx, dz in ((r, 0), (0, r), (-r, 0), (0, -r)) for y in (s0, s1)]
        m = mf.Manifold.hull_points(pts)
        if "bore" in kv:
            m = m - cyl_y((cx, cz), float(kv["bore"]), s0 - 1, s1 + 1)
        return m
    if kind == "channel":                        # U open at the top: floor and two walls of sheet t
        (x0, x1), y, (z0, z1), t = rng(kv["x"]), rng(kv["y"]), rng(kv["z"]), float(kv["t"])
        return box((x0, x1), y, (z0, z1)) - box((x0 + t, x1 - t), (y[0] - 1, y[1] + 1), (z0 + t, z1 + 1))
    if kind == "boxbore":
        y0, y1 = rng(kv["y"])
        return box(rng(kv["x"]), (y0, y1), rng(kv["z"])) - cyl_y(vec(kv["c"]), float(kv["d"]), y0 - 1, y1 + 1)
    raise ValueError(f"unknown geometry kind {kind!r}")


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3].astype(np.float64),
                           np.asarray(mesh.tri_verts), process=True)


# ---------------------------------------------------------------- anchors
def num(s):
    try:
        return float(s)
    except ValueError:
        return s


def parse_error(cell):
    cell = cell.replace("−", "-")
    if "=" in cell:
        return {k: float(v) for k, v in (t.split("=") for t in cell.split(","))}
    return float(cell)


def parse_motion(cell):
    """'<kind> key=value ...; note' -> (motion dict, passage box or None, space box or None, extras)."""
    head, _, note = cell.replace("−", "-").partition(";")
    toks = head.split()
    kv = kv_of(toks[1:])
    m = {"kind": toks[0] if toks else "", "note": note.strip()}
    for k in ("axis", "pivot"):
        if k in kv:
            m[k] = vec(kv[k])
    if "range" in kv:
        m["range"] = list(rng(kv["range"]))
        m["unit"] = "deg" if m["kind"] == "rot" else "mm"
    if "at" in kv:
        m["at"] = float(kv["at"])
    if "of" in kv:
        m["of"] = kv["of"]
    box_ = [list(rng(kv[a])) for a in "xyz"] if all(a in kv for a in "xyz") else None
    words = toks[1:]
    boxkind = "space" if "space" in words else "zone" if "zone" in words else "passage"
    extras = {k: (list(rng(v)) if k.endswith("_range") else vec(v) if k.endswith("_axis") else num(v)) for k, v in kv.items()
              if k not in ("axis", "pivot", "range", "at", "of", "x", "y", "z")}
    return m, box_, boxkind, extras


CUT_MARK = {"assembly": "frame passage, cut at assembly (DECISION 2)"}   # meta orc DECISION 2, 2026-11-25


def anchors_json(rows):
    """passage = box through a frame body: with cut_at=assembly the assembly cuts it out of the body cut_from
    names (DECISION 2), else the frame must cut and name it; space (min/max, as the frame's cavity anchors) =
    room this part claims; zone = a box that describes an interface, no claim."""
    out = {}
    for name, xyz, cls, err, src, motion in (r[:6] for r in rows):
        m, box_, boxkind, extras = parse_motion(motion)
        a = {"xyz": vec(xyz), "class": cls, "error_mm": parse_error(err), "source": src, "motion": m}
        if box_ and boxkind == "passage":
            a["passage"] = box_
            if "bore_d" in extras:
                a["bore_d"] = float(extras.pop("bore_d"))
                a["axis"] = m.pop("axis", None) or [0.0, 1.0, 0.0]
            if "cut_at" in extras:
                a["cut_at"] = str(extras.pop("cut_at"))
                a["cut_from"] = str(extras.pop("cut_from", ""))
                a["mark"] = CUT_MARK.get(a["cut_at"], "frame passage, cut at " + a["cut_at"])
        elif box_ and boxkind == "space":
            a["min"] = [s[0] for s in box_]
            a["max"] = [s[1] for s in box_]
        elif box_:
            a["zone"] = box_
        for k, v in extras.items():
            m[k] = v
        out[name] = a
    return out


def build(spec=SPEC):
    """-> list of (body, component, group, manifold)."""
    bodies, _, _ = read_spec(spec)
    built = []
    for bid, comp, group, geometry in (r[:4] for r in bodies):
        m = build_body(geometry)
        if m.status() != mf.Error.NoError or m.is_empty():
            raise SystemExit(f"{bid}: manifold error {m.status()}")
        built.append((bid, comp, group, m))
    return built


def main(argv):
    out = R / "out"
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
    spec = SPEC
    if "--spec" in argv:
        spec = Path(argv[argv.index("--spec") + 1])
    _, anchor_rows, _ = read_spec(spec)
    scene = trimesh.Scene()
    meshes, info = [], {}
    for bid, comp, group, m in build(spec):
        tm = to_trimesh(m)
        scene.add_geometry(tm, node_name="backgauge." + bid, geom_name="backgauge." + bid)
        meshes.append(tm)
        info["backgauge." + bid] = {"component": comp, "group": group,
                                    "bounds": np.round(tm.bounds, 3).tolist(),
                                    "volume_mm3": round(float(m.volume()), 1)}
    scene.metadata["units"] = "mm, machine coordinates, Z up, at rest (pusher face at Y 1150)"
    out.mkdir(parents=True, exist_ok=True)
    (out / "backgauge.glb").write_bytes(scene.export(file_type="glb"))
    allm = trimesh.util.concatenate(meshes)
    allm.export(out / "backgauge.stl")
    doc = {"meta": {"part": "backgauge", "units": "mm",
                    "coordinates": "X along knife +right, Y +rear from cutting line, Z up, Z0 floor",
                    "spec": "spec/backgauge.md", "script": "parts/backgauge/backgauge.py",
                    "state": "at rest: pusher face at Y 1150 (rear end, S27 reference)",
                    "groups": {"moving": "translate together along -Y by d = 1150 - face Y, d 0..1125",
                               "spindle": "turn about X 0, Z 725 (axis 0,1,0), fixed in place",
                               "handwheel": "knob, shaft and gear turn about their axis X (Y -695, Z 710) "
                                            "and push in 10 along -X [E]",
                               "fixed": "no motion"},
                    "bodies": info},
           "anchors": anchors_json(anchor_rows)}
    (out / "backgauge_anchors.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                                                encoding="utf-8")
    b = np.round(allm.bounds, 2).tolist()
    print(f"backgauge: {len(meshes)} bodies, {len(doc['anchors'])} anchors, bounds {b} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
