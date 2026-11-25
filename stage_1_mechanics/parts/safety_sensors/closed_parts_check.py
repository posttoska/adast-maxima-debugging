"""Section 04 check 30 of the t6 checklist: do the five closed parts' own checks still pass with this part's
outputs in out/?  Copies stage_1_mechanics twice into parts/safety_sensors/closed_checks_copy/ (files
overwritten on every run, nothing deleted but this part's three output files in the 'without' copy), runs
frame, knife, clamp, backgauge and housing check_spec.py in each copy, and prints both exit codes.
Run:  python stage_1_mechanics/parts/safety_sensors/closed_parts_check.py   (a few minutes)
Expected: five lines "with t6 exit 0 | without exit 0 | same FAIL lines: True"."""
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]
TMP = Path(__file__).resolve().parent / "closed_checks_copy"
MINE = ("safety_sensors.glb", "safety_sensors.stl", "safety_sensors_anchors.json")
res = {}
for label in ("with_t6", "without_t6"):
    dst = TMP / label / "stage_1_mechanics"
    shutil.copytree(SRC, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("mutants", "renders", "__pycache__", "closed_checks_copy"))
    if label == "without_t6":
        for f in MINE:
            p = dst / "out" / f
            if p.exists():
                p.unlink()
    for part in ("frame", "knife", "clamp", "backgauge", "housing"):
        r = subprocess.run([sys.executable, str(dst / "parts" / part / "check_spec.py")], capture_output=True,
                           text=True, cwd=str(dst.parent))
        lines = (r.stdout + r.stderr).splitlines()
        fails = [ln[:150] for ln in lines if "FAIL" in ln and "ALL PASS" not in ln]
        res[(label, part)] = (r.returncode, fails, lines[-1][:120] if lines else "")
for part in ("frame", "knife", "clamp", "backgauge", "housing"):
    a, b = res[("with_t6", part)], res[("without_t6", part)]
    print(f"{part}: with t6 exit {a[0]} | without exit {b[0]} | same FAIL lines: {a[1] == b[1]} | last: {a[2]}")
    for ln in a[1][:6]:
        print("   with:", ln)
    if a[1] != b[1]:
        for ln in b[1][:6]:
            print("   without:", ln)
