#!/usr/bin/env python3
"""Thread t5 (integration), part 4: the on-site measure list and the list of sources.

Reads only files under stage_2_electronics (and checks that each source path exists under the repository root):
  netlist/merged_devices.csv, merged_wires.csv, merged_conflicts.csv (integration_merge.py),
  scheme_3d/placements.csv, bundles.csv (thread t4),
  the on-site lists: spec/power.md section 9, spec/control.md section 11, spec/plc_drive.md section 11,
  spec/layout_3d.md section 11; the limits and rebuild commands of integration_draw.py (imported, so both pages agree).
Writes:
  measure_list.md  every on-site entry of the four specs (none lost, counted per source), every netlist, placement
                   and bundle row whose evidence is not plain "sure", every netlist row whose note compares the 568
                   print with a photo, every device field two threads give different values for; one table per place
                   (cabinet, console, machine, between places or documents)
  sources.md       every source path the merged netlists, placements and bundles cite: what it holds, the marks of the
                   rows citing it, committed or local only; the limits of the set; the rebuild commands
Run from the repository root (the folder that holds stage_2_electronics):
  python -B stage_2_electronics/schemes_2d/integration_lists.py
It ends with "result: PASS" when its self-check holds (counts per source equal, every row not plain "sure" listed,
every source path existing and listed once, no user path, every abbreviation with its full name at first use).
Output is the same on every run (no time stamps).
"""
import csv
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent            # stage_2_electronics/schemes_2d
S = HERE.parent                                   # stage_2_electronics
P = S.parent                                      # repository root
sys.path.insert(0, str(HERE))
import integration_draw as draw                   # limit_lines(), COMMANDS: the same text as index.html

SPEC_LISTS = [  # (letter, thread, spec file, heading of the on-site section)
    ("P", "power", "spec/power.md", "## 9. On-site list"),
    ("C", "control", "spec/control.md", "## 11. On-site list"),
    ("D", "plc_drive", "spec/plc_drive.md", "## 11. On-site list"),
    ("L", "layout_3d", "spec/layout_3d.md", "## 11. On-site check list"),
]
GROUPS = ["cabinet", "console", "machine", "between places or in the documents"]

# Every abbreviation the lists use, with its full name; written once at the top of each page (its first use).
ABBR = OrderedDict([
    ("PLC", "programmable logic controller"), ("OM", "operating manual of the MS 115 PS"),
    ("PE", "protective earth"), ("NO", "normally open contact"), ("NC", "normally closed contact"),
    ("AC", "alternating current"), ("DC", "direct current"), ("RC", "resistor-capacitor suppressor"),
    ("IEC", "International Electrotechnical Commission"), ("NPN", "negative-positive-negative transistor output"),
    ("PNP", "positive-negative-positive transistor output"), ("CSV", "comma-separated values"),
    ("SVG", "Scalable Vector Graphics"), ("GLB", "binary Graphics Library Transmission Format file, the 3D model"),
    ("3D", "three-dimensional"), ("2D", "two-dimensional"), ("LED", "light-emitting diode"),
    ("GND", "ground, 0 V"), ("TABLO", "control panel of the console [tablo]"), ("UZ1", "frequency inverter"),
    ("BMR1", "safety relay board of the cut cycle"), ("XP", "mains terminal block"), ("ZF1", "mains filter"),
    ("IN", "PLC input"), ("OUT", "PLC output"), ("DECISION", "settlement by the meta orchestrator"),
    ("LIVE", "a check made with the supply on"), ("EMC", "electromagnetic compatibility"),
    ("CAN", "Controller Area Network, a field bus"),
    ("NOARK", "maker of two breakers"), ("OEZ", "maker of breakers"), ("PDF", "Portable Document Format"),
    ("HTML", "HyperText Markup Language"), ("JPEG", "Joint Photographic Experts Group image"),
    ("JSON", "JavaScript Object Notation"), ("W", "web source, weaker evidence"),
    ("VDC", "volts direct current"), ("VA", "volt-ampere"), ("AT", "ampere, time-lag fuse"),
    ("DSR", "data set ready, serial line"), ("RTS", "request to send, serial line"),
    ("UG", "direct-current bus terminals of the inverter, +UG and -UG"), ("XC", "connector, designation prefix"),
])


def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def cell(s):
    return " ".join(str(s).replace("|", "\\|").split())


def short(s, n):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def full(s):
    """a cell's whole text, whitespace closed up: the measure list cuts no cell (tester 3, round 1)"""
    return " ".join(str(s).split())


# Measure list only (a text for the technician): letters of the netlists in the N and F ids, and what the
# workflow words of the netlist notes mean on site. Never applied to the source column.
THREAD_LETTER = {"power": "p", "control": "c", "plc_drive": "d"}
NET_NAME = {"power": "power netlist", "control": "control netlist", "plc_drive": "PLC and drive netlist"}
T_NAME = {"1": "power netlist", "2": "control netlist", "3": "PLC and drive netlist", "4": "3D scheme"}
T_LETTER = {"1": "P", "2": "C", "3": "D"}
# Russian notes as the sources quote them -> t5's English reading first, the Russian kept after it in [ ].
RU_READINGS = [
    ('"IN-8.-д. в конце хода пресса со вст." (IN-8 - sensor at the end of the clamp stroke [?])',
     '"IN-8 - sensor at the end of the clamp stroke [?]" [IN-8.-д. в конце хода пресса со вст.]'),
    ('"сигнал на резку A1K2"', '"signal to cut, A1K2" [сигнал на резку A1K2]'),
    ('"Y14 гидро распр. магнит."', '"Y14 hydraulic valve magnet" [Y14 гидро распр. магнит.]'),
    ('"Y01 блокир. шестерни"', '"Y01 gear lock" [Y01 блокир. шестерни]'),
    ('"?+24 (не взим.)"', '"?+24 (not, then a word not read [?])" [?+24 (не взим.)]'),
    ('"Норм „ON“"', '"normally ON" [Норм „ON“]'),
]
TERM_FIXES = [("the table's LINIE", "the table's line column [LINIE]"),
              ("(DECISION 1)", "(where photo and print differ, the photo counts)"),
              ("on-site list", "this list"),
              # workflow words a technician cannot use (critic g12, round 3)
              ("The PLC program itself is episode 3's.", "The PLC program itself is not part of this list."),
              ('see "Before any entry"', 'see "Before any entry" under Safety first')]
CYR = re.compile(r"[Ѐ-ӿ]{2,}")
# A spec's or netlist note's "entry n" names row n of that thread's on-site list, which is entry <letter>n here.
LIST_LETTER = {"power": "P", "control": "C", "plc_drive": "D"}
BARE_ENTRY = re.compile(r"\bentr(?:y|ies) \d")       # self-check: no bare entry number is left (critic g12, round 3)
ENTRY_REF = re.compile(r"\b(?:entry|entries|same as) ([A-Z]\+?\d+(?:(?:, | and )[A-Z]\+?\d+)*)")


def refs(s, letter):
    """the bare entry numbers of a thread's text written as this list's ids: "entry 21", "on-site entry 9",
    "on-site list, entry 8", "entries 18 and 19" -> entry P21, C9, P8, C18 and C19 (critic g12, round 3)"""
    s = re.sub(r"`?spec/(power|control|plc_drive)\.md`? section \d+, entry (\d+)",
               lambda m: f"entry {LIST_LETTER[m[1]]}{m[2]}", s)
    s = re.sub(r"\bon-site (?:list, )?entry (\d+)\b", lambda m: f"entry {letter}{m[1]}", s)
    s = re.sub(r"\bentries (\d+) and (\d+)\b", lambda m: f"entries {letter}{m[1]} and {letter}{m[2]}", s)
    return re.sub(r"\bentry (\d+)\b", lambda m: f"entry {letter}{m[1]}", s)


def own_text(r, by_num, letter):
    """a spec row whose cell is only "as entry n" takes row n's own text of that column, so the entry reads on its
    own (critic g12, round 3: P3, P12); every other cell stays as the spec has it"""
    out = {}
    for k, v in r.items():
        m = re.fullmatch(r"as entry (\d+)", v.strip())
        out[k] = f"{by_num[m[1]][k]} (same as {letter}{m[1]})" if m and m[1] in by_num and k in by_num[m[1]] else v
    return out


def list_ptr(s, key, key_num):
    """"(spec/control.md, on-site list)" in another list's row: the row of that list with the same key, as this
    list's id (plc_drive.md #7 points so at control.md's XC2 row)"""
    def sub(m):
        n = key_num.get((LIST_LETTER[m[1]], key))
        return f"(as entry {LIST_LETTER[m[1]]}{n})" if n else m[0]
    return re.sub(r"\(`?spec/(power|control|plc_drive)\.md`?, on-site list\)", sub, s)


WIRE_KEY_LINE = re.compile(r"` \((?:line )?(\d+)\)")       # a spec key: `A 1 -> B 2` (line 99), `C 3 -> D 4` (100)
WIRE_PTR = re.compile(r"(?:^|, )([^,]+?) -> ([^,]+?) \((?:\w+_wires\.csv )?line (\d+)\)")
LINE_FIRST = re.compile(r"\((?:(`?[\w./-]+\.csv`?) )?lines? \d")
BARE_WIRE_LINE = re.compile(r"-> [^,;()]+ \(\d+\)")


def wire_lines(s, thread):
    """a spec key's netlist line numbers named with their file (critic g13, round 4): "`A 1 -> B 2` (line 99),
    `C 3 -> D 4` (100)" -> "... (power_wires.csv line 99), ... (line 100)". Written without "netlist/", so that
    check 5, which looks for "netlist/<file> line n", still finds a row only through its own N or F entry."""
    first = [True]

    def sub(m):
        out = f"` ({thread}_wires.csv line {m[1]})" if first[0] else f"` (line {m[1]})"
        first[0] = False
        return out
    return WIRE_KEY_LINE.sub(sub, s)


def wire_lines_hold(eid, key, thread, wires, bad):
    """every wire key with a line pointer is that line of netlist/<thread>_wires.csv (header = line 1)"""
    n = 0
    for m in WIRE_PTR.finditer(key):
        i, n = int(m[3]), n + 1
        w = wires[i - 2] if 2 <= i < len(wires) + 2 else None
        if not (w and " ".join(f"{w['from_device']} {w['from_terminal']}".split()) == " ".join(m[1].split())
                and " ".join(f"{w['to_device']} {w['to_terminal']}".split()) == " ".join(m[2].split())):
            bad.append(f"measure list {eid} key: '{m[0].strip(', ')}' is not line {i} of netlist/{thread}_wires.csv")
    return n


LINE_ANY = re.compile(r"\((?:`?([\w./-]+\.csv)`? )?(lines?) (\d+)([^)]*)\)")


def line_ptrs(eid, col, r, wires_of, bad, n):
    """every "(... line n)" of a cell as written (critic g14, round 5): a "<netlist>_wires.csv line n" pointer and each
    bare "(line n)" after it in the same cell must end a wire key "from -> to (...)" that is line n of that file of
    the netlist folder, so the How-to-read sentence "a following (line 100) is a line of the same file" is tested; a
    bare "(line n)" with no such pointer before it is bad; a pointer into another named file stays as it stands"""
    ends, cur = {w.end(): w for w in WIRE_PTR.finditer(r)}, None
    for m in LINE_ANY.finditer(r):
        if m[1]:
            t = re.fullmatch(r"(power|control|plc_drive)_wires\.csv", m[1])
            cur = t[1] if t else None
            if not t:
                n["line pointers into other files (left as they stand)"] += 1
                continue
        elif cur is None:
            bad.append(f"measure list {eid} {col}: '{m[0]}' follows no <netlist>_wires.csv pointer in its cell")
            continue
        w, i, rows = ends.get(m.end()), int(m[3]), wires_of[cur]
        x = rows[i - 2] if 2 <= i < len(rows) + 2 else None
        if not (w and m[2] == "line" and not m[4] and x
                and " ".join(f"{x['from_device']} {x['from_terminal']}".split()) == " ".join(w[1].split())
                and " ".join(f"{x['to_device']} {x['to_terminal']}".split()) == " ".join(w[2].split())):
            bad.append(f"measure list {eid} {col}: '{(w[0] if w else m[0]).strip(', ')}' is not a wire key of "
                       f"line {i} of netlist/{cur}_wires.csv")
            continue
        n["wire keys checked on the page, " + ("naming the file" if m[1] else "same file")] += 1


def live_mark(s):
    """the power list writes its one supply-on row as "live, see ..."; the other lists mark theirs LIVE: one mark
    for all, so Safety first can be built from the rows marked LIVE alone (critic g12, round 3: P29)"""
    return re.sub(r"^live(?=[,:])", "LIVE", s)


def num_mm(x, f):
    v = float(x.replace(",", ".")) * f
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:g}"


def mm_units(s):
    """lengths in cm or m written in mm (R9: sizes in millimetres)"""
    s = re.sub(r"(\d+(?:[.,]\d+)?) x (\d+(?:[.,]\d+)?) cm\b",
               lambda m: f"{num_mm(m[1], 10)} x {num_mm(m[2], 10)} mm", s)
    s = re.sub(r"(\d+(?:[.,]\d+)?) ?cm\b", lambda m: f"{num_mm(m[1], 10)} mm", s)
    return re.sub(r"(?<![\w.,])(\d+(?:[.,]\d+)?) m\b(?![²³/])", lambda m: f"{num_mm(m[1], 1000)} mm", s)


def reader(s):
    """a measure-list cell as the technician reads it: English readings of the Russian notes, Czech terms in [ ],
    mm, and the netlists named instead of the workflow's thread numbers"""
    s = full(s)
    for a, b in RU_READINGS + TERM_FIXES:
        s = s.replace(a, b)
    s = re.sub(r"\bthread (power|control|plc_drive)\b", lambda m: f"the {NET_NAME[m[1]]}", s)
    s = re.sub(r"\banother thread\b", "another netlist", s)
    s = re.sub(r"\bthreads\b", "netlists", s)
    s = re.sub(r"\balso t([123])'s (?:on-site )?item (\d+)\b", lambda m: f"also entry {T_LETTER[m[1]]}{m[2]}", s)
    s = re.sub(r"\bt([1-4])'s\b", lambda m: f"the {T_NAME[m[1]]}'s", s)
    s = re.sub(r"\bt([1-4])\b", lambda m: f"the {T_NAME[m[1]]}", s)
    return mm_units(s)


def outside_brackets(s, rx):
    """matches of rx that stand outside every ( ) and [ ] of s"""
    depth, out = [0] * (len(s) + 1), []
    d = 0
    for i, ch in enumerate(s):
        depth[i] = d
        d += 1 if ch in "([" else -1 if ch in ")]" and d > 0 else 0
    return [m.group(0) for m in rx.finditer(s) if depth[m.start()] == 0]


DEV = rd(S / "netlist/merged_devices.csv")
WIR = rd(S / "netlist/merged_wires.csv")
CON = rd(S / "netlist/merged_conflicts.csv")
PLA = rd(S / "scheme_3d/placements.csv")
BUN = rd(S / "scheme_3d/bundles.csv")
PLACE = {}
for d in DEV:                                     # the first thread that gives a place (one may leave it empty)
    if d["place"].strip():
        PLACE.setdefault(d["designation"], d["place"].strip())
for r in PLA:
    for k in (r["item"], r["designation"]):
        if k:
            PLACE.setdefault(k, r["place"].strip())
DESIG = sorted({d["designation"] for d in DEV} | {r["designation"] for r in PLA if r["designation"]}, key=len,
               reverse=True)

# ---- where each entry is: the 3D scheme's place of the device it names, as one walk (cabinet, console, machine)
PL_ITEM = {r["item"]: r for r in PLA if r["item"]}
PL_DESIG = {}                                     # designation -> its placements row (dev, mark, conn items first)
for _r in sorted(PLA, key=lambda r: r["item"].split(".")[0] not in ("dev", "mark", "conn")):
    if _r["designation"] and _r["x_mm"]:
        PL_DESIG.setdefault(_r["designation"], _r)
BU_LEG = {r["leg"]: r for r in BUN}
# A device without a box of its own (a plug, a suppressor, a board part) is sought at its carrier: the placed device
# its own netlist rows say it sits across, on board or on (in this order of preference), else the placed device of
# the same place it has most conductors to (up to three when they tie).
HOST_PAT = [("across", r"\bacross (?:the coil of )?([A-Z][A-Z0-9]*)"), ("on board", r"\bon board ([A-Z][A-Z0-9]*)"),
            ("on the", r"\bon the ([A-Z][A-Z0-9]*)\b")]
HOST = {}                                         # designation -> (how, [placed designations])
for _d in OrderedDict.fromkeys(d["designation"] for d in DEV):
    if _d in PL_DESIG:
        continue
    _txt = [r["function_en"] + " " + r["note"] for r in DEV if r["designation"] == _d]
    _hit = next(((how, m.group(1)) for how, pat in HOST_PAT for t in _txt for m in re.finditer(pat, t)
                 if m.group(1) in PL_DESIG and m.group(1) != _d), None)
    if _hit:
        HOST[_d] = (f"its netlist row says \"{_hit[0]} {_hit[1]}\"", [_hit[1]])
        continue
    _nb = Counter()
    for _w in WIR:
        for a, b in (("from_device", "to_device"), ("to_device", "from_device")):
            if _w[a] == _d and _w[b] in PL_DESIG and PLACE.get(_w[b]) == PLACE.get(_d) and PLACE.get(_d):
                _nb[_w[b]] += 1
    if _nb:
        _top = [n for n, c in _nb.items() if c == max(_nb.values())][:3]
        HOST[_d] = (f"the device{'s' if len(_top) > 1 else ''} of the same place it has most conductors to", _top)
# a text ending in a device's name and one space: the next name is a terminal of that device ("UZ1 E3")
TERMINAL_BEFORE = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(d) for d in DESIG) + r") $")
ROW_Z = {}                                        # cabinet plate row as photographed -> mean Z of its items
for _r in PLA:
    if _r["photo_row"].isdigit():
        ROW_Z.setdefault(int(_r["photo_row"]), []).append(float(_r["z_mm"]))
ROW_Z = {k: sum(v) / len(v) for k, v in sorted(ROW_Z.items())}
NO_PLACE = 999
WALK = ("cabinet: door, switch plate, plate rows 1 (top) to 7 (bottom), left wall, floor, the wall toward the machine "
        "(cable entries), then its outside face (connectors XC1-XC4); console: left, middle, right part as the operator "
        "sees it, each part inside then outside; machine: the front "
        "(operator side) from left to right, the right side from front to rear, the rear (backgauge end) from right to "
        "left, the left side from rear to front, last the middle of the knife and clamp zone (under the covers)")


def num(s):
    t = f"{float(s):.1f}".rstrip("0").rstrip(".")
    return "0" if t in ("-0", "") else t


def place_of_point(x, y, z):
    if x <= -1245 and -205 <= y <= 305:
        return "cabinet"
    if z >= 1185 and -500 <= y <= -400 and -840 <= x <= 855:
        return "console"
    return "machine"


def area_of(place, x, y, z, photo_row=""):
    """(area label, rank in the walk, order inside the area) of a point of the 3D scheme"""
    if place.startswith("cabinet"):
        if place == "cabinet outside face":
            return "cabinet, outside face toward the machine", 21, -z
        if photo_row == "door":
            return "cabinet, door", 10, -z
        if photo_row == "switch plate":
            return "cabinet, switch plate", 10.3, -z
        if photo_row.isdigit():                   # along the row: left to right as seen through the door (Y down)
            return f"cabinet, plate row {photo_row} of 7", 10 + int(photo_row), -y
        if photo_row == "left wall":
            return "cabinet, left wall", 18, -z
        if photo_row == "floor":
            return "cabinet, floor", 19, -y
        if place == "cabinet wall":               # cable entries in the wall toward the machine (X -1250)
            return "cabinet, wall toward the machine (cable entries)", 20, -z
        k = min(ROW_Z, key=lambda k: abs(ROW_Z[k] - z))
        if abs(ROW_Z[k] - z) <= 40:               # its own rank, just after the photographed row k
            return f"cabinet, plate row {k} of 7 (by height)", 10 + k + 0.25, -y
        above = max((k for k in ROW_Z if ROW_Z[k] > z), default=0)
        if not above:
            return "cabinet, above plate row 1 (by height)", 10.5, -y
        if above == max(ROW_Z):
            return f"cabinet, below plate row {above} (by height)", 10 + above + 0.5, -y
        return f"cabinet, between plate rows {above} and {above + 1} (by height)", 10 + above + 0.5, -y
    if place.startswith("console"):
        part = 0 if x < -280 else 2 if x > 280 else 1
        out = "outside" in place                  # its own rank, just after the inside of the same part
        return ("console, " + ("left", "middle", "right")[part] + " part" + (", outside" if out else ""),
                30 + part + (0.5 if out else 0), x)
    side = 0 if x < -350 else 2 if x > 350 else 1
    sname = ("left", "middle", "right")[side]
    if y < -150:
        return f"machine, front (operator side), {sname}", 40 + side, x
    if y > 600:
        return f"machine, rear (backgauge end), {sname}", 46 - side, -x
    if side == 2:
        return "machine, knife and clamp zone, right side", 43, y
    if side == 0:
        return "machine, knife and clamp zone, left side", 47, -y
    return "machine, knife and clamp zone, middle (under the covers)", 48, y


def area_of_row(r):
    rail = re.match(r"mount\.rail\.R(\d)$", r["item"])     # plate rail Rn carries plate row n (same height)
    return area_of(r["place"].strip(), float(r["x_mm"]), float(r["y_mm"]), float(r["z_mm"]),
                   rail.group(1) if rail and not r["photo_row"] else r["photo_row"])


def spot_of_row(r):
    if not r["item"]:
        return f"{r['designation']}: no box (not fitted)"
    carrier = r["fastened_to"].split("; ")[0] if r["fastened_to"] else "no carrier named"
    return f"{r['designation'] or r['item']} on {carrier}, z {num(r['z_mm'])}"


def leg_end(b, which):
    """placements row of a bundle leg's end, or a point dict for a junction (first or last point of path_mm)"""
    item = b["from_item" if which == 0 else "to_item"]
    if item in PL_ITEM:
        return PL_ITEM[item]
    pts = [p.split() for p in b["path_mm"].split(";") if p.strip()]
    x, y, z = (float(v) for v in pts[0 if which == 0 else -1])
    return dict(item=item, designation="", place=place_of_point(x, y, z), x_mm=x, y_mm=y, z_mm=z, photo_row="",
                fastened_to="")


def now_item(r):
    if not r["item"]:
        return (f"now in the 3D scheme: no box (not fitted); point x {num(r['x_mm'])}, y {num(r['y_mm'])}, "
                f"z {num(r['z_mm'])} mm")
    pt = [num(r[c]) for c in ("x_mm", "y_mm", "z_mm")]
    box = [num(r[c]) for c in ("box_x_mm", "box_y_mm", "box_z_mm")]
    t = f"now in the 3D scheme: x {pt[0]}, y {pt[1]}, z {pt[2]} mm ({'anchor' if r['anchor'] else 'box centre'})"
    t += f"; box {num(r['size_x_mm'])} x {num(r['size_y_mm'])} x {num(r['size_z_mm'])} mm"
    if box != pt:
        t += f", centre x {box[0]}, y {box[1]}, z {box[2]}"
    t += f"; fastened to {r['fastened_to'].replace('; ', ', ')}"
    if r["photo_row"]:
        t += f"; photo row {r['photo_row']}"
    if r["moves_with"]:
        t += f"; moves with the {r['moves_with']}"
    return t


def now_leg(b):
    clips = [c for c in b["clips"].split("; ") if c]
    carriers = list(OrderedDict.fromkeys(c.split("@", 1)[1] for c in clips if "@" in c))
    t = (f"now in the 3D scheme: length {num(b['length_mm'])} mm, diameter {num(b['diameter_mm'])} mm, "
         f"{len(clips)} clips" + (" on " + ", ".join(carriers) if carriers else ""))
    if b["passes"]:
        t += f"; passes {b['passes'].replace('; ', ', ')}"
    if b["moves_with"]:
        t += f"; moves with the {b['moves_with']}"
    return t


def locate_desig(k):
    """(placements rows, where text) of a designation: its own box, else the device it is sought at (HOST)"""
    if k in PL_DESIG:
        return [PL_DESIG[k]], spot_of_row(PL_DESIG[k])
    if k in HOST:
        how, hosts = HOST[k]
        rows = [PL_DESIG[h] for h in hosts]
        return rows, (f"{k} ({PLACE.get(k) or 'place not given'}): no box in the 3D scheme; sought at "
                      f"{', '.join(hosts)} ({how}): " + "; ".join(spot_of_row(r) for r in rows))
    return [], f"{k} ({PLACE.get(k) or 'place not given'}; no box in the 3D scheme)"


def locate_one(how, k):
    """(placements rows or junction points, where text) of one thing an entry names"""
    if how == "item":
        return ([PL_ITEM[k]], spot_of_row(PL_ITEM[k])) if k in PL_ITEM else \
            ([], f"{k} (no box in the 3D scheme)")
    if how == "leg":
        return ([leg_end(BU_LEG[k], 0), leg_end(BU_LEG[k], 1)], "") if k in BU_LEG else ([], "")
    if how == "desig":
        return locate_desig(k)
    hits = []                       # "text": every designation (placed or with a carrier) and rail it names, except
    for d in list(PL_DESIG) + list(HOST):  # a name right after another device's name: its terminal ("UZ1 E3")
        for m in re.finditer(r"(?<![A-Za-z0-9])" + re.escape(d) + r"(?![A-Za-z0-9])", k):
            if not TERMINAL_BEFORE.search(k[:m.start()]):
                hits.append((m.start(), -len(d), d))
                break
    for m in re.finditer(r"\brails? (\d)(?:\s*(?:and|,)\s*(\d))?", k):    # "rail 4" = the plate rail mount.rail.R4
        hits += [(m.start(), 0, f"mount.rail.R{g}") for g in m.groups() if g and f"mount.rail.R{g}" in PL_ITEM]
    rows = []
    for _, _, d in sorted(hits):
        rows += [PL_ITEM[d]] if d.startswith("mount.rail.") else locate_desig(d)[0]
    spots = list(OrderedDict.fromkeys(spot_of_row(r) for r in rows))
    return rows, ("in the 3D scheme: " + "; ".join(spots[:4]) + (f"; and {len(spots) - 4} more (area column)"
                                                                 if len(spots) > 4 else "")) if spots else ""


def set_area(e):
    """area column, walk order and table of an entry; with spots, where = each named thing on its carrier, height"""
    rows, wh, located = [], [], []
    for how, k in e["loc"]:
        got, spot = locate_one(how, k)
        rows += got
        wh.append(spot)
        located.append(bool(got))
    best = {}                                     # area label -> (rank, order inside the area) of its first point
    for r in rows:
        lab, rank, sub = area_of_row(r)
        best[lab] = min(best.get(lab, (rank, sub)), (rank, sub))
    walk = sorted(best.items(), key=lambda kv: (kv[1][0], kv[0]))      # the areas in walk order
    e["area"] = " -> ".join(lab for lab, _ in walk) if walk else (
        f"{e['group']}, no 3D place" if e["group"] in GROUPS[:3] else "no 3D place")
    # sort key: the areas in walk order (an entry with two ends sorts by the end first in the walk, after the
    # entries of that area alone), then the place inside the first area
    e["walk"] = (tuple((v[0], lab) for lab, v in walk), walk[0][1][1]) if walk else (((NO_PLACE, ""),), 0)
    if e.get("spots"):
        e["where"] = "; ".join(OrderedDict.fromkeys(w for w in wh if w))
    elif e["loc"][0][0] == "text" and wh[0]:      # P, C, D: the spec's place, then the devices it names in 3D
        e["where"] = f"{e['where']}; {wh[0]}"
    # The table: the place of the areas when every thing the entry names has one (devices, boxes, cable ends); for a
    # text entry (P, C, D) only when its text names no device of a known place and no place word.
    places = {lab.split(",")[0] for lab, _ in walk}
    if walk and all(located) and e["loc"][0][0] != "text":
        e["group"] = places.pop() if len(places) == 1 else GROUPS[3]
    elif walk and e["loc"][0][0] == "text" and not e.get("named") and len(places) == 1:
        e["group"] = places.pop()


def plain_sure(ev):
    return ev.strip() == "sure"


def thread_lines(rows, kind):
    """(file under netlist/, line in the thread's own file, header = line 1) for each merged row."""
    seen, out = Counter(), []
    for r in rows:
        seen[r["thread"]] += 1
        out.append((f"{r['thread']}_{kind}.csv", seen[r["thread"]] + 1))
    return out


def places_named(text):
    """the places (cabinet, console, machine) of the devices a text names, else of the place words it uses"""
    found = set()
    for dsg in DESIG:
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(dsg) + r"(?![A-Za-z0-9])", text):
            pl = PLACE.get(dsg, "")
            if pl in ("cabinet", "console", "machine"):
                found.add(pl)
    if not found:
        for w in ("cabinet", "console", "machine"):
            if re.search(r"\b" + w + r"\b", text, re.I):
                found.add(w)
    return found


def group_of(text, fixed=""):
    if fixed in ("cabinet", "console", "machine"):
        return fixed
    found = places_named(text)
    return found.pop() if len(found) == 1 else GROUPS[3]


def err_of(*texts):
    for t in texts:
        m = re.search(r"±\s*\d[\d.,]*(?:\s*(?:%|mm|columns?|col\b))?", t)
        if m:
            return m.group(0)
    if any("[?]" in t for t in texts):
        return "[?] (unclear)"
    return "not given"


def moves_of(what):
    return "may" if re.search(r"\b(place|position|route|length|height|distance|mounted|facing)\b", what, re.I) else "no"


# The words of the likely-error column besides a ± or a [?] the source gives (explained in "How to read").
ERR_YESNO = "reading or yes/no check (no ±)"
ERR_NOSPEC = "no ± in the spec: measure it"
ERR_PP = "[?]: photo and print differ"
ERR_X = "[?]: two netlists give different values"
ERR_FORM = re.compile(r"±|^\[\?\]")


def err_pcd(what, why):
    """P, C and D entries: the ± or [?] their text gives, else what kind of check it is (never an invented ±)"""
    e = err_of(what, why)
    return e if e != "not given" else ERR_NOSPEC if moves_of(what) == "may" else ERR_YESNO


def parse_spec(path, heading):
    lines = (S / path).read_text(encoding="utf-8").splitlines()
    i0 = lines.index(heading)
    i1 = next((i for i in range(i0 + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    head, rows, stated, intro = None, [], None, []
    for ln in lines[i0 + 1:i1]:
        m = re.match(r"^(\d+) rows:", ln)
        if m:
            stated = int(m.group(1))
        if ln.startswith("| # |"):
            head = [c.strip() for c in re.split(r"(?<!\\)\|", ln.strip()[1:-1])]
        elif re.match(r"^\|\s*\d+\s*\|", ln):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", ln.strip()[1:-1])]
            rows.append(dict(zip(head, cells)))
        elif ln.startswith("**") and not intro:
            intro.append(ln)
    return head, rows, stated, intro


def main():
    bad, entries, per_source = [], [], OrderedDict()
    # 1. The four on-site lists of the specs.
    layout_keys, safety = {}, ""
    pl_line = {r["item"]: i for i, r in enumerate(PLA, start=2)}
    bu_line = {r["leg"]: i for i, r in enumerate(BUN, start=2)}
    key_num = {(lt, r["Key"].replace("`", "")): r["#"] for lt, _, pa, hd in SPEC_LISTS[:3]
               for r in reversed(parse_spec(pa, hd)[1])}     # (letter, key) -> first row number with that key
    wires_of = {t: rd(S / f"netlist/{t}_wires.csv") for t in LIST_LETTER}
    n_ptr = 0
    for letter, thread, path, heading in SPEC_LISTS:
        head, rows, stated, intro = parse_spec(path, heading)
        sec = heading.split()[1].rstrip(".")
        nums = [r["#"] for r in rows]
        per_source[f"{path} section {sec}"] = len(rows)
        if not rows or len(set(nums)) != len(nums):
            bad.append(f"{path}: {len(rows)} rows, numbers unique: {len(set(nums)) == len(nums)}")
        if stated is not None and stated != len(rows):
            bad.append(f"{path}: states {stated} rows, parsed {len(rows)}")
        if letter == "P" and intro:
            safety = re.sub(r"\(entry (\d+)\)", lambda m: f"(entry P{m.group(1)} below)", intro[0]).replace(
                "; section 2)", "; spec/power.md section 2)")
        by_num = {r["#"]: r for r in rows}
        for r0 in rows:
            # P, C, D: "as entry n" takes row n's text, "entry n" becomes this list's id, the live row is marked LIVE;
            # area and 3D location stay found from the row's own key and place (r0)
            r = r0 if letter == "L" else {k: live_mark(refs(list_ptr(v, r0["Key"].replace("`", ""), key_num), letter))
                                          for k, v in own_text(r0, by_num, letter).items()}
            if letter != "L":
                r["Key"] = wire_lines(r["Key"], thread)
                n_ptr += wire_lines_hold(f"{letter}{r['#']}", r["Key"].replace("`", ""), thread, wires_of[thread], bad)
            src = f"{path} section {sec} #{r['#']}"
            if letter == "L":
                key = r["row"]
                if key in pl_line:
                    src += f"; scheme_3d/placements.csv line {pl_line[key]}"
                    layout_keys[("p", key)] = 1
                elif key in bu_line:
                    src += f"; scheme_3d/bundles.csv line {bu_line[key]}"
                    layout_keys[("b", key)] = 1
                else:
                    bad.append(f"layout row {r['#']} {key}: not a placements item or bundle leg")
                where = " ".join(x for x in (r["designation or bundle"], r["place or ends"]) if x)
                fixed = r["place or ends"] if r["place or ends"] in ("cabinet", "console", "machine") else ""
                now = now_item(PL_ITEM[key]) if key in PL_ITEM else now_leg(BU_LEG[key]) if key in BU_LEG else \
                    "not in the 3D scheme"
                entries.append(dict(id=f"L{r['#']}", key=key, what=r["what to check on site"], where=where,
                                    why=f"{now}; stage-1 measure rows: {r['related stage-1 measure rows']}",
                                    err=r["evidence"], moves="yes", src=src,
                                    group=group_of(key + " " + where, fixed),
                                    loc=[("item" if key in PL_ITEM else "leg", key)], spots=key in PL_ITEM))
            else:
                what = r.get("What to check") or r.get("Look at or measure", "")
                why = r.get("Why") or r.get("Raised by") or r.get("How", "")
                if "How" in r:
                    why = "how: " + why
                key, key0 = r["Key"].replace("`", ""), r0["Key"].replace("`", "")
                entries.append(dict(id=f"{letter}{r['#']}", key=key, what=what, where=r["Where"], why=why,
                                    err=err_pcd(what, why), moves=moves_of(what), src=src,
                                    group=group_of(key0 + " " + r0["Where"]),
                                    named=places_named(key0 + " " + r0["Where"]),
                                    loc=[("text", key0 + "; " + r0["Where"])], spots=False))
    print(f"measure_list.md: wire keys of the P, C and D lists with a netlist line: {n_ptr}, each compared with "
          f"its line in netlist/<thread>_wires.csv")
    # Placements and bundles rows not plain "sure" that the layout list does not carry (FF1).
    extra = 0
    for kind, rows, col, fname, lines in (("p", PLA, "item", "placements.csv", pl_line),
                                          ("b", BUN, "leg", "bundles.csv", bu_line)):
        for r in rows:
            if not plain_sure(r["evidence"]) and (kind, r[col]) not in layout_keys:
                extra += 1
                loc = [("leg", r[col])] if kind == "b" else [("item", r[col])] if r[col] else \
                    [("desig", r["designation"])]
                entries.append(dict(id=f"L+{extra}", key=r[col] or r.get("designation", ""),
                                    what="confirm the place, or that it is not fitted",
                                    where=r.get("place") or f"{r['from_item']} -> {r['to_item']}",
                                    why=f"{now_leg(r) if kind == 'b' else now_item(r)}; {r['evidence']}; note: "
                                        f"{full(r['note'])}", err=err_of(r["evidence"]),
                                    moves="yes", src=f"scheme_3d/{fname} line {lines[r[col]]}",
                                    group=group_of(r[col], r.get("place", "")), loc=loc, spots=kind == "p"))
    per_source["placements and bundles rows not in the layout list"] = extra
    # 2. Netlist rows: evidence not plain "sure", or a note that compares the 568 print with a photo.
    n_ns = n_pp = n_both = 0
    for kind, rows in (("devices", DEV), ("wires", WIR)):
        merged_line = {id(r): i for i, r in enumerate(rows, start=2)}
        for r, (fname, line) in zip(rows, thread_lines(rows, kind)):
            ns = not plain_sure(r["evidence"])
            pp = bool(re.search(r"print|\b568\b", r["note"], re.I) and re.search(r"photo", r["note"], re.I))
            if not (ns or pp):
                continue
            n_ns += ns
            n_pp += pp
            if kind == "devices":
                key, where = r["designation"], r["place"]
                what = f"confirm the device: {r['kind']}, {r['function_en']}" + (
                    f", {r['type_rating']}" if r["type_rating"] else "")
                grp = group_of(key, r["place"])
                loc = [("desig", key)]
            else:
                key = (f"wire {r['wire']}: " if r["wire"] else "") + \
                      f"{r['from_device']} {r['from_terminal']} -> {r['to_device']} {r['to_terminal']}"
                ends = sorted({PLACE.get(r["from_device"], ""), PLACE.get(r["to_device"], "")} - {""})
                where = " - ".join(ends)
                what = "confirm the conductor and its terminals" + (f" ({r['signal']})" if r["signal"] else "")
                grp = ends[0] if len(ends) == 1 else GROUPS[3]
                loc = [("desig", r["from_device"]), ("desig", r["to_device"])]
            reason = []
            if ns:
                reason.append(f"evidence {r['evidence']}")
            if pp:
                agrees = re.search(r"\bas printed\b", r["note"]) and not re.search(r"hand|correct|\[\?\]", r["note"])
                reason.append("print and photo compared: " + ("agrees as printed" if agrees else
                                                              "differ, or the photo shows part of it; where photo "
                                                              "and print differ, the photo rated sure counts"))
            n_both += ns and pp
            entries.append(dict(id=("N" if ns else "F") + f"{THREAD_LETTER[r['thread']]}{kind[0]}{line}", key=key,
                                what=what, where=where or "not given",
                                why="; ".join(reason) + "; note: " + refs(full(r["note"]), LIST_LETTER[r["thread"]]),
                                err=err_of(r["evidence"]) if ns else ERR_YESNO if agrees else ERR_PP,
                                moves="no (wiring)", src=f"netlist/{fname} line {line}; netlist/merged_{kind}.csv "
                                                         f"line {merged_line[id(r)]}", group=grp, loc=loc,
                                spots=True))
    per_source["netlist rows not plain sure"] = n_ns
    per_source["netlist rows whose note compares print and photo"] = (
        n_pp - n_both, f"{n_pp} ({n_pp - n_both} own F entries + {n_both} within the N entries above, which are also "
                       f"not plain sure)")
    # 3. Device fields two threads give different values for.
    n_x = 0
    for i, c in enumerate(CON, start=2):
        if c["kind"] != "device field" or c["class"] != "differs":
            continue
        n_x += 1
        entries.append(dict(id=f"X{i}", key=f"{c['key']} {c['field']}", what="read the nameplate or the wiring and "
                            "settle which value holds", where=PLACE.get(c["key"], "not given"),
                            why=f"values: {full(c['values'])}; reading: {full(c['reading'])}",
                            err=ERR_X, moves="no", src=f"netlist/merged_conflicts.csv line {i}; "
                            + c["rows"], group=group_of(c["key"], PLACE.get(c["key"], "")),
                            loc=[("desig", c["key"])], spots=True))
    per_source["device fields that differ between the netlists (merged_conflicts.csv)"] = n_x
    write_measure(entries, per_source, safety, bad)
    write_sources(bad)
    for k, v in per_source.items():
        print(f"{k}: {v[1] if isinstance(v, tuple) else v}")
    return bad


CTX = {}
NOT_ABBR = {  # words in capitals that are no abbreviations: Czech words quoted from the print, makers, type
    # names, English words printed in capitals, a Roman numeral
    "POSUV", "VZAD", "RYCHLOSTI", "SEDLA", "FUNKCE", "POHONU", "TABULKA", "LINIE", "KONEKTORU", "NA",
    "ONLINE", "INPUTS", "PANELWARE", "MK",          # PLC port labels as printed, a B&R product name, initials in a label
    "SAMWHA", "EUCHNER", "OMRON", "COMPACT", "BMR", "BY", "TX", "ZN", "JOC", "XCK", "MS", "PS",
    "ANALOG", "OUTPUTS", "ON", "LOW", "CONFLICT", "OPTION", "III"}


def abbr_line():
    return "Abbreviations, with their full names (first use): " + "; ".join(f"{k} ({v})" for k, v in ABBR.items()) + "."


def used_abbr(txt):
    """the abbreviation line of a page, cut down to the abbreviations the rest of the page uses"""
    body = txt.replace(abbr_line(), "")
    used = [(k, v) for k, v in ABBR.items()
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(k) + r"(?![A-Za-z0-9])", body)]
    return txt.replace(abbr_line(), "Abbreviations, with their full names (first use): "
                       + "; ".join(f"{k} ({v})" for k, v in used) + ".")


def abbr_check(name, txt, bad):
    first = txt.index("Abbreviations, with their full names")
    body = txt[first:]
    dsg = {d for d in DESIG}
    left = Counter()
    for m in re.finditer(r"(?<![\w/.&-])([A-Z]{2,})(?![\w&])", body):
        tok = m.group(1)
        if tok not in ABBR and tok not in dsg and tok not in NOT_ABBR:
            left[tok] += 1
            CTX.setdefault(tok, body[max(0, m.start() - 45):m.end() + 25])
    head = txt[:first]
    early = [k for k in ABBR if re.search(r"(?<![A-Za-z0-9])" + re.escape(k) + r"(?![A-Za-z0-9])", head)]
    print(f"{name}: abbreviations used without a full name: {len(left)}"
          + (" (" + ", ".join(f"{k} x{v}" for k, v in left.most_common()) + ")" if left else "")
          + f"; used before the abbreviation line: {len(early)}" + (f" ({', '.join(early)})" if early else ""))
    if left or early:
        bad.append(f"{name}: abbreviations {dict(left)} {early}")


READ_COLS = ("key", "what", "where", "why", "err")
UNIT_BAD = re.compile(r"\d\s?cm\b|(?<![\w.,])\d+(?:[.,]\d+)? m\b(?![²³/])")


def text_rules(entries, bad):
    """Self-checks of the text rules on every cell as written (tester 3, round 1): no cell cut by this script (a
    "…" must stand in the source text itself), no Cyrillic outside ( ) or [ ], lengths in mm, every likely error
    one of the legend's forms, every N and F id decoding to the netlist file and line of its source column."""
    src_text = " ".join(" ".join(p.read_text(encoding="utf-8").split()) for p in
                        sorted((S / "netlist").glob("*.csv")) + sorted((S / "spec").glob("*.md"))
                        + [S / "scheme_3d/placements.csv", S / "scheme_3d/bundles.csv"])
    inv = {v: k for k, v in THREAD_LETTER.items()}
    ids = {e["id"] for e in entries}
    wires_of = {t: rd(S / f"netlist/{t}_wires.csv") for t in LIST_LETTER}
    n = Counter()
    for e in entries:
        for k in READ_COLS:
            raw, r = full(e[k]), reader(e[k])
            for m in re.finditer("…", raw):
                n["…"] += 1
                if raw[max(0, m.start() - 20):m.end()] not in src_text:
                    bad.append(f"measure list {e['id']} {k}: a cell cut with '…' ({raw[max(0, m.start() - 30):m.end()]})")
            for c in outside_brackets(r, CYR):
                bad.append(f"measure list {e['id']} {k}: Cyrillic outside brackets: {c}")
            for m in UNIT_BAD.finditer(r):
                bad.append(f"measure list {e['id']} {k}: length not in mm: {m.group(0)}")
            # cross-references a technician can follow (critic g12, round 3): no bare entry number, no workflow
            # word "episode", no pointer into a spec's list, and every id named after entry/entries/same as exists
            for m in BARE_ENTRY.finditer(r):
                bad.append(f"measure list {e['id']} {k}: bare entry number: {r[max(0, m.start() - 30):m.end() + 5]}")
            if re.search(r"\bepisode", r, re.I) or re.search(r"spec/\w+\.md`?, (?:this|on-site) list", r):
                bad.append(f"measure list {e['id']} {k}: workflow word or spec-list pointer left: {r[:80]}")
            # a netlist line number names its file where it first stands in a cell (critic g13, round 4)
            m1 = LINE_FIRST.search(r)
            if (m1 and not m1[1]) or BARE_WIRE_LINE.search(r):
                bad.append(f"measure list {e['id']} {k}: a line number without its file: {r[:90]}")
            line_ptrs(e["id"], k, r, wires_of, bad, n)
            for m in ENTRY_REF.finditer(r):
                n["entry refs"] += 1
                for i in re.findall(r"[A-Z]\+?\d+", m[1]):
                    if i not in ids:
                        bad.append(f"measure list {e['id']} {k}: names entry {i}, which the list does not have")
            if r != raw and mm_units(raw) != raw:
                n["mm"] += 1
                print(f"  {e['id']} {k}: mm: " + "; ".join(sorted({m.group(0) for m in UNIT_BAD.finditer(raw)})))
        er = reader(e["err"])
        if not (ERR_FORM.search(er) or er in (ERR_YESNO, ERR_NOSPEC)):
            bad.append(f"measure list {e['id']}: likely error not one of the legend's forms: {er}")
        n["err " + (er if er in (ERR_YESNO, ERR_NOSPEC, ERR_PP, ERR_X) else "± or [?] of the source")] += 1
        m = re.match(r"^[NF]([pcd])([dw])(\d+)$", e["id"])
        if e["id"][0] in "NF" and not (m and f"netlist/{inv[m[1]]}_{'devices' if m[2] == 'd' else 'wires'}.csv "
                                             f"line {m[3]};" in e["src"]):
            bad.append(f"measure list {e['id']}: id does not decode to the netlist line of its source {e['src']}")
    # the wire keys wire_lines_hold compared before the reader are the ones checked on the page as written
    pre = sum(1 for e in entries if e["id"][:1] in "PCD" for _ in WIRE_PTR.finditer(e["key"]))
    post = sum(v for k, v in n.items() if k.startswith("wire keys checked on the page"))
    if pre != post:
        bad.append(f"measure list: {pre} wire keys with a line in the P, C and D keys, {post} checked on the page")
    print("measure_list.md text rules: " + ", ".join(f"{k} {v}" for k, v in sorted(n.items())))


def id_order(i):
    return "PCDLNFX".find(i[0]), int(re.sub(r"\D", "", i) or 0), i


def safety_block(entries, safety, bad):
    """'Safety first': the power list's paragraph with its ids given their letter, then every entry made with the
    supply on, built from the rows marked LIVE, so the ids cannot drift from the rows (tester 3, round 1)"""
    s = re.sub(r"\b([Ee])ntry (\d+)\b", r"\1ntry P\2", safety)
    m = re.search(r"Entry (P\d+) is the only measurement on live parts\.", s)
    if not m:
        bad.append("Safety first: the sentence naming the power list's measurement on live parts was not found")
        return [s, ""]
    p_live = m.group(1)
    s = s.replace(m.group(0), f"Among the power entries (P), {p_live} is the only measurement on live parts.")
    text = lambda e: " ".join(str(e[k]) for k in ("what", "where", "why"))
    live = [e["id"] for e in entries if re.search(r"\bLIVE\b", text(e))]
    if p_live not in live:   # live_mark() gives the power list's live row the LIVE mark (critic g12, round 3)
        bad.append(f"Safety first: {p_live}, the power list's measurement on live parts, is not marked LIVE")
    run = sorted((e["id"] for e in entries if e["id"] in live and e["id"] != p_live
                  and re.search(r"two-hand", text(e))), key=id_order)
    cv = sorted((e["id"] for e in entries if e["id"] in live and e["id"] not in run and e["id"] != p_live
                 and re.search(r"control voltage only", text(e))), key=id_order)
    rest = sorted((i for i in live if i not in run and i not in cv and i != p_live), key=id_order)
    on = sorted(live, key=id_order)
    ids = {e["id"] for e in entries}
    def names(xs):
        return ", ".join(xs[:-1]) + " and " + xs[-1] if len(xs) > 1 else "".join(xs)
    para = (f"**Work with the supply on: {len(on)} entries, {', '.join(on)}.** {p_live} is the measurement on live "
            f"mains parts above. {names(run)} start the machine (M1, a cut from the two-hand buttons) while the "
            "cabinet is open and a meter fixed beforehand reads: the knife and the clamp can move, so nobody reaches "
            "into the cabinet, the knife opening or the clamp zone while the machine is on. "
            + (f"{names(cv)} run with control voltage only, as each row defines it. " if cv else "")
            + (f"{names(rest)} are read with the supply on, from a lamp, an LED or a meter fixed while the machine "
               "was isolated. " if rest else "")
            + "Each of these rows is marked LIVE and gives its own method: fix every meter lead while the machine is "
            "isolated, keep hands clear while the supply is on, and isolate again before touching anything. (Built "
            "by the script from the rows marked LIVE; the other rows are made with the machine isolated.)")
    back = re.findall(r"\b[PCDLNFX]\d+\b", para.split("**")[1])
    if set(back) != set(live) or not set(back) <= ids or not run:
        bad.append(f"Safety first: ids {sorted(back)} differ from the rows marked LIVE {sorted(live)}")
    print(f"measure_list.md: Safety first names {len(on)} supply-on entries ({', '.join(on)}); machine run {run}, "
          f"control voltage only {cv}")
    return [s + " (Copied from spec/power.md section 9, ids given their letter; spec/control.md section 11 says the "
                "same.)", "", para, ""]


def write_measure(entries, per_source, safety, bad):
    moved = Counter()
    for i, e in enumerate(entries):
        g0 = e["group"]
        set_area(e)
        e["order"] = i
        if e["group"] != g0:
            moved[f"{g0} -> {e['group']}"] += 1
    print(f"measure_list.md: entries whose table follows the 3D scheme instead of the netlist place: "
          f"{sum(moved.values())}" + (" (" + ", ".join(f"{k} {v}" for k, v in sorted(moved.items())) + ")"
                                      if moved else ""))
    out = ["# On-site measure list of the electrical installation, Adast Maxima MS 115 PS (serial 578.0009)", "",
           "Generated by stage_2_electronics/schemes_2d/integration_lists.py (the integration step); do not edit by "
           "hand, rerun the script. Everything below is a check to make at the machine: a value the drawings could "
           "not fix, a row marked [?] (unclear) or estimated, or a place where the cabinet photos and the 1998 print "
           "568-70.9001 [SCHÉMA ZAPOJENÍ] differ.", "", abbr_line(), "",
           "## Safety first", ""] + safety_block(entries, safety, bad) + [
           "## How to read this list", "",
           "- x, y, z: millimetres in the machine frame of the 3D model, the same frame as stage 1 (stage_1_mechanics). "
           "X runs along the knife, + to the operator's right (the operator stands at the front table, facing the "
           "machine); Y + from the cutting line toward the backgauge (rear); Z up. X 0 = middle of the cutting width, "
           "Y 0 = cutting line (where the knife edge meets the cutting stick), Z 0 = floor (underside of the feet), so "
           "every z in this list, \"where\" included, is a height above the floor. X 0 is itself an estimate (±20 mm, "
           "stage-1 measure row frame.M2): mark the middle of the cutting width first and measure each x from that "
           "mark. The model stands at rest: knife up, clamp up, backgauge pusher face at Y 1150, so a device on the "
           "knife, the clamp or the backgauge carriage has its x, y, z only in that pose. (Sources: "
           "stage_1_mechanics/spec/frame.md lines 15-17; stage_1_mechanics/spec/knife.md line 4; "
           "stage_1_mechanics/spec/clamp.md line 4; stage_1_mechanics/spec/backgauge.md line 3.)",
           "- One table per place: cabinet, console, machine, and a last table for entries between places or in the "
           "documents. An entry whose devices, boxes or cable ends all have an area (below) goes to the table of their "
           "place, or to the last table when they lie in two places. Otherwise the place comes from the place column "
           "of the netlist device rows the entry names (for P, C and D entries the devices or the place word their "
           "text names), and an entry naming devices of two places goes to the last table.",
           "- area (walk order): where the entry is, taken from the 3D scheme (scheme_3d/placements.csv) for the "
           "device, box or cable end the entry names. Each table runs in one walk, so a technician passes each area "
           "once: " + WALK + ". In the cabinet the area is the plate row as photographed (photo_row column), left to "
           "right as seen through the door; \"by height\" means no photo row is given, so the nearest plate row by "
           "height Z is named. On the console and the machine the area comes from X and Y of the device: left and right "
           "of X ±280 mm on the console and X ±350 mm on the machine, the front below Y -150 mm, the rear above Y 600 mm. "
           "An entry with two ends (a wire, a cable leg) shows its areas in walk order (A -> B) and sorts by the end "
           "that comes first in the walk, after the entries of that area alone. A device without a box of its own (a "
           "plug, a suppressor, a part on a board) is sought at the device its netlist row says it sits across, on "
           "board or on (\"across Y3\", \"on board UG50\", \"on the PLC\"), else at the device of the same place it "
           "has most conductors to, and takes that device's area. For P, C and D entries the area comes from every "
           "device their key and place text name (a name right after another device's name, such as E3 in \"UZ1 E3\", "
           "is a terminal of that device and is skipped); \"rail 4\" there is the plate rail mount.rail.R4, which "
           "carries plate row 4. \"no 3D place\" means the entry names no device the 3D scheme places; such entries "
           "come last in their table.",
           "- where: for L, L+ (placed boxes), N, F and X entries each device the entry names, on what it is fastened "
           "to and at which height z in mm (placements.csv), or \"no box in the 3D scheme\" with the device it is "
           "sought at; for a cable leg its two ends; for P, C and D entries the place the spec gives, then (\"in the "
           "3D scheme:\") the devices its text names, each on its carrier and height, at most four. A carrier written "
           "with dots is the body of the 3D model the device is fastened to, part first: mount.plate is the cabinet's "
           "mounting plate, mount.rail.R4 its rail 4 (plate row 4), housing.cabinet the cabinet itself, and a "
           "machine name such as safety_sensors.S10 or clamp.brake_y14 the machine part at that device (the area column "
           "says where it is). Notes quote the netlists of the drawings: power (568 sheets 1-3), control (sheets 4-7), "
           "PLC and drive (sheet 8).",
           "- current value, reason: for L and L+ first what the 3D scheme holds now (\"now in the 3D scheme\": a box "
           "with x, y, z in mm, its size, what it is fastened to and its photo row; a cable leg with its length, "
           "diameter, clips and what they hold on to, and the openings it passes), then the stage-1 measure rows that "
           "move it (L) or the evidence and note of the row (L+); for N and F the evidence and the netlist note, while "
           "the key column holds the wire and its terminals as the netlist has them now; for X the values the netlists "
           "give; for P, C and D the reason or the method the spec gives.",
           "- id: P = spec/power.md section 9, C = spec/control.md section 11, D = spec/plc_drive.md section 11, "
           "L = spec/layout_3d.md section 11 (placements and bundles of the 3D scheme), L+ = a placements or bundles "
           "row not plain sure that the layout list leaves out, N = a netlist row not plain sure (then the netlist: p = "
           "power, c = control, d = PLC and drive; then the file: d = devices or w = wires; then the line in that file, "
           "so Ndw9 is line 9 of netlist/plc_drive_wires.csv), F = a netlist row whose note compares the 568 print with a "
           "photo (same letters), X = a device field two netlists give different values for (merged_conflicts.csv "
           "line).",
           "- references inside a cell: \"entry P11\" or \"same as P11\" is the entry with that id in this list; a "
           "wire key \"from -> to (power_wires.csv line 99)\" gives the wire's line in that file of the netlist "
           "folder, stage_2_electronics/netlist (header = line 1), and a following \"(line 100)\" is a line of the same "
           "file.",
           "- likely error, one of these: the ± the source gives, in mm unless a unit is written (a column is a column "
           "of the 568 sheet), often after \"estimated\" and with the source's words on what it covers; \"[?] "
           "(unclear)\" or \"[?] ...\" where the source marks the row unclear; \"" + ERR_PP + "\" where the cabinet "
           "photo and the 1998 print disagree and the check decides which holds; \"" + ERR_X + "\" for X entries, "
           "where the check decides between the values in the current value column; \"" + ERR_YESNO + "\" for a "
           "wiring, nameplate or presence check, where a ± has no meaning; \"" + ERR_NOSPEC + "\" where a place, "
           "length or height is asked for and the spec gives no error. No ± is made up where the source gives none.",
           "- moves a device or route: yes for every placements or bundles row (the 3D scheme changes), may where the "
           "entry asks for a place, position, route, length or height, no for wiring and nameplate checks.",
           "", "Entries per source (none dropped; the script fails when a count differs from its source):", ""]
    for k, v in per_source.items():
        out.append(f"- {k}: {v[1] if isinstance(v, tuple) else v}")
    total = len(entries)
    summed = sum(v[0] if isinstance(v, tuple) else v for v in per_source.values())
    ids = Counter(e["id"] for e in entries)
    dup = sorted(i for i, c in ids.items() if c > 1)
    print(f"measure_list.md: entries {total}, sum of the counts per source {summed}, ids repeated {len(dup)}"
          + (f" ({', '.join(dup[:10])})" if dup else ""))
    if summed != total or dup:
        bad.append(f"measure list: {total} entries, counts per source add up to {summed}, repeated ids {dup[:10]}")
    out += ["", f"{total} entries in all (the counts above add up to it), each with its own id.", ""]
    for g in GROUPS:
        es = sorted((e for e in entries if e["group"] == g), key=lambda e: (e["walk"], e["order"]))
        out += [f"## {g[0].upper() + g[1:]} ({len(es)} entries)", "",
                "| id | area (walk order) | key | what to check | where | current value, reason | likely error | "
                "moves a device or route | source |", "|---|---|---|---|---|---|---|---|---|"]
        for e in es:
            out.append("| " + " | ".join(cell(reader(e[k]) if k in READ_COLS else e[k])
                                         for k in ("id", "area", "key", "what", "where", "why", "err", "moves", "src"))
                       + " |")
        out.append("")
        # Self-check of the walk: no area comes back once the table has left it (first area, and the whole column).
        for what, seq in (("first area", [e["area"].split(" -> ")[0] for e in es]), ("area", [e["area"] for e in es])):
            done, back = set(), []
            for a, b in zip(seq, seq[1:]):
                if a != b:
                    done.add(a)
                    if b in done:
                        back.append(b)
            if back:
                bad.append(f"measure list, {g}: {what} comes back after the walk left it: {back[:3]}")
        print(f"  {g}: {len(es)} entries, areas {len(set(e['area'].split(' -> ')[0] for e in es))}, "
              f"no 3D place {sum(1 for e in es if e['walk'][0][0][0] == NO_PLACE)}")
    late = [e["id"] for e in entries if e["id"].startswith("L") and not e["why"].startswith("now in the 3D scheme")]
    print(f"measure_list.md: L and L+ entries {sum(1 for e in entries if e['id'].startswith('L'))}, "
          f"without the value the 3D scheme holds now {len(late)}" + (f" ({', '.join(late[:10])})" if late else ""))
    if late:
        bad.append(f"measure list: L or L+ entries without the current 3D value: {late[:10]}")
    text_rules(entries, bad)
    txt = "\n".join(out)
    txt = used_abbr(txt)
    # Self-check: every row not plain "sure" of the netlists, placements and bundles is named in the list.
    miss = []
    for kind, rows in (("devices", DEV), ("wires", WIR)):
        for r, (fname, line) in zip(rows, thread_lines(rows, kind)):
            if not plain_sure(r["evidence"]) and f"netlist/{fname} line {line};" not in txt:
                miss.append(f"{fname} {line}")
    for fname, rows in (("placements.csv", PLA), ("bundles.csv", BUN)):
        for i, r in enumerate(rows, start=2):
            if not plain_sure(r["evidence"]) and not re.search(rf"scheme_3d/{fname} line {i}(?!\d)", txt):
                miss.append(f"{fname} {i}")
    print(f"measure_list.md: {total} entries; rows not plain sure missing from the list: {len(miss)}"
          + (f" ({', '.join(miss[:10])})" if miss else ""))
    if miss:
        bad.append(f"measure list misses {len(miss)} rows")
    abbr_check("measure_list.md", txt, bad)
    user_path(txt, "measure_list.md", bad)
    # the whole page, legend and Safety first included: no bare entry number, no "episode" (critic g12, round 3)
    left = [txt[max(0, m.start() - 40):m.end() + 5] for rx in (BARE_ENTRY, re.compile(r"\bepisode", re.I))
            for m in rx.finditer(txt)]
    print(f"measure_list.md: bare entry numbers and the word episode left on the page: {len(left)}")
    if left:
        bad.append(f"measure list: bare entry numbers or 'episode' left: {left[:5]}")
    # a pointer of the shape run_checks.py check 5 searches for ("netlist/<file> line n", "scheme_3d/<file> line n")
    # stands once on the page, in the source column of its own entry: anywhere else it would keep a row listed after
    # its entry is lost (critic g14, round 5: the legend's example named a real [?] row). Own: an N or F id's netlist
    # line and its merged twin, an X id's conflicts line, an L or L+ entry's placements or bundles line.
    inv = {v: k for k, v in THREAD_LETTER.items()}
    twin = {k: {fl: i for i, fl in enumerate(thread_lines(rows, k), start=2)} for k, rows in (("devices", DEV),
                                                                                             ("wires", WIR))}
    ptr5 = re.compile(r"(?:netlist|scheme_3d)/[\w.]+\.csv line \d+(?!\d)")
    on_page, in_src, stray = Counter(m[0] for m in ptr5.finditer(txt)), Counter(), []
    for e in entries:
        found = [m[0] for m in ptr5.finditer(cell(e["src"]))]
        in_src.update(found)
        m = re.match(r"^[NF]([pcd])([dw])(\d+)$", e["id"])
        if m:
            k = "devices" if m[2] == "d" else "wires"
            f = f"{inv[m[1]]}_{k}.csv"
            own ={f"netlist/{f} line {m[3]}", f"netlist/merged_{k}.csv line {twin[k].get((f, int(m[3])))}"}
        elif e["id"][0] == "X":
            own = {f"netlist/merged_conflicts.csv line {e['id'][1:]}"}
        else:
            own = {p for p in found if p.startswith("scheme_3d/")} if e["id"][0] == "L" else set()
        stray += [f"{e['id']} names {p}" for p in found if p not in own]
    stray += [f"{p}: {on_page[p]} times on the page, {in_src[p]} in source columns" for p in sorted(on_page)
              if on_page[p] != 1 or in_src[p] != 1]
    print(f"measure_list.md: pointers of check 5's shape {sum(on_page.values())}, outside their own entry's source "
          f"column or repeated {len(stray)}")
    if stray:
        bad.append(f"measure list: pointers that would keep a row listed without its own entry: {stray[:5]}")
    (S / "measure_list.md").write_text(txt, encoding="utf-8", newline="\n")


def user_path(txt, name, bad):
    pat = r"[A-Za-z]:[/\\]Users[/\\]" + (f"|{re.escape(Path.home().name)}" if len(Path.home().name) > 2 else "")
    if re.search(pat, txt, re.I):   # the user's name is read at run time, never written in a file
        bad.append(f"{name} holds a user path")


def gone_folder(s):
    """the highest folder of a source path that is not on this computer (the same rule as run_checks.py check 5)"""
    parts = s.split("/")[:-1]
    for k in range(1, len(parts) + 1):
        if not (P / "/".join(parts[:k])).is_dir():
            return "/".join(parts[:k])
    return None


def describe(src, cites):
    name = src.split("/")[-1]
    m = re.match(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})\.jpg$", name)
    when = f"taken {m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}:{m.group(6)}" if m else ""
    shows = ", ".join(sorted(cites["keys"], key=lambda s: (len(s), s))[:10]) + (
        ", …" if len(cites["keys"]) > 10 else "")
    sheets = ", ".join(sorted(cites["sheets"], key=lambda s: (len(s), s)))
    if "maxima_photos/" in src:
        return f"photo of the machine, {when}; named by the rows of: {shows}", "local only, not committed"
    if "wiring_and_plc_diagrams/" in src:
        return (f"photo of a page of the wiring set 568-70.9001 [SCHÉMA ZAPOJENÍ], {when}; sheets of the rows citing "
                f"it: {sheets or 'not given'}; rows of: {shows}"), "local only, not committed"
    if "operating_manual/" in src:
        return f"photo of a page of the OM, {when}; rows of: {shows}", "local only, not committed"
    if "control_panel_manual/" in src:
        return f"photo of a page of the console panel's manual, {when}; rows of: {shows}", "local only, not committed"
    if "8200_series/" in src:
        return (f"photo of a page of the Lenze 8200 inverter operating instructions (paper copy kept with the "
                f"machine), {when}; rows of: {shows}"), "local only, not committed"
    if "/artifacts/web/" in src:
        return f"web download (W, weaker evidence): {name}; rows of: {shows}", "local only, not committed"
    if "/artifacts/tables/" in src:
        return (f"table transcribed from the sources while preparing episode 2 (local memory block): {name}; rows of: "
                f"{shows}"), "local only, not committed"
    if "static_dynamic_memory/" in src:
        return f"note of the local memory block of episode 2: {name}; rows of: {shows}", "local only, not committed"
    if src.startswith("stage_1_mechanics/"):
        return f"output of the stage-1 mechanical model: {name}; rows of: {shows}", "committed (stage 1, f52cc8e)"
    return f"{name}; rows of: {shows}", "committed" if src.startswith("stage_2_electronics/") else "not known"


def write_sources(bad):
    cites = OrderedDict()
    for fname, rows, kcols in (("netlist/merged_devices.csv", DEV, ("designation",)),
                               ("netlist/merged_wires.csv", WIR, ("from_device", "to_device")),
                               ("scheme_3d/placements.csv", PLA, ("item",)), ("scheme_3d/bundles.csv", BUN, ("leg",))):
        for r in rows:
            for s in r["source_path"].split(";"):
                s = s.strip()
                if not s:
                    continue
                c = cites.setdefault(s, dict(files=Counter(), marks=Counter(), keys=set(), sheets=set()))
                c["files"][fname.split("/")[-1]] += 1
                ev = r["evidence"].strip()
                c["marks"]["sure" if ev == "sure" else "[?]" if ev.startswith("[?]") else
                           "estimated" if ev.startswith("estimated") else "W" if ev.startswith("W") else ev[:24]] += 1
                c["keys"].update(r[k] for k in kcols if r.get(k))
                if r.get("sheet"):
                    c["sheets"].add(r["sheet"])
    order = sorted(cites, key=lambda s: (s.split("/")[0], s))
    absent, missing = Counter(), []     # folders not on this computer (as run_checks.py check 5); files missing in a present one
    for s in order:
        if (P / s).exists():
            continue
        top = None if s.split("/")[0] in ("stage_1_mechanics", "stage_2_electronics") else gone_folder(s)
        if top:
            absent[top] += 1
        else:
            missing.append(s)
    out = ["# Sources of the electrical schemes, Adast Maxima MS 115 PS (serial 578.0009)", "",
           "Generated by stage_2_electronics/schemes_2d/integration_lists.py (thread t5, integration); rerun the "
           "script, do not edit by hand.", "", abbr_line(), "",
           "## What this page lists", "",
           f"Every source path that a row of netlist/merged_devices.csv, netlist/merged_wires.csv, "
           f"scheme_3d/placements.csv or scheme_3d/bundles.csv cites ({len(order)} paths, all relative to the "
           f"repository root). Marks of the rows: sure, [?] (unclear), "
           f"estimated with its likely error, W (web, weaker evidence). The photos and the photographed documents "
           f"under preparatory_data_analysis, and the tables and downloads under static_dynamic_memory, stay on "
           f"this computer: they are never committed (only results go to GitHub). The specs under "
           f"stage_2_electronics/spec name further sources in their own Sources sections.", "",
           "| source path | what it holds | marks of the rows citing it | rows citing it, by file | committed |",
           "|---|---|---|---|---|"]
    for s in order:
        c = cites[s]
        what, com = describe(s, c)
        marks = ", ".join(f"{k} {v}" for k, v in sorted(c["marks"].items()))
        files = ", ".join(f"{k} {v}" for k, v in sorted(c["files"].items()))
        out.append("| " + " | ".join(cell(x) for x in (s, what, marks, files, com)) + " |")
    out += ["", "## What the set does not know yet", ""]
    out += [f"- {li}" for li in draw.limit_lines()]
    out += ["", "## Rebuild and check", "",
            "Run from the repository root (the folder that holds stage_1_mechanics and stage_2_electronics), in this "
            "order; each command ends with a result line, the last one writes stage_2_electronics/checks/checks.txt. "
            "The sheet pages and the 3D layer are written by the thread scripts named in their specs; stage 1 is only "
            "read.", "", "```"] + draw.COMMANDS + ["```", "", draw.PROOF_TEXT, "", "```"] + draw.PROOF_RUNS + ["```", ""]
    txt = "\n".join(out)
    if missing:
        bad.append(f"sources missing: {missing[:5]}")
    listed = sum(1 for s in order if f"| {cell(s)} |" in txt)
    print(f"sources.md: {len(order)} source paths, listed {listed}, missing on disk {len(missing)}, "
          f"not checked (folder not on this computer) {sum(absent.values())}, "
          f"web (W) {sum(1 for s in order if '/artifacts/web/' in s)}, "
          f"local only {sum(1 for s in order if not s.startswith(('stage_1', 'stage_2')))}")
    for top, k in sorted(absent.items()):
        print(f"INFO: {k} source paths not checked: their folder {top} is not on this computer (local only, never "
              f"committed)")
    if listed != len(order):
        bad.append("sources.md: a path is not listed")
    txt = used_abbr(txt)
    abbr_check("sources.md", txt, bad)
    user_path(txt, "sources.md", bad)
    (S / "sources.md").write_text(txt, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    problems = main()
    for b in problems:
        print("FAIL:", b)
    print("result:", "FAIL" if problems else "PASS")
    sys.exit(1 if problems else 0)
