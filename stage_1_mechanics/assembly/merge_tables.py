"""Merged measure list and source table of the assembled model (thread 7, section 05 phase C) and check 11.

write_all(root, bodies, anchors, meta, report, bounds=None)
    root     the stage_1_mechanics folder or a copy of it (reads <root>/spec/<part>.md, writes <root>/measure_list.md
             and <root>/sources.md)
    bodies   the body names <part>.<body> of out/assembly.glb
    anchors  {part: {anchor name: anchor}}, meta {part: meta} as read from out/<part>_anchors.json
    report   assembly.Report: gets the check 11 lines
    bounds   {body: (lo, hi)} of the assembled bodies in mm (the model column of sources.md); optional

Every row is read from the specs' own tables at run time; nothing about a part is typed here.  The assembly adds
its own measure rows A1.. (photo requests of order 1 q4, DECISIONS 3 and 4, clamp open item 1) and one row for
each estimated body that no measure row of its spec covers; those rows say so.  Source keys are resolved to files
under preparatory_data_analysis/ and the block's artifacts/, and each file is checked to exist.

Run alone (no meshes, model column empty):  python merge_tables.py [--root <copy of stage_1_mechanics>]
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECTION10_REL = "static_dynamic_memory/blocks/generation_001/sections/10_safety_devices_and_sensors.md"
PROJECT_ABS = Path("C:/Users/ptsk/Documents/adast-maxima-debugging")   # last resort: the project folder on this PC


def is_project(p):
    """the project folder holds the sources (preparatory_data_analysis/) and the block's section 10"""
    return (p / "preparatory_data_analysis").is_dir() and (p / SECTION10_REL).is_file()


def find_project(project=None, root=None):
    """(project folder or None, how it was found): the one lookup of assembly.py, merge_tables.py and
    mutation_test.py: --project, else walking up from this script, from --root and from the working folder, else
    PROJECT_ABS.  A plain copy of stage_1_mechanics anywhere on this PC finds the project's sources this way."""
    if project:
        p = Path(project).resolve()
        return (p, "--project") if is_project(p) else (None, f"--project {p} holds no preparatory_data_analysis/ "
                                                             f"and {SECTION10_REL}")
    for how, base in (("up from the script", HERE), ("up from --root", root), ("up from the working folder", Path.cwd())):
        if base is not None:
            base = Path(base).resolve()
            for p in (base, *base.parents):
                if is_project(p):
                    return p, f"found walking {how}"
    if is_project(PROJECT_ABS):
        return PROJECT_ABS, "the fixed project path (not found walking up)"
    return None, "not found walking up from the script, --root or the working folder, nor at the fixed project path"


def set_project(p):
    """point the source lookups (short(), the key resolution) at project folder p"""
    global PROJECT, PREP, ART, EPISODE
    PROJECT = Path(p)
    PREP = PROJECT / "preparatory_data_analysis"
    ART = PROJECT / "static_dynamic_memory" / "blocks" / "generation_001" / "artifacts"
    EPISODE = PROJECT / "static_dynamic_memory" / "episodes" / "episode_001"


set_project(find_project()[0] or HERE.parents[1])     # assembly.main() sets it again with its --root and --project
PARTS = ("frame", "knife", "clamp", "backgauge", "housing", "safety_sensors")
PART_ALIAS = {"safety": "safety_sensors", "safety_sensors": "safety_sensors", "frame": "frame", "knife": "knife",
              "clamp": "clamp", "backgauge": "backgauge", "housing": "housing"}
MID = r"(?:M\d+|G\d+[a-z]?|SS\d+)"
CLASS_LETTERS = "DTPEW"
PREFIXES = {"OM/": "preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/",
            "OM ": "preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/",
            "ART/": "static_dynamic_memory/blocks/generation_001/artifacts/",
            "R/": "stage_1_mechanics/"}
SHORT = [("preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/", "OM/"),
         ("preparatory_data_analysis/maxima_documents/", "DOC/"),
         ("preparatory_data_analysis/maxima_photos/", "PH/"),
         ("static_dynamic_memory/blocks/generation_001/artifacts/", "ART/"),
         ("preparatory_data_analysis/", "PREP/")]
# the measure list's abbreviations, written out once in its header (user's global rule; critic g11 F-g11-1); each key's
# meaning is taken from the spec key tables and the files sources.md resolves them to, not guessed
ABBREV_MEASURE = (
    "Abbreviations: GLB (binary GL Transmission Format, GL = Graphics Library: the model files `out/<part>.glb`), "
    "JSON (JavaScript Object Notation: the anchors files `out/<part>_anchors.json`), Fig. (figure), p. (page), "
    "vs (versus), incl. (including), Ø (diameter), kW (kilowatts), MPa (megapascals), /min (per minute), LED (light-emitting diode), DECISION n (a "
    "ruling of the meta orchestrator of the workflow); S12, Y01, OA1, M1 and the like in the text are device "
    "designations of the electrical legend (wiring set 568-70.9001) and of the hydraulic parts list, not "
    "abbreviations. The rows quote each spec's own source keys, for example OM "
    "(operating manual of this variant), P7 or p7 (OM page 7), F101 (OM Fig. 10.1), PLAN (OM Fig. 4.2.2, the "
    "foundation plan), PL (packing list 578.0009), CERT (certificate of this machine), HC (hydraulic circuit "
    "diagram), HS2 (that circuit drawn in state 2, pre-clamp), HL (hydraulic parts list), OLD and OLD-I (the "
    "Russian manual of the older relay variant МС 115 Стандарт/Максиматик, and its Fig. I), FR (the frame's "
    "interface: `out/frame_anchors.json` and `spec/frame.md`), PH-stand or PH150610 (one machine photo), W568 "
    "(wiring set 568-70.9001 of this machine), W554 and W552 (wiring sets of other types). A key means what its own "
    "spec says (W1 is the knife price list on the web in `spec/knife.md`, and sheet 1 of wiring set 568-70.9001 in "
    "`spec/backgauge.md`); every spec's keys with the files they resolve to are listed in `sources.md`, section "
    "'Source keys of each spec and the files they resolve to'.")
ABBREV_SOURCES = (ABBREV_MEASURE + " Also in the source table: CZ (Czech), TDC (top dead centre), DC (direct current), "
                  "В (volt, in Russian text), daN (decanewtons), dm³ (cubic decimetres), cm² (square centimetres), "
                  "mm/s (millimetres per second), px (pixels of a photo or page image).")


# ---------------------------------------------------------------------------------------------- markdown helpers
def md_tables(text):
    """all markdown tables: (header line number 1-based, header cells, rows, heading above)"""
    lines, out, i, head = text.splitlines(), [], 0, ""
    while i < len(lines):
        if lines[i].startswith("#"):
            head = lines[i].lstrip("#").strip()
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            hdr = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            out.append((i + 1, hdr, rows, head))
            i = j
        else:
            i += 1
    return out


def col(hdr, *words, exclude=()):
    """index of the first header cell containing any of the words (lower case)"""
    for i, h in enumerate(hdr):
        hl = h.lower()
        if any(w in hl for w in words) and not any(x in hl for x in exclude):
            return i
    return None


def cell(row, i):
    return row[i] if i is not None and i < len(row) else ""


def esc(s):
    return str(s).replace("|", "/").replace("\n", " ").strip()


def short(path):
    s = str(path).replace("\\", "/")
    p = str(PROJECT).replace("\\", "/") + "/"
    r = getattr(short, "root", None)           # the run's root (R or a copy of it): printed as stage_1_mechanics/ (F12)
    if r and s.startswith(r):
        s = "stage_1_mechanics/" + s[len(r):]
    elif s.startswith(p):
        s = s[len(p):]
    for a, b in SHORT:
        if s.startswith(a):
            return b + s[len(a):]
    return s


def section(text, title):
    """text of the '## title...' section"""
    m = re.search(r"^##\s+" + re.escape(title) + r".*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------------------------- file index
class Files:
    """stamps, 6-digit times and file names under preparatory_data_analysis/ and the block's artifacts/"""

    def __init__(self, root):
        self.root = root
        self.stamp, self.time, self.name = {}, {}, {}
        for base in (PREP, ART):
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if not p.is_file():
                    continue
                self.name.setdefault(p.stem.lower(), []).append(p)
                m = re.fullmatch(r"(\d{8})_(\d{6})", p.stem)
                if m and base == PREP:
                    self.stamp.setdefault(p.stem, []).append(p)
                    self.time.setdefault(m.group(2), set()).add(p.stem)

    def by_stamp(self, s):
        c = sorted(self.stamp.get(s, []), key=lambda p: (0 if re.search(r"maxima_(documents|photos)", str(p)) else 1,
                                                         len(p.parts)))
        return c[:1]

    def by_path(self, s):
        s = s.strip().rstrip(".,;:)")
        for a, b in PREFIXES.items():
            if s.startswith(a):
                s = b + s[len(a):]
        cands = [PROJECT / s, PREP / s, PREP / "maxima_documents" / s, ART / s, ART / "crops" / s, EPISODE / s,
                 self.root / s, self.root / s.replace("stage_1_mechanics/", "", 1), self.root / "out" / s]
        for c in cands:
            if c.is_file():
                return [c]
        return []

    def resolve(self, text):
        """files named in a piece of text: full stamps, paths, crop names, unique 6-digit photo/page times"""
        found, t = [], text.replace("\\", "/")
        for m in re.finditer(r"(?:[\w.<>-]+/)+[\w.<>-]+\.(?:jpe?g|png|pdf|html?|md|json|txt|glb)|"
                             r"\b[\w-]+\.(?:pdf|html?)\b", t):
            if "<" in m.group(0):
                continue
            found += self.by_path(m.group(0))
        for s in re.findall(r"(?<!\d)(\d{8}_\d{6})(?!\d)", t):
            found += self.by_stamp(s)
        for s in re.findall(r"(?<![\d_.,])(\d{6})(?![\d_.,]\d)", t):
            st = self.time.get(s, set())
            if len(st) == 1:
                found += self.by_stamp(next(iter(st)))
        for s in re.findall(r"\b(p\d{1,3}_[A-Za-z0-9][\w.-]{3,})", t):
            s = s.rstrip(".")
            c = self.name.get(s.lower()) or [p for k, v in self.name.items() if k.startswith(s.lower()) for p in v]
            found += sorted(c, key=lambda p: len(str(p)))[:1]
        out = []
        for p in found:
            if p not in out:
                out.append(p)
        return out


def primary(p):
    s = str(p).replace("\\", "/")
    return "/preparatory_data_analysis/" in s or "/artifacts/" in s


# ---------------------------------------------------------------------------------------------- source keys
def key_map(part, text, files):
    """{key: [files]} from the part's key table, or from the backgauge's inline 'key = value' paragraph"""
    km = {}
    for ln, hdr, rows, head in md_tables(text):
        if hdr and hdr[0].lower() == "key":
            fi = col(hdr, "file") or 1
            for r in rows:
                keys = [k.strip() for k in re.split(r",|\s/\s", r[0]) if k.strip()]
                val = cell(r, fi)
                if len(keys) > 1:
                    segs = [s.strip() for s in val.split(",")]
                    if len(segs) == len(keys):
                        for k, s in zip(keys, segs):
                            km[k] = files.resolve(s)
                        continue
                for k in keys:
                    km[k] = files.resolve(val)
            return km
    sec = section(text, "Source keys")
    ms = list(re.finditer(r"(^|; |\. |\n)([A-Za-z][\w]*(?: / [A-Za-z][\w]*)*) = ", sec))
    for i, m in enumerate(ms):
        val = sec[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(sec)]
        keys = [k.strip() for k in m.group(2).split("/")]
        if len(keys) > 1:
            segs = [s for s in re.split(r"\s/\s", val)]
            if len(segs) == len(keys):
                for k, s in zip(keys, segs):
                    km[k] = files.resolve(s)
                continue
        for k in keys:
            km[k] = files.resolve(val) if k != "OM" else []
    return km


def keys_in(cell_text, km):
    used = []
    for k in sorted(km, key=len, reverse=True):
        if re.search(r"(?<![\w-])" + re.escape(k) + r"(?![\w-])", cell_text):
            used.append(k)
    return used


# ---------------------------------------------------------------------------------------------- measure rows
def measure_tables(part, text):
    """[(ln, hdr, rows)] of measure rows (tables with an error column under a heading that names 'measure')"""
    out = []
    for ln, hdr, rows, head in md_tables(text):
        if "measure" in head.lower() and col(hdr, "error") is not None:
            out.append((ln, hdr, rows))
    return out


def gap_map(text):
    """backgauge: the 'gap | components | named on' table -> {gap: (components, named on, line)}"""
    for ln, hdr, rows, head in md_tables(text):
        if hdr and hdr[0].lower() == "gap":
            return ln, {r[0]: ([c.strip() for c in cell(r, 1).split(",") if c.strip() not in ("", "-")], cell(r, 2),
                               ln + 2 + k) for k, r in enumerate(rows)}
    return None, {}


def read_measures(root):
    rows, groups, counts = [], [], {}
    for p in PARTS:
        text = (root / "spec" / f"{p}.md").read_text(encoding="utf-8")
        n = 0
        for ln, hdr, rws in measure_tables(p, text):
            ii, iw = 0, col(hdr, "what")
            ie, iwh = col(hdr, "error"), col(hdr, "where")
            ic = col(hdr, "current", "model now")
            prev_where = ""
            for k, r in enumerate(rws):
                where = cell(r, iwh)
                if where.lower().startswith("same") and prev_where:
                    where = f"{where} (as above: {prev_where})"
                else:
                    prev_where = where
                rows.append({"id": f"{p}.{cell(r, ii)}", "part": p, "rid": cell(r, ii), "what": cell(r, iw),
                             "where": where, "current": cell(r, ic), "error": cell(r, ie),
                             "line": f"spec/{p}.md:{ln + 2 + k}", "origin": "spec"})
                n += 1
        g_ln, gm = gap_map(text)
        for g, (comps, named, line) in gm.items():
            groups.append({"id": f"{p}.{g}", "part": p, "rid": g, "components": comps, "named": named,
                           "line": f"spec/{p}.md:{line}"})
        counts[p] = (n, len(gm))
    return rows, groups, counts


PQ = r"\b(frame|knife|clamp|backgauge|housing|safety_sensors|safety)[ .](" + MID + r")\b"
# Words a spec's measure rows use for a body other than its own name (judgement of actor t7; each alias must be
# found in a 'what' cell of that part at run time, else check 11 reports it)
ALIAS = {"knife.conrod": ["rod"], "knife.gear_box": ["wheel housing", "worm-gear housing"],
         "knife.lock_pin_1": ["pin 1"]}


def cross_refs(text, part, ids, devices=frozenset()):
    """measure references in a text. Part-qualified ('knife M9' -> knife.M9) anywhere; a bare ID only inside
    brackets ('(M18)', '(M9, M10)'), because a bare M1, M2, M3 elsewhere is mostly the motor of that name.
    A bracketed bare ID that names no measure row of its part is a broken reference (a dropped or renumbered row),
    unless it is a device designation of an anchors file ('(M1)' = motor.M1): mutant M11 of mutation_test.py."""
    refs, bad = [], []
    for m in re.finditer(PQ, text):
        q = f"{PART_ALIAS[m.group(1)]}.{m.group(2)}"
        (refs if q in ids else bad).append(q)
    bare = re.sub(PQ, " ", text)
    for grp in re.findall(r"\(([^()]*)\)", bare):
        # '(M4)', '(M9, M10)', '(placeholder; M18)' are references; '(rotor turns with M1)' is the motor
        for m in re.finditer(r"(?:^|[,;])\s*(" + MID + r")\s*(?=[,;]|$)", grp.strip()):
            q = f"{part}.{m.group(1)}"
            if q in ids:
                refs.append(q)
            elif m.group(1) not in devices:
                bad.append(q)
    return list(dict.fromkeys(refs)), list(dict.fromkeys(bad))


def device_ids(anchors):
    """designations of the device anchors that look like a measure ID (motor.M1 -> M1, motor.M2 -> M2)"""
    names = set()
    for k, v in (anchors or {}).items():
        sub = v.keys() if isinstance(v, dict) and k in PARTS else [k]   # flat {name: a} or {part: {name: a}}
        for n in sub:
            tail = str(n).split(".", 1)[-1]
            if re.fullmatch(MID, tail):
                names.add(tail)
    return frozenset(names)


def name_patterns(body, component, unique_base=None):
    """regexes for the ways a measure row's 'what' cell names a body: its id words (plural tolerant, with and
    without the side suffix), its component, its designation tokens (Y10, M1, S5, OA1), its aliases; the item
    number is dropped only when no other item of that name is in the part (flywheel_2 -> flywheel; guide 12 stays)"""
    part, bid = body.split(".", 1)
    phrases = {bid.replace("_", " "), re.sub(r"_(left|right)$", "", bid).replace("_", " "),
               str(component or "").replace("_", " ")}
    if unique_base:
        phrases.add(unique_base.replace("_", " "))
    pats = []
    for ph in phrases:
        toks = ph.lower().split()
        if not toks or len(ph) < 3:
            continue
        pats.append(r"(?<![\w])" + r"[\s-]+".join(re.escape(t) + "s?" for t in toks) + r"(?![\w])")
    for t in bid.split("_"):
        if re.fullmatch(r"[A-Za-z]{1,2}\d{1,3}", t):
            pats.append(r"(?<![\w.])" + re.escape(t.lower()) + r"(?![\w])")
    for a in ALIAS.get(body, []):
        pats.append(r"(?<![\w])" + re.escape(a.lower()) + r"(?![\w])")
    return pats


# ---------------------------------------------------------------------------------------------- component rows
def comp_table(text):
    for ln, hdr, rows, head in md_tables(text):
        h0 = hdr[0].lower() if hdr else ""
        if h0 in ("id", "component") and col(hdr, "class") is not None and \
                any(w in head.lower() for w in ("component", "bodies")):
            return ln, hdr, rows
    return None, [], []


def norm_comp(s):
    s = re.sub(r"\(.*?\)", "", s.lower()).strip()
    return s[:-1] if s.endswith("s") else s


def class_letters(c):
    return sorted(set(re.findall(r"(?<![A-Za-z])([" + CLASS_LETTERS + r"])(?![a-z])", c)), key=CLASS_LETTERS.index)


def read_components(root, bodies, meta, files):
    """{body: [row dict]} plus rows that are not bodies, unmatched bodies"""
    per_body, extra, keys_all = {}, [], {}
    terms_safety = {}
    for p in PARTS:
        text = (root / "spec" / f"{p}.md").read_text(encoding="utf-8")
        km = key_map(p, text, files)
        keys_all[p] = km
        ln, hdr, rows = comp_table(text)
        if p == "safety_sensors":
            for tl, th, trs, thd in md_tables(text):
                if th and th[0].lower() == "designation":
                    it = col(th, "term", "device")
                    terms_safety = {r[0]: cell(r, it) for r in trs}
        i_id = 0
        i_term = col(hdr, "term")
        i_src = max(i for i, h in enumerate(hdr) if h.lower().startswith("source"))
        i_cls, i_err = col(hdr, "class"), col(hdr, "error")
        i_geo = [i for i, h in enumerate(hdr) if re.search(r"solid|size|geometry|bounds|position|host", h.lower())
                 and i not in (i_id, i_term, i_src, i_cls, i_err)]
        pb = {b.split(".", 1)[1]: b for b in bodies if b.startswith(p + ".")}
        mb = meta.get(p, {}).get("bodies", {}) or {}
        comp_of = {}
        for b in pb:
            info = mb.get(f"{p}.{b}", mb.get(b, {})) or {}
            comp_of[b] = info.get("component") if isinstance(info, dict) else None
        table = []
        for k, r in enumerate(rows):
            if len(r) < len(hdr):
                r = r + [""] * (len(hdr) - len(r))
            table.append({"part": p, "row_id": r[i_id], "term": cell(r, i_term), "source": cell(r, i_src),
                          "class": cell(r, i_cls), "error": cell(r, i_err),
                          "geo": " ; ".join(f"{hdr[i]}: {cell(r, i)}" for i in i_geo if cell(r, i)),
                          "line": f"spec/{p}.md:{ln + 2 + k}", "raw": " ".join(r)})
        by_id = {t["row_id"]: t for t in table}
        used = set()
        for b, full in pb.items():
            hit = []
            if b in by_id:
                hit.append(by_id[b])
            elif comp_of.get(b):
                c = comp_of[b]
                hit += [t for t in table if t["row_id"] == c] or \
                       [t for t in table if norm_comp(t["row_id"]) == norm_comp(c)]
            hit += [t for t in table if t["row_id"].startswith(b + " ") and t not in hit]   # frame 'table slot' ...
            for t in hit:
                used.add(t["row_id"])
                if p == "safety_sensors" and not t["term"]:
                    t["term"] = terms_safety.get(b, "")
            per_body[full] = {"rows": hit, "component": comp_of.get(b) or b}
        extra += [t for t in table if t["row_id"] not in used]
    return per_body, extra, keys_all


# ---------------------------------------------------------------------------------------------- the merge
def fmt_xyz(v):
    return ", ".join(f"{float(x):.0f}" for x in v)


def fmt_err(e):
    if isinstance(e, dict):
        return "±(" + ", ".join(f"{k.upper()} {float(v):g}" for k, v in sorted(e.items())) + ")"
    if isinstance(e, (list, tuple)):
        return "±(" + ", ".join(f"{a} {float(v):g}" for a, v in zip("XYZ", e)) + ")"
    return f"±{e}"


def fmt_box(lohi):
    lo, hi = lohi
    return f"X {lo[0]:.0f}..{hi[0]:.0f}, Y {lo[1]:.0f}..{hi[1]:.0f}, Z {lo[2]:.0f}..{hi[2]:.0f}"


def anchor_of(anchors, name):
    for p, an in anchors.items():
        if name in an:
            return p, an[name]
    return None, None


def assembly_rows(anchors, bounds, report):
    """A1..: photo requests (order 1 q4), DECISION 3 and 4, clamp open item 1; numbers from the files and the run"""
    rows = []

    def add(what, where, current, error, src):
        rows.append({"id": f"assembly.A{len(rows) + 1}", "part": "assembly", "rid": f"A{len(rows) + 1}", "what": what,
                     "where": where, "current": current, "error": error, "line": src, "origin": "assembly"})

    def an_txt(names):
        out = []
        for n in names:
            p, a = anchor_of(anchors, n)
            if a:
                out.append(f"{n} ({p}) at {fmt_xyz(a['xyz'])}, {a.get('class', '?')} "
                           f"{fmt_err(a.get('error_mm', a.get('error', '?')))}")
        return "; ".join(out)

    def bx(names):
        if not bounds:
            return "model bounds: run assembly.py"
        return "; ".join(f"{n} {fmt_box(bounds[n])}" for n in names if n in bounds)

    add("Photos of the rear of the machine (straight from behind and from both rear corners, with a tape for scale): "
        "rear table end, rear stand, rear ring foot S3, blower motor M3 and valve Y3",
        "behind the rear table, standing on the floor; then each device close up",
        "; ".join(x for x in (bx(["frame.rear_stand", "frame.foot_rear"]), an_txt(["motor.M3", "valve.Y3"])) if x),
        "rear stand and devices are P/E (see the frame and safety_sensors rows); the photos settle them",
        "order 1 question 4 (rear photos); requirement R3")
    add("Photos under the table (torch, from the front skirt and from the rear table end): base cavity, backgauge "
        "spindle and nut, encoder BR40, the hydraulic box in the right support (tank OZ1, pump OP1, valve block OV2)",
        "under the front table and under the rear table, X 0; right support front cover open",
        "; ".join(x for x in (bx(["backgauge.spindle", "backgauge.encoder_BR40", "clamp.tank_oz1"]),
                              an_txt(["sensor.BR40"])) if x),
        "E/P values of the backgauge, clamp and frame rows; the photos settle them",
        "order 1 question 4 (photos under the table); requirement R3")
    d3 = None
    for c in (report.checks if report else []):
        if c.get("check") == "1" and isinstance(c.get("data"), dict) and "built_option" in c["data"]:
            d3 = c["data"]
    if d3:
        cur = (f"built option {d3['built_option']}: cabinet X {d3['built_cabinet_x'][0]:.0f}..{d3['built_cabinet_x'][1]:.0f}, "
               f"width across it {d3.get('built_span', 0):.0f}; left end without the cabinet "
               f"{d3['without_cabinet_left']:.0f} ({d3['without_cabinet_left_body']})")
        if "other_option" in d3:
            cur += (f"; option {d3['other_option']}: cabinet X {d3['other_cabinet_x'][0]:.0f}..{d3['other_cabinet_x'][1]:.0f}, "
                    f"width across {d3['other_span']:.0f}")
    else:
        cur = "as housing.M9 (check 1 of assembly.py gives the built numbers)"
    add("DECISION 3: X of the left column's outer face against the cabinet's left and right faces, and the overall "
        "width across the cabinet (settles cabinet option A or B); same question as housing.M9",
        "left end of the machine, tape along the floor from the right end", cur, "+-115 (housing cabinet X)",
        "DECISION 3; housing.M9-M11")
    add("DECISION 4: photos of the cam switches S12, S13, S14: where they sit and which cam or lever each one reads; "
        "same request as safety_sensors.SS2 = knife.M9",
        "drive side, at the crank / cam disc (cover open, machine off and locked)",
        an_txt(["sensor.S12", "sensor.S13", "sensor.S14"]) + "; flagged placeholders", "place unknown (E)",
        "DECISION 4; safety_sensors.SS2; knife.M9")
    add("Clamp open item 1: the frame wall that carries the two ball bearings of gear 8's shaft (no frame body holds "
        "it): its X extent, thickness and lowest Z; same question as frame.M7 and clamp.M7",
        "under cover 11 on the frame top, centre (cover off)", bx(["clamp.gear_8", "frame.crossbar"]),
        "E (no frame body there)", "clamp spec open item 1; frame.M7; clamp.M7")
    return rows


def write_all(root, bodies, anchors, meta, report, bounds=None):
    root = Path(root)
    short.root = str(root.resolve()).replace("\\", "/") + "/"
    files = Files(root)
    mrows, groups, counts = read_measures(root)
    ids = {r["id"] for r in mrows} | {g["id"] for g in groups}
    devs = device_ids(anchors)
    per_body, extra, keys_all = read_components(root, bodies, meta, files)

    # cross-references inside the measure rows
    bad_refs = []
    for r in mrows:
        refs, bad = cross_refs(" ".join((r["what"], r["where"], r["current"], r["error"])), r["part"], ids, devs)
        r["refs"] = [x for x in refs if x != r["id"]]
        bad_refs += [f"{r['id']} -> {b}" for b in bad]

    # body rows: files, classes, errors, measure links
    body_out, problems, e_unlinked = [], [], []
    gid_rows = {}
    for r in mrows:
        m = re.match(r"(G\d+)[a-z]$", r["rid"])
        if m:
            gid_rows.setdefault(f"{r['part']}.{m.group(1)}", []).append(r["id"])
    # the backgauge's MEASURE MAP: component i of a gap group -> the row named i-th in 'named on' ('G2g: journal'),
    # whose what or where cell must hold those words
    comp_to_rows, map_bad = {}, []
    by_id = {r["id"]: r for r in mrows}
    for g in groups:
        named = [x.strip() for x in g["named"].split(";") if x.strip() and x.strip() != "-"]
        if len(named) != len(g["components"]):
            map_bad.append(f"{g['id']}: {len(g['components'])} components but {len(named)} 'line: words' entries")
        for c, nm in zip(g["components"], named):
            m = re.match(r"(G\d+[a-z])\s*:\s*(.+)$", nm)
            rid = f"{g['part']}.{m.group(1)}" if m else None
            r = by_id.get(rid)
            if not r:
                map_bad.append(f"{g['id']}: '{nm}' names no measure row")
                continue
            if m.group(2).lower() not in (r["what"] + " " + r["where"]).lower():
                map_bad.append(f"{g['id']}: words '{m.group(2)}' not in {rid}'s what/where")
            comp_to_rows.setdefault((g["part"], c), []).append(rid)
    for b in bodies:
        part, bid = b.split(".", 1)
        info = per_body.get(b, {"rows": [], "component": bid})
        km = keys_all.get(part, {})
        if not info["rows"]:
            problems.append(f"{b}: no component row in spec/{part}.md")
        for t in info["rows"]:
            used = keys_in(t["source"], km)
            fl, unresolved = [], []
            for k in used:
                if km.get(k):
                    fl += km[k]
                else:
                    unresolved.append(k)
            fl += files.resolve(t["source"])
            fl = list(dict.fromkeys(fl))
            prim = [f for f in fl if primary(f) and f.exists()]
            cls_cell, err = t["class"], t["error"]
            # "as the right one": the cell is expanded with the mirrored body's own cell, and the class letters are
            # read from the printed cell (critic F6), so the class column itself carries D/T/P/E/W
            sib = re.sub(r"_(left|right)$", lambda m: "_right" if m.group(1) == "left" else "_left", bid)
            if sib != bid:
                for s in per_body.get(f"{part}.{sib}", {}).get("rows", [])[:1]:
                    if re.match(r"as (the )?(left|right)", cls_cell.strip().lower()):
                        cls_cell = f"{cls_cell} [= {s['class']}]"
                    if re.match(r"as (the )?(left|right)", err.strip().lower()):
                        err = f"{err} [= {s['error']}]"
            letters = class_letters(cls_cell)
            # measure links: IDs in the row, part-qualified refs, gap groups naming the component, rows naming the body
            refs, bad = cross_refs(t["raw"], part, ids, devs)
            bad_refs += [f"{b} -> {x}" for x in bad]
            refs += comp_to_rows.get((part, info["component"]), []) + comp_to_rows.get((part, bid), [])
            how = "spec" if refs else ""
            if not refs:                     # no link written by the spec: a measure row whose 'what' names the body
                side = re.sub(r"_(left|right)$", "", bid)
                base = re.sub(r"_\d+$", "", side)
                same = {re.sub(r"_(left|right)$", "", x.split(".", 1)[1]) for x in bodies if x.startswith(part + ".")
                        and re.sub(r"_\d+$", "", re.sub(r"_(left|right)$", "", x.split(".", 1)[1])) == base}
                pats = name_patterns(b, info["component"], base if base != side and len(same) == 1 else None)
                refs = [r["id"] for r in mrows if r["part"] == part
                        and any(re.search(pt, r["what"].lower()) for pt in pats)]
                how = "name" if refs else ""
            refs = list(dict.fromkeys(refs))
            need = bool(set(letters) & {"E", "W"})
            row = {"body": b, "spec_row": t["row_id"], "term": t["term"], "geo": t["geo"], "source": t["source"],
                   "keys": used, "unresolved": unresolved, "files": prim, "class": cls_cell, "letters": letters,
                   "error": err, "refs": refs, "how": how, "line": t["line"], "need": need}
            body_out.append(row)
            if not prim:
                problems.append(f"{b} ({t['row_id']}): no existing source file (keys {used}, unresolved {unresolved})")
            if not letters:
                problems.append(f"{b} ({t['row_id']}): class '{t['class']}' has none of {CLASS_LETTERS}")
            if need and (not err.strip() or err.strip() in ("-", "—")):
                problems.append(f"{b} ({t['row_id']}): class {''.join(letters)} without an error")
            if need and not refs:
                e_unlinked.append(row)

    # assembly rows: photo requests, decisions, then one row per estimated body without a measure row
    arows = assembly_rows(anchors, bounds, report)
    for row in e_unlinked:
        n = len(arows) + 1
        b = row["body"]
        cur = fmt_box(bounds[b]) if bounds and b in bounds else row["geo"][:160]
        arows.append({"id": f"assembly.A{n}", "part": "assembly", "rid": f"A{n}",
                      "what": f"{b} ({row['spec_row']}{', ' + row['term'] if row['term'] else ''}): outer size and position "
                              f"(class {'/'.join(row['letters'])}; spec/{b.split('.')[0]}.md has no measure row for it)",
                      "where": row["geo"][:200] or "see the spec row", "current": f"model {cur}", "error": row["error"],
                      "line": row["line"], "origin": "assembly (estimated body without a spec measure row)"})
        row["refs"] = [f"assembly.A{n}"]
    all_rows = mrows + arows

    # ------------------------------------------------------------------ measure_list.md
    n_spec = sum(c[0] for c in counts.values())
    n_gap = sum(c[1] for c in counts.values())
    L = ["# Tape-measure and photo list of the assembled model (Adast Maxima MS 115 PS, serial 578.0009)", "",
         "Written by `stage_1_mechanics/assembly/merge_tables.py` (run by `assembly.py`); do not edit by hand, re-run "
         "the script. Every row is read at run time from the measure tables of the six part specs (`spec/<part>.md`); "
         "the `assembly.A*` rows are the assembly's own (photo requests of order 1 question 4, DECISIONS 3 and 4, clamp "
         "open item 1, and one row for each estimated body that no spec row covers).",
         "IDs (identifiers) are part-qualified: `knife.M9` is row M9 of `spec/knife.md`. Units mm (millimetres); X + "
         "to the operator's right, Y + from the cutting line toward the rear, Z up from the floor. Classes: D drawing, "
         "T table or text, P photo proportion, E estimated, W web (counts as E, weaker than the machine's own "
         "documents).",
         ABBREV_MEASURE,
         "", "Rows per spec: " + "; ".join(f"{p} {c[0]}" + (f" + {c[1]} gap groups" if c[1] else "")
                                            for p, c in counts.items())
         + f"; together {n_spec} measure rows + {n_gap} gap groups; assembly rows {len(arows)}.", "",
         "| id | what to measure | where | current value (model) | error | from | see also |", "|---|---|---|---|---|---|---|"]
    for r in all_rows:
        L.append("| " + " | ".join(esc(x) for x in (r["id"], r["what"], r["where"], r["current"], r["error"], r["line"],
                                                    ", ".join(r.get("refs", [])))) + " |")
    if groups:
        L += ["", "## Gap groups of the backgauge (which measure rows cover which component)", "",
              "| id | components | measure rows | named on | from |", "|---|---|---|---|---|"]
        for g in groups:
            L.append("| " + " | ".join(esc(x) for x in (g["id"], ", ".join(g["components"]) or "-",
                                                        ", ".join(gid_rows.get(g["id"], [])) or "-", g["named"],
                                                        g["line"])) + " |")
    if bad_refs:
        L += ["", "## Cross-references that do not resolve", ""] + [f"- {x}" for x in bad_refs]
    (root / "measure_list.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ------------------------------------------------------------------ sources.md
    S = ["# Source table of the assembled model (Adast Maxima MS 115 PS, serial 578.0009)", "",
         "Written by `stage_1_mechanics/assembly/merge_tables.py` (run by `assembly.py`); do not edit by hand. One row "
         "for each spec row of each body of `out/assembly.glb` (a body with feature rows, such as the frame table's "
         "slot, has several). Columns: the body (`<part>.<body>`), the spec row and its Russian or Czech term as the "
         "spec gives it, the spec's size and position, the model's bounding box after assembly, the spec's source text "
         "(pages, figures, photos), the files its source keys resolve to (checked to exist), class, error, and the "
         "measure rows that cover it.",
         "File prefixes: OM/ = preparatory_data_analysis/maxima_documents/adast_guillotine_operating_manual/ (the "
         "operating manual of this variant), DOC/ = preparatory_data_analysis/maxima_documents/, PH/ = "
         "preparatory_data_analysis/maxima_photos/, ART/ = static_dynamic_memory/blocks/generation_001/artifacts/ "
         "(crops and saved web pages). Classes: D drawing, T table or text, P photo proportion, E estimated, W web "
         "(weaker than the machine's own documents and photos, marked 'weaker (web)').", ABBREV_SOURCES, "",
         "| body | spec row (term) | size and position (spec) | model bounding box | source (spec text) | files | class "
         "| error | measure rows | spec line |", "|---|---|---|---|---|---|---|---|---|---|"]
    for row in body_out:
        cls = row["class"] + (" - W: weaker (web)" if "W" in row["letters"] else "")
        S.append("| " + " | ".join(esc(x) for x in (
            row["body"], row["spec_row"] + (f" ({row['term']})" if row["term"] else ""), row["geo"],
            fmt_box(bounds[row["body"]]) if bounds and row["body"] in bounds else "-", row["source"],
            "; ".join(short(f) for f in row["files"]) or "NONE", cls, row["error"] or "-",
            (", ".join(row["refs"]) + (" (the row names it)" if row["how"] == "name" else "")) or "-",
            row["line"])) + " |")
    if extra:
        S += ["", "## Spec component rows that are not bodies (reference surfaces and features)", "",
              "| part | spec row (term) | source | class | error | spec line |", "|---|---|---|---|---|---|"]
        for t in extra:
            S.append("| " + " | ".join(esc(x) for x in (t["part"], t["row_id"] + (f" ({t['term']})" if t["term"] else ""),
                                                        t["source"], t["class"], t["error"], t["line"])) + " |")
    S += ["", "## Source keys of each spec and the files they resolve to", "",
          "| part | key | files (exist) |", "|---|---|---|"]
    for p, km in keys_all.items():
        for k, fl in km.items():
            S.append("| " + " | ".join(esc(x) for x in (p, k, "; ".join(short(f) + ("" if f.exists() else " (MISSING)")
                                                                          for f in fl) or "(no file: partner file or folder)")) + " |")
    (root / "sources.md").write_text("\n".join(S) + "\n", encoding="utf-8")

    # ------------------------------------------------------------------ check 11
    nb = len(bodies)
    covered = {r["body"] for r in body_out}
    need = [r for r in body_out if r["need"]]
    empty = [r["id"] for r in mrows if not (r["where"].strip() and r["current"].strip() and r["error"].strip())]
    # the specs' own "-" errors (items not modelled, or which-type questions): faithful, but printed (critic F7)
    dash = [r["id"] for r in mrows if r["error"].strip() in ("-", "—", "–")]
    problems += map_bad
    for body, words in ALIAS.items():
        if body in bodies:
            for w in words:
                if not any(r["part"] == body.split(".")[0] and w.lower() in r["what"].lower() for r in mrows):
                    problems.append(f"alias '{w}' of {body} is in no 'what' cell of spec/{body.split('.')[0]}.md")
    by_name = sorted(r["body"] for r in body_out if r["how"] == "name")
    ok = not problems and len(covered) == nb and not bad_refs and not empty
    text = (f"sources.md: {len(body_out)} rows for {len(covered)}/{nb} bodies; each with an existing source file "
            f"and a class of {CLASS_LETTERS}: {'yes' if not problems else 'NO'}; {len(need)} rows are E or W: each with "
            f"an error and a measure row (linked by the spec itself: {sum(1 for r in need if r['how'] == 'spec')}, "
            f"by a row whose 'what' names the body: {sum(1 for r in need if r['how'] == 'name')}); "
            f"{len(e_unlinked)} of them had no row in their spec and got assembly rows "
            f"{', '.join(r['refs'][0] for r in e_unlinked) if e_unlinked else '-'}. measure_list.md: {n_spec} spec rows "
            f"(" + ", ".join(f"{p} {c[0]}" for p, c in counts.items()) + f") + {n_gap} gap groups + {len(arows)} "
            f"assembly rows; rows with an empty where, current value or error cell: {empty or 'none'}; error '-' as "
            f"the spec writes it (not modelled or a which-type question): {len(dash)}"
            + (f" ({', '.join(dash)})" if dash else "") + "; unresolved "
            f"cross-references: {bad_refs or 'none'}" + ("; problems: " + "; ".join(problems) if problems else ""))
    data = {"bodies": nb, "source_rows": len(body_out), "e_or_w_rows": len(need),
            "assembly_rows_for_unlinked": [r["body"] for r in e_unlinked], "spec_measure_rows": dict(
                (p, c[0]) for p, c in counts.items()), "gap_groups": n_gap, "assembly_rows": len(arows),
            "problems": problems, "bad_refs": bad_refs, "empty_measure_cells": empty, "error_dash_rows": dash,
            "linked_by_name": by_name, "aliases": ALIAS}
    if report is not None:
        report.add("11", "PASS" if ok else "FAIL", text, data)
    else:
        print(("PASS" if ok else "FAIL") + " [11] " + text)
    # for the caller only, not stored in the report: each body's source rows (open items) and every measure ID
    # (the name guard of assembly.py)
    res = dict(data)
    res["rows_by_body"] = {}
    for r in body_out:
        res["rows_by_body"].setdefault(r["body"], []).append(
            {"class": r["class"], "letters": "".join(sorted(r["letters"])), "error": r["error"],
             "refs": list(r["refs"]), "line": r["line"]})
    res["measure_ids"] = sorted(ids)
    # each spec's source keys and the files they resolve to (the open items write out the keys they quote, critic g11)
    res["key_files"] = {p: {k: [short(f) for f in fl] for k, fl in km.items()} for p, km in keys_all.items()}
    return res


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(HERE.parent))
    ap.add_argument("--project", default=None)
    a = ap.parse_args()
    rt = Path(a.root)
    pj, how = find_project(a.project, rt)
    if pj is None:
        print(f"merge_tables.py: stop: no project folder ({how}); pass --project <folder>", file=sys.stderr)
        sys.exit(2)
    set_project(pj)
    names, anc, met = [], {}, {}
    for pt in PARTS:
        d = json.loads((rt / "out" / f"{pt}_anchors.json").read_text(encoding="utf-8"))
        anc[pt], met[pt] = d["anchors"], d.get("meta", {})
        import trimesh
        sc = trimesh.load(rt / "out" / f"{pt}.glb", force="scene")
        names += [n if n.startswith(pt + ".") else f"{pt}.{n}" for n in sc.graph.nodes_geometry]
    res = write_all(rt, sorted(names), anc, met, None)
    sys.exit(0 if not res["problems"] and not res["bad_refs"] else 1)
