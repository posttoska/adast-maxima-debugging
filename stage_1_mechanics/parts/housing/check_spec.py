"""Checks out/housing.glb and out/housing_anchors.json against spec/housing.md (read here, not copied).

Run:  python check_spec.py [--sources <folder holding preparatory_data_analysis>]      Exit 0 = ALL PASS.
On a copy without preparatory_data_analysis next to its stage_1_mechanics, the sources are looked up in the
work folder C:/Users/ptsk/Documents/adast-maxima-debugging; the first line printed names the root used.
Checks (section 04 of the step plan: 7, 10, 11 for this part):
  A  every component row of the spec is a GLB node housing.<id> and back; bounds within +-1 mm
  B  every component row has resolvable source keys, a class (D/T/P/E/W), an error with +-,
     and a P or E row names measure rows that exist
  C  the anchors table equals housing_anchors.json (names, xyz within 1 mm, class, error within 0.5 mm, every source key of
     the spec row named in the JSON source); P or E anchors name a measure row
  D  button.S1, switch.Q1, switch.Q2, switch.S2, switch.S4, lamp.E1..E4, connector.XC1..XC4 and one cabinet.* anchor exist exactly once
     across out/*_anchors.json
  E  every source key's file exists; every crop the spec names exists
  F  every Z read on F102 by its scale (switch.Q1/Q2/S4/S2, connector.XC1-XC4) lies within 0.5 mm of
     cabinet top - (y - top y) x mm/px for the y its anchor row prints; the F102 row's own y and Z lists agree
  G  every anchor citing PH152550 gives its pixel x and ratio; the ratio and its X follow from the row's inner faces
     and the NB row's frame columns (left inner face + ratio x opening, within 1 mm); the row's O = right - left
"""
import json
import re
import sys
from pathlib import Path

import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                 # stage_1_mechanics (of the work folder or of a copy)
SPEC = ROOT / "spec" / "housing.md"
OUT = ROOT / "out"
WORK_FOLDER = Path("C:/Users/ptsk/Documents/adast-maxima-debugging")   # fallback when run on a copy


def source_root(argv):
    """Folder holding preparatory_data_analysis: --sources <dir>; else next to stage_1_mechanics; else the work folder."""
    if "--sources" in argv:
        return Path(argv[argv.index("--sources") + 1]).resolve(), "--sources"
    if (ROOT.parent / "preparatory_data_analysis").is_dir():
        return ROOT.parent, "next to stage_1_mechanics"
    return WORK_FOLDER, "work-folder fallback (copy without preparatory_data_analysis)"


WORK, WORK_HOW = source_root(sys.argv)
PDA = WORK / "preparatory_data_analysis"
OM = PDA / "maxima_documents" / "adast_guillotine_operating_manual"
NUM = r"(-?\d+(?:\.\d+)?)"
BOUNDS = re.compile(rf"X {NUM}\.\.{NUM}; Y {NUM}\.\.{NUM}; Z {NUM}\.\.{NUM}")


def sections(text):
    out, cur = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = []
        elif cur:
            out[cur].append(line)
    return out


def rows(lines):
    r = []
    for line in lines:
        if line.startswith("| ") and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            r.append(cells)
    return r[1:]                          # drop the header row


def resolve(path_text):
    p = path_text.strip()
    if p.startswith("OM/"):
        return OM / p[3:]
    if p.startswith("maxima_"):
        return PDA / p
    if p.startswith("stage_1_mechanics/"):
        return ROOT / p[len("stage_1_mechanics/"):]          # this tree's own files (the copy's, on a copy)
    return WORK / p


F102_SWITCHES = ["switch.Q1", "switch.Q2", "switch.S4", "switch.S2"]
F102_CONNECTORS = ["connector.XC1", "connector.XC2", "connector.XC3", "connector.XC4"]


def check_f102(src_rows, arow, spec_b):
    """F: every Z read on F102 by its scale (Z = cabinet top - (y - top y) x mm/px) lies within 0.5 of that formula
    for the y its anchor row prints, and the F102 row's own y lists (switches; connector centres and their Z) agree."""
    bad = []
    f102 = next((c[2] for c in src_rows if c[0] == "F102"), "")
    top = re.search(r"top y (\d+)", f102)
    scale = re.search(r"at (\d+(?:\.\d+)?) mm/px", f102)
    sw = re.search(r"Q1 y (\d+), Q2 y (\d+), S4/S2 y (\d+)", f102)
    cn = re.search(r"stacked (XC\d+) \([^)]*\), (XC\d+) \([^)]*\), (XC\d+) and (XC\d+) \([^)]*\), "
                   r"drawn centres y (\d+) / (\d+) / (\d+) / (\d+), so Z (\d+) / (\d+) / (\d+) / (\d+)", f102)
    if not (top and scale and sw and cn and "cabinet" in spec_b):
        return False, f"F102 row or cabinet row unreadable: top {bool(top)}, scale {bool(scale)}, switches {bool(sw)}, " \
                      f"connectors {bool(cn)}, cabinet row {'cabinet' in spec_b}"
    y_top, k, z_top = float(top.group(1)), float(scale.group(1)), spec_b["cabinet"][5]

    def z_of(y):
        return z_top - (y - y_top) * k

    row_y = {}
    for name in F102_SWITCHES + F102_CONNECTORS:
        c = arow.get(name)
        m = re.search(r"F102 \((?:side strip )?y (\d+)", c[4]) if c else None
        if not m:
            bad.append(f"{name}: no 'F102 (y N' or 'F102 (side strip y N' in its anchor row")
            continue
        y, z = float(m.group(1)), float(c[1].split(",")[2])
        row_y[name] = y
        if abs(z - z_of(y)) > 0.5:
            bad.append(f"{name}: y {y:g} gives Z {z_of(y):.1f}, the anchor row holds {z:g}")
    for name, y in zip(F102_SWITCHES, [sw.group(1), sw.group(2), sw.group(3), sw.group(3)]):
        if name in row_y and row_y[name] != float(y):
            bad.append(f"{name}: F102 row y {y}, anchor row y {row_y[name]:g}")
    g = cn.groups()
    for i, xc in enumerate(g[0:4]):
        name, y, z = "connector." + xc, float(g[4 + i]), float(g[8 + i])
        if name not in F102_CONNECTORS:
            bad.append(f"F102 row names {xc}, not a connector anchor")
            continue
        if name in row_y and row_y[name] != y:
            bad.append(f"{name}: F102 row y {y:g}, anchor row y {row_y[name]:g}")
        if abs(z - z_of(y)) > 0.5:
            bad.append(f"{name}: F102 row y {y:g} gives Z {z_of(y):.1f}, the row prints Z {z:g}")
    if sorted(g[0:4]) != ["XC1", "XC2", "XC3", "XC4"]:
        bad.append(f"F102 row connectors {g[0:4]}")
    return not bad, f"top y {y_top:g} = Z {z_top:g}, {k} mm/px, {len(row_y)} anchors read on F102; problems {bad}"


def check_ph152550(src_rows, arows):
    """G: every anchor citing PH152550 gives 'x N = r O'; r within 0.0005 of (N - left) / (right - left), its X within
    1 mm of left inner face + r x opening (both from the NB row's frame columns); the row's O = right - left."""
    bad = []
    ph = next((c[2] for c in src_rows if c[0] == "PH152550"), "")
    nb = next((c[2] for c in src_rows if c[0] == "NB"), "")
    m = re.search(rf"left inner face x {NUM}, right x {NUM}, so opening O = {NUM} px", ph)
    f = re.search(rf"frame columns X {NUM}\.\.{NUM} / {NUM}\.\.", nb)
    if not (m and f):
        return False, f"PH152550 row readable {bool(m)}, NB frame columns readable {bool(f)}"
    left, right, o_px = (float(v) for v in m.groups())
    lx, rx = float(f.group(2)), float(f.group(3))
    if abs(o_px - (right - left)) > 0.5:
        bad.append(f"O = {o_px:g} px, but right - left = {right - left:g}")
    n, cites = 0, [c[0] for c in arows if "PH152550" in c[4]]
    for c in arows:
        for x, r in re.findall(r"PH152550 \([^)]*?x (\d+(?:\.\d+)?) = (\d+\.\d+) O", c[4]):
            n += 1
            exact = (float(x) - left) / (right - left)
            want, got = lx + exact * (rx - lx), float(c[1].split(",")[0])
            if abs(float(r) - exact) > 0.0005:
                bad.append(f"{c[0]}: x {x} gives {exact:.4f} O, the row prints {r}")
            if abs(got - want) > 1.0:
                bad.append(f"{c[0]}: x {x} gives X {want:.1f}, the row holds {got:g}")
    if n != len(cites):
        bad.append(f"{len(cites)} anchors cite PH152550, {n} give 'x N = r O'")
    return not bad, f"inner faces x {left:g} / {right:g}, O {o_px:g} px = {rx - lx:g} mm, {n} anchors; problems {bad}"


def main():
    print("sources root:", WORK, "|", WORK_HOW)
    text = SPEC.read_text(encoding="utf-8")
    sec = sections(text)
    res, ok = {}, True

    src_key = next(k for k in sec if k.startswith("Sources"))
    sources = {}
    for c in rows(sec[src_key]):
        sources[c[0]] = [resolve(p) for p in c[1].split(";")]
    missing_files = {k: [str(p) for p in v if not p.exists()] for k, v in sources.items()}
    missing_files = {k: v for k, v in missing_files.items() if v}
    crops = sorted(set(re.findall(r"\b([a-z_]+(?:_\d{6})?\.jpg)", text)))
    missing_crops = [c for c in crops if not (HERE / "crops" / c).exists()]
    res["E_source_files_and_crops"] = (not missing_files and not missing_crops,
                                       f"{len(sources)} keys, crops {crops}, missing {missing_files} {missing_crops}")

    meas = {c[0] for c in rows(sec[next(k for k in sec if k.startswith("Measure rows"))])}
    keys_sorted = sorted(sources, key=len, reverse=True)

    def keys_in(cell):
        return [k for k in keys_sorted if re.search(r"(?<![A-Za-z0-9])" + re.escape(k) + r"(?![A-Za-z0-9])", cell)]

    comp = rows(sec[next(k for k in sec if k.startswith("Components"))])
    spec_b, bad_rows = {}, []
    for c in comp:
        cid, bounds, srcs, cls, err = c[0], c[3], c[5], c[6], c[7]
        m = BOUNDS.search(bounds)
        if not m:
            bad_rows.append(f"{cid}: bounds unreadable")
            continue
        v = [float(x) for x in m.groups()]
        spec_b[cid] = v
        if not keys_in(srcs):
            bad_rows.append(f"{cid}: no source key")
        if not re.fullmatch(r"[DTPEW](/[DTPEW])*", cls):
            bad_rows.append(f"{cid}: class {cls!r}")
        if "+-" not in err:
            bad_rows.append(f"{cid}: error without +-")
        if re.search(r"[PE]", cls):
            refs = re.findall(r"M\d+", err)
            if not refs or any(r not in meas for r in refs):
                bad_rows.append(f"{cid}: measure rows {refs} not all in the table")
    res["B_component_rows"] = (not bad_rows, f"{len(comp)} rows; problems {bad_rows}")

    scene = trimesh.load(OUT / "housing.glb", force="scene")
    glb = {}
    for node in scene.graph.nodes_geometry:
        tf, g = scene.graph[node]
        tm = scene.geometry[g].copy()
        tm.apply_transform(tf)
        glb[node] = tm.bounds
    want = {"housing." + k for k in spec_b}
    diffs = []
    for k, v in spec_b.items():
        b = glb.get("housing." + k)
        if b is None:
            diffs.append(f"{k}: no GLB node")
            continue
        got = [b[0][0], b[1][0], b[0][1], b[1][1], b[0][2], b[1][2]]
        if any(abs(g - x) > 1.0 for g, x in zip(got, v)):
            diffs.append(f"{k}: GLB {[round(g, 1) for g in got]} vs spec {v}")
    extra = sorted(set(glb) - want)
    res["A_bounds_vs_spec"] = (not diffs and not extra, f"{len(spec_b)} bodies; diffs {diffs}; GLB nodes not in spec {extra}")

    arows = rows(sec[next(k for k in sec if k.startswith("Anchors"))])
    aj = json.loads((OUT / "housing_anchors.json").read_text(encoding="utf-8"))["anchors"]
    adiff = []
    for c in arows:
        name, xyz, cls, err = c[0], [float(x) for x in c[1].split(",")], c[2], c[3]
        j = aj.get(name)
        if j is None:
            adiff.append(f"{name}: not in JSON")
            continue
        if any(abs(a - b) > 1.0 for a, b in zip(xyz, j["xyz"])):
            adiff.append(f"{name}: spec {xyz} vs JSON {j['xyz']}")
        if cls != j["class"]:
            adiff.append(f"{name}: class {cls} vs {j['class']}")
        errs = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", err.split("(")[0])]
        jerr = j.get("error_mm")
        if not isinstance(jerr, list) or len(errs) != 3 or any(abs(a - b) > 0.5 for a, b in zip(errs, jerr)):
            adiff.append(f"{name}: error {errs} vs JSON {jerr}")
        skeys = keys_in(c[4])                     # every source key of the spec row must be named in the JSON source
        if not skeys:
            adiff.append(f"{name}: no source key in the spec row")
        lost = [k for k in skeys if k not in keys_in(j.get("source", ""))]
        if lost:
            adiff.append(f"{name}: source keys {lost} not in the JSON source")
        if re.search(r"[PE]", cls):
            refs = re.findall(r"M\d+", err)
            if not refs or any(r not in meas for r in refs):
                adiff.append(f"{name}: measure rows {refs}")
    extra_a = sorted(set(aj) - {c[0] for c in arows})
    res["C_anchors_vs_spec"] = (not adiff and not extra_a, f"{len(arows)} anchors; diffs {adiff}; JSON-only {extra_a}")

    need = ["button.S1", "switch.Q1", "switch.Q2", "switch.S2", "switch.S4", "lamp.E1", "lamp.E2", "lamp.E3", "lamp.E4",
            "connector.XC1", "connector.XC2", "connector.XC3", "connector.XC4"]
    cnt, cab = {n: 0 for n in need}, 0
    for f in sorted(OUT.glob("*_anchors.json")):
        for n in json.loads(f.read_text(encoding="utf-8"))["anchors"]:
            if n in cnt:
                cnt[n] += 1
            cab += n.startswith("cabinet.")
    res["D_devices_once"] = (all(v == 1 for v in cnt.values()) and cab == 1, f"{cnt}, cabinet.* {cab}")

    res["F_f102_scale"] = check_f102(rows(sec[src_key]), {c[0]: c for c in arows}, spec_b)
    res["G_ph152550_ratios"] = check_ph152550(rows(sec[src_key]), arows)

    for k, (good, info) in sorted(res.items()):
        print(k, "PASS" if good else "FAIL", "|", info)
        ok &= good
    print("check_spec housing:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
