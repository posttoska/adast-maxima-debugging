#!/usr/bin/env python3
"""Thread t5 (integration), part 3: the overview page, the connections page and the index page of the 2D schemes.

Reads only files under stage_2_electronics:
  netlist/merged_devices.csv, merged_wires.csv, merged_cores.csv (written by integration_merge.py),
  scheme_3d/bundles.csv and scheme_3d/contact_report.txt (thread t4), the <title> or first heading of the sheet pages.
Writes:
  schemes_2d/overview.svg     the whole machine on one page: every designation of merged_devices.csv drawn once, in
                              the block of the 568 sheet that shows its circuit; cabinet, console, machine; the cable
                              bundles between them with the cores they carry (counted from merged_cores.csv)
  schemes_2d/connections.svg  one line per drawn core of merged_cores.csv, grouped by bundle, with the cabinet-side
                              wiring of each connector pin, the bundle legs (route) and the far terminal; the connector
                              pins that stay inside the cabinet; every connector pin named in merged_wires.csv
  schemes_2d/index.html       relative links to the 10 pages, the viewer, the lists, specs, netlists and checks; the
                              rebuild and check commands; what the set does not know yet (no "://" in the file)
Run from the repository root (the folder that holds stage_2_electronics):
  python -B stage_2_electronics/schemes_2d/integration_draw.py
It ends with "result: PASS" when its self-check holds: every designation once on the overview, every drawn core once
on the connections page, every connector pin of merged_wires.csv shown, no text box overlapping another or leaving its
box or the page (Consolas advance 0.55 em, the pages' font), no "://" in index.html. Output is the same on every run.
"""
import csv
import html
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent            # stage_2_electronics/schemes_2d
S = HERE.parent                                   # stage_2_electronics
NL = S / "netlist"


def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


DEV = rd(NL / "merged_devices.csv")
WIR = rd(NL / "merged_wires.csv")
COR = rd(NL / "merged_cores.csv")
BUN = rd(S / "scheme_3d" / "bundles.csv")
BY = OrderedDict()
for _r in DEV:
    BY.setdefault(_r["designation"], []).append(_r)


def mark(ev):
    """evidence cell -> class: s sure, q [?], e estimated, w web"""
    ev = (ev or "").strip()
    if ev.startswith("[?]"):
        return "q"
    if ev.startswith("estimated"):
        return "e"
    if ev == "W" or ev.startswith("W ") or ev.startswith("W("):
        return "w"
    return "s"


RANK = {"s": 0, "w": 1, "e": 2, "q": 3}


def dev_cls(d):
    return max((mark(r["evidence"]) for r in BY[d]), key=RANK.get)


def sheet_key(s):
    m = re.match(r"\d+", s)
    return (int(m.group()) if m else 99, s)


def sheets_of(d):
    return ", ".join(sorted({r["sheet"] for r in BY[d] if r["sheet"]}, key=sheet_key))


def place_of(d):
    for r in BY.get(d, []):
        if r["place"]:
            return r["place"]
    return ""


def nat(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s or "")]


def ev_short(ev):
    """evidence up to its first remark, e.g. estimated ±100, [?] estimated ±200, estimated ±1 column, sure"""
    return (ev or "").split(" (")[0].split(";")[0].strip()


def ev_mm(ev):
    s = ev_short(ev)
    return s + " mm" if s[-1:].isdigit() else s


# short English function per device for the pages (from function_en of merged_devices.csv, cut to fit a cell;
# no designation of another device in it, so that each designation is printed once on the overview)
SHORT = {
    "XP": "mains connection terminals", "ZF1": "mains interference filter", "FA4": "service socket breaker",
    "XC7": "service socket 230 V (110 V)", "PE": "protective earth strip", "X5": "working earth strip, 0 V",
    "Q1": "main switch [HLAVNÍ VYPÍNAČ]", "QF1": "motor breaker, knife drive", "QF2": "motor breaker, blower",
    "KM1A": "main contactor", "KM1B": "main contactor", "KM2": "knife motor line contactor",
    "KM3": "knife motor delta contactor", "KM4": "knife motor star contactor", "KM8": "blower motor contactor",
    "FA3": "inverter supply breaker", "X2": "inverter feed terminals", "ZF2": "inverter input filter",
    "UZ1": "frequency inverter [MĚNIČ]",
    "FA1": "transformer primary breaker", "FA2": "transformer primary breaker", "T1": "control transformer",
    "X11": "transformer tap terminals", "UG50": "power-supply board",
    "Q2": "knife motor run switch (cam)", "S2": "lighting / cut-line selector", "S4": "blower motor switch",
    "KM6": "cut clutch contactor", "KM7": "cut clutch contactor", "KT1": "star-delta timer",
    "KT2": "cut delay timer", "K1": "relay, air-cushion magnet", "K2": "feed-cut interlock relay",
    "BMR1": "cut-control module", "RC...": "group name, sheet 1 list", "RC1": "coil suppressor",
    "RC2": "coil suppressor", "RC3": "coil suppressor", "RC4": "coil suppressor", "RC6": "coil suppressor",
    "RC7": "coil suppressor", "RC8": "coil suppressor", "V20": "free-wheel diode, timer coil",
    "R14": "series resistor, clamp brake",
    "PLC": "(programmable logic controller), type COMPACT",
    "XC50": "control-system connector, inverter speed setpoint",
    "X10": "terminal strip in the cabinet", "XC60": "connector, link to the console",
    "XC2": "table-cabinet connector", "XC4": "encoder connector", "XC1": "feed motor connector",
    "XC3": "blower motor connector",
    "S1": "emergency stop", "TABLO": "operator control panel", "XC70": "connector from the cabinet",
    "E1": "work-surface lighting lamp", "E2": "work-surface lighting lamp", "E3": "cut-line indication lamp",
    "E4": "cut-line indication lamp", "S28": "clamp plate sensor", "S30": "clamp top position sensor",
    "Y14": "clamp brake magnet", "V14": "diode across the clamp brake", "M1": "knife and hydraulics motor",
    "Y10": "cut clutch (with brake)", "V10": "Zener diode pair, clutch", "R10": "resistor across the clutch",
    "S5": "belt-pulley cover interlock", "S19": "clutch switch, knife change", "Y11": "hydraulics magnet (clamping)",
    "RC11": "suppressor, hydraulics", "X8": "knife sensors terminal strip", "S12": "knife position sensor (cam)",
    "S13": "knife position sensor (cam)", "S14": "knife position sensor (cam)", "SQ1": "knife lock sensor",
    "SQ2": "knife lock sensor", "Y01": "knife-lock magnet", "V01": "diode across the lock magnet",
    "S10": "cut start button", "S11": "cut start button", "S24": "saddle front limit switch",
    "S27": "saddle rear reference switch", "BR40": "backgauge position encoder", "M2": "backgauge feed motor",
    "M3": "air-cushion blower motor", "Y3": "air-cushion magnet (valve)", "C3": "suppression capacitor",
    "FF1": "light curtain (option)",
}

# ---------------------------------------------------------------- SVG page with a text-box self-check
STYLE = ("text{font-family:Consolas,'DejaVu Sans Mono','Courier New',monospace;fill:#111}"
         ".b{font-weight:bold}.fn{fill:#333}.sh{fill:#7a7a7a}.i{font-style:italic;fill:#444}"
         ".s{fill:#000}.q{fill:#b00000}.e{fill:#1f5fbf}.w{fill:#8a5a00}.o{fill:#a34f00}.rt{fill:#5a3a00}"
         ".fr{fill:none;stroke:#111;stroke-width:1.4}.bl{fill:#fbfbfb;stroke:#444;stroke-width:1}"
         ".hd{fill:#e9e9e9;stroke:#444;stroke-width:1}.sub{fill:#fff;stroke:#999;stroke-width:0.8}"
         ".ex{fill:#fff7e8;stroke:#b86a00;stroke-width:1}.gp{fill:#fbfbfb;stroke:#666;stroke-width:0.9}"
         ".cb{stroke:#e07800;stroke-width:2.4;fill:none}.cd{fill:#e07800}"
         ".ls{stroke:#000;stroke-width:1.1}.lq{stroke:#b00000;stroke-width:1.1;stroke-dasharray:6 3}"
         ".le{stroke:#1f5fbf;stroke-width:1.1;stroke-dasharray:2 2}.lw{stroke:#8a5a00;stroke-width:1.1;stroke-dasharray:8 2 2 2}"
         ".il{stroke:#777;stroke-width:0.9}.rb{fill:#fff}.dt{fill:#000}")


def f1(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


class Page:
    ADV = 0.55          # Consolas advance width per em

    def __init__(self, w, title):
        self.w, self.h, self.title = w, 0, title
        self.el, self.tb, self.regions = [], [], {}

    def t(self, x, y, s, size=10, cls="", anchor="start", region=None):
        w = self.ADV * size * len(s)
        x0 = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2)
        self.tb.append((x0, y - 0.78 * size, x0 + w, y + 0.22 * size, s, region))
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        c = f' class="{cls}"' if cls else ""
        self.el.append(f'<text x="{f1(x)}" y="{f1(y)}" font-size="{f1(size)}"{a}{c}>{html.escape(s, quote=False)}</text>')
        return x0 + w

    def rect(self, x, y, w, h, cls):
        return f'<rect x="{f1(x)}" y="{f1(y)}" width="{f1(w)}" height="{f1(h)}" class="{cls}"/>'

    def r(self, *a):
        self.el.append(self.rect(*a))

    def line(self, x1, y1, x2, y2, cls):
        self.el.append(f'<line x1="{f1(x1)}" y1="{f1(y1)}" x2="{f1(x2)}" y2="{f1(y2)}" class="{cls}"/>')

    def dot(self, x, y, r, cls):
        self.el.append(f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{f1(r)}" class="{cls}"/>')

    def svg(self):
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">\n'
                f'<title>{html.escape(self.title, quote=False)}</title>\n<style>{STYLE}</style>\n'
                f'<rect x="0" y="0" width="{self.w}" height="{self.h}" fill="#fff"/>\n'
                f'<rect x="8" y="8" width="{self.w - 16}" height="{self.h - 16}" class="fr"/>\n'
                + "\n".join(self.el) + "\n</svg>\n")

    def check(self):
        bad = []
        for x0, y0, x1, y1, s, reg in self.tb:
            if x0 < 10 or y0 < 10 or x1 > self.w - 10 or y1 > self.h - 10:
                bad.append(f"text outside the page frame: {s!r}")
            if reg:
                rx0, ry0, rx1, ry1 = self.regions[reg]
                if x0 < rx0 + 1 or x1 > rx1 - 1 or y0 < ry0 + 1 or y1 > ry1 - 1:
                    bad.append(f"text leaves its box {reg}: {s!r}")
        tb = sorted(self.tb)
        for i, a in enumerate(tb):
            for b in tb[i + 1:]:
                if b[0] >= a[2]:
                    break
                if b[1] < a[3] and a[1] < b[3]:
                    bad.append(f"text overlap: {a[4]!r} / {b[4]!r}")
        return bad


# ---------------------------------------------------------------- overview
CAB_BLOCKS = [
    ("Mains feed, main switch and power part", "568 sheet 2", 3, [
        ("mains feed and service socket", ["XP", "ZF1", "FA4", "XC7"]),
        ("main switch", ["Q1"]),
        ("earthing", ["PE", "X5"]),
        ("motor breakers and contactors", ["QF1", "QF2", "KM1A", "KM1B", "KM2", "KM3", "KM4", "KM8"]),
        ("frequency inverter of the backgauge feed", ["FA3", "X2", "ZF2", "UZ1"])], None),
    ("Control transformer and control voltages", "568 sheet 3", 3, [
        ("transformer, its breakers and taps", ["FA1", "FA2", "T1", "X11"]),
        ("power-supply board: +27 V, +24 V, +33 V rectified; ~24 V, ~48 V alternating", ["UG50"])], [
        ("rectifiers", ["V1", "V2", "V4"]),
        ("filter capacitors", ["C1", "C2", "C4"]),
        ("fuses of the windings", ["FU21", "FU22", "FU24", "FU25", "FU26", "FU27"]),
        ("indicator diodes", ["V11", "V12", "V13", "UG50/V14", "V15", "V16", "V17"]),
        ("indicator LEDs (light-emitting diodes)", ["V21", "V22", "V23", "V24", "V25", "V26", "V27"]),
        ("indicator resistors", ["R11", "R12", "UG50/R14", "R15", "R16", "R17"])]),
    ("Control relays, cut cycle, magnets and safety", "568 sheets 4-7", 3, [
        ("switches on the cabinet", ["Q2", "S2", "S4"]),
        ("contactors, timers, relays and the cut-control module", ["KM6", "KM7", "KT1", "KT2", "K1", "K2", "BMR1"]),
        ("RC (resistor-capacitor) coil suppressors, free-wheel diode, series resistor",
         ["RC...", "RC1", "RC2", "RC3", "RC4", "RC6", "RC7", "RC8", "V20", "R14"])], None),
    ("Controller and backgauge drive control", "568 sheet 8", 2, [(None, ["PLC", "XC50"])], None),
]
CONSOLE = ("console", "CONSOLE, operator side, above the knife opening", None, ["S1", "TABLO", "XC70"])
MACHINE_GROUPS = [
    ("lamps", "Lamps on the console front", None, ["E1", "E2", "E3", "E4"]),
    ("clamp", "Clamp beam: brake and position sensors", None, ["S28", "S30", "Y14", "V14"]),
    ("drive", "Main drive, knife and hydraulics", "INNER",
     ["M1", "Y10", "V10", "R10", "S5", "S19", "Y11", "RC11", "X8", "S12", "S13", "S14", "SQ1", "SQ2", "Y01", "V01"]),
    ("table", "Front table and backgauge", None, ["S10", "S11", "S24", "S27", "BR40"]),
    ("feed", "Backgauge feed motor and air cushion", None, ["M2", "M3", "Y3", "C3"]),
    ("none", "Not fitted on this machine", "certificate entry — (dash); no box in the 3D (three-dimensional) scheme", ["FF1"]),
]
EXIT_ORDER = ["XC60", "X10", "XC2", "XC4", "XC1", "XC3"]


def trunk(route):
    return " > ".join(leg for leg in route.split(" > ") if leg and "-" not in leg)


def cabinet_end(c):
    """(cabinet device, terminal, far device, terminal) of a core; None when both ends are on the machine"""
    if c["from_place"] == "cabinet" and c["to_place"] != "cabinet":
        return c["from_device"], c["from_terminal"], c["to_device"], c["to_terminal"]
    if c["to_place"] == "cabinet" and c["from_place"] != "cabinet":
        return c["to_device"], c["to_terminal"], c["from_device"], c["from_terminal"]
    return None


def build_overview(bad):
    W = 1800
    pg = Page(W, "568-70.9001 overview: the whole machine on one page (thread t5, redrawn 2026, not an original document)")
    pg.t(22, 36, "Adast Maxima MS 115 PS (serial 578.0009, 1998), wiring set 568-70.9001 [SCHÉMA ZAPOJENÍ]: "
                 "overview of the whole machine", 17, "b")
    pg.t(22, 56, "Redrawn 2026 by thread t5 from netlist/merged_devices.csv and merged_cores.csv (not an original document). "
                 "Each device is drawn once, in the block of the sheet that shows its circuit;", 10.5, "fn")
    pg.t(22, 71, "the grey numbers after a name are all the 568 sheets that show it (sheet 1 = device list). "
                 "Wiring detail: the sheet pages; cores between cabinet, console and machine: connections.svg.", 10.5, "fn")

    groups = [CONSOLE] + MACHINE_GROUPS
    group_of = {d: g[0] for g in groups for d in g[3]}
    arrows, inner_machine = OrderedDict(), 0
    for c in COR:
        if c["drawn"] != "yes":
            continue
        e = cabinet_end(c)
        if e is None:
            inner_machine += 1
            continue
        ex, far = e[0], e[2]
        if far not in group_of:
            bad.append(f"overview: far device {far} of core {c['thread']} {c['line']} is in no block")
            continue
        k = (ex, group_of[far])
        a = arrows.setdefault(k, [0, []])
        a[0] += 1
        if trunk(c["route"]) not in a[1]:
            a[1].append(trunk(c["route"]))
    for ex, _ in arrows:
        if ex not in EXIT_ORDER:
            bad.append(f"overview: cabinet end {ex} is not among the exits")

    # ---- right side: console and machine frames; their cable lines fix the heights of the exits
    RX, RW = 1180, 600
    GX, GW = RX + 8, RW - 16
    CX0, CW = 842, 210                    # exits strip inside the cabinet frame
    top = 84
    lines = []                            # (exit, y, label)

    def group_box(g, gy, title_cls="b"):
        gid, title, extra, names = g
        i0 = len(pg.el)
        rid = "g_" + gid
        pg.t(GX + 8, gy + 15, title, 11.5, title_cls, region=rid)
        yy = gy + 21
        if extra:
            txt = extra if extra != "INNER" else (f"plus {inner_machine} cores on the machine from the knife sensors' "
                                                  "terminal strip to the sensors (leg B4-K)")
            pg.t(GX + 8, yy + 10, txt, 9.5, "i", region=rid)
            yy += 14
        rows_top = yy
        cw = GW / 2
        for k, d in enumerate(names):
            chip(pg, GX + (k % 2) * cw, yy + (k // 2) * 17, cw, d, rid)
        nrows = -(-len(names) // 2)
        mine = sorted(((ex, a) for (ex, gg), a in arrows.items() if gg == gid),
                      key=lambda t: EXIT_ORDER.index(t[0]) if t[0] in EXIT_ORDER else 99)
        for i, (ex, a) in enumerate(mine):
            lines.append((ex, rows_top + 8 + i * 38, f"{' / '.join(a[1])}, {a[0]} cores"))
        yy = max(rows_top + nrows * 17, rows_top + 8 + len(mine) * 38 - 18) + 8
        pg.el.insert(i0, pg.rect(GX, gy, GW, yy - gy, "gp"))
        pg.regions[rid] = (GX, gy, GX + GW, yy)
        return yy

    # console frame
    i0 = len(pg.el)
    pg.t(RX + 8, top + 17, CONSOLE[1], 13, "b", region="console")
    yb = group_box(("console", "devices of the console", None, CONSOLE[3]), top + 26, "i") + 8
    pg.el.insert(i0, pg.rect(RX, top, RW, yb - top, "bl"))
    pg.regions["console"] = (RX, top, RX + RW, yb)
    # machine frame
    my = yb + 14
    i0 = len(pg.el)
    pg.t(RX + 8, my + 17, "MACHINE: field devices on the machine body", 13, "b", region="machine")
    gy = my + 26
    for g in MACHINE_GROUPS:
        gy = group_box(g, gy) + 8
    machine_bottom = gy

    # ---- left side: cabinet blocks
    LX, LW = 32, 798
    y = top + 30
    for title, sheet, ncol, groups_, board in CAB_BLOCKS:
        y = block(pg, LX, y, LW, title, sheet, ncol, groups_, board, "b_" + sheet.replace(" ", "_")) + 12
    cab_bottom = y

    # ---- exits: one chip per cabinet end, spanning all its cable lines
    ys = OrderedDict((ex, []) for ex in EXIT_ORDER)
    for ex, yy, _ in lines:
        ys.setdefault(ex, []).append(yy)
    exit_bottom = 0
    for ex, yl in ys.items():
        if not yl:
            bad.append(f"overview: exit {ex} carries no core")
            continue
        y0, y1 = min(yl) - 15, max(yl) + 15
        rid = "x_" + ex
        pg.r(CX0, y0, CW, y1 - y0, "ex")
        pg.regions[rid] = (CX0, y0, CX0 + CW, y1)
        pg.t(CX0 + 6, y0 + 12, ex, 11.5, "b dev " + dev_cls(ex), region=rid)
        pg.t(CX0 + CW - 6, y0 + 12, sheets_of(ex), 9, "sh", anchor="end", region=rid)
        pg.t(CX0 + 6, y0 + 25, SHORT[ex], 9.5, "fn", region=rid)
        exit_bottom = max(exit_bottom, y1)
    pg.t(CX0 + CW / 2, top + 22, "exits to the field", 10, "i", anchor="middle", region="cabinet")
    pg.t((CX0 + CW + GX) / 2, top + 22, "cable bundles", 9.5, "i", anchor="middle")
    for ex, yy, lab in lines:
        x1, x2 = CX0 + CW, GX
        pg.line(x1, yy, x2, yy, "cb")
        pg.dot(x1, yy, 3.2, "cd")
        pg.dot(x2, yy, 3.2, "cd")
        pg.t((x1 + x2) / 2, yy - 5, lab, 9.5, "o", anchor="middle")

    bottom = max(cab_bottom, exit_bottom + 10, machine_bottom) + 4
    pg.el.insert(0, pg.rect(20, top, 1040, bottom - top, "bl"))
    pg.el.insert(1, pg.rect(RX, my, RW, bottom - my, "bl"))
    pg.regions["cabinet"] = (20, top, 1060, bottom)
    pg.regions["machine"] = (RX, my, RX + RW, bottom)
    pg.t(LX, top + 22, "CABINET [ROZVADĚČ] at the left end of the machine", 13, "b", region="cabinet")

    # ---- legend
    ly = bottom + 24
    sp = Page.ADV * 10.5                          # one character (SVG drops leading and trailing spaces)
    x = pg.t(22, ly, "Names:", 10.5, "b") + sp
    for cls, word, rest in (("s", "black", "= sure (568 print or cabinet photo);"),
                            ("q", "red", "= [?] unclear, on the on-site list measure_list.md;"),
                            ("e", "blue", "= estimated ±error;"),
                            ("w", "brown", "= W (web source, weaker evidence).")):
        x = pg.t(x, ly, word, 10.5, "b " + cls) + sp
        x = pg.t(x, ly, rest, 10.5, "fn") + 2 * sp
    ly += 18
    pg.line(22, ly - 4, 62, ly - 4, "cb")
    pg.dot(22, ly - 4, 3.2, "cd")
    pg.dot(62, ly - 4, 3.2, "cd")
    pg.t(70, ly, "cable bundle with the number of cores it carries (netlist/merged_cores.csv); routes estimated, "
                 "unseen legs ±200 mm (millimetres); the 3D routes are in viewer/index.html.", 10.5, "fn")
    ly += 18
    pg.t(22, ly, "Cabinet and console devices are boxes at their photographed places in the 3D scheme; "
                 "field devices sit on the anchors of the stage-1 mechanical model.", 10.5, "fn")
    pg.h = int(ly + 22)

    # ---- self-check: every designation once
    got = re.findall(r'class="b dev [sqew]">([^<]*)</text>', "\n".join(pg.el))
    got = [html.unescape(g) for g in got]
    from collections import Counter
    cnt = Counter(got)
    missing = [d for d in BY if cnt[d] == 0]
    twice = [d for d in cnt if cnt[d] > 1]
    extra = [d for d in cnt if d not in BY]
    for d in missing:
        bad.append(f"overview: {d} not drawn")
    for d in twice:
        bad.append(f"overview: {d} drawn {cnt[d]} times")
    for d in extra:
        bad.append(f"overview: {d} is no designation of merged_devices.csv")
    nc = sum(a[0] for a in arrows.values())
    print(f"overview.svg: {len(got)} designations drawn of {len(BY)} (missing {len(missing)}, twice {len(twice)}, "
          f"extra {len(extra)}); {len(lines)} cable lines carry {nc} cores + {inner_machine} on the machine; "
          f"page {pg.w} x {pg.h}")
    return pg


def chip(pg, x, y, w, d, rid):
    pg.t(x + 6, y + 12, d, 11.5, "b dev " + dev_cls(d), region=rid)
    pg.t(x + 62, y + 12, SHORT[d], 10, "fn", region=rid)
    pg.t(x + w - 6, y + 12, sheets_of(d), 9, "sh", anchor="end", region=rid)


def block(pg, x, y, w, title, sheet, ncol, groups, board, rid):
    i0 = len(pg.el)
    pg.t(x + 8, y + 16, title, 12, "b", region=rid)
    pg.t(x + w - 8, y + 16, sheet, 11.5, "b", anchor="end", region=rid)
    yy = y + 27
    cw = w / ncol
    for head, names in groups:
        if head:
            pg.t(x + 8, yy + 11, head, 10, "i", region=rid)
            yy += 15
        for k, d in enumerate(names):
            chip(pg, x + (k % ncol) * cw, yy + (k // ncol) * 17, cw, d, rid)
        yy += -(-len(names) // ncol) * 17
    if board:
        bx, bw, b0 = x + 14, w - 28, yy + 2
        j0 = len(pg.el)
        pg.t(bx + 8, b0 + 13, "parts on the power-supply board, all on sheet 3:", 10, "i", region=rid)
        yy = b0 + 18
        for lab, names in board:
            pg.t(bx + 8, yy + 12, lab, 10, "fn", region=rid)
            nx = bx + 300
            for n in names:
                nx = pg.t(nx, yy + 12, n, 11, "b dev " + dev_cls(n), region=rid) + 12
            yy += 16
        yy += 4
        pg.el.insert(j0, pg.rect(bx, b0, bw, yy - b0, "sub"))
    yy += 6
    pg.el.insert(i0, pg.rect(x, y, w, yy - y, "bl"))
    pg.el.insert(i0 + 1, pg.rect(x, y, w, 22, "hd"))
    pg.regions[rid] = (x, y, x + w, yy)
    return yy


# ---------------------------------------------------------------- connections
CONNS = {"XC1", "XC2", "XC3", "XC4", "XC7", "XC50", "XC60"}
THREAD_RANK = {"plc_drive": 0, "control": 1, "power": 2}
BUNDLE_DESC = {
    "B1": "cabinet to the console, the lamps on the console front and, over branch B5, the clamp beam",
    "B2": "table-cabinet connector and encoder connector to the front table and the backgauge",
    "B3": "feed motor and blower connectors to the backgauge feed motor and the air cushion",
    "B4": "terminal strip in the cabinet to the main drive, the knife and the hydraulics",
}


def ends_at(r, dev, term):
    """the other end of wire r when one end is (dev, term)"""
    if r["from_device"] == dev and r["from_terminal"] == term:
        return r["to_device"], r["to_terminal"]
    if r["to_device"] == dev and r["to_terminal"] == term:
        return r["from_device"], r["from_terminal"]
    return None


def inner_of(dev, term):
    out = []
    for r in WIR:
        o = ends_at(r, dev, term)
        if o and o[0] and o[0] != dev and place_of(o[0]) == "cabinet":
            s = f"{o[0]} {o[1]}".strip()
            if s not in out:
                out.append(s)
    return out


def build_connections(bad):
    W = 1680
    pg = Page(W, "568-70.9001 connections between cabinet, console and machine (thread t5, redrawn 2026, not an original document)")
    pg.t(22, 36, "Adast Maxima MS 115 PS, wiring set 568-70.9001: connections between the cabinet, the console and the machine",
         16, "b")
    pg.t(22, 56, "Redrawn 2026 by thread t5 from netlist/merged_cores.csv and merged_wires.csv (not an original document): "
                 "one line per core that leaves the cabinet, grouped by cable bundle.", 10.5, "fn")
    pg.t(22, 71, "Abbreviations: PE (protective earth); PLC (programmable logic controller) with its inputs IN-x and outputs "
                 "OUT-x; Ø (diameter); mm (millimetres). Wire numbers as printed; ⏚ = earth.", 10.5, "fn")
    drawn = [c for c in COR if c["drawn"] == "yes"]
    core_pins = {(c[e + "_device"], c[e + "_terminal"]) for c in drawn for e in ("from", "to")}
    shown_cores, shown_pins = [], set()
    halves = [(20, ["B1", "B3"]), (850, ["B2", "B4"])]
    HW = 810
    ybot = 0
    used_internal = set()
    for x0, bl in halves:
        y = 96
        rid = f"h{x0}"
        hdr = [(2, "wire"), (178, "cabinet side"), (197, "leaves at"), (436, "bundle legs (route, estimated)"),
               (606, "far end"), (684, "device")]
        for dx, s in hdr:
            pg.t(x0 + dx, y, s, 9, "i", anchor=("end" if dx == 178 else "middle" if dx == 436 else "start"), region=rid)
        y += 8
        for b in bl:
            cs = [c for c in drawn if c["bundle"] == b]
            ext = [c for c in cs if cabinet_end(c)]
            inner = [c for c in cs if not cabinet_end(c)]
            legs = []
            for c in cs:
                for leg in c["route"].split(" > "):
                    if leg not in legs:
                        legs.append(leg)
            trunks = [lg for lg in legs if "-" not in lg]
            brow = {r["leg"]: r for r in BUN}
            y += 18
            pg.t(x0 + 2, y, f"{b} (cable bundle {b[1:]}): {len(cs)} cores, {BUNDLE_DESC[b]}", 11.5, "b", region=rid)
            y += 14
            pg.t(x0 + 2, y, "legs used: " + ", ".join(legs), 9.5, "fn", region=rid)
            y += 13
            tx = "; ".join(f"{t}: Ø {f1(float(brow[t]['diameter_mm']))} mm, {f1(float(brow[t]['length_mm']))} mm long, "
                           f"{ev_mm(brow[t]['evidence'])}" for t in trunks if t in brow)
            pg.t(x0 + 2, y, "trunk " + tx, 9.5, "fn", region=rid)
            y += 4
            for c in sorted(ext, key=lambda c: (EXIT_ORDER.index(cabinet_end(c)[0]) if cabinet_end(c)[0] in EXIT_ORDER else 99,
                                                nat(cabinet_end(c)[1]), c["thread"], int(c["line"]))):
                y += 14
                cd, ct, fd, ft = cabinet_end(c)
                core_row(pg, x0, y, c, cd, ct, fd, ft, rid, shown_pins)
                shown_cores.append((c["thread"], c["line"]))
            if inner:
                y += 16
                pg.t(x0 + 2, y, "on the machine: from the knife sensors' terminal strip X8 to the sensors "
                                "(leg B4-K and its branches)", 10, "i", region=rid)
                for c in sorted(inner, key=lambda c: (nat(c["from_terminal"] if c["from_device"] == "X8" else c["to_terminal"]),
                                                      int(c["line"]))):
                    y += 14
                    if c["from_device"] == "X8":
                        cd, ct, fd, ft = c["from_device"], c["from_terminal"], c["to_device"], c["to_terminal"]
                    else:
                        cd, ct, fd, ft = c["to_device"], c["to_terminal"], c["from_device"], c["from_terminal"]
                    core_row(pg, x0, y, c, cd, ct, fd, ft, rid, shown_pins)
                    shown_cores.append((c["thread"], c["line"]))
            y += 8
        if x0 == 20:
            # connector pins that stay inside the cabinet
            rows = OrderedDict()
            for r in WIR:
                for a, bb in (("from", "to"), ("to", "from")):
                    cdv, ctm = r[a + "_device"], r[a + "_terminal"]
                    odv, otm = r[bb + "_device"], r[bb + "_terminal"]
                    if cdv in CONNS and (cdv, ctm) not in core_pins and odv and odv not in CONNS and place_of(odv) == "cabinet":
                        rows.setdefault((cdv, ctm, odv, otm), []).append(r)
            y += 18
            pg.t(x0 + 2, y, "Inside the cabinet: connector pins that no cable leaves through", 11.5, "b", region=rid)
            y += 13
            pg.t(x0 + 2, y, "cabinet wiring of the connectors service socket XC7, inverter speed setpoint XC50 and "
                            "the encoder connector's shell", 9.5, "fn", region=rid)
            y += 2
            for (cdv, ctm, odv, otm), rs in sorted(rows.items(), key=lambda kv: (kv[0][0], nat(kv[0][1]))):
                y += 14
                rs = sorted(rs, key=lambda r: THREAD_RANK[r["thread"]])
                cls = mark(rs[0]["evidence"])
                pg.t(x0 + 2, y, rs[0]["wire"], 9, "sh", region=rid)
                pg.t(x0 + 178, y, f"{odv} {otm}", 9.5, "fn", anchor="end", region=rid)
                pg.line(x0 + 181, y - 3.5, x0 + 194, y - 3.5, "il")
                pg.t(x0 + 197, y, f"{cdv} {ctm}", 10.5, "b " + cls, region=rid)
                marks = []
                for r in rs:
                    m = f"{r['thread']}: {ev_short(r['evidence'])}"
                    if m not in marks:
                        marks.append(m)
                pg.t(x0 + 272, y, f"{SHORT[cdv]}; " + "; ".join(marks), 9, "fn", region=rid)
                shown_pins.add((cdv, ctm))
                used_internal.add((cdv, ctm))
            y += 8
        pg.regions[rid] = (x0 - 4, 82, x0 + HW, y + 6)
        ybot = max(ybot, y + 6)

    # legend
    ly = ybot + 24
    x = 22
    for cls, word in (("ls", "sure"), ("lq", "[?] unclear"), ("le", "estimated"), ("lw", "W (web)")):
        pg.line(x, ly - 4, x + 34, ly - 4, cls)
        x = pg.t(x + 40, ly, word, 10.5, "fn") + 22
    pg.t(x, ly, "line = the core's evidence mark in merged_cores.csv; red = on the on-site list measure_list.md", 10.5, "fn")
    ly += 18
    pg.t(22, ly, "Left: wire number as printed (grey), the cabinet wiring of a connector pin, the terminal or pin where the core "
                 "leaves the cabinet. Middle: the bundle legs of scheme_3d/bundles.csv it runs through.", 10.5, "fn")
    ly += 16
    pg.t(22, ly, "Right: the far terminal and its device. Routes are estimated (unseen legs ±200 mm); the 3D "
                 "(three-dimensional) routes are in viewer/index.html.", 10.5, "fn")
    nd = [f"{c['thread']} {c['line']}" for c in COR if c["drawn"] != "yes"]
    ly += 16
    pg.t(22, ly, f"Not drawn: {len(nd)} rows of merged_cores.csv ({', '.join(nd)}), the same conductor as a drawn core or a "
                 "superseded line; see netlist/merged_conflicts.csv.", 10.5, "fn")
    # machine wires whose two ends sit at one item of the 3D scheme: no bundle carries them, so no core row
    from collections import Counter
    devp = {}
    for d in rd(NL / "merged_devices.csv"):
        if d["place"] and d["designation"] not in devp:
            devp[d["designation"]] = d["place"]
    in_cor, seen, loc = {(c["thread"], c["line"]) for c in COR}, Counter(), []
    for w in rd(NL / "merged_wires.csv"):
        seen[w["thread"]] += 1
        ln = str(seen[w["thread"]] + 1)
        if devp.get(w["from_device"]) == devp.get(w["to_device"]) == "machine" and (w["thread"], ln) not in in_cor:
            loc.append(f"{w['thread']} {ln} {w['from_device']} {w['from_terminal']} -> {w['to_device']} "
                       f"{w['to_terminal']}")
    ly += 16
    pg.t(22, ly, f"Not drawn either: {len(loc)} machine wires (thread and line of its wires file) whose two ends sit at "
                 "one item of the 3D scheme (a suppressor at its magnet, a bridge inside one device, X8 at S12), so no "
                 "bundle carries them; length [?]:", 10.5, "fn")
    for i in range(0, len(loc), 5):
        ly += 16
        pg.t(34, ly, "; ".join(loc[i:i + 5]), 10.5, "fn")
    print(f"connections.svg: machine wires local at one item, listed: {len(loc)}")
    pg.h = int(ly + 22)

    # self-check
    want = [(c["thread"], c["line"]) for c in drawn]
    from collections import Counter
    cnt = Counter(shown_cores)
    miss = [k for k in want if cnt[k] == 0]
    dup = [k for k in cnt if cnt[k] > 1]
    for k in miss:
        bad.append(f"connections: core {k} not drawn")
    for k in dup:
        bad.append(f"connections: core {k} drawn {cnt[k]} times")
    need = {(r["connector"], r["pin"]) for r in WIR if r["connector"]}
    lost = sorted(need - shown_pins)
    for k in lost:
        bad.append(f"connections: connector pin {k} of merged_wires.csv not shown")
    print(f"connections.svg: {len(shown_cores)} cores drawn of {len(want)} (missing {len(miss)}, twice {len(dup)}); "
          f"connector pins of merged_wires.csv shown {len(need) - len(lost)} of {len(need)}; "
          f"{len(used_internal)} pins inside the cabinet; not drawn by rule {len(nd)}; page {pg.w} x {pg.h}")
    return pg


def core_row(pg, x0, y, c, cd, ct, fd, ft, rid, shown_pins):
    cls = mark(c["evidence"])
    pg.t(x0 + 2, y, c["wire"], 9, "sh", region=rid)
    inner = inner_of(cd, ct) if cd in CONNS else []
    if inner:
        pg.t(x0 + 178, y, " / ".join(inner), 9.5, "fn", anchor="end", region=rid)
        pg.line(x0 + 181, y - 3.5, x0 + 194, y - 3.5, "il")
    pg.t(x0 + 197, y, f"{cd} {ct}", 10.5, "b", region=rid)
    pg.line(x0 + 272, y - 3.5, x0 + 600, y - 3.5, "l" + cls)
    pg.dot(x0 + 272, y - 3.5, 2.4, "dt")
    pg.dot(x0 + 600, y - 3.5, 2.4, "dt")
    rt = c["route"]
    w = Page.ADV * 8.5 * len(rt)
    pg.r(x0 + 436 - w / 2 - 3, y - 10.5, w + 6, 11, "rb")
    pg.t(x0 + 436, y - 1.5, rt, 8.5, "rt", anchor="middle", region=rid)
    pg.t(x0 + 606, y, f"{fd} {ft}", 10.5, "b " + cls, region=rid)
    pg.t(x0 + 684, y, SHORT.get(fd, ""), 8, "fn", region=rid)
    shown_pins.add((cd, ct))
    shown_pins.add((fd, ft))


# ---------------------------------------------------------------- index page
SHEETS = [("power_sheet1.svg", 1, "t1 power"), ("power_sheet2.svg", 2, "t1 power"), ("power_sheet3.svg", 3, "t1 power"),
          ("control_sheet4.svg", 4, "t2 control"), ("control_sheet5.svg", 5, "t2 control"),
          ("control_sheet6.svg", 6, "t2 control"), ("control_sheet7.svg", 7, "t2 control"),
          ("plc_sheet8.svg", 8, "t3 plc_drive")]
COMMANDS = [
    "python -B stage_2_electronics/schemes_2d/integration_merge.py",
    "python -B stage_2_electronics/schemes_2d/integration_draw.py",
    "python -B stage_2_electronics/schemes_2d/integration_lists.py",
    "python -B stage_2_electronics/viewer/build_combined.py",
    "python -B stage_2_electronics/checks/run_checks.py",
]
PROOF_RUNS = [  # longer runs that test the checks and the commands above, each in new copies outside the repository
    "python -B stage_2_electronics/checks/mutation_run.py",
    "python -B stage_2_electronics/checks/copy_run.py",
]
PROOF_TEXT = ("Two longer runs test the checks and the commands themselves. Each copies the repository into new "
              "temporary folders outside it, works only there and deletes nothing. mutation_run.py breaks each check "
              "on purpose, one break at a time, and shows that the check then fails (checks/mutation_report.txt). "
              "copy_run.py runs the five commands above word for word in three copies: the committed files, the "
              "committed files with the local tables, and the files a clone from GitHub holds; it compares what they "
              "write with the repository and names each line of checks.txt that differs, with its reason "
              "(checks/copy_report.txt). Run the copy run after run_checks.py: it compares with the current "
              "checks.txt.")


def sheet_desc(fn, n):
    s = (HERE / fn).read_text(encoding="utf-8")
    cands = re.findall(r"<title>([^<]*)</title>", s) + re.findall(r"<text[^>]*>([^<]*)</text>", s)
    for t in cands:
        t = html.unescape(t)
        m = re.search(rf"sheet\s*{n}\b[^:]*:\s*(.+)", t)
        if m and "568" in t:
            return re.sub(r"\s*\(redrawn[^)]*\)\s*$", "", m.group(1)).strip()
    return ""


def limit_lines():
    """What the set does not know yet: shared by index.html and sources.md (integration_lists.py)."""
    limits = [ln.split(":")[0][5:] for ln in (S / "scheme_3d" / "contact_report.txt").read_text(encoding="utf-8").splitlines()
              if ln.startswith("INFO ")]
    return ["Cable routes are estimated: the bundles follow likely paths along the frame; legs nobody has seen are "
            "±200 mm, the console end of bundle B1 ±100 mm.",
            "The cabinet is built as option B (X −1420 … −1250 mm). Option A would move the cabinet, Q1, Q2, S4, S2 "
            "and the connectors XC1-XC4 by +113 mm in X.",
            "S12, S13 and S14 (knife position sensors on the cam) are placeholders: their place, facing and cam "
            "reading are not known.",
            "FF1 (light curtain) is not fitted on this machine (its certificate entry is a dash); no box is drawn.",
            f"{len(limits)} bodies of the stage-1 model that our items attach to touch no other body ("
            + ", ".join(limits) + "); they stay as built, stage 1 is read-only.",
            "Every [?] and estimated row, and every place where a cabinet photo differs from the 568 print, is on "
            "the on-site measure list."]


def build_index(bad):
    e = lambda s: html.escape(s, quote=True)
    rows = []
    for fn, n, th in SHEETS:
        rows.append((fn, f"sheet {n}", sheet_desc(fn, n), th))
    rows.append(("overview.svg", "sheets 1-8", "overview: the whole machine on one page, each device once, "
                 "cable bundles between cabinet, console and machine", "t5 integration"))
    rows.append(("connections.svg", "sheets 1-8", "connections: every core between cabinet, console and machine, "
                 "by bundle, terminal and connector pin", "t5 integration"))
    for fn, _, d, _ in rows:
        if not d:
            bad.append(f"index: no description for {fn}")
    links = [("../viewer/index.html", "3D (three-dimensional) viewer: stage-1 mechanical model with the electrical "
                                      "layer, offline, with layer switches"),
             ("../measure_list.md", "on-site measure list: every [?] and estimated row, every photo-against-print "
                                    "difference, grouped cabinet, console, machine"),
             ("../sources.md", "sources: every source path with what it holds and its mark; what stays local"),
             ("../checks/checks.txt", "results of the 12 checks"),
             ("../netlist/merged_devices.csv", "merged device list (CSV, comma-separated values), column thread first"),
             ("../netlist/merged_wires.csv", "merged wire list"),
             ("../netlist/merged_cores.csv", "cores between cabinet, console and machine with their bundle route"),
             ("../netlist/merged_conflicts.csv", "where two threads disagree, with both values and a reading"),
             ("../spec/power.md", "spec of thread t1 power (sheets 1-3)"),
             ("../spec/control.md", "spec of thread t2 control (sheets 4-7)"),
             ("../spec/plc_drive.md", "spec of thread t3 plc_drive (sheet 8)"),
             ("../spec/layout_3d.md", "spec of thread t4 layout_3d (3D scheme, placements, bundles, contact check)")]
    h = ['<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1">',
         '<title>Adast Maxima MS 115 PS: electrical schemes (stage 2), index</title>',
         '<style>body{font-family:Segoe UI,Arial,sans-serif;margin:24px 32px;max-width:1150px;color:#111;line-height:1.45}'
         'h1{font-size:22px}h2{font-size:17px;margin-top:26px}table{border-collapse:collapse}'
         'td,th{border:1px solid #bbb;padding:4px 8px;text-align:left;vertical-align:top}th{background:#eee}'
         'pre{background:#f4f4f4;padding:10px;border:1px solid #ddd}code{font-family:Consolas,monospace}</style>',
         '</head>', '<body>',
         '<h1>Adast Maxima MS 115 PS (serial 578.0009, 1998): electrical schemes, stage 2</h1>',
         '<p>The electrical installation of the paper guillotine, redrawn in 2026 from the wiring set 568-70.9001 '
         '[SCHÉMA ZAPOJENÍ] of 1998 and the cabinet photos (not original documents). The 2D (two-dimensional) '
         'sheet pages follow 568-70.9001 sheet by sheet with its column numbers; the overview and the connections page '
         'join them; the 3D (three-dimensional) electrical layer sits on the stage-1 mechanical model in one offline '
         'viewer. Every device, wire and number carries a source path and a mark: sure, [?] (unclear), '
         'estimated ±error or W (web source, weaker). Designations as printed on the sheets; PLC (programmable logic controller) '
         'addresses as IN-x and OUT-x. Text in English with Czech and Russian terms in brackets; sizes in '
         'mm (millimetres).</p>',
         '<h2>Pages: SVG (Scalable Vector Graphics) files that open in a browser</h2>',
         '<table><tr><th>Page</th><th>568 sheet</th><th>What it shows</th><th>Made by thread</th></tr>']
    for fn, sh, d, th in rows:
        h.append(f'<tr><td><a href="{e(fn)}">{e(fn)}</a></td><td>{e(sh)}</td><td>{e(d)}</td><td>{e(th)}</td></tr>')
    h.append('</table>')
    h.append('<h2>Viewer, lists and data</h2><ul>')
    for href, d in links:
        h.append(f'<li><a href="{e(href)}">{e(href.replace("../", ""))}</a>: {e(d)}</li>')
    h.append('</ul>')
    h.append('<h2>Rebuild and check</h2>')
    h.append('<p>Run from the folder that holds stage_1_mechanics and stage_2_electronics (the repository root), in this '
             'order; each command ends with a result line, the last one writes checks/checks.txt. The sheet pages and '
             'the 3D layer are written by the thread scripts named in their specs. Stage 1 is only read, never written.</p>')
    h.append('<pre><code>' + "\n".join(e(c) for c in COMMANDS) + '</code></pre>')
    h.append(f'<p>{e(PROOF_TEXT)}</p>')
    h.append('<pre><code>' + "\n".join(e(c) for c in PROOF_RUNS) + '</code></pre>')
    h.append('<h2>What the set does not know yet</h2><ul>')
    for li in limit_lines():
        h.append(f'<li>{e(li)}</li>')
    h.append('</ul>')
    h.append('<p>Thread t5 (integration) wrote this page with schemes_2d/integration_draw.py.</p>')
    h.append('</body>')
    h.append('</html>')
    txt = "\n".join(h) + "\n"
    if "://" in txt:
        bad.append("index.html holds ://")
    hrefs = re.findall(r'href="([^"]*)"', txt)
    missing = [x for x in hrefs if not (HERE / html.unescape(x)).resolve().is_file()]
    print(f"index.html: {len(hrefs)} links, {len(rows)} pages listed; link targets missing now: {len(missing)}"
          + (f" ({', '.join(missing)}; written by later steps)" if missing else ""))
    later = {"../sources.md", "../measure_list.md", "../checks/checks.txt"}
    for x in missing:
        if x not in later:
            bad.append(f"index: link target missing: {x}")
    return txt


def main():
    bad = []
    ov = build_overview(bad)
    cn = build_connections(bad)
    for name, pg in (("overview.svg", ov), ("connections.svg", cn)):
        b = pg.check()
        print(f"{name}: {len(pg.tb)} text boxes, overlaps or out of box {len(b)}")
        bad += [f"{name}: {x}" for x in b]
    for name, txt in (("overview.svg", ov.svg()), ("connections.svg", cn.svg())):
        with open(HERE / name, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
    ix = build_index(bad)                         # after the two pages exist, so that its link check sees them
    with open(HERE / "index.html", "w", encoding="utf-8", newline="\n") as f:
        f.write(ix)
    for x in bad[:40]:
        print("FAIL", x)
    print("result:", "PASS" if not bad else f"FAIL ({len(bad)})")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
