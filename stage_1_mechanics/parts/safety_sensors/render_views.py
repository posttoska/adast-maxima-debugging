"""Views of the safety_sensors part (thread 6) in context, for a visual check: flat-shaded orthographic
panels drawn with Pillow (painter's order; this part's bodies are drawn last, on top of the hosts, so that
they show where hosts would hide them).  This part's bodies red, labelled with their designation; the
five host parts light grey (housing covers left out in the close-ups, so that the inside shows).
Panels: whole machine from the front and from the right end; close-ups of the right drive side from +X
(S5, S19, S12-S14, SQ1/SQ2), of the lock area from the rear (-Y view of S12-S14, SQ1/SQ2), of the clamp
(S28, S30) from the right and of the rear table from above (M3, Y3).
Run: python stage_1_mechanics/parts/safety_sensors/render_views.py -> renders/safety_sensors_views.png (+ _small.png)
"""
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw
import json

# what each body reads or is pressed by (blue); '?' = actuation not known (DECISION 4, SS5)
TARGET = {"S30": "clamp.bar", "S28": "clamp.false_plate", "S5": "housing.belt_pulley_cover", "S12": "knife.cam_disc",
          "S13": "knife.cam_disc", "S14": "knife.cam_disc", "SQ1": "knife.y01_tail", "SQ2": "knife.y01_tail",
          "S19": "knife.clutch_y10"}
UNKNOWN = ("S12", "S13", "S14", "S19")

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "out"
W, H = 640, 480
LIGHT = np.array([0.35, -0.55, 0.75]) / np.linalg.norm([0.35, -0.55, 0.75])
# title, screen-x axis and sign, screen-y axis, depth key (larger = nearer), limits {axis: (lo, hi)}, hide housing
PANELS = [
    ("whole, from the front (operator)", (0, 1), 2, lambda c: -c[:, 1], {0: (-1500, 1650), 2: (-30, 1700)}, False),
    ("whole, right end (from +X)", (1, 1), 2, lambda c: c[:, 0], {1: (-1000, 1950), 2: (-30, 1700)}, False),
    ("right drive side from +X, covers off", (1, 1), 2, lambda c: c[:, 0], {1: (-250, 600), 2: (100, 1100)}, True),
    ("S12-S14, SQ1/SQ2 from the rear (-Y view), about 2 px/mm", (0, -1), 2, lambda c: c[:, 1],
     {0: (840, 1080), 2: (740, 920)}, True),
    ("clamp S28 / S30 from the right (+X)", (1, 1), 2, lambda c: c[:, 0], {1: (-150, 350), 2: (950, 1350)}, True),
    ("plan, rear on top: M3, Y3", (0, 1), 1, lambda c: c[:, 2], {0: (-700, 700), 1: (700, 1800)}, True),
]


def load():
    tris, cols, labels = [], [], []
    for part in ("frame", "knife", "clamp", "backgauge", "housing", "safety_sensors"):
        s = trimesh.load(OUT / f"{part}.glb", force="scene")
        for node in s.graph.nodes_geometry:
            T, g = s.graph[node]
            m = s.geometry[g].copy()
            m.apply_transform(T)
            mine = part == "safety_sensors"
            tris.append((m.triangles, mine, part, node))
            if mine:
                bid = node.split(".", 1)[1]
                labels.append((bid + ("?" if bid in UNKNOWN else ""), m.bounds.mean(0)))
    anc = json.loads((OUT / "safety_sensors_anchors.json").read_text(encoding="utf-8"))["anchors"]
    arrows = [(np.array(a["xyz"]), np.array(a["faces"], float)) for a in anc.values()]
    return tris, (labels, arrows)


def panel(tris, extra, title, sx, sy, depth, lim, hide):
    labels, arrows = extra
    targets = set(TARGET.values())
    img = Image.new("RGB", (W, H), (250, 250, 248))
    d = ImageDraw.Draw(img)
    ax_x, sgn = sx
    full = {0: (-1500, 1650), 1: (-1000, 1950), 2: (-30, 1700)}
    lx = lim.get(ax_x, full[ax_x])
    ly = lim.get(sy, full[sy])
    k = min((W - 20) / (lx[1] - lx[0]), (H - 40) / (ly[1] - ly[0]))

    def to_px(p):
        u = (p[..., ax_x] * sgn - (lx[0] if sgn > 0 else -lx[1])) * k + 10
        v = H - 10 - (p[..., sy] - ly[0]) * k
        return np.stack([u, v], -1)

    allt, allc, flag = [], [], []
    for t, mine, part, node in tris:
        if hide and part == "housing":
            continue
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        ln = np.linalg.norm(n, axis=1)
        keep = ln > 1e-9
        t, n = t[keep], n[keep] / ln[keep, None]
        shade = 0.45 + 0.55 * np.abs(n @ LIGHT)
        base = np.array([215, 40, 40]) if mine else (np.array([70, 110, 220]) if node in targets
                                                      else np.array([200, 200, 200]))
        allt.append(t)
        allc.append((shade[:, None] * base).astype(int))
        flag.append(np.full(len(t), mine))
    t = np.concatenate(allt)
    c = np.concatenate(allc)
    f = np.concatenate(flag)
    order = np.lexsort((depth(t.mean(1)), f))          # hosts first, this part's bodies on top (x-ray)
    px = to_px(t)
    for i in order:
        d.polygon([tuple(q) for q in px[i]], fill=tuple(int(v) for v in c[i]))
    for a, f in arrows:                                   # actuation point and facing, 60 mm
        u0, v0 = to_px(a)
        u1, v1 = to_px(a + 60 * f)
        d.line([(u0, v0), (u1, v1)], fill=(0, 140, 0), width=2)
        d.ellipse([u0 - 2, v0 - 2, u0 + 2, v0 + 2], fill=(0, 140, 0))
    for name, ctr in labels:
        u, v = to_px(np.array(ctr))
        if 0 <= u < W and 0 <= v < H:
            d.text((u + 4, v - 6), name, fill=(120, 0, 0))
    d.text((8, 6), title, fill=(0, 0, 0))
    return img


def main():
    tris, labels = load()
    imgs = [panel(tris, labels, *p) for p in PANELS]
    sheet = Image.new("RGB", (W * 3, H * 2), (255, 255, 255))
    for i, im in enumerate(imgs):
        sheet.paste(im, ((i % 3) * W, (i // 3) * H))
    out = HERE / "renders"
    out.mkdir(exist_ok=True)
    sheet.save(out / "safety_sensors_views.png")
    small = sheet.copy()
    small.thumbnail((1300, 1300))
    small.save(out / "safety_sensors_views_small.png")
    print("wrote", out / "safety_sensors_views.png", sheet.size)


if __name__ == "__main__":
    main()
