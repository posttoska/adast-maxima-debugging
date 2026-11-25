"""Orthographic top / front / right-side renders of out/frame.glb (PIL only, painter's algorithm).
Run: python render_views.py  -> parts/frame/renders/frame_top.png, frame_front.png, frame_side.png
Top view: rear at the top, as the plan Fig. 4.2.2. Front view: seen by the operator (from -Y).
Side view: seen from the right (+X), front on the left. Red: Y 0 cutting line; blue: line A; green: bolt axes.
"""
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
GLB = HERE.parent.parent / "out" / "frame.glb"
OUTD = HERE / "renders"
Y_A = 6.0

VIEWS = {  # name: (screen-x axis, screen-y axis (up), depth axis, depth sign: larger value = nearer)
    "top": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    "front": ((1, 0, 0), (0, 0, 1), (0, -1, 0)),
    "side": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
}


def render(scene, name, px_per_mm=0.42, margin=40):
    ax, ay, ad = (np.array(v, float) for v in VIEWS[name])
    tris, cols, depth = [], [], []
    light = np.array([0.3, -0.5, 0.8]); light /= np.linalg.norm(light)
    for node in scene.graph.nodes_geometry:
        T, gname = scene.graph[node]
        m = scene.geometry[gname].copy(); m.apply_transform(T)
        base = np.array(m.visual.material.baseColorFactor[:3], float)
        if base.max() > 1.0: base = base / 255.0
        v = m.vertices[m.faces]                       # (n, 3, 3)
        n = m.face_normals
        shade = 0.45 + 0.55 * np.abs(n @ light)
        for k in range(len(v)):
            tris.append(v[k]); cols.append(tuple(int(255 * c * shade[k]) for c in base))
            depth.append(float((v[k] @ ad).max()))
    allv = np.concatenate(tris)
    sx, sy = allv @ ax, allv @ ay
    x0, x1, y0, y1 = sx.min(), sx.max(), sy.min(), sy.max()
    W = int((x1 - x0) * px_per_mm) + 2 * margin; H = int((y1 - y0) * px_per_mm) + 2 * margin
    img = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)

    def P(p):
        return (margin + (p @ ax - x0) * px_per_mm, H - margin - (p @ ay - y0) * px_per_mm)

    for k in np.argsort(depth):
        d.polygon([P(p) for p in tris[k]], fill=cols[k], outline=(60, 60, 60))
    if name in ("top", "side"):
        for yv, c in ((0.0, (220, 0, 0)), (Y_A, (0, 0, 220))):
            if name == "top":
                d.line([P(np.array([x0 - 50, yv, 0])), P(np.array([x1 + 50, yv, 0]))], fill=c, width=1)
            else:
                d.line([P(np.array([0, yv, y0])), P(np.array([0, yv, y1]))], fill=c, width=1)
    if name in ("top", "front"):
        for xv in (-790.0, 932.0):
            a = np.array([xv, -800, 0]) if name == "top" else np.array([xv, 0, 0])
            b = np.array([xv, 2000, 0]) if name == "top" else np.array([xv, 0, 1600])
            d.line([P(a), P(b)], fill=(0, 150, 0), width=1)
    d.text((8, 8), f"frame {name}  ({px_per_mm} px/mm)", fill=(0, 0, 0))
    OUTD.mkdir(exist_ok=True)
    img.save(OUTD / f"frame_{name}.png")
    return OUTD / f"frame_{name}.png", img.size


if __name__ == "__main__":
    sc = trimesh.load(GLB)
    for v in VIEWS:
        print(*render(sc, v))
