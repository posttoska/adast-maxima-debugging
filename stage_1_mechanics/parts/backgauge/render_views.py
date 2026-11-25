"""Views of the backgauge (thread 4) for a visual check: flat-shaded orthographic panels, frame bodies near the
backgauge as grey edges. Panels: top at rest (rear on top), side from +X at rest and at the front end (face Y 25),
front from the operator at rest. Colours: moving group orange, spindle line blue, devices red, fixed grey-green.
Run (python without -I, PIL is in the user site):  python stage_1_mechanics/parts/backgauge/render_views.py
-> parts/backgauge/renders/backgauge_views.png
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
sys.path.insert(0, str(HERE))
import backgauge as B  # noqa: E402

DEVICES = {"S24", "S27", "M2", "encoder_BR40"}
COL = {"moving": (235, 140, 40), "spindle": (70, 130, 220), "handwheel": (170, 90, 200), "fixed": (120, 160, 130)}
VIEWS = {  # name: (screen x of p, screen y of p, depth: larger = nearer)
    "top": (lambda p: p[:, 0], lambda p: -p[:, 1], lambda p: p[:, 2]),
    "side": (lambda p: p[:, 1], lambda p: -p[:, 2], lambda p: p[:, 0]),
    "front": (lambda p: p[:, 0], lambda p: -p[:, 2], lambda p: -p[:, 1]),
}
LIGHT = np.array([0.4, -0.5, 0.75])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def panel(items, frame, view, title, size=(900, 620)):
    fx, fy, fd = VIEWS[view]
    img = Image.new("RGB", size, (255, 255, 255))
    dr = ImageDraw.Draw(img)
    pts = np.vstack([tm.vertices for tm, _ in items])
    sx, sy = fx(pts), fy(pts)
    lo, hi = np.array([sx.min(), sy.min()]), np.array([sx.max(), sy.max()])
    s = min((size[0] - 80) / (hi[0] - lo[0]), (size[1] - 90) / (hi[1] - lo[1]))

    def P(p):
        return np.stack([40 + (fx(p) - lo[0]) * s, 60 + (fy(p) - lo[1]) * s], axis=1)
    for tm in frame:                                 # frame context: grey triangle edges
        for tri in tm.vertices[tm.faces]:
            q = P(tri)
            dr.line([tuple(q[0]), tuple(q[1]), tuple(q[2]), tuple(q[0])], fill=(200, 200, 200), width=1)
    tris, cols = [], []
    for tm, col in items:
        n = tm.face_normals
        shade = 0.35 + 0.65 * np.abs(n @ LIGHT)
        for tri, sh in zip(tm.vertices[tm.faces], shade):
            tris.append(tri)
            cols.append(tuple(int(c * sh) for c in col))
    tris = np.array(tris)
    depth = np.array([fd(t).mean() for t in tris])
    for i in np.argsort(depth):
        q = P(tris[i])
        dr.polygon([tuple(v) for v in q], fill=cols[i])
    dr.text((40, 12), title, fill=(0, 0, 0))
    bar = 500 * s                                    # 500 mm scale bar
    dr.line([(40, size[1] - 20), (40 + bar, size[1] - 20)], fill=(0, 0, 0), width=3)
    dr.text((45 + bar, size[1] - 30), "500 mm", fill=(0, 0, 0))
    return img


def main():
    built = B.build(B.SPEC)
    frame_all = {}
    sc = trimesh.load(R / "out" / "frame.glb", force="scene")
    for n in sc.graph.nodes_geometry:
        T, g = sc.graph[n]
        tm = sc.geometry[g].copy()
        tm.apply_transform(T)
        frame_all[n] = tm
    allb = np.array([[-650, -900, 400], [650, 1950, 1050]])

    def items_at(d):
        out = []
        for bid, comp, group, m in built:
            tm = B.to_trimesh(m)
            if group == "moving" and d:
                tm.apply_translation([0, -d, 0])
            out.append((tm, (220, 40, 40) if bid in DEVICES else COL[group]))
        return out

    def near(view_keep):
        return [tm for n, tm in frame_all.items() if np.all(tm.bounds[0] < allb[1]) and np.all(allb[0] < tm.bounds[1])
                and n.split(".", 1)[1] in view_keep]
    keep_side = {"table", "base_front", "rear_stand", "foot_rear", "cutting_stick"}
    keep_top = {"table", "base_front", "rear_stand"}
    keep_front = {"table", "base_front"}
    rest, front = items_at(0), items_at(1125)
    p1 = panel(rest, near(keep_top), "top", "TOP at rest (face Y 1150), rear on top; frame table, base_front, rear_stand grey")
    p2 = panel(rest, near(keep_side), "side", "SIDE from +X at rest (face Y 1150); front (Y-) on the left")
    p3 = panel(front, near(keep_side), "side", "SIDE from +X at the front end (face Y 25)")
    p4 = panel(rest, near(keep_front), "front", "FRONT from the operator (from Y-) at rest")
    W, H = p1.size
    img = Image.new("RGB", (2 * W, 2 * H), (255, 255, 255))
    for k, p in enumerate((p1, p2, p3, p4)):
        img.paste(p, ((k % 2) * W, (k // 2) * H))
    outd = HERE / "renders"
    outd.mkdir(exist_ok=True)
    img.save(outd / "backgauge_views.png")
    small = img.resize((1300, int(1300 * img.size[1] / img.size[0])))
    small.save(outd / "backgauge_views_small.png")
    print("render:", outd / "backgauge_views.png", img.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
