#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Draw sheets 4-7 of the wiring set 568-70.9001 (control circuits) as SVG.

Run:  python -B stage_2_electronics/schemes_2d/control_draw.py      (from the project folder, or from anywhere)
Reads only ../netlist/control_devices.csv and ../netlist/control_wires.csv; every device, terminal,
wire label, rating and mark on the sheets comes from those two files. This file holds the layout
(where each symbol sits, in the printed column of 568) and the reading notes of each sheet.
Writes control_sheet4.svg ... control_sheet7.svg next to this file, prints one line per sheet and
'result: PASS' (exit 0), or each failed check and 'result: FAIL' (exit 1).
Self-checks: every wire row of a sheet drawn once on that sheet with both ends on placed pins;
every designation of control_devices.csv printed on its sheet(s); every wire label of a sheet's rows
printed on it; ruler columns complete; no two text boxes overlap; cross-references match real rows.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NET = os.path.normpath(os.path.join(HERE, '..', 'netlist'))
CW = 0.6          # advance width of the monospace font, per unit of font size


def rd(name):
    with open(os.path.join(NET, name), encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


DEVS = rd('control_devices.csv')
WIRES = rd('control_wires.csv')
DEV = {d['designation']: d for d in DEVS}
FAIL = []


def f(v):
    s = '%.1f' % v
    return s[:-2] if s.endswith('.0') else s


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def wrap(t, n):
    out, cur = [], ''
    for w in t.split(' '):
        while len(w) > n:
            if cur:
                out.append(cur)
                cur = ''
            out.append(w[:n])
            w = w[n:]
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= n:
            cur += ' ' + w
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def sheets_of(field):
    """'4-6' -> {4,5,6}; '6-7' -> {6,7}; '8' -> {8}."""
    m = re.match(r'^(\d+)(?:-(\d+))?$', field.strip())
    if not m:
        return set()
    a = int(m.group(1))
    b = int(m.group(2) or a)
    return set(range(a, b + 1))


def xref(dev, sheet):
    """Coil cross-reference printed beside a contact: (sheet:column) of the device row."""
    if (sheet, dev) in XR_PRINTED:
        return XR_PRINTED[(sheet, dev)]
    d = DEV[dev]
    return '(%s:%s)' % (d['sheet'].split('-')[0], d['column'].split(';')[0].split('-')[0].strip())


# cross-references printed differently from the device row's first column: kept as printed
# (checked against the paths tables read off the scans, see compare_refs)
XR_PRINTED = {(5, 'KM6'): '(4:16)', (4, 'QF1'): '(2:10)', (4, 'BMR1'): '(7:01)'}
# arrow references printed with one column where the far row spans two
XS_PRINTED = {(7, '13KM3'): '(4:17)'}
# Printed texts other than designations, terminal and wire numbers: (text, paper column, scan stem), read in the
# r7 pass of sheets 4-7 against the clean scans. main() checks each is drawn in that column of the drawing body,
# as often as listed. '(2:02)' is the reference of each printed X5 arrow (one per arrow). 'POUZE MS115' belongs to
# S1 (path 10) but is printed left of its mushroom, before the ruler tick 09 (232949): column 09, as drawn.
PRINTED_LABELS = {
    4: [('4:', 1, '232949'), ('~24V', 1, '232949'), ('~24V', 1, '232949'), ('(2:02)', 1, '232949'),
        ('(2:02)', 7, '232949'), ('POUZE MS115', 9, '232949'), ('+24V', 20, '233009')],  # 12UG50 and 13UG50
    5: [('5:', 1, '234959'), ('+14V', 4, '234616'), ('~48V', 7, '234616'), ('+33V', 10, '234616'),
        ('⏚', 1, '234959'), ('⏚', 2, '234959'), ('⏚', 6, '234959'), ('⏚', 7, '234959'),
        ('(2:02)', 2, '234959'), ('(2:02)', 4, '234959'), ('(2:02)', 7, '234959'), ('(2:02)', 10, '234959'),
        ('(2:02)', 16, '235017')],
    6: [('6:', 1, '014439'), ('START', 5, '014537'), ('+24V PLC', 17, '014513'), ('+24V', 18, '014325')],
    7: [('7:', 1, '014711'), ('+27V', 3, '014711'), ('+27V', 7, '014711'), ('11R/25W', 7, '014751'),
        ('~24V', 9, '014711'), ('+24V', 13, '014711'), ('+24V', 13, '014834')],  # terminal name and line label
}
# contact lists printed under the coils (sheet, coil, column, groups): each group is a label and the (sheet:column)
# references of that coil's contacts, top-down; NO left and NC right where the print splits them (paths tables)
CLISTS = [(4, 'KM1A', 9, [('', '2:04 2:04 2:04 4:10')]), (4, 'KM1B', 11, [('', '2:06 2:06 2:06 4:10')]),
          (4, 'KM8', 12, [('', '2:27 2:28 2:29 5:15')]),
          (4, 'KM2', 13, [('NO', '2:04 2:05 2:06 4:13'), ('NC', '4:16')]),
          (4, 'KM3', 14, [('NO', '2:07 2:08 2:09 4:18 4:19'), ('NC', '4:15')]),
          (4, 'KM4', 15, [('NO', '2:11 2:12 4:14'), ('NC', '4:14')]),
          (4, 'KT1', 16, [('', '4:15'), ('', '4:14')]),
          (4, 'KM6', 17, [('NO', '4:20 5:07 5:10'), ('NC', '6:04')]),
          (4, 'KM7', 19, [('NO', '5:10'), ('NC', '6:04')]),
          (4, 'KT2', 20, [('', '4:19')]),
          (5, 'K1', 15, [('', '2:31')]), (5, 'K2', 16, [('', '6:17')])]

TAB = os.path.join(HERE, '..', '..', 'static_dynamic_memory', 'blocks', 'generation_002', 'artifacts', 'tables')
PATH_TABLES = {4: '11_568_sheet4_paths.csv', 5: '12_568_sheet5_paths.csv',
               6: '12_568_sheet6_paths.csv', 7: '12_568_sheet7_paths.csv'}
REF = re.compile(r'\(\d:\d\d(?:-\d\d)?\)')
# in the paths tables a reference may carry an unclear-reading mark: '(7:10 [?])' counts as '(7:10)'
REF_T = re.compile(r'\((\d:\d\d(?:-\d\d)?)(?: \[\?\])?\)')


class Sheet:
    def __init__(s, n, ncols, subject, photo):
        s.n, s.N, s.subject, s.photo = n, ncols, subject, photo
        s.refs = []  # (label, printed reference) pairs, checked by compare_refs
        s.clists = []  # (column, coil, groups) of the contact lists drawn, checked by compare_refs
        s.W = 1680
        s.cw = (s.W - 60) / ncols
        s.body, s.texts, s.segs = [], [], []
        s.pins, s.plabel = {}, {}
        s.ndrawn = 0
        s.nxref = 0

    def X(s, c):
        return round(30 + (c - 0.5) * s.cw, 2)

    def add(s, frag):
        s.body.append(frag)

    def box(s, x, y, t, size, anchor):
        w = len(t) * size * CW
        x0 = x - w if anchor == 'end' else x - w / 2 if anchor == 'middle' else x
        return (x0, y - size * 0.8, x0 + w, y + size * 0.22)

    def text(s, x, y, t, size=8, anchor='start', cls='t', check=True):
        if check:
            s.texts.append(s.box(x, y, t, size, anchor) + (t,))
        a = '' if anchor == 'start' else ' text-anchor="%s"' % anchor
        s.add('<text x="%s" y="%s" font-size="%s"%s class="%s">%s</text>' % (f(x), f(y), f(size), a, cls, esc(t)))

    def free(s, b, lines=True):
        for o in s.texts:
            if b[0] < o[2] and o[0] < b[2] and b[1] < o[3] and o[1] < b[3]:
                return False
        if lines:
            for (ax, ay), (bx, by) in s.segs:
                if ax == bx and b[0] - 1 < ax < b[2] + 1 and min(ay, by) < b[3] and b[1] < max(ay, by):
                    return False
                if ay == by and b[1] - 1 < ay < b[3] + 1 and min(ax, bx) < b[2] and b[0] < max(ax, bx):
                    return False
        return True

    def place(s, cands, t, size=7.5, cls='t'):
        for lines in (True, False):
            for (x, y, a) in cands:
                if s.free(s.box(x, y, t, size, a), lines):
                    s.text(x, y, t, size, a, cls)
                    return
        x, y, a = cands[0]
        s.text(x, y, t, size, a, cls)

    def line(s, pts, cls='w', seg=True):
        pts = [(round(x, 2), round(y, 2)) for x, y in pts]
        if seg:
            for a, b in zip(pts, pts[1:]):
                if a != b:
                    s.segs.append((a, b))
        s.add('<polyline points="%s" class="%s"/>' % (' '.join('%s,%s' % (f(x), f(y)) for x, y in pts), cls))

    def pin(s, dev, t, x, y, d='any', label=None):
        key = (dev, t)
        if key in s.pins:
            FAIL.append('sheet %d: pin %s:%s placed twice' % (s.n, dev, t))
        if dev not in DEV:
            FAIL.append('sheet %d: pin of unknown device %s' % (s.n, dev))
        s.pins[key] = (round(x, 2), round(y, 2), d)
        if label:
            s.plabel[key] = label


# ---------------------------------------------------------------- symbols

def lab(s, x, y, lines, anchor='end'):
    """Designation (bold), then cross-reference, then a red tag."""
    for i, (t, size, cls) in enumerate(lines):
        s.text(x, y + i * 9, t, size, anchor, cls)


def contact(s, dev, t1, t2, x, y, kind='NO', act='', h=44, side='left', ref=False, tag='', extra=()):
    """Contact drawn in the off state, t1 at the top pin (x, y), t2 at the bottom pin (x, y + h)."""
    y1, y2 = y + 14, y + h - 14
    s.line([(x, y), (x, y1)])
    s.line([(x, y2), (x, y + h)])
    if kind == 'NO':
        s.line([(x, y2), (x - 9, y1 + 2)], 'e', False)
    else:
        s.line([(x, y1), (x + 9, y1)], 'e', False)
        s.line([(x, y2), (x + 11, y1 - 3)], 'e', False)
    my = (y1 + y2) / 2
    if act == 'push':
        s.line([(x - 5, my), (x - 16, my)], 'act', False)
        s.line([(x - 16, my - 4), (x - 16, my + 4)], 'e', False)
    elif act == 'turn':
        s.line([(x - 5, my), (x - 15, my)], 'act', False)
        s.line([(x - 19, my - 4), (x - 15, my - 4), (x - 15, my + 4)], 'e', False)
    elif act == 'pos':
        s.line([(x - 6, my), (x - 15, my)], 'act', False)
        s.line([(x - 15, my - 4), (x - 19, my), (x - 15, my + 4)], 'e', False)
    elif act == 'sensor':
        s.line([(x - 6, my), (x - 12, my)], 'act', False)
        s.line([(x - 16, my - 4), (x - 12, my), (x - 16, my + 4), (x - 20, my), (x - 16, my - 4)], 'e', False)
    elif act == 'delay':
        s.line([(x - 6, my), (x - 13, my)], 'e', False)
        s.add('<path d="M %s %s A 5 5 0 0 0 %s %s" class="e"/>' % (f(x - 13), f(my - 5), f(x - 13), f(my + 5)))
    elif act == 'mushroom':
        s.line([(x - 5, my), (x - 16, my)], 'e', False)
        s.add('<path d="M %s %s A 6 6 0 0 0 %s %s Z" class="e"/>' % (f(x - 16), f(my - 6), f(x - 16), f(my + 6)))
    s.pin(dev, t1, x, y, 'up')
    s.pin(dev, t2, x, y + h, 'down')
    s.text(x + 4, y + 9, t1, 7, 'start', 'n')
    s.text(x + 4, y + h - 3, t2, 7, 'start', 'n')
    lines = [(dev + (' [?]' if DEV[dev]['evidence'].startswith('[?]') else ''), 8, 'd')]
    if ref:
        lines.append((xref(dev, s.n), 7, 't'))
        s.refs.append((dev, xref(dev, s.n)))
    if tag:
        lines.append((tag, 6.5, 'q'))
    lines += list(extra)
    if side == 'left':
        lab(s, x - (28 if act == 'mushroom' else 22 if act else 13), my - 2, lines, 'end')
    else:
        lab(s, x + 14, my - 2, lines, 'start')


def coil(s, dev, x, y, h=40, t1='A1', t2='A2', kind='coil', pe=False):
    top, bot = y + 10, y + h - 10
    s.line([(x, y), (x, top)])
    s.line([(x, bot), (x, y + h)])
    s.add('<rect x="%s" y="%s" width="40" height="%s" class="b"/>' % (f(x - 20), f(top), f(bot - top)))
    if kind == 'timer':
        s.line([(x - 14, top), (x - 14, bot)], 'e', False)
        s.line([(x - 20, top), (x - 14, bot)], 'e', False)
        s.line([(x - 20, bot), (x - 14, top)], 'e', False)
    s.text(x + (3 if kind == 'timer' else 0), (top + bot) / 2 + 3, dev, 8, 'middle', 'd')
    s.pin(dev, t1, x, y, 'up')
    s.pin(dev, t2, x, y + h, 'down')
    s.text(x - 4, y + 8, t1, 6.5, 'end', 'n')
    s.text(x - 4, y + h - 1, t2, 6.5, 'end', 'n')
    if pe:
        my = (top + bot) / 2
        s.line([(x - 20, my), (x - 32, my)])
        s.pin(dev, 'PE', x - 32, my, 'left')
        s.text(x - 31, my - 3, '⏚', 6.5, 'start', 'n')


def clists(s, y0):
    """Contact lists of CLISTS under this sheet's coils, below the 0V rail; returns the lowest y used."""
    low = y0
    for n, dev, c, groups in CLISTS:
        if n != s.n:
            continue
        x = s.X(c)
        xs = [x] if len(groups) == 1 else [x - 14, x + 14]
        nrow = max(len(r.split()) for _, r in groups) + (1 if any(lb for lb, _ in groups) else 0)
        if len(groups) == 2:
            s.line([(x, y0 - 7), (x, y0 + 8 * nrow - 6)], 'r', False)
        for (lb, refs), cx in zip(groups, xs):
            y = y0
            if lb:
                s.text(cx, y, lb, 6, 'middle', 'n')
                y += 8
            for r in refs.split():
                s.text(cx, y, r, 6.5, 'middle', 't')
                y += 8
            low = max(low, y)
        s.clists.append((c, dev, [(lb, refs.split()) for lb, refs in groups]))
    return low


def lamp(s, dev, x, y, h=44):
    cy = y + h / 2
    s.line([(x, y), (x, cy - 9)])
    s.line([(x, cy + 9), (x, y + h)])
    s.add('<circle cx="%s" cy="%s" r="9" class="b"/>' % (f(x), f(cy)))
    s.line([(x - 6.4, cy - 6.4), (x + 6.4, cy + 6.4)], 'e', False)
    s.line([(x - 6.4, cy + 6.4), (x + 6.4, cy - 6.4)], 'e', False)
    s.pin(dev, '1', x, y, 'up')
    s.pin(dev, '2', x, y + h, 'down')
    s.text(x + 4, y + 8, '1', 6.5, 'start', 'n')
    s.text(x + 4, y + h - 2, '2', 6.5, 'start', 'n')
    s.text(x - 12, cy + 3, dev, 8, 'end', 'd')


def part(s, dev, x, y, h=40, kind='diode', name=None):
    """Two-pin part drawn upright beside a coil: pins '1' at the top, '2' at the bottom."""
    cy = y + h / 2
    if kind == 'diode':
        s.line([(x, y), (x, cy - 6)])
        s.line([(x, cy + 6), (x, y + h)])
        s.add('<polygon points="%s,%s %s,%s %s,%s" class="b"/>' % (f(x - 6), f(cy + 6), f(x + 6), f(cy + 6), f(x), f(cy - 6)))
        s.line([(x - 6, cy - 6), (x + 6, cy - 6)], 'e', False)
    elif kind == 'zener2':
        a, b = y + 7, y + h - 7
        s.line([(x, y), (x, a)])
        s.line([(x, b), (x, y + h)])
        m = (a + b) / 2
        s.add('<polygon points="%s,%s %s,%s %s,%s" class="b"/>' % (f(x - 5), f(a), f(x + 5), f(a), f(x), f(m - 1)))
        s.add('<polygon points="%s,%s %s,%s %s,%s" class="b"/>' % (f(x - 5), f(b), f(x + 5), f(b), f(x), f(m + 1)))
        s.line([(x - 6, m - 3), (x - 5, m - 1), (x + 5, m - 1), (x + 6, m + 1)], 'e', False)
        s.line([(x - 6, m - 1 + 2), (x - 5, m + 1), (x + 5, m + 1), (x + 6, m + 3)], 'e', False)
    elif kind == 'rc':
        s.line([(x, y), (x, y + 6)])
        s.add('<rect x="%s" y="%s" width="8" height="12" class="b"/>' % (f(x - 4), f(y + 6)))
        s.line([(x, y + 18), (x, y + h - 16)])
        s.line([(x - 7, y + h - 16), (x + 7, y + h - 16)], 'e', False)
        s.line([(x - 7, y + h - 12), (x + 7, y + h - 12)], 'e', False)
        s.line([(x, y + h - 12), (x, y + h)])
    else:  # resistor
        s.line([(x, y), (x, cy - 10)])
        s.line([(x, cy + 10), (x, y + h)])
        s.add('<rect x="%s" y="%s" width="8" height="20" class="b"/>' % (f(x - 4), f(cy - 10)))
    s.pin(dev, '1', x, y, 'any')
    s.pin(dev, '2', x, y + h, 'any')
    s.text(x + 9, cy + 3, name or dev, 7.5, 'start', 'd')
    if DEV[dev]['evidence'].startswith('[?]'):
        s.text(x + 9, cy + 12, '[?]', 6.5, 'start', 'q')


def term(s, dev, t, x, y, label=None, cands=None):
    s.add('<circle cx="%s" cy="%s" r="2.8" class="tc"/>' % (f(x), f(y)))
    lbl = label or (t + dev)
    s.pin(dev, t, x, y, 'any', lbl)
    s.place(cands or [(x + 5, y - 3, 'start'), (x - 5, y - 3, 'end'), (x + 5, y + 9, 'start'), (x - 5, y + 9, 'end')],
            lbl, 7, 'n')


def offref(s, dev, t, x, y, lines, pos='top'):
    """Arrow to a far end on another sheet: lines[0] names the far end, lines[1] its (sheet:column)."""
    if pos == 'top':
        s.add('<polygon points="%s,%s %s,%s %s,%s" class="b"/>' % (f(x - 4), f(y - 8), f(x + 4), f(y - 8), f(x), f(y)))
        for i, ln in enumerate(reversed(lines)):
            s.text(x, y - 11 - i * 9, ln, 7.5 if ln is lines[0] else 7, 'middle', 'd' if ln is lines[0] else 't')
        s.pin(dev, t, x, y, 'down', lines[0])
        refl = [ln for ln in lines[1:] if REF.fullmatch(ln)]
        if refl:
            s.refs.append((lines[0], refl[0]))
    else:
        s.add('<polygon points="%s,%s %s,%s %s,%s" class="b"/>' % (f(x - 4), f(y), f(x + 4), f(y), f(x), f(y + 8)))
        for i, ln in enumerate(lines):
            s.text(x, y + 18 + i * 9, ln, 7.5 if i == 0 else 7, 'middle', 'd' if i == 0 else 't')
        s.pin(dev, t, x, y, 'up', lines[0])
        refl = [ln for ln in lines[1:] if REF.fullmatch(ln)]
        if refl:
            s.refs.append((lines[0], refl[0]))


def leftref(s, dev, t, x, y, name, ref, volt=None, inline=False):
    """Arrow pointing left, tip at (x, y), as the print ends a line at a far end on another sheet; the line leaves
    to the right. Name and (sheet:column) stand left of the tip: stacked (13UG50 over (3:04)), or on one line
    as '(2:02) X5' (inline); a voltage stands above the line, right of the arrow."""
    s.add('<polygon points="%s,%s %s,%s %s,%s" class="b"/>' % (f(x), f(y), f(x + 8), f(y - 4), f(x + 8), f(y + 4)))
    if inline:
        s.text(x - 3, y + 3, name, 7.5, 'end', 'd')
        s.text(x - 6 - len(name) * 7.5 * CW, y + 3, ref, 7, 'end', 't')
    else:
        s.text(x - 3, y - 1, name, 7.5, 'end', 'd')
        s.text(x - 3, y + 8, ref, 7, 'end', 't')
    if volt:
        s.text(x + 12, y - 3, volt, 7, 'start', 't')
    s.pin(dev, t, x + 8, y, 'right', name)
    s.refs.append((name, ref))


def xref_stub(s, dev, t, x, y, via=None, extra=()):
    """A pin of this sheet whose conductor is a row of another sheet: arrow with 'label (sheet:column)'."""
    rows = [r for r in WIRES if int(r['sheet']) != s.n and
            ((r['from_device'], r['from_terminal']) == (dev, t) or (r['to_device'], r['to_terminal']) == (dev, t))]
    if len(rows) != 1:
        FAIL.append('sheet %d: cross-reference %s:%s matches %d rows of other sheets' % (s.n, dev, t, len(rows)))
        return
    r = rows[0]
    far = (r['to_device'], r['to_terminal']) if (r['from_device'], r['from_terminal']) == (dev, t) else (r['from_device'], r['from_terminal'])
    name = r['wire'] or (far[1] + far[0] if far[0] in ('X10', 'X8', 'XC2', 'X11') else ('%s %s' % far).strip())
    px, py, _ = s.pins[(dev, t)]
    pts = [(px, py)] + (via or []) + [(x, y)]
    s.line(orth(pts))
    s.add('<polygon points="%s,%s %s,%s %s,%s" class="b"/>' % (f(x - 4), f(y), f(x + 4), f(y), f(x), f(y + 8)))
    s.text(x, y + 18, name, 7.5, 'middle', 'd')
    ref = XS_PRINTED.get((s.n, name), '(%s:%s)' % (r['sheet'], r['column']))
    s.text(x, y + 27, ref, 7, 'middle', 't')
    s.refs.append((name, ref))
    for i, e in enumerate(extra):
        s.text(x, y + 36 + i * 9, e, 7, 'middle', 't')
    s.nxref += 1


def bmrbox(s, terms, y0, y1, title):
    xa = s.X(terms[0][1]) - s.cw * 0.45
    xb = s.X(terms[-1][1]) + s.cw * 0.45
    s.add('<rect x="%s" y="%s" width="%s" height="%s" class="b"/>' % (f(xa), f(y0), f(xb - xa), f(y1 - y0)))
    s.text(xa + 6, y0 + 13, title, 8.5, 'start', 'd')
    mid = {6: 8.5, 7: 6.5}.get(s.n)  # where the print writes BMR1 inside the box
    if mid:
        s.text(s.X(mid), (y0 + y1) / 2 + 4, 'BMR1', 9, 'middle', 'd')
    for t, c in terms:
        x = s.X(c)
        s.pin('BMR1', t, x, y1, 'down')
        s.text(x, y1 - 6, t, 7.5, 'middle', 'n')


# ---------------------------------------------------------------- wires

def orth(pts):
    out = [pts[0]]
    for p in pts[1:]:
        q = out[-1]
        if p[0] != q[0] and p[1] != q[1]:
            out.append((q[0], p[1]))
        out.append(p)
    return out


def route(a, b, vias):
    (ax, ay, ad), (bx, by, bd) = a, b
    if vias:
        return orth([(ax, ay)] + list(vias) + [(bx, by)])
    if ax == bx or ay == by:
        return [(ax, ay), (bx, by)]
    flip = ay > by
    if flip:
        (ax, ay, ad), (bx, by, bd) = (bx, by, bd), (ax, ay, ad)
    if ad == 'down' and bd == 'up':
        m = round((ay + by) / 2, 2)
        pts = [(ax, ay), (ax, m), (bx, m), (bx, by)]
    elif ad == 'down' or bd in ('left', 'right', 'any', 'down'):
        pts = [(ax, ay), (ax, by), (bx, by)]
    else:
        pts = [(ax, ay), (bx, ay), (bx, by)]
    if flip:
        pts.reverse()
    return pts


def endpos(s, key):
    return s.pins.get(key)


def wires(s, vias, ends=None):
    """ends: row key -> the two pin keys it is drawn to (a terminal the print draws twice)."""
    rows = [r for r in WIRES if int(r['sheet']) == s.n]
    labels = []
    s.rowpts = []
    for r in rows:
        a = (r['from_device'], r['from_terminal'])
        b = (r['to_device'], r['to_terminal'])
        key = '%s:%s>%s:%s' % (a + b)
        a, b = (ends or {}).get(key, (a, b))
        pa, pb = endpos(s, a), endpos(s, b)
        if pa is None or pb is None:
            FAIL.append('sheet %d: row %s:%s -> %s:%s has an end not placed' % ((s.n,) + a + b))
            continue
        pts = route(pa, pb, vias.get(key))
        s.rowpts.append((a, b, [(round(x, 2), round(y, 2)) for x, y in pts]))
        q = r['evidence'].startswith('[?]')
        s.line(pts, 'wq' if q else 'w')
        s.ndrawn += 1
        lbl = r['wire']
        if lbl and lbl not in (s.plabel.get(a), s.plabel.get(b)):
            labels.append((pts, lbl))
        if q:
            labels.append((pts, '[?]'))
    for pts, lbl in labels:     # labels last, so that they can avoid every line
        segs = sorted(zip(pts, pts[1:]), key=lambda sg: -(abs(sg[0][0] - sg[1][0]) + abs(sg[0][1] - sg[1][1])))
        cands = []
        for (x1, y1), (x2, y2) in segs:
            if x1 == x2:
                for dy in (0, 12, -12, 24, -24):
                    my = (y1 + y2) / 2 + dy + 3
                    if min(y1, y2) <= my - 3 <= max(y1, y2):
                        cands += [(x1 + 3, my, 'start'), (x1 - 3, my, 'end')]
            else:
                for dx in (0, 20, -20, 40, -40):
                    mx = (x1 + x2) / 2 + dx
                    if min(x1, x2) <= mx <= max(x1, x2):
                        cands += [(mx, y1 - 3, 'middle'), (mx, y1 + 9, 'middle')]
        if not cands:
            (x1, y1), (x2, y2) = segs[0]
            cands = [((x1 + x2) / 2 + 3, (y1 + y2) / 2, 'start')]
        s.place(cands, lbl, 7, 'q' if lbl == '[?]' else 'wl')


def dots(s):
    segs = sorted({(a, b) if a < b else (b, a) for a, b in s.segs})
    pts = sorted({p for sg in segs for p in sg})
    # a terminal circle is itself the connection point: no filled dot over it (it would hide the terminal)
    tpins = {(x, y) for (dev, t), (x, y, d) in s.pins.items() if DEV[dev]['kind'] in STRIP_KINDS}
    n = 0
    for p in pts:
        if p in tpins:
            continue
        dirs = set()
        for a, b in segs:
            for u, v in ((a, b), (b, a)):
                if u == p:
                    dirs.add((v[0] > u[0]) - (v[0] < u[0]) + 2 * ((v[1] > u[1]) - (v[1] < u[1])))
            if p != a and p != b and min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]):
                if a[0] == b[0] and p[0] == a[0]:
                    dirs.update((2, -2))
                elif a[1] == b[1] and p[1] == a[1]:
                    dirs.update((1, -1))
        if len(dirs) >= 3:
            s.add('<circle cx="%s" cy="%s" r="2.3" class="dot"/>' % (f(p[0]), f(p[1])))
            n += 1
    return n


# ---------------------------------------------------------------- frame, zones, notes, legend

def zones(s, zs):
    for lvl, c0, c1, t in zs:
        x0, x1 = s.X(c0) - s.cw / 2, s.X(c1) + s.cw / 2
        y0, y1 = {0: (62, 136), 1: (62, 98), 2: (100, 136)}[lvl]
        s.add('<rect x="%s" y="%s" width="%s" height="%s" class="z"/>' % (f(x0 + 1), f(y0), f(x1 - x0 - 2), f(y1 - y0)))
        for size in (7, 6.5, 6, 5.5, 5):
            n = int((x1 - x0 - 6) / (size * CW))
            ls = wrap(t, n)
            if len(ls) * (size + 1.5) <= y1 - y0 - 3:
                break
        for i, ln in enumerate(ls):
            s.text((x0 + x1) / 2, y0 + size + 2 + i * (size + 1.5), ln, size, 'middle', 't')


def frame(s, title):
    s.text(30, 24, title, 11, 'start', 'd')
    for c in range(1, s.N + 1):
        x = s.X(c)
        s.add('<rect x="%s" y="%s" width="%s" height="16" class="r"/>' % (f(x - s.cw / 2), '38', f(s.cw)))
        s.text(x, 50, '%02d' % c, 8, 'middle', 'd')
        if c == 1:
            s.text(x - s.cw / 2 + 4, 50, '%d:' % s.n, 8, 'start', 'd')


def textblock(s, y, head, items, width=None, cls='t', size=7.5):
    x0 = 34
    n = int(((width or (s.W - 68)) - 16) / (size * CW))
    s.text(x0 + 4, y + 12, head, 8.5, 'start', 'd')
    yy = y + 24
    for it in items:
        c = cls
        if it.startswith('ink:'):
            c = 'ink'
        for i, ln in enumerate(wrap(it, n - 2)):
            s.text(x0 + 6 + (0 if i == 0 else 12), yy, ('- ' if i == 0 else '') + ln, size, 'start', c)
            yy += size + 2.5
    s.add('<rect x="%s" y="%s" width="%s" height="%s" class="r"/>' % (f(x0), f(y), f(s.W - 68), f(yy - y)))
    return yy


def legend(s, y):
    here = [d for d in DEVS if d['designation'] in {k[0] for k in s.pins}]
    items = []
    for d in here:
        ev = d['evidence'] if d['evidence'].startswith('[') else '[%s]' % d['evidence']   # "[?]" once, not "[[?]]"
        t = '%s %s %s' % (d['designation'], ev, d['function_en'])
        if d['term_cz_ru'] not in ('', '-'):
            t += ' (%s)' % d['term_cz_ru']
        t += '; %s; place: %s; device row: sheet %s, column %s' % (d['type_rating'], d['place'] or 'not printed', d['sheet'], d['column'])
        items.append(t)
    size = 7
    colw = (s.W - 68 - 24) / 2
    n = int((colw - 14) / (size * CW))
    blocks = [wrap(t, n) for t in items]
    total = sum(len(b) for b in blocks)
    half, acc, split = total / 2, 0, len(blocks)
    for i, b in enumerate(blocks):
        if acc >= half:
            split = i
            break
        acc += len(b)
    s.text(38, y + 12, 'Devices on this sheet (from control_devices.csv; [?] = unclear, estimated = with likely error)', 8.5, 'start', 'd')
    bottom = y + 24
    for col, bl in enumerate((blocks[:split], blocks[split:])):
        yy = y + 24
        x = 40 + col * (colw + 24)
        for b in bl:
            for i, ln in enumerate(b):
                s.text(x + (0 if i == 0 else 10), yy, ln, size, 'start', 'd' if i == 0 and False else 't')
                yy += size + 2.3
            yy += 1.5
        bottom = max(bottom, yy)
    s.add('<rect x="34" y="%s" width="%s" height="%s" class="r"/>' % (f(y), f(s.W - 68), f(bottom - y + 4)))
    return bottom + 4


def finish(s, notes, ybody):
    y = textblock(s, ybody + 26, 'Notes on reading this sheet', notes) + 10
    y = legend(s, y) + 10
    tb = ['Adast Maxima MS 115 PS (serial 578.0009, 1998), control circuits: %s.' % s.subject,
          'Redrawn from the wiring set 568-70.9001 SCHEMA ZAPOJENÍ (MS 80 PS,DS MS 115 PS,DS), sheet %d; columns and zones as printed.' % s.n,
          'Sheet photo: preparatory_data_analysis/maxima_documents/adast_guillotine_wiring_and_plc_diagrams/%s.jpg' % s.photo,
          'Data: stage_2_electronics/netlist/control_devices.csv and control_wires.csv, drawn by stage_2_electronics/schemes_2d/control_draw.py.',
          'Marks: dashed line or [?] = unclear (on-site check list, spec/control.md); contacts in the off state as printed; '
          'end names 1/2 of lamps, RC parts and diodes are this redraw\'s names (1 = feed end, 2 = return end).']
    y = textblock(s, y, 'Title block (redrawn, not a copy)', tb) + 16
    return y


def write(s, H):
    head = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n' % (s.W, H, s.W, H) +
            '<style>.w,.e{fill:none;stroke:#000;stroke-width:1.2}.wq{fill:none;stroke:#000;stroke-width:1.2;stroke-dasharray:5 3}'
            '.b{fill:#fff;stroke:#000;stroke-width:1.2}.bd{fill:none;stroke:#000;stroke-width:1;stroke-dasharray:4 3}'
            '.z{fill:#f3f3f3;stroke:#000;stroke-width:0.8}.r{fill:none;stroke:#000;stroke-width:0.8}'
            '.act{fill:none;stroke:#000;stroke-width:0.9;stroke-dasharray:3 2}.tc{fill:#fff;stroke:#000;stroke-width:1}.dot{fill:#000}'
            'text{font-family:Consolas,"DejaVu Sans Mono","Courier New",monospace;fill:#000}.d{font-weight:bold}.n{fill:#333}'
            '.q{fill:#b00000}.ink{fill:#666;font-style:italic}.wl{fill:#0b4a8f}</style>\n'
            '<rect x="0" y="0" width="%d" height="%d" fill="#fff"/>\n<rect x="8" y="8" width="%d" height="%d" class="r"/>\n'
            % (s.W, H, s.W - 16, H - 16))
    path = os.path.join(HERE, 'control_sheet%d.svg' % s.n)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(head + '\n'.join(s.body) + '\n</svg>\n')
    return path


# ---------------------------------------------------------------- sheet 4

def sheet4():
    s = Sheet(4, 21, 'lighting, main contactors KM1A/KM1B, blower KM8, M1 star-delta KM2-KM4 with KT1, clutch contactors KM6/KM7, KT2',
              '20261113_232719')
    X = s.X
    frame(s, '568-70.9001 sheet 4 (redrawn): lighting, main contactors, motor and cut-clutch contactors, time relays')
    zones(s, [(0, 1, 2, '(9) work-surface lighting E1, E2 (OSVĚTLENÍ PRACOVNÍ PLOCHY E1,E2)'),
              (0, 3, 5, '(10) cut-line indication E3, E4 (NÁZNAK ŘEZU E3,E4)'),
              (0, 8, 11, '(11) main contactors KM1A, KM1B (HLAVNÍ STYKAČE KM1A,KM1B)'),
              (0, 12, 12, '(12) blower motor contactor KM8 (STYKAČ MOTORU DMYCHADLA KM8)'),
              (0, 13, 16, '(13) contactors of the knife and hydraulics drive motor KM2, KM3, KM4 (STYKAČE MOTORU PRO POHON NOŽE A HYDRAULIKY KM2,KM3,KM4)'),
              (0, 17, 18.5, '(14) cut clutch contactors KM6, KM7 (STYKAČE SPOJKY ŘEZU KM6,KM7)'),
              (0, 19.5, 21, '(15) time relay: cut delay after clamping KT2 (ČASOVÉ RELÉ ZPOŽDĚNÍ ŘEZU ZA LISOVÁNÍM KT2)')])
    YT, YR = 172, 740  # YR: the coil-return bus through the coil A2 ends, printed with its own X5 arrow
    # lighting; 12UG50 and 13UG50 are printed as arrows pointing left at the left margin, 13UG50 the upper one
    leftref(s, 'UG50', '12', X(1) + 4, 190, '12UG50', '(3:04)', '~24V')
    contact(s, 'S2', '3A', '4A', X(2), 210, 'NO', 'turn')
    contact(s, 'S2', '4B', '3B', X(4), 210, 'NO', 'turn')
    for t, c in (('7', 1), ('8', 2), ('9', 4), ('10', 5)):
        term(s, 'X10', t, X(c), 300)
    for d, c in (('E1', 1), ('E2', 2), ('E3', 4), ('E4', 5)):
        lamp(s, d, X(c), 340)
    for t, c in (('11', 2), ('12', 3), ('13', 4)):
        term(s, 'X10', t, X(c), 440, cands=[(X(c) + 5, 452, 'start'), (X(c) - 5, 452, 'end')])
    # main contactor chain
    leftref(s, 'UG50', '13', X(1) + 4, 160, '13UG50', '(3:04)', '~24V')
    contact(s, 'QF1', '43', '44', X(10), 200, 'NO', 'pos', ref=True)
    contact(s, 'BMR1', '19', '20', X(10), 270, 'NO', h=40, ref=True)
    term(s, 'X10', '14', X(10), 340)
    contact(s, 'S5', '21', '22', X(10), 360, 'NC', 'pos')
    term(s, 'X10', '15', X(10), 425)
    contact(s, 'S1', '21', '22', X(10), 445, 'NC', 'mushroom', extra=[('POUZE MS115', 6.5, 'n')])
    term(s, 'X10', '16', X(10), 510)
    term(s, 'X10', '17', X(10), 530)
    contact(s, 'KM1A', '13', '14', X(10), 550, 'NO', ref=True, side='right')
    contact(s, 'KM1B', '14', '13', X(10), 610, 'NO', ref=True, side='right')
    contact(s, 'Q2', '1', '2', X(8), 580, 'NO', 'turn')
    for d, c in (('KM1A', 9), ('KM1B', 11), ('KM8', 12), ('KM2', 13), ('KM3', 14), ('KM4', 15), ('KM6', 17), ('KM7', 19)):
        coil(s, d, X(c), 700)
    for d, c in (('RC1', 9), ('RC8', 12), ('RC2', 13), ('RC3', 14), ('RC4', 15), ('RC6', 17), ('RC7', 19)):
        part(s, d, X(c) + 30, 700, 40, 'rc')
    contact(s, 'S4', '3', '4', X(12), 270, 'NO', 'turn')
    # M1 star-delta
    contact(s, 'Q2', '9', '10', X(16), 270, 'NO', 'turn')
    contact(s, 'KT1', '4', '5', X(15), 360, 'NO', 'delay', ref=True, tag='15-18')
    contact(s, 'KM2', '14', '13', X(13), 440, 'NO', ref=True)
    contact(s, 'KM4', '5', '6', X(13) + 38, 440, 'NO', ref=True, side='right')
    contact(s, 'KT1', '12', '14', X(14), 520, 'NC', 'delay', ref=True, tag='25-26', side='right')
    contact(s, 'KM4', '21', '22', X(14), 580, 'NC', ref=True)
    contact(s, 'KM3', '62', '61', X(15), 580, 'NC', ref=True)
    coil(s, 'KT1', X(16), 700, t1='1', t2='2', kind='timer')
    s.pin('KT1', '9', X(16) + 20, 710, 'right')
    s.pin('KT1', '10', X(16) + 20, 730, 'right')
    s.text(X(16) + 23, 707, '9', 6.5, 'start', 'n')
    s.text(X(16) + 23, 738, '10', 6.5, 'start', 'n')
    contact(s, 'KM2', '62', '61', X(16) + 38, 620, 'NC', ref=True)
    # cut clutch contactors, KT2
    offref(s, 'BMR1', '29', X(17), YT, ['BMR1 29', '(7:11)'])
    offref(s, 'BMR1', '28', X(19), YT, ['BMR1 28', '(7:10)'])
    offref(s, 'UG50', '6', X(20), YT, ['6UG50', '(3:04)', '+24V'])
    contact(s, 'Q2', '3', '4', X(17), 400, 'NO', 'turn')
    contact(s, 'KM3', '13', '14', X(18), 400, 'NO', ref=True)
    contact(s, 'KM3', '53', '54', X(19), 400, 'NO', ref=True)
    contact(s, 'KT2', '4', '5', X(19), 580, 'NO', 'delay', ref=True)
    contact(s, 'KM6', '1', '2', X(20), 580, 'NO', ref=True)
    coil(s, 'KT2', X(20), 700, t1='1', t2='2', kind='timer')
    part(s, 'V20', X(20) + 30, 700, 40, 'diode')
    # two X5 ends as printed: the lamp return from 12X10 (column 01) and the coil-return bus (column 07)
    leftref(s, 'X5', '#L', X(1) + 20, YR, 'X5', '(2:02)', inline=True)
    leftref(s, 'X5', '#C', X(7) + 20, YR, 'X5', '(2:02)', inline=True)
    wires(s, {
        'BMR1:29>KM3:13': [(X(17), 380), (X(18), 380)],
        'KM3:13>Q2:3': [(X(18), 380), (X(17), 380)],
        'KM3:14>KT2:4': [(X(18), 464), (X(19), 464)],
        'Q2:4>KM3:14': [(X(17), 464), (X(18), 464)],
        'KM3:54>KM6:A1': [(X(19), 464), (X(17), 464)],
        'KM2:13>KT1:12': [(X(13), 502), (X(14), 502)],
        'KT1:12>KM2:A1': [(X(14), 502), (X(13), 502)],
        'KM2:61>KT1:9': [(X(16) + 38, 710)],
        'KM2:62>KT1:10': [(X(16) + 38, 605), (X(16) + 52, 605), (X(16) + 52, 730)],
    }, ends={'X10:12>X5:': (('X10', '12'), ('X5', '#L')), 'KM1A:A2>X5:': (('KM1A', 'A2'), ('X5', '#C'))})
    nd = dots(s)
    notes = [
        'KT1 contacts: NO or NC is not readable on the print; by the face legend of the maker (photo 20261102_144259, IEC numbering 15-16-18, 25-26-28) 4-5 = 15-18 is NO (star KM4) and 12-14 = 25-26 is NC (delta KM3); KT1 9-10 (B1-B2) is bridged by KM2 62-61 (NC). Dial setting not read (on-site).',
        'RC8 across the KM8 coil: label read as RC8 or RC6 [?].',
        'BMR1 19-20 (an output of the cut-control module, sheet 7) opens the main-contactor chain; drawn as printed: a NO contact with the reference (7:01).',
        'Q2 contacts are drawn open as printed (1-2, 3-4 closed in position 0; 9-10 closed in position 1).',
        'ink: pencil "ZN" (KT1) and "ZR" (KT2) at the contact lists of the clean copy of this sheet (20261113_233009): handwriting, not print.',
        'Which wire lands first on a shared terminal is not printed; lines follow the netlist rows.',
        'Under each coil, below the coil-return bus to X5: its contact list as printed, the (sheet:column) of each of its contacts; NO left and NC right where the print splits them.',
    ]
    return s, nd, notes, clists(s, YR + 20) + 4


# ---------------------------------------------------------------- sheet 5

def sheet5():
    s = Sheet(5, 16, 'knife-lock magnet Y01, clamp brake Y14, hydraulics magnet Y11, cut clutch Y10, PLC field signals, relays K1 and K2',
              '20261113_234616')
    X = s.X
    frame(s, '568-70.9001 sheet 5 (redrawn): electromagnets, cut clutch, signals for the PLC, auxiliary relays K1 and K2')
    zones(s, [(0, 1, 2, '(16) knife-lock electromagnet Y01 (ELEKTROMAGNET ZAJIŠTĚNÍ NOŽE Y01)'),
              (0, 3, 5, '(17) clamp brake Y14 (BRZDA LISOVADLA Y14)'),
              (0, 6, 8, '(18) hydraulics electromagnets Y11 (ELEKTROMAGNETY HYDRAULIKY Y11)'),
              (0, 9, 10, '(19) cut clutch Y10 (SPOJKA ŘEZU Y10)'),
              (1, 11, 16, '(20) signals for the PLC (SIGNÁLY PRO PCL, sic)'),
              (2, 11, 12, '(21) saddle position, front S24, rear S27 (POLOHA SEDLA PŘEDNÍ S24, ZADNÍ S27)'),
              (2, 13, 13, '(22) clamp position S30 (POLOHA LISOVADLA S30)'),
              (2, 14, 14, '(23) clamp plate S28 (PLECH LISOVADLA S28)'),
              (2, 15, 16, '(24) auxiliary relays K1 - control of Y3, K2 - feed-cut blocking (POMOCNÁ RELÉ K1 - ŘÍZENÍ Y3, K2 - BLOKOVÁNÍ POSUV-ŘEZ)')])
    YT, YR = 172, 730  # YR + 16: top of the contact lists of K1 and K2, below the X5 and earth arrows
    # Y01
    offref(s, 'BMR1', '22', X(2), YT, ['BMR1 22', '(7:04)'])
    term(s, 'X10', '18', X(2), 300)
    coil(s, 'Y01', X(2), 460, 44, '+', '-', pe=True)
    part(s, 'V01', X(2) + 34, 460, 44, 'diode')
    term(s, 'X10', '19', X(2), 600)
    term(s, 'X10', 'PE', X(1), 640, label='⏚X10', cands=[(X(1) - 5, 636, 'end'), (X(1) + 5, 652, 'start')])
    offref(s, 'PE', '', X(1), 700, ['⏚', '(2:01)'], pos='bottom')
    # Y14
    offref(s, 'BMR1', '26', X(4), YT, ['BMR1 26', '(7:08)'])
    term(s, 'X10', '20', X(4), 300)
    s.place([(X(4) + 5, 240, 'start'), (X(4) - 5, 240, 'end')], '+14V', 7, 'wl')
    coil(s, 'Y14', X(4), 460, 44, '+', '-')
    part(s, 'V14', X(4) + 34, 460, 44, 'diode')
    term(s, 'X10', '21', X(4), 600)
    # Y11
    offref(s, 'UG50', '18', X(7), YT, ['18UG50', '(3:04)', '~48V'])
    contact(s, 'KM6', '3', '4', X(7), 250, 'NO', ref=True)
    term(s, 'X10', '22', X(7), 360)
    coil(s, 'Y11', X(7), 460, 44, '1', '2', pe=True)
    part(s, 'RC11', X(7) + 34, 460, 44, 'rc')
    term(s, 'X10', '23', X(7), 600)
    # the print draws the earth terminal twice: column 01 (Y01) and column 06 (Y11); both are X10 PE
    term(s, 'X10', 'PE#2', X(6), 640, label='⏚X10', cands=[(X(6) - 5, 636, 'end'), (X(6) + 5, 652, 'start')])
    offref(s, 'PE', '#2', X(6), 700, ['⏚', '(2:01)'], pos='bottom')
    s.line([(X(6), 640), (X(6), 700)])
    # Y10 and the knife-change branch
    offref(s, 'UG50', '10', X(10), YT, ['10UG50', '(3:04)', '+33V'])
    contact(s, 'KM6', '5', '6', X(10), 230, 'NO', ref=True, side='right')
    contact(s, 'Q2', '5', '6', X(9), 230, 'NO', 'turn')
    contact(s, 'KM7', '6', '5', X(10), 300, 'NO', ref=True, side='right')
    term(s, 'X10', '24', X(9), 300)
    contact(s, 'S19', '13', '14', X(9), 320, 'NO', 'pos')
    term(s, 'X10', '25', X(9), 385)
    contact(s, 'S5', '13', '14', X(9), 405, 'NO', 'pos')
    term(s, 'X10', '26', X(9), 480, cands=[(X(9) - 5, 476, 'end'), (X(9) - 5, 492, 'end')])
    term(s, 'X10', '27', X(10), 480)
    coil(s, 'Y10', X(10), 515, 90, '+', '-')
    part(s, 'V10', X(10) + 34, 515, 36, 'zener2')
    part(s, 'R10', X(10) + 34, 569, 36, 'resistor')
    term(s, 'X10', '28', X(10), 640)
    # PLC signals
    offref(s, 'BMR1', '23', X(13) + 30, YT, ['BMR1 23', '(7:05)'])
    term(s, 'X10', '31', X(13), 270, cands=[(X(13) - 5, 266, 'end'), (X(13) + 5, 266, 'start')])
    term(s, 'X10', '32', X(14), 270)
    term(s, 'X10', '33', X(14) + 45, 270, label='33X10', cands=[(X(14) + 50, 266, 'start')])
    s.text(X(14) + 50, 284, '(6:15)', 7, 'start', 't')
    s.refs.append(('33X10', '(6:15)'))
    term(s, 'XC2', '1', X(11) + 50, 320)
    s.text(X(11) + 56, 338, 'XC2 [?]', 7, 'start', 'q')
    contact(s, 'S24', '21', '22', X(11), 400, 'NC', 'pos')
    contact(s, 'S27', '21', '22', X(12), 400, 'NC', 'pos')
    contact(s, 'S30', '13', '14', X(13), 400, 'NO', 'pos')
    contact(s, 'S28', '13', '14', X(14), 400, 'NO', 'sensor')
    term(s, 'XC2', '2', X(11), 500)
    term(s, 'XC2', '3', X(12), 500)
    term(s, 'X10', '29', X(13), 500)
    term(s, 'X10', '30', X(14), 500)
    for t, c, ref in (('IN-A', 11, '(8:02)'), ('IN-9', 12, '(8:02)'), ('IN-2', 13, '(8:01)'), ('IN-1', 14, '(8:01)')):
        offref(s, 'PLC', t, X(c), 580, ['PLC ' + t, ref], pos='bottom')
    offref(s, 'PLC', 'OUT-9', X(15), YT, ['PLC OUT-9', '(8:02)'])
    offref(s, 'PLC', 'OUT-0', X(16), YT, ['PLC OUT-0', '(8:01)'])
    contact(s, 'KM8', '13', '14', X(15), 270, 'NO', ref=True, side='right')
    coil(s, 'K1', X(15), 460)
    coil(s, 'K2', X(16), 460)
    # each 0 V line ends at its own printed arrow 'X5 (2:02)': under 19X10, 21X10, 23X10, 28X10 (beside the earth
    # arrows) and, at column 16, from the joined A2 ends of K1 and K2 (level with the PLC arrows)
    x5 = {'X10:19>X5:': ('X10', '19', '#1', 2), 'X10:21>X5:': ('X10', '21', '#2', 4),
          'X10:23>X5:': ('X10', '23', '#3', 7), 'X10:28>X5:': ('X10', '28', '#4', 10)}
    for dev, t, p, c in x5.values():
        offref(s, 'X5', p, X(c), 700, ['X5', '(2:02)'], pos='bottom')
    offref(s, 'X5', '#5', X(16), 580, ['X5', '(2:02)'], pos='bottom')
    ends = {k: ((dev, t), ('X5', p)) for k, (dev, t, p, c) in x5.items()}
    ends['K1:A2>X5:'] = (('K1', 'A2'), ('X5', '#5'))
    ends['Y11:PE>X10:PE'] = (('Y11', 'PE'), ('X10', 'PE#2'))
    # 31X10 enters XC2 pin 1 from above (cabinet side); S24 and S27 leave it below (field side)
    wires(s, {'Y11:PE>X10:PE': [(X(6), 482)],
              'BMR1:23>X10:32': [(X(13) + 30, 250), (X(14), 250)],
              'X10:31>XC2:1': [(X(11) + 50, 270)],
              'XC2:1>S24:21': [(X(11) + 50, 350), (X(11), 350)],
              'XC2:1>S27:21': [(X(11) + 50, 350), (X(12), 350)],
              'K1:A2>X5:': [(X(16), 500)]},
          ends=ends)
    nd = dots(s)
    notes = [
        'The contacts of KM6 on this sheet carry the cross-reference (4:16) as printed; the KM6 coil is at 4:17.',
        'PLC OUT-9 -> 13KM8 [?]: the cabinet photo shows about four output wires among OUT-8 to OUT-D, their positions not read (on-site check).',
        '32X10 is printed at 5:13 (wire from BMR1 23) and at 5:14 (wire from 33X10, sheet 6): two wires on terminal 32.',
        'Y3 (air cushion): the operating manual p.42 says it is controlled by the inverter UZ1; this sheet: PLC OUT-9 -> KM8 13-14 -> K1, K1 switches Y3 on sheet 2 (on-site check).',
        'Y01, Y14, Y10 ends are printed + and -; Y11 ends 1/2 and every diode and RC end are this redraw\'s names. V10 = two Zener diodes back to back, in series with R10, the pair across Y10.',
        'Zone borders follow the columns of each zone\'s devices; the printed zone borders of this sheet were not measured.',
        'ink: blue Russian notes on the annotated copy (20261113_212552), not print: under Y01 "Блокир. шестерни" (gear blocking), under Y11 "гидрораспр." (hydraulic distributor), under Y10 "сцепление" (clutch).',
        'The earth terminal is printed twice, ⏚X10 at column 01 (Y01) and at column 06 (Y11), each to ⏚ (2:01); the netlist has one X10 PE terminal and one X10 PE -> PE row (line 86), so column 06 repeats it.',
        '"+14V" is printed on the line from BMR1 26 (through R14 on sheet 7) to 20X10. Under K1 and K2, at the bottom: their contact lists as printed.',
    ]
    return s, nd, notes, clists(s, YR + 16) + 4


# ---------------------------------------------------------------- sheet 6

TIMING_SRC = 'clean copy of sheet 6, timing diagram under columns 05-10 (photo 20261114_014537)'
# fraction of one knife stroke: 0 = START, 0.5 = bottom, 1 = back at the top; estimated +-10 %
TIMING = [('SQ1', [(0, 0.04), (0.67, 1)]), ('SQ2', [(0.04, 0.6)]), ('S12', [(0.48, 0.98)]),
          ('S13', [(0, 0.49), (0.98, 1)]), ('S14', [(0, 0.08), (0.94, 1)])]


def knife(s, x, y, low, cut):
    """Knife pictogram, simplified: table line, four sheet lines (split where cut), filled blade with a slanted
    edge, raised (top y) or down through the stack to the table."""
    base = y + 44
    s.line([(x - 22, base), (x + 22, base)], 'e', False)
    for i in range(1, 5):
        yy = base - 4 * i
        for xa, xb in (((x - 20, x - 4), (x + 4, x + 20)) if cut else ((x - 20, x + 6),)):
            s.line([(xa, yy), (xb, yy)], 'e', False)
    top, bot = (y + 18, base) if low else (y, y + 22)
    s.add('<polygon points="%s,%s %s,%s %s,%s %s,%s" fill="#000"/>'
          % (f(x - 3), f(top), f(x + 3), f(top), f(x + 3), f(bot - 6), f(x - 3), f(bot)))


def blockarrow(s, x, y, down):
    """Open block arrow (shaft and head, 14 x 24) of the print between two knife pictograms."""
    a, b, c = (y, y + 14, y + 24) if down else (y + 24, y + 10, y)  # shaft end, head base, tip
    pts = [(x - 3, a), (x + 3, a), (x + 3, b), (x + 7, b), (x, c), (x - 7, b), (x - 3, b)]
    s.add('<polygon points="%s" class="b"/>' % ' '.join('%s,%s' % (f(px), f(py)) for px, py in pts))


def timing(s, x0, y0, w):
    s.text(x0, y0, 'Knife-position sensors over one stroke (from the %s)' % TIMING_SRC, 7, 'start', 'd')
    s.text(x0, y0 + 10, 'bar ends estimated ±10 % of the stroke; what a bar means (contact closed or sensor actuated): [?]', 7, 'start', 'q')
    xa = x0 + 40
    yb = y0 + 30 + 22 * len(TIMING)
    for frac in (0, 0.04, 0.5, 1):  # the print has two START lines, at 0 and about 0.04
        x = xa + frac * w
        s.line([(x, y0 + 29), (x, yb)], 'act', False)
    s.text(xa + 0.02 * w, y0 + 26, 'START', 7, 'middle', 't')
    # pictograms of the print under the diagram: knife raised over the stack at START, open arrow down, knife
    # through the stack at the bottom (middle line), open arrow up, knife back at the top (end line), stack cut
    for frac, low, cut in ((0.02, False, False), (0.5, True, True), (1, False, True)):
        knife(s, xa + frac * w, yb + 8, low, cut)
    for frac, down in ((0.26, True), (0.75, False)):
        blockarrow(s, xa + frac * w, yb + 14, down)
    for i, (dev, bars) in enumerate(TIMING):
        y = y0 + 44 + 22 * i
        s.text(x0, y, dev, 7.5, 'start', 'd')
        s.line([(xa, y - 3), (xa + w, y - 3)], 'r', False)
        for a, b in bars:
            s.add('<rect x="%s" y="%s" width="%s" height="8" fill="#555"/>' % (f(xa + a * w), f(y - 8), f((b - a) * w)))


def sheet6():
    s = Sheet(6, 18, 'inputs 1-18 of the cut-control module BMR1: two-hand start, contactor feedback, knife sensors, interlocks',
              '20261114_014325')
    X = s.X
    frame(s, '568-70.9001 sheet 6 (redrawn): connection of the cut-control module BMR1, inputs 1-18')
    zones(s, [(1, 1, 18, '(25, number cut off on the photo) connection of the cut-control module (PŘIPOJENÍ MODULU ŘÍZENÍ ŘEZU)'),
              (2, 1, 3, '(26) cut start buttons S10, S11 (TLAČÍTKA SPOUŠTĚNÍ ŘEZU S10,S11)'),
              (2, 4, 5, '(27) cut clutch contactors - feedback KM6, KM7 (STYKAČE SPOJKY ŘEZU - ZPĚTNÁ VAZBA KM6,KM7)'),
              (2, 6, 8, '(26) cut start buttons S10, S11 (TLAČÍTKA SPOUŠTĚNÍ ŘEZU S10,S11)'),
              (2, 9, 10, '(29) knife-lock position sensors SQ1, SQ2 (SNÍMAČE POLOHY ZAJIŠTĚNÍ NOŽE SQ1,SQ2)'),
              (2, 11, 13, '(28) knife position sensors S12, S13, S14 (SNÍMAČE POLOHY NOŽE S12,S13,S14)'),
              (2, 16, 16, '(30) clamp position switch S30 (SPÍNAČ POLOHY LISOVADLA S30)'),
              (2, 17, 17, '(32) feed-cut blocking 17 (BLOKOVÁNÍ POSUV-ŘEZ 17)'),
              (2, 18, 18, '(31) cut clutch switch (knife change) S19 (SPÍNAČ SPOJKY ŘEZU (VÝMĚNA NOŽE: S19)')])
    bmrbox(s, [(str(i), i) for i in range(1, 19)], 150, 196,
           'BMR1 cut-control module (MODUL ŘÍZENÍ ŘEZU): inputs 1-18 (outputs 19-29, 0V, +24V on sheet 7)')
    # S10, S11
    term(s, 'X11', '5', X(1), 240)
    term(s, 'X11', '6', X(1), 280)
    s.text(X(1) + 5, 262, 'print: 3X11', 6.5, 'start', 'q')
    s.text(X(1) + 5, 300, 'print: 4X11', 6.5, 'start', 'q')
    for t, c in (('4', 1), ('5', 2), ('6', 3), ('7', 6), ('8', 7), ('9', 8)):
        term(s, 'XC2', t, X(c), 330)
    s.text(X(1) - 30, 346, 'XC2 [?]', 7, 'middle', 'q')
    contact(s, 'S10', '2A', '1A', X(2), 380, 'NC', 'push')
    contact(s, 'S10', '4A', '3A', X(3), 380, 'NO', side='right')
    contact(s, 'S11', '2A', '1A', X(7), 380, 'NC', 'push')
    contact(s, 'S11', '4A', '3A', X(8), 380, 'NO', side='right')
    # KM6/KM7 feedback
    contact(s, 'KM6', '61', '62', X(4), 260, 'NC', ref=True, side='right')
    contact(s, 'KM7', '22', '21', X(4), 340, 'NC', ref=True, side='right', tag='print 62-61 [?]')
    # sensors
    for t, c in (('37', 9), ('38', 10), ('39', 11), ('41', 12), ('40', 13)):
        term(s, 'X10', t, X(c), 240)
    term(s, 'X10', '42', X(12), 275)
    for t, c in (('2', 9), ('3', 10), ('4', 11), ('5', 12), ('6', 13)):
        term(s, 'X8', t, X(c), 320)
    s.text(X(9) - 30, 336, 'X8 [?]', 7, 'middle', 'q')
    contact(s, 'SQ1', '4', '1', X(9), 370, 'NO', 'sensor')
    contact(s, 'SQ2', '4', '1', X(10), 370, 'NO', 'sensor')
    contact(s, 'S12', '2', '1', X(11), 370, 'NC', 'sensor')
    contact(s, 'S13', '2', '1', X(12), 370, 'NC', 'sensor')
    contact(s, 'S14', '2', '1', X(13), 370, 'NC', 'sensor')
    term(s, 'X8', '1', X(13) + 45, 470)
    # Q2 loop, S30, K2, S19, +24V bus
    contact(s, 'Q2', '7', '8', X(14), 270, 'NO', 'turn')
    term(s, 'X10', '43', X(16), 240)
    contact(s, 'S30', '21', '22', X(16), 300, 'NC', 'pos')
    contact(s, 'K2', '11', '14', X(17), 300, 'NO', ref=True, tag='print 13-14', side='right')
    term(s, 'X10', '44', X(18), 240)
    contact(s, 'S19', '21', '22', X(18), 300, 'NC', 'pos')
    for t, c in (('33', 15), ('34', 16), ('35', 17), ('36', 18)):
        term(s, 'X10', t, X(c), 560, cands=[(X(c) + 5, 556, 'start'), (X(c) - 5, 556, 'end'), (X(c) + 5, 572, 'start')])
    # arrows in the printed order (20261114_014325): UZ1 K14 under 1X8, TABLO, 32X10 under 33X10, BMR1 under 34X10, PLC, 5UG50
    offref(s, 'UZ1', 'K14', X(13) + 45, 680, ['UZ1 K14', '(2:26)'], pos='bottom')
    offref(s, 'TABLO', '+24V', X(14), 680, ['TABLO +24V', '(8:03)'], pos='bottom')
    offref(s, 'BMR1', '+24V', X(16), 680, ['BMR1 +24V', '(7:13)'], pos='bottom')
    offref(s, 'PLC', '+24V', X(17), 680, ['PLC', '+24V PLC', '(8:03)'], pos='bottom')
    offref(s, 'UG50', '5', X(18), 680, ['5UG50', '(3:04)', '+24V'], pos='bottom')
    wires(s, {
        'XC2:4>S10:3A': [(X(1), 450), (X(3), 450)],
        'XC2:7>S11:3A': [(X(6), 450), (X(8), 450)],
        'KM7:21>BMR1:5': [(X(4), 410), (X(5), 410)],
        'Q2:8>BMR1:15': [(X(14), 340), (X(15), 340)],
        'X10:34>UZ1:K14': [(X(16), 600), (X(13) + 45, 600)],
        'X10:33>TABLO:+24V': [(X(15), 625), (X(14), 625)],
    })
    xref_stub(s, 'X10', '33', X(15), 680)
    timing(s, X(5) - 40, 530, 6 * s.cw - 60)
    nd = dots(s)
    notes = [
        'BMR1 1 line: wired 5X11 -> bridge -> 6X11 -> 4XC2, as the hand correction on the clean copy (20261114_014439) and the blue wires on X11 5 and 6 in photo 20261102_144309; the print has 3X11/4X11 (20261113_194606). X11 5-6 is likely a bridged light-curtain place (estimated); the light curtain FF1 is not fitted.',
        'K2 contact at BMR1 17: wired 11-14 (hand "11" over "13" on 20261114_014513, marker 11K2 in photo 20261102_144324); print 13-14. Whether +24V on BMR1 17 allows or blocks the cut is not printed [?].',
        'KM6/KM7 feedback: print KM6 61-62 + KM7 62-61; photo: KM7 has only its built-in NC 21-22 (markers 21KM7, 22KM7), so KM7 is drawn 22-21 [?].',
        'SQ1, SQ2 drawn NO, S12, S13, S14 drawn NC, as printed; common terminal 1 of each sensor on 1X8 (+24V); no 0 V wire to the sensors is drawn on the print.',
        'Zone borders follow the columns of each zone\'s devices; columns 14-15 (Q2 7-8 loop) carry no zone title in the reading.',
        'Timing diagram: the print has two dashed START lines (at 0 and about 0.04 of the stroke). Under it the print draws the knife '
        'raised over the stack at START, an arrow down, the knife through the stack at the bottom (middle line), an arrow up and the knife '
        'back at the top (end line), the stack cut; drawn here simplified: filled blade, sheet lines, open block arrows.',
        'ink: red notes on the annotated copy (20261113_194606), not print: "?+24 (не взим.)" (last word read [?]) in the BMR1 box above terminals 3-5; "26 „0“" at BMR1 1, "+26" at BMR1 4 and 6; '
        'triangles above 37X10, 41X10, 40X10 (outlined) and 38X10 (filled), none above 39X10; dotted triangles on the BMR1 4 line above KM6 61 and on the BMR1 14 line; '
        'red "Норм „ON“" (normally ON) by SQ1 (20261113_194843). What the triangles mean is not written (on-site list).',
        'The +24V-bus arrows stand in the printed order: UZ1 K14 (from 34X10), TABLO (from the 33X10 line), 32X10, BMR1, PLC, 5UG50.',
    ]
    return s, nd, notes, 780


# ---------------------------------------------------------------- sheet 7

def sheet7():
    s = Sheet(7, 13, 'outputs 19-29 and supply of the cut-control module BMR1', '20261114_014711')
    X = s.X
    frame(s, '568-70.9001 sheet 7 (redrawn): connection of the cut-control module BMR1, outputs 19-29 and supply')
    zones(s, [(1, 1, 13, '(33) connection of the cut-control module BMR1 (PŘIPOJENÍ MODULU ŘÍZENÍ ŘEZU BMR1)'),
              (2, 1, 2, '(34) blocking of the contactors KM1A, B 19, 20 (BLOKOVÁNÍ STYKAČŮ KM1A,B 19,20)'),
              (2, 3, 4, '(35) control of the knife-lock electromagnet Y01 21, 22 (OVLÁDÁNÍ ELEKTROMAGNETU ZAJIŠTĚNÍ NOŽE Y01 21,22)'),
              (2, 5, 6, '(36) cut-done signal 23, 24 (SIGNÁL PROVEDENÍ ŘEZU 23,24)'),
              (2, 7, 8, '(37) control of the clamp brake Y14 25, 26 (OVLÁDÁNÍ BRZDY LISOVADLA Y14 25,26)'),
              (2, 9, 11, '(38) control of the contactors KM6, KM7 27, 28, 29 (OVLÁDÁNÍ STYKAČŮ KM6,KM7 27,28,29)')])
    terms = [(str(19 + i), 1 + i) for i in range(11)] + [('0V', 12), ('+24V', 13)]
    bmrbox(s, terms, 150, 196, 'BMR1 cut-control module (MODUL ŘÍZENÍ ŘEZU): outputs 19-29, 0V, +24V (inputs 1-18 on sheet 6)')
    YB = 330
    offref(s, 'UG50', '1', X(3), YB, ['1UG50', '(3:04)', '+27V'], pos='bottom')
    offref(s, 'PLC', 'IN-0', X(6), YB, ['PLC', 'IN-0', '(8:01)'], pos='bottom')
    part(s, 'R14', X(7), 236, 50, 'resistor')
    s.pins[('R14', '2')], s.pins[('R14', '1')] = s.pins[('R14', '1')], s.pins[('R14', '2')]
    s.text(X(7) - 4, 244, '2', 6.5, 'end', 'n')
    s.text(X(7) - 4, 284, '1', 6.5, 'end', 'n')
    s.place([(X(7) + 9, 274, 'start'), (X(7) + 9, 284, 'start'), (X(7) - 14, 262, 'end')], '11R/25W', 7, 't')
    offref(s, 'UG50', '2', X(7), YB, ['2UG50', '(3:04)', '+27V'], pos='bottom')
    offref(s, 'UG50', '14', X(9), YB, ['14UG50', '(3:04)', '~24V'], pos='bottom')
    offref(s, 'X5', '', X(12), YB, ['X5', '(2:02)'], pos='bottom')
    wires(s, {})
    for t, c in (('19', 1), ('20', 2), ('22', 4), ('23', 5), ('26', 8), ('28', 10), ('29', 11), ('+24V', 13)):
        xref_stub(s, 'BMR1', t, X(c), YB, extra=['+24V'] if t == '+24V' else ())
    nd = dots(s)
    notes = [
        'Every terminal arrow names its far end as printed: wire label, then (sheet:column) of the sheet where that conductor is drawn.',
        'Copies of this sheet: clean 20261114_014711, 20261114_014751 and 20261114_014834; annotated in red 20261113_193629, photographed again as 20261113_193705. All print "34X10 (6:16)" at +24V.',
        'BMR1 is one relay board with plate "BMR2" (photo 20261102_143021); its maker is not printed or seen and its inner circuit is not printed: the box shows terminals only.',
        'Y14 (clamp brake): the operating manual (p.40, p.42) says it is released at the top by a BMR output driven by S14 and held by KM6; this set feeds Y14 only from BMR1 25-26 (on-site check).',
        'ink: red Russian notes on the annotated copy (20261113_193629, the same on 20261113_193705), not print: "сигнал на резку A1K2" (signal for cutting) and a tick at IN-0; '
        '"Y01 блокир. шестерни" (Y01 gear blocking) at 18X10; "Y14 гидро распр. магнит." (Y14 hydraulic distributor magnet) at 20X10; "A1 KM1A KM1B" at 14X10; "~24V" at 19 and 20.',
    ]
    return s, nd, notes, 400


# ---------------------------------------------------------------- checks and main

def overlaps(s):
    bad = []
    T = s.texts
    for i in range(len(T)):
        for j in range(i + 1, len(T)):
            a, b = T[i], T[j]
            if a[0] < b[2] - 0.3 and b[0] < a[2] - 0.3 and a[1] < b[3] - 0.3 and b[1] < a[3] - 0.3:
                bad.append('%r / %r' % (a[4], b[4]))
    return bad


STRIP_KINDS = ('terminal strip', 'earthing terminal strip', 'connector')
PARENT = {}


def node(k):
    """Electrical node of a (device, terminal) end: ends joined by wire rows of control_wires.csv."""
    if not PARENT:
        PARENT[('', '')] = ('', '')     # marks the table as built before the recursive calls below
        for r in WIRES:
            PARENT[node((r['from_device'], r['from_terminal']))] = node((r['to_device'], r['to_terminal']))
    PARENT.setdefault(k, k)
    while PARENT[k] != k:
        PARENT[k] = PARENT[PARENT[k]]
        k = PARENT[k]
    return k


def lead(pts, p):
    """Direction (dx, dy) in which a polyline leaves its end point p."""
    seq = pts if pts[0] == p else pts[::-1]
    for q in seq[1:]:
        if q != p:
            return ((q[0] > p[0]) - (q[0] < p[0]), (q[1] > p[1]) - (q[1] < p[1]))
    return None


def on_seg(p, a, b):
    return (a[0] == b[0] == p[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])) or \
           (a[1] == b[1] == p[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0]))


def pin_sides(s):
    """A terminal or connector pin has two sides. At each such pin, a row whose far end is a cabinet
    device and a row whose far end is a machine or console device must leave the pin in different
    directions; leaving in the same direction they share a stretch, and the sheet would join the two
    sides past the pin (bridges to the same strip and far ends without a place count for either side).
    Second rule: no row passes over a terminal or connector pin it does not end at, nor over any pin
    of another node; a device pin of the same node on the line is an ordinary T-junction (the RC
    suppressors on the coil A2 lines of sheet 4)."""
    bad, npins = [], 0
    for key, (px, py, _) in s.pins.items():
        if DEV[key[0]]['kind'] not in STRIP_KINDS:
            continue
        npins += 1
        p, seen = (px, py), {}
        for a, b, pts in s.rowpts:
            if key not in (a, b):
                continue
            far = b if a == key else a
            if far[0] == key[0] or not DEV[far[0]]['place']:
                continue
            side = 'cabinet' if DEV[far[0]]['place'] == 'cabinet' else 'field'
            d = lead(pts, p)
            for (d2, side2), far2 in seen.items():
                if d2 == d and side2 != side:
                    bad.append('pin %s:%s: %s:%s (%s) and %s:%s (%s) leave it in the same direction'
                               % (key + far + (side,) + far2 + (side2,)))
            seen.setdefault((d, side), far)
    for a, b, pts in s.rowpts:
        for key, (px, py, _) in s.pins.items():
            if key in (a, b):
                continue
            if DEV[key[0]]['kind'] not in STRIP_KINDS and node(key) == node(a):
                continue
            if any(on_seg((px, py), u, v) for u, v in zip(pts, pts[1:]) if u != v):
                bad.append('row %s:%s -> %s:%s passes over pin %s:%s' % (a + b + key))
    return bad, npins


# drawn labels that the paths tables spell differently
LABEL_T = {'PE': '⏚'}


def pair_found(label, ref, rows):
    """A drawn pair is in the table when one field prints the label and, within 12 characters, the reference,
    or when the row's device or wire is the label and the row prints the reference."""
    label = LABEL_T.get(label, label)
    pat = re.compile(re.escape(label) + r'[^()]{0,12}' + re.escape(ref[:-1]) + r'(?: \[\?\])?\)')
    for r in rows:
        fields = [r.get(k) or '' for k in ('device', 'terminal', 'wire', 'to', 'path', 'rating')]
        if any(pat.search(v) for v in fields):
            return True
        if label in (fields[0], fields[2]) and any(ref == '(%s)' % m for v in fields for m in REF_T.findall(v)):
            return True
    return False


def t_clist(rating):
    """The contact list of a paths-table rating field as [(label, [references])], or None."""
    if not re.match(r'(?:contacts? |NO \d|\w+ contact at )', rating):
        return None
    g = [((re.match(r'(NO|NC) ', p) or [''])[0].strip(), re.findall(r'\d:\d\d', p)) for p in rating.split(' / ')]
    return g if all(refs for _, refs in g) else None


def compare_refs(drawn, pairs, cl):
    """Each sheet's (sheet:column) references against the paths tables read off the scans; skipped without them."""
    if not os.path.isdir(TAB):
        print('INFO static_dynamic_memory/ absent: printed references not compared')
        return
    nd = 0
    for n in sorted(drawn):
        want = set()
        with open(os.path.join(TAB, PATH_TABLES[n]), encoding='utf-8', newline='') as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            for k in ('device', 'terminal', 'wire', 'to', 'path', 'rating'):
                want.update('(%s)' % m for m in REF_T.findall(r.get(k) or ''))
        for label, ref in pairs[n]:
            if not pair_found(label, ref, rows):
                FAIL.append('sheet %d: %s %s drawn, this pair not in the paths table' % (n, label, ref))
                nd += 1
        for x in sorted(drawn[n] - want):
            FAIL.append('sheet %d: reference %s drawn, not in the paths table' % (n, x))
        for x in sorted(want - drawn[n]):
            FAIL.append('sheet %d: reference %s in the paths table, not drawn' % (n, x))
        nd += len(drawn[n] ^ want)
        tl = {int(r['column'][:2]): t_clist(r.get('rating') or '') for r in rows if t_clist(r.get('rating') or '')}
        dl = {c: g for c, dev, g in cl[n]}
        for c in sorted(set(tl) | set(dl)):
            if tl.get(c) != dl.get(c):
                FAIL.append('sheet %d column %02d: contact list drawn %s, paths table %s' % (n, c, dl.get(c), tl.get(c)))
                nd += 1
    print('printed references compared with the paths tables: sheet %s; label pairs %d; contact lists %d; differences %d'
          % (', '.join('%d %d' % (n, len(drawn[n])) for n in sorted(drawn)), sum(len(p) for p in pairs.values()),
             sum(len(v) for v in cl.values()), nd))


def main():
    built = [sheet4(), sheet5(), sheet6(), sheet7()]
    alltext = {}
    drawn = {}
    pairs = {}
    cl = {}
    npl = []
    for s, nd, notes, ybody in built:
        H = int(finish(s, notes, ybody))
        write(s, H)
        alltext[s.n] = '\n'.join(t[4] for t in s.texts)
        # references beside contacts, arrows and rails (short texts); notes and the legend not counted
        drawn[s.n] = {m for t in s.texts if len(t[4]) <= 40 for m in REF.findall(t[4])}
        pairs[s.n] = s.refs
        cl[s.n] = s.clists
        nrows = sum(1 for r in WIRES if int(r['sheet']) == s.n)
        if s.ndrawn != nrows:
            FAIL.append('sheet %d: %d of %d wire rows drawn' % (s.n, s.ndrawn, nrows))
        for c in range(1, s.N + 1):
            if '%02d' % c not in alltext[s.n].split('\n'):
                FAIL.append('sheet %d: ruler column %02d missing' % (s.n, c))
        for r in WIRES:
            if int(r['sheet']) == s.n and r['wire'] and r['wire'] not in alltext[s.n]:
                FAIL.append('sheet %d: wire label %s not printed' % (s.n, r['wire']))
        want = {}
        for text, col, stem in PRINTED_LABELS.get(s.n, ()):
            want[(text, col)] = want.get((text, col), 0) + 1
        for (text, col), k in sorted(want.items()):
            lo, hi = 30 + (col - 1) * s.cw, 30 + col * s.cw
            got = sum(1 for t in s.texts if t[4] == text and t[3] < ybody and lo <= (t[0] + t[2]) / 2 <= hi)
            if got < k:
                FAIL.append('sheet %d column %02d: printed label "%s" drawn %d times, printed %d' % (s.n, col, text, got, k))
        npl.append('%d %d' % (s.n, sum(want.values())))
        ov = overlaps(s)
        for o in ov:
            FAIL.append('sheet %d: text overlap %s' % (s.n, o))
        sb, npins = pin_sides(s)
        for m in sb:
            FAIL.append('sheet %d: %s' % (s.n, m))
        print('sheet %d: wire rows %d/%d drawn, cross-references %d, pins %d, junction dots %d, texts %d, overlaps %d, '
              'terminal pins side-checked %d, side faults %d, height %d px'
              % (s.n, s.ndrawn, nrows, s.nxref, len(s.pins), nd, len(s.texts), len(ov), npins, len(sb), H))
    for d in DEVS:
        des = d['designation']
        pat = re.compile(r'(?<![A-Za-z0-9])' + re.escape(des) + r'(?![A-Za-z0-9])')
        want = sheets_of(d['sheet']) & {4, 5, 6, 7}
        found = {n for n, t in alltext.items() if pat.search(t)}
        if want - found:
            FAIL.append('device %s not printed on sheet(s) %s' % (des, sorted(want - found)))
        if not found:
            FAIL.append('device %s printed on no sheet' % des)
    print('printed labels (PRINTED_LABELS) checked in their columns: sheet %s' % ', '.join(npl))
    compare_refs(drawn, pairs, cl)
    for m in FAIL:
        print('FAIL ' + m)
    print('devices %d checked on sheets 4-7' % len(DEVS))
    print('result: ' + ('FAIL' if FAIL else 'PASS'))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
