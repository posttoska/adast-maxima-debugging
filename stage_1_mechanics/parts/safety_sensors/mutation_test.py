"""Mutation test of check_spec.py (thread 6): planted errors that the check must catch.

Each mutant is a copy of out/ and of the spec in parts/safety_sensors/mutants/<name>/ (overwritten on every
run, never deleted), changed in one place, optionally rebuilt, then checked.  Expected: the base copy
passes, every mutant fails on the named check, and the 'follow' mutant (host anchor moved, then rebuilt)
passes with its body moved by the same amount.
Run:  python stage_1_mechanics/parts/safety_sensors/mutation_test.py   (a few minutes; log it to a file)
Last line: mutation_test safety_sensors: PASS (n/n caught, follow ok)
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
SPEC = R / "spec" / "safety_sensors.md"
PY = sys.executable


def copy(name):
    d = HERE / "mutants" / name
    (d / "out").mkdir(parents=True, exist_ok=True)
    for f in (R / "out").iterdir():
        if f.is_file():
            shutil.copyfile(f, d / "out" / f.name)
    shutil.copyfile(SPEC, d / "spec.md")
    return d


def edit_text(path, old, new):
    s = path.read_text(encoding="utf-8")
    assert s.count(old) == 1, (path, old)
    path.write_text(s.replace(old, new), encoding="utf-8")


def edit_json(path, fn):
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")


def run(d, rebuild):
    if rebuild:
        subprocess.run([PY, str(HERE / "safety_sensors.py"), "--spec", str(d / "spec.md"), "--out", str(d / "out"),
                        "--anchors-dir", str(d / "out")], capture_output=True, text=True, check=True)
    r = subprocess.run([PY, str(HERE / "check_spec.py"), "--out", str(d / "out"), "--spec", str(d / "spec.md")],
                       capture_output=True, text=True)
    return r.returncode, [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL")]


def move_s1(doc):
    doc["anchors"]["button.S1"]["xyz"][0] += 50.0


MUTANTS = [  # name, change, rebuild, the check that must fail
    ("moved_anchor_no_rebuild", lambda d: edit_json(d / "out" / "housing_anchors.json", move_s1), False, "A7"),
    ("wrong_size_no_rebuild", lambda d: edit_text(d / "spec.md", "| S10 | S10 | button.S10 | cyl ax=y d=30",
                                                  "| S10 | S10 | button.S10 | cyl ax=y d=40"), False, "A7"),
    ("doubled_device_anchor", lambda d: edit_json(d / "out" / "safety_sensors_anchors.json",
                                                  lambda j: j["anchors"].update({"sensor.S28": j["anchors"]["body.S28"]})),
     False, "C10"),
    ("device_name_published", lambda d: edit_json(d / "out" / "safety_sensors_anchors.json",
                                                  lambda j: j["anchors"].update({"button.S10": j["anchors"].pop("body.S10")})),
     False, "C10"),
    ("S30_into_the_bar", lambda d: edit_text(d / "spec.md", "box x=-15.5..15.5 y=0.5..95.5 z=-15..15",
                                             "box x=-15.5..15.5 y=-5..95.5 z=-15..15"), True, "D8"),
    ("Y3_into_keepout", lambda d: edit_text(d / "spec.md", "box x=-25..25 y=-25..25 z=-56..34",
                                            "box x=-25..25 y=-25..25 z=-45..45"), True, "E9"),
    ("S28_out_of_zone", lambda d: edit_text(d / "spec.md", "box x=-15.5..15.5 y=-11..11 z=0..80",
                                            "box x=-15.5..15.5 y=-11..11 z=0..120"), True, "D the excused"),
    ("S13_back_on_anchor", lambda d: edit_text(d / "spec.md", "box x=-24.5..24.5 y=5..30 z=21..39",
                                               "box x=-24.5..24.5 y=5..30 z=-9..9"), True, "D8"),
    ("measure_row_dropped", lambda d: edit_text(d / "spec.md", "| SS7 | M3 blower:", "| SS7 | blower:"), False, "G11"),
    ("measure_row_dropped_host_cited", lambda d: (  # M3's row gone while SS9 cites the housing's rows M12, M3
        edit_text(d / "spec.md", "| SS7 | M3 blower:", "| SS7 | blower:"),
        edit_text(d / "spec.md", "(named in How this part is built, orientation)",
                  "(named in How this part is built, orientation; the S1 console in housing M12, M3)")), False, "G11"),
    ("measure_row_dropped_host_rows_and", lambda d: (  # the same, cited as "housing rows M12 and M3"
        edit_text(d / "spec.md", "| SS7 | M3 blower:", "| SS7 | blower:"),
        edit_text(d / "spec.md", "(named in How this part is built, orientation)",
                  "(named in How this part is built, orientation; housing rows M12 and M3)")), False, "G11"),
    ("S5_off_the_cover", lambda d: (edit_text(d / "spec.md", "box x=109..140 y=-15..15", "box x=100..131 y=-15..15"),
                                    edit_text(d / "spec.md", "at=140,0,0 dir=+x", "at=131,0,0 dir=+x")), True, "F S30"),
]


def main():
    log = []
    base = copy("base")
    code, fails = run(base, rebuild=True)
    log.append(f"base: exit {code} {fails or 'ALL PASS'}")
    caught = 0
    for name, change, rebuild, must in MUTANTS:
        d = copy(name)
        change(d)
        code, fails = run(d, rebuild)
        hit = code != 0 and any(f[5:].startswith(must) for f in fails)
        caught += hit
        log.append(f"{name}: {'caught' if hit else 'NOT CAUGHT'} by {must} (exit {code}; {[f[:60] for f in fails]})")
    d = copy("follow_moved_anchor")
    edit_json(d / "out" / "housing_anchors.json", move_s1)
    code, fails = run(d, rebuild=True)
    b0 = trimesh.load(R / "out" / "safety_sensors.glb", force="scene").geometry["safety_sensors.S1"].bounds
    b1 = trimesh.load(d / "out" / "safety_sensors.glb", force="scene").geometry["safety_sensors.S1"].bounds
    follow = code == 0 and np.allclose(b1 - b0, [[50, 0, 0], [50, 0, 0]], atol=0.01)
    log.append(f"follow_moved_anchor: exit {code}, S1 moved by {np.round((b1 - b0)[0], 2).tolist()} -> "
               f"{'ok' if follow else 'BAD'}")
    print("\n".join(log))
    good = run(base, False)[0] == 0 and caught == len(MUTANTS) and follow
    print(f"mutation_test safety_sensors: {'PASS' if good else 'FAIL'} ({caught}/{len(MUTANTS)} caught, "
          f"follow {'ok' if follow else 'BAD'})")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
