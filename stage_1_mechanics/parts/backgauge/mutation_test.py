"""Base run, copy test and mutation test of check_spec.py (backgauge, thread 4).

0. Base run on the real files: check_spec.py with no options must exit 0 with 0 FAIL lines. The two frame
   passages are marked cut_at=assembly (DECISION 2 of the meta orc); out/frame_anchors.json does not name them.
1. Copy test of the frame-named rule: writes parts/backgauge/mutants/frame_anchors_with_passages.json =
   out/frame_anchors.json plus every backgauge anchor that carries a passage box, at the backgauge's xyz (as the
   frame would name it), and runs check_spec.py --frame-anchors <copy> --require-frame-names: 0 FAIL lines.
   Then the same rule on the real frame file must FAIL each passage as not named (the rule is kept, not lost).
2. Mutants: each changes one thing in a copy of spec/backgauge.md (mutants/<name>/backgauge.md), builds it into
   mutants/<name>/out and runs check_spec.py on it against the real frame file. A mutant is caught only if a FAIL
   line with the intended text appears.
Run:  python stage_1_mechanics/parts/backgauge/mutation_test.py      Exit 0 = 0, 1 and all mutants pass.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
SPEC = R / "spec" / "backgauge.md"
MUT = HERE / "mutants"

MUTANTS = [   # name, old text, new text, FAIL text that must appear
    ("s24_off", "| sensor.S24 | -163,378,736.5 |", "| sensor.S24 | -163,384,736.5 |", "FAIL 10 sensor.S24 at its body"),
    ("outer_y", "| y | -725 | 1880 |", "| y | -725 | 1890 |", "FAIL 7 outer size"),
    ("neck_wide", "| neck | neck | moving | box x=-12.5..12.5", "| neck | neck | moving | box x=-25..25", "FAIL 9 neck inside"),
    ("m2_no_source", "| p44 (type), F101 (on the centre line at the apex), 144524 (hangs below the rear table); PL 3.2 (motor drive 577-17.0000) |", "|  |",
     "FAIL 11 each of"),
    ("ext_short", "fixed x=-20..20 y=235..420 z=785..885", "fixed x=-20..20 y=300..420 z=785..885",
     "FAIL 9 collision neck x frame.table"),
    ("s27_into_stand", "| S27 | S27 | fixed | box x=-178.5..-147.5 y=1377..1407", "| S27 | S27 | fixed | box x=-178.5..-147.5 y=1360..1390",
     "FAIL 9 collision S27 x frame.rear_stand"),
    ("trips_s24_inside", "fixed trips_at_face_y=20 trips_range=15..25", "fixed trips_at_face_y=30 trips_range=25..35",
     "FAIL 10 sensor.S24 trips"),
    ("trips_s27_inside", "fixed trips_at_face_y=1155 trips_range=1150..1160", "fixed trips_at_face_y=1139 trips_range=1135..1145",
     "FAIL 10 sensor.S27 trips"),
    ("travel_prose", "Face Y 25 (front end) .. 1150 (rear end)", "Face Y 25 (front end) .. 1250 (rear end)",
     "FAIL 11 travel line of the prose"),
    ("space_unlisted", "| carriage, nut | keepout, corridor.base_cavity_centre |", "| carriage, nut | keepout |",
     "FAIL 12 bodies leaving frame.keepout"),
    ("pusher_wide_rear", "34.74,1670;-34.74,1670", "300,1670;-300,1670", "FAIL 9 bodies above the table"),
    ("journal_unnamed", "| spindle front journal Ø and length;", "| spindle front end Ø and length;",
     "FAIL 11 each map component is named"),
    ("comp_cell_x", "| X −550..550, Y f..f+60, Z 886..991 |", "| X −600..600, Y f..f+60, Z 886..991 |",
     "FAIL 7b Components positions"),
    # check 7b beyond the ranges (critic t4 g11 on r6): single values, segments, relations, every number checked
    ("m2_centre_x", "| X 0, Z 530, Y 1565..1795 |", "| X 80, Z 530, Y 1565..1795 |",
     "FAIL 7b Components single values"),
    ("guides_rib_z", "ribs X ±(66..92), Z 738..784;", "ribs X ±(66..92), Z 740..784;", "FAIL 7b Components segments"),
    ("gear_left_of_knob", "(centre 205 left of the knob centre)", "(centre 215 left of the knob centre)",
     "FAIL 7b Components relations"),
    ("cell_unchecked_number", "(centred on the nut)", "(centred on the nut, 430 long)", "FAIL 7b Components numbers"),
    # DECISION 2 rule: a passage counts only when marked, in the frame body it names, shaped as written, and used
    ("bore_unmarked", "axis=0,1,0 cut_at=assembly cut_from=frame.base_front", "axis=0,1,0 cut_from=frame.base_front",
     "FAIL 8 passage joint.bore.spindle.base_front: not named by the frame and not marked"),
    ("bore_narrow", "bore_d=30 axis=0,1,0", "bore_d=20 axis=0,1,0", "FAIL 9 collision journal x frame.base_front"),
    ("ext_wrong_body", "cut_at=assembly cut_from=frame.table", "cut_at=assembly cut_from=frame.base_front",
     "FAIL 8 passage joint.slot.front_extension:"),
    ("ext_aside", "fixed x=-20..20 y=235..420 z=785..885", "fixed x=100..140 y=235..420 z=785..885",
     "FAIL 9 passage joint.slot.front_extension (cut at assembly, DECISION 2) is used"),
]


# 3. the shared-name rule of check 10 on a copy of the other parts' anchors files (the real files are never touched):
#    the copy of clamp_anchors.json gets (a) the joint moved 5 mm, (b) sensor.S24 at the backgauge's own point
def _moved(a, mine):
    p = dict(mine["interface.clamp.comb_interleave"])
    p["xyz"] = [p["xyz"][0], p["xyz"][1] + 5, p["xyz"][2]]
    a["interface.clamp.comb_interleave"] = p


def _device(a, mine):
    a["sensor.S24"] = dict(mine["sensor.S24"])


PARTS_MUTANTS = [("shared_moved_5mm", _moved), ("shared_device_S24", _device)]
PARTS_WANT = "FAIL 10 names shared with other parts"


def run(extra):
    res = subprocess.run([sys.executable, str(HERE / "check_spec.py")] + extra,
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = res.stdout.splitlines()
    return res.returncode, [l for l in lines if l.startswith("PASS")], [l for l in lines if l.startswith("FAIL ")], res.stderr


def show(fs):
    for l in fs:
        print("   " + l[:220])


def main():
    MUT.mkdir(exist_ok=True)
    code, ps, fs, err = run([])
    ok0 = code == 0 and not fs
    print(f"0. real files (passages marked cut at assembly, DECISION 2): exit {code}, {len(ps)} PASS lines, "
          f"{len(fs)} FAIL lines" + ("" if ok0 or fs else f"; stderr {err.strip()[-200:]}"))
    show(fs)

    frame = json.loads((R / "out" / "frame_anchors.json").read_text(encoding="utf-8"))
    mine = json.loads((R / "out" / "backgauge_anchors.json").read_text(encoding="utf-8"))["anchors"]
    passages = {n: v for n, v in mine.items() if "passage" in v}
    missing = [n for n in passages if n not in frame["anchors"]]
    for n, v in passages.items():
        frame["anchors"].setdefault(n, {"xyz": v["xyz"], "class": v["class"], "error_mm": v["error_mm"],
                                        "passage": v["passage"],
                                        "source": "mutation_test copy: backgauge passage named as the frame would"})
    copy = MUT / "frame_anchors_with_passages.json"
    copy.write_text(json.dumps(frame, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    code, ps, fs, err = run(["--frame-anchors", str(copy), "--require-frame-names"])
    ok1 = code == 0 and not fs
    print(f"1. copy with the {len(passages)} passages named, --require-frame-names: exit {code}, {len(ps)} PASS lines, "
          f"{len(fs)} FAIL lines; passages not named by the real frame file: {missing or 'none'}")
    show(fs)
    code, ps, fs, err = run(["--require-frame-names"])
    want = [f"FAIL 8 passage {n} named in frame_anchors.json" for n in missing]
    got = [w for w in want if any(l.startswith(w) for l in fs)]
    ok1b = code != 0 and len(got) == len(want)
    print(f"1b. real frame file, --require-frame-names: exit {code}, {len(fs)} FAIL lines, "
          f"{len(got)}/{len(want)} unnamed passages failed as not named ({'kept' if ok1b else 'LOST'})")

    text = SPEC.read_text(encoding="utf-8")
    caught = 0
    for name, old, new, want in MUTANTS:
        if text.count(old) != 1:
            print(f"2. {name}: old text found {text.count(old)} times - mutant not applied (counts as missed)")
            continue
        d = MUT / name
        (d / "out").mkdir(parents=True, exist_ok=True)
        (d / "backgauge.md").write_text(text.replace(old, new), encoding="utf-8")
        code, ps, fs, err = run(["--spec", str(d / "backgauge.md"), "--out", str(d / "out")])
        hit = any(l.startswith(want) for l in fs)
        caught += hit
        print(f"2. {name}: {'caught' if hit else 'MISSED'} (exit {code}, {len(fs)} FAIL lines; wanted '{want}')"
              + ("" if hit else f"; stderr {err.strip()[-200:]}"))
    ok2 = caught == len(MUTANTS)
    pcaught = 0
    for name, edit in PARTS_MUTANTS:
        d = MUT / name / "parts"
        d.mkdir(parents=True, exist_ok=True)
        for f in d.glob("*_anchors.json"):
            f.unlink()
        for f in (R / "out").glob("*_anchors.json"):
            if f.name != "backgauge_anchors.json":
                (d / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
        cp = d / "clamp_anchors.json"
        data = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {"anchors": {}}
        edit(data["anchors"], mine)
        cp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        code, ps, fs, err = run(["--parts-dir", str(d)])
        hit = any(l.startswith(PARTS_WANT) for l in fs)
        pcaught += hit
        print(f"3. {name}: {'caught' if hit else 'MISSED'} (exit {code}, {len(fs)} FAIL lines; wanted '{PARTS_WANT}')"
              + ("" if hit else f"; stderr {err.strip()[-200:]}"))
        show([l for l in fs if l.startswith(PARTS_WANT)])
    ok3 = pcaught == len(PARTS_MUTANTS)
    ok = ok0 and ok1 and ok1b and ok2 and ok3
    print(f"MUTATION TEST {'PASS' if ok else 'FAIL'} (base {'0 FAIL' if ok0 else 'FAIL'}, copy test "
          f"{'0 FAIL' if ok1 else 'FAIL'}, frame-named rule {'kept' if ok1b else 'LOST'}, "
          f"{caught}/{len(MUTANTS)} spec mutants caught, {pcaught}/{len(PARTS_MUTANTS)} parts-copy mutants caught)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
