"""Check 9 (contact) of episode 2: nothing of the electrical layer hangs in the air.

Run:  python -B stage_2_electronics/scheme_3d/contact_check.py [electrical.glb] [placements.csv] [bundles.csv] [report.txt]
      python -B stage_2_electronics/scheme_3d/contact_check.py --selftest   (eight mutations, each must FAIL)
Defaults: the files next to this script; report contact_report.txt next to it. Exit 1 when FAIL > 0.

Geometry is real mesh-to-mesh (manifold3d min_gap and intersection volume), in mm, machine coordinates, Z up,
never rescaled. Stage 1 (stage_1_mechanics/out/assembly.glb, 125 bodies) is only read.
Rules (meta orc, settled): an item (box, marker, mounting part, gland, clip) lies at most 1 mm from a body of the
model, the cabinet, the console, the floor (Z 0) or another item of ours, and no item overlaps a body (passes named in
the CSV files excepted); every connected group of our items reaches the model, the cabinet, the console or the floor;
every clip lies at most 1 mm from a body that is not a bundle; along every bundle leg the free span between fastened
points (clip, gland, duct, end item) is at most 300 mm; no item lies in a space stage 1 keeps free for moving or
reserved parts (RESERVED boxes of stage_1_mechanics/out/*_anchors.json, critic finding G). INFO: stage-1 bodies we attach to that touch no other body.
housing.cabinet and housing.console are solid blocks in stage 1: they are checked as shells of WALL mm (estimated).
"""
import csv, json, sys
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
S1_GLB = ROOT / "stage_1_mechanics" / "out" / "assembly.glb"
WALL = {"housing.cabinet": 2.0, "housing.console": 2.0}   # sheet-steel wall, estimated ±1 mm
GAP, SPAN, OVL, STEP = 1.0, 300.0, 0.5, 5.0
STROKE = {"clamp": 130.0}   # mm down from rest: clamp lift 130 (stage_1_mechanics/spec/clamp.md line 51, OM p.7)
FLOOR = "floor.Z0"
# stage-1 spaces kept free (box min/max, or a joint's passage): moving clamp parts, the backgauge drive, the knife
# drive unit, mechanical passages, bores, slots and windows, the pedal; frame.cavity.*, corridor.* and cabinet.* are
# room, not reserved
RESERVED = ("envelope.", "space.", "joint.passage.", "joint.bore.", "joint.slot.", "joint.window.", "table.slot",
            "plan.pedal")


def load_glb(path):
    """Every node of a GLB as a trimesh in its world frame (the stage-1 loader, assembly.py lines 276-282)."""
    sc = trimesh.load(str(path), force="scene")
    out = {}
    for node in sc.graph.nodes_geometry:
        tf, g = sc.graph[node]
        m = sc.geometry[g].copy()
        m.apply_transform(tf)
        out[node] = m
    return out


def to_mf(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))


def shell(m, t):
    """Convex solid -> its shell: the solid minus the solid with every face plane moved inward by t."""
    outer = to_mf(m)
    inner = outer
    planes = {}
    for n, f in zip(m.face_normals, m.faces):
        d = float(np.dot(n, m.vertices[f[0]]))
        planes[tuple(np.round(n, 5)) + (round(d, 3),)] = (n, d)
    for n, d in planes.values():
        inner = inner.trim_by_plane((-float(n[0]), -float(n[1]), -float(n[2])), t - d)
    return outer - inner


def bodies_s1():
    """name -> (manifold, lo, hi) for the 125 stage-1 bodies (enclosures as shells) and the floor."""
    out = {}
    for name, m in load_glb(S1_GLB).items():
        man = shell(m, WALL[name]) if name in WALL else to_mf(m)
        out[name] = (man, m.bounds[0], m.bounds[1])
    fl = mf.Manifold.cube((8000.0, 8000.0, 50.0)).translate((-4000.0, -4000.0, -50.0))
    out[FLOOR] = (fl, np.array([-4000, -4000, -50.0]), np.array([4000, 4000, 0.0]))
    return out


def reserved_s1():
    """Stage-1 reserved boxes (RESERVED prefixes and every *.keepout.*) as manifolds, from the committed anchor files."""
    out = {}
    for f in sorted((ROOT / "stage_1_mechanics" / "out").glob("*_anchors.json")):
        for k, v in json.loads(f.read_text(encoding="utf-8"))["anchors"].items():
            if not (k.startswith(RESERVED) or ".keepout." in k):
                continue
            if "min" in v and "max" in v:
                lo, hi = np.array(v["min"], float), np.array(v["max"], float)
            elif "passage" in v:
                lo, hi = (np.array([q[i] for q in v["passage"]], float) for i in (0, 1))
            else:
                continue
            box = trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix((lo + hi) / 2))
            out[k] = (to_mf(box), lo, hi)
    return out


def near(lo1, hi1, lo2, hi2, tol=GAP):
    return bool(np.all(lo1 <= hi2 + tol) and np.all(lo2 <= hi1 + tol))


def gap_ovl(a, b):
    """(gap mm, overlap mm3) of two manifolds; gap 0 when they touch or overlap."""
    ov = (a ^ b).volume()
    if ov > 1e-6:
        return 0.0, ov
    return a.min_gap(b, GAP + 2.0), 0.0


def read_rows(path):
    if not path or not Path(path).exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def run(glb, placements, bundles, report=None, mutate=None, mutate_legs=None, mutate_rows=None):
    s1, RES = bodies_s1(), reserved_s1()
    el = {k: v for k, v in load_glb(glb).items() if k.startswith("electrical.")}
    if mutate:
        el = mutate(el)
    E = {k: (to_mf(m), m.bounds[0], m.bounds[1]) for k, m in el.items()}
    prow, brow = read_rows(placements), read_rows(bundles)
    if mutate_legs:
        brow = mutate_legs(brow)
    if mutate_rows:
        prow = mutate_rows(prow)
    passes = {}                                   # node -> names it may overlap
    for r in prow:
        passes.setdefault("electrical." + r["item"], set()).update("electrical." + p for p in r.get("passes", "").split("; ") if p)
    legs = {r["leg"]: r for r in brow}
    for k in E:
        if k.startswith("electrical.bundle."):
            leg = k.split(".")[2]
            if leg in legs:
                passes.setdefault(k, set()).update("electrical." + p for p in legs[leg]["passes"].split("; ") if p)
    parent = {g: r["from_item"][len("junction on "):] for g, r in legs.items() if r["from_item"].startswith("junction on ")}

    PS = {k: v for k, v in E.items() if k.startswith("electrical.pass.")}   # holes, grommets, glands
    through = {}                                  # (pass items, stage-1 body) -> legs

    OURS = ("dev", "mark", "conn", "mount", "pass", "clip", "bundle")
    fast = {"electrical." + r["item"]: {("electrical." + f if f.split(".")[0] in OURS else f)
                                        for f in r["fastened_to"].split("; ") if f}
            for r in prow if r["item"].startswith("pass.")}

    def allowed(a, b):
        for p, x in ((a, b), (b, a)):             # rule 1: a pass may overlap only the bodies its fastened_to names
            if p.startswith("electrical.pass."):  # and the segments and clips of the legs whose passes column names it
                lx = x.split(".")[2] if x.split(".")[:2] in (["electrical", "bundle"], ["electrical", "clip"]) else ""
                return x in fast.get(p, ()) or p[len("electrical."):] in legs.get(lx, {}).get("passes", "").split("; ")
        if b in passes.get(a, ()) or a in passes.get(b, ()):
            return True
        lg = lambda x: x.split(".")[2] if x.split(".")[1] in ("bundle", "clip") else None
        la, lb = lg(a), lg(b)                     # segments and clips of one bundle, or of a branch and its parent
        return bool(la and lb) and (la.split("-")[0] == lb.split("-")[0] or parent.get(la) == lb or parent.get(lb) == la)

    lines, fails, touch_s1, edges, clipc = [], 0, {}, {k: set() for k in E}, {}
    soft = lambda x: x.split(".")[1] in ("bundle", "clip")   # a cable and its clips carry nothing (finding C)
    for k, (a, lo, hi) in sorted(E.items()):
        hits, bad = [], []
        pool = [(n, v) for n, v in s1.items()] + [(n, v) for n, v in E.items() if n != k]
        for n, (b, blo, bhi) in pool:
            if not near(lo, hi, blo, bhi):
                continue
            g, ov = gap_ovl(a, b)
            if ov > OVL and not allowed(k, n):
                if k.startswith("electrical.bundle.") and not n.startswith("electrical."):
                    ps = [p for p, (pm, plo, phi) in PS.items() if near(lo, hi, plo, phi, 0.0)]
                    rest = (a ^ b)
                    for p in ps:
                        rest = rest - PS[p][0]
                    ov = rest.volume()            # overlap with a wall outside every passage
                    if ov <= OVL:
                        through.setdefault((", ".join(ps), n), set()).add(k.split(".")[2])
                        continue
                bad.append(f"{n} {ov:.1f}mm3")
            if g <= GAP:
                hits.append(n)
        s1hits = [n for n in hits if not n.startswith("electrical.")]
        touch_s1[k] = s1hits
        for n in hits:
            if n.startswith("electrical.") and not soft(k) and not soft(n):
                edges[k].add(n); edges[n].add(k)
        kind = k.split(".")[1]
        carriers = [n for n in hits if not n.startswith(("electrical.bundle.", "electrical.clip."))]
        if kind == "clip":
            clipc[k] = carriers
        why = []
        if bad:
            why.append("overlap " + ", ".join(bad))
        if not hits:
            why.append("in the air (nothing within 1 mm)")
        if kind == "clip" and not carriers:
            why.append("clip on no body")
        res = [f"{rn} {(a ^ rb).volume():.0f}mm3" for rn, (rb, rlo, rhi) in sorted(RES.items())
               if near(lo, hi, rlo, rhi, 0.0) and (a ^ rb).volume() > OVL]
        if res:
            why.append("in a stage-1 reserved space: " + ", ".join(res))
        st = "FAIL" if why else "PASS"
        fails += st == "FAIL"
        if kind != "bundle" or why:
            lines.append(f"{st} {k} touches {', '.join(hits[:6]) or '-'}" + (" | " + "; ".join(why) if why else ""))
    for (ps, n), lg in sorted(through.items()):
        lines.append(f"PASS-THROUGH {n} inside {ps}: legs {', '.join(sorted(lg))}, overlap outside the passage 0")
    # field devices: anchor in or on its stage-1 body, our item at most 1 mm from its carrier
    for r in prow:
        if not r.get("device_body") or ("electrical." + r["item"]) not in E:
            continue
        a = E["electrical." + r["item"]][0]
        q = mf.Manifold.cube((0.2, 0.2, 0.2), True).translate(tuple(float(r[c]) for c in ("x_mm", "y_mm", "z_mm")))
        db = s1.get(r["device_body"]); fb = s1.get(r["fastened_to"]) or E.get("electrical." + r["fastened_to"])
        d_anchor = gap_ovl(q, db[0])[0] if db else 99.0
        d_fast = gap_ovl(a, fb[0])[0] if fb else 99.0
        d_item = q.min_gap(a, 2000.0)
        # check 6 as read here (critic finding I): anchor in or on the device's stage-1 body; our item at most 1 mm
        # from that body, unless the row's note names an exception (item on another carrier: S28, Y10)
        d_body = gap_ovl(a, db[0])[0] if db else 99.0
        if db and d_body > GAP:
            d_body = a.min_gap(db[0], 2000.0)
        exc = "exception:" in r["note"]
        st = "PASS" if d_anchor <= GAP and d_fast <= GAP and (d_body <= GAP or exc) else "FAIL"
        fails += st == "FAIL"
        lines.append(f"{st} MARKER {r['designation']} anchor {r['anchor']} {d_anchor:.1f} mm from {r['device_body']}; "
                     f"{r['item']} {d_body:.1f} mm from it, {d_fast:.1f} mm from {r['fastened_to']}; "
                     f"anchor to item {d_item:.1f} mm" + (f" ({r['note']})" if d_body > GAP else ""))
    # connected groups of our rigid items (no bundle, no clip) must reach stage 1, the cabinet, the console or the floor
    seen, grounded = set(), set()
    for k in sorted(E):
        if k in seen or soft(k):
            continue
        comp, todo = set(), [k]
        while todo:
            x = todo.pop()
            if x not in comp:
                comp.add(x); todo.extend(edges[x] - comp)
        seen |= comp
        if any(touch_s1[x] for x in comp):
            grounded |= comp
        else:
            fails += 1
            lines.append(f"FAIL group of {len(comp)} ({sorted(comp)[0]} ...) touches only itself or a cable")
    for k, cs in sorted(clipc.items()):       # a clip sits on stage 1 or on a grounded item of ours
        if cs and not any(not n.startswith("electrical.") or n in grounded for n in cs):
            fails += 1
            lines.append(f"FAIL {k} sits only on {', '.join(cs)}, which reach no body of the model")
    # free spans along each leg
    fixers = {k: (lo, hi) for k, (a, lo, hi) in E.items()
              if k.split(".")[1] in ("clip", "pass") or k.startswith("electrical.mount.duct")}
    nspan = 0
    for leg, r in legs.items():
        pts = [np.array([float(c) for c in p.split()]) for p in r["path_mm"].split("; ")]
        ends = [("electrical." + r[c]) for c in ("from_item", "to_item") if not r[c].startswith(("junction on ", "stage-1 "))]
        boxes = list(fixers.values()) + [(E[e][1], E[e][2]) for e in ends if e in E]
        miss = [e for e in ends if e not in E]
        free, worst, wq = 0.0, 0.0, pts[0]
        for p0, p1 in zip(pts[:-1], pts[1:]):
            L = float(np.linalg.norm(p1 - p0))
            for t in np.linspace(0, 1, max(2, int(L / STEP) + 1)):
                q = p0 + t * (p1 - p0)
                held = any(np.all(q >= lo - GAP) and np.all(q <= hi + GAP) for lo, hi in boxes)
                free = 0.0 if held else free + L / max(1, int(L / STEP))
                if free > worst:
                    worst, wq = free, q
        nspan += 1
        st = "FAIL" if worst > SPAN or miss else "PASS"
        fails += st == "FAIL"
        lines.append(f"{st} leg {leg} longest free span {worst:.0f} mm, ending at ({wq[0]:.0f}, {wq[1]:.0f}, {wq[2]:.0f})"
                     + (f" | end item missing {miss}" if miss else ""))
    # leg ends (check 8, finding D): first and last path point at most 1 mm from the named item,
    # a junction at most 1 mm from its parent leg's path, a stage-1 end at most 1 mm from that body
    paths = {g: [np.array([float(c) for c in p.split()]) for p in r["path_mm"].split("; ")] for g, r in legs.items()}

    def to_path(q, pts):
        best = 1e9
        for a, b in zip(pts[:-1], pts[1:]):
            ab = b - a
            t = float(np.clip(np.dot(q - a, ab) / max(float(np.dot(ab, ab)), 1e-12), 0.0, 1.0))
            best = min(best, float(np.linalg.norm(q - (a + t * ab))))
        return best
    for g, r in legs.items():
        for which, q, it in (("from", paths[g][0], r["from_item"]), ("to", paths[g][-1], r["to_item"])):
            if it.startswith("junction on "):
                par = it[len("junction on "):]
                d = to_path(q, paths[par]) if par in paths else 99.0
            else:
                b = s1.get(it[len("stage-1 "):]) if it.startswith("stage-1 ") else E.get("electrical." + it)
                cube = mf.Manifold.cube((0.2, 0.2, 0.2), True).translate(tuple(float(c) for c in q))
                d = (0.0 if (cube ^ b[0]).volume() > 0 else cube.min_gap(b[0], 2000.0)) if b and it else 99.0
            st = "PASS" if d <= GAP else "FAIL"
            fails += st == "FAIL"
            lines.append(f"{st} END {g} {which} {it or '-'} {d:.1f} mm")
    # slack loops (critic finding H): a leg that moves with a part and hangs on a fixed leg must start at the end of
    # an unclipped fixed loop whose path is at least the rest gap between the loop's ends plus the part's stroke
    for g, r in legs.items():
        mv, p = r["moves_with"], parent.get(g)
        if not mv or p not in legs or legs[p]["moves_with"] == mv:
            continue
        pts, stroke = paths[p], STROKE.get(mv, 0.0)
        length = sum(float(np.linalg.norm(b - a)) for a, b in zip(pts[:-1], pts[1:]))
        rest = float(np.linalg.norm(pts[-1] - pts[0]))
        full = float(np.linalg.norm(pts[-1] - np.array((0.0, 0.0, stroke)) - pts[0]))
        at_end = float(np.linalg.norm(paths[g][0] - pts[-1])) <= GAP
        clipped = bool(legs[p]["clips"].strip())
        st = "PASS" if at_end and not clipped and stroke > 0 and length >= rest + stroke else "FAIL"
        fails += st == "FAIL"
        lines.append(f"{st} SLACK {p} -> {g} (moves with {mv}, stroke {stroke:.0f} mm down): loop {length:.0f} mm >= "
                     f"straight distance between the loop's ends at rest {rest:.0f} + stroke {stroke:.0f} = "
                     f"{rest + stroke:.0f} mm; straight distance between the loop's ends at full stroke {full:.0f} mm"
                     + ("" if at_end else "; moving leg not at the loop's end") + ("; loop is clipped" if clipped else ""))
    # INFO: stage-1 bodies we attach to that touch no other stage-1 body
    used = sorted({n for v in touch_s1.values() for n in v if n != FLOOR and n not in WALL})
    for n in used:
        b, lo, hi = s1[n]
        if not any(m != n and near(lo, hi, v[1], v[2]) and gap_ovl(b, v[0])[0] <= GAP for m, v in s1.items()):
            lines.append(f"INFO {n}: stage-1 body that touches no other body; our items attach to it, it stays as built")
    head = (f"contact_check {Path(glb).name}: {len(E)} items, {nspan} legs, FAIL {fails}; "
            f"rules gap <= {GAP} mm, overlap <= {OVL} mm3 outside named passes, free span <= {SPAN} mm, "
            f"enclosure walls {WALL} mm (estimated), no item in the {len(RES)} stage-1 reserved spaces")
    if report:
        Path(report).write_text(head + "\n" + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return fails, head, lines


def selftest(glb, placements, bundles):
    """Eight mutations of the delivered layer; each must give FAIL > 0."""
    def up(el):            # first device box 50 mm up into the air
        k = next(k for k in sorted(el) if k.startswith("electrical.dev."))
        el[k] = el[k].copy(); el[k].apply_translation((0, 0, 50.0)); return el
    def noclip(el):        # all clips of the longest leg removed
        leg = max({k.split(".")[2] for k in el if k.startswith("electrical.clip.")},
                  key=lambda g: sum(k.split(".")[2] == g for k in el if k.startswith("electrical.clip.")))
        return {k: v for k, v in el.items() if not (k.startswith("electrical.clip.") and k.split(".")[2] == leg)}
    def sink(el):          # a marker that sits on top of its body sunk 10 mm into it
        k = next(k for k in ("electrical.mark.S30", "electrical.mark.Y14") if k in el)
        el[k] = el[k].copy(); el[k].apply_translation((0, 0, -10.0)); return el
    def hang(el):          # a 16 mm cube that touches only a bundle (critic finding C)
        lo, hi = el["electrical.bundle.B1.s2"].bounds
        c = (hi[0] + 8.3, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)
        el["electrical.dev.ZZ_test"] = trimesh.creation.box(extents=(16, 16, 16),
                                                             transform=trimesh.transformations.translation_matrix(c))
        return el
    def reserved(el):      # a 16 mm cube on the floor inside the clamp pedal link's space (critic finding G)
        el["electrical.dev.ZZ_reserved"] = trimesh.creation.box(
            extents=(16, 16, 16), transform=trimesh.transformations.translation_matrix((100.0, 0.0, 8.0)))
        return el
    def taut(rows):        # every slack loop pulled straight between its ends (critic finding H)
        for r in rows:
            if any(o["from_item"] == "junction on " + r["leg"] and o["moves_with"] and not r["moves_with"] for o in rows):
                p = r["path_mm"].split("; ")
                r["path_mm"] = "; ".join((p[0], p[-1]))
        return rows
    def unfasten(rows):    # pass.G1 no longer fastened to mount.plate, which it overlaps (tester 3, mutation 2)
        for r in rows:
            if r["item"] == "pass.G1":
                r["fastened_to"] = "housing.cabinet"
        return rows
    def unpass(rows):      # pass.G1 dropped from the passes column of leg B1, which runs through it
        for r in rows:
            if r["leg"] == "B1":
                r["passes"] = "; ".join(p for p in r["passes"].split("; ") if p != "pass.G1")
        return rows
    ok = True
    for name, f, fl, fr in (("box up 50 mm", up, None, None), ("clips of one leg removed", noclip, None, None),
                            ("marker sunk 10 mm", sink, None, None), ("cube hanging on bundle B1", hang, None, None),
                            ("cube on the floor in envelope.clamp.pedal_link", reserved, None, None),
                            ("slack loop pulled straight", None, taut, None),
                            ("pass.G1 not fastened to mount.plate", None, None, unfasten),
                            ("pass.G1 dropped from leg B1's passes", None, unpass, None)):
        n, _, lines = run(glb, placements, bundles, mutate=f, mutate_legs=fl, mutate_rows=fr)
        print(f"selftest {name}: FAIL {n} -> {'caught' if n else 'NOT CAUGHT'}")
        ok &= n > 0
    return ok


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    glb = args[0] if len(args) > 0 else HERE / "electrical.glb"
    pl = args[1] if len(args) > 1 else HERE / "placements.csv"
    bu = args[2] if len(args) > 2 else HERE / "bundles.csv"
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest(glb, pl, bu) else 1)
    rep = args[3] if len(args) > 3 else HERE / "contact_report.txt"
    n, head, lines = run(glb, pl, bu, rep)
    print(head)
    print("\n".join(l for l in lines if not l.startswith("PASS"))[:3000])
    sys.exit(1 if n else 0)
