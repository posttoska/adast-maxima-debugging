#!/usr/bin/env python3
"""Thread t5 (integration), part 5: the 12 checks of section 04 of the plan, run on the current files.

Run from the repository root (the folder that holds stage_1_mechanics and stage_2_electronics):
  python -B stage_2_electronics/checks/run_checks.py            all 12 checks; writes stage_2_electronics/checks/checks.txt
  python -B stage_2_electronics/checks/run_checks.py 4 9        checks 4 and 9 only, printed; checks.txt stays as it is
  python -B stage_2_electronics/checks/run_checks.py --make-manifest   writes checks/stage1_manifest.txt (check 10) from
                                                                 stage 1 as it is, only while git shows it unchanged
Each check is one function below (check_1 ... check_12). checks.txt holds one block per check with its counts, no time
stamps and no absolute paths: a rerun on the same files gives the same text. The run ends with "result: PASS" (exit 0)
or "result: FAIL" (exit 1). A check whose reference data is not on this computer (the tables of the local memory block,
the photos, the .git folder, stage 1) prints SKIP with the reason; it never prints PASS for what it could not check.
"""
import csv
import hashlib
import html
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent            # stage_2_electronics/checks
S = HERE.parent                                   # stage_2_electronics
P = S.parent                                      # repository root
S1 = P / "stage_1_mechanics"
T = P / "static_dynamic_memory" / "blocks" / "generation_002" / "artifacts"
THREADS = ("power", "control", "plc_drive")
SHEETS = {1: "power_sheet1.svg", 2: "power_sheet2.svg", 3: "power_sheet3.svg", 4: "control_sheet4.svg",
          5: "control_sheet5.svg", 6: "control_sheet6.svg", 7: "control_sheet7.svg", 8: "plc_sheet8.svg"}
NET = re.compile(r"://|\bfetch\s*\(|XMLHttpRequest|<link\b|<img\b|<iframe\b|\bsrc\s*=|@import|url\(|import\s*\(", re.I)
MARK = re.compile(r"^(sure|\[\?\]|estimated ±|W\b)")
MARK_RE = re.compile(r"^(\w+) MARKER (\S+) anchor (\S+) ([\d.]+) mm from (\S+); (\S+) ([\d.]+) mm from it, ([\d.]+) mm "
                     r"from (\S+); anchor to item ([\d.]+) mm(.*)$")


def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def texts(p):
    t = Path(p).read_text(encoding="utf-8")
    return [html.unescape(re.sub(r"<[^>]+>", "", m)) for m in re.findall(r"<text\b[^>]*>(.*?)</text>", t, re.S)]


def has_tok(name, blob):
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", blob) is not None


def thread_line_map(rows):
    seen, out = Counter(), []
    for r in rows:
        seen[r["thread"]] += 1
        out.append(seen[r["thread"]] + 1)
    return out


def fl(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


DEV = rd(S / "netlist/merged_devices.csv")
WIR = rd(S / "netlist/merged_wires.csv")
PLA = rd(S / "scheme_3d/placements.csv")
BUN = rd(S / "scheme_3d/bundles.csv")
NAMES = {d["designation"] for d in DEV}
KIND = {}
PLACE = {}
for d in DEV:                       # first non-empty value over the threads (power leaves the place of V01, V14, RC11,
    if d["kind"]:                   # V10 and R10 empty; control gives "machine")
        KIND.setdefault(d["designation"], d["kind"])
    if d["place"]:
        PLACE.setdefault(d["designation"], d["place"])
_CONTACT = {}


def contact_run():
    """contact_check.py (thread t4) run once per call of this script on the delivered layer; checks 6 and 9 read it.
    Returns (exit code, report lines or None when it wrote no new report)."""
    if "r" not in _CONTACT:
        rel = "stage_2_electronics/"
        rep = HERE / "contact_report_check9.txt"
        before = rep.stat().st_mtime_ns if rep.is_file() else None
        pr = subprocess.run([sys.executable, "-B", rel + "scheme_3d/contact_check.py", rel + "scheme_3d/electrical.glb",
                             rel + "scheme_3d/placements.csv", rel + "scheme_3d/bundles.csv",
                             rel + "checks/contact_report_check9.txt"], cwd=str(P), capture_output=True, text=True)
        new = rep.is_file() and rep.stat().st_mtime_ns != before
        _CONTACT["r"] = (pr.returncode, rep.read_text(encoding="utf-8").splitlines() if new else None)
    return _CONTACT["r"]


def item_meshes():
    """every node of electrical.glb in its world frame, as stage 1's loader reads it (no rescaling: the numbers are mm)"""
    import trimesh
    sc = trimesh.load(str(S / "scheme_3d/electrical.glb"), force="scene")
    out = {}
    for node in sc.graph.nodes_geometry:
        tf, g = sc.graph[node]
        m = sc.geometry[g].copy()
        m.apply_transform(tf)
        out[node] = m
    return out


def body_bounds(names):
    """axis-aligned bounds (lo, hi per axis) of named bodies of stage_1_mechanics/out/assembly.glb"""
    import trimesh
    sc = trimesh.load(str(S1 / "out/assembly.glb"), force="scene")
    out = {}
    for node in sc.graph.nodes_geometry:
        if node in names:
            tf, g = sc.graph[node]
            m = sc.geometry[g].copy()
            m.apply_transform(tf)
            out[node] = tuple((float(m.bounds[0][i]), float(m.bounds[1][i])) for i in range(3))
    return out


def check_1():
    f = T / "tables/11_568_devices.csv"
    if not f.is_file():
        return "SKIP", ["the reference table 11_568_devices.csv of the local memory block is not on this computer"]
    rows = rd(f)
    non = re.compile(r"^\((table \d+|components)\)$|^NOTE\b|^SHEETS\b|^TITLE BLOCK$")
    kinds = Counter("title" if r["designation"].startswith("(") and r["designation"] != "(earth symbol)" else
                    "note" if r["designation"].startswith("NOTE") else "other"
                    for r in rows if non.match(r["designation"].strip()))
    devrows = [r for r in rows if not non.match(r["designation"].strip())]
    want = []
    for r in devrows:
        for part in re.split(r"[,;]", r["designation"]):
            part = part.strip()
            m = re.match(r"^([A-Z]+)(\d+)-([A-Z]+)?(\d+)$", part)
            if m:
                want += [f"{m.group(1)}{i}" for i in range(int(m.group(2)), int(m.group(4)) + 1)]
            elif part:
                want.append(part)
    sheet_txt = {n: "\n".join(texts(S / "schemes_2d" / fn)) for n, fn in SHEETS.items()}
    blob = "\n".join(sheet_txt.values())
    miss_n, miss_s = [], []
    for w in want:
        m = re.match(r"^(\S+) \(sheet (\d+)\)$", w)
        if w == "(earth symbol)":           # rule: the earth row is the PE (protective earth) terminal group
            ok_n, ok_s = "PE" in NAMES, has_tok("PE", blob) or "⏚" in blob
        elif w == "RC...":                  # rule: "RC..." stands for the RC suppressors: any RC<number>
            ok_n = any(re.match(r"RC\d", x) for x in NAMES)
            ok_s = re.search(r"(?<![A-Za-z0-9])RC\d", blob) is not None
        elif m:                             # rule: "R14 (sheet 7)" is R14 with sheet 7 among its sheets
            nm, sh = m.group(1), m.group(2)
            ok_n = any(d["designation"] == nm and sh in re.findall(r"\d+", d["sheet"]) for d in DEV)
            ok_s = has_tok(nm, sheet_txt[int(sh)])
        else:
            ok_n, ok_s = w in NAMES, has_tok(w, blob)
        if not ok_n:
            miss_n.append(w)
        if not ok_s:
            miss_s.append(w)
    lines = [f"11_568_devices.csv rows {len(rows)}; not devices {len(rows) - len(devrows)} (table titles "
             f"{kinds['title']}, notes {kinds['note']}, sheet list and title block {kinds['other']}); device rows "
             f"{len(devrows)} (section 04: 74)",
             f"names after splitting groups and ranges {len(want)}; rules: (earth symbol) = PE, RC... = any RC<n>, "
             f"R14 (sheet 7) = R14 with sheet 7",
             f"missing in merged_devices.csv {len(miss_n)}" + (f": {', '.join(miss_n)}" if miss_n else ""),
             f"missing as text on the 8 sheet pages {len(miss_s)}" + (f": {', '.join(miss_s)}" if miss_s else "")]
    return ("FAIL" if miss_n or miss_s or len(devrows) != 74 else "PASS"), lines


def ruler(p):
    """Two-digit texts of an SVG page grouped by their row (y attribute, class). The ruler (the column numbers along the
    top of a 568 sheet) is the row that holds the most of them; wire and terminal numbers elsewhere do not count."""
    t = Path(p).read_text(encoding="utf-8")
    rows = defaultdict(list)
    for attrs, inner in re.findall(r"<text\b([^>]*)>(.*?)</text>", t, re.S):
        s = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        if re.fullmatch(r"\d{2}", s):
            y = re.search(r'\by="([^"]*)"', attrs)
            c = re.search(r'\bclass="([^"]*)"', attrs)
            rows[(y.group(1) if y else "", c.group(1) if c else "")].append(int(s))
    if not rows:
        return ("", ""), set(), 0
    key = max(sorted(rows), key=lambda k: len(rows[k]))
    return key, set(rows[key]), sum(len(v) for k, v in rows.items() if k != key)


def check_2():
    files = list(SHEETS.values()) + ["overview.svg", "connections.svg"]
    have = [f for f in files if (S / "schemes_2d" / f).is_file()]
    lines = [f"SVG (Scalable Vector Graphics) pages present {len(have)} of 10"
             + (f"; missing {', '.join(sorted(set(files) - set(have)))}" if len(have) < 10 else "")]
    if not (T / "tables").is_dir():
        return ("FAIL" if len(have) < 10 else "SKIP"), lines + [
            "column numbers: SKIP, the paths tables of the local memory block are not on this computer"]
    bad = len(have) < 10
    for n in range(2, 9):
        tab = T / "tables" / (f"11_568_sheet{n}_paths.csv" if n <= 4 else f"12_568_sheet{n}_paths.csv")
        rows = rd(tab)
        used = set()
        for r in rows:
            for a, b in re.findall(r"(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?", r["column"] if r["column"] != "header" else ""):
                used.update(range(int(a), int(b or a) + 1))
        (ry, rc), shown, others = ruler(S / "schemes_2d" / SHEETS[n])
        miss = sorted(used - shown)
        bad |= bool(miss)
        lines.append(f"sheet {n}: paths rows {len(rows)}, column numbers used {len(used)}; ruler of {SHEETS[n]} (row y "
                     f"{ry or '?'}" + (f", class {rc}" if rc else "") + f") holds {len(shown)}, of them used "
                     f"{len(used & shown)}, missing {len(miss)}" + (f" ({miss})" if miss else "")
                     + f"; two-digit labels off the ruler (wire and terminal numbers, not counted) {others}")
    return ("FAIL" if bad else "PASS"), lines


def check_3():
    bad = [f"line {i}: {w['from_device']} -> {w['to_device']}" for i, w in enumerate(WIR, start=2)
           if w["from_device"] not in NAMES or w["to_device"] not in NAMES]
    return ("FAIL" if bad else "PASS"), [f"merged_wires.csv rows {len(WIR)}, ends {2 * len(WIR)}, ends that are no "
                                         f"device of merged_devices.csv (dangling) {len(bad)}"] + bad[:10]


def check_4():
    by = defaultdict(list)
    for w in WIR:
        if w["plc_address"]:
            by[w["plc_address"]].append(w)
    at = defaultdict(list)
    for w in WIR:
        at[(w["from_device"], w["from_terminal"])].append(w)
        at[(w["to_device"], w["to_terminal"])].append(w)
    lines, bad = [], False
    f = T / "tables/12_568_plc_io.csv"
    table = rd(f) if f.is_file() else []
    tcount = Counter(r["plc_address"] for r in table)
    two, cnt = [], []
    for a in sorted(by):
        allowed = max(1, tcount[a])                 # the table's own rows for the address (IN-GND: 2 by design)
        nums = sorted({w["wire"] for w in by[a] if w["wire"]})
        sigs = sorted({w["signal"].strip() for w in by[a] if w["signal"].strip()})
        root = {}                                   # rows that share an end (device, terminal) are one conductor

        def find(x):
            while root.setdefault(x, x) != x:
                x = root[x]
            return x
        for w in by[a]:
            root[find((w["from_device"], w["from_terminal"]))] = find((w["to_device"], w["to_terminal"]))
        comp = len({find(x) for x in list(root)})
        cnt.append(f"{a} {len(by[a])}/{len(nums)}/{len(sigs)}/{comp}")
        if len(nums) > allowed or len(sigs) > allowed or comp > allowed:
            two.append(f"{a} (rows {len(by[a])}; wire numbers {len(nums)}: {', '.join(nums)}; signals {len(sigs)}: "
                       f"{' | '.join(sigs)}; separate conductors {comp}; table rows {tcount[a]})")
    for a in sorted(x for x in tcount if tcount[x] > 1):
        lines.append(f"INFO: {a} has {tcount[a]} rows in the table itself (two signals by design), not a fault: " + ", ".join(sorted({w['wire'] for w in by.get(a, []) if w['wire']})))
    if two and table:
        bad = True
    lines.insert(0, f"addresses in merged_wires.csv {len(by)}; per address rows/wire numbers/signal texts/separate "
                    f"conductors (rows joined by a shared device terminal): {', '.join(cnt)}")
    if table:
        lines.insert(1, f"an address on more than one wire number, signal text or conductor (more than its rows in "
                        f"12_568_plc_io.csv) {len(two)}" + (f": {'; '.join(two)}" if two else ""))
    else:                                           # the limit per address is its row count in the table: unknown here
        lines.insert(1, "an address on more than one wire number, signal text or conductor: SKIP, the limit of each "
                        "address is its row count in 12_568_plc_io.csv of the local memory block, not on this computer"
                        + (f" (addresses above 1, not judged: {', '.join(x.split(' (')[0] for x in two)})" if two else ""))
    if not table:
        return ("FAIL" if bad else "SKIP"), lines + [
            "address to device: SKIP, the table 12_568_plc_io.csv of the local memory block is not on this computer"]
    want = [r for r in table if re.fullmatch(r"(IN|OUT)-[0-9A-F]", r["plc_address"]) and r["device"] not in ("", "-")]
    lines.insert(1, f"12_568_plc_io.csv rows {len(table)}; addresses with a device {len(want)} (section 04: 14)")
    bad |= len(want) != 14
    for r in want:
        a, dev = r["plc_address"], r["device"].split()[0]
        pair = re.search(r"through (\S+) (\w+)-(\w+)", r["device"])
        wn = {w["wire"] for w in by.get(a, []) if w["wire"]}
        seen, order, reached = set(), [], []
        todo = [(w["from_device"], w["from_terminal"]) for w in by.get(a, [])] + \
               [(w["to_device"], w["to_terminal"]) for w in by.get(a, [])]
        while todo:
            node = todo.pop(0)
            if node in seen:
                continue
            seen.add(node)
            order.append(f"{node[0]} {node[1]}".strip())
            d = node[0]
            k = KIND.get(d, "").lower()
            if pair and node == (pair.group(1), pair.group(2)):       # the contact pair the table names
                nxt = (pair.group(1), pair.group(3))
                todo.append(nxt)
                reached.append(d)
                continue
            if pair and node == (pair.group(1), pair.group(3)):
                todo += [(x, t) for w in at[node] for x, t in ((w["from_device"], w["from_terminal"]),
                                                                (w["to_device"], w["to_terminal"]))]
                continue
            if d != "PLC" and "terminal" not in k and "connector" not in k:
                reached.append(d)
                continue
            for w in at[node]:                                       # same conductor: same wire number or none
                if w["wire"] and wn and w["wire"] not in wn:
                    continue
                todo += [(w["from_device"], w["from_terminal"]), (w["to_device"], w["to_terminal"])]
        ok = dev in reached
        bad |= not ok
        lines.append(f"{a}: table device {dev}" + (f" through {pair.group(1)} {pair.group(2)}-{pair.group(3)}"
                                                   if pair else "") + f"; route {' - '.join(order)}; "
                     f"{'on it' if ok else 'NOT on it'}")
    return ("FAIL" if bad else "PASS"), lines


def check_5():
    ml_p = S / "measure_list.md"
    ml = ml_p.read_text(encoding="utf-8") if ml_p.is_file() else ""
    committed = ("stage_1_mechanics", "stage_2_electronics")      # in every copy of the repository

    def gone_folder(s):
        """the highest folder of a source path that is not on this computer (photos, documents, the local memory block)"""
        parts = s.split("/")[:-1]
        for k in range(1, len(parts) + 1):
            if not (P / "/".join(parts[:k])).is_dir():
                return "/".join(parts[:k])
        return None
    files = [f"netlist/{t}_{k}.csv" for t in THREADS for k in ("devices", "wires")] + \
            [f"netlist/merged_{k}.csv" for k in ("devices", "wires")] + \
            ["scheme_3d/placements.csv", "scheme_3d/bundles.csv"]
    n = nomark = nosrc = absolute = missing = skipped = unlisted = notsure = 0
    skip_in = Counter()
    ex = []
    for f in files:
        for i, r in enumerate(rd(S / f), start=2):
            n += 1
            ev = r["evidence"].strip()
            if not MARK.match(ev):
                nomark += 1
                ex.append(f"no mark: {f} line {i}")
            srcs = [s.strip() for s in r["source_path"].split(";") if s.strip()]
            if not srcs:
                nosrc += 1
                ex.append(f"no source: {f} line {i}")
            for s in srcs:
                if re.match(r"^([A-Za-z]:|/)", s) or "\\" in s:
                    absolute += 1
                    ex.append(f"absolute path: {f} line {i}")
                elif (P / s).exists():
                    pass
                elif s.split("/")[0] not in committed and gone_folder(s):
                    skipped += 1                    # its folder is not here: cannot be checked on this computer
                    skip_in[gone_folder(s)] += 1
                else:                               # missing although its folder is here (or in the repository)
                    missing += 1
                    ex.append(f"source missing: {f} line {i}: {s}")
            if ev != "sure":
                notsure += 1
                if not re.search(re.escape(f"{f} line {i}") + r"(?!\d)", ml):
                    unlisted += 1
                    ex.append(f"not in measure_list.md: {f} line {i}")
    # merged = stacked thread rows: each merged row less its thread column is its thread row, in the same order
    differ, sizes = 0, []
    for k in ("devices", "wires"):
        want = [dict(thread=t, **r) for t in THREADS for r in rd(S / f"netlist/{t}_{k}.csv")]
        got = rd(S / f"netlist/merged_{k}.csv")
        sizes.append(f"{k} {len(got)} of {len(want)}")
        for i in range(max(len(want), len(got))):
            a = want[i] if i < len(want) else {}
            b = got[i] if i < len(got) else {}
            if a != b:
                differ += 1
                cols = sorted(c for c in set(a) | set(b) if a.get(c) != b.get(c))
                ex.append(f"merged row differs from its thread row: netlist/merged_{k}.csv line {i + 2} "
                          f"({', '.join(cols)})")
    lines = [f"rows {n} (6 thread netlists, 2 merged netlists, placements, bundles); without a mark {nomark}; "
             f"without a source {nosrc}; absolute source paths {absolute}; source paths missing {missing}",
             f"rows not plain sure {notsure}; of them not named in measure_list.md {unlisted}",
             f"merged netlists = the thread rows stacked in order ({', '.join(sizes)}): rows that differ {differ}"]
    if skipped:
        lines.append(f"source existence: SKIP for {skipped} source references in folders that are not on this computer "
                     f"(photos, documents or the local memory block): "
                     + ", ".join(f"{k} ({v})" for k, v in sorted(skip_in.items())))
    bad = nomark or nosrc or absolute or missing or unlisted or differ or not ml
    return ("FAIL" if bad else "SKIP" if skipped else "PASS"), lines + ex[:12]


def check_6():
    f = T / "anchors_index.csv"
    if not f.is_file():
        return "SKIP", ["anchors_index.csv of the local memory block is not on this computer"]
    arows = rd(f)
    A, pts = {}, defaultdict(set)
    for r in arows:
        nm = r["name"] if "." in r["name"] else f"{r['kind']}.{r['name']}"
        A[nm] = (float(r["x_mm"]), float(r["y_mm"]), float(r["z_mm"]))
        pts[nm].add(A[nm])
    twice = [nm for nm, c in Counter(r["name"] if "." in r["name"] else f"{r['kind']}.{r['name']}"
                                     for r in arows).items() if c > 1]
    split = sorted(nm for nm in twice if len(pts[nm]) > 1)
    used, bad, n, on = set(), [], 0, []
    for i, r in enumerate(PLA, start=2):
        an, d = r["anchor"].strip(), r["designation"].strip()
        if not an:
            continue
        n += 1
        used.add(d)
        if an not in A:
            bad.append(f"line {i} {r['item']}: anchor {an} not in anchors_index.csv")
            continue
        if f"body.{d}" in A and an != f"body.{d}":
            bad.append(f"line {i} {r['item']}: stands on {an}, body.{d} exists")
        xyz = (fl(r["x_mm"]), fl(r["y_mm"]), fl(r["z_mm"]))
        dist = math.dist(A[an], xyz) if None not in xyz else math.inf
        if dist > 1.0:
            bad.append(f"line {i} {r['item']}: x_mm, y_mm, z_mm {dist:.1f} mm from {an}")
        if r["item"].strip():
            on.append((i, r, an))
    devs = {nm.split(".", 1)[1] for nm in A if nm.split(".", 1)[1] in NAMES}
    unplaced = sorted(devs - used - {"FF1"})
    ff1 = [r for r in PLA if r["designation"] == "FF1" and any((fl(r[k]) or 0) > 0
                                                              for k in ("size_x_mm", "size_y_mm", "size_z_mm"))]
    lines = [f"anchors_index.csv rows {len(arows)}, distinct names {len(A)} (names listed by two parts {len(twice)}, "
             f"with two different points {len(split)}" + (f": {', '.join(split)}" if split else "") + "); "
             f"designations of merged_devices.csv with an anchor {len(devs)}",
             f"placements rows standing on an anchor {n}; unknown anchor, not on body.<designation> although it exists, "
             f"or x_mm/y_mm/z_mm more than 1 mm from the anchor point (spec/layout_3d.md: they restate it) {len(bad)}; "
             f"devices with an anchor but no row on it {len(unplaced)}" + (f" ({', '.join(unplaced)})" if unplaced else "")]
    # the drawn item: spec/layout_3d.md section 8 (agreed with t4's critic): the anchor lies in or on the device's own
    # stage-1 body and our item lies at most 1 mm from that body and from its carrier (contact_check.py MARKER lines,
    # exceptions named there); a lamp or connector box holds its anchor point (at most 1 mm from its bounds)
    skip, mbad, exc, mk, boxed, ref = False, [], [], {}, 0, []
    if not (S1 / "out/assembly.glb").is_file():
        skip = True
        lines.append("drawn items: SKIP, stage_1_mechanics/out/assembly.glb is not on this computer (contact_check.py "
                     "needs it)")
    else:
        code, rl = contact_run()
        if rl is None:
            mbad.append(f"contact_check.py wrote no report (exit {code})")
        for ln in rl or []:
            if " MARKER " not in ln:
                continue
            m = MARK_RE.match(ln)
            if not m:
                mbad.append(f"MARKER line not understood: {ln[:90]}")
                continue
            st, des, an, a2b, body, item, i2b, i2c, carrier, a2i, rest = m.groups()
            mk[item] = (des, an)
            if st != "PASS" or float(a2b) > 1.0 or float(i2c) > 1.0 or (float(i2b) > 1.0 and "exception:" not in rest):
                mbad.append(f"{st} MARKER {des}: anchor {an} {a2b} mm from {body}; {item} {i2b} mm from it, {i2c} mm "
                            f"from {carrier}")
            elif float(i2b) > 1.0:
                exc.append(f"{des} ({item} {i2b} mm from {body}, fastened to {carrier})")
        meshes = item_meshes()
        for i, r, an in on:
            if r["item"] in mk:
                if mk[r["item"]] != (r["designation"], an):
                    mbad.append(f"line {i} {r['item']}: MARKER line names {mk[r['item']]}, the row {r['designation']} "
                                f"on {an}")
                continue
            g = meshes.get("electrical." + r["item"])
            if g is None:
                mbad.append(f"line {i} {r['item']}: no node electrical.{r['item']} in electrical.glb")
                continue
            lo, hi = g.bounds
            d = math.dist(A[an], [min(max(A[an][k], lo[k]), hi[k]) for k in range(3)])
            if an.split(".", 1)[1] != r["designation"]:      # a stage-1 reference point, not the device's own anchor
                ref.append(f"{r['item']} {d:.1f} mm from {an}")
                continue
            boxed += 1
            if d > 1.0:
                mbad.append(f"line {i} {r['item']}: drawn {d:.1f} mm from its anchor {an}")
        lines += [f"drawn items (electrical.glb): MARKER lines of contact_check.py {len(mk)} (anchor in or on the "
                  f"device's own stage-1 body, item at most 1 mm from that body and from its carrier); other items "
                  f"on their own anchor (lamps, connectors) {boxed}, anchor point at most 1 mm from the drawn box; "
                  f"faults {len(mbad)}",
                  f"named exceptions of spec/layout_3d.md section 8 (item fastened next to its device body) {len(exc)}"
                  + (f": {'; '.join(exc)}" if exc else "")]
        if ref:
            lines.append(f"INFO: placed from a stage-1 reference point, not body.<designation> or <kind>.<designation> "
                         f"(the box is checked by checks 7 and 9; spec/layout_3d.md: console devices against the inner "
                         f"face of the 2 mm front cover) {len(ref)}: {'; '.join(ref)}")
    lines.append(f"FF1 (light curtain, not fitted): boxes drawn {len(ff1)}")
    lines += bad[:10] + mbad[:10]
    st = "FAIL" if bad or unplaced or ff1 or split or mbad else "SKIP" if skip else "PASS"
    return st, lines


def box(r):
    c = [fl(r[k]) for k in ("box_x_mm", "box_y_mm", "box_z_mm")]
    s = [fl(r[k]) for k in ("size_x_mm", "size_y_mm", "size_z_mm")]
    if None in c or None in s or min(s) <= 0:
        return None
    return [(c[i] - s[i] / 2, c[i] + s[i] / 2) for i in range(3)]


def check_7():
    lim04 = {"cabinet": ((-1420, -1250), (-200, 300), (0, 1535)),         # section 04 (option B)
             "console": ((-835, 850), (-454, -394), (1190, 1535))}         # 04, back wall Y -394 from the stage-1 model
    body = {"cabinet": "housing.cabinet", "console": "housing.console"}
    if (S1 / "out/assembly.glb").is_file():
        got = body_bounds(set(body.values()))
        lim = {p: got.get(b, lim04[p]) for p, b in body.items()}
        src = "bounds of housing.cabinet and housing.console in stage_1_mechanics/out/assembly.glb"
        differ = [p for p in lim if p in got and any(abs(a - c) > 0.5 or abs(b - d) > 0.5
                                                     for (a, b), (c, d) in zip(lim[p], lim04[p]))]
        src += "; section 04 numbers " + (f"differ for {', '.join(differ)}" if differ else "the same")
    else:
        lim = lim04
        src = "section 04 numbers (stage_1_mechanics/out/assembly.glb is not on this computer)"
    walls = ("cabinet wall", "cabinet outside face", "console wall", "console outside")
    cnt, bad, wall, other, nobox = Counter(), [], [], [], []
    for i, r in enumerate(PLA, start=2):
        pl, it = r["place"], r["item"] or r["designation"]
        if pl == "machine":
            cnt["machine"] += 1
        elif pl in walls or (pl in lim and it.startswith("pass.")):   # on or through a wall: check 9 tests them
            wall.append(it)
        elif pl in lim:
            b = box(r)
            if b is None:
                nobox.append(f"line {i} {it} ({pl}): no box")
                continue
            cnt[pl] += 1
            out = [ax for ax, (lo, hi), (a, z) in zip("XYZ", b, lim[pl]) if lo < a - 0.5 or hi > z + 0.5]
            if out:
                bad.append(f"line {i} {it} ({pl}): outside in {''.join(out)}")
        else:
            other.append(f"line {i} {it}: place {pl!r}")
    f2 = lambda v: f"{v:g}"
    lines = [f"limits: {src}: " + "; ".join(f"{p} X {f2(lim[p][0][0])}..{f2(lim[p][0][1])}, Y {f2(lim[p][1][0])}.."
                                            f"{f2(lim[p][1][1])}, Z {f2(lim[p][2][0])}..{f2(lim[p][2][1])}" for p in lim),
             f"placements rows {len(PLA)} = cabinet {cnt['cabinet']} + console {cnt['console']} (boxes checked here) + "
             f"on, through or outside a wall {len(wall)} (contact: check 9) + machine {cnt['machine']} (anchors: check 6; "
             f"contact: check 9)" + (f" + without a box {len(nobox)}" if nobox else "")
             + (f" + other places {len(other)}" if other else ""),
             f"boxes outside their housing {len(bad)}; wall items: {', '.join(wall)}",
             f"pass items (holes, glands, shafts through a wall) in all {sum(1 for r in PLA if r['item'].startswith('pass.'))}"]
    lines += bad[:10] + nobox[:5] + other[:5]
    return ("FAIL" if bad or nobox or other else "PASS"), lines


def check_8():
    items = {r["item"] for r in PLA}
    legs = {b["leg"] for b in BUN}
    bodies = {r["device_body"] for r in PLA if r["device_body"]}
    kinds, opened = Counter(), []
    for i, b in enumerate(BUN, start=2):
        clips = {c.split("@")[0].strip() for c in b["clips"].split(";") if c.strip()}
        for end in (b["from_item"].strip(), b["to_item"].strip()):
            m_j = re.fullmatch(r"junction on (\S+)", end)
            m_b = re.fullmatch(r"stage-1 (\S+)", end)
            if end in items:
                kinds["placements item"] += 1
            elif re.fullmatch(r"connector\.XC[1-4]", end):
                kinds["connector XC1-XC4"] += 1
            elif m_j and m_j.group(1) in legs:
                kinds["junction on an existing leg"] += 1
            elif end in clips:
                kinds["clip of the same leg"] += 1
            elif m_b and m_b.group(1) in bodies:
                kinds["stage-1 device body"] += 1
            else:
                opened.append(f"line {i} {b['leg']}: {end}")
    cores = {(c["thread"], c["line"]) for c in rd(S / "netlist/merged_cores.csv")}
    local = [f"{w['thread']} {ln} {w['from_device']} {w['from_terminal']}-{w['to_device']} {w['to_terminal']}"
             for w, ln in zip(WIR, thread_line_map(WIR))
             if PLACE.get(w["from_device"]) == PLACE.get(w["to_device"]) == "machine" and (w["thread"], str(ln)) not in cores]
    lines = [f"bundle legs {len(BUN)}, ends {2 * len(BUN)}: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
             + f"; open ends {len(opened)}",
             f"INFO: machine wires carried by no bundle (local: their ends meet at one item or at one leg end, as "
             f"integration_merge.py lists them) {len(local)}: " + "; ".join(local)] + opened[:10]
    return ("FAIL" if opened else "PASS"), lines


def check_9():
    if not (S1 / "out/assembly.glb").is_file():
        return "SKIP", ["stage_1_mechanics/out/assembly.glb is not on this computer"]
    code, rl = contact_run()
    if rl is None:
        return "FAIL", [f"contact_check.py wrote no report (exit {code})"]
    c = Counter(l.split()[0] for l in rl if l.split() and l.split()[0] in ("PASS", "FAIL", "INFO"))
    t4 = (S / "scheme_3d/contact_report.txt").read_text(encoding="utf-8").splitlines()
    import trimesh
    sc = trimesh.load(str(S / "scheme_3d/electrical.glb"), force="scene")
    glb_names = set(sc.graph.nodes_geometry)
    page = (S / "viewer/index.html").read_text(encoding="utf-8")
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', page, re.S)
    data = json.loads(m.group(1)) if m else {}
    vnames = {b.get("n") for b in data.get("bodies", [])}
    miss = sorted(glb_names - vnames)
    lines = [f"contact_check.py rerun on the electrical layer (exit {code}): report "
             f"checks/contact_report_check9.txt, PASS {c['PASS']}, FAIL {c['FAIL']}, INFO {c['INFO']}; same text as "
             f"scheme_3d/contact_report.txt (thread t4): {'yes' if rl == t4 else 'no'}",
             f"electrical.glb nodes {len(glb_names)}; in the viewer's data {len(glb_names) - len(miss)}; missing {len(miss)}"]
    lines += [l for l in rl if l.startswith("FAIL")][:10] + miss[:10]
    return ("FAIL" if c["FAIL"] or code or miss or not c["PASS"] else "PASS"), lines


def md5n(p):
    return hashlib.md5(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def s1_files():
    return sorted(str(p.relative_to(P)).replace("\\", "/") for p in S1.rglob("*") if p.is_file())


def git(*a):
    return subprocess.run(["git", "-C", str(P)] + list(a), capture_output=True, text=True)


def check_10():
    if not S1.is_dir():
        return "SKIP", ["stage_1_mechanics is not on this computer"]
    lines, bad = [], False
    tracked = None                                  # the stage-1 files of f52cc8e: a clone holds only these
    if (P / ".git").exists():
        d = git("diff", "--quiet", "f52cc8e", "--", "stage_1_mechanics").returncode
        st = git("status", "--short", "--", "stage_1_mechanics").stdout.strip()
        bad |= d != 0 or bool(st)
        lines.append(f"git diff --quiet f52cc8e -- stage_1_mechanics: exit {d}; git status --short -- "
                     f"stage_1_mechanics: {len(st.splitlines())} lines")
        ls = git("ls-tree", "-r", "-z", "--name-only", "f52cc8e", "--", "stage_1_mechanics")
        if ls.returncode == 0 and ls.stdout.strip("\0"):
            tracked = set(ls.stdout.split("\0")) - {""}
    else:
        lines.append("git part: SKIP, no .git folder in this copy")
    man = HERE / "stage1_manifest.txt"
    if not man.is_file():
        return "FAIL", lines + ["checks/stage1_manifest.txt missing"]
    want = dict(reversed(l.split("  ", 1)) for l in man.read_text(encoding="utf-8").splitlines() if "  " in l)
    have = s1_files()
    changed = [f for f in have if f in want and md5n(P / f) != want[f]]
    extra = [f for f in have if f not in want]
    gone = [f for f in want if not (P / f).is_file()]
    cache = {f for f in gone if "__pycache__" in f}             # episode-1 caches, ignored by git: INFO
    # the stage-1 files git never tracked (test copies, logs, crops): a clone of f52cc8e holds none of them, so they
    # are INFO only when every one of them is absent; a partial loss (some absent, others on disk) is a change of
    # stage 1 that git cannot see (they are ignored): FAIL, as every missing file is when this copy has no .git
    untracked = set() if tracked is None else {f for f in want if f not in tracked and "__pycache__" not in f}
    gone_untracked = [f for f in gone if f in untracked]
    clone = bool(untracked) and len(gone_untracked) == len(untracked)
    gone_bad = [f for f in gone if f not in cache and not (clone and f in untracked)]
    cut = datetime(2026, 11, 25, 17, 0).timestamp()
    newer = sum(1 for f in have if (P / f).stat().st_mtime > cut)
    bad |= bool(changed or extra or gone_bad)
    lines += [f"manifest files {len(want)} (md5 with CRLF read as LF); on disk {len(have)}; changed {len(changed)}; "
              f"extra {len(extra)}; missing {len(gone_bad)}"
              + (f" (git never tracked {len(gone_untracked)} of them; the other {len(untracked) - len(gone_untracked)} "
                 f"untracked files are on disk: a loss, not a clone)" if gone_untracked and not clone else "")
              + (f"; missing __pycache__ files of episode 1 (ignored by git, INFO) {len(cache)}" if cache else "")
              + (f"; missing files that git never tracked: all {len(untracked)} of them, as in a clone of f52cc8e "
                 f"(test copies, logs, crops; INFO; some of them missing would be FAIL)" if clone else ""),
              f"INFO: files with a time stamp after 2026-11-25 17:00 {newer} (a copy changes time stamps)"]
    lines += [f"changed: {f}" for f in changed[:5]] + [f"extra: {f}" for f in extra[:5]] + \
             [f"missing: {f}" for f in gone_bad[:5]]
    return ("FAIL" if bad else "PASS" if (P / ".git").exists() else "SKIP"), lines   # git part skipped: never PASS


def check_11():
    p = S / "viewer/index.html"
    page = p.read_text(encoding="utf-8")
    hits = sorted({m.group(0) for m in NET.finditer(page)})
    sw = "Electrical layer, all of it" in page
    lines = [f"viewer/index.html: network references (://, fetch(, XMLHttpRequest, <link, <img, <iframe, src=, @import, "
             f"url(, import() {len(hits)}" + (f" ({', '.join(hits)})" if hits else ""),
             f"switch of the electrical layer (\"Electrical layer, all of it\"): {'present' if sw else 'missing'}"]
    return ("FAIL" if hits or not sw else "PASS"), lines


def check_12():
    lines, bad = [], False
    files = [p for p in S.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    rel = [str(p.relative_to(P)).replace("\\", "/") for p in files]
    photos = [r for r in rel if re.search(r"\.(jpe?g|heic|pdf|docx?|xlsx?|tiff?)$", r, re.I)
              or (r.lower().endswith(".png") and "/scheme_3d/renders/" not in r)]
    bad |= bool(photos)
    lines.append(f"files under stage_2_electronics {len(rel)}; photos, documents or images outside scheme_3d/renders "
                 f"{len(photos)}" + (f" ({', '.join(photos[:5])})" if photos else ""))
    sizes = defaultdict(list)
    for p in files:
        sizes[p.stat().st_size].append(p)
    same, looked = [], 0
    for root in (P / "preparatory_data_analysis", P / "static_dynamic_memory"):
        if not root.is_dir():
            continue
        looked += 1
        for q in root.rglob("*"):
            if q.is_file() and q.stat().st_size in sizes:
                h = hashlib.md5(q.read_bytes()).hexdigest()
                same += [str(p.relative_to(P)).replace("\\", "/") for p in sizes[q.stat().st_size]
                         if hashlib.md5(p.read_bytes()).hexdigest() == h]
    bad |= bool(same)
    partial = looked < 2                            # a folder not here cannot be compared: never a PASS for it
    lines.append(f"files equal to a photo, document, download or memory-block file {len(same)}"
                 + ("" if looked == 2 else f" (compared with {looked} of the 2 local folders; SKIP for the others: "
                                           f"not on this computer)"))
    home = Path.home().name
    pat = re.compile(r"[A-Za-z]:[/\\]Users[/\\]" + (f"|{re.escape(home)}" if len(home) > 2 else ""), re.I)
    upath = [r for p, r in zip(files, rel) if p.suffix.lower() in (".py", ".md", ".csv", ".svg", ".html", ".txt", ".json")
             and pat.search(p.read_text(encoding="utf-8", errors="replace"))]
    bad |= bool(upath)
    lines.append(f"text files holding a user path or the user's name {len(upath)}" + (f" ({', '.join(upath)})" if upath else ""))
    if not (P / ".git").exists():
        return ("FAIL" if bad else "SKIP"), lines + ["git part: SKIP, no .git folder in this copy"]
    st = [l[3:].strip().strip('"') for l in git("status", "--porcelain", "--untracked-files=all").stdout.splitlines()]
    outside = [s for s in st if not (s.startswith("stage_2_electronics/") or s == ".gitignore")]
    ign = [l[3:].strip() for l in git("status", "--porcelain", "--ignored", "--untracked-files=all", "--",
                                      "stage_2_electronics").stdout.splitlines() if l.startswith("!!")]
    ign_bad = [s for s in ign if "__pycache__" not in s]
    bad |= bool(outside or ign_bad)
    lines.append(f"git status: changed or new paths {len(st)}, outside stage_2_electronics and .gitignore "
                 f"{len(outside)}" + (f" ({', '.join(outside[:5])})" if outside else ""))
    lines.append(f"ignored files under stage_2_electronics other than __pycache__ {len(ign_bad)}"
                 + (f" ({', '.join(ign_bad[:5])})" if ign_bad else ""))
    return ("FAIL" if bad else "SKIP" if partial else "PASS"), lines


CHECKS = [(1, "devices", check_1), (2, "sheets", check_2), (3, "wires", check_3), (4, "PLC (programmable logic "
          "controller) addresses", check_4), (5, "evidence", check_5), (6, "anchors", check_6), (7, "boxes", check_7),
          (8, "bundles", check_8), (9, "contact", check_9), (10, "stage 1 untouched", check_10),
          (11, "viewer", check_11), (12, "git and committed files", check_12)]


def clean(s):
    for base in (str(P), str(P).replace("\\", "/")):
        s = s.replace(base, ".")
    return s


def main():
    args = sys.argv[1:]
    if "--make-manifest" in args:
        if (P / ".git").exists() and git("diff", "--quiet", "f52cc8e", "--", "stage_1_mechanics").returncode:
            print("stage 1 differs from f52cc8e: manifest not written")
            return 1
        (HERE / "stage1_manifest.txt").write_text("".join(f"{md5n(P / f)}  {f}\n" for f in s1_files()),
                                                  encoding="utf-8", newline="\n")
        print(f"stage1_manifest.txt: {len(s1_files())} files")
        return 0
    sel = {int(a) for a in args if a.isdigit()}
    out = ["Checks of stage_2_electronics against section 04 of the plan (thread t5, integration).",
           "Written by stage_2_electronics/checks/run_checks.py; rerun it, do not edit. Paths relative to the "
           "repository root.", ""]
    st = Counter()
    for n, name, fn in CHECKS:
        if sel and n not in sel:
            continue
        try:
            s, lines = fn()
        except Exception as e:                       # a crash is a failed check, with its reason
            s, lines = "FAIL", [f"crashed: {type(e).__name__}: {e}"]
        st[s] += 1
        out.append(f"check {n} {name}: {s}")
        out += ["  " + clean(l) for l in lines]
    out += ["", f"summary: PASS {st['PASS']}, FAIL {st['FAIL']}, SKIP {st['SKIP']}",
            f"result: {'FAIL' if st['FAIL'] else 'PASS'}"]
    txt = "\n".join(out) + "\n"
    if not sel:
        (HERE / "checks.txt").write_text(txt, encoding="utf-8", newline="\n")
    sys.stdout.write(txt)
    return 1 if st["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
