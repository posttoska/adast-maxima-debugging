"""Handwheel push-in check of the backgauge (thread 4, critic finding I).

The handwheel group (knob handwheel_disc, handwheel_shaft, handwheel_gear) turns about its axis X and pushes
in 10 mm along -X (spec/backgauge.md, conflict 9). This moves it at rest and pushed in by 2.5, 5, 7.5 and 10 mm
and intersects it with every body of the other published parts (out/*.glb except backgauge and assembly) and
with the backgauge's own other bodies (bracket, spindle, ...). Turning about its own axis changes no volume.
Run:  python stage_1_mechanics/parts/backgauge/handwheel_check.py [extra shifts in mm, e.g. -12 as a probe]
Expected: RESULT PASS, 0 overlaps at every step; a probe of -12 must give overlaps with the bracket.
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import backgauge as B  # noqa: E402

R = B.R


def to_mf(tm):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                               tri_verts=np.asarray(tm.faces, np.uint32)))


def scene_bodies(path):
    sc = trimesh.load(path, force="scene")
    out = {}
    for node in sc.graph.nodes_geometry:
        tf, gname = sc.graph[node]
        m = sc.geometry[gname].copy()
        m.apply_transform(tf)
        out[node] = m
    return out


def main(argv):
    bodies, _, _ = B.read_spec()
    hw = {r[0]: B.build_body(r[3]) for r in bodies if r[2] == "handwheel"}
    own = {"backgauge." + r[0]: B.build_body(r[3]) for r in bodies if r[2] != "handwheel"}
    others = {}
    for f in sorted((R / "out").glob("*.glb")):
        if f.stem in ("backgauge", "assembly"):
            continue
        for n, tm in scene_bodies(f).items():
            if len(tm.faces):
                others[f"{f.stem}:{n}"] = to_mf(tm)
    print(f"handwheel bodies {sorted(hw)}; other parts' bodies {len(others)} "
          f"({sorted({k.split(':')[0] for k in others})}); own other bodies {len(own)}")
    worst = 0.0
    for shift in (0.0, -2.5, -5.0, -7.5, -10.0) + tuple(float(a) for a in argv):
        hits = []
        for hn, hm in hw.items():
            m = hm.translate([shift, 0, 0])
            for on, om in list(others.items()) + list(own.items()):
                v = (m ^ om).volume()
                if v > 0.5:
                    hits.append((hn, on, round(v, 1)))
                    worst = max(worst, v)
        print(f"push-in {shift:+.1f} mm: {len(hits)} overlaps" + (f" {hits[:6]}" if hits else ""))
    ok = worst <= 0.5
    print("RESULT", "PASS" if ok else "FAIL", f"max overlap {worst:.1f} mm3")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
