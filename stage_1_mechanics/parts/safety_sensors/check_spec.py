"""Checks the safety_sensors part (thread 6) against spec/safety_sensors.md and the five host parts.

  A  build: 18 bodies, one per Bodies row; each body's bounds = the spec solid on its host anchor (+-1 mm,
     check 7); watertight, volume > 0; part bounds printed
  B  inventory: 28 designations + cabinet, each once; host-body rows name a node of the host GLB; FF1 no body
  C  anchors (check 10): every section-10 device and the cabinet exactly once over all out/*_anchors.json
     (this part publishes none of them: only body.<id>); fields xyz, class, error_mm, source, motion
  D  at rest (check 8): no body overlaps a host body (<= 1 mm3) or another body of this part; the one excused
     overlap, S28 x clamp.front_block, lies inside the clamp's S28 zone
  E  sweeps (check 9): no fixed body meets a moving host part over its whole stroke (hosts.SWEEPS: knife down,
     crank turn, lock pin, clamp beam, piston, pedal, backgauge 25..1150) or a host keep-out box; S28 swept
     with the beam meets nothing outside the beam
  F  actuators: each actuation point lies on its body; S30, S28, S5 touch their target; face bodies touch
     their face from outside
  G  spec rows: class, error, source in every row; every source key is in the Sources table; every E or P
     row has a measure row (SS..) naming it; a host row cited as "<host> <id>" or a list of them (housing M3;
     housing M12, M3; housing rows M12 and M3) is stripped first, so it never counts as a body's row
Run:  python stage_1_mechanics/parts/safety_sensors/check_spec.py [--out <dir>] [--spec <md>]
Last line: check_spec safety_sensors: ALL PASS  (exit 0), else FAIL (exit 1).
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

import hosts
import safety_sensors as ss

R = hosts.R
DEVICES = ["button.S10", "button.S11", "button.S1", "sensor.FF1", "sensor.S12", "sensor.S13", "sensor.S14",
           "sensor.SQ1", "sensor.SQ2", "magnet.Y01", "clutch.Y10", "sensor.S19", "sensor.S5", "sensor.S30",
           "sensor.S28", "valve.Y11", "brake.Y14", "sensor.S24", "sensor.S27", "sensor.BR40", "motor.M1",
           "motor.M2", "motor.M3", "valve.Y3", "switch.Q1", "switch.Q2", "switch.S2", "switch.S4"]
KINDS = tuple(sorted({d.split(".")[0] + "." for d in DEVICES} | {"cabinet."}))
TOUCH = {"S30": "clamp.bar", "S28": "clamp.false_plate", "S5": "housing.belt_pulley_cover"}
FACE = {"S10": "frame.table", "S11": "frame.table", "S1": "housing.console", "Q1": "housing.cabinet",
        "Q2": "housing.cabinet", "S2": "housing.cabinet", "S4": "housing.cabinet"}
ok = True


def check(good, msg):
    global ok
    ok &= bool(good)
    print(("PASS " if good else "FAIL ") + msg)


def cube(c, h):
    c = np.array(c, float)
    return mf.Manifold.cube([2 * h] * 3).translate((c - h).tolist())


def bb(m):
    return np.array(m.bounding_box()).reshape(2, 3)


def main(argv):
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else R / "out"
    spec = Path(argv[argv.index("--spec") + 1]) if "--spec" in argv else ss.SPEC
    text = spec.read_text(encoding="utf-8")
    rows = ss.read_spec(spec)
    anchors = hosts.load_anchors(out)

    # A build
    scene = trimesh.load(out / "safety_sensors.glb", force="scene")
    mine = {n: hosts.to_manifold(scene.geometry[scene.graph[n][1]]) for n in scene.graph.nodes_geometry}
    check(len(rows) == 18 and sorted(mine) == sorted("safety_sensors." + r["id"] for r in rows),
          f"A 18 bodies, one per Bodies row ({len(mine)} nodes, {len(rows)} rows)")
    bad = []
    for r in rows:
        want = bb(ss.build_row(r, anchors))
        got = bb(mine["safety_sensors." + r["id"]])
        if np.abs(want - got).max() > 1:
            bad.append(f"{r['id']} {np.round(got, 1).tolist()} vs spec {np.round(want, 1).tolist()}")
    check(not bad, f"A7 every body's bounds = its spec solid on its host anchor within 1 mm {bad or ''}")
    tms = [scene.geometry[scene.graph[n][1]] for n in scene.graph.nodes_geometry]
    check(all(t.is_watertight and t.volume > 0 for t in tms), "A watertight bodies with volume > 0")
    stl = trimesh.load(out / "safety_sensors.stl")
    allb = np.array([bb(m) for m in mine.values()])
    pb = np.array([allb[:, 0].min(0), allb[:, 1].max(0)])
    check(np.abs(stl.bounds - pb).max() < 0.01, f"A STL = GLB, part bounds {np.round(pb, 1).tolist()}")

    # B inventory
    inv = ss.table(text, "## Inventory", "Not in this part")
    names = [c[0] for c in inv]
    want_inv = [d.split(".")[1] for d in DEVICES] + ["cabinet"]
    check(sorted(names) == sorted(want_inv), f"B inventory: 28 designations + cabinet, each once ({len(names)} rows)")
    host_nodes = set(hosts.load_bodies(out).keys())
    miss = []
    for c in inv:
        cell = c[4]
        if cell.startswith("host:"):
            node = cell.split(":", 1)[1].split("(")[0].strip()
            if node not in host_nodes:
                miss.append(node)
        elif cell.startswith("safety_sensors."):
            if cell not in mine:
                miss.append(cell)
    check(not miss, f"B host-body rows name existing host nodes, body rows existing nodes {miss or ''}")
    ff1 = [c for c in inv if c[0] == "FF1"][0]
    check(ff1[4].startswith("none") and "safety_sensors.FF1" not in mine, "B FF1: not fitted, no body")

    # C anchors
    files = {f.name: json.loads(f.read_text(encoding="utf-8"))["anchors"] for f in sorted(out.glob("*_anchors.json"))}
    cnt = {d: sum(d in a for a in files.values()) for d in DEVICES}
    cab = sum(n.startswith("cabinet.") for a in files.values() for n in a)
    check(all(v == 1 for v in cnt.values()) and cab == 1,
          f"C10 each device once over {len(files)} anchors files, cabinet.* {cab} {[d for d, v in cnt.items() if v != 1] or ''}")
    own = files.get("safety_sensors_anchors.json", {})
    check(sorted(own) == sorted("body." + r["id"] for r in rows) and not any(n.startswith(KINDS) for n in own),
          f"C own anchors are body.<id> only ({len(own)}), no device kind prefix")
    check(all(all(k in a for k in ("xyz", "class", "error_mm", "source", "motion")) for a in own.values()),
          "C own anchors carry xyz, class, error_mm, source, motion")

    # D at rest
    obs = hosts.obstacles(out)
    rest = {n: m for n, m in obs.items() if not n.startswith(("sweep:", "keepout:"))}
    zone = np.array(anchors["clamp"]["sensor.S28"]["zone"], float).T          # [[x0,y0,z0],[x1,y1,z1]]
    hits = []
    for r in rows:
        m = mine["safety_sensors." + r["id"]]
        for n, v in hosts.clash(m, rest).items():
            if r["id"] == "S28" and n == "clamp.front_block":
                ib = bb(m ^ rest[n])
                inside = np.all(ib[0] >= zone[0] - 0.01) and np.all(ib[1] <= zone[1] + 0.01)
                check(inside, f"D the excused overlap S28 x clamp.front_block ({v:.0f} mm3) lies in the S28 zone")
                continue
            if v > 1:
                hits.append(f"{r['id']} x {n} {v:.0f}")
    ids = list(mine)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            v = (mine[a] ^ mine[b]).volume()
            if v > 1:
                hits.append(f"{a} x {b} {v:.0f}")
    check(not hits, f"D8 at rest no overlap with host bodies or between own bodies {hits or ''}")

    # E sweeps
    beam = {n for names, part, _ in hosts.moving_sets(out) if part == "clamp" for n in names
            if anchors["clamp"].get("clamp.face")}
    beam = {n for n in beam if json.loads((out / "clamp_anchors.json").read_text(encoding="utf-8"))["meta"]["bodies"]
            .get(n, {}).get("group") == "beam"}
    hits = []
    for r in rows:
        m = mine["safety_sensors." + r["id"]]
        mot = ss.parse_motion(r["motion"])
        if mot["kind"] == "fixed":
            for n, v in hosts.clash(m, {k: o for k, o in obs.items() if k.startswith(("sweep:", "keepout:"))}).items():
                if v > 1:
                    hits.append(f"{r['id']} x {n} {v:.0f}")
        else:
            sw = hosts.sweep(m, {"kind": "trans", "axis": mot["axis"], "range": mot["range"]})
            skip = beam | {"sweep:" + n for n in beam}
            for n, v in hosts.clash(sw, obs, skip).items():
                if v > 1:
                    hits.append(f"{r['id']} swept x {n} {v:.0f}")
    check(not hits, f"E9 no body meets a moving host part over its stroke or a keep-out box {hits or ''}")

    # F actuators
    far, miss = [], []
    for r in rows:
        p, d, _ = ss.actuator(r, anchors)
        m = mine["safety_sensors." + r["id"]]
        if (cube(p, 0.6) ^ m).is_empty():
            far.append(r["id"])
        if r["id"] in TOUCH and (cube(p, 1.0) ^ rest[TOUCH[r["id"]]]).is_empty():
            miss.append(f"{r['id']}->{TOUCH[r['id']]}")
        if r["id"] in FACE:
            b = bb(m)
            back = b[1].copy()
            slab = mf.Manifold.cube([b[1][0] - b[0][0], 1.0, b[1][2] - b[0][2]]).translate([b[0][0], b[1][1], b[0][2]])
            if (slab ^ rest[FACE[r["id"]]]).is_empty() or not hosts.clash(slab, {"h": rest[FACE[r["id"]]]}):
                miss.append(f"{r['id']} face")
    check(not far, f"F each actuation point lies on its body {far or ''}")
    check(not miss, f"F S30, S28, S5 touch their targets; face bodies touch their face from outside {miss or ''}")

    # G spec rows
    keys = {c[0] for c in ss.table(text, "## Sources", "## Inventory")}
    meas = ss.table(text, "## Measure and photo rows", "## Gaps")
    # A host's own row cited as "<host> <id>" (housing M3, knife M9, backgauge S24) is the host's, never a body's:
    # strip such citations first, or "housing M3" would pass as motor M3's measure row.  A citation may name a
    # list ("housing M12, M3", "housing rows M3 and M12", "frame M14-M15"): the whole list is stripped.
    rid = r"(?:rows?\s+)?[A-Za-z]+\d+"
    sep = r"\s*(?:,|;|/|-|–|\.\.|\band\b|\bor\b)\s*"
    cite = re.compile(rf"\b(?:frame|knife|clamp|backgauge|housing|assembly)(?:'s)?\s+{rid}(?:{sep}{rid})*\b", re.I)
    meas_text = [cite.sub(" ", " ".join(c)) for c in meas]
    bad = []
    for r in rows:
        if not (r["class"] and r["error"] and r["source"]):
            bad.append(f"{r['id']} empty")
        for k in re.findall(r"\b(P\d\d|F\d+|PH\d+|PL\d|W\d+|CERT)\b", r["source"]):
            if k not in keys:
                bad.append(f"{r['id']} key {k}")
        if ("E" in r["class"] or "P" in r["class"]) and not any(re.search(rf"\b{r['id']}\b", t) for t in meas_text):
            bad.append(f"{r['id']} no measure row")
    check(not bad, f"G11 rows have class, error, source; keys defined; E/P rows have a measure row {bad or ''}")
    print("check_spec safety_sensors:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
