#!/usr/bin/env python3
"""Thread t5 (integration): the combined offline viewer, stage 1's mechanical model with the electrical layer.

Run from the project folder:  python -B stage_2_electronics/viewer/build_combined.py
Writes stage_2_electronics/viewer/index.html: one self-contained page, no library, nothing fetched.

Reads, never writes, stage_1_mechanics (read-only in episode 2; no script of it is run):
  - viewer/index.html, stage 1's own page written by assembly.py at commit f52cc8e: the 125 bodies with the
    DECISION 2 passages cut, the 360 knife poses of its motion model, the clamp and backgauge groups, its 41 checks
    and 8 open items. These are passed to build() unchanged, so the mechanical part of the page is stage 1's.
    assembly.py itself is not run, because it writes into stage_1_mechanics.
  - out/<part>_anchors.json and out/assembly_anchors.json: the 158 anchors, as assembly.py passes them.
Reads stage_2_electronics:
  - scheme_3d/electrical.glb, loaded as stage 1's load() loads a GLB (GLB = binary GL Transmission Format, GL =
    Graphics Library): trimesh scene, each node's transform applied, mm kept (never rescaled); vertices and faces
    go to build() as they are (no Manifold, no to_mesh()). The 489 nodes form 7 sub-layers by node kind, plus one
    switch for the whole electrical layer.
  - spec/layout_3d.md, block CLAMP_GROUP: the 10 nodes that move with the clamp beam (S28 and its cable end);
    B5-S28s, the bending loop, stays fixed.
build() is the copy build_viewer.py beside this file (changes marked "t5:"); the template is the copy
viewer_template.html beside it. After writing, the page is read back and compared with stage 1's page and with
electrical.glb; the script ends with "result: PASS" (exit 0) or names what differs (exit 1).
"""
import base64
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
S = HERE.parent                                   # stage_2_electronics
P = S.parent                                      # project folder
S1 = P / "stage_1_mechanics"
sys.path.insert(0, str(HERE))
import build_viewer as bv                         # noqa: E402  (the copy in stage_2_electronics/viewer)

DATA_RE = re.compile(r'<script id="data" type="application/json">(.*?)</script>', re.S)
ANCHOR_FILES = ("frame", "knife", "clamp", "backgauge", "housing", "safety_sensors", "assembly")
PART_LABELS = {
    "frame": "Frame, base and tables (mechanical)",
    "knife": "Knife and main drive (mechanical)",
    "clamp": "Clamp beam (mechanical)",
    "backgauge": "Backgauge (mechanical)",
    "housing": "Covers, console and cabinet (mechanical)",
    "safety_sensors": "Safety sensors and holders (mechanical)",
}
# node kind of electrical.<kind>.<name> -> sub-layer name, checkbox words, colour
ELEC = {
    "dev": ("el_devices", "Electrical: cabinet and console devices (boxes)", [60, 110, 210]),
    "mark": ("el_field", "Electrical: field devices on their anchors", [220, 50, 50]),
    "conn": ("el_connectors", "Electrical: connectors XC1-XC4", [240, 175, 30]),
    "mount": ("el_mounting", "Electrical: mounting plate, rails, ducts", [150, 150, 165]),
    "pass": ("el_passes", "Electrical: cable passes and switch shafts", [130, 120, 60]),
    "clip": ("el_clips", "Electrical: cable clips", [70, 70, 70]),
    "bundle": ("el_bundles", "Electrical: cable bundles (routes estimated)", [255, 135, 0]),
}


class Mesh:
    """vertices and faces, as build() reads them from a mesh"""
    def __init__(self, v, f):
        self.vertices, self.faces = v, f


class Report:
    def __init__(self):
        self.lines = []

    def add(self, check, status, text, data=None):
        self.lines.append({"check": check, "status": status, "text": text})


def page_data(path):
    m = DATA_RE.search(path.read_text(encoding="utf-8"))
    return json.loads(m.group(1)) if m else None


def load_layer(path, part="electrical"):
    """stage 1's load(): every node of the GLB with its transform applied, named <part>.<node>"""
    sc = trimesh.load(path, force="scene")
    out = {}
    for node in sc.graph.nodes_geometry:
        tf, g = sc.graph[node]
        mesh = sc.geometry[g].copy()
        mesh.apply_transform(tf)
        name = node if node.startswith(part + ".") else f"{part}.{node}"
        out[name] = mesh
    return out


def clamp_group(spec):
    txt = spec.read_text(encoding="utf-8")
    m = re.search(r"<!-- BEGIN CLAMP_GROUP -->(.*?)<!-- END CLAMP_GROUP -->", txt, re.S)
    return re.findall(r"^- `([^`]+)`", m.group(1), re.M) if m else []


def main():
    bad = []
    d1 = page_data(S1 / "viewer" / "index.html")
    # ---- the mechanical model as stage 1's page holds it
    mans, part_of, colors, cut = {}, {}, {}, []
    for b in d1["bodies"]:
        v = np.frombuffer(base64.b64decode(b["v"]), np.float32).reshape(-1, 3)
        f = np.frombuffer(base64.b64decode(b["f"]), np.uint32).reshape(-1, 3)
        mans[b["n"]] = Mesh(v, f)
        part_of[b["n"]] = b["p"]
        colors[b["n"]] = list(b["c"]) + [b["a"]]
        if b["cut"]:
            cut.append(b["n"])
    order = list(dict.fromkeys(a["p"] for a in d1["anchors"]))
    anchors_all = {}
    for p in order + [p for p in ANCHOR_FILES if p not in order]:
        anchors_all[p] = json.loads((S1 / "out" / f"{p}_anchors.json").read_text(encoding="utf-8"))["anchors"]
    K1 = d1["knife"]
    kb, steps = K1["bodies"], K1["steps"]
    T = np.frombuffer(base64.b64decode(K1["tf"]), np.float32).reshape(steps, len(kb), 12)

    def pose(th):                                   # stage 1's motion model, one pose per degree, as its page holds it
        i = int(round(th / (2 * math.pi) * steps)) % steps
        return {b: T[i, j].reshape(3, 4) for j, b in enumerate(kb)}, K1["dz"][i]

    g0, g1 = d1["clamp"]["groups"]
    # ---- the electrical layer
    layer = load_layer(S / "scheme_3d" / "electrical.glb")
    cg = clamp_group(S / "spec" / "layout_3d.md")
    if len(cg) != 10 or any(n not in layer for n in cg):
        bad.append(f"CLAMP_GROUP of spec/layout_3d.md: {len(cg)} names, not in the layer: {[n for n in cg if n not in layer]}")
    labels, layers, units = dict(PART_LABELS), {}, {}
    for n, mesh in layer.items():
        kind = n.split(".")[1]
        if kind not in ELEC:
            bad.append(f"unknown node kind {n}")
            continue
        p, lab, col = ELEC[kind]
        mans[n] = Mesh(np.asarray(mesh.vertices, np.float32), np.asarray(mesh.faces, np.uint32))
        part_of[n] = p
        colors[n] = col + [255]
        labels[p], layers[p], units[p] = lab, "electrical", "items"
    mm = {"knife": {"pose": pose, "th0": 0.0},
          "clamp": {"range": d1["clamp"]["range"], "axis": g0["axis"], "beam": g0["bodies"], "riders": cg,
                    "p_axis": g1["axis"], "piston": g1["bodies"]},
          "backgauge": {"range": d1["backgauge"]["range"], "axis": d1["backgauge"]["axis"],
                        "moving": d1["backgauge"]["bodies"]}}
    rep = Report()
    out = HERE / "index.html"
    info = bv.build(P, mans, part_of, anchors_all, {}, mm, cut_names=cut, colors=colors, report=rep,
                    checks=d1["checks"], open_items=d1["open_items"], inputs=d1["inputs"], out_path=out,
                    legend=d1["legend"], labels=labels, layers=layers, units=units, extra=set(layer))
    v_line = rep.lines[0] if rep.lines else {"status": "FAIL", "text": "no line V"}
    if v_line["status"] != "PASS":
        bad.append("line V: " + v_line["text"][:300])

    # ---- read the page back and compare
    d2 = page_data(out)
    nb1 = len(d1["bodies"])
    same_bodies = d2["bodies"][:nb1] == d1["bodies"]
    same_anchors = d2["anchors"] == d1["anchors"]
    if not same_bodies:
        bad.append("the mechanical bodies differ from stage 1's page")
    if not same_anchors:
        diff = [a["n"] for a, b in zip(d2["anchors"], d1["anchors"]) if a != b]
        bad.append(f"anchors differ from stage 1's page: {len(d2['anchors'])} vs {len(d1['anchors'])}, {diff[:5]}")
    for k in ("knife", "backgauge", "checks", "open_items", "legend", "inputs"):
        if d2[k] != d1[k]:
            bad.append(f"{k} differs from stage 1's page")
    want0 = dict(g0, bodies=list(g0["bodies"]) + cg)
    if d2["clamp"]["groups"] != [want0, g1] or d2["clamp"]["range"] != d1["clamp"]["range"]:
        bad.append("clamp groups are not stage 1's plus the CLAMP_GROUP nodes")
    if any("B5-S28s" in n for g in d2["clamp"]["groups"] for n in g["bodies"]):
        bad.append("B5-S28s moves with the clamp")
    el = [b for b in d2["bodies"] if b["n"] in layer]
    if sorted(b["n"] for b in el) != sorted(layer):
        bad.append(f"electrical nodes in the page {len(el)} of {len(layer)}")
    worst = 0.0
    for b in el:
        v = np.frombuffer(base64.b64decode(b["v"]), np.float32).reshape(-1, 3)
        f = np.frombuffer(base64.b64decode(b["f"]), np.uint32).reshape(-1, 3)
        m = layer[b["n"]]
        if f.shape != m.faces.shape or not np.array_equal(f, m.faces.astype(np.uint32)):
            bad.append(f"faces of {b['n']} differ")
        worst = max(worst, float(np.abs(v.astype(float) - np.asarray(m.vertices, float)).max()))
    if worst > 0.01:
        bad.append(f"electrical vertices off by {worst:.3f} mm")
    html = out.read_text(encoding="utf-8")
    net = sorted({x.group(0) for x in bv.NET.finditer(html)})
    if net:
        bad.append(f"network references {net}")
    eparts = [p for p in d2["parts"] if p.get("layer") == "electrical"]
    if "Electrical layer, all of it" not in html or len(eparts) != len({v[0] for v in ELEC.values()}):
        bad.append("no switch for the electrical layer")

    print(f"viewer/index.html: {len(html.encode('utf-8')) / 1e6:.2f} MB, {len(d2['bodies'])} bodies = "
          f"{nb1} mechanical (equal to stage 1's page: {'yes' if same_bodies else 'NO'}) + {len(el)} electrical "
          f"(electrical.glb {len(layer)} nodes, vertices within {worst:.4f} mm)")
    print(f"parts: {len(d2['parts'])} checkboxes = {len(d2['parts']) - len(eparts)} mechanical + {len(eparts)} "
          f"electrical sub-layers, plus one switch for the whole electrical layer")
    print(f"anchors {len(d2['anchors'])} (equal to stage 1's page: {'yes' if same_anchors else 'NO'}, none added); "
          f"clamp group {len(d2['clamp']['groups'][0]['bodies'])} bodies = {len(g0['bodies'])} stage 1 + {len(cg)} "
          f"CLAMP_GROUP nodes; B5-S28s fixed")
    print(f"network references: {len(net)}; line V: {v_line['status']}")
    for b in bad:
        print("bad:", b)
    print("result:", "PASS" if not bad else "FAIL")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
