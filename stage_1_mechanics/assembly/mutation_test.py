"""Mutation test of assembly.py (critic item 28): every check must FAIL on a fault planted in a copy.

Each mutant is a fresh copy of the six parts' inputs (out/<part>.glb, out/<part>_anchors.json, spec/) with one planted
fault: a body moved, scaled, opened or renamed in a part GLB (edited in the GLB's own JSON chunk, the mesh bytes stay),
an anchor or a spec row changed, or, for the two self-checks of the writers (B3, V), a fault in the writer itself (the
GLB export shifted by 1 mm; a template copy with "https://"). assembly.main() runs on each copy in this process; a
mutant is CAUGHT when every check it targets has a FAIL line and the run exits 1. The unmutated copy runs first and
must give 0 FAIL. Then the clause cases (tester 3, round 3, item 13): copies with one anchor error, tie or share
condition changed, each AS EXPECTED when the clauses of the open item 'checks on estimated values' it feeds print the
expected can/cannot words; the base copy's words are case F0.

    python stage_1_mechanics/assembly/mutation_test.py --work <empty folder in job tmp> [--only M3,M9a]

Writes <work>/<mutant>/ (each copy with its assembly_report.json and log) and R/assembly/mutation_report.txt + .json.
Units mm, Z up, as the parts.
"""
import argparse
import contextlib
import json
import re
import shutil
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
R = HERE.parent
sys.path.insert(0, str(HERE))
import assembly  # noqa: E402
import build_viewer  # noqa: E402

PARTS = assembly.PARTS


# ---------------------------------------------------------------------------------------------- GLB JSON chunk
def glb_load(p):
    b = Path(p).read_bytes()
    n = int.from_bytes(b[12:16], "little")
    return json.loads(b[20:20 + n].decode("utf-8")), b[20 + n:]


def glb_save(p, js, rest):
    j = json.dumps(js, separators=(",", ":")).encode("utf-8")
    j += b" " * (-len(j) % 4)
    body = len(j).to_bytes(4, "little") + b"JSON" + j + rest
    Path(p).write_bytes(b"glTF" + (2).to_bytes(4, "little") + (12 + len(body)).to_bytes(4, "little") + body)


def local(nd):
    if "matrix" in nd:
        return np.array(nd["matrix"], float).reshape(4, 4).T
    T, Rm, S = np.eye(4), np.eye(4), np.eye(4)
    if "translation" in nd:
        T[:3, 3] = nd["translation"]
    if "rotation" in nd:
        x, y, z, w = nd["rotation"]
        Rm[:3, :3] = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    if "scale" in nd:
        S[:3, :3] = np.diag(nd["scale"])
    return T @ Rm @ S


def node_index(js, body):
    part, short = body.split(".", 1)
    hits = [i for i, nd in enumerate(js["nodes"]) if "mesh" in nd and nd.get("name") in (short, body)]
    assert len(hits) == 1, f"{body}: {len(hits)} nodes"
    return hits[0]


def edit_world(root, body, F):
    """apply the world-space 4x4 F to the node of body (its parents' matrices kept)"""
    p = root / "out" / f"{body.split('.')[0]}.glb"
    js, rest = glb_load(p)
    i = node_index(js, body)
    parent = {c: k for k, nd in enumerate(js["nodes"]) for c in nd.get("children", [])}
    W, k = np.eye(4), parent.get(i)
    while k is not None:
        W = local(js["nodes"][k]) @ W
        k = parent.get(k)
    nd = js["nodes"][i]
    new = np.linalg.inv(W) @ F @ W @ local(nd)
    for key in ("translation", "rotation", "scale"):
        nd.pop(key, None)
    nd["matrix"] = new.T.reshape(-1).tolist()
    glb_save(p, js, rest)


def Tm(d):
    M = np.eye(4)
    M[:3, 3] = d
    return M


def Sm(s):
    return np.diag(list(np.broadcast_to(np.asarray(s, float), 3)) + [1.0])


def move(root, body, d):
    edit_world(root, body, Tm(d))


def scale_about_centre(root, body, s):
    c = BOX[body].mean(axis=0)
    edit_world(root, body, Tm(c) @ Sm(s) @ Tm(-c))


def place(root, body, centre, size=None):
    """move body so that its box centre is at centre; with size, first shrink it to that largest extent"""
    c = BOX[body].mean(axis=0)
    k = size / float((BOX[body][1] - BOX[body][0]).max()) if size else 1.0
    edit_world(root, body, Tm(centre) @ Sm(k) @ Tm(-c))


def drop_triangle(root, body):
    p = root / "out" / f"{body.split('.')[0]}.glb"
    js, rest = glb_load(p)
    acc = js["accessors"][js["meshes"][js["nodes"][node_index(js, body)]["mesh"]]["primitives"][0]["indices"]]
    acc["count"] -= 3
    glb_save(p, js, rest)


def rename(root, body, new_short):
    p = root / "out" / f"{body.split('.')[0]}.glb"
    js, rest = glb_load(p)
    js["nodes"][node_index(js, body)]["name"] = new_short
    glb_save(p, js, rest)


def anchor(root, part, fn):
    p = root / "out" / f"{part}_anchors.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    fn(d["anchors"], d.get("meta", {}))
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")


def drop_line(root, rel, start):
    p = root / rel
    L = p.read_text(encoding="utf-8").split("\n")
    hit = [i for i, line in enumerate(L) if line.replace(" ", "").startswith(start.replace(" ", ""))]
    assert len(hit) == 1, f"{rel}: {len(hit)} lines start with {start!r}"
    del L[hit[0]]
    p.write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------------------------------------- writer faults
@contextlib.contextmanager
def export_shift():
    """B3: the assembly GLB writer moves one body by 1 mm"""
    orig = trimesh.Scene.export

    def export(self, *a, **k):
        g = sorted(self.geometry)[0]
        m = self.geometry[g].copy()
        m.apply_translation([1.0, 0.0, 0.0])
        self.geometry[g] = m
        return orig(self, *a, **k)
    trimesh.Scene.export = export
    try:
        yield
    finally:
        trimesh.Scene.export = orig


@contextlib.contextmanager
def patch_items(edit):
    """N, EW: a fault planted in the written open items (the two guards read them), critic g8"""
    orig = assembly.open_items
    assembly.open_items = lambda *a, **k: edit(orig(*a, **k))
    try:
        yield
    finally:
        assembly.open_items = orig


def doubled_prefix(items):
    """open item 1 names 'frame.frame.<body>' (the round-1 defect)"""
    return [items[0].replace("(cut from frame.", "(cut from frame.frame.", 1)] + items[1:]


def drop_check_3(items):
    """the open item 'checks on estimated values' without its [3] clause (the round-1 defect)"""
    out = []
    for t in items:
        if t.startswith("checks on estimated values"):
            head, _, body = t.partition(": ")
            t = head + ": " + "; ".join(p for p in re.split(r"; (?=\[)", body) if not p.startswith("[3]"))
        out.append(t)
    return out


def joint_4_6(items):
    """the open item 'checks on estimated values' with its [4] and [6] clauses replaced by the round-2 joint clause,
    which called both 'cannot flip' and named no value (critic g9 F1)"""
    out = []
    for t in items:
        if t.startswith("checks on estimated values"):
            head, _, body = t.partition(": ")
            cl = [p for p in re.split(r"; (?=\[)", body) if not p.startswith(("[4]", "[6]"))]
            cl.insert(3, "[4] and [6] compare heights with the table top (clamp face, knife edge and cutting-stick top "
                         "stand on it): differences, so the table top's +-100 moves both sides and cannot flip them")
            t = head + ": " + "; ".join(cl)
        out.append(t)
    return out


@contextlib.contextmanager
def patch_line(cid, edit_text=None, edit_data=None):
    """EW (critic g9): a fault planted in what the lines of check cid print (edit_text) or declare (edit_data)"""
    orig = assembly.Report.add

    def add(self, c, status, text, data=None):
        if c == cid:
            text = edit_text(text) if edit_text else text
            data = edit_data(data) if edit_data else data
        return orig(self, c, status, text, data)
    assembly.Report.add = add
    try:
        yield
    finally:
        assembly.Report.add = orig


@contextlib.contextmanager
def patch_attr(name, make):
    """EW (critic g10): a name of the assembly module replaced by make(original) for one run"""
    orig = getattr(assembly, name)
    setattr(assembly, name, make(orig))
    try:
        yield
    finally:
        setattr(assembly, name, orig)


def drop_reads(d, pair=None):
    """a line's data without its 'reads' (pair None) or without one declared read"""
    if not d:
        return d
    if pair is None:
        return {k: v for k, v in d.items() if k != "reads"} or None
    return {**d, "reads": [r for r in d.get("reads", []) if r != pair]}


@contextlib.contextmanager
def template_https(work):
    """V: a copy of the viewer template that loads a script from the web"""
    orig = build_viewer.TEMPLATE
    t = work / "viewer_template_https.html"
    s = orig.read_text(encoding="utf-8")
    s = s.replace("</body>", '<script src="https://cdn.example.invalid/x.js"></script>\n</body>', 1) \
        if "</body>" in s else s + '\n<script src="https://cdn.example.invalid/x.js"></script>\n'
    t.write_text(s, encoding="utf-8")
    build_viewer.TEMPLATE = t
    try:
        yield
    finally:
        build_viewer.TEMPLATE = orig


# ---------------------------------------------------------------------------------------------- the mutants
def interior(part, exclude=()):
    """bodies of part whose removal leaves the part's box unchanged (so check 7 keeps its PASS), smallest first"""
    names = [n for n in BOX if n.startswith(part + ".") and n not in exclude]
    lo = np.min([BOX[n][0] for n in names], axis=0)
    hi = np.max([BOX[n][1] for n in names], axis=0)
    res = []
    for n in names:
        rest = [m for m in names if m != n]
        if np.allclose(np.min([BOX[m][0] for m in rest], axis=0), lo) and np.allclose(np.max([BOX[m][1] for m in rest], axis=0), hi):
            res.append(n)
    return sorted(res, key=lambda n: float(np.prod(BOX[n][1] - BOX[n][0])))


def mutants(work):
    ss = interior("safety_sensors", exclude=("safety_sensors.S28",))
    ob = iter(ss)
    knife = BOX["knife.knife"]
    beam_low = min(MM["clamp"]["beam"], key=lambda b: BOX[b][0][2])
    hw = np.array([BOX[b] for b in MM["handwheel"]["bodies"]])
    hw_lo, hw_hi = hw[:, 0].min(axis=0), hw[:, 1].max(axis=0)
    right = max((n for n in BOX if n.startswith("housing.")), key=lambda n: BOX[n][1][0])
    left_bg = min((n for n in BOX if n.startswith("backgauge.")), key=lambda n: BOX[n][0][0])
    house = interior("housing", exclude=("housing.cabinet", "housing.cover_11"))
    hn = sorted(n for n in BOX if n.startswith("housing."))
    o8, o9a, o9b, o9c, o9x = next(ob), next(ob), next(ob), next(ob), next(ob)
    tt0 = A0["frame"]["table.top"]["xyz"][2]                       # headline values of checks 2, 3 and 4
    tb0 = BOX["frame.table"][1][2]
    tw0 = BOX["frame.table"][1][0] - BOX["frame.table"][0][0]
    cf0 = A0["clamp"]["clamp.face"]["xyz"][2]
    lp0 = BOX["housing.left_side_panel_rear"][0][0]                # check 1 without the cabinet (critic g6)

    def tdc_out(a, m):
        c, p = np.array(a["crank.centre"]["xyz"]), np.array(a["crank.pin.tdc"]["xyz"])
        a["crank.pin.tdc"]["xyz"] = (p + (p - c) / np.linalg.norm(p - c) * 1.0).tolist()

    def dup_s24(a, m):
        a["sensor.S24"] = dict(BG_ANCHORS["sensor.S24"])

    def z_up(name, dz):
        def f(a, m):
            a[name]["xyz"][2] += dz
        return f

    return [
        ("MB1", ["B1"], f"housing GLB: node {hn[1]} renamed to {hn[0].split('.', 1)[1]} (two nodes, one name)",
         lambda r: rename(r, hn[1], hn[0].split(".", 1)[1]), None),
        ("MB2", ["B2"], f"housing GLB: last triangle of {house[0]} dropped (an open body)",
         lambda r: drop_triangle(r, house[0]), None),
        ("MB3", ["B3"], "assembly GLB writer shifts one body by +1 mm X before export (writer fault)",
         lambda r: None, export_shift),
        ("MD2a", ["D2", "8"], "clamp anchors: joint.passage.clamp_brake.crossbar without cut_at (uncut passage)",
         lambda r: anchor(r, "clamp", lambda a, m: a["joint.passage.clamp_brake.crossbar"].pop("cut_at")), None),
        ("MD2b", ["D2"], "backgauge anchors: passage box of joint.slot.front_extension 1000 mm up (cuts no frame)",
         lambda r: anchor(r, "backgauge", lambda a, m: a["joint.slot.front_extension"].update(
             passage=[[q[0], q[1]] if i < 2 else [q[0] + 1000, q[1] + 1000]
                      for i, q in enumerate(a["joint.slot.front_extension"]["passage"])])), None),
        ("M1", ["1"], f"housing GLB: right-most body {right} moved +60 X", lambda r: move(r, right, [60, 0, 0]), None),
        ("M1b", [f"1~{lp0 - 100:.1f} (housing.left_side_panel_rear) vs body line -1250"],
         f"housing GLB: housing.left_side_panel_rear moved -100 X (left end without the cabinet {lp0:.1f} -> "
         f"{lp0 - 100:.1f}; the cabinet stays the left-most body, so the left-end line stays OPEN)",
         lambda r: move(r, "housing.left_side_panel_rear", [-100, 0, 0]), None),
        ("M2", ["2"], "frame anchors: table.top Z +20 (body unchanged)",
         lambda r: anchor(r, "frame", z_up("table.top", 20)), None),
        ("M2b", [f"2~table top Z {tt0 + 120:.1f} (anchor table.top), frame.table top {tb0 + 120:.1f}"],
         "frame GLB + anchors: frame.table body and table.top anchor both +120 Z (only the 885 +-100 band breaks)",
         lambda r: (move(r, "frame.table", [0, 0, 120]), anchor(r, "frame", z_up("table.top", 120))), None),
        ("M3", ["3"], "knife GLB: knife.knife scaled 0,8 along X about its centre (1056 < 1150)",
         lambda r: scale_about_centre(r, "knife.knife", [0.8, 1, 1]), None),
        ("M3b", [f"3~= {tw0 * 0.98:.1f} (T 1150)"], f"frame GLB: frame.table scaled 0,98 along X about its centre "
         f"({tw0 * 0.98:.1f} < 1140)", lambda r: scale_about_centre(r, "frame.table", [0.98, 1, 1]), None),
        ("M4", ["4"], "knife anchors: knife.edge.rest Z -20 (edge 130 - 20 above the table)",
         lambda r: anchor(r, "knife", z_up("knife.edge.rest", -20)), None),
        ("M4b", [f"4~: {cf0 - 20 - tt0:.1f} above the table (T 130)"], f"clamp GLB + anchors: clamp.face anchor and "
         f"the clamp beam bodies ({', '.join(MM['clamp']['beam'])}) -20 Z together (face {cf0 - 20 - tt0:.0f} above "
         f"the table, beam bottom still = face)",
         lambda r: ([move(r, b, [0, 0, -20]) for b in MM["clamp"]["beam"]], anchor(r, "clamp", z_up("clamp.face", -20))),
         None),
        ("M5", ["5"], "backgauge anchors: backgauge.face range 0..1100 (front end Y 50)",
         lambda r: anchor(r, "backgauge", lambda a, m: a["backgauge.face"]["motion"].update(range=[0.0, 1100.0])), None),
        ("M6", ["6"], "knife anchors: crank.pin.tdc 1 mm further from crank.centre (crank radius +1)",
         lambda r: anchor(r, "knife", tdc_out), None),
        ("M6b", ["6~clamp stroke 115.0 (T 130)"], "clamp anchors: clamp.face motion range 0..115 (clamp stroke 115)",
         lambda r: anchor(r, "clamp", lambda a, m: a["clamp.face"]["motion"].update(range=[0.0, 115.0])), None),
        ("M7", ["7"], f"backgauge GLB: left-most body {left_bg} moved -5 X", lambda r: move(r, left_bg, [-5, 0, 0]), None),
        ("M8", ["8"], f"safety_sensors GLB: {o8} moved into frame.table (centre X 300, Y 586, Z 835)",
         lambda r: place(r, o8, [300, 586, 835]), None),
        ("M8e", ["8e"], "clamp anchors: envelope.clamp.pedal_link box moved into frame.table",
         lambda r: anchor(r, "clamp", lambda a, m: a["envelope.clamp.pedal_link"].update(
             min=[250.0, 500.0, 800.0], max=[350.0, 600.0, 870.0])), None),
        ("M9a", ["9:knife turn"], f"safety_sensors GLB: {o9a} shrunk to 8 mm, under the knife edge (X 300, "
         f"Y {knife.mean(axis=0)[1]:.1f}, Z {(885 + knife[0][2]) / 2:.1f})",
         lambda r: place(r, o9a, [300, knife.mean(axis=0)[1], (885 + knife[0][2]) / 2], 8), None),
        ("M9b", ["9:backgauge travel"], f"safety_sensors GLB: {o9b} shrunk to 8 mm on the table in the pusher's "
         f"path (X 400, Y 600, Z 940)", lambda r: place(r, o9b, [400, 600, 940], 8), None),
        ("M9c", ["9:clamp stroke, backgauge at rest"], f"safety_sensors GLB: {o9c} shrunk to 8 mm under {beam_low} "
         f"(X 300, Y {BOX[beam_low].mean(axis=0)[1]:.1f}, Z 950)",
         lambda r: place(r, o9c, [300, BOX[beam_low].mean(axis=0)[1], 950], 8), None),
        ("M9x", ["9x:handwheel push-in"], f"safety_sensors GLB: {o9x} shrunk to 4 mm, 5 mm to -X of the handwheel "
         f"group (X {hw_lo[0] - 5:.1f})",
         lambda r: place(r, o9x, [hw_lo[0] - 5, (hw_lo[1] + hw_hi[1]) / 2, (hw_lo[2] + hw_hi[2]) / 2], 4), None),
        ("M10", ["10"], "housing anchors: a second sensor.S24 (doubled device anchor)",
         lambda r: anchor(r, "housing", dup_s24), None),
        ("M11", ["11"], "spec/frame.md: measure row M13 dropped (base_front's row cites it)",
         lambda r: drop_line(r, "spec/frame.md", "| M13 |"), None),
        ("M12", ["12"], "frame anchors: anchor_bolt axis +20 X on one bolt",
         lambda r: anchor(r, "frame", lambda a, m: a[sorted(k for k in a if k.startswith("anchor_bolt."))[0]]["xyz"]
                          .__setitem__(0, a[sorted(k for k in a if k.startswith("anchor_bolt."))[0]]["xyz"][0] + 20)),
         None),
        ("MV", ["V"], 'viewer template copy with <script src="https://..."> (a load from the web)',
         lambda r: None, lambda: template_https(work)),
        ("MVc", ["V"], "clamp anchors: sensor.S28 motion axis flipped to 0,0,1 (the page carries it down, its own "
         "motion says up)", lambda r: anchor(r, "clamp", lambda a, m: a["sensor.S28"]["motion"].update(axis=[0.0, 0.0, 1.0])),
         None),
        ("MN", ["N~frame.frame."], "open item 1 written with a doubled prefix 'frame.frame.<body>' (a name that is no "
         "body, anchor or measure ID)", lambda r: None, lambda: patch_items(doubled_prefix)),
        ("MEW", ["EW~missing [3]"], "open item 'checks on estimated values' written without [3] (check 3 prints the "
         "knife's W 1320)", lambda r: None, lambda: patch_items(drop_check_3)),
        ("MEW4a", ["EW~the [4] line does not print knife.edge.rest"], "the [4] line printed without "
         "'knife.edge.rest: <class> <error>' (its data still declares it)",
         lambda r: None, lambda: patch_line("4", edit_text=lambda t: re.sub(r"knife\.edge\.rest: [^;)]*; ", "", t, count=1))),
        ("MEW4b", ["EW~the [4] clause does not name knife.edge.rest"], "open item 'checks on estimated values' with "
         "the round-2 joint clause '[4] and [6] ... cannot flip them' in place of its [4] and [6] clauses (critic g9 F1)",
         lambda r: None, lambda: patch_items(joint_4_6)),
        ("MEW4c", ["EW~[4] reads knife.edge.rest"], "the [4] line declares its reads without knife.edge.rest (the "
         "code still reads it)", lambda r: None,
         lambda: patch_line("4", edit_data=lambda d: drop_reads(d, ["knife", "knife.edge.rest"]))),
        ("MEW1", ["EW~[1] reads lift.eye_left"], "the check 1 lines declare no reads (the Z line still reads "
         "lift.eye_left, D (X, Z); E (Y)), critic g10", lambda r: None, lambda: patch_line("1", edit_data=drop_reads)),
        ("MEW6", ["EW~[6] reads crank.centre"], "KNIFE_CRANK emptied: check 6 neither declares nor prints the crank "
         "anchors, so only the motion model's charge (Charged) can find them, critic g10", lambda r: None,
         lambda: patch_attr("KNIFE_CRANK", lambda o: ())),
        ("MEW3", ["EW~[3] reads crank.centre"], "motion_model built without its windows (rec dropped): its reads fall "
         "into check 3's window, as before round 3 (critic g10)", lambda r: None,
         lambda: patch_attr("motion_model", lambda o: (lambda a, m, b, rec=None: o(a, m, b)))),
    ]


# ---------------------------------------------------------------------------------------------- clause cases
# tester 3, round 3, item 13 (critic g13): a clause of the open item 'checks on estimated values' is computed only if a
# copy with one error, tie or share condition changed changes that clause's can/cannot word. A case names what it
# changes and the words it expects as (clause id, lead, word, text the span from lead to the word must hold).
BASE_WORDS = [("4", "Clamp half:", "cannot", None), ("4", "Knife half:", "can", None), ("5", "[5]", "cannot", None),
              ("6", "Clamp stroke:", "cannot", None), ("6", "Knife stroke:", "can", None),
              ("6", "Edge at the bottom:", "can", None), ("6", "Cut depth:", "can", None),
              ("12", "X verdict", "can", None)]


def set_err(part, names, value, axis=None):
    """an edit: error_mm of each named anchor set to value (only its axis entry when the error is given per axis)"""
    def fn(a, m):
        for n in names:
            e = a[n].get("error_mm")
            if isinstance(e, dict):
                for k in ([axis] if axis else list(e)):
                    e[k] = value
            else:
                a[n]["error_mm"] = value
    return lambda root: anchor(root, part, fn)


def edit_anchor(part, name, fn):
    return lambda root: anchor(root, part, lambda a, m: fn(a[name]))


def chain(*edits):
    def run_all(root):
        for e in edits:
            e(root)
    return run_all


def shift_z(d, dz):
    d["xyz"] = [d["xyz"][0], d["xyz"][1], d["xyz"][2] + dz]


def clause_cases():
    bolts = sorted(n for n in A0["frame"] if n.startswith("anchor_bolt."))
    tiny = set_err("knife", ["crank.centre", "crank.pin.tdc", "holder.pin.rest", "knife.edge.rest"], 0.01)
    return [
        ("Fe", "knife.edge.rest error 30 -> 15 (tester 3)", set_err("knife", ["knife.edge.rest"], 15),
         [("4", "Knife half:", "cannot", None)]),
        ("Ff", "backgauge.face y error 10 -> 15 (tester 3)", set_err("backgauge", ["backgauge.face"], 15, "y"),
         [("5", "[5]", "can", None)]),
        ("Fg", "clamp.face z error 100 -> 50 (tester 3)", set_err("clamp", ["clamp.face"], 50, "z"),
         [("4", "Clamp half:", "can", None)]),
        ("Fh", "anchor-bolt x errors 15 -> 5 (tester 3)", set_err("frame", bolts, 5, "x"),
         [("12", "X verdict", "cannot", None)]),
        ("F6a", "errors of crank.centre, crank.pin.tdc, holder.pin.rest and knife.edge.rest -> 0.01", tiny,
         [("6", "Knife stroke:", "cannot", None), ("6", "Edge at the bottom:", "cannot", None),
          ("6", "Cut depth:", "cannot", None)]),
        ("F6i", "as F6a, and knife.edge.bottom error 100 -> 1 (the share broken by its error)",
         chain(tiny, set_err("knife", ["knife.edge.bottom"], 1)),
         [("6", "Knife stroke:", "cannot", None), ("6", "Edge at the bottom:", "cannot", None),
          ("6", "Cut depth:", "can", "knife.edge.bottom +-1")]),
        ("F6k", "as F6a, and knife.edge.bottom's source without 'stick top' (the share broken by its source)",
         chain(tiny, edit_anchor("knife", "knife.edge.bottom",
                                 lambda d: d.update(source=d["source"].replace("stick top", "stick")))),
         [("6", "Edge at the bottom:", "cannot", None), ("6", "Cut depth:", "can", "cutting_stick.top +-")]),
        ("F6t", "as F6a, and knife.edge.rest Z + 0.5 (the tie broken; check 4 allows the body 1 from the anchor)",
         chain(tiny, edit_anchor("knife", "knife.edge.rest", lambda d: shift_z(d, 0.5))),
         [("6", "Knife stroke:", "cannot", None), ("6", "Edge at the bottom:", "can", "knife.edge.bottom +-")]),
        ("F6c", "clamp.face's source without the number 130 (the clamp range no longer a number its source names)",
         edit_anchor("clamp", "clamp.face", lambda d: d.update(source=d["source"].replace("lift 130", "lift"))),
         [("6", "Clamp stroke:", "can", None)]),
    ]


def words(items, expect):
    """for each expected (clause id, lead, word, held text): what the clause says from lead to its first verdict"""
    body = next((t.partition(": ")[2] for t in items if t.startswith("checks on estimated values")), "")
    cl = {p.split("]", 1)[0] + "]": p for p in re.split(r"; (?=\[)", body)}
    out = []
    for cid, lead, word, held in expect:
        m = re.search(re.escape(lead) + r".*?\b(CAN|can|cannot) flip", cl.get(f"[{cid}]", ""))
        found = m.group(1).lower() if m else "(no verdict)"
        has = held is None or (m is not None and held in m.group(0))
        out.append({"clause": cid, "lead": lead, "expected": word + (f" + '{held}'" if held else ""),
                    "found": found + ("" if has else f", without '{held}'"), "ok": found == word and has})
    return out


# ---------------------------------------------------------------------------------------------- running
def copy_base(base, dst):
    if dst.exists():
        raise SystemExit(f"{dst} exists: give an empty --work folder")
    (dst / "out").mkdir(parents=True)
    (dst / "assembly").mkdir()
    for p in PARTS:
        for f in (f"{p}.glb", f"{p}_anchors.json"):
            shutil.copy2(base / "out" / f, dst / "out" / f)
    shutil.copytree(base / "spec", dst / "spec")


def run(root, log, ctx=None):
    t0 = time.time()
    with open(log, "w", encoding="utf-8") as f, contextlib.redirect_stdout(f):
        try:
            with (ctx() if ctx else contextlib.nullcontext()):
                code = assembly.main(["--root", str(root)])
            err = None
        except Exception:
            code, err = None, traceback.format_exc()
            print(err)
    rp = root / "assembly" / "assembly_report.json"
    checks = json.loads(rp.read_text(encoding="utf-8"))["checks"] if rp.exists() and err is None else []
    return code, err, checks, time.time() - t0


def failing(checks, target):
    """target 'id', 'id:prefix' (the FAIL line starts with prefix) or 'id~text' (the FAIL line holds text: the
    headline number of the check, critic g5)"""
    head, _, has = target.partition("~")          # '~' first: the headline text may hold ':'
    cid, _, sub = head.partition(":")
    return [c for c in checks if c["check"] == cid and c["status"] == "FAIL" and (not sub or c["text"].startswith(sub))
            and (not has or has in c["text"])]


def target_id(t):
    return t.split("~")[0].split(":")[0]


BOX, MM, BG_ANCHORS, A0 = {}, {}, {}, {}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--base", default=str(R), help="where the six parts' out/ and spec/ are read from")
    ap.add_argument("--only", default="")
    ap.add_argument("--report", default=str(HERE / "mutation_report"))
    a = ap.parse_args(argv)
    work, base = Path(a.work).resolve(), Path(a.base).resolve()
    work.mkdir(parents=True, exist_ok=True)

    bodies, part_of, anchors, meta = assembly.load(base)
    BOX.update({n: np.array(m.bounds, float) for n, m in bodies.items()})
    MM.update(assembly.motion_model(anchors, meta, bodies))
    BG_ANCHORS.update(anchors["backgauge"])
    A0.update(anchors)

    rows = []
    c0 = work / "base"
    copy_base(base, c0)
    code, err, checks, dt = run(c0, work / "base.log")
    st = [c["status"] for c in checks]
    base_ok = err is None and code == 0 and st.count("FAIL") == 0
    base_code = code
    print(f"base copy: exit {code}, {st.count('PASS')} PASS, {st.count('FAIL')} FAIL, {st.count('OPEN')} OPEN, {dt:.1f} s"
          + ("" if base_ok else f" -- NOT CLEAN {err or ''}"), flush=True)
    only = {x for x in a.only.split(",") if x}
    for mid, targets, text, apply, ctx in mutants(work):
        if only and mid not in only:
            continue
        root = work / mid
        copy_base(base, root)
        apply(root)
        changed = [str(p.relative_to(root)) for p in sorted(root.rglob("*")) if p.is_file()
                   and (base / p.relative_to(root)).exists() and p.read_bytes() != (base / p.relative_to(root)).read_bytes()]
        code, err, checks, dt = run(root, root / "assembly" / "mutant.log", ctx)
        hit = {t: failing(checks, t) for t in targets}
        others = sorted({c["check"] for c in checks if c["status"] == "FAIL"} - {target_id(t) for t in targets})
        caught = err is None and code == 1 and all(hit.values()) and bool(changed or ctx)
        row = {"mutant": mid, "targets": targets, "planted": text, "files_changed": changed or ["(writer fault)"],
               "exit": code, "caught": caught, "error": err,
               "target_fail_lines": {t: [c["text"][:220] for c in h] for t, h in hit.items()},
               "other_failing_checks": others, "seconds": round(dt, 1)}
        rows.append(row)
        print(f"{mid:5s} {'CAUGHT' if caught else 'MISSED'} exit {code} targets {targets} -> "
              f"{ {t: len(h) for t, h in hit.items()} }; other FAIL {others}; {dt:.1f} s"
              + (f"; ERROR {err.splitlines()[-1]}" if err else ""), flush=True)
    # clause cases: the base copy's words first (no edit), then one fresh copy per case
    rp0 = c0 / "assembly" / "assembly_report.json"
    w0 = words(json.loads(rp0.read_text(encoding="utf-8")).get("open_items", []) if rp0.exists() else [], BASE_WORDS)
    frows = [{"case": "F0", "changed": "nothing (the base copy)", "files_changed": [], "exit": base_code,
              "fail_checks": [], "words": w0, "ok": base_ok and all(w["ok"] for w in w0), "error": None}]
    print(f"F0    {'AS EXPECTED' if frows[0]['ok'] else 'NOT AS EXPECTED'} "
          f"{[(w['clause'], w['lead'], w['found']) for w in w0]}", flush=True)
    for fid, text, edit, expect in clause_cases():
        if only and fid not in only:
            continue
        root = work / fid
        copy_base(base, root)
        edit(root)
        changed = [str(p.relative_to(root)) for p in sorted(root.rglob("*")) if p.is_file()
                   and (base / p.relative_to(root)).exists() and p.read_bytes() != (base / p.relative_to(root)).read_bytes()]
        code, err, checks, dt = run(root, root / "assembly" / "case.log")
        rp = root / "assembly" / "assembly_report.json"
        items = json.loads(rp.read_text(encoding="utf-8")).get("open_items", []) if rp.exists() and err is None else []
        w = words(items, expect)
        fails = sorted({c["check"] for c in checks if c["status"] == "FAIL"})
        ok = err is None and bool(changed) and all(x["ok"] for x in w)
        frows.append({"case": fid, "changed": text, "files_changed": changed, "exit": code, "fail_checks": fails,
                      "words": w, "ok": ok, "error": err})
        print(f"{fid:5s} {'AS EXPECTED' if ok else 'NOT AS EXPECTED'} exit {code} FAIL {fails} "
              f"{[(x['clause'], x['lead'], x['expected'], x['found']) for x in w]}; {dt:.1f} s"
              + (f"; ERROR {err.splitlines()[-1]}" if err else ""), flush=True)
    n_c = sum(r["caught"] for r in rows)
    n_f = sum(r["ok"] for r in frows)
    summary = (f"{n_c}/{len(rows)} mutants caught; {n_f}/{len(frows)} clause cases as expected; "
               f"base copy clean: {base_ok}")
    print(summary)
    lines = [f"# Mutation test of assembly.py ({time.strftime('%Y-%m-%d %H:%M')}): {summary}", "",
             f"Base: {base} (its out/ and spec/ copied fresh for every mutant); work folder {work}.", "",
             "| mutant | targets | planted fault | files changed | exit | result | target FAIL line (first, cut) | other FAIL |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        first = next((v[0] for v in r["target_fail_lines"].values() if v), "-").replace("|", "/")
        lines.append(f"| {r['mutant']} | {', '.join(r['targets'])} | {r['planted']} | {', '.join(r['files_changed'])} | "
                     f"{r['exit']} | {'CAUGHT' if r['caught'] else 'MISSED'} | {first[:160]} | "
                     f"{', '.join(r['other_failing_checks']) or '-'} |")
    lines += ["", "## Clause cases (tester 3, round 3, item 13): a copy with one error, tie or share condition changed "
              "must change the can/cannot word of the clause it feeds, so a typed clause cannot pass", "",
              "| case | changed | files changed | exit | FAIL checks | clause: expected -> found | result |",
              "|---|---|---|---|---|---|---|"]
    for r in frows:
        ws = "; ".join(f"[{w['clause']}] {w['lead']} {w['expected']} -> {w['found']}" for w in r["words"])
        lines.append(f"| {r['case']} | {r['changed']} | {', '.join(r['files_changed']) or '-'} | {r['exit']} | "
                     f"{', '.join(r['fail_checks']) or '-'} | {ws.replace('|', '/')} | "
                     f"{'AS EXPECTED' if r['ok'] else 'NOT AS EXPECTED'} |")
    Path(a.report + ".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    Path(a.report + ".json").write_text(json.dumps({"summary": summary, "base_clean": base_ok, "mutants": rows,
                                                    "clause_cases": frows}, indent=1, ensure_ascii=False),
                                        encoding="utf-8")
    return 0 if base_ok and n_c == len(rows) and n_f == len(frows) else 1


if __name__ == "__main__":
    sys.exit(main())
