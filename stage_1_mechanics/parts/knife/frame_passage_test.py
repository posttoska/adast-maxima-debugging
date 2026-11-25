"""Frame-passage test of check_spec.py section 8 (knife thread 2).

1. Writes parts/knife/mutants/frame_anchors_with_passages.json = out/frame_anchors.json plus every knife
   anchor that carries a passage box, at the knife's xyz (as the frame would name it), then runs
   check_spec.py --frame-anchors <that copy>. It must exit 0 (ALL PASS): this proves that the passage
   boxes cover every knife-frame contact at rest and over the whole crank turn.
2. Runs check_spec.py on the real out/frame_anchors.json and prints the passages the frame does not
   name yet, and how many FAIL lines remain once they are named (must be 0, from step 1).
Run:  python stage_1_mechanics/parts/knife/frame_passage_test.py      Exit 0 = step 1 passed.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]


def run(extra):
    res = subprocess.run([sys.executable, str(HERE / "check_spec.py")] + extra,
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = res.stdout.splitlines()
    return res.returncode, sum(l.startswith("PASS") for l in lines), [l for l in lines if l.startswith("FAIL ")]


def main():
    frame = json.loads((R / "out" / "frame_anchors.json").read_text(encoding="utf-8"))
    knife = json.loads((R / "out" / "knife_anchors.json").read_text(encoding="utf-8"))["anchors"]
    passages = {n: v for n, v in knife.items() if "passage" in v}
    missing = [n for n in passages if n not in frame["anchors"]]
    for n, v in passages.items():
        frame["anchors"].setdefault(n, {"xyz": v["xyz"], "class": v["class"], "error_mm": v["error_mm"],
                                        "source": "frame_passage_test copy: knife passage named as the frame would"})
    copy = HERE / "mutants" / "frame_anchors_with_passages.json"
    copy.parent.mkdir(exist_ok=True)
    copy.write_text(json.dumps(frame, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    code, npass, fails = run(["--frame-anchors", str(copy)])
    print(f"1. copy with the {len(passages)} passages named: exit {code}, {npass} PASS lines, {len(fails)} FAIL lines")
    for l in fails:
        print("   " + l[:200])
    code2, npass2, fails2 = run([])
    print(f"2. real frame_anchors.json: exit {code2}, {npass2} PASS lines, {len(fails2)} FAIL lines; "
          f"passages not yet named by the frame: {missing or 'none'}")
    print("FRAME PASSAGE TEST " + ("PASS" if code == 0 else "FAIL"))
    return 0 if code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
