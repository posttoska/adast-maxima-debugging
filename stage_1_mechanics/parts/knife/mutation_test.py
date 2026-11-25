"""Mutation test of check_spec.py: each one-value change of a spec copy must make the checker FAIL
(a mutant flagged 'line' instead deletes the one whole line that starts with its old text, e.g. a source key row).

Copies spec/knife.md to parts/knife/mutants/<name>.md (overwritten each run, never deleted)
and runs check_spec.py --spec <copy> --no-sweep on each (with the sweep for a mutant marked full,
whose check lives in section 8). A mutant counts as caught only when the
checker exits 1 AND a FAIL line contains the mutant's expected text (the check meant to catch it).
Exit 0 = every mutant caught that way.
Run:  python stage_1_mechanics/parts/knife/mutation_test.py
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE.parents[1] / "spec" / "knife.md"
MUTANTS = [  # name, old text, new text (each old text occurs exactly once in the spec), expected FAIL text
    ("geometry_only", "knife x=-660..660 y=-12..0", "knife x=-650..660 y=-12..0", "knife: outer size column"),
    ("outer_size_only", "| X -704..704 Y -92..-12 Z 1069.85..1219.85 |", "| X -704..704 Y -92..-12 Z 1069.85..1229.85 |",
     "holder: outer size column"),
    ("kinematics_stroke", "| stroke | 150 |", "| stroke | 140 |", "rod length"),
    ("anchor_xyz", "| motor.M1 | 1205,455,175 |", "| motor.M1 | 1205,455,185 |", "knife_anchors.json = anchors table"),
    ("worm_mesh", "cyl ax=x c=40,629 d=72 s=875..995 | X 875..995 Y 4..76 Z 593..665",
     "cyl ax=x c=40,629 d=80 s=875..995 | X 875..995 Y 0..80 Z 589..669", "worm meshes"),
    ("long_shaft", "cyl ax=y c=935,795 d=60 s=-27..140 | X 905..965 Y -27..140 Z 765..825",
     "cyl ax=y c=935,795 d=60 s=-27..575 | X 905..965 Y -27..575 Z 765..825", "compact unit"),
    ("guide_offset", "box x=690..719.5 y=-107..-93 z=900..1225 | X 690..719.5 Y -107..-93 Z 900..1225",
     "box x=690..719.5 y=-108..-94 z=900..1225 | X 690..719.5 Y -108..-94 Z 900..1225", "guide_12_right: over the holder"),
    ("crank_axis", "| rot axis=0,-1,0 pivot=935,-52,795 range=0..360; one turn",
     "| rot axis=0,-1,1 pivot=935,-52,795 range=0..360; one turn", "motion crank.centre"),
    ("state_angle", "state of=crank.pin.tdc at=196.39", "state of=crank.pin.tdc at=163.61", "motion crank.pin.bottom"),
    ("passage_box", "fixed passage x=720..760", "fixed passage x=760..800", "motion joint.window.conrod.right_cheek"),
    ("space_xyz", "| space.knife.drive_unit | 962.65,36.5,680 |", "| space.knife.drive_unit | 962.65,36.5,480 |",
     "motion space.knife.drive_unit"),
    ("space_box", "fixed space x=785..1140.3 y=-77..150 z=575..785", "fixed space x=785..1140.3 y=-27..150 z=575..785",
     "only inside space.knife.drive_unit", "full"),
    ("term_missing", "| conrod | connecting rod (шатун), one,", "| conrod | connecting rod, one,",
     "every model row names its Russian or Czech term"),
    ("source_missing", "| P44 (4AP 112 M-4: frame size 112; shaft Ø28 x 60 of that frame size, E) |", "| frame 112 shaft (E) |",
     "every model row cites a key"),
    ("planar_range", " range=32.2..54.6; range = the rod's angle", "; range = the rod's angle", "every moving anchor has a range"),
    ("m_range", "(M1-M16 below;", "(M1-M14 below;", "measure rows M1..M"),
    ("coverage", "flange_2 M4; ", "", "every model row maps to an existing measure row"),
    ("abs_class", "(P23: T ±0,05) | E | 100 |", "(P23: T ±0,05) | T | 0.05 |", "absolute knife-edge Z"),
    ("sq_station", "| sensor.SQ2 | 905,360,912 |", "| sensor.SQ2 | 905,345,912 |", "SQ1, SQ2 within"),
    # round 7 (tester 3 round 2 N1: these passed before; check 9b)
    ("anchor_class", "| motor.M1 | 1205,455,175 | E |", "| motor.M1 | 1205,455,175 | D |", "class, error, source"),
    ("anchor_error", "| sensor.S12 | 1009.05,145,743.84 | E | 100 |", "| sensor.S12 | 1009.05,145,743.84 | E | 10 |", "class, error, source"),
    ("anchor_source", "Honeywell; W568; P40; next to S12", "Honeywell; W568; P30; next to S12", "class, error, source"),
    ("q_removed_S14", "128,97° = TDC (E [?], conflict 7)", "128,97° = TDC (E, conflict 7)", "must stay [?]"),
    ("sq_credited", "which sensor reads which state is not printed (see sensor.SQ1)", "SQ2 reads pin out (P30)",
     "no page credited for the SQ1/SQ2 assignment"),
    ("m2_rod_length", "51,5; 385,8; Ø50", "51,5; 395,8; Ø50", "M2 stroke, crank radius, rod length"),
    ("m4_ratio", "ratio ≈ 10 (9,0 at 1420/min", "ratio ≈ 20 (9,0 at 1420/min", "M4 worm ratio"),
    ("prose_tdc", "crank pin at TDC (902.60, −52, 835.06)", "crank pin at TDC (902.60, −52, 845.06)", "prose 'Derived points'"),
    ("s13_order", "| sensor.S13 | 1019.76,145,764.75 |", "| sensor.S13 | 993.28,145,726.42 |", "sensor.S13 on the vane circle"),
    ("m9_s13", "S13 (1020, 145, 765) at −19,6°", "S13 (993, 145, 726) at −49,6°", "M9: S12, S13, S14"),
    # round 8 (soft critic t2 g13: a deleted key row passed 229/0; check 9c)
    ("drop_key_row", "| P34 | ", "", "has a row in the Sources table", "line"),
    ("orphan_key", "| P36 | OM/20261115_022221.jpg |",
     "| P99 | OM/none.jpg | mutant: a row nothing cites |\n| P36 | OM/20261115_022221.jpg |", "no orphans"),
]


def main():
    text = SPEC.read_text(encoding="utf-8")
    out = HERE / "mutants"
    out.mkdir(exist_ok=True)
    bad = 0
    for name, old, new, want, *flags in MUTANTS:
        if "line" in flags:  # delete the one whole line that starts with old (new unused)
            lines = text.split("\n")
            hits = [i for i, l in enumerate(lines) if l.startswith(old)]
            if len(hits) != 1:
                print(f"SETUP {name}: line found {len(hits)} times, expected 1")
                bad += 1
                continue
            mutated = "\n".join(lines[:hits[0]] + lines[hits[0] + 1:])
        elif text.count(old) != 1:
            print(f"SETUP {name}: text found {text.count(old)} times, expected 1")
            bad += 1
            continue
        else:
            mutated = text.replace(old, new)
        path = out / f"{name}.md"
        path.write_text(mutated, encoding="utf-8")
        args = [sys.executable, str(HERE / "check_spec.py"), "--spec", str(path)] + ([] if "full" in flags else ["--no-sweep"])
        res = subprocess.run(args,
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        fails = [l for l in res.stdout.splitlines() if l.startswith("FAIL ")]
        hit = next((l for l in fails if want in l), None)
        caught = res.returncode == 1 and hit is not None
        bad += not caught
        shown = hit if hit else (fails[0] if fails else "no FAIL line") + f" (expected a FAIL with {want!r})"
        print(f"{'CAUGHT' if caught else 'MISSED'} {name}: exit {res.returncode}, {len(fails)} FAIL; {shown[:180]}")
    print(f"MUTATION TEST {len(MUTANTS) - bad}/{len(MUTANTS)} caught by the intended check: "
          + ("PASS" if bad == 0 else f"FAIL ({bad})"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
