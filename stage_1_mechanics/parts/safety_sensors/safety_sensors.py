"""Safety devices and sensors of the Adast Maxima MS 115 PS (thread 6, episode 1): one body per device.

Builds every body from the bodies table of spec/safety_sensors.md, placed on its host's device anchor,
which is read at run time from out/<host>_anchors.json (frame, knife, clamp, backgauge, housing): the spec
holds only the solid relative to that anchor, so a moved host anchor moves the body.  Nothing else holds
a number.  Writes out/safety_sensors.glb, out/safety_sensors.stl and out/safety_sensors_anchors.json.
Millimetres, machine coordinates (X along the knife, + right; Y + from the cutting line to the rear;
Z up, Z 0 floor), at rest = knife up, clamp up.  No device anchor is published again (check 10): each
body publishes one anchor body.<designation> at its actuation point.
Run:  python stage_1_mechanics/parts/safety_sensors/safety_sensors.py [--spec <md>] [--out <dir>]
      [--anchors-dir <dir with the hosts' *_anchors.json>]
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

import hosts

R = hosts.R
SPEC = R / "spec" / "safety_sensors.md"
SEG = 64                                         # circle segments, divisible by 4: exact extents
AX = {"x": 0, "y": 1, "z": 2}
DIR = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0), "+z": (0, 0, 1), "-z": (0, 0, -1)}


def table(text, start, end):
    """Rows (lists of stripped cells) of the markdown table between two marker comments."""
    body = text.split(start, 1)[1].split(end, 1)[0]
    rows = [ln.strip() for ln in body.splitlines() if ln.strip().startswith("|")]
    out = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
    return [r for r in out[2:]]                  # skip header and the --- line


def num(s):
    return float(s.replace("−", "-").replace(",", "."))


def rng(s):
    a, b = re.fullmatch(r"\s*(-?[\d.,]+)\.\.(-?[\d.,]+)\s*", s.replace("−", "-")).groups()
    return num(a), num(b)


def vec(s):
    return [num(v) for v in s.replace("−", "-").split(";")] if ";" in s else [num(v) for v in s.split(",")]


def kv_of(tokens):
    return dict(t.split("=", 1) for t in tokens if "=" in t)


def read_spec(path=SPEC):
    """-> list of row dicts from the bodies table."""
    text = Path(path).read_text(encoding="utf-8")
    rows = []
    for c in table(text, "<!-- BODIES START -->", "<!-- BODIES END -->"):
        rid, desig, anchor, solid, actuator, motion, pocket, cls, err, src = c[:10]
        rows.append({"id": rid, "designation": desig, "anchor": anchor, "solid": solid, "actuator": actuator,
                     "motion": motion, "excused": [] if pocket in ("-", "") else [p.strip() for p in pocket.split(",")],
                     "class": cls, "error": err, "source": src})
    return rows


def prim(tok, a):
    """One primitive 'box x=a..b y=c..d z=e..f' or 'cyl ax=y d=40 s=a..b [at=u,v]', relative to anchor point a."""
    words = tok.split()
    kv = kv_of(words[1:])
    if words[0] == "box":
        lo = [a[i] + rng(kv[k])[0] for i, k in enumerate("xyz")]
        hi = [a[i] + rng(kv[k])[1] for i, k in enumerate("xyz")]
        return mf.Manifold.cube([hi[i] - lo[i] for i in range(3)]).translate(lo)
    if words[0] == "cyl":
        ax, d = kv["ax"], num(kv["d"])
        s0, s1 = rng(kv["s"])
        u, v = vec(kv["at"]) if "at" in kv else (0.0, 0.0)
        m = mf.Manifold.cylinder(s1 - s0, d / 2.0, d / 2.0, SEG)            # along +Z from 0
        if ax == "z":
            return m.translate([a[0] + u, a[1] + v, a[2] + s0])
        if ax == "y":
            return m.rotate([-90, 0, 0]).translate([a[0] + u, a[1] + s0, a[2] + v])   # Z -> +Y
        return m.rotate([0, 90, 0]).translate([a[0] + s0, a[1] + u, a[2] + v])       # Z -> +X
    raise ValueError(f"unknown primitive {tok!r}")


def anchor_point(row, anchors):
    part, a = hosts.find_anchor(anchors, row["anchor"])
    return part, np.array(a["xyz"], dtype=float)


def build_row(row, anchors):
    _, a = anchor_point(row, anchors)
    parts = [prim(t.strip(), a) for t in row["solid"].split("+")]
    m = parts[0]
    for p in parts[1:]:
        m = m + p
    return m


def actuator(row, anchors):
    """-> (point, direction, target text) of the body's actuation point (offset from the host anchor)."""
    _, a = anchor_point(row, anchors)
    kv = kv_of(row["actuator"].split(";")[0].split())
    p = a + np.array(vec(kv["at"]))
    return p, DIR[kv["dir"]], row["actuator"].split(";", 1)[1].strip() if ";" in row["actuator"] else ""


def parse_motion(cell):
    head, _, note = cell.partition(";")
    toks = head.split()
    kv = kv_of(toks[1:])
    m = {"kind": toks[0], "note": note.strip()}
    if "axis" in kv:
        m["axis"] = vec(kv["axis"])
    if "range" in kv:
        m["range"] = list(rng(kv["range"]))
        m["unit"] = "mm"
    if "with" in kv:
        m["with"] = kv["with"]
    return m


def parse_error(cell):
    v = [num(x) for x in re.findall(r"-?[\d]+(?:[.,]\d+)?", cell.split("(")[0])][:3]
    return {"x": v[0], "y": v[1], "z": v[2]} if len(v) == 3 else v[0]


def build(spec=SPEC, anchors_dir=None):
    rows = read_spec(spec)
    anchors = hosts.load_anchors(anchors_dir)
    built = []
    for r in rows:
        m = build_row(r, anchors)
        if m.status() != mf.Error.NoError or m.is_empty():
            raise SystemExit(f"{r['id']}: manifold error {m.status()}")
        built.append((r, m))
    return built, anchors


def main(argv):
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else R / "out"
    spec = Path(argv[argv.index("--spec") + 1]) if "--spec" in argv else SPEC
    adir = Path(argv[argv.index("--anchors-dir") + 1]) if "--anchors-dir" in argv else None
    built, anchors = build(spec, adir)
    scene, meshes, info, anc = trimesh.Scene(), [], {}, {}
    groups = {"fixed": "no motion"}            # motion groups, written from the spec's motion cells
    for r, m in built:
        name = "safety_sensors." + r["id"]
        tm = hosts.to_trimesh(m)
        scene.add_geometry(tm, node_name=name, geom_name=name)
        meshes.append(tm)
        host, a = anchor_point(r, anchors)
        mot = parse_motion(r["motion"])
        if "with" in mot:
            kind = {"trans": "translate", "rot": "rotate"}.get(mot["kind"], mot["kind"])
            axis = ", ".join(f"{v:g}" for v in mot.get("axis", []))
            lo, hi = mot.get("range", [0, 0])
            groups[mot["with"]] = f"moves with {mot['with']}: {kind} along ({axis}) by {lo:g}..{hi:g}"
        info[name] = {"designation": r["designation"], "host_anchor": f"{r['anchor']} ({host})",
                      "group": mot.get("with", "fixed"), "bounds": np.round(tm.bounds, 3).tolist(),
                      "volume_mm3": round(float(m.volume()), 1), "excused_overlap_with": r["excused"]}
        p, d, target = actuator(r, anchors)
        anc["body." + r["id"]] = {"xyz": np.round(p, 3).tolist(), "class": r["class"],
                                  "error_mm": parse_error(r["error"]), "source": r["source"],
                                  "motion": mot, "host_anchor": r["anchor"], "host": host,
                                  "host_error_mm": hosts.find_anchor(anchors, r["anchor"])[1].get("error_mm"),
                                  "offset_from_host_anchor_mm": np.round(p - a, 3).tolist(),
                                  "faces": list(d), "target": target}
        print(f"{name:26s} on {r['anchor']:13s} bounds {np.round(tm.bounds, 1).tolist()}")
    scene.metadata["units"] = "mm, machine coordinates, Z up, at rest (knife up, clamp up)"
    out.mkdir(parents=True, exist_ok=True)
    (out / "safety_sensors.glb").write_bytes(scene.export(file_type="glb"))
    allm = trimesh.util.concatenate(meshes)
    allm.export(out / "safety_sensors.stl")
    doc = {"meta": {"part": "safety_sensors", "units": "mm",
                    "coordinates": "X along knife +right, Y +rear from cutting line, Z up, Z0 floor; glTF readers: "
                                   "scale 0.001 and turn -90 deg about X",
                    "spec": "spec/safety_sensors.md", "script": "parts/safety_sensors/safety_sensors.py",
                    "state": "at rest: knife up, clamp up",
                    "naming": "one anchor body.<designation> per body, at its actuation point; the device anchors "
                              "(button., sensor., switch., motor., valve. ...) stay published once, by the hosts",
                    "groups": groups,
                    "bodies": info},
           "anchors": anc}
    (out / "safety_sensors_anchors.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                                                     encoding="utf-8")
    print("part bounds", np.round(allm.bounds, 2).tolist(), "bodies", len(meshes), "anchors", len(anc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
