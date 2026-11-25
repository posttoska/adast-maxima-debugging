"""Orthographic renders of the knife part at rest and at the bottom of the stroke (PIL only).
Run: python stage_1_mechanics/parts/knife/render_views.py -> parts/knife/renders/knife_views.png
Panels: front at rest, front at the bottom (seen by the operator from -Y), right side at rest (from +X,
front on the left), top at rest (rear at the top). Reference lines: table top Z 885 and crossbar
underside Z 1415 (grey), cheek faces X +-720 (green), overall width X 1553 (red).
"""
import math
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import knife as K  # noqa: E402

VIEWS = {"front": ((1, 0, 0), (0, 0, 1), (0, -1, 0)), "side": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
         "top": ((1, 0, 0), (0, 1, 0), (0, 0, 1))}
MOVING = {"knife", "holder", "holder_pin", "conrod", "crank_pin"}
S, PAD = 0.28, 30                      # px per mm, margin
BOX = np.array([[-800, -150, 0], [1600, 900, 1560]], float)


def colour(b):
    if b in MOVING:
        return (235, 190, 40)
    if b.startswith(("guide", "lever", "gear_box")):
        return (90, 170, 90)
    return (90, 130, 190)


def panel(meshes, view, title):
    ax, ay, ad = (np.array(v, float) for v in VIEWS[view])
    lo, hi = BOX[0], BOX[1]
    w = int((abs(ax) @ (hi - lo)) * S) + 2 * PAD
    h = int((abs(ay) @ (hi - lo)) * S) + 2 * PAD
    img = Image.new("RGB", (w, h), (250, 250, 250))
    d = ImageDraw.Draw(img)
    def P(p):
        return (PAD + (p @ ax - lo @ abs(ax) if ax.sum() > 0 else 0) * S,
                h - PAD - (p @ ay - lo @ abs(ay)) * S)
    tris = []
    for b, m in meshes.items():
        tri = m.vertices[m.faces]
        n = m.face_normals @ ad
        depth = tri.mean(axis=1) @ ad
        for t, nn, dd in zip(tri, n, depth):
            if nn > 0:
                tris.append((dd, t, nn, colour(b)))
    tris.sort(key=lambda x: x[0])
    for dd, t, nn, c in tris:
        f = 0.45 + 0.55 * nn
        d.polygon([P(p) for p in t], fill=tuple(int(v * f) for v in c))
    def line(p0, p1, col):
        d.line([P(np.array(p0, float)), P(np.array(p1, float))], fill=col, width=1)
    if view in ("front", "side"):
        for z in (885, 1415):
            line([-800, -150, z], [1600, 900, z], (150, 150, 150))
    if view in ("front", "top"):
        for x in (-720, 720):
            line([x, -150, 0], [x, 900, 1560], (40, 160, 40))
        line([1553, -150, 0], [1553, 900, 1560], (220, 40, 40))
    d.text((6, 4), title, fill=(0, 0, 0))
    return img


def bottom_state(meshes, kin, geo):
    cx, cz, hx, hz, s, y = (kin[k] for k in ("crank_x", "crank_z", "pin_x", "pin_z_rest", "stroke", "rod_plane_y"))
    L, r = kin["rod_length"], kin["crank_radius"]
    B = math.hypot(cx - hx, hz - s - cz)
    pb = np.array([cx, cz]) - r * np.array([hx - cx, hz - s - cz]) / B
    out = {}
    for b, m in meshes.items():
        m2 = m.copy()
        if b in ("knife", "holder", "holder_pin"):
            m2.apply_translation([0, 0, -s])
        out[b] = m2
    out["conrod"] = K.to_trimesh(K.rod([pb[0], y, pb[1]], [hx, y, hz - s], float(geo["conrod"]["d"])))
    out["crank_pin"] = K.to_trimesh(K.cylinder("y", list(pb), float(geo["crank_pin"]["d"]), *K.rng(geo["crank_pin"]["s"])))
    return out


def main():
    rows, _, kin = K.read_spec(HERE.parents[1] / "spec" / "knife.md")
    geo = {r[0]: K.parse_geometry(r[2])[1] for r in rows}
    sc = trimesh.load(HERE.parents[1] / "out" / "knife.glb", force="scene")
    rest = {}
    for node in sc.graph.nodes_geometry:
        tf, g = sc.graph[node]
        m = sc.geometry[g].copy()
        m.apply_transform(tf)
        rest[node.split(".", 1)[1]] = m
    bot = bottom_state(rest, kin, geo)
    ps = [panel(rest, "front", "front, at rest (knife up, crank at TDC)"),
          panel(bot, "front", "front, at the bottom (edge Z 884.85)"),
          panel(rest, "side", "right side, at rest (front on the left)"),
          panel(rest, "top", "top, at rest (rear at the top)")]
    W = ps[0].width + ps[1].width
    H = ps[0].height + max(ps[2].height, ps[3].height)
    img = Image.new("RGB", (max(W, ps[2].width + ps[3].width), H), (255, 255, 255))
    img.paste(ps[0], (0, 0)); img.paste(ps[1], (ps[0].width, 0))
    img.paste(ps[2], (0, ps[0].height)); img.paste(ps[3], (ps[2].width, ps[0].height))
    outd = HERE / "renders"
    outd.mkdir(exist_ok=True)
    img.save(outd / "knife_views.png")
    print("render:", outd / "knife_views.png", img.size)


if __name__ == "__main__":
    main()
