"""Mutation test of the clamp checks (thread 3): each mutant breaks the spec in one way, is rebuilt into
parts/clamp/mutants/<name>/out and checked; a mutant is caught when check_spec.py exits 1.
Run: python stage_1_mechanics/parts/clamp/mutation_test.py  -> MUTANTS caught n/N (N = len(MUTANTS)), exit 0 when all are caught.
Round 2 added S28/S30 placement mutants (F1) and source-number mutants (F2, F6); round 3 F101 places, stale
outputs and prose sizes; round 4 position prose, an anchor off its body, the pedal-link rise and the data dwell;
round 5 height, rack side, F71 reading, mirrored prose, knob length, M3; round 6 gear 8's turn sense, axis, turn and pivot
(tester 2 r3, critic g9) and the spec's mutant count.
The real R/out is never touched. Files in mutants/ are overwritten on each run (nothing is deleted).
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE.parents[1] / "spec" / "clamp.md"

# name: (old text, new text, check against the original spec instead of the mutated one)
MUTANTS = {
    "body_moved": ("box x=-690..690 y=2..150 z=1155..1255", "box x=-700..700 y=2..150 z=1155..1255", False),
    "finger_on_backgauge_finger": ("fingers x0=-527.8", "fingers x0=-546", False),
    "tank_into_knife_space": ("box x=735..1130 y=-70..145 z=30..470", "box x=735..1130 y=-70..145 z=30..600", False),
    "anchor_dropped": ("| sensor.S30 |", "| sensor.S30_gone |", False),
    "bbox_drift": ("box x=-575..575 y=2..24 z=1021..1155", "box x=-575..575 y=2..24 z=1021..1165", True),
    "motor_M1_doubled": ("| pump.OP1 |", "| motor.M1 |", False),
    "passage_dropped": ("| joint.passage.clamp_brake.crossbar |", "| note.no_passage |", False),
    "pedal_into_corridor": ("box x=-150..150 y=-611..-571 z=60..80", "box x=-150..150 y=-611..-571 z=690..710", False),
    # round 2, F1: S28 away from the false plate, S30 below the bar's top edge
    "S28_off_plate": ("| sensor.S28 | -490,13,1021 |", "| sensor.S28 | -490,150,1205 |", False),
    "S30_low": ("| sensor.S30 | 280,150,1250 |", "| sensor.S30 | 280,150,1205 |", False),
    # round 2, F2 and F6: numbers printed in HC, P11 and HL
    "oa1_bore_90": ("d=100 di=70", "d=100 di=90", False),
    "rod_40": ("d=25 s=250..420", "d=40 s=250..420", False),
    "knob3_60": ("c=937,1244 d=40", "c=937,1244 d=60", False),
    "tube_short": ("di=70 s=400..750", "di=70 s=400..520", False),
    "pedal_200": ("box x=-150..150 y=-611..-571 z=60..80", "box x=-100..100 y=-611..-571 z=60..80", False),
    "gauge_100": ("c=937,1377 d=60", "c=937,1377 d=100", False),
    # r3 (tester 3, critic g5): F101 places, stale outputs, prose read-back
    "panel_back_1127": ("cyl ax=y c=937,1377 d=60", "cyl ax=y c=1127,1430 d=60", False),
    "ov2_back_420": ("box x=241..401 y=270..370 z=390..510", "box x=340..500 y=270..370 z=390..510", False),
    "anchor_changed_no_rebuild": ("| tank.OZ1 | 932.5,37.5,250 | T/E | 60 |", "| tank.OZ1 | 932.5,37.5,250 | T/E | 70 |", True),
    "prose_lift_150": ("+ lift 130 | down 130 |", "+ lift 130 | down 150 |", False),
    "prose_bore_90": ("tube Ø100 / bore Ø70 x 350", "tube Ø100 / bore Ø90 x 350", False),
    # r4 (critics g5 and g6, H1-H3): position prose, anchor on its body, envelope chain, data dwell
    "pos_gauge_1127": ("| X 937, Z 1377, on column_right", "| X 1127, Z 1377, on column_right", False),
    "pos_ov2_420": ("X 241..401 (centre 321)", "X 340..500 (centre 420)", False),
    "anchor_gauge_off_body": ("| gauge.OZ13 | 937,-434,1377 |", "| gauge.OZ13 | 1127,-434,1377 |", False),
    "pedal_rise_short": ("x=241..401 y=270..370 z=150..390", "x=241..401 y=270..370 z=150..300", False),
    "dwell_back_3s": ("dwell 0-2,5 s (timer KT2", "dwell 0-3 s (timer KT2", False),
    # r5 (critics g7 and g8 G7-1, critic g6's survivor, tester 2 check 4): height, rack mesh and side, F71 reading,
    # one-sided prose of a mirrored body, knob length, OA1 sizes on M3
    "r5_rack_top_1625": ("box x=-60..-40 y=80..120 z=1255..1535", "box x=-60..-40 y=80..120 z=1255..1625", True),
    "r5_rack_head_1490": ("box x=-60..-40 y=80..120 z=1255..1535", "box x=-60..-40 y=80..120 z=1255..1490", True),
    "r5_rack_plus_x": ("box x=-60..-40 y=80..120 z=1255..1535", "box x=40..60 y=80..120 z=1255..1535", True),
    "r5_y14_at_1475": ("cyl ax=y c=0,1380 d=160", "cyl ax=y c=0,1475 d=160", True),
    "r5_f71_reading_1475": ("pinion centre is at Z ≈ 1380", "pinion centre is at Z ≈ 1475", False),
    "g6_prose_guides_minus_only": ("| X ±690..±720, Y 50..150, Z 1000..1280 | fixed |",
                                   "| X −720..−690, Y 50..150, Z 1000..1280 | fixed |", False),
    "r5_knob3_25_long": ("cyl ax=y c=937,1244 d=40 s=-464..-394", "cyl ax=y c=937,1244 d=40 s=-419..-394", True),
    "r5_m3_no_oa1_outer": ("; OA1 outer Ø ±20, length ±100; piston length ±15;", "; piston length ±15;", False),
    "r5_knob_err_10": ("knob length ±30 (covers", "knob length ±10 (covers", False),
    # r6 (tester 2 r3 check 7, critic g9): gear 8's turn sense, its axis in all places, its turn and pivot; the count
    "r6_gear_turns_plus_y": ("rot axis=0,-1,0 pivot=0,100,1380 range=0..186.2",
                             "rot axis=0,1,0 pivot=0,100,1380 range=0..186.2", False),
    "r6_gear_range_negative": ("pivot=0,100,1380 range=0..186.2", "pivot=0,100,1380 range=0..-186.2", False),
    "r6_groups_line_plus_y": ("gear = turns about (0, −1, 0)", "gear = turns about (0, 1, 0)", False),
    "r6_gear_range_150": ("pivot=0,100,1380 range=0..186.2", "pivot=0,100,1380 range=0..150", False),
    "r6_gear_pivot_off_centre": ("pivot=0,100,1380 range=0..186.2", "pivot=0,100,1475 range=0..186.2", False),
    "r6_count_back_26": ("makes 41 broken copies", "makes 26 broken copies", False),
}


def main():
    base = SPEC.read_text(encoding="utf-8")
    caught = 0
    for name, (old, new, against_original) in MUTANTS.items():
        if base.count(old) != 1:
            print(f"NOT APPLIED {name}: text found {base.count(old)} times")
            continue
        d = HERE / "mutants" / name
        (d / "out").mkdir(parents=True, exist_ok=True)
        spec = d / "clamp.md"
        spec.write_text(base.replace(old, new), encoding="utf-8")
        if new.startswith("| note.no_passage"):        # a passage row without its passage keyword
            spec.write_text(spec.read_text(encoding="utf-8").replace(
                "fixed passage x=-70..45 y=70..150 z=1415..1535 cut_at=assembly cut_from=frame.crossbar;", "fixed;"),
                encoding="utf-8")
        b = subprocess.run([sys.executable, str(HERE / "clamp.py"), "--spec", str(spec), "--out", str(d / "out")],
                           capture_output=True, text=True)
        chk_spec = SPEC if against_original else spec
        c = subprocess.run([sys.executable, str(HERE / "check_spec.py"), "--spec", str(chk_spec), "--out", str(d / "out")],
                           capture_output=True, text=True)
        (d / "check.log").write_text(c.stdout + c.stderr, encoding="utf-8")
        fl = [ln for ln in c.stdout.splitlines() if ln.startswith("FAIL ") and not ln.startswith("FAIL 1:")]
        ok = b.returncode == 0 and c.returncode == 1
        caught += ok
        print(("CAUGHT " if ok else "MISSED ") + f"{name}: build {b.returncode}, check {c.returncode}; "
              + (fl[0][:150] if fl else "no FAIL line"))
    print(f"MUTANTS caught {caught}/{len(MUTANTS)}")
    return 0 if caught == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
