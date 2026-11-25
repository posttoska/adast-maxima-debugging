"""Mutation test of check_spec.py: one changed value per spec copy must FAIL with its MISMATCH line;
the unchanged copy must PASS. This shows that check_spec.py takes its expected values from the spec text.
Run:  python mutation_test.py   (after frame.py; each copy is written over one file, frame_spec_mutation.md,
in a new folder of its own in the system temp folder, so two runs at once do not meet; all results go to mutation_test.log next to this file, and its last
line, MUTATION TEST PASS or FAIL, is printed; exit code 1 on FAIL)"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE.parent.parent / "spec" / "frame.md"
CHECK = str(HERE / "check_spec.py")
COPY = Path(tempfile.mkdtemp(prefix="frame_mutation_")) / "frame_spec_mutation.md"   # own folder per run
base = SPEC.read_text(encoding="utf-8")

M = [  # name, old (must occur once), new, expected
    ("control (unchanged)", None, None, "PASS"),
    ("1 table row front Y -729 -> -700", "Y −729…+1901; top Z 885", "Y −700…+1901; top Z 885", "FAIL"),
    ("2 anchor_bolt.left_front Y -214 -> -200", "anchor_bolt.left_front (−790, −214, 0)",
     "anchor_bolt.left_front (−790, −200, 0)", "FAIL"),
    ("3 right foot area 1460 -> 1400 cm2", "right foot 1460 cm², left foot", "right foot 1400 cm², left foot", "FAIL"),
    ("4 taper start +1334 -> +1300", "taper Y +1334…+1806", "taper Y +1300…+1806", "FAIL"),
    ("5 anchor joint.crossbar.underside deleted",
     " joint.crossbar.underside (0, 0, 1415), ±50, spanning X −720…+720, Y −150…+150.", "", "FAIL"),
    ("6 slot rear end +1860 -> +1800", "X −20…+20; Y +420…+1860 |", "X −20…+20; Y +420…+1800 |", "FAIL"),
    ("7 keep-out top Z 785 -> 800", "frame.keepout.backgauge_drive box X −100…+100, Y +236…+1901, Z 635…785",
     "frame.keepout.backgauge_drive box X −100…+100, Y +236…+1901, Z 635…800", "FAIL"),
    ("8 rear_stand outer Z 765 -> 800", "| 292,5 x 322,5 x 765 |", "| 292,5 x 322,5 x 800 |", "FAIL"),
    ("9 derived bbox Z top 1535 -> 1500", "Z 0…1535 (lifting eyes excluded)", "Z 0…1500 (lifting eyes excluded)", "FAIL"),
    # 10-12: the side-table chamfer corners lie inside the plates' bounding boxes, so only the section
    # check (check_plate_sections) can catch them (critic finding E)
    ("10 side_table_right chamfer corner Y -711 -> -650", "(+575, −711), Z 860…885", "(+575, −650), Z 860…885", "FAIL"),
    ("11 side_table_right chamfer corner X +673 -> +800", "plate corners (+673, −894)", "plate corners (+800, −894)", "FAIL"),
    ("12 side_table_left chamfer corner X -673 -> -700", "(−673, −894), Z 860…885", "(−700, −894), Z 860…885", "FAIL"),
    ("13 anchor joint.window.conrod.right_cheek Z 990 -> 900", "joint.window.conrod.right_cheek (+740, −52, 990)",
     "joint.window.conrod.right_cheek (+740, −52, 900)", "FAIL"),
]
out, all_ok = [], True
for i, (name, old, new, exp) in enumerate(M):
    t = base
    if old is not None:
        n = t.count(old)
        if n != 1:
            out.append(f"[{name}] SETUP ERROR: old text occurs {n} times")
            all_ok = False
            continue
        t = t.replace(old, new)
    cp = COPY
    cp.write_text(t, encoding="utf-8")
    r = subprocess.run([sys.executable, CHECK, "--spec", str(cp)], capture_output=True, text=True, encoding="utf-8")
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    got = "PASS" if (r.returncode == 0 and lines and lines[-1].endswith("PASS")) else "FAIL"
    ok = got == exp
    all_ok &= ok
    out.append(f"[{name}] expected {exp}, got {got} (exit {r.returncode}) -> {'OK' if ok else 'WRONG'}")
    out += ["    " + ln for ln in lines if ln.startswith("MISMATCH")][:4]
    out.append("    " + (lines[-1] if lines else "(no output) " + r.stderr[-300:]))
out.append("MUTATION TEST " + ("PASS" if all_ok else "FAIL") + f" ({len(M)} cases)")
(HERE / "mutation_test.log").write_text("\n".join(out) + "\n", encoding="utf-8")
print(out[-1])
sys.exit(0 if all_ok else 1)
