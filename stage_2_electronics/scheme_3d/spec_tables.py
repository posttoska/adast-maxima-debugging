"""Write the generated tables of stage_2_electronics/spec/layout_3d.md (thread t4 of episode 2, layout_3d).

Run:  python -B stage_2_electronics/scheme_3d/spec_tables.py
Reads placements.csv, bundles.csv, contact_report.txt and electrical.glb next to this script, and the stage-1 anchor
files through contact_check.reserved_s1(); replaces the text between each pair of marker comments
<!-- BEGIN <name> --> and <!-- END <name> --> in the spec. The prose outside the markers stays as written.
The stage-1 measure-row table (19_stage1_model_measure_rows.csv) is a local file: when it is there, every measure id
cited here must be in it; when it is not, an INFO line says the ids were not checked.
Exit 1 when a marker pair is missing or a count does not add up.
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

import trimesh

import contact_check as cc

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = ROOT / "stage_2_electronics" / "spec" / "layout_3d.md"
MEASURE_REL = "static_dynamic_memory/blocks/generation_002/artifacts/tables/19_stage1_model_measure_rows.csv"

PCOLS = {
    "item": "name of the drawn item in electrical.glb without the prefix \"electrical.\": dev.<designation> (device "
            "box), mark.<designation> (marker on a field device), conn.<designation> (connector), mount.* (plate, "
            "rails, ducts), pass.* (gland, hole or shaft through a wall); empty when nothing is drawn (FF1)",
    "designation": "designation as in set 568-70.9001 or as read on the photos; empty for mounting parts and holes",
    "kind": "what the item is: cabinet device, console device, field device, connector, DIN rail 35 mm, wiring duct, "
            "passage, switch block, switch shaft, lamp, ...",
    "place": "cabinet or console (inside the enclosure: the only two values check 7 bounds), cabinet wall, cabinet "
             "outside face, console wall, console outside, machine",
    "anchor": "stage-1 anchor the row stands on (<kind>.<designation> or body.<designation>); empty for boxes placed "
              "from the photos",
    "device_body": "stage-1 body that is the device itself (field devices, switch handles); empty otherwise",
    "x_mm": "X of the anchor when the row has one, else X of the box centre",
    "y_mm": "Y, as x_mm",
    "z_mm": "Z, as x_mm",
    "box_x_mm": "X of the centre of the item's axis-aligned box",
    "box_y_mm": "Y of that centre",
    "box_z_mm": "Z of that centre",
    "size_x_mm": "size of that box along X",
    "size_y_mm": "size along Y",
    "size_z_mm": "size along Z",
    "fastened_to": "what holds the item: a stage-1 body, housing.cabinet or housing.console (2 mm shells), floor.Z0, "
                   "or one of our mount.* items; a pass names every wall it goes through, separated by \"; \"",
    "photo_row": "cabinet row 1-7 or floor as photographed (inside the cabinet only)",
    "moves_with": "clamp for the items that ride the clamp beam (the viewer's clamp group), else empty",
    "passes": "pass items the row goes through; empty in every placements row of this build (bundles use it)",
    "evidence": "marks drawn only from these four, with their reasons: sure, [?] (unclear), estimated ±<likely error>, "
                "W (web, weaker); a cell may combine them, either naming what each covers (\"estimated ±10 % size, ±60 "
                "height, order sure (photo)\") or starting with [?] (\"[?] estimated ±100\": the item, or a fact named "
                "in brackets or in the note, is unclear, and its place or route is estimated); \"[likely]\" appears "
                "only in notes and means probable, not proven",
    "source_path": "repository-relative source paths, separated by \"; \"",
    "note": "free text: reasons, photo-against-print differences, exceptions",
}
BCOLS = {
    "leg": "leg name: B1-B5 for a trunk, B<n>-<end> for a branch; <end> is the designation the branch ends at, "
           "or a leg letter (list below this table)",
    "bundle": "bundle B1-B5 (routes of section 22)",
    "from_item": "start: an item of placements.csv, or \"junction on <leg>\" (a point on that leg's path)",
    "to_item": "end, as from_item",
    "diameter_mm": "bundle diameter (estimated)",
    "length_mm": "length along path_mm",
    "path_mm": "via points \"x y z; x y z; ...\" in mm; each segment runs along one axis and is one node <leg>.s<i>",
    "clips": "clips as clip.<leg>.c<i>@<carrier body>, separated by \"; \"",
    "contents": "what the bundle carries; terminal first: 14X10 = terminal 14 of strip X10",
    "moves_with": "clamp for the legs that ride the clamp beam, else empty",
    "passes": "our items the leg runs through (ducts, glands, holes, the plate), separated by \"; \"",
    "evidence": "mark with its reason, as in placements.csv",
    "source_path": "repository-relative source paths, separated by \"; \"",
    "note": "free text: deviations from the section-22 route and why",
}
# related stage-1 measure rows (ids of 19_stage1_model_measure_rows.csv) per designation, item or place
MEAS = {
    ("S10", "S11"): "frame.M1 frame.M4 frame.M14 safety_sensors.SS9",
    ("M3",): "frame.M15 safety_sensors.SS7 assembly.A1",
    ("Y3",): "frame.M15 safety_sensors.SS8 assembly.A1",
    ("Y10",): "knife.M5",
    ("M1",): "knife.M8",
    ("S12", "S13", "S14"): "knife.M9 knife.M15 safety_sensors.SS2 assembly.A4",
    ("Y01", "SQ1", "SQ2"): "knife.M10 knife.M15 safety_sensors.SS3",
    ("S5",): "knife.M11 safety_sensors.SS4 safety_sensors.SS6 housing.M6",
    ("S19",): "knife.M11 safety_sensors.SS5 safety_sensors.SS6",
    ("S28", "S30"): "clamp.M1 clamp.M7 safety_sensors.SS6",
    ("Y14",): "clamp.M7 safety_sensors.SS6",
    ("Y11",): "clamp.M4 assembly.A2",
    ("BR40",): "backgauge.G2c backgauge.G6a backgauge.G6b backgauge.G6c assembly.A2",
    ("M2",): "backgauge.G3a backgauge.G3b backgauge.G3c",
    ("S24",): "backgauge.G4a backgauge.G4b backgauge.G4d backgauge.G4e",
    ("S27",): "backgauge.G4c backgauge.G4d backgauge.G4e",
    ("E1", "E2", "E3", "E4"): "housing.M15 housing.M1",
    ("Q1", "Q2", "S4", "S2"): "housing.M12 housing.M10",
    ("XC1", "XC2", "XC3", "XC4"): "housing.M18 housing.M10",
    ("FF1",): "safety_sensors.SS1",
}
MEAS_ITEM = {"dev.door_plate": "housing.M16", "pass.H1": "housing.M1 housing.M2", "pass.H2": "housing.M1",
             "pass.H3a": "housing.M1", "pass.H3b": "housing.M1", "pass.H4": "housing.M2", "pass.H5": "housing.M1",
             "pass.H6": "clamp.M7", "pass.H8": "housing.M6 knife.M5",
             "pass.H9": "knife.M9 knife.M15 safety_sensors.SS2", "pass.H10": "knife.M10 knife.M15 safety_sensors.SS3",
             "pass.H11": "knife.M10 knife.M15 safety_sensors.SS3"}
MEAS_PLACE = {"cabinet": "housing.M9 housing.M10 housing.M11 assembly.A3",
              "cabinet wall": "housing.M9 housing.M10 assembly.A3",
              "cabinet outside face": "housing.M18 housing.M10", "console": "housing.M2 housing.M3",
              "console wall": "housing.M2 housing.M3", "console outside": "housing.M1 housing.M2"}
MEAS_BUNDLE = {"B1": "housing.M1 housing.M2", "B3": "frame.M19"}
OPTION_A_PLACES = ("cabinet", "cabinet outside face", "cabinet wall")
CAB_FACE_X = -1250.0                                  # machine-side face of the cabinet (option B, stage 1)


def rows(name):
    with open(HERE / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def table(head, body):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(cell(c) for c in r) + " |" for r in body]
    return "\n".join(out)


def num(s):
    return f"{float(s):g}"


P, B = rows("placements.csv"), rows("bundles.csv")
REPORT = (HERE / "contact_report.txt").read_text(encoding="utf-8").splitlines()
PH = list(next(csv.reader(open(HERE / "placements.csv", encoding="utf-8", newline=""))))
BH = list(next(csv.reader(open(HERE / "bundles.csv", encoding="utf-8", newline=""))))
assert PH == list(PCOLS), f"placements.csv header differs from PCOLS: {PH}"
assert BH == list(BCOLS), f"bundles.csv header differs from BCOLS: {BH}"
BY_ITEM = {r["item"]: r for r in P if r["item"]}
sc = trimesh.load(HERE / "electrical.glb", force="scene")
NODES = sorted(sc.graph.nodes_geometry)
blocks = {}

# ---- counts -------------------------------------------------------------------------------------------------------
cls = Counter(n.split(".")[1] for n in NODES)
fails = [l for l in REPORT if l.startswith("FAIL")]
ends = [(l, float(re.search(r"([\d.]+) mm$", l).group(1))) for l in REPORT if l.startswith("PASS END ")]
spans = {m.group(1): float(m.group(2)) for l in REPORT
         for m in [re.match(r"PASS leg (\S+) longest free span ([\d.]+) mm", l)] if m}
slack = [l for l in REPORT if " SLACK " in l]
lmax = max(spans, key=spans.get)
emax = max(ends, key=lambda t: t[1])
assert len(P) == len(BY_ITEM) + sum(1 for r in P if not r["item"])
assert cls["clip"] == sum(len([c for c in r["clips"].split("; ") if c]) for r in B), "clip nodes != clips column"
assert cls["bundle"] == sum(len(r["path_mm"].split("; ")) - 1 for r in B), "segment nodes != path segments"
assert len(NODES) == len(BY_ITEM) + cls["clip"] + cls["bundle"], "nodes != items + clips + segments"
blocks["COUNTS"] = "\n".join([
    f"- electrical.glb: {len(NODES)} nodes = {len(BY_ITEM)} items + {cls['clip']} clips + {cls['bundle']} bundle "
    f"segments; items by class: " + ", ".join(f"{k} {cls[k]}" for k in ("dev", "mark", "conn", "mount", "pass")) + ".",
    f"- placements.csv: {len(P)} rows ({len(BY_ITEM)} with a drawn item; FF1 without); by place: "
    + ", ".join(f"{k} {v}" for k, v in sorted(Counter(r['place'] for r in P).items(), key=lambda t: -t[1])) + ".",
    f"- bundles.csv: {len(B)} legs in bundles " + ", ".join(sorted({r['bundle'] for r in B})) + "; "
    f"total length {sum(float(r['length_mm']) for r in B):.0f} mm.",
    f"- contact_report.txt: FAIL {len(fails)}; {sum(1 for l in REPORT if l.startswith('PASS '))} PASS lines, "
    f"{sum(1 for l in REPORT if l.startswith('PASS-THROUGH'))} PASS-THROUGH lines, "
    f"{sum(1 for l in REPORT if l.startswith('INFO'))} INFO lines; {len(ends)} END lines, largest end gap "
    f"{emax[1]:g} mm; longest free span {spans[lmax]:g} mm (leg {lmax}) of the 300 mm allowed; "
    f"{sum(1 for l in REPORT if ' MARKER ' in l)} MARKER lines.",
    f"- SLACK: {slack[0][len('PASS SLACK '):] if slack else 'no line'}.",
])

# ---- columns ------------------------------------------------------------------------------------------------------
blocks["COLUMNS"] = "\n".join([
    "placements.csv header (exactly):", "", "```", ",".join(PH), "```", "",
    table(["column", "meaning"], [(f"`{k}`", v) for k, v in PCOLS.items()]), "",
    "bundles.csv header (exactly):", "", "```", ",".join(BH), "```", "",
    table(["column", "meaning"], [(f"`{k}`", v) for k, v in BCOLS.items()]), "",
    "Leg letters, used in B<n>-<end> where <end> is not a designation (K, R and T here are not the designation "
    "letters listed at the top of this text):", "",
    "- `PLC`: the PLC socket (B1-PLC, from the PLC down into duct D23).",
    "- `T`: TABLO, the B&R terminal in the console (B1-T).",
    "- `F`: front table (B2-F to S10, then B2-S11).",
    "- `R`: rear table (B2-R to S27, then B2-S24); drive corner on the right (B4-R to S5, then B4-Y10 and B4-S19).",
    "- `K`: knife-lock area: sensors S12-S14, SQ1 and SQ2, wired through terminal strip X8, and magnet Y01 (B4-K to "
    "S12, then B4-S13, B4-S14, B4-SQ1 with B4-SQ2, and B4-Y01).",
    "- `s`, `r`, `p` after S28: the S28 lead's slack loop (B5-S28s), its part that rides the clamp (B5-S28r) and its "
    "pocket lead (B5-S28p).",
])

# ---- check-6 reading: one row per MARKER line -------------------------------------------------------------------
mrx = re.compile(r"^(PASS|FAIL) MARKER (\S+) anchor (\S+) ([\d.]+) mm from (\S+); (\S+) ([\d.]+) mm from it, "
                 r"([\d.]+) mm from (\S+); anchor to item ([\d.]+) mm(?: \((.*)\))?$")
mk = []
for l in REPORT:
    if " MARKER " not in l:
        continue
    m = mrx.match(l)
    assert m, f"MARKER line not understood: {l}"
    exc = m.group(11) or ""
    exc = exc[exc.find("exception:") + len("exception:"):].strip() if "exception:" in exc else ""
    mk.append((m.group(1), m.group(2), m.group(3), m.group(5), m.group(4), m.group(6), m.group(7), m.group(9),
               m.group(8), m.group(10), exc))
blocks["MARKER"] = table(["result", "designation", "anchor", "device body", "anchor to body (mm)", "item",
                          "item to body (mm)", "carrier", "item to carrier (mm)", "anchor to item (mm, info)",
                          "exception"], mk)

# ---- clamp group --------------------------------------------------------------------------------------------------
mv_items = [r["item"] for r in P if r["moves_with"] == "clamp"]
mv_legs = [r["leg"] for r in B if r["moves_with"] == "clamp"]
grp = [n for n in NODES if n[len("electrical."):] in mv_items
       or any(n.startswith(f"electrical.{c}.{g}.") for g in mv_legs for c in ("bundle", "clip"))]
blocks["CLAMP_GROUP"] = (f"{len(grp)} nodes (items {', '.join(mv_items)}; legs {', '.join(mv_legs)}):\n\n"
                         + "\n".join(f"- `{n}`" for n in grp))

# ---- passes -------------------------------------------------------------------------------------------------------
blocks["PASSES"] = table(["item", "designation", "goes through (fastened_to)", "size x, y, z (mm)", "evidence", "note"],
                         [(r["item"], r["designation"], r["fastened_to"],
                           f"{num(r['size_x_mm'])} x {num(r['size_y_mm'])} x {num(r['size_z_mm'])}",
                           r["evidence"], r["note"]) for r in P if r["item"].startswith("pass.")])

# ---- bundles ------------------------------------------------------------------------------------------------------
endd = {}
for l, d in ends:
    m = re.match(r"PASS END (\S+) (from|to) (.+) ([\d.]+) mm$", l)
    endd[(m.group(1), m.group(2))] = d
blocks["BUNDLES"] = table(["leg", "from", "to", "diameter (mm)", "length (mm)", "clips", "longest free span (mm)",
                           "end gaps from / to (mm)", "moves with", "evidence"],
                          [(r["leg"], r["from_item"], r["to_item"], num(r["diameter_mm"]), num(r["length_mm"]),
                            len([c for c in r["clips"].split("; ") if c]), f"{spans.get(r['leg'], float('nan')):g}",
                            f"{endd.get((r['leg'], 'from'), '-')} / {endd.get((r['leg'], 'to'), '-')}",
                            r["moves_with"], r["evidence"]) for r in B])

# ---- reserved spaces ----------------------------------------------------------------------------------------------
res = cc.reserved_s1()
blocks["RESERVED"] = (f"{len(res)} boxes:\n\n" + table(
    ["stage-1 anchor", "min x, y, z (mm)", "max x, y, z (mm)"],
    [(k, ", ".join(f"{v:g}" for v in lo), ", ".join(f"{v:g}" for v in hi)) for k, (_, lo, hi) in sorted(res.items())]))

# ---- option A -----------------------------------------------------------------------------------------------------
oa = [r["item"] or r["designation"] for r in P if r["place"] in OPTION_A_PLACES]
legs_a = []
for r in B:
    pts = [tuple(map(float, q.split())) for q in r["path_mm"].split("; ")]
    k = sum(1 for p in pts if p[0] <= CAB_FACE_X + 1.0)
    ends = [e for e in (r["from_item"], r["to_item"]) if e in oa]
    if k or ends:
        legs_a.append(f"{r['leg']} ({k} of {len(pts)} points" + (f"; end at {', '.join(ends)}" if ends else "") + ")")
blocks["OPTION_A"] = (f"- {len(oa)} placements rows (place {', '.join(OPTION_A_PLACES)}): {', '.join(oa)}.\n"
                      f"- {len(legs_a)} bundle legs with points on or inside the cabinet (X <= {CAB_FACE_X:g} + 1 mm) "
                      f"or an end at one of those rows: those points and ends move with the cabinet, the rest of "
                      f"each route stretches: {', '.join(legs_a)}.")

# ---- photo against print ------------------------------------------------------------------------------------------
pp = re.compile(r"\(check\)|: check|OM |plate reads|LED bar seen|568 [0-9]")
blocks["PHOTO_PRINT"] = table(["item", "evidence", "note (photo against print)"],
                              [(r["item"], r["evidence"], r["note"]) for r in P if pp.search(r["note"])])

# ---- on-site list -------------------------------------------------------------------------------------------------
def meas(r, leg=False):
    if leg:
        t = BY_ITEM.get(r["to_item"])
        ids = (meas(t) if t else "").split() + MEAS_BUNDLE.get(r["bundle"], "").split()
        return " ".join(dict.fromkeys(ids))
    for k, v in MEAS.items():
        if r["designation"] in k:
            return v
    return MEAS_ITEM.get(r["item"]) or MEAS_PLACE.get(r["place"], "")


def what(r, leg=False):
    it = "" if leg else r["item"]
    w = ("route along path_mm, clip places, length and diameter; which cores it carries" if leg else
         "device place x, y, z on the machine; where its cable enters" if it.startswith("mark.") else
         "is the hole or shaft there; place and diameter" if it.startswith("pass.") else
         "height, length and depth of the plate, rail or duct" if it.startswith("mount.") else
         "label, height Z and place Y on the face" if it.startswith("conn.") else
         "row, order, size (width x height x depth), plate text" if r["place"] == "cabinet" else
         "fitted? place and size" if r["place"].startswith("console") else
         "fitted? place on the machine" if r["kind"].startswith("lamp") else
         "place and size")
    if "[?]" in r["note"] or "check" in r["note"] or "[?]" in r["evidence"]:
        w += "; note: " + r["note"]
    return w


onsite = [(r["item"] or "(no item)", r["designation"], r["place"], r["evidence"], what(r), meas(r))
          for r in P if r["evidence"].strip() != "sure"]
onsite += [(r["leg"], r["bundle"], f"{r['from_item']} -> {r['to_item']}", r["evidence"], what(r, True), meas(r, True))
           for r in B if r["evidence"].strip() != "sure"]
not_listed = [r["item"] or r["designation"] for r in P if r["evidence"].strip() == "sure"]
assert len(onsite) + len(not_listed) == len(P) + len(B)
ids_used = sorted({i for row in onsite for i in row[5].split()})
mfile = ROOT / MEASURE_REL
if mfile.exists():
    known = {r["id"] for r in csv.DictReader(open(mfile, encoding="utf-8", newline=""))}
    bad = [i for i in ids_used if i not in known]
    assert not bad, f"measure ids not in the stage-1 measure table: {bad}"
else:
    print(f"INFO {MEASURE_REL} not in this copy: measure ids not checked")
blocks["ONSITE"] = (f"{len(onsite)} rows: every placements and bundles row whose evidence is not plain \"sure\" "
                    f"(not listed: {', '.join(not_listed)}).\n\n"
                    + table(["#", "row", "designation or bundle", "place or ends", "evidence", "what to check on site",
                             "related stage-1 measure rows"], [(i + 1, *r) for i, r in enumerate(onsite)]))

# ---- write --------------------------------------------------------------------------------------------------------
text = SPEC.read_text(encoding="utf-8")
for name, body in blocks.items():
    a, b = f"<!-- BEGIN {name} -->", f"<!-- END {name} -->"
    if text.count(a) != 1 or text.count(b) != 1:
        sys.exit(f"marker pair {name} missing or doubled in {SPEC.name}")
    i, j = text.index(a) + len(a), text.index(b)
    text = text[:i] + "\n" + body + "\n" + text[j:]
with open(SPEC, "w", encoding="utf-8", newline="\n") as f:
    f.write(text)
print(f"{SPEC.name}: {len(blocks)} blocks written; on-site rows {len(onsite)}; MARKER rows {len(mk)}; "
      f"clamp group {len(grp)} nodes; reserved {len(res)}; option A rows {len(oa)}, legs {len(legs_a)}")
