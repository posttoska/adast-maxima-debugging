#!/usr/bin/env python3
"""Thread t5 (integration), part 1: merge the three thread netlists.

Run from the project folder:  python -B stage_2_electronics/schemes_2d/integration_merge.py
Reads only files under stage_2_electronics (no source photo, no workflow table), so it runs
in any copy of the folder. Writes, under stage_2_electronics/netlist:

  merged_devices.csv   the device rows of power, control and plc_drive stacked 1:1,
                       column "thread" first; nothing dropped, edited or added.
  merged_wires.csv     the wire rows of the three threads stacked the same way.
  merged_conflicts.csv the merge log: (a) every designation found in two or more threads
                       whose kind, type_rating, place or function_en differ, with both
                       values and the rows; (b) every conductor written by two threads
                       (same two ends), with the fields that differ; (c) rows a thread
                       marked as superseded. Nothing is resolved in merged_*.csv; the log
                       gives the reading and the rule the drawings use.
  merged_cores.csv     every merged wire whose two end devices sit at different places
                       (cabinet, console, machine) with the bundle legs of
                       scheme_3d/bundles.csv that carry it (the "cores into bundles" step).

The script ends with "result: PASS" (exit 0) or lists what failed (exit 1).
"""
import csv
import re
import sys
from pathlib import Path

S = Path(__file__).resolve().parents[1]           # stage_2_electronics
NET = S / "netlist"
THREADS = ("power", "control", "plc_drive")       # t1, t2, t3, stacked in this order
DEV_COLS = ["designation", "kind", "function_en", "term_cz_ru", "type_rating", "place",
            "sheet", "column", "evidence", "source_path", "note"]
WIRE_COLS = ["wire", "from_device", "from_terminal", "to_device", "to_terminal", "signal",
             "plc_address", "connector", "pin", "cable", "sheet", "column", "evidence",
             "source_path", "note"]
COMPARED = ("kind", "type_rating", "place", "function_en")      # section 05 join rule
WIRE_COMPARED = ("wire", "signal", "plc_address", "connector", "pin", "evidence")

# Readings of the device fields that differ in wording (class "differs"). Each names
# what the two threads say; none of them is a contradiction in the machine.
READINGS = {
    ("K1", "type_rating"): "same relay; t1 adds the OM (operating manual) type RE6-0011, t2 notes the coil voltage is not read",
    ("PLC", "type_rating"): "same B&R (Bernecker + Rainer) COMPACT PLC; t3 adds the 1 A per output terminal",
    ("PLC", "function_en"): "t2 names the sheet-8 I/O (inputs/outputs), t3 the job (cut cycle, backgauge); same device",
    ("PE", "type_rating"): "t1 counts the PE (protective earth) terminals, t2 quotes the earth symbol; same terminal group",
    ("QF1", "type_rating"): "t1 gives the breaker (568: 10-16 A, photo EP1-M10 6-10 A), t2 only the aux contact 43-44 it uses",
    ("R14", "function_en"): "both are the sheet-7 series resistor of Y14; the R14 printed on board UG50 (sheet 3) is another part, with its own device row UG50/R14 in power_devices.csv",
    ("R10", "function_en"): "t1 'resistor of sheet 5 (across Y10)', t2 adds 'in series with V10'; same resistor",
    ("RC11", "function_en"): "t1 'RC suppressor of sheet 5 (across Y11)', t2 'RC suppressor across Y11'; same part",
    ("V10", "function_en"): "t1 'Zener diode pair of sheet 5 (across Y10)', t2 adds 'in series with R10'; same part",
    ("S10", "function_en"): "t2 adds which hand (left); same button",
    ("S11", "function_en"): "t2 adds which hand (right); same button",
    ("TABLO", "type_rating"): "t2 gives the supply (+24 V from 33X10), t3 the panel type 4E0040.01-590 (estimated); different aspects",
    ("TABLO", "function_en"): "same console operator terminal; t3 adds what the keys and display do",
    ("UZ1", "type_rating"): "t2 names only the relay terminals K12/K14 it uses; t1 and t3 give the same Lenze plate EVF8202-E-V002",
    ("V01", "function_en"): "t1 'diode of sheet 5', t2 'diode across Y01'; same diode",
    ("V14", "function_en"): "same diode across Y14 (sheet 5); the V14 on board UG50 (sheet 3) is another part, with its own device row UG50/V14 in power_devices.csv",
    ("X11", "type_rating"): "t1: 1-4 + earth drawn, photo 6 terminals; t2: 6 terminals (photo); same strip",
    ("X11", "function_en"): "t1 adds what the strip carries (T1 tap links, FF1 feed); same strip",
    ("X5", "type_rating"): "t2 notes terminal numbers not printed; t1 and t3: 17 drawn, photo about 13; same strip",
    ("X8", "function_en"): "t2 adds that S13 and S14 hang on X8 too (sheet 6); same strip",
    ("XC50", "function_en"): "same connector (PLC analog output to UZ1 7, 8); t3 adds the port it sits on (estimated)",
}

# Rows a thread itself marked as superseded by another thread's rows.
SUPERSEDED = {
    ("power", "X5", "", "TABLO", "-"): (
        "plc_drive rows of 45X10 (X10 45 -> TABLO -) and the X5 -> X10 45 link",
        "568 sheet 8 and photo 144309 route the TABLO 0 V through terminal 45X10 (plc_drive.md section 9); "
        "power.md section 10 keeps the row as printed on sheet 2; the drawings and the cores table use the plc_drive rows"),
}

# Precedence for the one-row-per-conductor view used by the drawings (never for the
# merged CSVs): the later thread wins (plc_drive over control over power), because t1
# wrote the sheet 4-8 ends only as copies (power.md section 10) and t3's sheet-8 rows of
# PLC, TABLO, XC4, XC50, XC60, XC70 win by plc_drive.md section 9.
PRECEDENCE = {"power": 0, "control": 1, "plc_drive": 2}

# Devices that have no bundle leg of their own, and the device they sit at (its leg carries them).
AT = {
    "X8": ("S12", "X8 sits with the knife sensors; leg B4-K carries them 'via X8' (X8 place [?])"),
    "C3": ("Y3", "C3 is the suppression capacitor across Y3 (XC3 pins 5-6), at the valve"),
    "XC70": ("TABLO", "XC70 is the console plug of the TABLO link"),
    "V01": ("Y01", "V01 is the diode across magnet Y01 (568 sheet 5), at the coil"),
    "V14": ("Y14", "V14 is the diode across brake Y14 (568 sheet 5), at the coil"),
    "V10": ("Y10", "V10 is the Zener pair across clutch Y10 (568 sheet 5), at the coil"),
    "R10": ("Y10", "R10 is the resistor across clutch Y10 (568 sheet 5), at the coil"),
    "RC11": ("Y11", "RC11 is the RC (resistor-capacitor) suppressor across valve Y11 (568 sheet 5), at the coil"),
}
# Cabinet ends that have no item of their own in placements.csv.
CAB_ALIAS = {
    "XC60": ("PLC", "XC60 is the PLC's port of the TABLO link"),
    "X5": ("X10", "superseded row: its 0 V leaves the cabinet on terminal 45X10"),
}


def read(path):
    """Rows of a CSV file with the file line each row starts on."""
    with open(path, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        header = rd.fieldnames
        rows, prev = [], 1
        for r in rd:
            rows.append((prev + 1, r))
            prev = rd.line_num
    return header, rows


def write(path, cols, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def classify(values):
    """values: list of strings that are not all equal."""
    filled = [v for v in values if v.strip()]
    if len(set(norm(v) for v in filled)) <= 1:
        return "gap"            # some thread left it empty, the others agree
    longest = max(filled, key=len)
    if all(norm(v) in norm(longest) for v in filled):
        return "detail"         # every value is contained in the fullest one
    return "differs"


def main():
    bad = []
    dev_rows, wire_rows = [], []
    for t in THREADS:
        h, rows = read(NET / f"{t}_devices.csv")
        if h != DEV_COLS:
            bad.append(f"{t}_devices.csv header {h}")
        dev_rows += [(t, ln, r) for ln, r in rows]
        h, rows = read(NET / f"{t}_wires.csv")
        if h != WIRE_COLS:
            bad.append(f"{t}_wires.csv header {h}")
        wire_rows += [(t, ln, r) for ln, r in rows]

    write(NET / "merged_devices.csv", ["thread"] + DEV_COLS,
          [dict(r, thread=t) for t, _, r in dev_rows])
    write(NET / "merged_wires.csv", ["thread"] + WIRE_COLS,
          [dict(r, thread=t) for t, _, r in wire_rows])

    # ---- (a) device conflicts -------------------------------------------------------
    by_des = {}
    for t, ln, r in dev_rows:
        by_des.setdefault(r["designation"], []).append((t, ln, r))
    conflicts = []
    shared = sorted(d for d, v in by_des.items() if len({t for t, _, _ in v}) > 1)
    within = sorted(d for d, v in by_des.items() if len({t for t, _, _ in v}) != len(v))
    for d in within:
        bad.append(f"designation {d} twice inside one thread")
    for d in shared:
        v = by_des[d]
        for fld in COMPARED:
            vals = [r[fld] for _, _, r in v]
            if len(set(vals)) == 1:
                continue
            cls = classify(vals)
            reading = READINGS.get((d, fld), "")
            if cls == "gap":
                reading = reading or "one thread leaves it empty; the filled value stands"
            elif cls == "detail":
                reading = reading or "the fuller value contains the shorter one"
            elif not reading:
                bad.append(f"no reading for differing {d}.{fld}")
            conflicts.append({
                "kind": "device field", "key": d, "field": fld, "class": cls,
                "rows": "; ".join(f"{t}_devices.csv line {ln}" for t, ln, _ in v),
                "values": " || ".join(f"{t}: {r[fld]}" for t, _, r in v),
                "reading": reading,
                "rule_for_drawings": ("place: the filled value" if fld == "place"
                                      else "none needed: both values stay in merged_devices.csv"),
            })
    # place conflicts between filled values would make a wire's place ambiguous
    place = {}
    for d, v in by_des.items():
        filled = sorted({r["place"] for _, _, r in v if r["place"]})
        if len(filled) > 1:
            bad.append(f"{d} has two filled places {filled}")
        place[d] = filled[0] if filled else ""

    # ---- (b) one conductor written by two threads ---------------------------------
    def ends(r):
        return frozenset({(r["from_device"], r["from_terminal"]), (r["to_device"], r["to_terminal"])})
    by_ends = {}
    for t, ln, r in wire_rows:
        by_ends.setdefault(ends(r), []).append((t, ln, r))
    n_same = 0
    keep = {}                          # (thread, line) -> True if the row is the one drawn
    for k, v in by_ends.items():
        threads = {t for t, _, _ in v}
        best = max(v, key=lambda x: (PRECEDENCE[x[0]], -x[1]))
        for t, ln, r in v:
            keep[(t, ln)] = (t, ln) == (best[0], best[1]) or len(threads) == 1
        if len(threads) < 2:
            continue
        n_same += 1
        diff = [f for f in WIRE_COMPARED if len({r[f] for _, _, r in v}) > 1]
        a = sorted(k)
        conflicts.append({
            "kind": "same conductor", "key": " - ".join(f"{dv} {tm}".strip() for dv, tm in a),
            "field": ", ".join(diff) if diff else "none",
            "class": "differs" if diff else "equal",
            "rows": "; ".join(f"{t}_wires.csv line {ln}" for t, ln, _ in v),
            "values": " || ".join(f"{t}: " + ", ".join(f"{f}={r[f]}" for f in (diff or ["wire"])) for t, _, r in v),
            "reading": "one conductor drawn on two threads' sheets; both rows stay in merged_wires.csv",
            "rule_for_drawings": f"drawn once, from the {best[0]} row (line {best[1]}): later thread wins",
        })
    # ---- (c) superseded rows --------------------------------------------------------
    n_sup = 0
    for t, ln, r in wire_rows:
        key = (t, r["from_device"], r["from_terminal"], r["to_device"], r["to_terminal"])
        if key in SUPERSEDED:
            n_sup += 1
            by, why = SUPERSEDED[key]
            keep[(t, ln)] = False
            conflicts.append({
                "kind": "superseded row", "key": f"{r['from_device']} {r['from_terminal']} - {r['to_device']} {r['to_terminal']}".replace("  ", " "),
                "field": "route", "class": "differs", "rows": f"{t}_wires.csv line {ln}",
                "values": f"{t}: {r['from_device']} -> {r['to_device']} {r['to_terminal']}; superseded by {by}",
                "reading": why, "rule_for_drawings": "not drawn; the superseding rows are",
            })
    if n_sup != len(SUPERSEDED):
        bad.append(f"superseded rows found {n_sup} of {len(SUPERSEDED)}")
    write(NET / "merged_conflicts.csv",
          ["kind", "key", "field", "class", "rows", "values", "reading", "rule_for_drawings"], conflicts)

    # ---- (d) cores into bundles -----------------------------------------------------
    _, legs = read(S / "scheme_3d" / "bundles.csv")
    legs = [r for _, r in legs]
    by_leg = {r["leg"]: r for r in legs}
    to_item = {r["to_item"]: r for r in legs}
    from_item = {}
    for r in legs:
        from_item.setdefault(r["from_item"], []).append(r)

    def parent(leg):
        m = re.match(r"junction on (\S+)$", leg["from_item"])
        return by_leg[m.group(1)] if m else None

    def joins(leg):
        m = re.match(r"junction on (\S+)$", leg["to_item"])
        return by_leg[m.group(1)] if m else None

    def path_to(leg):
        chain = []
        while leg is not None:
            chain.insert(0, leg)
            leg = parent(leg)
        return chain

    def item_leg(d):
        for pre in ("mark.", "dev.", "conn."):
            if pre + d in to_item:
                return to_item[pre + d]
        return None

    def word_in(word, text):
        return re.search(r"(?<![A-Za-z0-9])" + re.escape(word) + r"(?![A-Za-z0-9])", text) is not None

    def at(d, notes):
        """the device whose bundle leg carries d's cores (d itself, or the device d sits at)"""
        if d in AT:
            notes.append(AT[d][1])
            return AT[d][0]
        return d

    cores = []
    uncarried, local = 0, []
    for t, ln, r in wire_rows:
        a, b = r["from_device"], r["to_device"]
        pa, pb = place.get(a, ""), place.get(b, "")
        if not pa or not pb:
            bad.append(f"{t}_wires.csv line {ln}: end place unknown ({a}:{pa!r}, {b}:{pb!r})")
            continue
        notes, route = [], []
        if pa == pb:
            if pa != "machine":
                continue                                   # inside the cabinet or the console
            da, db = at(a, notes), at(b, notes)
            la, lb = item_leg(da), item_leg(db)
            if la is None or lb is None:
                notes.append(f"no bundle leg ends at {da if la is None else db}")
                uncarried += 1
            elif la is lb:                                 # both ends at one item: no bundle needed
                local.append(f"{t} {ln} {a} {r['from_terminal']}-{b} {r['to_terminal']}"
                             + (" (inside one device)" if a == b else ""))
                continue
            else:                                          # through the leg tree, e.g. B4-K > B4-SQ1
                pa_, pb_ = path_to(la), path_to(lb)
                k = 0
                while k < min(len(pa_), len(pb_)) and pa_[k] is pb_[k]:
                    k += 1
                if k == 0:
                    notes.append("the two legs share no trunk")
                    uncarried += 1
                else:
                    route = pa_[k:][::-1] + [pa_[k - 1]] + pb_[k:]
            far = b
        else:
            cab, far = (a, b) if pa == "cabinet" else (b, a) if pb == "cabinet" else (None, None)
            if cab is None:
                uncarried += 1
                notes.append("no cabinet end")
            else:
                fl = item_leg(at(far, notes))
                route = path_to(fl) if fl else []
                if fl:
                    route += from_item.get(fl["to_item"], [])  # e.g. B5-S28p after mark.S28
                cab_d = cab
                if cab in CAB_ALIAS:
                    cab_d, why = CAB_ALIAS[cab]
                    notes.append(why)
                starts = from_item.get("conn." + cab_d, []) + from_item.get("dev." + cab_d, [])
                if route and route[0] in starts:
                    pass                                       # the trunk leaves from this end
                elif route and any(joins(s) in route for s in starts):
                    s0 = next(s for s in starts if joins(s) in route)   # e.g. B3-XC3 joins B3
                    route = [s0] + route[route.index(joins(s0)):]
                elif route:
                    notes.append(f"cabinet end {cab_d} has no leg on the route")
                    route = []
                if not route:
                    uncarried += 1
        if route:
            words = {w for w in (far, AT.get(far, (far,))[0], r["connector"]) if w}
            if not any(word_in(w, route[-1]["contents"]) for w in words):
                notes.append(f"leg {route[-1]['leg']} contents do not name {far}")
        cores.append({
            "thread": t, "line": ln, "wire": r["wire"],
            "from_device": a, "from_terminal": r["from_terminal"], "from_place": pa,
            "to_device": b, "to_terminal": r["to_terminal"], "to_place": pb,
            "connector": r["connector"], "pin": r["pin"],
            "route": " > ".join(lg["leg"] for lg in route),
            "bundle": route[0]["bundle"] if route else "",
            "drawn": "yes" if keep.get((t, ln), True) else "no (same conductor or superseded, see merged_conflicts.csv)",
            "evidence": r["evidence"], "note": "; ".join(dict.fromkeys(notes)),
        })
    used = {x for c in cores for x in c["route"].split(" > ") if x}
    idle = [lg["leg"] for lg in legs if lg["leg"] not in used]
    write(NET / "merged_cores.csv",
          ["thread", "line", "wire", "from_device", "from_terminal", "from_place", "to_device",
           "to_terminal", "to_place", "connector", "pin", "route", "bundle", "drawn", "evidence", "note"], cores)

    nd = {t: sum(1 for x in dev_rows if x[0] == t) for t in THREADS}
    nw = {t: sum(1 for x in wire_rows if x[0] == t) for t in THREADS}
    cls = {}
    for c in conflicts:
        cls[(c["kind"], c["class"])] = cls.get((c["kind"], c["class"]), 0) + 1
    print("merged_devices.csv rows", len(dev_rows), "=", " + ".join(f"{t} {nd[t]}" for t in THREADS))
    print("merged_wires.csv rows", len(wire_rows), "=", " + ".join(f"{t} {nw[t]}" for t in THREADS))
    print("designations in 2+ threads", len(shared), "; field disagreements",
          sum(v for (k, _), v in cls.items() if k == "device field"),
          "(" + ", ".join(f"{c} {v}" for (k, c), v in sorted(cls.items()) if k == "device field") + ")")
    print("conductors in 2+ threads", n_same, "(" + ", ".join(
        f"{c} {v}" for (k, c), v in sorted(cls.items()) if k == "same conductor") + "); superseded rows", n_sup)
    print("merged_conflicts.csv rows", len(conflicts))
    nx = sum(1 for c in cores if c["from_place"] != c["to_place"])
    print("cores in bundles", len(cores), "(between places", nx, "+ between machine items", len(cores) - nx,
          "); carried by a bundle leg", len(cores) - uncarried, "; uncarried", uncarried,
          "; leg contents not naming the far end", sum(1 for c in cores if "contents do not name" in c["note"]),
          "; machine wires local at one item", len(local))
    print("  local:", "; ".join(local))
    print("bundle legs", len(legs), "; carrying no core", len(idle), ("(" + ", ".join(idle) + ")") if idle else "")
    for b in bad:
        print("bad:", b)
    ok = not bad and uncarried == 0 and not idle
    print("result:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
