"""Early cross-part check of the backgauge (thread 4) against the OTHER published parts (section 04 checks 8 and 9
for the backgauge's own pairs; the frame is covered by check_spec.py, the full check stays with the assembly).
  at rest : intersection volume of every backgauge body with every body of each other part's GLB
  sweep   : the moving group (bodies marked group "moving" in backgauge_anchors.json) translated along -Y by
            d = 0..1125 in 5 mm steps and d = 1125, against each other part at rest
A pair is intersected only when its (swept) bounding boxes touch; the counts of such pairs are printed.
Run:  python stage_1_mechanics/parts/backgauge/xcheck_parts.py [--out <R/out folder>]
Exit 0 = no overlap with any other part; 1 = overlaps listed.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as m3

HERE = Path(__file__).resolve().parent
SKIP = ("backgauge", "frame", "assembly")


def bodies(glb):
    sc = trimesh.load(glb, force="scene")
    res = {}
    for name in sc.graph.nodes_geometry:
        tf, gname = sc.graph[name]
        g = sc.geometry[gname].copy()
        g.apply_transform(tf)
        res[name] = g
    return res


def man(mesh):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                               tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))


def touch(lo, hi, olo, ohi):
    return not (np.any(hi < olo) or np.any(ohi < lo))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent.parent / "out"))
    out = Path(ap.parse_args().out)
    info = json.loads((out / "backgauge_anchors.json").read_text(encoding="utf-8"))["meta"]["bodies"]
    bg = bodies(out / "backgauge.glb")
    moving = {n: m for n, m in bg.items() if isinstance(info.get(n), dict) and info[n].get("group") == "moving"}
    others = [p for p in sorted(out.glob("*.glb")) if p.stem not in SKIP]
    D = sorted(set(np.arange(0.0, 1125.0, 5.0).tolist() + [1125.0]))
    print("backgauge bodies", len(bg), "| moving", len(moving), "| other parts", [p.stem for p in others])
    fails = 0
    for p in others:
        ob = bodies(p)
        cache = {}
        # at rest
        rest_pairs, rest_hits = 0, []
        for bn, bm in bg.items():
            for on, om in ob.items():
                if not touch(*bm.bounds, *om.bounds):
                    continue
                rest_pairs += 1
                cache.setdefault(on, man(om))
                v = (man(bm) ^ cache[on]).volume()
                if v > 0:
                    rest_hits.append((bn, on, v))
        # sweep of the moving group
        sw_pairs, sw_hits = 0, []
        for bn, bm in moving.items():
            lo, hi = bm.bounds.copy()
            lo[1] -= 1125.0
            mb = None
            for on, om in ob.items():
                if not touch(lo, hi, *om.bounds):
                    continue
                sw_pairs += 1
                cache.setdefault(on, man(om))
                mb = mb or man(bm)
                worst, wd = 0.0, None
                for d in D:
                    v = (mb.translate([0.0, -d, 0.0]) ^ cache[on]).volume()
                    if v > worst:
                        worst, wd = v, d
                if worst > 0:
                    sw_hits.append((bn, on, wd, worst))
        env = np.array([m.bounds for m in ob.values()])
        print(f"{p.stem}: {len(ob)} bodies, envelope min {env[:, 0].min(axis=0).round(0).tolist()} "
              f"max {env[:, 1].max(axis=0).round(0).tolist()}")
        print(f"  at rest: {rest_pairs} bbox-touching pairs, {len(rest_hits)} overlapping")
        for h in rest_hits:
            print(f"    OVERLAP {h[0]} x {h[1]}: {h[2]:.1f} mm3")
        print(f"  sweep d 0..1125 ({len(D)} steps): {sw_pairs} swept-bbox pairs, {len(sw_hits)} colliding")
        for h in sw_hits:
            print(f"    COLLIDE {h[0]} x {h[1]}: worst at d {h[2]} (face Y {1150 - h[2]}), {h[3]:.1f} mm3")
        fails += len(rest_hits) + len(sw_hits)
    print("RESULT", "PASS" if fails == 0 else "FAIL", fails)
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
