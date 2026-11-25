"""Mutation test of the housing checks: a clean baseline first, then planted errors that a check must catch.

Run:  python mutation_test.py      Exit 0 = the clean baseline passes and every planted error is caught.
Model mutants run housing.checks() in memory (no file is written). The anchors mutants copy the published
out/*_anchors.json and out/housing.glb into a folder of the system temp folder, plant a duplicate switch.Q1 or
drop a source key there, and run housing's check 7 and check_spec.py on that copy. Spec mutants run check_spec.main() on a
mutated copy of spec/housing.md written to the system temp folder. The real out/ and spec files are never changed.
"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import housing as H      # noqa: E402
import check_spec as C   # noqa: E402

NB, BAD = H.load_neighbours()


def group_bounds(names):
    los, his = zip(*(H.bb(NB[n]) for n in names if n in NB))
    return np.min(los, axis=0), np.max(his, axis=0)


def plant(box6):
    """A box that only a sweep can hit: the patch (expected bounds) and the extra body."""
    eb = H.expected_bounds
    return {"expected_bounds": lambda option, eb=eb: {**eb(option), "plant": box6}}, {"plant": H.box(*box6)}


def run_model(patch, expect, drop=None, option="B", add=None):
    saved = {k: getattr(H, k) for k in patch}
    try:
        for k, v in patch.items():
            setattr(H, k, v)
        bodies = H.build(option)
        if drop:
            bodies.pop(drop)
        if add:
            bodies.update(add)
        rep = H.checks(bodies, NB, BAD, option)
    finally:
        for k, v in saved.items():
            setattr(H, k, v)
    failed = sorted(k for k, v in rep["checks"].items() if not v.get("pass", True))
    return failed, (expect in failed) if expect else not failed


def check_spec_failed(spec=None, out=None):
    saved = (C.SPEC, C.OUT)
    try:
        C.SPEC, C.OUT = spec or C.SPEC, out or C.OUT
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            C.main()
    finally:
        C.SPEC, C.OUT = saved
    lines = buf.getvalue().splitlines()
    return sorted(f for f in (ln.split()[0] for ln in lines if " FAIL " in ln or ln.endswith(" FAIL")) if f != "check_spec")


def run_spec(old, new, expect):
    text = C.SPEC.read_text(encoding="utf-8")
    assert text.count(old) == 1, old
    tmp = Path(tempfile.gettempdir()) / "housing_spec_mutant.md"
    tmp.write_text(text.replace(old, new), encoding="utf-8")
    try:
        failed = check_spec_failed(spec=tmp)
    finally:
        tmp.unlink()
    return failed, expect in failed


def dup_switch_q1(tmp):
    """switch.Q1 planted a second time in the copy of clamp_anchors.json."""
    cj = json.loads((tmp / "clamp_anchors.json").read_text(encoding="utf-8"))
    cj["anchors"]["switch.Q1"] = {"xyz": [0.0, 0.0, 0.0], "class": "E", "error_mm": 0, "source": "mutant"}
    (tmp / "clamp_anchors.json").write_text(json.dumps(cj), encoding="utf-8")


def drop_nb_key(tmp):
    """the key NB dropped from cover.right_support_front's source in the copy of housing_anchors.json."""
    hj = json.loads((tmp / "housing_anchors.json").read_text(encoding="utf-8"))
    a = hj["anchors"]["cover.right_support_front"]
    assert "; NB (" in a["source"], a["source"]
    a["source"] = a["source"].split("; NB (")[0]
    (tmp / "housing_anchors.json").write_text(json.dumps(hj), encoding="utf-8")


def run_out_mutant(edit, expect):
    """Copy out/*_anchors.json and out/housing.glb into a folder of the system temp folder, apply edit(tmp) there,
    run housing check 7 and check_spec.py on that copy; every check named in expect must fail."""
    tmp = Path(tempfile.gettempdir()) / "housing_out_mutant"
    tmp.mkdir(exist_ok=True)
    made = []
    for f in list(H.OUT.glob("*_anchors.json")) + [H.OUT / "housing.glb"]:
        shutil.copyfile(f, tmp / f.name)
        made.append(tmp / f.name)
    saved = H.OUT
    try:
        edit(tmp)
        H.OUT = tmp
        rep = {"checks": {}, "pass": True}
        H.check_anchor_uniqueness(rep)
        failed = (["7_anchors_once"] if not rep["checks"]["7_anchors_once"]["pass"] else []) + check_spec_failed(out=tmp)
    finally:
        H.OUT = saved
        for f in made:
            f.unlink()
        tmp.rmdir()
    return failed, all(e in failed for e in expect)


OUT_MUTANTS = [
    ("switch.Q1 planted twice (copy of clamp_anchors.json): housing 7 and check_spec D", dup_switch_q1,
     ["7_anchors_once", "D_devices_once"]),
    ("source key NB dropped from cover.right_support_front (copy of housing_anchors.json): check_spec C", drop_nb_key,
     ["C_anchors_vs_spec"]),
]


k_lo, k_hi = group_bounds(H.KNIFE_MOVING)
kn_lo, kn_hi = H.bb(NB["knife.knife"])
c_lo, c_hi = group_bounds(H.CLAMP_MOVING)
cf_lo, cf_hi = H.bb(NB["clamp.false_plate"])
p_lo, p_hi = H.bb(NB["backgauge.pusher_body"])
P_KNIFE = plant((-20.0, 20.0, float(kn_lo[1]), float(kn_hi[1]), float(k_lo[2]) - 50.0, float(k_lo[2]) - 30.0))
P_CLAMP = plant((-20.0, 20.0, float(cf_lo[1]), float(cf_hi[1]), float(c_lo[2]) - 50.0, float(c_lo[2]) - 30.0))
pz = float(p_lo[2] + p_hi[2]) / 2.0
P_BG = plant((-20.0, 20.0, 600.0, 620.0, pz - 10.0, pz + 10.0))

BASELINE = ("clean baseline: nothing planted, every check passes", {}, None, None, "B", None)
MODEL = [
    ("console pushed 50 into the frame", {"CON_Y0": -404.0, "CON_Y1": -344.0}, "3_no_overlap_neighbours_at_rest", None, "B", None),
    ("gauge hole Ø62 -> Ø56", {"IP_HOLES": [(937.0, 1377.0, 56.0), (937.0, 1309.0, 32.0), (937.0, 1244.0, 42.0)]},
     "3_no_overlap_neighbours_at_rest", None, "B", None),
    ("belt cover outer face 1553 -> 1546 (3 from the slip rings)", {"BPC": (1400.0, 1546.0, -394.0, 545.0, 70.0, 1000.0)},
     "5_belt_cover_clearance_ge_5", None, "B", None),
    ("right front cover turns backward", {"RFC_MAX_DEG": -90.0}, "4_swept_motions", None, "B", None),
    ("cover 11 sunk 5 into the frame top", {"C11": (-80.0, 55.0, 60.0, 150.0, 1530.0, 1560.0)},
     "3_no_overlap_neighbours_at_rest", None, "B", None),
    ("left panel in front of the cabinet dropped", {}, "6b_cavity_faces_covered", "left_side_panel_front", "B", None),
    ("cabinet option A (inside the frame)", {}, "3_no_overlap_neighbours_at_rest", None, "A", None),
    ("box 30..50 below the knife's lowest point at rest (only the knife stroke reaches it)", P_KNIFE[0],
     "4_swept_motions", None, "B", P_KNIFE[1]),
    ("box 30..50 below the clamp's lowest point at rest (only the clamp stroke reaches it)", P_CLAMP[0],
     "4_swept_motions", None, "B", P_CLAMP[1]),
    ("box at Y 600..620 in the pusher's path (only the backgauge travel reaches it)", P_BG[0],
     "4_swept_motions", None, "B", P_BG[1]),
    ("lamp E3 back at the drawing's own X -675 (r2: 149 inside the console's left edge)",
     {"LAMPS": {**H.LAMPS, "lamp.E3": ((-675.0, -454.0, 1467.0), "r2 reading")}},
     "10_lamps_on_their_F101_surface", None, "B", None),
    ("lamp E4 back at the drawing's own X 650 (r2: on the console face, not right of it)",
     {"LAMPS": {**H.LAMPS, "lamp.E4": ((650.0, -454.0, 1474.0), "r2 reading")}},
     "10_lamps_on_their_F101_surface", None, "B", None),
]
SPEC = [
    ("spec console bounds X ..850 -> ..900", "| X -835..850; Y -454..-394;", "| X -835..900; Y -454..-394;", "A_bounds_vs_spec"),
    ("spec instrument panel error loses its measure row", "X +-20, Y +-2, Z +-20 (M4)", "X +-20, Y +-2, Z +-20", "B_component_rows"),
    ("spec anchor S1 moved 30 in X", "| button.S1 | 773, -454, 1297 |", "| button.S1 | 803, -454, 1297 |", "C_anchors_vs_spec"),
    ("spec source file renamed", "maxima_photos/20261102_150610.jpg", "maxima_photos/20261102_150611.jpg", "E_source_files_and_crops"),
    ("spec F102 row: XC2 centre back at y 583 (the r4 text; its Z 686 does not follow)", "drawn centres y 582 /",
     "drawn centres y 583 /", "F_f102_scale"),
    ("spec anchor XC4 source back at side strip y 625 (the r4 text)", "side strip y 624,", "side strip y 625,",
     "F_f102_scale"),
    ("spec anchor Q2 read at F102 y 250 instead of 240", "F102 (y 240, 0.62)", "F102 (y 250, 0.62)", "F_f102_scale"),
    ("spec PH152550 row: O back at 890 px (the r5 slip)", "so opening O = 900 px", "so opening O = 890 px",
     "G_ph152550_ratios"),
    ("spec anchor S1 back at the r5 ratio 1.045 O", "plate centre x 1060 = 1.037 O", "plate centre x 1060 = 1.045 O",
     "G_ph152550_ratios"),
]


def main():
    name, patch, expect, drop, opt, add = BASELINE
    failed, clean = run_model(patch, expect, drop, opt, add)
    print("CLEAN  " if clean else "DIRTY  ", name, "| failed:", failed)
    ok, n = clean, 0
    for name, patch, expect, drop, opt, add in MODEL:
        failed, caught = run_model(patch, expect, drop, opt, add)
        n += 1
        ok &= caught
        print("CAUGHT " if caught else "MISSED ", name, "| failed:", failed)
    for name, edit, expect in OUT_MUTANTS:
        failed, caught = run_out_mutant(edit, expect)
        n += 1
        ok &= caught
        print("CAUGHT " if caught else "MISSED ", name, "| failed:", failed)
    for name, old, new, expect in SPEC:
        failed, caught = run_spec(old, new, expect)
        n += 1
        ok &= caught
        print("CAUGHT " if caught else "MISSED ", name, "| failed:", failed)
    print(f"mutation test housing: clean baseline {'PASS' if clean else 'FAIL'}, {n} planted errors,",
          "ALL CAUGHT" if ok else "SOME MISSED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
