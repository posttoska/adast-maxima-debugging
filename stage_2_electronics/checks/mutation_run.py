#!/usr/bin/env python3
"""Thread t5 (integration): mutation run of checks/run_checks.py. Each of the 12 checks of section 04 is broken on purpose,
one break at a time, in a fresh copy of the repository outside it; the check must then print FAIL with a line that names
the break. This shows that a PASS in checks.txt is a check that could have failed.

Run from the repository root (the folder that holds stage_1_mechanics and stage_2_electronics):
  python -B stage_2_electronics/checks/mutation_run.py
Steps: (1) copy stage_2_electronics (without __pycache__), stage_1_mechanics, .gitignore, .git, the tables and
anchors_index.csv of the local memory block and the memory-block files named in source_path columns into a new folder
from tempfile.mkdtemp (prefix t5_mutation_; the variables TMPDIR, TEMP or TMP choose where). The photos and documents of
preparatory_data_analysis are not copied (290 MB): checks 5 and 12 say SKIP for the part that needs them (their
existence, the comparison with them), by their own rule; their other parts still run, so their breaks are made.
(2) run_checks.py in full in the copy: the baseline. (3) for each break: change the file(s) in the copy, run
"run_checks.py <n>" there, compare the status and the named line with what the break must give, put the file(s) back
(copied back from a saved copy, or moved back) and test that they are back byte for byte. (4) run_checks.py in full again:
the same statuses and the same checks.txt text as the baseline. Nothing in the repository changes except
checks/mutation_report.txt, and nothing is deleted: the copy stays, its path is printed at the end, never written into
the report. Report: stage_2_electronics/checks/mutation_report.txt, without time stamps or temporary paths (a rerun on the
same files gives the same text). Exit 0 when every break gave what it must and the last run equals the baseline, else 1.
"""
import csv
import hashlib
import html
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent            # stage_2_electronics/checks
S = HERE.parent
P = S.parent
SR = "stage_2_electronics"
S1R = "stage_1_mechanics"
TR = "static_dynamic_memory/blocks/generation_002/artifacts"
SHEETS = {1: "power_sheet1.svg", 2: "power_sheet2.svg", 3: "power_sheet3.svg", 4: "control_sheet4.svg",
          5: "control_sheet5.svg", 6: "control_sheet6.svg", 7: "control_sheet7.svg", 8: "plc_sheet8.svg"}
SRC_FILES = [f"netlist/{t}_{k}.csv" for t in ("power", "control", "plc_drive") for k in ("devices", "wires")] + \
            ["scheme_3d/placements.csv", "scheme_3d/bundles.csv"]
STATUS = re.compile(r"^check (\d+) (.+): (PASS|FAIL|SKIP)$", re.M)
TEXT = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.S)
ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
HOME = Path.home().name
UPATH = re.compile(r"[A-Za-z]:[/\\]Users[/\\]" + (f"|{re.escape(HOME)}" if len(HOME) > 2 else ""), re.I)


# ---------------------------------------------------------------- files
def read_csv(p):
    raw = Path(p).read_bytes()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    with open(p, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        rows = list(r)
    return list(r.fieldnames), rows, nl


def write_csv(p, fields, rows, nl):
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator=nl)
        w.writeheader()
        w.writerows(rows)


def md5_tree(root, skip=()):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            rel = p.relative_to(root).as_posix()
            if rel not in skip:
                out[rel] = hashlib.md5(p.read_bytes()).hexdigest()
    return out


def memory_sources():
    """files under static_dynamic_memory named in the source_path columns that check 5 reads"""
    out = set()
    for f in SRC_FILES:
        for r in read_csv(S / f)[1]:
            for s in r["source_path"].split(";"):
                s = s.strip()
                if s.startswith("static_dynamic_memory/") and (P / s).is_file():
                    out.add(s)
    return sorted(out)


def photo_sources():
    out = set()
    for f in SRC_FILES:
        for r in read_csv(S / f)[1]:
            out |= {s.strip() for s in r["source_path"].split(";") if s.strip().startswith("preparatory_data_analysis/")}
    return out


class Work:
    """the copy and what one break changed in it"""

    def __init__(self, base):
        self.base, self.root, self.orig = base, base / "repo", base / "orig"
        self.saved, self.moved = [], []

    def save(self, rel):
        if rel not in self.saved:
            d = self.orig / rel
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.root / rel, d)
            self.saved.append(rel)
        return self.root / rel

    def move(self, a, b):
        os.replace(self.root / a, self.root / b)
        self.moved.append((a, b))

    def restore(self):
        for a, b in reversed(self.moved):
            os.replace(self.root / b, self.root / a)
        for rel in self.saved:
            shutil.copy2(self.orig / rel, self.root / rel)
        ok = all((self.orig / r).read_bytes() == (self.root / r).read_bytes() for r in self.saved)
        ok = ok and all((self.root / a).is_file() and not (self.root / b).exists() for a, b in self.moved)
        self.saved, self.moved = [], []
        return ok


def make_copy(base):
    w = Work(base)
    shutil.copytree(S, w.root / SR, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(P / S1R, w.root / S1R)
    shutil.copy2(P / ".gitignore", w.root / ".gitignore")
    if (P / ".git").is_dir():
        shutil.copytree(P / ".git", w.root / ".git")
    if (P / TR / "tables").is_dir():
        shutil.copytree(P / TR / "tables", w.root / TR / "tables")
    if (P / TR / "anchors_index.csv").is_file():
        shutil.copy2(P / TR / "anchors_index.csv", w.root / TR / "anchors_index.csv")
    mem = memory_sources()
    for s in mem:
        if not (w.root / s).exists():
            (w.root / s).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(P / s, w.root / s)
    return w, mem


def scrub(s, base):
    for b in {str(base), base.as_posix(), str(base.resolve()), base.resolve().as_posix()}:
        s = s.replace(b, "<copy>")
    return s


def run_checks(w, nums):
    pr = subprocess.run([sys.executable, "-B", f"{SR}/checks/run_checks.py"] + [str(n) for n in nums], cwd=str(w.root),
                        capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV, timeout=900)
    out = scrub(pr.stdout + pr.stderr, w.base)
    return pr.returncode, out, {int(n): s for n, _, s in STATUS.findall(out)}


# ---------------------------------------------------------------- edits (each one tests that it did exactly its change)
def set_cells(w, rel, changes):
    """changes: (line, field, value), line as in a text editor (header = line 1); returns the old values"""
    p = w.save(rel)
    fields, rows, nl = read_csv(p)
    before = [dict(r) for r in rows]
    old = []
    for line, field, value in changes:
        old.append(rows[line - 2][field])
        rows[line - 2][field] = value
    write_csv(p, fields, rows, nl)
    after = read_csv(p)[1]
    diff = sum(1 for a, b in zip(before, after) for k in fields if a[k] != b[k])
    want = sum(1 for (_, _, v), o in zip(changes, old) if v != o)
    if len(after) != len(before) or diff != want or after != rows:
        raise RuntimeError(f"{rel}: the edit changed {diff} cells, meant {want}")
    return old


def drop_rows(w, rel, pred):
    p = w.save(rel)
    fields, rows, nl = read_csv(p)
    keep = [r for r in rows if not pred(r)]
    write_csv(p, fields, keep, nl)
    if read_csv(p)[1] != keep:
        raise RuntimeError(f"{rel}: rows not written as meant")
    return len(rows) - len(keep)


def append_bytes(w, rel, data):
    p = w.save(rel)
    with open(p, "ab") as f:
        f.write(data)


def text_of(inner):
    return html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()


def key_of(attrs):
    y = re.search(r'\by="([^"]*)"', attrs)
    c = re.search(r'\bclass="([^"]*)"', attrs)
    return (y.group(1) if y else "", c.group(1) if c else "")


def two_digit_rows(t):
    """two-digit texts of an SVG page by row (y, class) and the ruler row, read as run_checks.py ruler() reads them"""
    rows = {}
    for attrs, inner in TEXT.findall(t):
        s = text_of(inner)
        if re.fullmatch(r"\d{2}", s):
            rows.setdefault(key_of(attrs), []).append(int(s))
    if not rows:
        return None, rows
    return max(sorted(rows), key=lambda k: len(rows[k])), rows


def used_columns(w, n):
    tab = w.root / TR / "tables" / (f"11_568_sheet{n}_paths.csv" if n <= 4 else f"12_568_sheet{n}_paths.csv")
    used = set()
    for r in read_csv(tab)[1]:
        for a, b in re.findall(r"(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?", r["column"] if r["column"] != "header" else ""):
            used.update(range(int(a), int(b or a) + 1))
    return used


def glb_bounds(p):
    """world bounds of every node of a GLB, read as stage 1's loader reads it (numbers are mm, never rescaled)"""
    import trimesh
    sc = trimesh.load(str(p), force="scene")
    out = {}
    for node in sc.graph.nodes_geometry:
        tf, g = sc.graph[node]
        m = sc.geometry[g].copy()
        m.apply_transform(tf)
        out[node] = [[float(v) for v in m.bounds[0]], [float(v) for v in m.bounds[1]]]
    return out


def glb_move(w, rel, node, vec):
    """move one node of a GLB by vec mm: a translation added to that node in the JSON chunk, the binary chunk unchanged;
    then test that this node moved by vec and no other node moved"""
    p = w.save(rel)
    b = p.read_bytes()
    magic, _, total = struct.unpack_from("<4sII", b, 0)
    jlen, jtype = struct.unpack_from("<I4s", b, 12)
    if magic != b"glTF" or jtype != b"JSON" or total != len(b):
        raise RuntimeError(f"{rel}: not a GLB as expected")
    doc = json.loads(b[20:20 + jlen].decode("utf-8"))
    hit = [n for n in doc["nodes"] if n.get("name") == node]
    if len(hit) != 1 or "matrix" in hit[0]:
        raise RuntimeError(f"{rel}: node {node} found {len(hit)} times or holds a matrix")
    t0 = hit[0].get("translation", [0.0, 0.0, 0.0])
    hit[0]["translation"] = [float(t0[k]) + float(vec[k]) for k in range(3)]
    j = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    j += b" " * (-len(j) % 4)
    rest = b[20 + jlen:]
    p.write_bytes(struct.pack("<4sII", b"glTF", 2, 20 + len(j) + len(rest)) + struct.pack("<I4s", len(j), b"JSON") + j
                  + rest)
    old, new = glb_bounds(w.orig / rel), glb_bounds(p)
    moved = sorted(k for k in old if k in new and any(abs(old[k][s][i] - new[k][s][i]) > 1e-6
                                                      for s in (0, 1) for i in range(3)))
    shift_ok = all(abs(new[node][s][i] - old[node][s][i] - vec[i]) < 1e-4 for s in (0, 1) for i in range(3))
    if set(old) != set(new) or moved != [node] or not shift_ok:
        raise RuntimeError(f"{rel}: moving {node} moved {moved}")
    return f"{len(old)} nodes, only {node} moved, by ({vec[0]:g}, {vec[1]:g}, {vec[2]:g}) mm (bounds read back)"


def off_face(item, body):
    """axis and sign that move box `item` straight off the face of box `body` it sits on (the side where the two
    overlap least); from the bounds of both"""
    best = None
    for k in range(3):
        for sgn, g in ((-1.0, body[0][k] - item[1][k]), (1.0, item[0][k] - body[1][k])):
            if best is None or g > best[0]:
                best = (g, k, sgn)
    v = [0.0, 0.0, 0.0]
    v[best[1]] = best[2]
    return v, ("-" if best[2] < 0 else "+") + "XYZ"[best[1]]


# ---------------------------------------------------------------- the breaks
WIRES = f"{SR}/netlist/merged_wires.csv"
PLACE = f"{SR}/scheme_3d/placements.csv"
GLB = f"{SR}/scheme_3d/electrical.glb"
FRAME_MD = f"{S1R}/spec/frame.md"


def b1(w):
    rel = f"{SR}/netlist/merged_devices.csv"
    n = drop_rows(w, rel, lambda r: r["designation"] == "S30")
    return rel, f"all {n} rows of S30 dropped", [r"^  missing in merged_devices\.csv \d+: (?:.*, )?S30(?:,|$)"]


def b1b(w):
    tok = re.compile(r"(?<![A-Za-z0-9])S30(?![A-Za-z0-9])")
    hits, files = 0, []
    for fn in SHEETS.values():
        rel = f"{SR}/schemes_2d/{fn}"
        t = (w.root / rel).read_bytes().decode("utf-8")

        def cut(m):
            nonlocal hits
            inner = re.sub(r"(<[^>]+>)|([^<]+)", lambda q: q.group(1) or tok.sub("", q.group(2)), m.group(2))
            hits += inner != m.group(2)
            return f"<text{m.group(1)}>{inner}</text>"
        t2 = TEXT.sub(cut, t)
        if t2 != t:
            w.save(rel).write_bytes(t2.encode("utf-8"))
            files.append(fn)
    left = sum(1 for fn in SHEETS.values() for _, inner in TEXT.findall((w.root / SR / "schemes_2d" / fn).read_text(
        encoding="utf-8")) if tok.search(text_of(inner)))
    if not hits or left:
        raise RuntimeError(f"S30 texts changed {hits}, left {left}")
    return f"{SR}/schemes_2d/" + ", ".join(files), f"S30 taken out of {hits} texts of the sheet pages (none left)", \
        [r"^  missing as text on the 8 sheet pages \d+: (?:.*, )?S30(?:,|$)"]


def b2(w):
    for n in range(2, 9):
        rel = f"{SR}/schemes_2d/{SHEETS[n]}"
        t = (w.root / rel).read_bytes().decode("utf-8")
        key, rows = two_digit_rows(t)
        if key is None:
            continue
        off = [v for k, vs in rows.items() if k != key for v in vs]
        cand = sorted(used_columns(w, n) & set(rows[key]) & set(off))
        if not cand:
            continue
        c, blanked = cand[0], 0

        def blank(m):
            nonlocal blanked
            s = text_of(m.group(2))
            if key_of(m.group(1)) == key and re.fullmatch(r"\d{2}", s) and int(s) == c:
                blanked += 1
                return f"<text{m.group(1)}></text>"
            return m.group(0)
        t2 = TEXT.sub(blank, t)
        w.save(rel).write_bytes(t2.encode("utf-8"))
        key2, rows2 = two_digit_rows(t2)
        kept = sum(1 for k, vs in rows2.items() if k != key2 for v in vs if v == c)
        if key2 != key or c in rows2[key2] or kept != off.count(c):
            raise RuntimeError(f"sheet {n}: ruler edit not as meant")
        return rel, (f"sheet {n}: column number {c} blanked on the ruler (row y {key[0]}, {blanked} text); it stays "
                     f"printed {kept} time(s) off the ruler as a wire or terminal number"), \
            [rf"^  sheet {n}: .*missing 1 \(\[{c}\]\)"]
    raise RuntimeError("no column number printed both on and off a ruler")


def b2b(w):
    w.move(f"{SR}/schemes_2d/overview.svg", f"{SR}/schemes_2d/overview.svg.moved")
    return f"{SR}/schemes_2d/overview.svg", "moved away (renamed overview.svg.moved)", \
        [r"pages present 9 of 10; missing overview\.svg$"]


def b3(w):
    old = set_cells(w, WIRES, [(2, "to_device", "NOPE")])
    return WIRES, f"line 2: to_device {old[0]} -> NOPE (no such device)", [r"dangling\) 1$", r"^  line 2: \S+ -> NOPE$"]


def b4a(w):
    rows = read_csv(w.root / WIRES)[1]
    mine = sorted({r["wire"] for r in rows if r["plc_address"] == "IN-1" and r["wire"]})
    line = next(i for i, r in enumerate(rows, 2) if r["wire"] and r["wire"] not in mine and not r["plc_address"])
    set_cells(w, WIRES, [(line, "plc_address", "IN-1")])
    return WIRES, (f"line {line} (wire {rows[line - 2]['wire']}, no address) given IN-1, which is on wire "
                   f"{', '.join(mine)}"), [r"IN-1 \(rows \d+; wire numbers 2: "]


def b4b(w):
    rows = read_csv(w.root / WIRES)[1]
    ind = [r for r in rows if r["plc_address"] == "IN-D"]
    ends = {(r[d], r[t]) for r in ind for d, t in (("from_device", "from_terminal"), ("to_device", "to_terminal"))}
    sig = next(r["signal"] for r in ind if r["signal"].strip())
    line = next(i for i, r in enumerate(rows, 2) if not r["wire"] and not r["plc_address"]
                and (r["from_device"], r["from_terminal"]) not in ends and (r["to_device"], r["to_terminal"]) not in ends)
    r = rows[line - 2]
    set_cells(w, WIRES, [(line, "plc_address", "IN-D"), (line, "signal", sig)])
    return WIRES, (f"line {line} ({r['from_device']} {r['from_terminal']} - {r['to_device']} {r['to_terminal']}, no wire "
                   f"number, no address) given IN-D and its signal text: same wire numbers, same signal, a second "
                   f"conductor"), [r"IN-D \(rows \d+; wire numbers 1: [^;]*; signals 1: [^;]*; separate conductors 2;"]


def b4c(w):
    rows = read_csv(w.root / WIRES)[1]
    lines = [i for i, r in enumerate(rows, 2) if r["plc_address"] == "OUT-9"]
    set_cells(w, WIRES, [(i, "plc_address", "") for i in lines])
    return WIRES, f"OUT-9 taken off its {len(lines)} rows (lines {', '.join(map(str, lines))})", \
        [r"^  OUT-9: table device .*NOT on it$"]


def b5a(w):
    rel = f"{SR}/netlist/control_devices.csv"
    old = set_cells(w, rel, [(2, "evidence", "")])
    return rel, f"line 2: evidence {old[0]!r} -> empty", [r"^  no mark: netlist/control_devices\.csv line 2$"]


def b5b(w):
    rel = f"{SR}/netlist/power_wires.csv"
    set_cells(w, rel, [(2, "source_path", f"{S1R}/spec/no_such_file.md")])
    return rel, f"line 2: source_path -> {S1R}/spec/no_such_file.md (a file that does not exist in a present folder)", \
        [r"^  source missing: netlist/power_wires\.csv line 2: stage_1_mechanics/spec/no_such_file\.md$"]


def b5c(w):
    f = "netlist/power_devices.csv"
    ml = (w.root / SR / "measure_list.md").read_text(encoding="utf-8")
    rows = read_csv(w.root / SR / f)[1]
    line = next(i for i, r in enumerate(rows, 2) if r["evidence"].strip() == "sure"
                and not re.search(re.escape(f"{f} line {i}") + r"(?!\d)", ml))
    set_cells(w, f"{SR}/{f}", [(line, "evidence", "[?]")])
    return f"{SR}/{f}", f"line {line}: evidence sure -> [?], a row that measure_list.md does not name", \
        [rf"^  not in measure_list\.md: {re.escape(f)} line {line}$"]


def b5d(w):
    rel = f"{SR}/netlist/merged_wires.csv"
    old = set_cells(w, rel, [(2, "evidence", "")])
    return rel, f"line 2: evidence {old[0]!r} -> empty (a merged row; its thread row unchanged)", \
        [r"^  no mark: netlist/merged_wires\.csv line 2$",
         r"^  merged row differs from its thread row: netlist/merged_wires\.csv line 2 \(evidence\)$"]


def b5e(w):
    rel = f"{SR}/netlist/merged_devices.csv"
    set_cells(w, rel, [(2, "source_path", f"{S1R}/spec/no_such_file.md")])
    return rel, f"line 2: source_path -> {S1R}/spec/no_such_file.md (a merged row; a file that does not exist)", \
        [r"^  source missing: netlist/merged_devices\.csv line 2: stage_1_mechanics/spec/no_such_file\.md$",
         r"^  merged row differs from its thread row: netlist/merged_devices\.csv line 2 \(source_path\)$"]


def b5f(w):
    rel = f"{SR}/netlist/merged_devices.csv"
    old = set_cells(w, rel, [(2, "type_rating", "edited in the merged file only")])
    return rel, f"line 2: type_rating {old[0]!r} -> 'edited in the merged file only' (a cell no other part of " \
                f"check 5 reads)", \
        [r"^  merged row differs from its thread row: netlist/merged_devices\.csv line 2 \(type_rating\)$"]


def b6a(w):
    rows = read_csv(w.root / PLACE)[1]
    cand = [(i, r) for i, r in enumerate(rows, 2) if r["anchor"].strip() and r["designation"] == "S30"] or \
           [(i, r) for i, r in enumerate(rows, 2) if r["anchor"].strip()]
    i, r = cand[0]
    dec = len(r["x_mm"].split(".")[1]) if "." in r["x_mm"] else 0
    new = f"{float(r['x_mm']) + 5.0:.{dec}f}"
    set_cells(w, PLACE, [(i, "x_mm", new)])
    return PLACE, f"line {i} {r['item']} ({r['designation']} on {r['anchor']}): x_mm {r['x_mm']} -> {new} (5 mm)", \
        [rf"^  line {i} {re.escape(r['item'])}: x_mm, y_mm, z_mm [\d.]+ mm from {re.escape(r['anchor'].strip())}$"]


def mark_vec(w, sign):
    el = glb_bounds(w.root / GLB)
    s1 = glb_bounds(w.root / S1R / "out/assembly.glb")
    v, _ = off_face(el["electrical.mark.S10"], s1["safety_sensors.S10"])
    vec = [sign * 5.0 * x + 0.0 for x in v]                 # + 0.0: no "-0" in the report
    return vec, axis_name(vec)


def axis_name(vec):
    k = max(range(3), key=lambda i: abs(vec[i]))
    return ("-" if vec[k] < 0 else "+") + "XYZ"[k]


def first_line(rx, out):
    """the whole output line in which the pattern of a break is found (None when no line holds it)"""
    for ln in out.splitlines():
        if re.search(rx, ln):
            return ln.strip()
    return None


def b6b(w):
    vec, ax = mark_vec(w, 1.0)
    how = glb_move(w, GLB, "electrical.mark.S10", vec)
    return GLB, f"mark.S10 moved 5 mm off the face of safety_sensors.S10 it sits on ({ax}); {how}", \
        [r"^  FAIL MARKER S10: .*; mark\.S10 [\d.]+ mm from it"]


def b7a(w):
    rows = read_csv(w.root / PLACE)[1]
    i, r = next((i, r) for i, r in enumerate(rows, 2) if r["place"] == "cabinet" and r["item"].startswith("dev.")
                and r["box_x_mm"])
    set_cells(w, PLACE, [(i, "box_x_mm", "-1000.0")])
    return PLACE, f"line {i} {r['item']}: box_x_mm {r['box_x_mm']} -> -1000.0", \
        [rf"^  line {i} {re.escape(r['item'])} \(cabinet\): outside in X$"]


def b7b(w):
    rows = read_csv(w.root / PLACE)[1]
    i, r = next((i, r) for i, r in enumerate(rows, 2) if r["place"] == "console" and r["box_y_mm"]
                and not r["item"].startswith("pass."))
    dec = len(r["box_y_mm"].split(".")[1]) if "." in r["box_y_mm"] else 0
    new = f"{float(r['box_y_mm']) + 1000.0:.{dec}f}"
    set_cells(w, PLACE, [(i, "box_y_mm", new)])
    return PLACE, f"line {i} {r['item']}: box_y_mm {r['box_y_mm']} -> {new} (+1000 mm)", \
        [rf"^  line {i} {re.escape(r['item'])} \(console\): outside in Y$"]


def b8(w):
    rel = f"{SR}/scheme_3d/bundles.csv"
    rows = read_csv(w.root / rel)[1]
    set_cells(w, rel, [(2, "to_item", "nowhere")])
    return rel, f"line 2 {rows[0]['leg']}: to_item {rows[0]['to_item']} -> nowhere", \
        [r"open ends 1$", rf"^  line 2 {re.escape(rows[0]['leg'])}: nowhere$"]


def b9(w):
    el = glb_bounds(w.root / GLB)
    v, _ = off_face(el["electrical.dev.BMR1"], el["electrical.mount.plate"])
    vec = [5.0 * x + 0.0 for x in v]
    ax = axis_name(vec)
    how = glb_move(w, GLB, "electrical.dev.BMR1", vec)
    return GLB, (f"dev.BMR1 (it touches only mount.plate) moved 5 mm off the plate ({ax}); {how}. Not dev.UZ1: it has "
                 f"5.5 mm to the cabinet door, so 5 mm leave it within the 1 mm contact rule of the door"), \
        [r"^  FAIL electrical\.dev\.BMR1 touches .*in the air"]


def b9b(w):
    vec, ax = mark_vec(w, -1.0)
    how = glb_move(w, GLB, "electrical.mark.S10", vec)
    return GLB, (f"mark.S10 pushed 5 mm into safety_sensors.S10 ({ax}); {how}. Check 6 tests contact (at most 1 mm), "
                 f"not position, so it stays PASS; the overlap is check 9's to catch"), \
        [r"^  FAIL electrical\.mark\.S10 touches .*overlap"]


def b10(w):
    append_bytes(w, FRAME_MD, b" ")
    rx = [r"^  changed: stage_1_mechanics/spec/frame\.md$"]
    if (w.root / ".git").is_dir():
        rx.append(r"stage_1_mechanics: exit 1;")
    return FRAME_MD, "one byte (a space) appended", rx


UNTRACKED_S1 = f"{S1R}/parts/backgauge/mutants/bore_narrow/backgauge.md"   # an episode-1 test copy, ignored by git


def b10b(w):
    pr = subprocess.run(["git", "-C", str(w.root), "ls-files", "--error-unmatch", UNTRACKED_S1], capture_output=True)
    if pr.returncode == 0:
        raise RuntimeError(f"{UNTRACKED_S1} is tracked by git; break 10b needs a file git never tracked")
    w.move(UNTRACKED_S1, "t5_break_10b_backgauge.md")
    return UNTRACKED_S1, ("moved out of stage_1_mechanics (a file git never tracked and ignores, so git status cannot "
                          "see it go; the other untracked files stay: a loss, not a clone)"), \
        [r"^  missing: stage_1_mechanics/parts/backgauge/mutants/bore_narrow/backgauge\.md$",
         r"git status --short -- stage_1_mechanics: 0 lines$"]


def b11(w):
    rel = f"{SR}/viewer/index.html"
    append_bytes(w, rel, b"\n://\n")
    return rel, 'one line "://" appended after the page', [r"import\(\) 1 \(://\)$"]


def b12a(w):
    rel = f"{SR}/sources.md"
    upath = "".join(["C", ":", "/", "Us", "ers", "/", "example", "/", "notes.txt"])   # built here: no user path in this file
    append_bytes(w, rel, ("\n" + upath + "\n").encode("utf-8"))
    return rel, "one line holding a Windows user-folder path (built at run time) appended", \
        [r"user's name 1 \(stage_2_electronics/sources\.md\)$"]


def b12b(w):
    w.move(f"{SR}/scheme_3d/renders/top.png", f"{SR}/checks/top.png")
    return f"{SR}/scheme_3d/renders/top.png", "moved into stage_2_electronics/checks/ (an image outside the renders)", \
        [r"outside scheme_3d/renders 1 \(stage_2_electronics/checks/top\.png\)$"]


def b12c(w):
    append_bytes(w, FRAME_MD, b" ")
    return FRAME_MD, "one byte appended: a changed path outside stage_2_electronics and .gitignore", \
        [r"outside stage_2_electronics and \.gitignore 1 \(stage_1_mechanics/spec/frame\.md\)$"]


T_ALL = (f"{TR}/tables", f"{TR}/anchors_index.csv")
# (id, checks run, expected status per check, edit, files the break needs in the repository)
BREAKS = [
    ("1", [1], {1: "FAIL"}, b1, (f"{TR}/tables",)),
    ("1b", [1], {1: "FAIL"}, b1b, (f"{TR}/tables",)),
    ("2", [2], {2: "FAIL"}, b2, (f"{TR}/tables",)),
    ("2b", [2], {2: "FAIL"}, b2b, ()),
    ("3", [3], {3: "FAIL"}, b3, ()),
    ("4a", [4], {4: "FAIL"}, b4a, ()),
    ("4b", [4], {4: "FAIL"}, b4b, ()),
    ("4c", [4], {4: "FAIL"}, b4c, (f"{TR}/tables",)),
    ("5a", [5], {5: "FAIL"}, b5a, ()),
    ("5b", [5], {5: "FAIL"}, b5b, ()),
    ("5c", [5], {5: "FAIL"}, b5c, ()),
    ("5d", [5], {5: "FAIL"}, b5d, ()),
    ("5e", [5], {5: "FAIL"}, b5e, ()),
    ("5f", [5], {5: "FAIL"}, b5f, ()),
    ("6a", [6], {6: "FAIL"}, b6a, T_ALL),
    ("6b", [6], {6: "FAIL"}, b6b, T_ALL),
    ("7a", [7], {7: "FAIL"}, b7a, ()),
    ("7b", [7], {7: "FAIL"}, b7b, ()),
    ("8", [8], {8: "FAIL"}, b8, ()),
    ("9", [9], {9: "FAIL"}, b9, ()),
    ("9b", [6, 9], {6: "PASS", 9: "FAIL"}, b9b, T_ALL),
    ("10", [10], {10: "FAIL"}, b10, ()),
    ("10b", [10], {10: "FAIL"}, b10b, (".git",)),
    ("11", [11], {11: "FAIL"}, b11, ()),
    ("12a", [12], {12: "FAIL"}, b12a, ()),
    ("12b", [12], {12: "FAIL"}, b12b, ()),
    ("12c", [12], {12: "FAIL"}, b12c, (".git",)),
]


def main():
    p_before = md5_tree(S, skip={"checks/mutation_report.txt"}), md5_tree(P / S1R)
    base = Path(tempfile.mkdtemp(prefix="t5_mutation_"))
    w, mem = make_copy(base)
    photos = photo_sources()
    rep = ["Mutation run of stage_2_electronics/checks/run_checks.py (thread t5, integration).",
           "Written by stage_2_electronics/checks/mutation_run.py; rerun it, do not edit. Paths relative to the "
           "repository root; no time stamps, no temporary paths.", "",
           f"copy (a new temporary folder outside the repository): {SR} (without __pycache__), {S1R}, .gitignore"
           + (", .git" if (P / ".git").is_dir() else "") + f", {TR}/tables, {TR}/anchors_index.csv and the "
           f"{len(mem)} memory-block files named in source_path columns; not copied: the {len(photos)} photo and "
           f"document paths of preparatory_data_analysis named there (checks 5 and 12 say SKIP for the part that "
           f"needs them)"]
    code, out, st0 = run_checks(w, [])
    base_txt = (w.root / SR / "checks/checks.txt").read_text(encoding="utf-8")
    rep += [f"baseline, run_checks.py in full in the copy (exit {code}): "
            + ", ".join(f"check {n} {s}" for n, s in sorted(st0.items()))]
    rep += ["  " + l.strip() for l in out.splitlines() if "SKIP" in l and not l.startswith(("check ", "summary"))]
    print(rep[-1] if st0 else out[-2000:])
    n_ok, n_skip, bad = 0, 0, []
    for bid, nums, expect, fn, needs in BREAKS:
        miss = [x for x in needs if not (P / x).exists()]
        rep.append("")
        # checks 5 and 12 say SKIP in the copy for one part only (photos absent); their other parts can still FAIL
        if miss or any(st0.get(n) == "SKIP" and expect[n] == "FAIL" and n not in (5, 12) for n in nums):
            n_skip += 1
            rep.append(f"break {bid} (check {' and '.join(map(str, nums))}): SKIP, not on this computer: "
                       + (", ".join(miss) or "the check's reference data (baseline SKIP)"))
            continue
        try:
            rel, change, rx = fn(w)
        except Exception as e:                       # a break that could not be made is a fault of this run
            back = w.restore()
            bad.append(bid)
            rep.append(f"break {bid} (check {' and '.join(map(str, nums))}): NOT MADE: {type(e).__name__}: {e}; files "
                       f"back: {'yes' if back else 'NO'}")
            continue
        code, out, st = run_checks(w, nums)
        back = w.restore()
        found = [first_line(x, out) for x in rx]
        ok = all(st.get(n) == s for n, s in expect.items()) and None not in found and back
        n_ok += ok
        if not ok:
            bad.append(bid)
        rep += [f"break {bid} (check {' and '.join(map(str, nums))}): {rel}: {change}",
                "  expected: " + ", ".join(f"check {n} {s}" for n, s in expect.items()) + " and a line naming the break",
                "  got: " + ", ".join(f"check {n} {st.get(n, 'no status line')}" for n in nums) + f" (exit {code}); "
                f"files back byte for byte: {'yes' if back else 'NO'}"]
        rep += [f"  line: {f}" if f else f"  line NOT found: {x}" for f, x in zip(found, rx)]
        rep.append(f"  result: {'as expected' if ok else 'NOT as expected'}")
        print(f"break {bid}: {'as expected' if ok else 'NOT as expected'}")
        if not ok:
            print(out[-3000:])
    code, out, st1 = run_checks(w, [])
    end_txt = (w.root / SR / "checks/checks.txt").read_text(encoding="utf-8")
    in_copy, in_p = md5_tree(w.root / SR), md5_tree(S)
    differ = sorted(k for k in set(in_copy) | set(in_p) if in_copy.get(k) != in_p.get(k))
    p_after = md5_tree(S, skip={"checks/mutation_report.txt"}), md5_tree(P / S1R)
    p_changed = sum(1 for a, b in zip(p_before, p_after) for k in set(a) | set(b) if a.get(k) != b.get(k))
    end_ok = st1 == st0 and end_txt == base_txt and set(differ) <= {"checks/checks.txt"} and not p_changed
    rep += ["", f"end, run_checks.py in full in the copy after every break was put back (exit {code}): statuses as the "
            f"baseline: {'yes' if st1 == st0 else 'NO'}; checks.txt text as the baseline: "
            f"{'yes' if end_txt == base_txt else 'NO'}",
            f"files of {SR} in the copy that differ from the repository's: {len(differ)}"
            + (f" ({', '.join(differ)}: the copy's own checks.txt, written by its own run)" if differ else ""),
            f"files of the repository changed by this run ({SR} apart from this report, {S1R}): {p_changed}",
            "", "reading: check 6 tests contact (item at most 1 mm from its own stage-1 body and its carrier), not "
            "position; an item pushed into its own body passes check 6 and is caught by check 9 (overlap), break 9b",
            f"summary: breaks {len(BREAKS)}, as expected {n_ok}, skipped {n_skip}, not as expected {len(bad)}"
            + (f" ({', '.join(bad)})" if bad else ""),
            f"result: {'PASS' if not bad and end_ok else 'FAIL'}"]
    txt = "\n".join(rep) + "\n"
    if UPATH.search(txt):
        print("the report would hold a user path: not written")
        return 1
    (HERE / "mutation_report.txt").write_text(txt, encoding="utf-8", newline="\n")
    print("\n".join(rep[-6:]))
    print(f"copy kept (nothing deleted): {base}")
    return 0 if not bad and end_ok else 1


if __name__ == "__main__":
    sys.exit(main())
