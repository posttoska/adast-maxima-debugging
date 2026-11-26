"""Renders of the electrical layer on episode 1's model (PIL only, painter's algorithm, as stage 1's render_views.py).

Run:   python -B stage_2_electronics/scheme_3d/render_views.py   -> scheme_3d/renders/*.png
Reads stage_1_mechanics/out/assembly.glb (read-only) and electrical.glb next to this file; writes nothing else.
The model is drawn faded ("X-ray"), so that bundles inside the frame stay visible; the electrical layer is drawn on top,
sorted by depth among itself. Colours: bundles B1-B5 one colour each, clips black, cabinet and console devices orange,
field-device markers red, connectors XC1-XC4 purple, passages (glands, holes) cyan, plate/rails/ducts blue-grey.
Views are orthographic; screen right / up / toward-the-viewer axes are written under each picture.
"""
import math
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "renders"
BUNDLE_RGB = {"B1": (31, 119, 180), "B2": (44, 160, 44), "B3": (214, 39, 40), "B4": (148, 103, 189), "B5": (255, 127, 14)}
CLASS_RGB = {"clip": (20, 20, 20), "dev": (240, 150, 40), "mark": (220, 20, 60), "conn": (120, 40, 160),
             "pass": (0, 170, 190), "mount": (110, 130, 150)}
MODEL_RGB = (150, 150, 150)
LIGHT = np.array([0.35, -0.55, 0.76]) / np.linalg.norm([0.35, -0.55, 0.76])


def font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def load(path):
    """Nodes of a GLB in machine coordinates (mm, never rescaled), the stage-1 loader (assembly.py 276-282)."""
    sc = trimesh.load(path, force="scene")
    out = []
    for node in sc.graph.nodes_geometry:
        tf, g = sc.graph[node]
        m = sc.geometry[g].copy()
        m.apply_transform(tf)
        out.append((node, m))
    return out


def colour(name):
    if not name.startswith("electrical."):
        return MODEL_RGB
    cls = name.split(".")[1]
    if cls == "bundle":
        return BUNDLE_RGB[name.split(".")[2].split("-")[0]]
    return CLASS_RGB[cls]


def view_axes(right, up):
    r, u = np.array(right, float), np.array(up, float)
    return r, u, np.cross(r, u)          # toward the viewer (larger = nearer)


def oblique(az_deg, el_deg):
    """Viewer at azimuth az (0 = in front, from -Y; + toward -X) and elevation el above the horizon."""
    a, e = math.radians(az_deg), math.radians(el_deg)
    d = np.array([-math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])
    r = np.cross(-d, [0, 0, 1.0]); r /= np.linalg.norm(r)
    return r, np.cross(r, -d), d


def inside(m, region):
    if region is None:
        return True
    lo, hi = m.bounds
    return bool(np.all(hi >= region[0]) and np.all(lo <= region[1]))


def tris(items, axes):
    r, u, d = axes
    pts, cols, dep = [], [], []
    for name, m in items:
        v = m.vertices[m.faces]                              # (n, 3, 3)
        n = m.face_normals
        shade = 0.45 + 0.55 * np.abs(n @ LIGHT)
        base = np.array(colour(name), float)
        pts.append(np.stack([v @ r, v @ u], axis=-1))
        cols.append(np.clip(base[None, :] * shade[:, None], 0, 255).astype(int))
        dep.append((v @ d).mean(axis=1))
    if not pts:
        return np.zeros((0, 3, 2)), np.zeros((0, 3), int), np.zeros(0)
    return np.concatenate(pts), np.concatenate(cols), np.concatenate(dep)


def render(model, elec, axes, region, width, title, axis_note, labels=(), fade=0.28, label_px=14):
    """One picture: model faded, electrical layer on top; region = (lo, hi) in mm selects the items drawn."""
    mod = [(n, m) for n, m in model if inside(m, region)]
    ele = [(n, m) for n, m in elec if inside(m, region)]
    P1, C1, D1 = tris(mod, axes)
    P2, C2, D2 = tris(ele, axes)
    allp = np.concatenate([P1.reshape(-1, 2), P2.reshape(-1, 2)])
    if region is not None:                                   # frame the region, not the whole bodies cut by it
        corners = np.array([[x, y, z] for x in (region[0][0], region[1][0]) for y in (region[0][1], region[1][1])
                            for z in (region[0][2], region[1][2])], float)
        allp = np.stack([corners @ axes[0], corners @ axes[1]], axis=-1)
    lo, hi = allp.min(axis=0), allp.max(axis=0)
    margin, top, bottom = 20, 44, 30
    s = (width - 2 * margin) / max(hi[0] - lo[0], 1e-9)
    height = int((hi[1] - lo[1]) * s) + top + bottom
    to_px = lambda p: np.stack([margin + (p[..., 0] - lo[0]) * s, top + (hi[1] - p[..., 1]) * s], axis=-1)
    layers = []
    for P, C, D in ((P1, C1, D1), (P2, C2, D2)):
        im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        q = to_px(P)
        for i in np.argsort(D):                              # far first
            c = tuple(int(x) for x in C[i])
            dr.polygon([tuple(xy) for xy in q[i]], fill=c + (255,), outline=c + (255,))
        layers.append(im)
    a = layers[0].getchannel("A").point(lambda x: int(x * fade))
    layers[0].putalpha(a)
    img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    img.alpha_composite(layers[0])
    img.alpha_composite(layers[1])
    dr = ImageDraw.Draw(img)
    f, placed = font(label_px), []
    for text, xyz, rgb in sorted(labels, key=lambda l: np.dot(l[1], axes[0])):
        p = to_px(np.array([[np.dot(xyz, axes[0]), np.dot(xyz, axes[1])]]))[0]
        x, y = p[0] + 4, p[1] - label_px - 2
        w = dr.textlength(text, font=f)
        for _ in range(6):                                   # move a label down until it hits no earlier label
            if not any(x < bx1 and bx0 < x + w and y < by1 and by0 < y + label_px + 2 for bx0, by0, bx1, by1 in placed):
                break
            y += label_px + 2
        placed.append((x, y, x + w, y + label_px + 2))
        dr.text((x, y), text, fill=rgb, font=f, stroke_width=3, stroke_fill=(255, 255, 255))
    dr.text((margin, 10), title, fill=(0, 0, 0), font=font(18))
    dr.text((margin, height - bottom + 6), axis_note, fill=(60, 60, 60), font=font(13))
    return img.convert("RGB")


def legend(img):
    dr, f, x, y = ImageDraw.Draw(img), font(13), img.width - 250, 40
    for k, rgb in list(BUNDLE_RGB.items()) + [("clip", CLASS_RGB["clip"]), ("cabinet/console device", CLASS_RGB["dev"]),
                                               ("field-device marker", CLASS_RGB["mark"]), ("connector XC", CLASS_RGB["conn"]),
                                               ("passage", CLASS_RGB["pass"]), ("plate, rail, duct", CLASS_RGB["mount"])]:
        dr.rectangle([x, y, x + 14, y + 12], fill=rgb)
        dr.text((x + 20, y - 2), ("bundle " + k) if k.startswith("B") else k, fill=(0, 0, 0), font=f)
        y += 17
    return img


def leg_labels(elec):
    """Label each trunk leg (B1..B5) at the middle of its longest segment; markers by designation."""
    out, best = [], {}
    for n, m in elec:
        p = n.split(".")
        if p[1] == "bundle" and "-" not in p[2]:
            ext = float(np.max(m.extents))
            if ext > best.get(p[2], (0, None))[0]:
                best[p[2]] = (ext, m.bounds.mean(axis=0))
    for k, (_, c) in sorted(best.items()):
        out.append((k, c, BUNDLE_RGB[k]))
    return out


def main():
    OUT.mkdir(exist_ok=True)
    model = load(ROOT / "stage_1_mechanics" / "out" / "assembly.glb")
    elec = load(HERE / "electrical.glb")
    marks = [(n.split(".")[2], m.bounds.mean(axis=0), CLASS_RGB["mark"]) for n, m in elec if n.split(".")[1] == "mark"]
    conns = [(n.split(".")[2], m.bounds.mean(axis=0), CLASS_RGB["conn"]) for n, m in elec if n.split(".")[1] == "conn"]
    devs = [(n.split(".")[2], m.bounds.mean(axis=0), (150, 80, 0)) for n, m in elec if n.split(".")[1] == "dev"]
    bl = leg_labels(elec)
    shots = {
        "overview_oblique": (oblique(35, 28), None, 1300, "front-left-above, oblique (azimuth 35 deg, elevation 28 deg)",
                             bl + marks),
        "top": (view_axes((1, 0, 0), (0, 1, 0)), None, 1300, "screen right +X, up +Y (rear), viewer above (+Z)", bl + marks),
        "front": (view_axes((1, 0, 0), (0, 0, 1)), None, 1300, "screen right +X, up +Z, viewer in front (-Y)", bl + marks),
        "side_right": (view_axes((0, 1, 0), (0, 0, 1)), None, 1300, "screen right +Y (rear), up +Z, viewer at the right (+X)",
                       bl + marks),
    }
    for name, (axes, region, w, note, lab) in shots.items():
        img = render(model, elec, axes, region, w, f"Electrical layer (thread t4) on stage-1 assembly.glb: {name}", note, lab)
        legend(img).save(OUT / f"{name}.png")
    cab = ((-1440, -215, -10), (-1100, 315, 1560))
    a = render(model, elec, view_axes((0, -1, 0), (0, 0, 1)), cab, 620, "Cabinet through the door (from -X)",
               "screen right -Y, up +Z, viewer at -X (door)", devs, label_px=12)
    b = render(model, elec, view_axes((1, 0, 0), (0, 0, 1)), cab, 420, "Cabinet from the front (-Y)",
               "screen right +X, up +Z", devs[:0] + conns, label_px=12)
    h = max(a.height, b.height)
    both = Image.new("RGB", (a.width + b.width, h), (255, 255, 255))
    both.paste(a, (0, 0)); both.paste(b, (a.width, 0))
    both.save(OUT / "cabinet.png")
    con = ((-860, -500, 1150), (880, -370, 1560))
    c = render(model, elec, view_axes((1, 0, 0), (0, 0, 1)), con, 1300, "Console from the front (-Y), cover faded",
               "screen right +X, up +Z, viewer in front (-Y)", devs + [l for l in marks if l[0] in ("S1",)], label_px=14)
    c.save(OUT / "console.png")
    for p in sorted(OUT.glob("*.png")):
        print(p.name, Image.open(p).size)


if __name__ == "__main__":
    main()
