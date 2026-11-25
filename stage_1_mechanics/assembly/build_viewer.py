"""Offline viewer of the assembled Adast Maxima MS 115 PS model: writes R/viewer/index.html.

One self-contained file: its own WebGL (Web Graphics Library) code from assembly/viewer_template.html, no library, no
network, and no fetch of a separate model file (browsers block that for pages opened from disk). The meshes are the
assembly's bodies after the DECISION 2 passages are cut (the solids the checks used), inlined as base64 float32
vertices and uint32 triangles. The knife's crank turn is precomputed with assembly.py's motion model (one pose per
degree), so the viewer moves the knife bodies exactly as check 9 does; the clamp and backgauge bodies move along the
motion axes the parts publish (clamp.face, backgauge.face), as clamp_tf and bg_tf do.

Called by assembly.py after the checks; it adds its own line V to the report. Units mm, Z up, as the parts.
"""
import base64
import json
import math
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "viewer_template.html"
DEVICE_KINDS = ("button", "sensor", "magnet", "clutch", "valve", "brake", "motor", "switch")
STEPS = 360
# what a page could load from elsewhere; none of it may appear in the written file
NET = re.compile(r"://|\bfetch\s*\(|XMLHttpRequest|<link\b|<img\b|<iframe\b|\bsrc\s*=|@import|url\(|import\s*\(", re.I)


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode("ascii")


def rnd(v, k=2):
    return [round(float(x), k) for x in v]


def slim(a, limit=700):
    """an anchor dict for the info panel: every key but xyz, long values cut"""
    out = {}
    for k, v in a.items():
        if k == "xyz":
            continue
        s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        out[k] = s if len(s) <= limit else s[:limit] + " ..."
    return out


def build(root, mans, part_of, anchors_all, meta, mm, cut_names=(), colors=None, report=None, checks=None,
          open_items=None, inputs=None, out_path=None, legend=None):
    root = Path(root)
    out_path = Path(out_path) if out_path else root / "viewer" / "index.html"
    colors = colors or {}

    # ---- bodies, in load order (parts in assembly.PARTS order, bodies in their GLB order)
    bodies, parts, ntri, rest_box = [], {}, 0, {}
    for n, m in mans.items():
        me = m.to_mesh()
        v = np.asarray(me.vert_properties, np.float32)[:, :3]
        f = np.asarray(me.tri_verts, np.uint32).reshape(-1)
        c = list(colors.get(n, [180, 180, 180, 255])) + [255]
        p = part_of[n]
        bodies.append({"n": n, "p": p, "c": [int(x) for x in c[:3]], "a": int(c[3]), "cut": n in cut_names,
                       "v": b64(v), "f": b64(f)})
        rest_box[n] = (v.min(axis=0).astype(float), v.max(axis=0).astype(float))
        ntri += len(f) // 3
        q = parts.setdefault(p, {"name": p, "bodies": 0, "color": [int(x) for x in c[:3]]})
        q["bodies"] += 1

    # ---- anchors of all parts and of the assembly (the passages)
    anchors, src = [], {}
    for p, an in anchors_all.items():
        for n, a in an.items():
            if isinstance(a, dict) and isinstance(a.get("xyz"), (list, tuple)) and len(a["xyz"]) == 3:
                k = n.split(".", 1)[0]
                anchors.append({"n": n, "p": p, "x": rnd(a["xyz"]), "dev": k in DEVICE_KINDS or k == "cabinet",
                                "i": slim(a)})
                src[(p, n)] = a
    ndev = sum(1 for a in anchors if a["dev"])

    # ---- motions: the knife from the motion model, one pose per degree; clamp and backgauge along their axes
    K = mm["knife"]
    tf0, _ = K["pose"](K["th0"])
    kb = [b for b in tf0 if b in mans]
    T = np.zeros((STEPS, len(kb), 12), np.float32)
    dz = []
    for i in range(STEPS):
        tf, d = K["pose"](K["th0"] + 2 * math.pi * i / STEPS)
        for j, b in enumerate(kb):
            T[i, j] = np.asarray(tf[b], float).reshape(12)
        dz.append(round(float(d), 3))
    ka = anchors_all.get("knife", {})
    edge = ka.get("knife.edge.rest", {}).get("xyz") if isinstance(ka.get("knife.edge.rest"), dict) else None
    C, G = mm["clamp"], mm["backgauge"]
    # ---- carried anchors (critic F8): an anchor that publishes a motion moves with the moving body of the page that holds
    # it (rest box +-1 mm, the smallest such box); a rotation anchor on its own axis stays; one no slider moves stays
    movers = list(kb) + list(C["beam"]) + list(C["riders"]) + list(C["piston"]) + list(G["moving"])
    still_axis, still_none = [], []
    for e in anchors:
        mo = src[(e["p"], e["n"])].get("motion")
        if not isinstance(mo, dict) or mo.get("kind") not in ("trans", "planar", "rot"):
            continue
        x = np.array(e["x"], float)
        if mo["kind"] == "rot" and mo.get("pivot") is not None:
            ax = np.array(mo["axis"], float) / np.linalg.norm(mo["axis"])
            d = x - np.array(mo["pivot"], float)
            if np.linalg.norm(d - ax * d.dot(ax)) < 1.0:
                still_axis.append(e["n"])
                continue
        cand = [b for b in movers if b in rest_box and np.all(x >= rest_box[b][0] - 1.0) and np.all(x <= rest_box[b][1] + 1.0)]
        if cand:
            e["c"] = min(cand, key=lambda b: float(np.prod(rest_box[b][1] - rest_box[b][0] + 1.0)))
        else:
            still_none.append(f"{e['n']} ({e['p']})")
    cface = anchors_all.get("clamp", {}).get("clamp.face", {}).get("xyz")
    bface = anchors_all.get("backgauge", {}).get("backgauge.face", {}).get("xyz")
    data = {
        "parts": list(parts.values()),
        "bodies": bodies,
        "anchors": anchors,
        "knife": {"bodies": kb, "steps": STEPS, "tf": b64(T), "dz": dz, "edge_z": round(float(edge[2]), 2) if edge else None},
        "clamp": {"range": rnd(C["range"], 3), "face": rnd(cface) if cface else None,
                  "groups": [{"axis": rnd(C["axis"], 6), "bodies": list(C["beam"]) + list(C["riders"])},
                             {"axis": rnd(C["p_axis"], 6), "bodies": list(C["piston"])}]},
        "backgauge": {"range": rnd(G["range"], 3), "axis": rnd(G["axis"], 6), "bodies": list(G["moving"]),
                      "face": rnd(bface) if bface else None},
        "checks": [{"check": c["check"], "status": c["status"], "text": c["text"]} for c in (checks or [])],
        "open_items": list(open_items or []),
        "legend": legend or "",
        "inputs": {k: v[:12] for k, v in (inputs or {}).items()},
    }
    st = [c["status"] for c in data["checks"]]
    data["summary"] = {s: st.count(s) for s in ("PASS", "FAIL", "OPEN")}

    # every "<" inside the JSON becomes <, so no text of the data can end the script element
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    tpl = TEMPLATE.read_text(encoding="utf-8")
    assert tpl.count("__DATA__") == 1, "viewer_template.html must hold __DATA__ once"
    html = tpl.replace("__DATA__", js)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8", newline="\n")

    # ---- check V: read the file back
    back = out_path.read_text(encoding="utf-8")
    m0 = re.search(r'<script id="data" type="application/json">(.*?)</script>', back, re.S)
    got = json.loads(m0.group(1)) if m0 else {}
    net = sorted({x.group(0) for x in NET.finditer(back)})
    dev_names = sorted(a["n"] for a in got.get("anchors", []) if a["dev"])
    nb_ok = sorted(b["n"] for b in got.get("bodies", [])) == sorted(mans)
    # the knife poses in the file against the motion model at 4 angles
    Tb = np.frombuffer(base64.b64decode(got["knife"]["tf"]), np.float32).reshape(STEPS, len(kb), 12) if got else None
    dev_pose = 0.0
    for i in (0, 90, 180, 270):
        tf, _ = K["pose"](K["th0"] + 2 * math.pi * i / STEPS)
        for j, b in enumerate(kb):
            dev_pose = max(dev_pose, float(np.abs(Tb[i, j] - np.asarray(tf[b], float).reshape(12)).max()))
    i_bdc = int(np.argmax(dz))

    # ---- carried anchors read back from the file: each lands where its own published motion puts it (critic F8)
    kbi = {b: j for j, b in enumerate(got["knife"]["bodies"])} if got else {}
    ga_ax = {}
    for g in (got.get("clamp", {}).get("groups", []) if got else []):
        for b in g["bodies"]:
            ga_ax[b] = (np.array(g["axis"], float), "clamp")
    for b in (got.get("backgauge", {}).get("bodies", []) if got else []):
        ga_ax[b] = (np.array(got["backgauge"]["axis"], float), "bg")
    cr = float(got["clamp"]["range"][1]) if got else 0.0
    gr = float(got["backgauge"]["range"][1]) if got else 0.0

    def carry(c, p, i):
        """the page's own transform of carrier c at crank step i, clamp at its end cr, backgauge at its end gr"""
        if c in kbi:
            M = Tb[i, kbi[c]].reshape(3, 4).astype(float)
            return M[:, :3] @ p + M[:, 3]
        if c in ga_ax:
            return p + ga_ax[c][0] * (cr if ga_ax[c][1] == "clamp" else gr)
        return p

    def turn(p, axis, piv, deg):
        k = np.array(axis, float) / np.linalg.norm(axis)
        v, t = p - np.array(piv, float), math.radians(deg)
        return np.array(piv, float) + v * math.cos(t) + np.cross(k, v) * math.sin(t) + k * k.dot(v) * (1 - math.cos(t))

    states = (90, i_bdc, 270)
    ga = {(a["p"], a["n"]): a for a in (got.get("anchors", []) if got else [])}
    carried, bad_carry, worst, shown = [], [], 0.0, []
    for (p, n), a in ga.items():
        c = a.get("c")
        if not c:
            continue
        mo, x = src[(p, n)]["motion"], np.array(a["x"], float)
        if mo["kind"] == "trans":
            got_p = carry(c, x, i_bdc)
            errs = [float(np.abs(got_p - (x + np.array(mo["axis"], float) / np.linalg.norm(mo["axis"]) * mo["range"][1])).max())]
        elif mo["kind"] == "rot":
            errs = [float(np.abs(carry(c, x, i) - turn(x, mo["axis"], mo["pivot"], i)).max()) for i in states]
        else:                                   # planar: the middle of its two end anchors, each carried by its own body
            ends = [ga.get((p, e)) for e in mo.get("ends", [])]
            if len(ends) != 2 or not all(e and e.get("c") for e in ends):
                bad_carry.append(f"{n}: ends {mo.get('ends')} not both carried")
                continue
            errs = [float(np.abs(carry(c, x, i) - (carry(ends[0]["c"], np.array(ends[0]["x"], float), i)
                                                   + carry(ends[1]["c"], np.array(ends[1]["x"], float), i)) / 2).max())
                    for i in states]
        carried.append(n)
        worst = max(worst, max(errs))
        if max(errs) > 0.5:
            bad_carry.append(f"{n} ({c}): {max(errs):.2f} mm off its own {mo['kind']} motion")
        des = n.split(".", 1)[1]
        sb_ = f"safety_sensors.{des}"
        if sb_ in rest_box and sb_ in ga_ax:     # a sensor that rides a moving body: its anchor stays inside its body
            q = carry(c, x, i_bdc)
            blo, bhi = carry(sb_, rest_box[sb_][0], i_bdc), carry(sb_, rest_box[sb_][1], i_bdc)
            inside = bool(np.all(q >= blo - 1.0) and np.all(q <= bhi + 1.0))
            shown.append(f"{n} at clamp {cr:g}: Z {q[2]:.1f} = rest {x[2]:.1f} - {x[2] - q[2]:.1f}, "
                         f"{'inside' if inside else 'OUTSIDE'} {sb_} moved")
            if not inside:
                bad_carry.append(f"{n}: outside {sb_} at the end of the clamp stroke")
        if n == "backgauge.face":
            shown.append(f"backgauge.face at backgauge {gr:g}: Y {carry(c, x, 0)[1]:.1f}")
    carry_txt = (f"anchors with a motion: {len(carried)} carried by a moving body of the page and read back where their "
                 f"own published motion puts them (trans at the end of its range, rot and planar at +{states[0]}, "
                 f"+{states[1]}, +{states[2]} deg): max error {worst:.2f} mm (<= 0,5)"
                 + (f" [{'; '.join(shown)}]" if shown else "") + f"; {len(still_axis)} turn on their own axis and stay; "
                 f"{len(still_none)} are moved by no slider of the page and stay ({', '.join(still_none) or '-'})"
                 + (f"; NOT RIGHT: {'; '.join(bad_carry)}" if bad_carry else ""))
    ok = (bool(m0) and nb_ok and not net and len(dev_names) == ndev and dev_pose < 1e-3 and abs(dz[0]) < 1e-6
          and bool(carried) and not bad_carry)
    info = {"file": str(out_path), "bytes": len(back.encode("utf-8")), "bodies": len(bodies), "triangles": ntri,
            "anchors": len(anchors), "device_anchors": ndev, "device_anchor_names": dev_names, "network_refs": net,
            "knife_bodies": kb, "knife_pose_max_dev": dev_pose, "knife_down_max": max(dz), "knife_bdc_deg": i_bdc,
            "carried_anchors": {n: a["c"] for (p, n), a in ga.items() if a.get("c")}, "carried_max_error_mm": worst,
            "carried_problems": bad_carry, "still_on_own_axis": still_axis, "still_no_slider": still_none}
    if report is not None:
        report.add("V", "PASS" if ok else "FAIL",
                   f"viewer/index.html, one file of {info['bytes'] / 1e6:.2f} MB: {len(got.get('bodies', []))}/{len(mans)} "
                   f"bodies ({ntri} triangles, frame bodies with the DECISION 2 passages cut: {len(set(cut_names))}), "
                   f"{len(anchors)} anchors of which {ndev} device anchors with search and locate; references that "
                   f"would load from elsewhere (://, fetch, XMLHttpRequest, link, img, src=, import, url): "
                   f"{net or 'none'}; knife: {STEPS} crank poses of {', '.join(kb)} read back equal to the motion "
                   f"model within {dev_pose:.1e} mm, down {dz[0]:.1f} at rest and {max(dz):.1f} at +{i_bdc} deg; "
                   f"clamp slider {C['range'][0]:g}..{C['range'][1]:g} along {rnd(C['axis'], 3)}, backgauge slider "
                   f"{G['range'][0]:g}..{G['range'][1]:g} along {rnd(G['axis'], 3)}; {carry_txt}", data=info)
    return info
