"""Views of the clamp part (thread 3) for a visual check: flat-shaded orthographic panels drawn with Pillow.
Panels: front (from the operator) and side (from +X) at rest and with the clamp down 130, top at rest (rear on top).
Frame, knife and backgauge bodies as a light grey background; clamp bodies coloured by group; envelopes as
yellow outlines. Run: python stage_1_mechanics/parts/clamp/render_views.py -> parts/clamp/renders/clamp_views.png
"""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
COL = {"beam": (235, 140, 40), "piston": (170, 90, 200), "gear": (70, 130, 220), "pedal": (60, 170, 90),
       "hyd": (40, 160, 170), "panel": (210, 60, 60), "fixed": (120, 150, 120)}
HYD = {"tank_oz1", "pump_op1", "valve_block_ov2", "oa1_body"}
PANEL = {"gauge_oz13", "knob_3", "knob_4"}
VIEWS = {"front": (0, 2, 1, -1), "side": (1, 2, 0, 1), "top": (0, 1, 2, 1)}   # sx axis, sy axis, depth axis, depth sign
BOUNDS = {"front": ((-1350, 1600), (0, 1700)), "side": ((-950, 1950), (0, 1700)), "top": ((-1350, 1600), (-950, 1950))}
LIGHT = np.array([0.4, -0.5, 0.75]) / np.linalg.norm([0.4, -0.5, 0.75])


def load(path):
    s = trimesh.load(path)
    out = {}
    for node in s.graph.nodes_geometry:
        T, g = s.graph[node]
        tm = s.geometry[g].copy()
        tm.apply_transform(T)
        out[node] = tm
    return out


def panel(items, envs, view, title, size=(760, 520)):
    ax, ay, ad, sgn = VIEWS[view]
    (x0, x1), (y0, y1) = BOUNDS[view]
    s = min((size[0] - 40) / (x1 - x0), (size[1] - 60) / (y1 - y0))
    img = Image.new("RGB", size, (255, 255, 255))
    dr = ImageDraw.Draw(img)

    def P(p):
        return np.stack([20 + (p[:, 0] - x0) * s, size[1] - 20 - (p[:, 1] - y0) * s], 1)

    tris = []
    for tm, col, bg in items:
        v = tm.vertices[tm.faces]
        n = tm.face_normals
        shade = 0.55 + 0.45 * np.abs(n @ LIGHT)
        depth = sgn * v[:, :, ad].mean(1) + (0 if bg else 1e5)      # clamp drawn over the partners
        for k in range(len(v)):
            c = tuple(int(255 - (255 - ch) * (0.35 if bg else 1.0) * shade[k]) for ch in col)
            tris.append((depth[k], v[k][:, [ax, ay]], c))
    tris.sort(key=lambda t: t[0])
    for _, pts, c in tris:
        q = P(pts)
        dr.polygon([tuple(p) for p in q], fill=c)
    for mn, mx in envs:
        q = P(np.array([[mn[ax], mn[ay]], [mx[ax], mx[ay]]]))
        dr.rectangle([min(q[:, 0]), min(q[:, 1]), max(q[:, 0]), max(q[:, 1])], outline=(220, 180, 0), width=2)
    dr.text((10, 6), title, fill=(0, 0, 0))
    return img


def main():
    out = R / "out"
    meta = json.loads((out / "clamp_anchors.json").read_text(encoding="utf-8"))
    groups = {k.split(".", 1)[1]: v["group"] for k, v in meta["meta"]["bodies"].items()}
    envs = [(a["min"], a["max"]) for a in meta["anchors"].values() if a.get("box_kind") == "envelope"]
    clamp = load(out / "clamp.glb")
    partners = []
    for f in ("frame.glb", "knife.glb", "backgauge.glb"):
        partners += [(tm, (110, 110, 110), True) for tm in load(out / f).values()]

    def items_at(d):
        its = list(partners)
        for node, tm in clamp.items():
            b = node.split(".", 1)[1]
            g = groups[b]
            t = tm.copy()
            if g == "beam":
                t.apply_translation([0, 0, -d])
            elif g == "piston":
                t.apply_translation([0, 0, d])
            col = COL["hyd"] if b in HYD else COL["panel"] if b in PANEL else COL.get(g, COL["fixed"])
            its.append((t, col, False))
        return its

    rest, down = items_at(0.0), items_at(130.0)
    pans = [panel(rest, envs, "front", "front from the operator, at rest (clamp up)"),
            panel(down, envs, "front", "front, clamp down 130"),
            panel(rest, envs, "side", "side from +X (rear to the right), at rest"),
            panel(down, envs, "side", "side from +X, clamp down 130"),
            panel(rest, envs, "top", "top, rear on top, at rest"),
            Image.new("RGB", (760, 520), (255, 255, 255))]
    d = ImageDraw.Draw(pans[5])
    legend = ["orange: beam (moves down 130)", "purple: OA1 piston and rod (up 130)", "blue: gear 8",
              "green: pedal 5", "teal: tank OZ1, pump OP1, valve block OV2, OA1 body", "red: gauge OZ13, knobs 3, 4",
              "grey-green: guides, brake Y14", "yellow outline: envelopes (linkage and pedal link, contents unknown)",
              "light grey: frame, knife, backgauge (delivered files)"]
    for i, t in enumerate(legend):
        d.text((20, 30 + 22 * i), t, fill=(0, 0, 0))
    img = Image.new("RGB", (760 * 2, 520 * 3), (255, 255, 255))
    for i, p in enumerate(pans):
        img.paste(p, ((i % 2) * 760, (i // 2) * 520))
    outd = HERE / "renders"
    outd.mkdir(exist_ok=True)
    img.save(outd / "clamp_views.png")
    small = img.copy()
    small.thumbnail((1300, 1300))
    small.save(outd / "clamp_views_small.png")
    print("render:", outd / "clamp_views.png", img.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
