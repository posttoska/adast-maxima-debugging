"""Clamp part of the Adast Maxima MS 115 PS (thread 3, episode 1).

Builds every body from the model table of spec/clamp.md and the anchors from its anchors table;
nothing else holds a number. Writes out/clamp.glb, out/clamp.stl and out/clamp_anchors.json.
Millimetres, machine coordinates (X along the knife, + right; Y + from the cutting line to the rear;
Z up, Z 0 floor), at rest = clamp up, knife up.
Run:  python stage_1_mechanics/parts/clamp/clamp.py [--spec <md>] [--out <dir>]   (paths from __file__)
"""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

R = Path(__file__).resolve().parents[2]          # stage_1_mechanics
SPEC = R / "spec" / "clamp.md"
SEG = 64                                         # circle segments, divisible by 4: exact extents


def table(text, start, end):
    """Rows of the markdown table between two HTML comment markers (header dropped)."""
    block = text.split(start, 1)[1].split(end, 1)[0]
    rows = []
    for line in block.strip().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    return rows[1:]


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


def cyl(ax, c, d, s):
    """Cylinder of diameter d along axis ax from s[0] to s[1]; c = the two other coordinates in x, y, z order."""
    m = mf.Manifold.cylinder(s[1] - s[0], d / 2.0, d / 2.0, SEG)    # along +Z from 0
    if ax == "z":
        return m.translate([c[0], c[1], s[0]])
    if ax == "y":
        return m.rotate([-90, 0, 0]).translate([c[0], s[0], c[1]])  # Z -> +Y
    return m.rotate([0, 90, 0]).translate([s[0], c[0], c[1]])       # Z -> +X


def one_solid(geometry):
    kind, *rest = geometry.split()
    kv = kv_of(rest)
    if kind == "box":
        return box(rng(kv["x"]), rng(kv["y"]), rng(kv["z"]))
    if kind in ("cyl", "tube"):
        m = cyl(kv["ax"], vec(kv["c"]), float(kv["d"]), rng(kv["s"]))
        if kind == "tube":
            m = m - cyl(kv["ax"], vec(kv["c"]), float(kv["di"]), rng(kv["s"]))
        return m
    if kind == "fingers":
        x0, p, t = float(kv["x0"]), float(kv["pitch"]), float(kv["t"])
        parts = [box((x0 + k * p - t / 2, x0 + k * p + t / 2), rng(kv["y"]), rng(kv["z"]))
                 for k in range(int(kv["n"]))]
        return mf.Manifold.batch_boolean(parts, mf.OpType.Add)
    raise SystemExit("unknown geometry: " + geometry)


def build_body(geometry):
    parts = [one_solid(g.strip()) for g in geometry.split(" + ")]
    return parts[0] if len(parts) == 1 else mf.Manifold.batch_boolean(parts, mf.OpType.Add)


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


CUT_MARK = {"assembly": "frame passage, cut at assembly (DECISION 2)"}   # meta orc DECISION 2, 2026-11-25
BOXES = ("space", "envelope", "zone", "passage")


def parse_motion(cell):
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
    bk = next((w for w in toks[1:] if w in BOXES), None)
    bx = [list(rng(kv[a])) for a in "xyz"] if all(a in kv for a in "xyz") else None
    extras = {k: num(v) for k, v in kv.items() if k not in ("axis", "pivot", "range", "at", "of", "x", "y", "z")}
    return m, bx, bk, extras


def anchors_json(rows):
    """space/envelope -> min/max (envelope = swept keep-out box of parts not modelled as solids);
    zone = interface box, no claim; passage = box through a frame body (cut_at=assembly: DECISION 2)."""
    out = {}
    for name, xyz, cls, err, src, motion in (r[:6] for r in rows):
        m, bx, bk, extras = parse_motion(motion)
        a = {"xyz": vec(xyz), "class": cls, "error_mm": parse_error(err), "source": src, "motion": m}
        if bx and bk in ("space", "envelope"):
            a["min"] = [s[0] for s in bx]
            a["max"] = [s[1] for s in bx]
            a["box_kind"] = bk
        elif bx and bk == "zone":
            a["zone"] = bx
        elif bx and bk == "passage":
            a["passage"] = bx
            if "cut_at" in extras:
                a["cut_at"] = str(extras.pop("cut_at"))
                a["cut_from"] = str(extras.pop("cut_from", ""))
                a["mark"] = CUT_MARK.get(a["cut_at"], "frame passage, cut at " + a["cut_at"])
        for k, v in extras.items():
            m[k] = v
        out[name] = a
    return out


GROUPS = {"beam": "translate along (0, 0, -1) by 0..130 (clamp down)",
          "piston": "translate along (0, 0, +1) by the beam's travel (ratio 1:1, E)",
          "gear": "turns about (0, -1, 0) through X 0, Z 1380, so its -X side, where the rack meshes, moves down "
                  "with the beam; round, the solid does not change",
          "pedal": "turns about (1, 0, 0) through (0, -571, 70) by 0..15 deg",
          "fixed": "no motion"}


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
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else R / "out"
    spec = Path(argv[argv.index("--spec") + 1]) if "--spec" in argv else SPEC
    _, anchor_rows, _ = read_spec(spec)
    scene = trimesh.Scene()
    meshes, info = [], {}
    for bid, comp, group, m in build(spec):
        tm = to_trimesh(m)
        scene.add_geometry(tm, node_name="clamp." + bid, geom_name="clamp." + bid)
        meshes.append(tm)
        info["clamp." + bid] = {"component": comp, "group": group, "bounds": np.round(tm.bounds, 3).tolist(),
                                "volume_mm3": round(float(m.volume()), 1)}
        print(f"clamp.{bid:16s} {group:7s} bounds {np.round(tm.bounds, 1).tolist()}")
    scene.metadata["units"] = "mm, machine coordinates, Z up, at rest (clamp up)"
    out.mkdir(parents=True, exist_ok=True)
    (out / "clamp.glb").write_bytes(scene.export(file_type="glb"))
    allm = trimesh.util.concatenate(meshes)
    allm.export(out / "clamp.stl")
    doc = {"meta": {"part": "clamp", "units": "mm",
                    "coordinates": "X along knife +right, Y +rear from cutting line, Z up, Z0 floor; glTF readers: "
                                   "scale 0.001 and turn -90 deg about X",
                    "spec": "spec/clamp.md", "script": "parts/clamp/clamp.py",
                    "state": "at rest: clamp up (lowest surface Z 1015), knife up", "groups": GROUPS,
                    "bodies": info},
           "anchors": anchors_json(anchor_rows)}
    (out / "clamp_anchors.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("part bounds", np.round(allm.bounds, 2).tolist(), "bodies", len(meshes), "anchors", len(doc["anchors"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
