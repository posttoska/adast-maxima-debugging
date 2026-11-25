"""Placement probe for the safety_sensors bodies (thread 6) - an analysis helper, not a builder.

For each body of spec/safety_sensors.md it tests the solid written in the spec at offset 0 against the
obstacles of hosts.obstacles(): every host body at rest, the sweep of every moving host body over its whole
motion (hosts.SWEEPS, motions read from the hosts' anchors) and the hosts' keep-out boxes, plus the bodies
of this part placed before it.  When the solid hits one, it searches 26 directions (the axes, face and
space diagonals) in --step mm rings up to --radius mm (no direction limit) for the nearest offset that hits nothing and prints it.  The output is
advice only: each offset taken into the spec is written there with its direction and reason and folded
into the row's error.  The builder and check_spec.py never call it.
Run:  python stage_1_mechanics/parts/safety_sensors/place_probe.py [--step 2.5] [--radius 160] [name ...]
"""
import itertools
import sys

import numpy as np
import manifold3d as mf

import hosts
import safety_sensors as ss


def main(argv):
    step = float(argv[argv.index("--step") + 1]) if "--step" in argv else 2.5
    radius = float(argv[argv.index("--radius") + 1]) if "--radius" in argv else 160.0
    only = [a for a in argv if not a.startswith("--") and not a.replace(".", "").isdigit()]
    rows = ss.read_spec()
    anchors = hosts.load_anchors()
    hm = hosts.obstacles()
    for row in rows:
        if only and row["id"] not in only:
            continue
        base = ss.build_row(row, anchors)
        skip = set(row["excused"])
        hit0 = hosts.clash(base, hm, skip)
        line = f"{row['id']:4s} offset 0: " + (", ".join(f"{n} {v:.0f}" for n, v in hit0.items()) or "free")
        if hit0:
            dirs = [np.array(d, float) / np.linalg.norm(d) for d in itertools.product((-1, 0, 1), repeat=3) if any(d)]
            cand = [r * d for r in np.arange(step, radius + step / 2, step) for d in dirs]
            best = None
            for o in cand:
                m = base.translate([float(v) for v in o])
                if not hosts.clash(m, hm, skip):
                    best = o
                    break
            line += f" | nearest free offset {None if best is None else [round(v, 1) for v in best]}"
        print(line, flush=True)
        hm["own:" + row["id"]] = base if not hit0 or best is None else base.translate([float(v) for v in best])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
