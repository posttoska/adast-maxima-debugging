"""Knife part of the Adast Maxima MS 115 PS (thread 2, episode 1).

Builds every body from the component table of spec/knife.md (geometry column) and the
anchors from its anchors table; nothing else holds a number. Writes out/knife.glb,
out/knife.stl, out/knife_anchors.json. Millimetres, machine coordinates, Z up, at rest.
Run:  python stage_1_mechanics/parts/knife/knife.py   (paths come from __file__)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

R = Path(__file__).resolve().parents[2]          # stage_1_mechanics
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
    a, b = s.split("..")
    return float(a), float(b)


def vec(s):
    return [float(v) for v in s.split(",")]


def parse_geometry(g):
    kind, *rest = g.split()
    kv = dict(t.split("=", 1) for t in rest)
    return kind, kv


def cylinder(ax, c, d, s0, s1):
    """Cylinder along ax ('x','y','z'); c = the other two coordinates in x,y,z order."""
    m = mf.Manifold.cylinder(s1 - s0, d / 2.0, d / 2.0, SEG)        # along +Z from 0
    if ax == "x":
        m = m.rotate([0, 90, 0]).translate([s0, c[0], c[1]])          # Z -> +X
    elif ax == "y":
        m = m.rotate([-90, 0, 0]).translate([c[0], s0, c[1]])         # Z -> +Y
    else:
        m = m.translate([c[0], c[1], s0])
    return m


def rod(p1, p2, d):
    """Round bar between two points whose axis lies in a plane Y = const."""
    p1, p2 = np.array(p1), np.array(p2)
    a = p2 - p1
    length = float(np.linalg.norm(a))
    phi = math.degrees(math.atan2(a[0], a[2]))                        # rotation about Y: Z -> a
    m = mf.Manifold.cylinder(length, d / 2.0, d / 2.0, SEG).rotate([0, phi, 0])
    return m.translate(p1.tolist())


def circle_pts(ax, c, d, s):
    pts = []
    for k in range(SEG):
        t = 2 * math.pi * k / SEG
        u, v = c[0] + d / 2 * math.cos(t), c[1] + d / 2 * math.sin(t)
        pts.append([s, u, v] if ax == "x" else [u, s, v] if ax == "y" else [u, v, s])
    return pts


def build_body(geometry):
    kind, kv = parse_geometry(geometry)
    if kind in ("box", "shell", "knife", "holder"):
        (x0, x1), (y0, y1), (z0, z1) = rng(kv["x"]), rng(kv["y"]), rng(kv["z"])
    if kind == "box":
        return mf.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])
    if kind == "shell":
        t = float(kv["t"])
        outer = mf.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])
        inner = mf.Manifold.cube([x1 - x0 - 2 * t, y1 - y0 - 2 * t, z1 - z0 - 2 * t]).translate(
            [x0 + t, y0 + t, z0 + t])
        return outer - inner
    if kind == "knife":                          # edge on the +Y face at z0, bevel on the -Y face
        h = float(kv["bevel"])
        yz = [(y1, z0), (y1, z1), (y0, z1), (y0, z0 + h)]
        return mf.Manifold.hull_points([[x, y, z] for x in (x0, x1) for y, z in yz])
    if kind == "holder":                         # box with the upper +X corner chamfered
        c = float(kv["chamfer"])
        xz = [(x0, z0), (x1, z0), (x1, z1 - c), (x1 - c, z1), (x0, z1)]
        return mf.Manifold.hull_points([[x, y, z] for y in (y0, y1) for x, z in xz])
    if kind == "cyl":
        s0, s1 = rng(kv["s"])
        return cylinder(kv["ax"], vec(kv["c"]), float(kv["d"]), s0, s1)
    if kind == "rod":
        return rod(vec(kv["p1"]), vec(kv["p2"]), float(kv["d"]))
    if kind == "belt":
        s0, s1 = rng(kv["s"])
        pts = []
        for c, d in ((vec(kv["c1"]), float(kv["d1"])), (vec(kv["c2"]), float(kv["d2"]))):
            for s in (s0, s1):
                pts += circle_pts(kv["ax"], c, d, s)
        return mf.Manifold.hull_points(pts)
    raise ValueError(f"unknown geometry kind {kind!r}")


def to_trimesh(m):
    mesh = m.to_mesh()
    tm = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3].astype(np.float64),
                         np.asarray(mesh.tri_verts), process=True)
    return tm


def read_spec(spec_path):
    text = Path(spec_path).read_text(encoding="utf-8")
    bodies = table(text, "<!-- MODEL TABLE START -->", "<!-- MODEL TABLE END -->")
    anchors = table(text, "<!-- ANCHORS START -->", "<!-- ANCHORS END -->")
    kin = {r[0]: float(r[1]) for r in table(text, "<!-- KIN START -->", "<!-- KIN END -->")}
    return bodies, anchors, kin


def parse_motion(cell):
    """Motion cell '<kind> key=value ...; note' -> (motion dict, passage box or None).
    kind fixed | rot | trans | planar | state.  rot: axis (unit vector; + = right-hand turn about it),
    pivot, range in degrees.  trans: axis (unit vector), range in mm.  planar: normal, plane (offset
    along the normal), ends (two anchor names).  state: of (anchor), at (value in that anchor's range).
    A fixed joint may carry a passage box x=a..b y=c..d z=e..f: the space the other part must cut or name."""
    head, _, note = cell.replace("−", "-").partition(";")
    toks = head.split()
    kv = dict(t.split("=", 1) for t in toks[1:] if "=" in t)
    m = {"kind": toks[0] if toks else "", "note": note.strip()}
    for k in ("axis", "pivot", "normal"):
        if k in kv:
            m[k] = vec(kv[k])
    if "range" in kv:
        m["range"] = list(rng(kv["range"]))
        m["unit"] = "deg" if m["kind"] in ("rot", "planar") else "mm"
    for k in ("plane", "at"):
        if k in kv:
            m[k] = float(kv[k])
    if "ends" in kv:
        m["ends"] = kv["ends"].split(",")
    if "of" in kv:
        m["of"] = kv["of"]
    box = [list(rng(kv[a])) for a in "xyz"] if all(a in kv for a in "xyz") else None
    passage = box if box is not None and "space" not in toks[1:] else None
    return m, passage


def parse_space(cell):
    """A fixed anchor 'fixed space x=a..b y=c..d z=e..f; note' claims room inside another part's cavity
    that the other part must leave free (not a passage to cut) -> [[x0, x1], [y0, y1], [z0, z1]] or None."""
    toks = cell.replace("−", "-").partition(";")[0].split()
    kv = dict(t.split("=", 1) for t in toks[1:] if "=" in t)
    return [list(rng(kv[a])) for a in "xyz"] if "space" in toks[1:] and all(a in kv for a in "xyz") else None


def anchors_json(rows):
    out = {}
    for name, xyz, cls, err, src, motion in (r[:6] for r in rows):
        m, passage = parse_motion(motion)
        out[name] = {"xyz": vec(xyz), "class": cls, "error_mm": float(err), "source": src, "motion": m}
        if passage:
            out[name]["passage"] = passage
        space = parse_space(motion)
        if space:                                   # same keys as the frame's cavity anchors
            out[name]["min"] = [s[0] for s in space]
            out[name]["max"] = [s[1] for s in space]
    return out


def main(argv):
    spec = R / "spec" / "knife.md"
    out = R / "out"
    bodies, anchors, _ = read_spec(spec)
    scene = trimesh.Scene()
    meshes = []
    for row in bodies:
        bid, geometry = row[0], row[2]
        m = build_body(geometry)
        if m.status() != mf.Error.NoError or m.is_empty():
            raise SystemExit(f"{bid}: manifold error {m.status()}")
        tm = to_trimesh(m)
        scene.add_geometry(tm, node_name="knife." + bid, geom_name="knife." + bid)
        meshes.append(tm)
    scene.metadata["units"] = "mm, machine coordinates, Z up, at rest (knife up, crank at TDC)"
    out.mkdir(parents=True, exist_ok=True)
    (out / "knife.glb").write_bytes(scene.export(file_type="glb"))
    trimesh.util.concatenate(meshes).export(out / "knife.stl")
    doc = {"meta": {"part": "knife", "units": "mm",
                    "coordinates": "X along knife +right, Y +rear from cutting line, Z up, Z0 floor",
                    "spec": "spec/knife.md", "script": "parts/knife/knife.py",
                    "state": "at rest: knife up, crank at top dead centre"},
           "anchors": anchors_json(anchors)}
    (out / "knife_anchors.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                                            encoding="utf-8")
    print(f"knife: {len(meshes)} bodies, {len(doc['anchors'])} anchors -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
