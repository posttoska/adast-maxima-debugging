"""Assembly of the Adast Maxima MS 115 PS mechanical model (thread 7, section 05 phase C).

Reads at run time only delivered files: <root>/out/<part>.glb and <part>_anchors.json, <root>/spec/<part>.md
for the six parts, and the block's section 10 (device inventory).  No part coordinate is copied into this file;
the numbers below in REQ are the targets of section 04 (requirements), each with its source.

Writes (all under <root>):
  out/assembly.glb             125 bodies, node names <part>.<body>, millimetres, machine coordinates, Z up, at rest
                               (no root transform: a glTF viewer must scale by 0.001 and turn -90 deg about X)
  out/assembly_anchors.json    the frame passages cut at assembly (DECISION 2) under their requested names
  measure_list.md, sources.md  merged from the six specs (merge_tables.py)
  viewer/index.html            offline viewer (build_viewer.py)
  assembly/assembly_report.json, assembly/assembly_checks.txt   every check line, PASS / FAIL / OPEN

Run:  python stage_1_mechanics/assembly/assembly.py [--root <copy of stage_1_mechanics>] [--section10 <file>]
                                                    [--no-sweep] [--no-viewer]
      or, inside stage_1_mechanics or any copy of it:  python assembly/assembly.py     [--project <folder>]
The project folder (it holds preparatory_data_analysis/ and the block's section 10) comes from
merge_tables.find_project(): --project, else walking up from this script, from --root and from the working folder,
else the fixed project path; when none holds it the run stops with one line.  Section 10 is
<project>/static_dynamic_memory/blocks/generation_001/sections/10_safety_devices_and_sensors.md unless --section10
names another file.  The project used is recorded in assembly_report.json (not in assembly_checks.txt).
Exit 0 = no FAIL (OPEN lines are known conflicts settled by a meta orc decision and listed as open items).
"""
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as m3

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PARTS = ("frame", "knife", "clamp", "backgauge", "housing", "safety_sensors")
import merge_tables  # noqa: E402  (find_project, set_project; the merge itself runs in main)
EPS = 0.01          # mm3: an intersection above this is an overlap
TOL_DT = 10.0       # mm: tolerance where a D or T source gives the number (section 04)
TOL_SIDE = 1.0      # mm: a body against the anchor that stands for it (beam vs clamp face, comb vs backgauge face,
                    #     knife body vs knife.edge.rest)
TOL_BOTTOM = 0.05   # mm: knife edge at the bottom of the crank model vs the knife.edge.bottom anchor
TOL_STROKE = 0.5    # mm: knife stroke of the crank model vs the range of the knife.edge.rest anchor
TIE = 0.05          # mm: bodies this close to an extreme X are all named as that end
LEGEND = (f"# Tolerances: a D or T target is checked to +-{TOL_DT:g} mm (section 04) unless its line prints another "
          "bound; P, E and W values carry their own stated error (check EW: a check that reads one prints it with its "
          "class and error from the anchors file, and the open item 'checks on estimated values' names it in that "
          "check's clause). Classes: D drawing, T table or text, P photo proportion, E estimated, W web.")
# the abbreviations of the check lines, written out once below LEGEND (user's global rule; critic g11 F-g11-1); the
# spec-local keys in quoted sources are the specs' own, resolved to files in sources.md, not guessed
ABBREV = ("# Abbreviations: GLB (binary GL Transmission Format, GL = Graphics Library), JSON (JavaScript Object "
          "Notation), MB (megabytes), ID (identifier), mm (millimetres), mm3 (cubic millimetres), deg (degrees), vs "
          "(versus), trans and rot (translation and rotation, motion types of the anchors files), p. (page), Fig. (figure), OM (operating manual of this variant), OM/, DOC/, PH/ and ART/ (the "
          "folders of the operating manual, the other documents, the machine photos and the memory block's "
          "artifacts, as the header of sources.md writes them out), DTPEW (the five classes D, T, P, "
          "E, W), DECISION n (a ruling of the meta orchestrator of the workflow). [1] to [12] are the checks of "
          "section 04, [8e] (envelope boxes) and [9x] (the other motions) belong to checks 8 and 9; [B1], [B2], [B3], "
          "[D2], [N], [EW] and [V] are the script's own checks, EW standing for values of class E or W (P counts with "
          "them). M7, G3a, SS5 and the like are rows of a spec's measure table (measure_list.md lists them); Q1, S28, "
          "Y01, OA1 and the like are device designations of the electrical legend (wiring set 568-70.9001) and of the "
          "hydraulic parts list. Quoted sources use the specs' own source keys, for example P6, P7 or P36 (OM page 6, "
          "7 or 36), P37f (OM "
          "p.37, Fig. 7.1 front view close-up), F412, F63 and F81 (OM Figs. 4.1.2, 6.3 and 8.1), PLAN (OM Fig. 4.2.2, "
          "the foundation plan), CERT (certificate of this machine), OLD-I (Fig. I of "
          "the Russian manual of the older relay variant), PH-cross1 (one machine photo): a key means what its own "
          "spec says, and each spec's keys with the files they resolve to are listed in sources.md, section 'Source "
          "keys of each spec and the files they resolve to'.")

# Section 04 targets (requirements, not part data).  D drawing, T table or text, E estimated.
REQ = {
    "x_min": (-1307.0, "D", "OM Fig. 4.2.2, 20261115_011021"), "x_max": (1553.0, "D", "OM Fig. 4.2.2, 20261115_011021"),
    "x_body_left": (-1250.0, "D", "OM Fig. 4.2.2, 20261115_011021: body lines -1250 / +1400 (section 05 shared values)"),
    "y_span": (2795.0, "D", "OM Fig. 4.2.2, 20261115_011021"), "z_top": (1535.0, "T", "OM p.7, 20261114_215113"),
    "table_top": (885.0, "E", "OM p.19 elevation 20261115_010448, error 100; W 900"),
    "table_w": (1150.0, "T", "OM p.7; Fig. 4.1.2 20261115_005319"), "table_l": (2630.0, "D", "Fig. 4.1.2 20261115_005319"),
    "knife_len_min": (1150.0, "T", "cutting width, OM p.7"),
    "pile": (130.0, "T", "OM p.7 clamp lift; certificate 20261113_195028"),
    "bg_front": (25.0, "T", "OM p.7"), "bg_rear": (1150.0, "T", "OM p.7 (certificate 1160)"),
    "clamp_stroke": (130.0, "T", "OM p.7"), "cut_depth": ((0.1, 0.2), "T", "OM p.21, 20261115_012035"),
    "bolt_x": ((-790.0, 932.0), "D", "Fig. 4.2.2"), "rear_foot_d": (165.0, "D", "Fig. 4.2.2"),
    "rear_foot_behind": (1130.0, "D", "Fig. 4.2.2"), "pad": ((450.0, 220.0, 230.0), "D", "Fig. 4.2.2"),
}
DEVICE_KINDS = ("button", "sensor", "magnet", "clutch", "valve", "brake", "motor", "switch")
HOST_LETTER = {"F": "frame", "K": "knife", "C": "clamp", "B": "backgauge", "H": "housing"}
# knife moving bodies over one crank turn (knife anchors: knife.edge.rest "knife and holder", holder.pin.rest
# "moves with the holder", conrod.mid.rest planar, crank.pin.tdc circle; same set as parts/knife/check_spec.py)
KNIFE_TRANSLATE = ("knife.knife", "knife.holder", "knife.holder_pin")
KNIFE_CONROD, KNIFE_CRANKPIN = "knife.conrod", "knife.crank_pin"
KNIFE_CRANK = ("crank.centre", "crank.pin.tdc", "holder.pin.rest")  # knife anchors the crank model is built from
KNIFE_LOCK = ("knife.lock_pin_1", "knife.y01_tail")       # anchor lock.pin_1: "y01_tail with the flag moves with it"
CONTACT_KNIFE_STICK = ("knife.knife", "frame.cutting_stick")  # check 6: the edge enters the stick 0,1-0,2 at the bottom
# DECISION 2 asks whether a cut removes material that the frame's sources show as solid (then DISAGREE to the meta orc).
# Judgement of actor t7, from the requesting specs' open items and the frame rows (printed beside it at run time).
JUDGE = {
    "joint.passage.clamp_brake.crossbar": "no DISAGREE: P36 7.4 names an opening in the frame under cover 11 "
        "(clamp open item 1); frame.crossbar is itself an E placeholder sized to photos (frame M7)",
    "joint.passage.clamp_tie.support_left": "no DISAGREE: no mesh passes it; it joins the envelope chain "
        "pull_rod_left -> tie -> levers_tie; its only source is OLD-I (older relay variant, clamp M3); the support "
        "wall is an E placeholder (outline continued upward, frame M18), so no source shows it solid",
    "joint.bore.spindle.base_front": "no DISAGREE: F81 shows the spindle end held by a double nut in a wall "
        "(backgauge open items); frame.base_front is an E placeholder plate (frame M13)",
    "joint.slot.front_extension": "no DISAGREE: F63 shows a slotted table plate with the neck through it; the frame's "
        "slot start Y 420 came from the losing reading of photo 150809 (backgauge conflict 1); no photo shows solid table there",
}


# ---------------------------------------------------------------------------------------------- helpers
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def man(mesh):
    m = m3.Manifold(m3.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                            tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))
    return m


def bb(m):
    b = m.bounding_box()
    return np.array(b[:3], float), np.array(b[3:], float)


def touch(a, b, gap=0.0):
    return not (np.any(a[1] < b[0] - gap) or np.any(b[1] < a[0] - gap))


def box_man(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def err3(e):
    if isinstance(e, dict):
        return np.array([float(e.get(k, max(e.values()))) for k in "xyz"])
    if isinstance(e, (list, tuple)):
        return np.array([float(v) for v in e][:3])
    return np.array([float(e)] * 3) if e is not None else np.zeros(3)


def mat_t(t):
    m = np.zeros((3, 4))
    m[:, :3] = np.eye(3)
    m[:, 3] = t
    return m


def mat_rot(axis, pivot, deg):
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    th = math.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    Rm = np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K
    p = np.asarray(pivot, float)
    m = np.zeros((3, 4))
    m[:, :3] = Rm
    m[:, 3] = p - Rm @ p
    return m


def compose(a, b):
    """a after b, both 3x4."""
    A, B = np.vstack([a, [0, 0, 0, 1]]), np.vstack([b, [0, 0, 0, 1]])
    return (A @ B)[:3]


def num(s):
    return float(s.replace(",", ".").replace("−", "-").replace("–", "-"))


def norm_txt(s):
    return s.replace("−", "-").replace("–", "-").replace("…", "..").replace("+", "")


def ranges(text):
    """'X a..b Y c..d Z e..f' (any separators) -> {axis: (lo, hi)}"""
    out = {}
    for ax, a, b in re.findall(r"\b([XYZxyz])\s*=?\s*(-?\d+(?:[.,]\d+)?)\s*\.\.\s*(-?\d+(?:[.,]\d+)?)", norm_txt(text)):
        out.setdefault(ax.lower(), (num(a), num(b)))
    return out


def md_tables(text):
    """all markdown tables: list of (first line number, header cells, rows of cells)"""
    lines, out, i = text.splitlines(), [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            hdr = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            out.append((i + 1, hdr, rows))
            i = j
        else:
            i += 1
    return out


class Report:
    def __init__(self):
        self.checks, self.lines = [], []

    def add(self, cid, status, text, data=None):
        self.checks.append({"check": cid, "status": status, "text": text, **({"data": data} if data else {})})
        line = f"{status:4s} [{cid}] {text}"
        self.lines.append(line)
        print(line, flush=True)

    def note(self, text):
        self.lines.append("     " + text)
        print("     " + text, flush=True)


class Reads:
    """critic g9: what each check's code reads while it runs (from start(cid) to the next start or stop), so that check
    EW can FAIL a check that reads a P, E or W value it does not declare in its data 'reads'"""
    def __init__(self):
        self.cid, self.seen = None, {}

    def start(self, cid):
        self.cid = cid
        self.seen.setdefault(cid, set())

    def stop(self):
        self.cid = None


class Noted(dict):
    """one anchor of a part (name given: any field read notes (part, name)), or a part's meta (name None: each number
    read notes (part, key)); notes go to the Reads only while a check runs"""
    def __init__(self, d, rec, part, name=None):
        super().__init__(d)
        self._rec, self._part, self._name = rec, part, name

    def _note(self, k):
        r = self._rec
        if r.cid is None:
            return
        if self._name is not None:
            r.seen[r.cid].add((self._part, self._name))
        elif isinstance(super().get(k), (int, float)) and not str(k).endswith("_error"):
            r.seen[r.cid].add((self._part, k))

    def __getitem__(self, k):
        self._note(k)
        return super().__getitem__(k)

    def get(self, k, default=None):
        self._note(k)
        return super().get(k, default)


class Charged(dict):
    """the motion model (critic g10): a check that uses one of its motions (mm['knife'] ...) is charged with the
    anchors that motion was built from, as the recorder saw them in the window mm.<motion> (the pedal is built in the
    clamp window, the handwheel in the backgauge window); outside a check nothing is charged"""
    WINDOW = {"pedal": "clamp", "handwheel": "backgauge"}

    def __init__(self, d, rec):
        super().__init__(d)
        self._rec = rec

    def __getitem__(self, k):
        r = self._rec
        if r.cid is not None and not r.cid.startswith("mm."):
            r.seen[r.cid].update(r.seen.get(f"mm.{self.WINDOW.get(k, k)}", ()))
        return super().__getitem__(k)


# ---------------------------------------------------------------------------------------------- loading
def load(root):
    out = root / "out"
    bodies, part_of, anchors, meta = {}, {}, {}, {}
    for p in PARTS:
        sc = trimesh.load(out / f"{p}.glb", force="scene")
        for node in sc.graph.nodes_geometry:
            tf, g = sc.graph[node]
            mesh = sc.geometry[g].copy()
            mesh.apply_transform(tf)
            name = node if node.startswith(p + ".") else f"{p}.{node}"
            bodies[name], part_of[name] = mesh, p
        d = json.loads((out / f"{p}_anchors.json").read_text(encoding="utf-8"))
        anchors[p], meta[p] = d["anchors"], d.get("meta", {})
    return bodies, part_of, anchors, meta


def glb_mesh_nodes(path):
    """names of the nodes with a mesh, read from the GLB's own JSON chunk (not through trimesh)"""
    b = Path(path).read_bytes()
    n = int.from_bytes(b[12:16], "little")
    js = json.loads(b[20:20 + n].decode("utf-8"))
    return [nd.get("name", "") for nd in js.get("nodes", []) if "mesh" in nd]


def color_of(mesh):
    try:
        c = mesh.visual.main_color
        return [int(v) for v in c[:4]]
    except Exception:
        try:
            return [int(v) for v in mesh.visual.material.main_color[:4]]
        except Exception:
            return [180, 180, 180, 255]


# ---------------------------------------------------------------------------------------------- passages (DECISION 2)
def passages(anchors):
    res = []
    for p, an in anchors.items():
        for n, a in an.items():
            if isinstance(a, dict) and a.get("cut_at") == "assembly":
                box = np.array(a["passage"], float)
                if a.get("bore_d"):
                    ax = int(np.argmax(np.abs(a["axis"])))
                    h = box[ax, 1] - box[ax, 0]
                    cyl = m3.Manifold.cylinder(h, a["bore_d"] / 2, a["bore_d"] / 2, 64)
                    rot = {0: [0, 90, 0], 1: [-90, 0, 0], 2: [0, 0, 0]}[ax]
                    c = np.array(a["xyz"], float)
                    start = c.copy()
                    start[ax] = box[ax, 0]
                    shape, kind = cyl.rotate(rot).translate(start.tolist()), f"bore d{a['bore_d']:g} along {'XYZ'[ax]}"
                else:
                    shape, kind = box_man(box[:, 0], box[:, 1]), "box"
                res.append({"name": n, "part": p, "anchor": a, "box": box, "shape": shape, "kind": kind,
                            "cut_from": a["cut_from"]})
    return res


# ---------------------------------------------------------------------------------------------- joints and excuses
def joint_boxes(anchors):
    """name -> (parts, lo, hi, how): every anchor name published by two or more parts (assembly anchors included)"""
    seen = {}
    for p, an in anchors.items():
        for n, a in an.items():
            # the assembly publishes the frame side of the passages it cut (DECISION 2)
            seen.setdefault(n, []).append(("frame" if p == "assembly" else p, a))
    res = {}
    for n, lst in seen.items():
        if len(lst) < 2:
            continue
        parts = tuple(sorted({p for p, _ in lst}))
        if len(parts) < 2:
            continue
        lo = hi = None
        how = None
        for _, a in lst:
            if not isinstance(a, dict):
                continue
            for key in ("passage", "zone"):
                if key in a:
                    b = np.array(a[key], float)
                    lo = b[:, 0] if lo is None else np.minimum(lo, b[:, 0])
                    hi = b[:, 1] if hi is None else np.maximum(hi, b[:, 1])
                    how = key
        if lo is None:
            e = np.max([err3(a.get("error_mm")) for _, a in lst if isinstance(a, dict)], axis=0)
            c = np.array(lst[0][1]["xyz"], float)
            lo, hi, how = c - e, c + e, "point +- error"
        res[n] = (parts, lo, hi, how)
    return res


def pocket_boxes(anchors, meta):
    """safety_sensors bodies that list an excused overlap: (body, other body) -> zone of the host anchor"""
    res = {}
    for bn, info in meta["safety_sensors"].get("bodies", {}).items():
        for other in info.get("excused_overlap_with") or []:
            host = (info.get("host_anchor") or "").split(" ")[0]
            for p, an in anchors.items():
                a = an.get(host)
                if isinstance(a, dict) and "zone" in a:
                    z = np.array(a["zone"], float)
                    name = bn if bn.startswith("safety_sensors.") else "safety_sensors." + bn
                    res[(name, other)] = (z[:, 0], z[:, 1], f"{host} zone ({p})", info.get("group"))
    return res


# ---------------------------------------------------------------------------------------------- motion model
def motion_model(anchors, meta, bodies, rec=None):
    """returns dict of motions, each: bodies and a function state -> 3x4 transform per body. With a recorder (critic
    g10), each motion is built in its own window mm.<motion>, so that a check that later uses that motion is charged
    with the anchors it was built from (Charged)"""
    mark = rec.start if rec else (lambda cid: None)
    mark("mm.knife")
    ka = anchors["knife"]
    C = np.array(ka["crank.centre"]["xyz"], float)
    P0 = np.array(ka["crank.pin.tdc"]["xyz"], float)
    H0 = np.array(ka["holder.pin.rest"]["xyz"], float)
    r = math.hypot(P0[0] - C[0], P0[2] - C[2])
    L = math.hypot(H0[0] - P0[0], H0[2] - P0[2])
    th0 = math.atan2(P0[2] - C[2], P0[0] - C[0])

    def knife_pose(th):
        P = np.array([C[0] + r * math.cos(th), P0[1], C[2] + r * math.sin(th)])
        Hz = P[2] + math.sqrt(L * L - (H0[0] - P[0]) ** 2)
        dz = H0[2] - Hz
        phi0 = math.atan2(H0[2] - P0[2], H0[0] - P0[0])
        phi = math.atan2(Hz - P[2], H0[0] - P[0])
        rod = compose(mat_t(P), compose(mat_rot([0, -1, 0], [0, 0, 0], math.degrees(phi - phi0)), mat_t(-P0)))
        tf = {b: mat_t([0, 0, -dz]) for b in KNIFE_TRANSLATE}
        tf[KNIFE_CONROD] = rod
        tf[KNIFE_CRANKPIN] = mat_t(P - P0)
        return tf, dz

    # check the rotation sense of mat_rot about -Y: phi measured from +X toward +Z
    t = mat_rot([0, -1, 0], [0, 0, 0], 90.0)
    assert np.allclose(t[:, :3] @ [1, 0, 0], [0, 0, 1], atol=1e-9)

    mark("mm.clamp")        # the clamp beam, piston, riders and pedal
    cm, bm, sm = meta["clamp"], meta["backgauge"], meta["safety_sensors"]
    beam = [b if b.startswith("clamp.") else "clamp." + b for b, i in cm["bodies"].items() if i.get("group") == "beam"]
    piston = [b if b.startswith("clamp.") else "clamp." + b for b, i in cm["bodies"].items() if i.get("group") == "piston"]
    pedal = [b if b.startswith("clamp.") else "clamp." + b for b, i in cm["bodies"].items() if i.get("group") == "pedal"]
    riders = [b if b.startswith("safety_sensors.") else "safety_sensors." + b
              for b, i in sm["bodies"].items() if i.get("group") == "clamp.beam"]
    cf = anchors["clamp"]["clamp.face"]["motion"]
    c_axis, c_range = np.array(cf["axis"], float), cf["range"]
    g = cm["groups"]
    mp = re.search(r"about \(([^)]*)\) through \(([^)]*)\) by ([\d.]+)\.\.([\d.]+)", g.get("pedal", ""))
    pedal_axis = [float(v) for v in mp.group(1).split(",")] if mp else [1, 0, 0]
    pedal_piv = [float(v) for v in mp.group(2).split(",")] if mp else [0, 0, 0]
    pedal_rng = (float(mp.group(3)), float(mp.group(4))) if mp else (0, 0)
    mpist = re.search(r"along \(([^)]*)\)", g.get("piston", ""))
    p_axis = np.array([float(v) for v in mpist.group(1).split(",")]) if mpist else -c_axis
    mark("mm.backgauge")    # the backgauge carriage and its handwheel
    moving = [b if b.startswith("backgauge.") else "backgauge." + b for b, i in bm["bodies"].items() if i.get("group") == "moving"]
    hw = [b if b.startswith("backgauge.") else "backgauge." + b for b, i in bm["bodies"].items() if i.get("group") == "handwheel"]
    bf = anchors["backgauge"]["backgauge.face"]["motion"]
    b_axis, b_range = np.array(bf["axis"], float), bf["range"]
    mh = re.search(r"push in ([\d.]+) along -X", bm["groups"].get("handwheel", ""))
    hw_push = float(mh.group(1)) if mh else 0.0
    mark("mm.lock")
    lk = ka["lock.pin_1"]["motion"]
    mark("mm.door")
    door = anchors["housing"].get("right_front_cover.pivot", {})

    return {
        "knife": {"pose": knife_pose, "th0": th0, "r": r, "L": L, "C": C, "P0": P0, "H0": H0},
        "clamp": {"beam": beam, "piston": piston, "riders": riders, "axis": c_axis, "range": c_range, "p_axis": p_axis},
        "pedal": {"bodies": pedal, "axis": pedal_axis, "pivot": pedal_piv, "range": pedal_rng},
        "backgauge": {"moving": moving, "axis": b_axis, "range": b_range},
        "handwheel": {"bodies": hw, "push": hw_push},
        "lock": {"bodies": [b for b in KNIFE_LOCK if b in bodies], "axis": lk["axis"], "range": lk["range"]},
        "door": door,
    }


def clamp_tf(mm, s):
    c = mm["clamp"]
    tf = {b: mat_t(c["axis"] * s) for b in c["beam"] + c["riders"]}
    tf.update({b: mat_t(c["p_axis"] * s) for b in c["piston"]})
    return tf


def bg_tf(mm, d):
    return {b: mat_t(mm["backgauge"]["axis"] * d) for b in mm["backgauge"]["moving"]}


# ---------------------------------------------------------------------------------------------- the checker of overlaps
class Space:
    def __init__(self, mans, part_of, jbox, pockets, stick_box):
        self.m, self.part_of, self.jbox, self.pockets = mans, part_of, jbox, pockets
        self.rest_bb = {n: bb(m) for n, m in mans.items()}
        self.stick_box = stick_box     # the only place where the knife may enter frame.cutting_stick
        self.cache = {}

    def placed(self, n, tf):
        if tf is None:
            return self.m[n], self.rest_bb[n]
        key = (n, tf.tobytes())
        if key not in self.cache:
            mm = self.m[n].transform(tf)
            self.cache[key] = (mm, bb(mm))
            if len(self.cache) > 4000:
                self.cache.clear()
        return self.cache[key]

    def excuse(self, a, b, inter, tfa, tfb):
        """volume of inter that lies outside every box that may excuse it, with the names used"""
        pa, pb = self.part_of[a], self.part_of[b]
        boxes, names = [], []
        for n, (parts, lo, hi, how) in self.jbox.items():
            if pa in parts and pb in parts and n != "interface.clamp.comb_interleave":
                boxes.append(box_man(lo - 1e-3, hi + 1e-3))
                names.append(f"{n} ({how})")
        for (s, o), (lo, hi, why, grp) in self.pockets.items():
            if {s, o} == {a, b}:
                t = tfa if s == a else tfb
                bx = box_man(lo, hi)
                boxes.append(bx.transform(t) if t is not None else bx)
                names.append(f"pocket {why}")
        for lo, hi, nm in getattr(self, "extra", {}).get(frozenset((a, b)), []):
            boxes.append(box_man(lo, hi))
            names.append(nm)
        if set((a, b)) == set(CONTACT_KNIFE_STICK) and self.stick_box is not None:
            lo, hi = self.stick_box
            boxes.append(box_man(lo, hi))
            names.append(f"contact.knife_edge.cutting_stick (x {lo[0]:.1f}..{hi[0]:.1f} y {lo[1]:.2f}..{hi[1]:.2f} "
                         f"z {lo[2]:.2f}..{hi[2]:.2f}; check 6)")
        if not boxes:
            return inter.volume(), []
        u = boxes[0]
        for x in boxes[1:]:
            u = u + x
        out = (inter - u).volume()
        used = [nm for bx, nm in zip(boxes, names) if (inter ^ bx).volume() > EPS]
        return out, used

    def overlaps(self, tfs, moving=None, internal_rest=None):
        """overlaps in one state; tfs: body -> 3x4 (bodies not in tfs stay at rest).
        moving None: every cross-part pair (check 8).  moving set: every pair with a moving body whose transforms
        differ (relative motion), cross-part and same-part; a same-part pair that already overlaps at rest
        (internal_rest: a pin in its eye) is a part-internal joint and is skipped.
        returns list of (a, b, vol, outside, used, bounds)"""
        names = list(self.m)
        if moving is None:
            pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:] if self.part_of[a] != self.part_of[b]]
        else:
            pairs, seen = [], set()
            for a in moving:
                for b in names:
                    if b == a or (b, a) in seen:
                        continue
                    seen.add((a, b))
                    ta, tb = tfs.get(a), tfs.get(b)
                    if (ta is None and tb is None) or (ta is not None and tb is not None and np.allclose(ta, tb)):
                        continue
                    if self.part_of[a] == self.part_of[b] and internal_rest and frozenset((a, b)) in internal_rest:
                        continue
                    pairs.append((a, b))
        placed = {}
        res = []
        for a, b in pairs:
            for n in (a, b):
                if n not in placed:
                    placed[n] = self.placed(n, tfs.get(n))
            if True:
                (ma, ba), (mb, bb_) = placed[a], placed[b]
                if not touch(ba, bb_):
                    continue
                inter = ma ^ mb
                v = inter.volume()
                if v <= EPS:
                    continue
                out, used = self.excuse(a, b, inter, tfs.get(a), tfs.get(b))
                res.append((a, b, v, out, used, [np.round(x, 1).tolist() for x in bb(inter)]))
        return res


# ---------------------------------------------------------------------------------------------- spec outer sizes (check 7)
def spec_outer(root, anchors):
    res = {}
    for p in PARTS:
        txt = (root / "spec" / f"{p}.md").read_text(encoding="utf-8")
        lo, hi, how = None, None, None

        def grow(r):
            nonlocal lo, hi
            if not all(k in r for k in "xyz"):
                return False
            a = np.array([min(r[k]) for k in "xyz"])
            b = np.array([max(r[k]) for k in "xyz"])
            lo = a if lo is None else np.minimum(lo, a)
            hi = b if hi is None else np.maximum(hi, b)
            return True

        m = re.search(r"<!-- OUTER START -->(.*?)<!-- OUTER END -->", txt, re.S)
        line = next((ln for ln in txt.splitlines() if "Bounding box of all" in ln), None)
        if m:
            rows = {r[0].lower(): (num(r[1]), num(r[2])) for _, h, rs in md_tables(m.group(1)) for r in rs}
            grow(rows)
            how = "OUTER block"
        elif line:
            grow(ranges(line))
            how = "line 'Bounding box of all ...'"
        elif p == "safety_sensors":
            allan = {n: a for an in anchors.values() for n, a in an.items()}
            n_rows = 0
            for _, h, rs in md_tables(txt):
                hl = [c.lower() for c in h]
                if "host anchor" in hl and any(c.startswith("solid") for c in hl):
                    ih, isol = hl.index("host anchor"), next(i for i, c in enumerate(hl) if c.startswith("solid"))
                    for r in rs:
                        host = allan.get(r[ih].split()[0])
                        geo = norm_txt(r[isol])
                        if host is None:
                            continue
                        c = np.array(host["xyz"], float)
                        if geo.startswith("box"):
                            rr = ranges(geo)
                            a = c + [min(rr[k]) for k in "xyz"]
                            b = c + [max(rr[k]) for k in "xyz"]
                        elif geo.startswith("cyl"):
                            ax = re.search(r"ax=([xyz])", geo).group(1)
                            d = num(re.search(r"\bd=(-?[\d.,]+)", geo).group(1))
                            s0, s1 = [num(v) for v in re.search(r"\bs=(-?[\d.,]+)\.\.(-?[\d.,]+)", geo).groups()]
                            mc = re.search(r"\bc=(-?[\d.,]+),(-?[\d.,]+)", geo)
                            off = [num(v) for v in mc.groups()] if mc else [0.0, 0.0]
                            k = "xyz".index(ax)
                            others = [i for i in range(3) if i != k]
                            a, b = c.copy(), c.copy()
                            a[k], b[k] = c[k] + s0, c[k] + s1
                            for j, i in enumerate(others):
                                a[i], b[i] = c[i] + off[j] - d / 2, c[i] + off[j] + d / 2
                        else:
                            continue
                        n_rows += 1
                        lo = a if lo is None else np.minimum(lo, a)
                        hi = b if hi is None else np.maximum(hi, b)
            how = f"Bodies table: {n_rows} rows placed on their host anchors"
        else:
            n_rows = 0
            for _, h, rs in md_tables(txt):
                hl = [c.lower() for c in h]
                col = next((i for i, c in enumerate(hl) if c in ("outer size", "bounds")), None)
                if col is None or not ("id" in hl):
                    continue
                for r in rs:
                    if col < len(r) and grow(ranges(r[col])):
                        n_rows += 1
            how = f"union of {n_rows} component rows"
        res[p] = (lo, hi, how)
    return res


# ---------------------------------------------------------------------------------------------- section 10 (check 10)
def cabinet_alternatives(root, mans, part_of, meta, x_right):
    """DECISION 3 numbers for check 1, all from the delivered files: the built option (meta cabinet_option), the
    machine without the cabinet and the devices mounted on it, and the other option read from spec/housing.md
    (cabinet row / M9: 'A: X a..b'), the devices moved with the cabinet."""
    cab_lo, cab_hi = bb(mans["housing.cabinet"])
    sb = meta.get("safety_sensors", {}).get("bodies", {})
    hosted = []
    for n, info in sb.items():
        n = n if n.startswith("safety_sensors.") else "safety_sensors." + n
        if n in mans and "(housing)" in str(info.get("host_anchor", "")):
            blo, bhi = bb(mans[n])
            if touch((blo, bhi), (cab_lo, cab_hi), gap=1.0):
                hosted.append(n)
    group = ["housing.cabinet"] + sorted(hosted)
    rest = {n: bb(mans[n])[0][0] for n in mans if n not in group}
    rest_body = min(rest, key=rest.get)
    opt = meta.get("housing", {}).get("cabinet_option", "?")
    other = "A" if opt == "B" else "B"
    txt = (root / "spec" / "housing.md").read_text(encoding="utf-8")
    m = re.search(r"\b" + other + r"(?: loses)?:\s*X\s*(-?\d+(?:[.,]\d+)?)\s*\.\.\s*(-?\d+(?:[.,]\d+)?)", norm_txt(txt))
    dev_lo = min((bb(mans[n])[0][0] for n in hosted), default=cab_lo[0])
    rest_names = ", ".join(sorted(n for n, v in rest.items() if v <= rest[rest_body] + TIE))   # all bodies at that end
    data = {"built_option": opt, "built_cabinet_x": [round(cab_lo[0], 1), round(cab_hi[0], 1)],
            "built_left": round(min(cab_lo[0], dev_lo), 1), "built_right": round(x_right, 1),
            "built_span": round(x_right - min(cab_lo[0], dev_lo), 1),
            "devices_on_cabinet": [n.split(".", 1)[1] for n in hosted],
            "without_cabinet_left": round(rest[rest_body], 1), "without_cabinet_left_body": rest_names,
            "without_cabinet_span": round(x_right - rest[rest_body], 1)}
    s = (f"{opt} (built): cabinet X {cab_lo[0]:.1f}..{cab_hi[0]:.1f}, span {x_right - min(cab_lo[0], dev_lo):.1f}; "
         f"without the cabinet and the {len(hosted)} devices on it ({', '.join(d.split('.', 1)[1] for d in hosted)}): "
         f"left end {rest[rest_body]:.1f} ({rest_names}), span {x_right - rest[rest_body]:.1f}")
    if m:
        a_lo, a_hi = num(m.group(1)), num(m.group(2))
        shift = a_lo - cab_lo[0]
        a_left = min(a_lo, dev_lo + shift, rest[rest_body])
        data.update({"other_option": other, "other_cabinet_x": [a_lo, a_hi], "other_left": round(a_left, 1),
                     "other_span": round(x_right - a_left, 1)})
        s += (f"; {other} (spec/housing.md): cabinet X {a_lo:.0f}..{a_hi:.0f}, devices moved with it by {shift:+.1f}: "
              f"left end {a_left:.1f}, span {x_right - a_left:.1f}")
    else:
        s += f"; option {other}: no 'X a..b' range found in spec/housing.md"
    return {"text": s, "data": data}


def section10_expect(path):
    txt = path.read_text(encoding="utf-8")
    exp = {}
    for _, h, rs in md_tables(txt):
        if not h or not h[0].lower().startswith("desig"):
            continue
        for r in rs:
            desigs = [d.strip() for d in r[0].split(",") if d.strip()]
            cell = r[-1]
            kinds = re.findall(r"\b([a-z]+)\.", cell)
            tail = re.search(r",\s*([FKCBH])\s*$", cell)
            for d in desigs:
                mk = re.search(r"\b([a-z]+)\." + re.escape(d) + r"\b", cell)
                kind = mk.group(1) if mk else (kinds[0] if kinds else None)
                mh = re.search(re.escape(d) + r"\s+([FKCBH])\b", cell)
                host = mh.group(1) if mh else (tail.group(1) if tail else None)
                exp[d] = (kind, HOST_LETTER.get(host))
    return exp


# ---------------------------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(HERE.parent))
    ap.add_argument("--project", default=None, help="the project folder; default: merge_tables.find_project()")
    ap.add_argument("--section10", default=None, help="default: <project>/" + merge_tables.SECTION10_REL)
    ap.add_argument("--no-sweep", action="store_true")
    ap.add_argument("--no-viewer", action="store_true")
    ap.add_argument("--no-merge", action="store_true", help="skip measure_list.md, sources.md and check 11")
    ap.add_argument("--steps", type=int, default=180, help="crank steps per turn")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    project, proj_how = merge_tables.find_project(args.project, root)
    if project is None:
        print(f"assembly.py: stop: no project folder ({proj_how}); pass --project <the folder that holds "
              f"preparatory_data_analysis/ and {merge_tables.SECTION10_REL}>", file=sys.stderr)
        return 2
    merge_tables.set_project(project)
    if args.section10 is None:
        args.section10 = str(project / merge_tables.SECTION10_REL)
    out = root / "out"
    rep = Report()
    inputs = {}
    for p in PARTS:
        for f in (out / f"{p}.glb", out / f"{p}_anchors.json", root / "spec" / f"{p}.md"):
            inputs[str(f.relative_to(root)).replace("\\", "/")] = sha(f)
    inputs["section10"] = sha(args.section10)

    bodies, part_of, anchors, meta = load(root)
    # every anchor and meta number is read through Noted, so check EW sees what checks 1-6 and 12 really read
    rec = Reads()
    anchors = {p: {n: Noted(a, rec, p, n) if isinstance(a, dict) else a for n, a in an.items()}
               for p, an in anchors.items()}
    meta = {p: Noted(m, rec, p) for p, m in meta.items()}
    counts = {p: sum(1 for v in part_of.values() if v == p) for p in PARTS}
    # B1 against the GLB files themselves: the mesh nodes their JSON chunk names, each once, all loaded under that name
    bad1 = []
    for p in PARTS:
        raw = [x[len(p) + 1:] if x.startswith(p + ".") else x for x in glb_mesh_nodes(out / f"{p}.glb")]
        got = sorted(n.split(".", 1)[1] for n in part_of if part_of[n] == p)
        dup = sorted({x for x in raw if raw.count(x) > 1})
        if not raw or dup or sorted(raw) != got:
            bad1.append(f"{p}: file names {len(raw)} mesh nodes" + (f", twice: {dup}" if dup else "")
                        + f", loaded {len(got)}" + (f"; only in the file: {sorted(set(raw) - set(got))}, only loaded: "
                                                     f"{sorted(set(got) - set(raw))}" if set(raw) != set(got) else ""))
    rep.add("B1", "PASS" if not bad1 else "FAIL",
            f"loaded {len(bodies)} bodies: " + ", ".join(f"{p} {n}" for p, n in counts.items())
            + "; each part's GLB JSON names the same mesh nodes, each once" + ("; " + "; ".join(bad1) if bad1 else ""))

    # ---- manifolds; watertight
    mans, bad = {}, []
    for n, mesh in bodies.items():
        m = man(mesh)
        if not str(m.status()).endswith("NoError") or m.volume() <= 0:
            bad.append(n)
        mans[n] = m
    rep.add("B2", "PASS" if not bad else "FAIL", f"every body is a closed solid with volume > 0 (manifold3d): "
            f"{len(mans) - len(bad)}/{len(mans)}" + (f"; not closed: {bad}" if bad else ""))
    if bad:      # cuts, volumes, overlaps and sweeps need closed solids: stop here with the report written
        rep.note("stopped after B2: the later checks need every body closed")
        return finish(root, rep, inputs, [])

    # ---- DECISION 2 passages: cut from the named frame bodies
    pas = passages(anchors)
    cut_info = {}
    for ps in pas:
        tgt = ps["cut_from"]
        if tgt not in mans:
            rep.add("D2", "FAIL", f"passage {ps['name']} ({ps['part']}): cut_from {tgt} is not a body of out/frame.glb")
            continue
        before = mans[tgt]
        removed = (before ^ ps["shape"]).volume()
        mans[tgt] = before - ps["shape"]
        left = (mans[tgt] ^ ps["shape"]).volume()
        cut_info[ps["name"]] = {"removed_mm3": round(removed, 1), "left_mm3": round(left, 3)}
        rep.add("D2", "PASS" if removed > EPS and left <= EPS else "FAIL",
                f"passage {ps['name']} ({ps['part']}): {ps['kind']} x {ps['box'][0].tolist()} y {ps['box'][1].tolist()} "
                f"z {ps['box'][2].tolist()} cut from {tgt}: removed {removed:.1f} mm3, frame material left in it {left:.3f} mm3")
    if len(pas) != 4:
        rep.add("D2", "FAIL", f"expected the 4 passages of DECISION 2 (2 clamp, 2 backgauge), found {len(pas)}")

    # ---- assembly anchors (frame side of the cut passages)
    an_out = {"meta": {"part": "assembly", "units": "mm", "coordinates": meta["frame"].get("coordinates"),
                       "note": "frame passages cut at assembly (DECISION 2, signals/DECISION_2_passages_at_assembly.txt); "
                               "each is named as the requesting part names it, at the same xyz",
                       "script": "stage_1_mechanics/assembly/assembly.py"},
              "anchors": {}}
    for ps in pas:
        a = dict(ps["anchor"])
        a.update({"requested_by": ps["part"], "cut_shape": ps["kind"], **cut_info.get(ps["name"], {})})
        an_out["anchors"][ps["name"]] = a
    anchors_all = dict(anchors)
    anchors_all["assembly"] = an_out["anchors"]
    part_of_all = dict(part_of)

    # ---- write assembly.glb (frame bodies with their passages cut)
    sc = trimesh.Scene()
    for n in bodies:
        if n in [ps["cut_from"] for ps in pas]:
            mm = mans[n].to_mesh()
            mesh = trimesh.Trimesh(vertices=np.asarray(mm.vert_properties)[:, :3], faces=np.asarray(mm.tri_verts),
                                   process=False)
            mat = getattr(bodies[n].visual, "material", None)
            if mat is not None:                  # keep the frame body's own material
                mesh.visual = trimesh.visual.TextureVisuals(material=mat)
            else:
                mesh.visual = trimesh.visual.ColorVisuals(
                    mesh=mesh, vertex_colors=np.tile(np.array(color_of(bodies[n]), np.uint8), (len(mesh.vertices), 1)))
        else:
            mesh = bodies[n]
        sc.add_geometry(mesh, node_name=n, geom_name=n)
    glb = sc.export(file_type="glb")
    (out / "assembly.glb").write_bytes(glb)
    (out / "assembly_anchors.json").write_text(json.dumps(an_out, indent=1, ensure_ascii=False), encoding="utf-8")
    # reload and compare every node with its source body
    back = trimesh.load(out / "assembly.glb", force="scene")
    diffs = []
    for node in back.graph.nodes_geometry:
        tf, g = back.graph[node]
        mesh = back.geometry[g].copy()
        mesh.apply_transform(tf)
        lo, hi = bb(mans[node])
        if np.abs(mesh.bounds - np.array([lo, hi])).max() > 0.01 or abs(mesh.volume - mans[node].volume()) > 0.5:
            diffs.append(node)
    rep.add("B3", "PASS" if len(back.graph.nodes_geometry) == len(bodies) and not diffs else "FAIL",
            f"out/assembly.glb: {len(back.graph.nodes_geometry)} nodes, each equal to its part body (bounds 0,01 mm, "
            f"volume 0,5 mm3; frame bodies after the cuts)" + (f"; differ: {diffs}" if diffs else ""))

    # ---- overall bounds per part and assembly
    allb = np.array([bb(m) for m in mans.values()])
    lo, hi = allb[:, 0].min(axis=0), allb[:, 1].max(axis=0)
    pbox = {p: (np.min([bb(mans[n])[0] for n in mans if part_of[n] == p], axis=0),
                np.max([bb(mans[n])[1] for n in mans if part_of[n] == p], axis=0)) for p in PARTS}
    pbox_raw = {p: (np.min([bodies[n].bounds[0] for n in bodies if part_of[n] == p], axis=0),
                    np.max([bodies[n].bounds[1] for n in bodies if part_of[n] == p], axis=0)) for p in PARTS}

    fa, ha = anchors["frame"], anchors["housing"]

    def shown(part, name):
        """'knife.edge.rest: E +-30': a value a check reads, with its class and error as the anchors file gives them
        (critic g9: check EW demands this in the line of every check whose data 'reads' name a P, E or W value)"""
        return f"{name}: {cls_err(*read_value(anchors.get(part, {}), meta.get(part, {}), name))}"

    # ---------------- check 1: overall size
    rec.start("1")
    named_exc = {}
    for n in mans:
        if n == "housing.cabinet":
            named_exc[n] = "cabinet option B (DECISION 3), outside the plan's 2860"
        elif n == "housing.cover_11":
            named_exc[n] = "cap over the frame-top opening, named exception to check 1 (housing conflict 10, M13)"
    rest = np.array([bb(m) for n, m in mans.items() if n not in named_exc])
    lo2, hi2 = rest[:, 0].min(axis=0), rest[:, 1].max(axis=0)
    xr, yr, zt = REQ["x_min"][0], REQ["x_max"][0], REQ["z_top"][0]
    ok_y = abs((hi[1] - lo[1]) - REQ["y_span"][0]) <= TOL_DT
    rep.add("1", "PASS" if ok_y else "FAIL",
            f"overall Y {lo[1]:.1f}..{hi[1]:.1f} = {hi[1] - lo[1]:.1f} vs {REQ['y_span'][0]:.0f} (D) +-{TOL_DT:g}")
    ok_xr = abs(hi[0] - yr) <= TOL_DT
    rep.add("1", "PASS" if ok_xr else "FAIL", f"overall X right end {hi[0]:.1f} vs {yr:.0f} (D) +-{TOL_DT:g}")
    ok_xl = abs(lo[0] - xr) <= TOL_DT
    # every body at the left end is named (a tie of two bodies is two names, critic g8)
    left_bodies = sorted(n for n in mans if bb(mans[n])[0][0] <= lo[0] + TIE)
    d3 = "housing.cabinet" in left_bodies and meta["housing"].get("cabinet_option") == "B"
    cab_info = cabinet_alternatives(root, mans, part_of, meta, hi[0]) if "housing.cabinet" in mans else None
    rep.add("1", "PASS" if ok_xl else ("OPEN" if d3 else "FAIL"),
            f"overall X left end {lo[0]:.1f} ({', '.join(left_bodies)}) vs {xr:.0f} (D): X span {hi[0] - lo[0]:.1f} vs "
            f"{yr - xr:.0f}; {cab_info['text'] if cab_info else ''}. Open conflict, DECISION 3 (option B kept for this "
            f"episode; option A puts the cabinet over the left column; housing M9-M11 settle it on site)"
            if not ok_xl else f"overall X left end {lo[0]:.1f} vs {xr:.0f} (D) +-{TOL_DT:g}",
            data=cab_info["data"] if cab_info else None)
    # the OPEN left end above must not hide another left body (critic g6): the machine without the cabinet and its
    # devices ends at the body line, and option A (cabinet over the left column) ends at the plan's -1307
    if cab_info:
        cd, xb = cab_info["data"], REQ["x_body_left"][0]
        wl = cd["without_cabinet_left"]
        a_left = cd.get("other_left") if cd.get("other_option") == "A" else (lo[0] if cd["built_option"] == "A" else None)
        ok_wl = abs(wl - xb) <= TOL_DT
        ok_a = a_left is not None and abs(a_left - xr) <= TOL_DT
        rep.add("1", "PASS" if ok_wl and ok_a else "FAIL",
                f"left end without the cabinet and its {len(cd['devices_on_cabinet'])} devices {wl:.1f} "
                f"({cd['without_cabinet_left_body']}) vs body line {xb:.0f} (D) +-{TOL_DT:g}; option A left end "
                + (f"{a_left:.1f} vs {xr:.0f} (D) +-{TOL_DT:g}" if a_left is not None else "not found (no 'A: X a..b' in "
                   "spec/housing.md)") + f"; built option {cd['built_option']}")
    top_body = max((n for n in mans if n not in named_exc), key=lambda n: bb(mans[n])[1][2])
    ok_z = abs(hi2[2] - zt) <= TOL_DT and abs(pbox["frame"][1][2] - zt) <= TOL_DT
    # the lifting eyes are read inside the window, only to print them as excluded: lift.eye_left is 'D (X, Z); E (Y)',
    # so this line declares it and prints its class (critic g10: declared, not read outside the window)
    cov = (f"; named exception housing.cover_11 top Z {bb(mans['housing.cover_11'])[1][2]:.1f}"
           if "housing.cover_11" in mans else "")
    rep.add("1", "PASS" if ok_z else "FAIL",
            f"Z top {hi2[2]:.1f} ({top_body}) vs frame top {zt:.0f} (T) +-{TOL_DT:g}; floor Z {lo[2]:.1f}; lifting eyes are "
            f"anchors only (lift.eye_* Z {fa['lift.eye_left']['xyz'][2]:.0f}, excluded; "
            f"{shown('frame', 'lift.eye_left')})" + cov,
            data={"reads": [["frame", "lift.eye_left"]]})

    # ---------------- check 2: table top
    rec.start("2")
    tt = fa["table.top"]["xyz"][2]
    tb = bb(mans["frame.table"])[1][2]
    rep.add("2", "PASS" if abs(tt - REQ["table_top"][0]) <= 100 and abs(tb - tt) <= 1 else "FAIL",
            f"table top Z {tt:.1f} (anchor table.top), frame.table top {tb:.1f}; target 885 E +-100 "
            f"({REQ['table_top'][2]}); estimated, on the tape-measure list ({shown('frame', 'table.top')})",
            data={"reads": [["frame", "table.top"]]})

    # ---------------- check 3: table and knife
    rec.start("3")
    tl, th = bb(mans["frame.table"])
    kl, kh = bb(mans["knife.knife"])
    ok3 = abs((th[0] - tl[0]) - 1150) <= TOL_DT and abs((th[1] - tl[1]) - 2630) <= TOL_DT and (kh[0] - kl[0]) >= 1150
    rep.add("3", "PASS" if ok3 else "FAIL",
            f"table X {tl[0]:.1f}..{th[0]:.1f} = {th[0] - tl[0]:.1f} (T 1150) +-{TOL_DT:g}, Y {tl[1]:.1f}..{th[1]:.1f} = "
            f"{th[1] - tl[1]:.1f} (D 2630) +-{TOL_DT:g}; knife length {kh[0] - kl[0]:.1f} >= 1150 (T cutting width; "
            f"the knife's own size is W 1320, see the open item on estimated values)")

    # ---------------- check 4: pile height
    # the motion model serves checks 4, 6, 9 and V: it is built in its own windows (mm.<motion>), not in check 3's,
    # and each check that uses a motion is charged with that motion's reads (critic g10; no rec.stop() here)
    mm = Charged(motion_model(anchors, meta, bodies, rec), rec)
    rec.start("4")
    cf = anchors["clamp"]["clamp.face"]
    beam_min = min(bb(mans[b])[0][2] for b in mm["clamp"]["beam"])
    ke = anchors["knife"]["knife.edge.rest"]["xyz"][2]
    ok4 = abs((cf["xyz"][2] - tt) - 130) <= TOL_DT and abs(beam_min - cf["xyz"][2]) <= TOL_SIDE and (ke - tt) >= 130 \
        and abs(kl[2] - ke) <= TOL_SIDE
    rep.add("4", "PASS" if ok4 else "FAIL",
            f"clamp face at the top Z {cf['xyz'][2]:.1f} (anchor {shown('clamp', 'clamp.face')}), lowest beam body "
            f"{beam_min:.1f} (= anchor +-{TOL_SIDE:g}): {cf['xyz'][2] - tt:.1f} above the table (T 130) +-{TOL_DT:g}, "
            f"the table top being {shown('frame', 'table.top')}; knife edge at rest {ke:.2f} "
            f"({shown('knife', 'knife.edge.rest')}; body {kl[2]:.2f}, = anchor +-{TOL_SIDE:g}): {ke - tt:.2f} above "
            f"(>= 130), margin {ke - tt - 130:.2f} against its error: see the open item on estimated values",
            data={"reads": [["frame", "table.top"], ["clamp", "clamp.face"], ["knife", "knife.edge.rest"]]})

    # ---------------- check 5: backgauge travel
    rec.start("5")
    bfa = anchors["backgauge"]["backgauge.face"]
    face_rest = bfa["xyz"][1]
    rngb = bfa["motion"]["range"]
    front = face_rest + bfa["motion"]["axis"][1] * rngb[1]
    combs = [n for n in mans if n.startswith("backgauge.") and n.split(".", 1)[1] in ("comb_fingers", "comb_strip")]
    comb_front = min(bb(mans[n])[0][1] for n in combs) if combs else float("nan")
    ok5 = abs(face_rest - 1150) <= TOL_DT and abs(front - 25) <= TOL_DT and abs(comb_front - face_rest) <= TOL_SIDE
    rep.add("5", "PASS" if ok5 else "FAIL",
            f"backgauge face Y {front:.1f}..{face_rest:.1f} (anchor {shown('backgauge', 'backgauge.face')}, range "
            f"{rngb}); comb front at rest {comb_front:.1f} (= face +-{TOL_SIDE:g}); target 25..1150 (T; certificate "
            f"1160) +-{TOL_DT:g} at each end",
            data={"reads": [["backgauge", "backgauge.face"]]})

    # ---------------- check 6: strokes
    rec.start("6")
    th0 = mm["knife"]["th0"]
    dzs = [mm["knife"]["pose"](th0 + 2 * math.pi * k / 3600)[1] for k in range(3601)]
    stroke = max(dzs)
    stick_top = bb(mans["frame.cutting_stick"])[1][2]
    bottom = kl[2] - stroke
    depth = stick_top - bottom
    kb = anchors["knife"].get("knife.edge.bottom", {}).get("xyz", [0, 0, float("nan")])[2]
    d_lo, d_hi = REQ["cut_depth"][0]
    ok6 = abs(cf["motion"]["range"][1] - 130) <= TOL_DT and d_lo - 1e-6 <= depth <= d_hi + 1e-6 \
        and abs(bottom - kb) <= TOL_BOTTOM \
        and abs(stroke - anchors["knife"]["knife.edge.rest"]["motion"]["range"][1]) <= TOL_STROKE
    # the knife at its exact bottom against the cutting stick: the designed contact (evidence for check 6)
    i_bdc = int(np.argmax(dzs))
    tf_bdc = mm["knife"]["pose"](th0 + 2 * math.pi * i_bdc / 3600)[0]
    sl, sh = bb(mans["frame.cutting_stick"])
    stick_box = (np.array([sl[0], sl[1], bottom - 0.01]), np.array([sh[0], 0.01, stick_top]))
    kc = mans["knife.knife"].transform(tf_bdc["knife.knife"]) ^ mans["frame.cutting_stick"]
    kcv = kc.volume()
    kcb = [np.round(x, 2).tolist() for x in bb(kc)] if kcv > 0 else None
    ok6 = ok6 and kcv > EPS and kcb is not None and kcb[0][2] >= stick_box[0][2] - 1e-6 and kcb[1][1] <= 0.01
    rep.add("6", "PASS" if ok6 else "FAIL",
            f"clamp stroke {cf['motion']['range'][1]:.1f} (T 130) +-{TOL_DT:g} (range of {shown('clamp', 'clamp.face')}); "
            f"knife stroke from the crank model {stroke:.2f} (the model built from "
            f"{', '.join(shown('knife', n) for n in KNIFE_CRANK)}; anchor range "
            f"{anchors['knife']['knife.edge.rest']['motion']['range'][1]} +-{TOL_STROKE:g}; "
            f"{shown('knife', 'knife.edge.rest')}), edge at the bottom Z {bottom:.2f} (anchor {kb:.2f} +-{TOL_BOTTOM:g}; "
            f"{shown('knife', 'knife.edge.bottom')}), cutting stick top {stick_top:.2f}: "
            f"{depth:.2f} into the stick (T 0,1-0,2, checked as {d_lo:g}..{d_hi:g}); "
            f"contact.knife_edge.cutting_stick at the bottom: {kcv:.1f} mm3 in {kcb}",
            data={"reads": [["clamp", "clamp.face"], ["knife", "knife.edge.rest"], ["knife", "knife.edge.bottom"]]
                  + [["knife", n] for n in KNIFE_CRANK],
                  # the numbers this check compares, for its clause in the open item on estimated values (tester 3 r3)
                  "stroke": float(stroke), "range": float(anchors["knife"]["knife.edge.rest"]["motion"]["range"][1]),
                  "edge_rest": float(kl[2]), "bottom": float(bottom), "kb": float(kb), "stick_top": float(stick_top),
                  "depth": float(depth)})

    # ---------------- check 7: part bounds = spec outer size
    rec.stop()
    so = spec_outer(root, anchors)
    for p in PARTS:
        slo, shi, how = so[p]
        glo, ghi = pbox_raw[p]
        if slo is None:
            rep.add("7", "FAIL", f"{p}: no outer size found in spec/{p}.md")
            continue
        dev = max(np.abs(glo - slo).max(), np.abs(ghi - shi).max())
        rep.add("7", "PASS" if dev <= 1 else "FAIL",
                f"{p}: GLB X {glo[0]:.1f}..{ghi[0]:.1f} Y {glo[1]:.1f}..{ghi[1]:.1f} Z {glo[2]:.1f}..{ghi[2]:.1f} vs "
                f"spec ({how}) X {slo[0]:.1f}..{shi[0]:.1f} Y {slo[1]:.1f}..{shi[1]:.1f} Z {slo[2]:.1f}..{shi[2]:.1f}: "
                f"max deviation {dev:.2f} (+-1)")

    # ---------------- check 8: at rest
    jb = joint_boxes(anchors_all)
    for n, (parts, jlo, jhi, how) in sorted(jb.items()):
        rep.note(f"joint {n}: {', '.join(parts)}; box ({how}) x {jlo[0]:.1f}..{jhi[0]:.1f} y {jlo[1]:.1f}..{jhi[1]:.1f} "
                 f"z {jlo[2]:.1f}..{jhi[2]:.1f}" + ("; clearance joint, excuses nothing" if n == "interface.clamp.comb_interleave" else ""))
    pk = pocket_boxes(anchors, meta)
    space = Space(mans, part_of_all, {n: v for n, v in jb.items()}, pk, stick_box)
    rest_hits = space.overlaps({})
    # same-part overlaps at rest = part-internal joints (pins in eyes); the sweeps skip exactly these pairs
    internal = set()
    names_ = list(mans)
    for i, a in enumerate(names_):
        for b in names_[i + 1:]:
            if part_of[a] == part_of[b] and touch(space.rest_bb[a], space.rest_bb[b]):
                v = (mans[a] ^ mans[b]).volume()
                if v > EPS:
                    internal.add(frozenset((a, b)))
                    rep.note(f"part-internal overlap at rest (not check 8; skipped in the sweeps): {a} x {b} {v:.1f} mm3")
    space.internal = internal
    n_pairs = sum(1 for i, a in enumerate(mans) for b in list(mans)[i + 1:]
                  if part_of[a] != part_of[b] and touch(space.rest_bb[a], space.rest_bb[b]))
    bad8 = [h for h in rest_hits if h[3] > EPS]
    for a, b, v, o, used, q in rest_hits:
        rep.note(f"rest overlap {a} x {b}: {v:.1f} mm3, outside excusing boxes {o:.2f} mm3; excused by {used or 'nothing'}; "
                 f"bounds {q}")
    rep.add("8", "PASS" if not bad8 else "FAIL",
            f"at rest, {n_pairs} cross-part body pairs with touching boxes intersected (manifold3d); "
            f"{len(rest_hits)} with volume > {EPS} mm3, {len(bad8)} not inside a joint box or pocket"
            + "".join(f"; {a} x {b} {o:.1f} mm3 at {q}" for a, b, v, o, used, q in bad8))
    # passages: what passes at rest, which envelopes meet them, and whether the frame's sources show solid there
    frow = {}
    for _, h, rs in md_tables((root / "spec" / "frame.md").read_text(encoding="utf-8")):
        hl = [c.lower() for c in h]
        if hl and hl[0] == "id" and "class" in hl and "source" in hl:
            for r in rs:
                frow[r[0]] = (r[hl.index("class")], r[hl.index("source")])
    envs = [(n, p, np.array(a["min"], float), np.array(a["max"], float)) for p, an in anchors.items()
            for n, a in an.items() if (n.startswith("envelope.") or n.startswith("corridor.")) and "min" in a]
    for ps in pas:
        inside = []
        for n, m in mans.items():
            if part_of[n] == ps["part"] and touch(bb(m), (ps["box"][:, 0], ps["box"][:, 1])):
                v = (m ^ ps["shape"]).volume()
                if v > EPS:
                    inside.append(f"{n} {v:.0f} mm3")
        meet = [n for n, p, elo, ehi in envs if p == ps["part"] and touch((elo, ehi), (ps["box"][:, 0], ps["box"][:, 1]), 0.5)]
        cls, src = frow.get(ps["cut_from"].split(".", 1)[1], ("not found", ""))
        ps["used_rest"], ps["envelopes"] = inside, meet
        rep.note(f"passage {ps['name']}: at rest it holds {', '.join(inside) or 'no mesh'}; envelopes meeting it: "
                 f"{', '.join(meet) or 'none'}; frame row {ps['cut_from']}: class '{cls}', source '{src[:120]}'; "
                 f"judgement (actor t7): {JUDGE.get(ps['name'], 'not judged')}")
    # envelope and corridor boxes (JSON only, no mesh) against every mesh of the other parts and each other
    bad_e = []
    for n, p, elo, ehi in envs:
        bxm = box_man(elo, ehi)
        for b, m in mans.items():
            if part_of[b] != p and touch(bb(m), (elo, ehi)):
                v = (m ^ bxm).volume()
                if v > EPS:
                    bad_e.append(f"{n} x {b} {v:.1f} mm3 at {[np.round(x, 1).tolist() for x in bb(m ^ bxm)]}")
        for n2, p2, lo2_, hi2_ in envs:
            if p2 != p and n2 > n:
                ov = np.clip(np.minimum(ehi, hi2_) - np.maximum(elo, lo2_), 0, None).prod()
                if ov > EPS:
                    bad_e.append(f"{n} x {n2} {ov:.1f} mm3")
    rep.add("8e", "PASS" if not bad_e else "FAIL",
            f"{len(envs)} envelope / corridor boxes ({', '.join(n for n, *_ in envs)}) against every mesh of the other "
            f"parts (frame after the cuts) and each other: {len(bad_e)} overlaps" + "".join("; " + x for x in bad_e))

    # ---------------- check 9: sweeps
    if not args.no_sweep:
        sweeps(rep, space, mm, mans, part_of, args.steps, pas)
    else:
        rep.add("9", "OPEN", "sweeps skipped (--no-sweep)")

    # ---------------- check 10: device anchors
    exp = section10_expect(Path(args.section10))
    found = {}
    for p, an in anchors_all.items():
        for n in an:
            k, _, d = n.partition(".")
            if k in DEVICE_KINDS:
                found.setdefault(d, []).append((k, p, n))
            if k == "cabinet":
                found.setdefault("cabinet", []).append((k, p, n))
    bad10 = []
    for d, (kind, host) in sorted(exp.items()):
        f = found.get(d, [])
        ok = len(f) == 1 and f[0][0] == kind and (host is None or f[0][1] == host)
        if not ok:
            bad10.append(f"{d}: expected {kind}.{d} on {host}, found {[x[2] + ' (' + x[1] + ')' for x in f]}")
    cab = found.get("cabinet", [])
    if len(cab) != 1 or cab[0][1] != "housing":
        bad10.append(f"cabinet: expected one cabinet.* anchor on housing, found {cab}")
    extra = sorted(f"{x[2]} ({x[1]})" for d, f in found.items() for x in f if d not in exp and d != "cabinet")
    rep.add("10", "PASS" if not bad10 and len(exp) == 28 else "FAIL",
            f"{len(exp)} designations of section 10 + cabinet = {len(exp) + 1}: each exactly one device anchor of the "
            f"kind and host part section 10 names (prefixes {', '.join(DEVICE_KINDS)}, cabinet; foot.* and body.* not "
            f"counted)" + ("; " + "; ".join(bad10) if bad10 else "") + (f"; other device anchors: {extra}" if extra else ""))

    # ---------------- check 12: footprint
    rec.start("12")
    yA = meta["frame"].get("y_anchor_line_A")
    bx = sorted({round(a["xyz"][0], 1) for n, a in fa.items() if n.startswith("anchor_bolt.")})
    fr_lo, fr_hi = bb(mans["frame.foot_rear"])
    rd = fr_hi[0] - fr_lo[0]
    rc = (fr_lo + fr_hi) / 2
    pr_lo, pr_hi = bb(mans["frame.foot_right"])
    ok12 = (len(bx) == 2 and abs(bx[0] - REQ["bolt_x"][0][0]) <= TOL_DT and abs(bx[1] - REQ["bolt_x"][0][1]) <= TOL_DT
            and abs(rd - 165) <= TOL_DT and abs(rc[0]) <= TOL_DT and abs((rc[1] - yA) - 1130) <= TOL_DT
            and abs((pr_hi[1] - pr_lo[1]) - 450) <= TOL_DT and abs((yA - pr_lo[1]) - 220) <= TOL_DT
            and abs((pr_hi[1] - yA) - 230) <= TOL_DT)
    bolts = sorted(n for n in fa if n.startswith("anchor_bolt."))
    # the bolts placed partly from the drawing's scale (class D/P) print their class and error (check EW)
    bolts_pe = [n for n in bolts if is_estimated(read_value(fa, meta["frame"], n)[0])]
    rep.add("12", "PASS" if ok12 else "FAIL",
            f"each D number +-{TOL_DT:g}: anchor-bolt axes X {bx} (D -790 / +932"
            + "".join(f"; {shown('frame', n)}" for n in bolts_pe) + f"); rear ring foot outer {rd:.1f} wide "
            f"(D 165) at X {rc[0]:.1f} (D 0), "
            f"Y {rc[1]:.1f} = {rc[1] - yA:.1f} behind anchor line A (Y {yA}, {shown('frame', 'y_anchor_line_A')}) "
            f"(D 1130); right pad Y {pr_lo[1]:.1f}..{pr_hi[1]:.1f} = {pr_hi[1] - pr_lo[1]:.1f} deep, "
            f"{yA - pr_lo[1]:.1f} in front of / {pr_hi[1] - yA:.1f} behind line A (D 450 = 220 + 230)",
            data={"reads": [["frame", "y_anchor_line_A"]] + [["frame", n] for n in bolts]})

    # ---------------- merged tables and check 11
    rec.stop()
    mdata = None
    if not args.no_merge:
        mdata = merge_tables.write_all(root, bodies=sorted(bodies), anchors=anchors, meta=meta, report=rep,
                                       bounds={n: bb(mans[n]) for n in mans})

    # ---------------- open items, the two guards on the written text, then the viewer (it shows the checks above
    # and the open items; it adds line V)
    items = open_items(root, mans, pas, cab_info, REQ["z_top"][0], mdata, checks=rep.checks)
    guard_names(rep, items, mans, anchors_all, mdata)
    guard_estimated(rep, items, anchors, meta, rec)
    if not args.no_viewer:
        import build_viewer
        build_viewer.build(root, mans, part_of, anchors_all, meta, mm, cut_names=[ps["cut_from"] for ps in pas],
                           colors={n: color_of(bodies[n]) for n in bodies}, report=rep, checks=list(rep.checks),
                           open_items=items, inputs=inputs, legend=LEGEND.lstrip("# "))

    return finish(root, rep, inputs, items, {"project": str(project), "project_found": proj_how,
                                             "section10": str(args.section10)})


# names that look like '<part>.<name>' but are files (spec/housing.md, parts/housing/housing.py ...)
FILE_EXT = (".py", ".md", ".json", ".glb", ".stl", ".txt", ".html", ".jpg", ".png", ".log")
NAME_TOKEN = re.compile(r"(?<![\w./\\-])((?:" + "|".join(PARTS) + r")\.[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)")


def guard_names(rep, items, mans, anchors_all, mdata):
    """check N (critic g8): every '<part>.<name>' token in the check lines so far (line V comes later and names
    bodies of the motion model only) and in the open items is a body, an anchor or a measure ID"""
    known = set(mans) | {n for an in anchors_all.values() for n in an} | set((mdata or {}).get("measure_ids", []))
    seen, bad = 0, []
    texts = [(f"[{c['check']}]", c["text"]) for c in rep.checks] + [(f"open item {i + 1}", t) for i, t in enumerate(items)] \
        + [("a note line", ln.strip()) for ln in rep.lines if ln.startswith("     ")]
    for where, t in texts:
        for tok in NAME_TOKEN.findall(t):
            if tok.lower().endswith(FILE_EXT):
                continue
            seen += 1
            if tok not in known:
                bad.append(f"{tok} in {where}")
    rep.add("N", "FAIL" if bad else "PASS",
            f"names in the check lines and open items: {seen} '<part>.<name>' tokens, each a body, an anchor or a "
            f"measure ID" + (" (measure IDs not checked: --no-merge)" if not mdata else "")
            + (": NO, unknown: " + "; ".join(dict.fromkeys(bad)) if bad else ": yes"))


# a check line compares an estimated or web value when it prints the class E or W before a number or a +- bound
EW_MARK = re.compile(r"(?<![A-Za-z0-9])[EW](?= ?\+-| ?±| \d)")


def read_value(part_anchors, part_meta, name):
    """class and error of a value a check reads, as the part's anchors file publishes them (critic g9): an anchor
    (its 'class' and 'error_mm'), or a meta value such as the frame's y_anchor_line_A (value and error from its
    keys; the frame publishes its class only in the meta 'errors' text: 'Y_A = +6, E +-80')"""
    a = part_anchors.get(name)
    if isinstance(a, dict):
        return a.get("class", "?"), a.get("error_mm")
    if name in part_meta:
        cls = part_meta.get(f"{name}_class")
        if cls is None and name == "y_anchor_line_A":
            mt = re.search(r"Y_A = [+-]?[\d.]+, ([A-Z/]+) \+-", str(part_meta.get("errors", "")))
            cls = mt.group(1) if mt else None
        return cls or "?", part_meta.get(f"{name}_error")
    return "?", None


def cls_err(cls, err):
    """'E +-30' or 'T/E y +-10, z +-100': a class and its error as the anchors file gives them"""
    if isinstance(err, dict):
        es = ", ".join(f"{k} +-{v:g}" for k, v in err.items())
    elif isinstance(err, (int, float)):
        es = f"+-{err:g}"
    else:
        es = "with no error given"
    return f"{cls} {es}"


def is_estimated(cls):
    """a value with its own stated error (section 04): P, E or W in its class, or a class not known"""
    return cls == "?" or bool(set(re.findall(r"[A-Z]", cls)) & {"P", "E", "W"})


def ew_clauses(items):
    """the clauses of the open item 'checks on estimated values', each with the check ids it starts with"""
    item = next((t for t in items if t.startswith("checks on estimated values")), "")
    out = []
    for c in (re.split(r"; (?=\[)", item.partition(": ")[2]) if item else []):
        m = re.match(r"\[\w+\](?:(?:, | and )\[\w+\])*", c)
        out.append((set(re.findall(r"\[(\w+)\]", m.group(0))) if m else set(), c))
    return item, out


def guard_estimated(rep, items, anchors, meta, rec=None):
    """check EW (critic g8, g9). A P, E or W value carries its own stated error (section 04); its class is looked up
    in the anchors files, not taken from the printed text. (0) Every such value that the code of checks 1-6 and 12
    reads while it runs (Reads) is declared in that check's data 'reads'. (a) A check prints each such value it
    declares as '<name>: <class> <error>'. (b) The open item 'checks on estimated values' has a clause starting with
    that check's '[id]' that names each of them. (c) A check line that prints an E or W letter before a number or a
    +- bound is named in the item too."""
    item, clauses = ew_clauses(items)
    named = set().union(*(ids for ids, _ in clauses)) if clauses else set()
    reads, bad = {}, []
    for cid, touched in (rec.seen if rec else {}).items():
        if cid.startswith("mm."):
            continue        # a window of the motion model: its reads are charged to the checks that use it (Charged)
        declared ={tuple(r) for c in rep.checks if c["check"] == cid for r in (c.get("data") or {}).get("reads", [])}
        for part, name in sorted(touched - declared):
            cls, err = read_value(anchors.get(part, {}), meta.get(part, {}), name)
            if is_estimated(cls):
                bad.append(f"[{cid}] reads {name} ({cls_err(cls, err)}) and does not declare it")
    for c in rep.checks:
        for part, name in (c.get("data") or {}).get("reads", []):
            cls, err = read_value(anchors.get(part, {}), meta.get(part, {}), name)
            if not is_estimated(cls):
                continue
            shown = f"{name}: {cls_err(cls, err)}"
            reads.setdefault(c["check"], {})[name] = shown
            if shown not in c["text"]:
                bad.append(f"the [{c['check']}] line does not print {shown}")
    for cid, vals in reads.items():
        cl = [t for ids, t in clauses if cid in ids]
        for name, shown in vals.items():
            if not cl:
                bad.append(f"[{cid}] (reads {shown}) has no clause in the item")
            elif not any(name in t for t in cl):
                bad.append(f"the [{cid}] clause does not name {shown}")
    marked = list(dict.fromkeys(c["check"] for c in rep.checks if EW_MARK.search(c["text"])))
    missing = [c for c in marked if c not in named]
    rep.add("EW", "FAIL" if bad or missing or not item else "PASS",
            "checks that read a P, E or W value (class from the anchors files; what checks 1-6 and 12 read is "
            "recorded while they run, and a check that uses a motion of the motion model is charged with the anchors "
            "that motion was built from): "
            + ("; ".join(f"[{cid}] {', '.join(v)}" for cid, v in reads.items()) or "none")
            + "; each declares it, prints it as '<name>: <class> <error>' and has a clause in the open item 'checks "
              "on estimated values' that names it: " + ("NO: " + "; ".join(bad) if bad else "yes")
            + f"; check lines that print an E or W letter: {', '.join(f'[{c}]' for c in marked) or 'none'}, each "
              f"named in that item: "
            + ("NO, the item is missing" if not item else ("NO, missing " + ", ".join(f"[{c}]" for c in missing))
               if missing else "yes"))


def finish(root, rep, inputs, items, where=None):
    """write assembly_report.json and assembly_checks.txt; exit code 1 on any FAIL"""
    st = [c["status"] for c in rep.checks]
    summary = {s: st.count(s) for s in ("PASS", "FAIL", "OPEN")}
    rep_json = {"script": "stage_1_mechanics/assembly/assembly.py", "root": str(root), **(where or {}),
                "inputs_sha256": inputs, "summary": summary, "checks": rep.checks, "open_items": items,
                "legend": LEGEND.lstrip("# "), "abbreviations": ABBREV.lstrip("# ")}
    (root / "assembly").mkdir(exist_ok=True)
    (root / "assembly" / "assembly_report.json").write_text(json.dumps(rep_json, indent=1, ensure_ascii=False),
                                                            encoding="utf-8")
    (root / "assembly" / "assembly_checks.txt").write_text("\n".join([LEGEND, ABBREV] + rep.lines) + "\n",
                                                           encoding="utf-8")
    nb = next((c["text"].split(" bodies")[0].replace("loaded ", "") for c in rep.checks if c["check"] == "B1"), "?")
    print(f"assembly: {nb} bodies | {summary['PASS']} PASS, {summary['FAIL']} FAIL, {summary['OPEN']} OPEN")
    return 1 if summary["FAIL"] else 0


def sweeps(rep, space, mm, mans, part_of, steps, pas):
    k = mm["knife"]
    th0 = k["th0"]
    c_rng, b_rng = mm["clamp"]["range"], mm["backgauge"]["range"]
    cl_down, bg_front = c_rng[1], b_rng[1]

    def run(label, states, moving, cid="9"):
        worst, use = {}, {}
        for st_name, tfs in states:
            hits = space.overlaps(tfs, moving=moving, internal_rest=space.internal)
            for a, b, v, o, used, q in hits:
                key = (a, b)
                if key not in worst or o > worst[key][1] or (o == worst[key][1] and v > worst[key][0]):
                    worst[key] = (v, o, used, q, st_name)
            for ps in pas:                       # which moving bodies pass through the passages cut at assembly
                for n in moving:
                    if space.part_of[n] != ps["part"]:
                        continue
                    mb, bbx = space.placed(n, tfs.get(n))
                    if touch(bbx, (ps["box"][:, 0], ps["box"][:, 1])):
                        v = (mb ^ ps["shape"]).volume()
                        if v > EPS:
                            u = use.setdefault((ps["name"], n), [0.0, None, None, 0])
                            u[0] = max(u[0], v)
                            u[1] = u[1] or st_name
                            u[2] = st_name
                            u[3] += 1
        for (pn, n), (v, s1, s2, cnt) in sorted(use.items()):
            rep.note(f"{label}: {n} passes through {pn} in {cnt} of {len(states)} states (from '{s1}' to '{s2}'), "
                     f"up to {v:.0f} mm3 inside the cut")
        bad = {kk: w for kk, w in worst.items() if w[1] > EPS}
        for (a, b), (v, o, used, q, s) in sorted(worst.items()):
            rep.note(f"{label}: {a} x {b} worst {v:.1f} mm3 at {s}, outside excusing boxes {o:.2f}; excused by "
                     f"{used or 'nothing'}; bounds {q}")
        rep.add(cid, "PASS" if not bad else "FAIL",
                f"{label}: {len(states)} states, moving {len(moving)} bodies; {len(bad)} colliding pairs"
                + "".join(f"; {a} x {b} {w[1]:.1f} mm3 at {w[4]} {w[3]}" for (a, b), w in sorted(bad.items())))

    # knife: whole crank turn; clamp up / down; backgauge at rest / front
    angs = [th0 + 2 * math.pi * i / steps for i in range(steps)]
    dmax, prev, pz = 0.0, None, []
    for t in angs + [th0 + 2 * math.pi]:
        tf, dz = k["pose"](t)
        pz.append(dz)
    dmax = max(abs(pz[i + 1] - pz[i]) for i in range(len(pz) - 1))
    # largest travel of any conrod vertex per step
    rod = np.asarray(space.m[KNIFE_CONROD].to_mesh().vert_properties)[:, :3]
    rmax = 0.0
    for i in range(steps):
        a = k["pose"](angs[i])[0][KNIFE_CONROD]
        b = k["pose"](angs[(i + 1) % steps] if i + 1 < steps else th0 + 2 * math.pi)[0][KNIFE_CONROD]
        pa = rod @ a[:, :3].T + a[:, 3]
        pb = rod @ b[:, :3].T + b[:, 3]
        rmax = max(rmax, float(np.linalg.norm(pa - pb, axis=1).max()))
    step_deg = 360.0 / steps
    rep.add("9", "PASS" if dmax <= 10 and rmax <= 10 and step_deg <= 11 else "FAIL",
            f"knife sweep resolution: {steps} crank steps of {step_deg:.1f} deg over the whole turn; holder moves <= "
            f"{dmax:.2f} mm and any conrod point <= {rmax:.2f} mm per step (<= 10)")
    kmov = set(KNIFE_TRANSLATE) | {KNIFE_CONROD, KNIFE_CRANKPIN}
    for cs, cname in ((0.0, "clamp up"), (cl_down, "clamp down")):
        for bd, bname in ((0.0, "backgauge at rest"), (bg_front, "backgauge at the front")):
            states = []
            for i, t in enumerate(angs):
                tf, dz = k["pose"](t)
                tf = dict(tf)
                tf.update(clamp_tf(mm, cs))
                tf.update(bg_tf(mm, bd))
                states.append((f"crank +{i * step_deg:.0f} deg (knife down {dz:.1f}), {cname}, {bname}", tf))
            run(f"knife turn, {cname}, {bname}", states, kmov)
    # clamp: top to bottom, steps of 5; knife at rest; backgauge at rest and at the front (comb interleave)
    cmov = set(mm["clamp"]["beam"] + mm["clamp"]["piston"] + mm["clamp"]["riders"])
    svals = sorted(set(np.arange(c_rng[0], c_rng[1], 5.0).tolist() + [c_rng[1]]))
    for bd, bname in ((0.0, "backgauge at rest"), (bg_front, "backgauge at the front (comb interleave)")):
        states = []
        for s in svals:
            tf = clamp_tf(mm, s)
            tf.update(bg_tf(mm, bd))
            states.append((f"clamp down {s:.0f}, {bname}", tf))
        run(f"clamp stroke, {bname}", states, cmov)
    # backgauge: whole travel in steps of 5; knife and clamp at rest (it moves only with the clamp up, p25, S30)
    bmov = set(mm["backgauge"]["moving"])
    dvals = sorted(set(np.arange(b_rng[0], b_rng[1], 5.0).tolist() + [b_rng[1]]))
    run("backgauge travel", [(f"face Y {1150 - d:.0f}", bg_tf(mm, d)) for d in dvals], bmov)
    # extra motions of the parts (not named in check 9; reported the same way)
    pd = mm["pedal"]
    if pd["bodies"]:
        angs_p = np.linspace(pd["range"][0], pd["range"][1], 16)
        run("pedal 5 turn", [(f"pedal {a:.1f} deg", {b: mat_rot(pd["axis"], pd["pivot"], a) for b in pd["bodies"]})
                             for a in angs_p], set(pd["bodies"]), cid="9x")
    hw = mm["handwheel"]
    if hw["bodies"] and hw["push"]:
        run("handwheel push-in", [(f"pushed {s:.0f}", {b: mat_t([-s, 0, 0]) for b in hw["bodies"]})
                                  for s in np.linspace(0, hw["push"], 3)], set(hw["bodies"]), cid="9x")
    lk = mm["lock"]
    if lk["bodies"] and "knife.y01_magnet" in mans and "knife.y01_tail" in mans:
        # the magnet is modelled solid; its plunger (y01_tail) already runs through it at rest, so the pin that the
        # plunger pulls may follow into that channel: the tail's X-Z section across the magnet's Y extent, no more
        tl, th_ = bb(mans["knife.y01_tail"])
        ml, mh_ = bb(mans["knife.y01_magnet"])
        ch = (np.array([tl[0], ml[1], tl[2]]), np.array([th_[0], mh_[1], th_[2]]))
        space.extra = {frozenset(("knife.lock_pin_1", "knife.y01_magnet")):
                       [(ch[0], ch[1], f"plunger channel of knife.y01_tail through knife.y01_magnet (x {ch[0][0]:.0f}.."
                                       f"{ch[1][0]:.0f} y {ch[0][1]:.0f}..{ch[1][1]:.0f} z {ch[0][2]:.0f}..{ch[1][2]:.0f}; "
                                       f"the magnet is modelled solid)")]}
    if lk["bodies"]:
        run("lock pin 1 stroke (Y01)", [(f"pulled {s:.0f}", {b: mat_t(np.array(lk["axis"], float) * s) for b in lk["bodies"]})
                                        for s in np.linspace(lk["range"][0], lk["range"][1], 4)], set(lk["bodies"]), cid="9x")
    dr = mm["door"]
    if dr.get("body") in space.m:
        run("right front cover opening", [(f"cover {a:.0f} deg", {dr["body"]: mat_rot(dr["axis"], dr["pivot"], a)})
                                          for a in np.linspace(dr["range_deg"][0], dr["range_deg"][1], 19)],
            {dr["body"]}, cid="9x")


def open_items(root, mans, pas, cab_info, frame_top, mdata=None, checks=None):
    """the open items of the assembled model; every number is taken from this run's bodies and files (and, for the
    [6] clause, from the numbers check 6 wrote into its data: checks = rep.checks)"""
    items = []
    by_part = {}
    for ps in pas:
        cut = ps["cut_from"] if ps["cut_from"].startswith("frame.") else f"frame.{ps['cut_from']}"   # one prefix
        by_part.setdefault(ps["part"], []).append(f"{ps['name']} (cut from {cut})")
    items.append(f"DECISION 2: {len(pas)} frame passages cut at assembly ("
                 + "; ".join(f"{p}: {', '.join(v)}" for p, v in sorted(by_part.items()))
                 + "); published in out/assembly_anchors.json; the frame files are unchanged")
    if cab_info:
        d = cab_info["data"]
        plan = REQ["x_max"][0] - REQ["x_min"][0]
        txt = (f"DECISION 3: built option {d['built_option']}: cabinet X {d['built_cabinet_x'][0]:.0f}.."
               f"{d['built_cabinet_x'][1]:.0f}, machine X {d['built_left']:.0f}..{d['built_right']:.0f}, span "
               f"{d['built_span']:.0f} against the plan's {plan:.0f} (D, Fig. 4.2.2); without the cabinet and its devices "
               f"({', '.join(d['devices_on_cabinet'])}) the left end is {d['without_cabinet_left']:.0f} "
               f"({d['without_cabinet_left_body']})")
        if "other_option" in d:
            txt += (f"; option {d['other_option']} (python parts/housing/housing.py --option {d['other_option']}): "
                    f"cabinet X {d['other_cabinet_x'][0]:.0f}..{d['other_cabinet_x'][1]:.0f}, machine X "
                    f"{d['other_left']:.0f}..{d['built_right']:.0f}, span {d['other_span']:.0f}")
        items.append(txt + "; housing measure rows M9-M11 settle it on site")
    sb = [n for n in ("S12", "S13", "S14") if f"safety_sensors.{n}" in mans]
    items.append(f"DECISION 4: cam sensors {', '.join(sb)} are flagged placeholders (place and cam reading not known); "
                 "measure row safety_sensors.SS2 = knife.M9 asks for a site photo")
    if "housing.cover_11" in mans:
        c_lo, c_hi = bb(mans["housing.cover_11"])
        items.append(f"housing.cover_11 stands {c_hi[2] - frame_top:.0f} above the frame top (Z {c_lo[2]:.0f}..{c_hi[2]:.0f}): "
                     "named exception to check 1 (housing M13)")
    if "clamp.gear_8" in mans:
        g_lo, g_hi = bb(mans["clamp.gear_8"])
        items.append(f"clamp open item 1: the frame wall that carries gear 8's two bearings (clamp.gear_8 X "
                     f"{g_lo[0]:.0f}..{g_hi[0]:.0f}, Z {g_lo[2]:.0f}..{g_hi[2]:.0f}) is in no frame body; the frame "
                     "thread is closed (frame M7, clamp M7)")
    # checks that rest on estimated values (checklist 27) and the clamp spec's open item 4 (brief 2 item 10)
    an = {p: json.loads((root / "out" / f"{p}_anchors.json").read_text(encoding="utf-8")) for p in PARTS}
    tt, fm = an["frame"]["anchors"]["table.top"], an["frame"].get("meta", {})
    # the anchor files give errors as error_mm (table.top: 100, as frame measure row M4 writes it: +-100)
    tt_err = tt.get("error_mm")
    tt_err = f"+-{tt_err:g}" if isinstance(tt_err, (int, float)) else "with no error_mm in frame_anchors.json"
    # each check that compares an E or W value: value, class, error, and whether the verdict can flip within the error
    # (critic g8); guard_estimated() FAILs a check line that prints an E or W value and is not named here
    def val(p, name):
        """'name (class error)': a value the checks read, as this run's anchors file of part p gives it (check EW)"""
        return f"{name} ({cls_err(*read_value(an[p]['anchors'], an[p].get('meta', {}), name))})"

    # an anchor's source as its anchors file writes it, with the spec-local keys it uses (P7, FR, P23 ...) written
    # out as the files the part's spec resolves them to, as sources.md lists them (critic g11 F-g11-1)
    key_files = (mdata or {}).get("key_files")

    def qsrc(p, a):
        s = str(a.get("source", "?"))
        if key_files is None:
            return f"source '{s}'; its keys: sources.md, 'Source keys of each spec' (not read in this run: --no-merge)"
        km = key_files.get(p, {})
        ks = sorted(merge_tables.keys_in(s, km), key=s.find)
        return f"source '{s}'" + (f", keys of spec/{p}.md: " + ", ".join(
            f"{k} = {' and '.join(km[k]) or 'no file'}" for k in ks) if ks else "")

    nan3 = [float("nan")] * 3
    eye = an["frame"]["anchors"].get("lift.eye_left", {})
    parts6 = [f"[1] the left end is OPEN (DECISION 3, above); the Z line reads {val('frame', 'lift.eye_left')} only to "
              f"print the lifting eyes it leaves out (Z {eye.get('xyz', nan3)[2]:g}): they are anchors, not bodies, and the "
              f"check compares bodies only, so that error cannot flip it",
              f"[2] table top Z {tt['xyz'][2]:g} is {tt.get('class', '?')} {tt_err} (frame anchors table.top error_mm; "
              f"frame measure row M4; OM p.19 elevation; W 900): the model takes this estimate, so the check cannot "
              f"fail on it; the true height waits for M4"]
    kr = [r for r in ((mdata or {}).get("rows_by_body", {}).get("knife.knife") or []) if set(r["letters"]) & set("EW")]
    if "knife.knife" in mans:
        k_lo, k_hi = bb(mans["knife.knife"])
        k_len = k_hi[0] - k_lo[0]
        if kr:
            r = kr[0]
            m = re.search(r"size\s*(?:\+-|±)\s*(\d+(?:[.,]\d+)?)", r["error"])
            e = num(m.group(1)) if m else None
            flip = (f"margin {k_len - 1150:.0f} {'>' if e is not None and k_len - 1150 > e else 'vs'} size error "
                    f"{e:g}, so the verdict {'cannot' if e is not None and k_len - 1150 > e else 'can'} flip"
                    if e is not None else f"margin {k_len - 1150:.0f}; the size error is not a number")
            parts6.append(f"[3] knife length {k_len:.0f} is {r['class']} (web price list) with error '{r['error']}' "
                          f"(sources.md row knife.knife, {r['line']}; measure rows {', '.join(r['refs']) or '-'}): "
                          f"the check needs >= 1150, {flip}")
        else:
            parts6.append(f"[3] knife length {k_len:.0f} is W 1320 (web price list; class and error in sources.md "
                          f"row knife.knife, not read in this run: --no-merge)")
    # [4]: two halves, each computed from the anchors files (critic g9 F1): the clamp face stands on the table top;
    # the knife edge at rest has its own error, to be weighed against its margin over the pile height
    an_k, an_c = an["knife"]["anchors"], an["clamp"]["anchors"]
    cfa, kea, kba = an_c.get("clamp.face", {}), an_k.get("knife.edge.rest", {}), an_k.get("knife.edge.bottom", {})
    tz, cz, kz = tt["xyz"][2], cfa.get("xyz", nan3)[2], kea.get("xyz", nan3)[2]
    cfe, ke_err = cfa.get("error_mm"), kea.get("error_mm")
    cf_ez = cfe.get("z") if isinstance(cfe, dict) else cfe
    on_table = cf_ez == tt.get("error_mm") and "table.top" in str(cfa.get("source", ""))
    margin = kz - tz - 130
    flips = not isinstance(ke_err, (int, float)) or margin < ke_err
    ke_txt = f"{ke_err:g}" if isinstance(ke_err, (int, float)) else "(not given)"
    ks = (root / "spec" / "knife.md").read_text(encoding="utf-8").splitlines()
    srow = next(((i + 1, [c.strip() for c in ln.strip().strip("|").split("|")]) for i, ln in enumerate(ks)
                 if re.match(r"\|\s*stroke\s*\|", ln)), None)
    mrow = next((re.match(r"\|\s*(M\d+)\s*\|", ln).group(1) for ln in ks if re.match(r"\|\s*M\d+\s*\|\s*stroke\b", ln)),
                None)
    stroke_txt = (f"the stroke {srow[1][1]} is chosen (spec/knife.md:{srow[0]}: '{srow[1][2]}', {srow[1][3]} "
                  f"+-{srow[1][4]})" if srow and len(srow[1]) >= 5 else "the knife spec has no stroke row")
    settle = f"knife.{mrow} settles it" if mrow else "no measure row of the knife spec names the stroke"
    parts6.append(
        f"[4] reads {val('frame', 'table.top')}, {val('clamp', 'clamp.face')} and {val('knife', 'knife.edge.rest')}. "
        f"Clamp half: the clamp face at Z {cz:g} ({qsrc('clamp', cfa)}) "
        + (f"stands on the table top (its z error is the table top's +-{cf_ez:g}), so the difference {cz - tz:g} "
           f"against T 130 moves with the table and cannot flip" if on_table else
           f"has its own z error ({cf_ez}), so the difference {cz - tz:g} against T 130 +-{TOL_DT:g} can flip")
        + f". Knife half: the edge at rest at Z {kz:g} ({qsrc('knife', kea)}) stands {kz - tz:.2f} above "
          f"the table top, margin {margin:.2f} over 130 "
        + (f"< its error {ke_txt}, so this half CAN flip: {stroke_txt}, and {settle}" if flips else
           f">= its error {ke_txt}, so this half cannot flip ({stroke_txt}, and {settle})"))
    # [5]: the backgauge face takes its Z from the table top; the check compares its Y
    # (critic g10: the error weighed is the one on the axis the check compares, against the margin the tolerance leaves)
    bfa = an["backgauge"]["anchors"].get("backgauge.face", {})
    bfe = bfa.get("error_mm")
    by_err = bfe.get("y") if isinstance(bfe, dict) else bfe
    b_rest, bmo = bfa.get("xyz", nan3)[1], bfa.get("motion", {})
    b_front = b_rest + bmo.get("axis", [0, 0, 0])[1] * bmo.get("range", [0, float("nan")])[1]
    b_d = max(abs(b_rest - REQ["bg_rear"][0]), abs(b_front - REQ["bg_front"][0]))
    b_flip = not isinstance(by_err, (int, float)) or TOL_DT - b_d < by_err
    parts6.append(
        f"[5] reads {val('backgauge', 'backgauge.face')} ({qsrc('backgauge', bfa)}) and compares only its Y, "
        f"at both ends of the travel ({b_front:g} and {b_rest:g} against T {REQ['bg_front'][0]:g} and "
        f"{REQ['bg_rear'][0]:g}): the model takes the T numbers (difference up to {b_d:.1f}), so the check cannot fail on "
        f"the model, and on the machine its y error "
        f"{f'+-{by_err:g}' if isinstance(by_err, (int, float)) else '(not given)'} "
        + (f"exceeds the margin {TOL_DT - b_d:.1f} (+-{TOL_DT:g} less the difference), so the Y verdict CAN flip"
           if b_flip else f"does not exceed the margin {TOL_DT - b_d:.1f} (+-{TOL_DT:g} less the difference), so the "
           f"Y verdict cannot flip")
        + ". The estimated part is the Z it takes from the table top, which the check does not compare")
    # [6]: each quantity the check compares, weighed against the errors that stay on it, computed like [4] (tester 3,
    # round 3, item 13; critic g13). The clamp stroke is the range of clamp.face, a length. The knife stroke, the edge
    # at the bottom and the cut depth all come from the crank model (bottom = knife edge at rest - crank stroke). When
    # knife.edge.rest is knife.edge.bottom plus the range (the tie) and knife.edge.bottom stands on the stick top (the
    # share), bottom - anchor = range - crank stroke and depth = 0.15 + crank stroke - range: the crank anchors' errors
    # and the chosen stroke's stay on all three, and the two tests only decide which other errors are listed
    d6 = next(((c.get("data") or {}) for c in (checks or []) if c.get("check") == "6"), {})
    s6, r6, er6, b6, kb6, st6, dp6 = (d6.get(k, float("nan")) for k in
                                      ("stroke", "range", "edge_rest", "bottom", "kb", "stick_top", "depth"))
    d_lo, d_hi = REQ["cut_depth"][0]

    def zerr(a):
        e = a.get("error_mm")
        return e.get("z") if isinstance(e, dict) else e

    def fe(e):
        return f"+-{e:g}" if isinstance(e, (int, float)) else "(no error given)"

    def weigh(lst, margin):
        """(flips, text): the largest error that stays on a compared quantity, against the margin its tolerance leaves"""
        listed = ", ".join(f"{n} {fe(e)}" for n, e in lst)
        es = [e for _, e in lst]
        if not es or not all(isinstance(e, (int, float)) for e in es) or not margin >= 0:
            return True, f"on it stay {listed or 'no named errors'}, not all of them numbers, so it CAN flip"
        w = max(es)
        return w > margin, (f"on it stay {listed}, largest {w:g} "
                            + (f"> the margin {margin:.2f}, so it CAN flip" if w > margin else
                               f"<= the margin {margin:.2f}, so it cannot flip"))

    def qkeys(p, s):
        """the spec-local keys a quoted text uses, written out as the files spec/<p>.md resolves them to"""
        if key_files is None:
            return " (its keys: sources.md, 'Source keys of each spec')"
        km = key_files.get(p, {})
        ks_ = sorted(merge_tables.keys_in(s, km), key=s.find)
        return (f" (keys of spec/{p}.md: " + ", ".join(f"{k} = {' and '.join(km[k]) or 'no file'}" for k in ks_)
                + ")") if ks_ else ""

    # clamp stroke: a length; it cannot flip only when the range is a number its D or T source names, with no error
    # of its own (an error_mm in the motion would be weighed against the margin)
    cmo = cfa.get("motion", {})
    c_rng, c_t = (cmo.get("range") or [0, float("nan")])[1], REQ["clamp_stroke"][0]
    c_m = TOL_DT - abs(c_rng - c_t)
    c_named = any(abs(num(x) - c_rng) < 1e-6
                  for x in re.findall(r"(?<![\w.,])\d+(?:[.,]\d+)?(?!\w)", str(cfa.get("source", ""))))
    c_dt = bool(set(str(cfa.get("class", ""))) & set("DT"))
    c_re = cmo.get("error_mm")
    c_flip = (not (c_named and c_dt)) if c_re is None else (not isinstance(c_re, (int, float)) or not c_m >= c_re)
    c_txt = (f"Clamp stroke: the range of clamp.face, {c_rng:g} against T {c_t:g} +-{TOL_DT:g} (margin {c_m:.1f}), is a "
             f"length ({qsrc('clamp', cfa)}), "
             + ((f"a number its source names, class {cfa.get('class')}, with no error of its own, so the z and y errors, "
                 f"which move the face and not the length, cannot flip it") if c_re is None and not c_flip else
                f"with its own error {fe(c_re)} <= the margin, so it cannot flip" if not c_flip else
                f"with its own error {fe(c_re)} > the margin, so it CAN flip" if c_re is not None else
                "not a number its D or T source names, so it CAN flip"))
    # the knife: the tie and the share tested on the anchors files
    sta = an["frame"]["anchors"].get("cutting_stick.top", {})
    kz_rest, kz_bot = kea.get("xyz", nan3)[2], kba.get("xyz", nan3)[2]
    k_rng = (kea.get("motion", {}).get("range") or [0, float("nan")])[1]
    tied = abs((kz_rest - kz_bot) - k_rng) <= 1e-3
    shared = zerr(kba) == zerr(sta) and "stick top" in str(kba.get("source", ""))
    on_s = [(n, zerr(an_k.get(n, {}))) for n in KNIFE_CRANK] + [("knife.edge.rest", zerr(kea))]
    on_b = on_s + ([] if tied else [("knife.edge.bottom", zerr(kba))])
    on_d = on_s + ([] if tied and shared else [("knife.edge.bottom", zerr(kba)),
                                               ("frame anchor cutting_stick.top", zerr(sta))])
    f_s, t_s = weigh(on_s, TOL_STROKE - abs(s6 - r6))
    f_b, t_b = weigh(on_b, TOL_BOTTOM - abs(b6 - kb6))
    f_d, t_d = weigh(on_d, min(dp6 - d_lo, d_hi - dp6))
    # what knife.edge.rest's error is: its spec row (critic g13: the height the two share cancels, that error does not)
    erow = next(((i + 1, ln) for i, ln in enumerate(ks) if re.match(r"\|\s*edge_z_rest\s*\|", ln)), None)
    e_der = re.search(r"derived:\s*([^|]*?)\s*\|", erow[1]) if erow else None
    e_of = "the chosen stroke's error" if e_der and "stroke" in e_der.group(1) else "its own error"
    e_at = ((f"spec/knife.md:{erow[0]}" + (f", edge_z_rest derived as {e_der.group(1)}" if e_der else ""))
            if erow else "spec/knife.md has no edge_z_rest row")
    tie_txt = (f"knife.edge.rest is knife.edge.bottom plus the range ({kz_rest:g} - {kz_bot:g} = {k_rng:g}), so the "
               f"height they share cancels (knife.edge.bottom's z error {fe(zerr(kba))} is not on it) and "
               f"knife.edge.rest's {fe(zerr(kea))}, {e_of} ({e_at}), does not" if tied else
               f"knife.edge.rest is not knife.edge.bottom plus the range ({kz_rest:g} - {kz_bot:g} = "
               f"{kz_rest - kz_bot:g}, range {k_rng:g}), so knife.edge.bottom's error is on it too")
    dep_txt = (f"knife.edge.bottom's z error is the stick top's ({fe(zerr(sta))}, frame anchor cutting_stick.top) and its "
               f"source names the stick top, so with the tie the stick's error cancels as well" if tied and shared else
               "the tie is broken, so the stick top's and knife.edge.bottom's errors are on it" if not tied else
               f"knife.edge.bottom's z error {fe(zerr(kba))} is not the stick top's {fe(zerr(sta))} (frame anchor "
               f"cutting_stick.top) or its source does not name the stick top, so both errors are on it")
    # the knife spec's conflict that the motion note of knife.edge.rest names, and the rows that settle the crank
    cn = re.search(r"conflict (\d+)", str(kea.get("motion", {}).get("note", "")))
    ci = next((i for i, ln in enumerate(ks) if ln.startswith("## Conflicts")), None)
    sect = []
    for ln in (ks[ci + 1:] if ci is not None else []):
        if ln.startswith("## "):
            break
        sect.append(ln)
    cline = next((ln for ln in sect if cn and re.match(rf"{cn.group(1)}\.\s", ln)), "")
    conf_txt = ""
    if cline:
        head = re.match(r"\d+\.\s*([^.]*)\.", cline)
        bits = [f"modelled: {m.group(1)}" for m in [re.search(r"Modelled: ([^.]+)\.", cline)] if m]
        bits += [f"crank radius {m.group(1)} derived from the stroke {m.group(2)}"
                 for m in [re.search(r"r (\d+(?:,\d+)?) is derived[^.]*?from stroke (\d+)", cline)] if m]
        bits += [f"against the drawn {m.group(1)} ({m.group(2)})"
                 for m in [re.search(r"sits (\d+\s*-\s*\d+) from the wheel centre \((\w+)\)", cline)] if m]
        quoted = (head.group(1) if head else "") + (": " + ", ".join(bits) if bits else "")
        conf_txt = f"The knife path and the crank are conflict {cn.group(1)} of spec/knife.md ('{quoted}'){qkeys('knife', quoted)}"
    crow = next((re.match(r"\|\s*(M\d+)\s*\|", ln).group(1) for ln in ks
                 if re.match(r"\|\s*M\d+\s*\|[^|]*\bcrank centre\b", ln)), None)
    rows6 = [f"knife.{r}" for r in (mrow, crow) if r]
    flips6 = [q for q, f in (("the knife stroke", f_s), ("the edge at the bottom", f_b), ("the cut depth", f_d)) if f]
    cam = "S12-S14" in str(an_k.get("crank.centre", {}).get("motion", {}).get("note", ""))
    parts6.append(
        f"[6] reads {val('clamp', 'clamp.face')}, {val('knife', 'knife.edge.rest')}, {val('knife', 'knife.edge.bottom')} "
        f"and, through the knife motion of the motion model, {', '.join(val('knife', n) for n in KNIFE_CRANK)}, and each "
        f"quantity it compares is weighed against the errors that stay on it. {c_txt}. "
        f"Knife stroke: the crank model gives {s6:.2f} against the range of knife.edge.rest, {r6:g} +-{TOL_STROKE:g} "
        f"(margin {TOL_STROKE - abs(s6 - r6):.2f}), the range being the chosen stroke ({stroke_txt}): {t_s}. "
        f"Edge at the bottom: the knife body's edge at rest {er6:.2f} less the crank stroke, {b6:.2f}, against "
        f"knife.edge.bottom {kb6:.2f} +-{TOL_BOTTOM:g} (margin {TOL_BOTTOM - abs(b6 - kb6):.2f}): {tie_txt}, and {t_b}. "
        f"Cut depth: the cutting-stick top {st6:.2f} less that bottom, {dp6:.2f}, in {d_lo:g}..{d_hi:g} (margin "
        f"{min(dp6 - d_lo, d_hi - dp6):.2f}): {dep_txt} ({qsrc('knife', kba)}), and {t_d}. "
        + (f"{conf_txt}. " if conf_txt else "")
        + ((("So " + (", ".join(flips6[:-1]) + " and " if len(flips6) > 1 else "") + flips6[-1] + " CAN flip until "
             + (" and ".join(rows6) or "a site measurement") + " settle the stroke and the crank")
            if flips6 else "So none of the three knife quantities can flip")
           + (". The S12-S14 cam turns on the same crank shaft (crank.centre motion note), so its switching angles "
              "wait for the same rows" if cam and flips6 else "")
           + ". On the machine the depth is set as on OM p.21 (20261115_012035)"))
    # [12]: line A and the bolts placed partly from the drawing's scale (class D/P)
    fan = an["frame"]["anchors"]
    bolts_pe = [n for n in sorted(fan) if n.startswith("anchor_bolt.") and is_estimated(fan[n].get("class", "?"))]
    c12 = (f"[12] reads {val('frame', 'y_anchor_line_A')} (Y {fm.get('y_anchor_line_A')}, frame.M1): the foot and pad "
           f"offsets are measured from it, so its error cannot flip them, and where the line really is waits for "
           f"frame.M1")
    if bolts_pe:
        # the axis the check compares is X (critic g10): its error against the margin the +-TOL_DT leaves
        def axis_err(n, k):
            e = fan[n].get("error_mm")
            return e.get(k) if isinstance(e, dict) else e
        bdx = max(min(abs(fan[n]["xyz"][0] - x) for x in REQ["bolt_x"][0]) for n in bolts_pe)
        exs = [axis_err(n, "x") for n in bolts_pe]
        ex = max(exs) if all(isinstance(e, (int, float)) for e in exs) else None
        eys = sorted({axis_err(n, "y") for n in bolts_pe if isinstance(axis_err(n, "y"), (int, float))})
        b_flip = ex is None or TOL_DT - bdx < ex
        fs = (root / "spec" / "frame.md").read_text(encoding="utf-8").splitlines()
        bm = next((re.match(r"\|\s*(M\d+)\s*\|", ln).group(1) for ln in fs
                   if re.match(r"\|\s*M\d+\s*\|[^|]*\bX\b[^|]*bolt", ln)), None)
        c12 += (f". It reads {' and '.join(val('frame', n) for n in bolts_pe)} and compares only their X with the D "
                f"numbers {REQ['bolt_x'][0][0]:g} / +{REQ['bolt_x'][0][1]:g}, which the model takes (difference up to "
                f"{bdx:.1f}), so the check cannot fail on the model, and on the machine their x error "
                f"{f'+-{ex:g}' if ex is not None else '(not given)'} "
                + (f"exceeds the margin {TOL_DT - bdx:.1f} (+-{TOL_DT:g} less the difference), so the X verdict CAN "
                   f"flip, and " + (f"frame.{bm} settles it" if bm else "no frame measure row names the bolt X")
                   if b_flip else f"does not exceed the margin {TOL_DT - bdx:.1f} (+-{TOL_DT:g} less the difference), "
                   f"so the X verdict cannot flip")
                + (f". Their y error ({', '.join(f'+-{v:g}' for v in eys)}) is not compared" if eys else ""))
    parts6.append(c12)
    if mdata:
        parts6.append(f"[7], [8] and [9] compare the model with the specs and with itself; {mdata['e_or_w_rows']} of "
                      f"{mdata['source_rows']} source rows are E or W (sources.md), so they show that the parts fit as "
                      f"specified, not that the specified sizes are true")
    items.append("checks on estimated values (value, class, error, can the verdict flip within it): "
                 + "; ".join(parts6))
    env = sorted(n for p in PARTS for n, a in an[p]["anchors"].items()
                 if (n.startswith("envelope.") or n.startswith("corridor.")) and isinstance(a, dict) and "min" in a)
    items.append(f"clamp open item 4: the {len(env)} envelope and corridor boxes ({', '.join(env)}) stay JSON-only "
                 f"keep-out boxes, not bodies; check 8e tests each against every mesh of the other parts and against "
                 f"each other; the viewer shows their centre anchors only")
    items.append("safety_sensors: S19's actuation not known (SS5); S28 sits in a pocket of clamp.front_block "
                 "(clamp open item 5)")
    return items


if __name__ == "__main__":
    sys.exit(main())
