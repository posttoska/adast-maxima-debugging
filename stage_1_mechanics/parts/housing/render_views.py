"""Views of the housing part (thread 5) for a visual check: flat-shaded orthographic panels drawn with Pillow.
Panels: front (from the operator, looking +Y), right end (from +X), left end (from -X), top (plan, rear on top).
Housing bodies coloured (cabinet blue-grey, console dark, covers orange, panels green); every other part's body light grey.
Run: python stage_1_mechanics/parts/housing/render_views.py -> parts/housing/renders/housing_views.png (+ _small.png)
"""
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "out"
W, H = 760, 520
COL = {"cabinet": (90, 120, 160), "console": (60, 60, 70), "instrument_panel": (200, 60, 60), "cover_11": (230, 120, 30),
       "right_front_cover": (230, 120, 30), "belt_pulley_cover": (230, 120, 30)}
PANEL_COL = (80, 160, 90)
# view: screen-x = sx_sign * axis sx, screen-y = axis sy (up), depth key (larger = drawn later = nearer)
VIEWS = {"front (from the operator, +Y away)": (0, 1, 2, 1, lambda c: -c[:, 1]),
         "right end (from +X, front on the left)": (1, 1, 2, 1, lambda c: c[:, 0]),
         "left end (from -X, front on the right)": (1, -1, 2, 1, lambda c: -c[:, 0]),
         "top (plan, rear on top)": (0, 1, 1, 1, lambda c: c[:, 2])}
LIM = {0: (-1500, 1650), 1: (-1000, 1950), 2: (-30, 1700)}
LIGHT = np.array([0.35, -0.55, 0.75]) / np.linalg.norm([0.35, -0.55, 0.75])


def load():
    tris = []
    for f in sorted(OUT.glob("*.glb")):
        if f.stem == "assembly":
            continue
        s = trimesh.load(f, force="scene")
        for node in s.graph.nodes_geometry:
            tf, g = s.graph[node]
            tm = s.geometry[g].copy()
            tm.apply_transform(tf)
            if node.startswith("housing."):
                n = node.split(".", 1)[1]
                col = COL.get(n, PANEL_COL)
            else:
                col = (205, 205, 205)
            tris.append((tm.triangles, tm.face_normals, np.array(col, dtype=float)))
    return tris


def panel(tris, title, view):
    ax, sgn, ay, _, depth = view
    img = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(img)
    (x0, x1) = LIM[ax] if sgn > 0 else (-LIM[ax][1], -LIM[ax][0])
    (y0, y1) = LIM[ay]
    k = min((W - 20) / (x1 - x0), (H - 40) / (y1 - y0))
    allt, alln, allc = [], [], []
    for t, n, c in tris:
        allt.append(t)
        alln.append(n)
        allc.append(np.repeat(c[None, :], len(t), axis=0))
    T, N, Cc = np.concatenate(allt), np.concatenate(alln), np.concatenate(allc)
    order = np.argsort(depth(T.mean(axis=1)))
    shade = 0.45 + 0.55 * np.abs(N @ LIGHT)
    for i in order:
        p = T[i]
        xs = 10 + (sgn * p[:, ax] - x0) * k
        ys = H - 10 - (p[:, ay] - y0) * k
        col = tuple(int(v) for v in np.clip(Cc[i] * shade[i], 0, 255))
        dr.polygon(list(zip(xs.tolist(), ys.tolist())), fill=col)
    dr.text((10, 8), title + f"   ({1 / k:.1f} mm/px)", fill=(0, 0, 0))
    return img


def main():
    tris = load()
    pans = [panel(tris, t, v) for t, v in VIEWS.items()]
    img = Image.new("RGB", (W * 2, H * 2), (255, 255, 255))
    for i, p in enumerate(pans):
        img.paste(p, ((i % 2) * W, (i // 2) * H))
    (HERE / "renders").mkdir(exist_ok=True)
    img.save(HERE / "renders" / "housing_views.png")
    img.resize((W * 2 * 3 // 4, H * 2 * 3 // 4)).save(HERE / "renders" / "housing_views_small.png")
    print("wrote", HERE / "renders" / "housing_views.png")


if __name__ == "__main__":
    main()
