"""Host geometry for the safety_sensors thread (thread 6): loads the five closed parts' bodies at rest.

Used by safety_sensors.py (nothing), check_spec.py (clash, sweep) and place_probe.py (free space).
Bodies come from out/<part>.glb (millimetres, machine coordinates, Z up, at rest), anchors from
out/<part>_anchors.json; both are read at run time, never copied.
"""
import json
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

R = Path(__file__).resolve().parents[2]          # stage_1_mechanics
HOSTS = ("frame", "knife", "clamp", "backgauge", "housing")


def to_manifold(tm):
    mesh = mf.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                   tri_verts=np.asarray(tm.faces, dtype=np.uint32))
    return mf.Manifold(mesh)


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3].astype(np.float64),
                           np.asarray(mesh.tri_verts), process=True)


def load_bodies(out=None, parts=HOSTS):
    """-> {body name: trimesh} for every node of out/<part>.glb (scene transforms applied)."""
    out = Path(out) if out else R / "out"
    bodies = {}
    for p in parts:
        scene = trimesh.load(out / f"{p}.glb", force="scene")
        for node in scene.graph.nodes_geometry:
            T, gname = scene.graph[node]
            tm = scene.geometry[gname].copy()
            tm.apply_transform(T)
            bodies[node] = tm
    return bodies


def load_anchors(out=None, parts=HOSTS):
    """-> {part: anchors dict} from out/<part>_anchors.json."""
    out = Path(out) if out else R / "out"
    return {p: json.loads((out / f"{p}_anchors.json").read_text(encoding="utf-8"))["anchors"] for p in parts}


def find_anchor(anchors, name):
    """-> (part, anchor dict) for a name published by exactly one part, else raises."""
    hits = [(p, a[name]) for p, a in anchors.items() if name in a]
    if len(hits) != 1:
        raise KeyError(f"anchor {name}: found in {[p for p, _ in hits]} (need exactly one host)")
    return hits[0]


def clash(m, host_mf, skip=()):
    """Intersection volumes (mm3) of manifold m with every host manifold whose bbox overlaps; -> {name: vol}."""
    res = {}
    b0 = np.array(m.bounding_box()).reshape(2, 3) if hasattr(m, "bounding_box") else None
    for n, h in host_mf.items():
        if n in skip:
            continue
        hb = np.array(h.bounding_box()).reshape(2, 3)
        if b0 is not None and (np.any(b0[1] < hb[0] - 1e-6) or np.any(hb[1] < b0[0] - 1e-6)):
            continue
        v = (m ^ h).volume()
        if v > 1e-3:
            res[n] = v
    return res


# ---------------------------------------------------------------- moving hosts and keep-out boxes
# Which host bodies move, and with the motion of which host anchor (read at run time).  Round bodies that
# turn about their own axis (flywheel, clutch, worm, motors, pump, spindle, gear 8, knobs) occupy the same
# space in every pose, so their rest body is their sweep.  The conrod's planar motion is covered by the hull
# of its rest pose, its pose with the knife at the bottom and the swept crank pin (conservative).
SWEEPS = [
    (("knife.knife", "knife.holder", "knife.holder_pin"), "knife", "knife.edge.rest"),
    (("knife.crank_pin", "knife.crank_disc", "knife.cam_disc", "knife.worm_wheel", "knife.flange_2",
      "knife.crank_shaft"), "knife", "crank.centre"),
    (("knife.lock_pin_1", "knife.y01_tail"), "knife", "lock.pin_1"),
    ("group:beam", "clamp", "clamp.face"),
    ("group:piston", "clamp", "piston.OA1"),
    ("group:pedal", "clamp", "pedal.5"),
    ("group:moving", "backgauge", "backgauge.face"),
]
KEEPOUT = ("envelope.", "space.", "frame.keepout.", "corridor.", "table.slot")
TRANS_STEP, ROT_STEP = 10.0, 5.0


def _rot(m, axis, pivot, deg):
    """Right-handed turn of manifold m by deg about axis through pivot."""
    a = np.array(axis, float) / np.linalg.norm(axis)
    t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    Rm = np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K
    p = np.array(pivot, float)
    T = np.hstack([Rm, (p - Rm @ p).reshape(3, 1)])
    return m.transform(T.tolist())


def poses(m, motion, step_t=TRANS_STEP, step_r=ROT_STEP):
    """Manifold m in every pose of motion (trans: every <= step_t mm; rot: every <= step_r deg)."""
    lo, hi = motion["range"]
    if motion["kind"] == "trans":
        n = max(1, int(np.ceil((hi - lo) / step_t)))
        ax = np.array(motion["axis"], float)
        return [m.translate((ax * v).tolist()) for v in np.linspace(lo, hi, n + 1)]
    if motion["kind"] == "rot":
        n = max(1, int(np.ceil((hi - lo) / step_r)))
        return [_rot(m, motion["axis"], motion["pivot"], v) for v in np.linspace(lo, hi, n + 1)]
    return [m]


def sweep(m, motion):
    """Union of all poses (exact up to the step)."""
    return mf.Manifold.batch_boolean(poses(m, motion), mf.OpType.Add)


def moving_sets(out=None):
    """-> list of (body names, host part, motion dict) for the moving host bodies."""
    out = Path(out) if out else R / "out"
    anchors = load_anchors(out)
    metas = {p: json.loads((out / f"{p}_anchors.json").read_text(encoding="utf-8"))["meta"] for p in HOSTS}
    res = []
    for names, part, anc in SWEEPS:
        if isinstance(names, str):
            g = names.split(":", 1)[1]
            names = tuple(n for n, b in metas[part].get("bodies", {}).items() if b.get("group") == g)
        res.append((names, part, anchors[part][anc]["motion"]))
    return res


def obstacles(out=None, with_sweeps=True):
    """-> {name: manifold}: every host body at rest, the sweep of every moving host body ('sweep:<body>'),
    the conrod hull ('sweep:knife.conrod') and every keep-out box the hosts publish ('keepout:<anchor>')."""
    out = Path(out) if out else R / "out"
    bodies = {n: to_manifold(t) for n, t in load_bodies(out).items()}
    obs = dict(bodies)
    if with_sweeps:
        knife_motion = None
        for names, part, motion in moving_sets(out):
            for n in names:
                if n in bodies:
                    obs["sweep:" + n] = sweep(bodies[n], motion)
            if names and names[0] == "knife.knife":
                knife_motion = motion
        if "knife.conrod" in bodies and knife_motion and "sweep:knife.crank_pin" in obs:
            c = bodies["knife.conrod"]
            obs["sweep:knife.conrod"] = mf.Manifold.batch_hull(
                [c, c.translate((np.array(knife_motion["axis"]) * knife_motion["range"][1]).tolist()),
                 obs["sweep:knife.crank_pin"]])
    for part, anc in load_anchors(out).items():
        for n, a in anc.items():
            if n.startswith(KEEPOUT) and "min" in a and "max" in a:
                lo, hi = np.array(a["min"], float), np.array(a["max"], float)
                obs["keepout:" + n] = mf.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())
    return obs
