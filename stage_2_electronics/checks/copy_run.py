#!/usr/bin/env python3
"""Thread t5 (integration): copy run. The five commands that rebuild every t5 output and rerun every check (COMMANDS
in schemes_2d/integration_draw.py, the list that index.html and sources.md print) run word for word in three new
copies of the repository outside it, working folder = the copy:
  copy A: stage_2_electronics (without __pycache__), stage_1_mechanics as on disk and .gitignore;
  copy B: copy A with the tables and anchors_index.csv of the local memory block;
  copy C: the files a clone from GitHub holds once stage_2_electronics is committed: the files of stage_2_electronics
          that git would stage, the stage-1 files of commit f52cc8e (no caches, test copies, logs or crops), .gitignore
          and .git.
Run from the repository root (the folder that holds stage_1_mechanics and stage_2_electronics), after run_checks.py
(the copies are compared with the repository's current checks.txt):
  python -B stage_2_electronics/checks/copy_run.py
Must hold in each copy: every command exits 0; every file of stage_2_electronics comes out byte-identical to the
repository's, except checks/checks.txt; no other file of the copy appears, changes or goes away (stage_1_mechanics
too, so no __pycache__; the copy's .git is git's own bookkeeping and not compared); in checks.txt each check equals the
repository's line for line, or says SKIP and names what is not on this computer, or adds only INFO lines; never FAIL.
And the repository (stage_2_electronics apart from this report, stage_1_mechanics, .gitignore) is unchanged.
The copies are new folders from tempfile.mkdtemp (prefix t5_copy_; TMPDIR, TEMP or TMP choose where); nothing is
deleted, their paths are printed at the end and never written into the report. Report:
stage_2_electronics/checks/copy_report.txt, without time stamps or temporary paths (a rerun on the same files gives the
same text). Exit 0 when everything holds, else 1.
"""
import ast
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent            # stage_2_electronics/checks
S = HERE.parent
P = S.parent
SR = "stage_2_electronics"
S1R = "stage_1_mechanics"
TR = "static_dynamic_memory/blocks/generation_002/artifacts"
REPORT = "checks/copy_report.txt"
CHECK = re.compile(r"^check (\d+) (.+): (PASS|FAIL|SKIP)$")
WHY = re.compile(r"not on this computer|no \.git folder in this copy")
HOME = Path.home().name
UPATH = re.compile(r"[A-Za-z]:[/\\]Users[/\\]" + (f"|{re.escape(HOME)}" if len(HOME) > 2 else ""), re.I)
COPIES = [
    ("A", f"{SR} (without __pycache__), {S1R} as on disk, .gitignore"),
    ("B", f"copy A with {TR}/tables and {TR}/anchors_index.csv of the local memory block"),
    ("C", f"a clone's files: the files of {SR} that git would stage, the {S1R} files of commit f52cc8e, .gitignore, "
          f".git"),
]


def commands():
    """COMMANDS of integration_draw.py, read from its text (nothing imported, nothing run)"""
    tree = ast.parse((S / "schemes_2d/integration_draw.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "COMMANDS" for t in node.targets):
            return list(ast.literal_eval(node.value))
    raise SystemExit("COMMANDS not found in schemes_2d/integration_draw.py")


def tree_md5(root, skip_top=()):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            if rel.split("/")[0] not in skip_top:
                out[rel] = hashlib.md5(p.read_bytes()).hexdigest()
    return out


def git_list(*args):
    pr = subprocess.run(["git", "-C", str(P)] + list(args), capture_output=True)
    if pr.returncode:
        raise SystemExit(f"git {' '.join(args)}: exit {pr.returncode}")
    return [x for x in pr.stdout.decode("utf-8").split("\0") if x]


def copy_file(rel, root):
    d = root / rel
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(P / rel, d)


def make_copy(kind):
    base = Path(tempfile.mkdtemp(prefix=f"t5_copy_{kind}_"))
    root = base / "repo"
    if kind in ("A", "B"):
        shutil.copytree(S, root / SR, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(P / S1R, root / S1R)
        if kind == "B":
            shutil.copytree(P / TR / "tables", root / TR / "tables")
            copy_file(f"{TR}/anchors_index.csv", root)
    else:
        for rel in git_list("ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", SR):
            if (P / rel).is_file():                 # a tracked file deleted on disk is not staged either
                copy_file(rel, root)
        for rel in git_list("ls-tree", "-r", "-z", "--name-only", "f52cc8e", "--", S1R):
            copy_file(rel, root)
        shutil.copytree(P / ".git", root / ".git")
    shutil.copy2(P / ".gitignore", root / ".gitignore")
    return base, root


def scrub(s, base):
    for b in {str(base), base.as_posix(), str(base.resolve()), base.resolve().as_posix()}:
        s = s.replace(b, "<copy>")
    return s


def blocks(txt):
    """checks.txt -> {n: (name, status, [lines])}, the lines with their line numbers in the file"""
    out, cur = {}, None
    for i, line in enumerate(txt.splitlines(), start=1):
        m = CHECK.match(line)
        if m:
            cur = int(m.group(1))
            out[cur] = (m.group(2), m.group(3), [])
        elif line.startswith("  ") and cur is not None:
            out[cur][2].append((i, line.strip()))
        else:
            cur = None
    return out


def spans(nums):
    """[5, 6, 7, 9] -> '5-7, 9'"""
    out, start, prev = [], None, None
    for n in nums + [None]:
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            out.append(f"{start}" if start == prev else f"{start}-{prev}")
            start = prev = n
    return ", ".join(out)


def compare_checks(p_txt, c_txt):
    """lines for the report and the number of checks that differ without a stated reason (or FAIL)"""
    pb, cb = blocks(p_txt), blocks(c_txt)
    rep, bad, same = [], 0, []
    for n in sorted(set(pb) | set(cb)):
        pname, pst, plines = pb.get(n, ("?", "missing", []))
        cname, cst, clines = cb.get(n, ("?", "missing", []))
        ptext, ctext = [t for _, t in plines], [t for _, t in clines]
        if pst == cst and ptext == ctext:
            same.append(n)
            continue
        only_p = [i for i, t in plines if t not in ctext]
        only_c = [t for _, t in clines if t not in ptext]
        if cst == "SKIP":
            ok = any(WHY.search(t) for t in ctext)
            how = "SKIP with the reason the copy names"
        elif cst == pst == "PASS":
            ok = bool(only_c) and all("INFO" in t for t in only_c)
            how = "PASS, the lines that differ say INFO"
        else:
            ok, how = False, f"{cst} where the repository says {pst}"
        bad += not ok
        rep.append(f"  check {n} {pname}: repository {pst}, copy {cst}: {how if ok else 'NOT explained: ' + how}")
        rep += [f"    copy only: {t}" for t in only_c]
        if only_p:
            rep.append(f"    repository only (not computed in the copy): checks.txt line"
                       f"{'s' if len(only_p) > 1 else ''} {spans(only_p)} ({len(only_p)} line"
                       f"{'s' if len(only_p) > 1 else ''})")
    head = [f"  checks.txt: checks equal to the repository's line for line {len(same)}"
            + (f" ({', '.join(map(str, same))})" if same else "") + f"; differing {len(set(pb) | set(cb)) - len(same)}"]
    tail = [l for l in c_txt.splitlines() if l.startswith(("summary:", "result:"))]
    return head + rep + [f"  copy's checks.txt: {t}" for t in tail], bad


def run_copy(kind, desc, cmds, p_tree, p_checks):
    base, root = make_copy(kind)
    rep = ["", f"copy {kind}: {desc}"]
    files0 = tree_md5(root, skip_top=(".git",))
    rep.append(f"  files copied (without .git) {len(files0)}; of them under {SR} "
               f"{sum(1 for r in files0 if r.startswith(SR + '/'))}, under {S1R} "
               f"{sum(1 for r in files0 if r.startswith(S1R + '/'))}")
    bad = 0
    for k, cmd in enumerate(cmds, start=1):
        try:
            pr = subprocess.run(cmd.split(" "), cwd=str(root), capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=900)
            code, out = pr.returncode, scrub(pr.stdout + pr.stderr, base)
        except (OSError, subprocess.TimeoutExpired) as e:
            code, out = "not run", f"{type(e).__name__}"
        res = [l.strip() for l in out.splitlines() if l.startswith("result:")]
        info = [l.strip() for l in out.splitlines() if l.startswith(("INFO:", "FAIL:"))] if k < len(cmds) else []
        bad += code != 0
        rep.append(f"  command {k}: {cmd}: exit {code}; {res[-1] if res else 'no result line'}")
        rep += [f"    {l}" for l in info]
        if code != 0:
            print(out[-3000:])
    files1 = tree_md5(root, skip_top=(".git",))
    new = sorted(set(files1) - set(files0))
    gone = sorted(set(files0) - set(files1))
    changed = sorted(r for r in set(files0) & set(files1) if files0[r] != files1[r])
    own = f"{SR}/checks/checks.txt"
    rep.append(f"  files the commands wrote with new bytes {len(changed)}"
               + (f" ({', '.join(changed)})" if changed else "") + f"; new files {len(new)}"
               + (f" ({', '.join(new[:8])})" if new else "") + f"; files gone {len(gone)}"
               + (f" ({', '.join(gone[:8])})" if gone else ""))
    bad += bool(new or gone or set(changed) - {own})
    s_copy = {r[len(SR) + 1:]: h for r, h in files1.items() if r.startswith(SR + "/")}
    s_copy.pop(REPORT, None)                        # this run's own report: the copy holds the previous one
    differ = sorted(r for r in set(s_copy) | set(p_tree) if s_copy.get(r) != p_tree.get(r))
    rep.append(f"  files of {SR} that differ from the repository's {len(differ)}"
               + (f" ({', '.join(differ)})" if differ else "")
               + ("" if set(differ) <= {"checks/checks.txt"} else ": NOT allowed (only checks/checks.txt may)"))
    bad += not set(differ) <= {"checks/checks.txt"}
    c_checks = (root / own).read_text(encoding="utf-8") if (root / own).is_file() else ""
    lines, nbad = compare_checks(p_checks, c_checks)
    rep += lines
    bad += nbad
    rep.append(f"  copy {kind}: {'as expected' if not bad else 'NOT as expected'}")
    print(f"copy {kind}: {'as expected' if not bad else 'NOT as expected'}")
    return rep, bad, base


def main():
    sys.dont_write_bytecode = True
    cmds = commands()
    p_tree = tree_md5(S)
    p_tree.pop(REPORT, None)
    p_s1, p_gi = tree_md5(P / S1R), hashlib.md5((P / ".gitignore").read_bytes()).hexdigest()
    p_checks = (S / "checks/checks.txt").read_text(encoding="utf-8")
    rep = ["Copy run of the rebuild and check commands (thread t5, integration).",
           "Written by stage_2_electronics/checks/copy_run.py; rerun it, do not edit. Paths relative to the repository "
           "root; no time stamps, no temporary paths.", "",
           f"commands, word for word from COMMANDS of {SR}/schemes_2d/integration_draw.py (as index.html and sources.md "
           f"print them), run in each copy in this order, working folder = the copy:"]
    rep += [f"  {k}. {c}" for k, c in enumerate(cmds, start=1)]
    rep.append(f"compared with: the repository's files of {SR} ({len(p_tree)} without this report) and its "
               f"checks/checks.txt")
    total, bases, n_ok = 0, [], 0
    for kind, desc in COPIES:
        r, b, base = run_copy(kind, desc, cmds, p_tree, p_checks)
        rep += r
        total += b
        n_ok += not b
        bases.append(base)
    a_tree = tree_md5(S)
    a_tree.pop(REPORT, None)
    a_s1, a_gi = tree_md5(P / S1R), hashlib.md5((P / ".gitignore").read_bytes()).hexdigest()
    p_changed = sum(1 for k in set(p_tree) | set(a_tree) if p_tree.get(k) != a_tree.get(k)) + \
        sum(1 for k in set(p_s1) | set(a_s1) if p_s1.get(k) != a_s1.get(k)) + (p_gi != a_gi)
    total += bool(p_changed)
    rep += ["", f"files of the repository changed by this run ({SR} apart from this report, {S1R}, .gitignore): "
                f"{p_changed}",
            f"summary: copies {len(COPIES)}, as expected {n_ok}; faults {total}",
            f"result: {'PASS' if not total else 'FAIL'}"]
    txt = "\n".join(rep) + "\n"
    if UPATH.search(txt):
        print("the report would hold a user path: not written")
        return 1
    (S / REPORT).write_text(txt, encoding="utf-8", newline="\n")
    print("\n".join(rep[-3:]))
    for kind, base in zip((k for k, _ in COPIES), bases):
        print(f"copy {kind} kept (nothing deleted): {base}")
    return 0 if not total else 1


if __name__ == "__main__":
    sys.exit(main())
