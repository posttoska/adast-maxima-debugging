#!/usr/bin/env python3
"""Draw set 568-70.9001 sheets 1-3 (thread t1, power) as SVG from the t1 netlist.

Run:     python -B stage_2_electronics/schemes_2d/power_draw.py
Reads:   ../netlist/power_devices.csv, ../netlist/power_wires.csv
Writes:  power_sheet1.svg, power_sheet2.svg, power_sheet3.svg next to this script.
Layout follows the photographed paper sheets (folder preparatory_data_analysis/
maxima_documents/adast_guillotine_wiring_and_plc_diagrams: sheet 1 20261113_213049,
sheet 2 20261113_214644, sheet 3 20261113_232117); every sheet says it is redrawn.
Every wire row of sheets 2-3 is drawn: both ends placed on one sheet -> a routed
line; otherwise (or with an 'x' hint, as the paper does) a stub arrow at each placed
end, labelled with the far end "<device> <terminal> (<sheet>:<column>)".
Not in the netlist, drawn from the tables below: the printed 230 V variant
"FA3 A,B" (2:24-25) and the FF1 option feeds (sheet 3), both dashed, not fitted.
Self-checks, exit 1 on a failure: every designation printed on its sheet, rulers,
wire coverage, text overlap, text on a wire, different nets overlapping or touching,
marks: each not-sure row ([?], or "estimated ±1 column" shown as "est. ±1 col") shows
its mark exactly once on its own sheet and at most once on another sheet. A text that
shows the mark of rows names them in data-rows="D:<designation>|W:<from> <t> -> <to> <t>".
"""
import csv
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
NETDIR = HERE.parent / 'netlist'
TAB = HERE.parents[1] / 'static_dynamic_memory' / 'blocks' / 'generation_002' / 'artifacts' / 'tables'
FONT = "Consolas,'DejaVu Sans Mono',monospace"
CW = 0.6                          # advance per em used by the overlap estimate (Consolas: 0.55)
SRC = 'preparatory_data_analysis/maxima_documents/adast_guillotine_wiring_and_plc_diagrams/'


def read(p):
    with open(p, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


DEV = {d['designation']: d for d in read(NETDIR / 'power_devices.csv')}
WIRES = read(NETDIR / 'power_wires.csv')
for i, w in enumerate(WIRES):
    w['i'] = i
    w['a'] = (w['from_device'], w['from_terminal'])
    w['b'] = (w['to_device'], w['to_terminal'])
    w['k'] = '%s %s>%s %s' % (w['a'] + w['b'])

PAR = {}                          # nets: union-find over the wire rows


def find(n):
    PAR.setdefault(n, n)
    while PAR[n] != n:
        PAR[n] = PAR[PAR[n]]
        n = PAR[n]
    return n


for w in WIRES:
    PAR[find(w['a'])] = find(w['b'])


def net(node):
    return find(node)


def f(v):
    s = ('%.1f' % v).rstrip('0').rstrip('.')
    return '0' if s == '-0' else s


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


DIRV = {'E': (1, 0), 'W': (-1, 0), 'N': (0, -1), 'S': (0, 1)}


class Sheet:
    def __init__(s, n, w, h, edges=None):
        s.n, s.w, s.h, s.edges = n, w, h, edges
        s.el, s.top, s.txt, s.seg, s.words = [], [], [], [], set()
        s.T, s.lead, s.node = {}, defaultdict(set), {}
        s.marks = []                  # (row keys, text) of every text that carries the mark of not-sure rows

    def col_of(s, x):
        for i in range(1, len(s.edges)):
            if x < s.edges[i]:
                return max(i, 1)
        return len(s.edges) - 1

    def line(s, x1, y1, x2, y2, w=1.0, dash=''):
        s.el.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#111" stroke-width="%s"%s/>' % (
            f(x1), f(y1), f(x2), f(y2), f(w), ' stroke-dasharray="%s"' % dash if dash else ''))

    def rect(s, x0, y0, x1, y1, w=1.0, dash='', fill='none', rx=0):
        s.el.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="#111" stroke-width="%s"%s/>' % (
            f(x0), f(y0), f(x1 - x0), f(y1 - y0), f(rx), fill, f(w), ' stroke-dasharray="%s"' % dash if dash else ''))

    def circ(s, cx, cy, r, w=1.0, fill='none', dash=''):
        s.el.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#111" stroke-width="%s"%s/>' % (
            f(cx), f(cy), f(r), fill, f(w), ' stroke-dasharray="%s"' % dash if dash else ''))

    def path(s, d, w=1.0, fill='none', dash=''):
        s.el.append('<path d="%s" fill="%s" stroke="#111" stroke-width="%s"%s/>' % (
            d, fill, f(w), ' stroke-dasharray="%s"' % dash if dash else ''))

    def text(s, x, y, t, size=9.0, anchor='start', bold=False, rot=0, check=True, rows=()):
        """rows: keys ('D:<designation>', 'W:<wire key>') of the not-sure rows whose mark this text shows;
        written as data-rows="k1|k2" so that a reader-side script can count each row's mark."""
        wd = len(t) * size * CW
        if rows:
            s.marks.append((tuple(rows), t))
        if rot:                       # rotate(-90): the text runs upward from its start
            y1 = y if anchor == 'start' else y + wd / 2 if anchor == 'middle' else y + wd
            bb = (x - 0.78 * size, y1 - wd, x + 0.22 * size, y1)
        else:
            x0 = x if anchor == 'start' else x - wd / 2 if anchor == 'middle' else x - wd
            bb = (x0, y - 0.78 * size, x0 + wd, y + 0.22 * size)
        if check:
            s.txt.append(bb + (t,))
        s.words.update(p for p in re.split(r'[\s,;:()/]+', t) if p)
        s.words.update(p for p in re.split(r'[\s,;:()]+', t) if p)        # keeps UG50/R14 whole
        s.top.append('<text x="%s" y="%s" font-size="%s"%s%s%s%s>%s</text>' % (
            f(x), f(y), f(size), ' text-anchor="%s"' % anchor if anchor != 'start' else '',
            ' font-weight="bold"' if bold else '', ' transform="rotate(-90 %s %s)"' % (f(x), f(y)) if rot else '',
            ' data-rows="%s"' % esc('|'.join(rows)) if rows else '', esc(t)))

    def term(s, dev, t, x, y, lead=None, mark=True):
        assert (dev, t) not in s.T, (dev, t)
        s.T[(dev, t)] = (x, y)
        if lead:
            s.lead[(x, y)].add(lead)
        if mark:
            s.node[(x, y)] = 'mark'

    def wire(s, pts, nt, dash=False, w=1.3):
        pts = [p for k, p in enumerate(pts) if k == 0 or p != pts[k - 1]]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            assert x1 == x2 or y1 == y2, ('wire not orthogonal', pts)
            s.seg.append((x1, y1, x2, y2, nt))
        s.el.append('<polyline points="%s" fill="none" stroke="#111" stroke-width="%s"%s/>' % (
            ' '.join('%s,%s' % (f(x), f(y)) for x, y in pts), f(w), ' stroke-dasharray="7 4"' if dash else ''))

    def arrow(s, x, y, d):
        dx, dy = DIRV[d]
        px, py = -dy, dx
        s.path('M%s,%s L%s,%s L%s,%s Z' % (f(x), f(y), f(x - 8 * dx + 3.5 * px), f(y - 8 * dy + 3.5 * py),
                                          f(x - 8 * dx - 3.5 * px), f(y - 8 * dy - 3.5 * py)), w=0.8, fill='#111')

    def label_at(s, tip, t, side, size=8.5, rows=()):
        x, y = tip
        if side == 'r':
            s.text(x + 5, y + 3.5, t, size, rows=rows)
        elif side == 'l':
            s.text(x - 5, y + 3.5, t, size, 'end', rows=rows)
        elif side == 'u':
            s.text(x + 0.28 * size, y - 5, t, size, 'start', rot=1, rows=rows)
        else:
            s.text(x + 0.28 * size, y + 5, t, size, 'end', rot=1, rows=rows)

    def svg(s, title):
        dots = []
        for p in junctions(s):
            dots.append('<circle cx="%s" cy="%s" r="3" fill="#111"/>' % (f(p[0]), f(p[1])))
        marks = ['<circle cx="%s" cy="%s" r="2.3" fill="#fff" stroke="#111" stroke-width="0.9"/>' % (f(x), f(y))
                 for (x, y) in sorted(s.node)]
        return '\n'.join(['<?xml version="1.0" encoding="UTF-8"?>',
                          '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="%s" fill="#111">' % (s.w, s.h, s.w, s.h, FONT),
                          '<title>%s</title>' % esc(title),
                          '<rect x="0" y="0" width="%d" height="%d" fill="#fff"/>' % (s.w, s.h)]
                         + s.el + dots + marks + s.top + ['</svg>', ''])


def on_seg(p, sg, inclusive):
    x, y = p
    x1, y1, x2, y2 = sg[:4]
    if x1 == x2 == x and min(y1, y2) <= y <= max(y1, y2):
        return inclusive or y not in (y1, y2)
    if y1 == y2 == y and min(x1, x2) <= x <= max(x1, x2):
        return inclusive or x not in (x1, x2)
    return False


def junctions(s):
    """Points where a net leaves in three or more directions (wires plus device leads)."""
    by = defaultdict(list)
    for sg in s.seg:
        by[sg[4]].append(sg)
    out = set()
    for nt, ss in by.items():
        pts = {(sg[0], sg[1]) for sg in ss} | {(sg[2], sg[3]) for sg in ss}
        for p in pts:
            dirs = set(s.lead.get(p, ()))
            for x1, y1, x2, y2, _ in ss:
                for (ax, ay), (bx, by_) in (((x1, y1), (x2, y2)), ((x2, y2), (x1, y1))):
                    if p == (ax, ay):
                        dirs.add('E' if bx > ax else 'W' if bx < ax else 'S' if by_ > ay else 'N')
                if on_seg(p, (x1, y1, x2, y2), False):
                    dirs.update(('E', 'W') if y1 == y2 else ('N', 'S'))
            if len(dirs) >= 3:
                out.add(p)
    return sorted(out)


# ---------------------------------------------------------------- symbols
def tn(s, x, y, t, dx=3, dy=-4, size=6.5, anchor='start'):
    s.text(x + dx, y + dy, t, size, anchor)


def pole_v(s, dev, x, y0, y1, t0, t1, kind='k', dash=''):
    """Vertical pole, t0 on top. kind: cb breaker, k contactor, no plain contact, fuse."""
    m = (y0 + y1) / 2
    s.line(x, y0, x, m - 10, dash=dash)
    s.line(x, m + 10, x, y1, dash=dash)
    if kind == 'fuse':
        s.rect(x - 4, m - 10, x + 4, m + 10, dash=dash)
        s.line(x, m - 10, x, m + 10, w=0.6)
    else:
        s.line(x, m + 10, x - 9, m - 8, dash=dash)
        if kind == 'cb':
            s.line(x - 3.5, m - 13.5, x + 3.5, m - 6.5)
            s.line(x - 3.5, m - 6.5, x + 3.5, m - 13.5)
        elif kind == 'k':
            s.path('M%s,%s A3.5,3.5 0 0 0 %s,%s' % (f(x - 3.5), f(m - 10), f(x + 3.5), f(m - 10)))
    s.term(dev, t0, x, y0, 'S')
    s.term(dev, t1, x, y1, 'N')
    return m


def pole_h(s, dev, x0, x1, y, t0, t1, kind='k'):
    """Horizontal pole, t0 on the left."""
    m = (x0 + x1) / 2
    s.line(x0, y, m - 10, y)
    s.line(m + 10, y, x1, y)
    if kind == 'fuse':
        s.rect(m - 10, y - 4, m + 10, y + 4)
        s.line(m - 10, y, m + 10, y, w=0.6)
    else:
        s.line(m - 10, y, m + 8, y - 9)
        if kind == 'k':
            s.path('M%s,%s A3.5,3.5 0 0 1 %s,%s' % (f(m + 10), f(y - 3.5), f(m + 10), f(y + 3.5)))
        elif kind == 'q':
            s.line(m + 10, y - 4, m + 10, y + 4, w=1.6)
    s.term(dev, t0, x0, y, 'E')
    s.term(dev, t1, x1, y, 'W')
    return m


def motor(s, dev, cx, cy, r, top=(), bot=(), pe=None):
    s.circ(cx, cy, r, w=1.4)
    s.text(cx, cy + 1, 'M', 14, 'middle', bold=True)
    s.text(cx, cy + 16, '3~', 9.5, 'middle')
    for t, x in top:
        s.line(x, cy - r - 10, x, cy - math.sqrt(max(r * r - (x - cx) ** 2, 0)))
        s.term(dev, t, x, cy - r - 10, 'S')
        tn(s, x, cy - r - 10, t, 3, 9)
    for t, x in bot:
        s.line(x, cy + r + 10, x, cy + math.sqrt(max(r * r - (x - cx) ** 2, 0)))
        s.term(dev, t, x, cy + r + 10, 'N')
        tn(s, x, cy + r + 10, t, 3, -3)
    if pe:
        t, x = pe
        s.line(x, cy, cx - r if x < cx else cx + r, cy)
        s.term(dev, t, x, cy, 'E' if x < cx else 'W')
        tn(s, x, cy, t, 2 if x < cx else -2, -4, anchor='start' if x < cx else 'end')


def earth(s, x, y):
    s.line(x, y - 8, x, y)
    for k, hw in enumerate((8, 5, 2)):
        s.line(x - hw, y + 3 * k, x + hw, y + 3 * k, w=1.1)


def diode_v(s, dev, x, y0, y1, up=False, led=False):
    """Vertical diode between terminal 1 (top) and 2 (bottom); 'up' points it upward."""
    m = (y0 + y1) / 2
    s.line(x, y0, x, m - 5)
    s.line(x, m + 5, x, y1)
    a, b = (m - 5, m + 4) if not up else (m + 5, m - 4)
    s.path('M%s,%s L%s,%s L%s,%s Z' % (f(x - 5), f(a), f(x + 5), f(a), f(x), f(b)), w=0.9)
    s.line(x - 5, b, x + 5, b, w=1.1)
    if led:
        for k in (0, 5):
            s.line(x + 6, m - 4 + k, x + 11, m - 8 + k, w=0.7)
    s.term(dev, '1', x, y0, 'S')
    s.term(dev, '2', x, y1, 'N')


def resistor_v(s, dev, x, y0, y1):
    m = (y0 + y1) / 2
    s.line(x, y0, x, m - 6)
    s.line(x, m + 6, x, y1)
    s.rect(x - 3.5, m - 6, x + 3.5, m + 6)
    s.term(dev, '1', x, y0, 'S')
    s.term(dev, '2', x, y1, 'N')


def ecap_v(s, dev, x, y0, y1):
    m = (y0 + y1) / 2
    s.line(x, y0, x, m - 5)
    s.line(x, m + 4, x, y1)
    s.rect(x - 9, m - 5, x + 9, m - 2)
    s.rect(x - 9, m + 1, x + 9, m + 4, fill='#111')
    s.text(x - 11, m - 4, '+', 7, 'end', check=False)
    s.term(dev, '+', x, y0, 'S')
    s.term(dev, '-', x, y1, 'N')


def frame(s, zones, title, stem):
    s.rect(20, 20, s.w - 20, s.h - 20, w=1.4)
    if s.edges:
        e = s.edges
        s.rect(e[0], 28, e[-1], 82, w=0.9)
        s.line(e[0], 62, e[-1], 62, w=0.6)
        for k in range(len(e) - 1):
            s.line(e[k], 62, e[k], 82, w=0.6)
            s.text((e[k] + e[k + 1]) / 2, 76.5, '%02d' % (k + 1), 9, 'middle')
        for c0, c1, en, cz in zones:
            xa, xb = e[c0 - 1], e[c1]
            s.line(xa, 28, xa, 62, w=0.9)
            s.text((xa + xb) / 2, 43, en, 9, 'middle', bold=True)
            s.text((xa + xb) / 2, 56, cz, 8, 'middle')
    s.text(40, s.h - 29, 'Wiring diagram (SCHEMA ZAPOJENÍ) 568-70.9001 · MS80PS,DS MS115PS,DS · sheet %d of 8: %s · redrawn 2026 from '
                         'photos (%s.jpg), not an original document · drawn by schemes_2d/power_draw.py from '
                         'netlist/power_*.csv' % (s.n, title, stem), 8.5)


def ref(dev):
    m = re.search(r'coil (\d:\d\d)', DEV[dev]['note'] + ' ' + DEV[dev]['type_rating'])
    return m.group(1) if m else ''


def mark_of(ev):
    """The mark a not-sure row shows once on its sheet: '[?]' or 'est. ±1 col' ('' for a sure row)."""
    if ev == '[?]':
        return '[?]'
    if ev.startswith('estimated'):
        return 'est. ' + ev[len('estimated '):].replace(' column', ' col')
    return ''


def rkey(w):
    """Key of a wire row as spec/power.md section 9 writes it: '<from> <terminal> -> <to> <terminal>'."""
    return ' '.join(('%s %s -> %s %s' % (w['a'] + w['b'])).split())


def q(dev):
    return ' ' + mark_of(DEV[dev]['evidence']) if mark_of(DEV[dev]['evidence']) else ''


def mk(*devs, wires=()):
    """Row keys for rows=: the not-sure devices among devs and the not-sure wire rows with keys (w['k']) in wires."""
    return tuple(['D:' + d for d in devs if q(d)]
                 + ['W:' + rkey(w) for w in WIRES if w['k'] in wires and mark_of(w['evidence'])])


def marked(group):
    """('XC50 [?], XC60 [?], XC70 [?]', row keys): the mark right after each not-sure member of a group."""
    names = [g.strip() for g in group.split(',')]
    return (', '.join(g + (q(g) if g in DEV else '') for g in names),
            tuple('D:' + g for g in names if g in DEV and q(g)))


def parts(dev):
    """The '; '-separated parts of the netlist type_rating (568 / photo / OM data) of dev."""
    return [t.strip() for t in DEV[dev]['type_rating'].split(';') if t.strip()]


def part(dev, key):
    """The part of dev's type_rating that starts with '<key>: ', without the key ('' if none)."""
    return next((t[len(key) + 2:] for t in parts(dev) if t.startswith(key + ': ')), '')


def lines(s, x, y, ts, size=8, anchor='start', step=13):
    for k, t in enumerate(ts):
        s.text(x, y + step * k, t, size, anchor)


# ---------------------------------------------------------------- sheet 2: power circuits
E2 = [40, 303, 360, 533, 594, 633, 703, 768, 793, 819, 873, 934, 973, 1031, 1087, 1126, 1184, 1249, 1296, 1334,
      1380, 1426, 1460, 1494, 1531, 1570, 1647, 1723, 1757, 1808, 1885, 1944, 2020]
ZONES2 = [(1, 1, 'Main terminal strip XP', '(HLAVNÍ SVORKOVNICE XP)'),
          (2, 3, 'Main switch Q1', '(HLAVNÍ VYPÍNAČ Q1)'),
          (4, 16, 'M1 knife drive and hydraulics, star-delta', '(MOTOR PRO POHON NOŽE A HYDRAULIKY M1)'),
          (17, 26, 'M2 saddle feed via inverter UZ1', '(MOTOR PRO POSUV SEDLA M2)'),
          (27, 32, 'M3 air-cushion blower, magnet Y3', '(MOTOR A ELEKTROMAGNET VZDUCHOVÉHO POLŠTÁŘE M3, Y3)')]
BUS = {'L1': 283, 'L2': 312, 'L3': 341}
# the printed 230 V mains variant (ZAPOJENÍ MĚNIČE PRO 230V), source 20261113_210838, not fitted
VARIANT = [('FA3 A', 1505, 'L2', 'ZF2 N (via L2)'), ('FA3 B', 1530, 'L3', 'ZF2 L')]


def sheet2():
    s = Sheet(2, 2070, 1450, E2)
    frame(s, ZONES2, 'power circuits (SILOVÉ OBVODY)', '20261113_214644')
    s.text(50, 108, 'Redrawn 2026 from photos of set 568-70.9001 sheet 2; not an original document. Lines: netlist/power_wires.csv.', 8.5)
    s.text(50, 121, 'Dashed wire or breaker = printed variant or option, not fitted; thin dashed = pole link or cable shield.', 8.5)
    s.text(50, 147, '[?] = unclear; est. ±1 col = column read ±1 (estimated); both on the on-site list of spec/power.md. '
                    'Ratings and plate data: power_devices.csv (568 / photo / OM).', 8.5)
    s.text(50, 134, '"<device> <terminal> (s:cc)" at an arrow = the far end, continued at sheet:column.', 8.5)
    # XP mains terminals and the incoming supply
    for t, y in (('L1', 283), ('L2', 312), ('L3', 341), ('N', 370), ('PE', 567)):
        s.term('XP', t, 150, y)
        s.wire([(60, y), (150, y)], net(('XP', t)))
        s.text(44, y - 3, t, 8)
    s.text(150, 266, 'XP', 11, 'middle', bold=True)
    # ZF1 mains filter, supply side of Q1
    s.rect(205, 400, 295, 440)
    for t, x in (('N', 215), ('L3', 238), ('L2', 261), ('L1', 284)):
        s.term('ZF1', t, x, 400, 'S')
        s.text(x, 410, t, 6.5, 'middle')
    s.term('ZF1', 'PE', 290, 440, 'N')
    s.text(281, 436, 'PE', 6.5, 'end')
    s.text(240, 433, 'ZF1', 10, 'middle', bold=True)
    # PE earthing strip (node) and X5 working-earth bar
    s.term('PE', '', 90, 567, mark=False)
    earth(s, 75, 598)
    s.text(100, 600, 'PE', 10, bold=True)
    s.text(100, 613, 'earthing strip (UZEMŇOVACÍ SVORKOVNICE)', 8)
    s.term('X5', '', 330, 640, mark=False)
    s.text(300, 1088, 'X5 working earth, 0 V', 9, bold=True)
    s.text(300, 1101, '(SVORKOVNICE PRAC. ZEMĚ)', 8)
    # Q1 main switch, three poles on the lines
    for t0, t1, y in (('L1', 'U', 283), ('L2', 'V', 312), ('L3', 'W', 341)):
        pole_h(s, 'Q1', 363, 414, y, t0, t1, 'q')
        tn(s, 363, y, t0, 2, -4)
        tn(s, 414, y, t1, -2, -4, anchor='end')
    s.line(387.5, 262, 387.5, 341, w=0.7, dash='4 3')
    s.text(366, 258, 'Q1', 11, 'end', bold=True)
    lines(s, 392, 236, parts('Q1') + ['0/1'])
    # main contactors KM1A, KM1B in series (KM1B drawn mirrored)
    for dev, x0, x1, flip in (('KM1A', 540, 590, False), ('KM1B', 645, 695, True)):
        for (a, b), y in zip((('1', '2'), ('3', '4'), ('5', '6')), (283, 312, 341)):
            t0, t1 = (b, a) if flip else (a, b)
            pole_h(s, dev, x0, x1, y, t0, t1, 'k')
            tn(s, x0, y, t0, 2, -4)
            tn(s, x1, y, t1, -2, -4, anchor='end')
        s.line((x0 + x1) / 2 - 1, 268, (x0 + x1) / 2 - 1, 337, w=0.7, dash='4 3')
        s.text((x0 + x1) / 2, 263, dev, 10, 'middle', bold=True)
        s.text((x0 + x1) / 2, 251, 'coil ' + ref(dev), 7.5, 'middle')
    # QF1 (M1) with auxiliary contact 43-44
    for x, (a, b) in zip((730, 760, 790), (('1', '2'), ('3', '4'), ('5', '6'))):
        pole_v(s, 'QF1', x, 470, 560, a, b, 'cb')
        tn(s, x, 470, a, 3, 10)
        tn(s, x, 560, b, 3, -3)
    pole_v(s, 'QF1', 840, 470, 560, '43', '44', 'no')
    tn(s, 840, 470, '43', 3, 10)
    tn(s, 840, 560, '44', 3, -3)
    s.line(721, 516, 831, 516, w=0.7, dash='4 3')
    s.text(716, 505, 'QF1', 10, 'end', bold=True)
    lines(s, 716, 518, parts('QF1'), 8, 'end')
    s.text(848, 530, '(4:10)', 8)
    # KM2 line, KM3 delta, KM4 star contactors
    for dev, xs, terms in (('KM2', (570, 600, 630), '123456'), ('KM3', (730, 760, 790), '123456')):
        for x, k in zip(xs, (0, 2, 4)):
            pole_v(s, dev, x, 760, 830, terms[k], terms[k + 1], 'k')
            tn(s, x, 760, terms[k], 3, 10)
            tn(s, x, 830, terms[k + 1], 3, -3)
        s.line(xs[0] - 4.5, 796, xs[-1] - 4.5, 796, w=0.7, dash='4 3')
    for dev, x in (('KM2', 556), ('KM3', 716)):
        s.text(x, 790, dev, 10, 'end', bold=True)
        s.text(x, 803, 'coil ' + ref(dev), 7.5, 'end')
    for x, a, b in ((905, '1', '2'), (945, '3', '4')):
        pole_v(s, 'KM4', x, 760, 830, a, b, 'k')
        tn(s, x, 760, a, 3, 10)
        tn(s, x, 830, b, 3, -3)
    s.line(900.5, 796, 940.5, 796, w=0.7, dash='4 3')
    s.text(959, 790, 'KM4', 10, bold=True)
    s.text(959, 803, 'coil ' + ref('KM4'), 7.5)
    s.text(959, 816, 'terminals [?]', 7.5, rows=mk(wires=('X10 6>KM4 1', 'KM4 1>KM4 3', 'KM4 2>X10 4', 'KM4 4>X10 5')))
    # X10 terminals to M1, M1 star-delta motor
    for t, x in (('PE', 540), ('1', 570), ('2', 600), ('3', 630), ('4', 730), ('5', 760), ('6', 790)):
        s.term('X10', t, x, 1000)
        tn(s, x, 1000, t, 3, 12, 7)
    s.text(525, 1004, 'X10', 10, 'end', bold=True)
    motor(s, 'M1', 600, 1160, 40, top=(('U2', 570), ('V2', 600), ('W2', 630)),
          bot=(('U1', 570), ('V1', 600), ('W1', 630)), pe=('PE', 540))
    s.text(533, 1122, 'M1', 11, 'end', bold=True)
    lines(s, 533, 1135, parts('M1') + ['star-delta'], 8, 'end')
    # FA4 and the service socket XC7 (supply side of Q1)
    pole_v(s, 'FA4', 1060, 540, 640, '1', '2', 'cb')
    tn(s, 1060, 540, '1', 3, 10)
    tn(s, 1060, 640, '2', 3, -3)
    s.text(1046, 585, 'FA4', 10, 'end', bold=True)
    lines(s, 1046, 598, parts('FA4'), 8, 'end')
    s.rect(1040, 1070, 1160, 1140)
    for t, x in (('L', 1060), ('PE', 1100), ('N', 1140)):
        s.term('XC7', t, x, 1070, 'S')
        s.text(x, 1081, t, 6.5, 'middle')
    s.text(1100, 1100, 'XC7', 10, 'middle', bold=True)
    s.text(1100, 1114, 'socket 230 V (110 V)', 7.5, 'middle')
    s.text(1100, 1128, '(%s)' % DEV['XC7']['term_cz_ru'], 7.5, 'middle')
    lines(s, 1100, 1156, ['live with Q1 off (OM p.12)'] + parts('XC7'), 7.5, 'middle')
    # FA3, X2, ZF2, UZ1, XC1, M2
    for x, a, b in ((1265, '3', '4'), (1290, '1', '2')):
        pole_v(s, 'FA3', x, 470, 570, a, b, 'cb')
        tn(s, x, 470, a, 3, 10)
        tn(s, x, 570, b, 3, -3)
    s.line(1260.5, 521, 1285.5, 521, w=0.7, dash='4 3')
    s.text(1251, 515, 'FA3', 10, 'end', bold=True)
    lines(s, 1251, 528, parts('FA3'), 8, 'end')
    for t, x in (('N', 1265), ('L', 1290), ('PE', 1315)):
        s.term('X2', t, x, 620)
        tn(s, x, 620, t, 3, -4)
    s.text(1251, 624, 'X2', 10, 'end', bold=True)
    s.rect(1250, 670, 1330, 710, rx=8)
    for t, x in (('N', 1265), ('L', 1290), ('PE', 1315)):
        s.term('ZF2', t, x, 670, 'S')
        s.text(x, 681, t, 6.5, 'middle')
    for t, x in (('1N', 1265), ('1L', 1290)):
        s.term('ZF2', t, x, 710, 'N')
        s.text(x, 705, t, 6.5, 'middle')
    s.text(1245, 694, 'ZF2', 10, 'end', bold=True)
    s.rect(1200, 760, 1640, 830, w=1.2)
    # PE: the earth circle of the printed top edge stands left of the 21 tick, in the wide column 20 (w231229)
    for t, x in (('N', 1265), ('L', 1290), ('PE', 1350), ('K12', 1545), ('K14', 1605)):
        s.term('UZ1', t, x, 760, 'S')
        s.text(x, 771, t, 6.5, 'middle')
    s.node[(1330, 760)] = 'mark'      # 3rd circle of the printed top edge, unlabeled: takes the UZ1-XC1 cable shield
    for t, x in (('U', 1265), ('V', 1295), ('W', 1325), ('39', 1400), ('E3', 1440), ('E4', 1475), ('28', 1510),
                 ('7', 1550), ('8', 1590)):
        s.term('UZ1', t, x, 830, 'N')
        s.text(x, 825, t, 6.5, 'middle')
    s.text(1205, 799, 'UZ1', 10, bold=True)
    s.text(1348, 791, 'inverter (%s), photo: %s' % (DEV['UZ1']['term_cz_ru'], parts('UZ1')[0]), 8)
    s.text(1348, 805, ', '.join(parts('UZ1')[1:]), 8)
    for t, x in (('PE', 1235), ('1', 1265), ('2', 1295), ('3', 1325)):
        s.term('XC1', t, x, 930)
        tn(s, x, 930, t, 3, 12, 7)
    s.rect(1222, 922, 1338, 938, w=0.9, rx=3)
    s.text(1345, 934, 'XC1', 10, bold=True)
    for cy in (880, 972):
        s.el.append('<ellipse cx="1295" cy="%d" rx="46" ry="9" fill="none" stroke="#111" stroke-width="0.8" stroke-dasharray="3 2"/>' % cy)
    s.path('M1330,760 V745 H1190 V880 H1249', w=0.8)       # UZ1-XC1 shield to the unlabeled 3rd circle (print)
    s.line(1235, 972, 1249, 972, w=0.8)                     # XC1-M2 shield on the earth line (print: dot)
    s.text(1345, 1000, 'shield UZ1-XC1: to an unlabeled UZ1 terminal (on-site list)', 7.5)
    s.text(1345, 1011, 'shield XC1-M2: on the PE line', 7.5)
    motor(s, 'M2', 1295, 1060, 36, top=(('U1', 1265), ('V1', 1295), ('W1', 1325)), pe=('PE', 1235))
    s.text(1345, 1050, 'M2', 11, bold=True)
    lines(s, 1345, 1063, parts('M2') + ['UZ1 ' + re.search(r'\+UG/-UG[^;]*', DEV['UZ1']['note']).group(0)])
    for t, x in (('6+9', 1550), ('4', 1590)):
        s.term('XC50', t, x, 930)
        tn(s, x, 930, t, 3, 12, 7)
    s.rect(1535, 922, 1605, 938, w=0.9, rx=3)
    s.text(1612, 934, 'XC50' + q('XC50'), 9, bold=True, rows=mk('XC50'))
    # the 5 rows "estimated +-1 column" (paper column read +-1): one mark beside the stubs E3, E4, 28, one at 7, 8
    s.text(1530, 865, 'E3, E4, 28: est. ±1 col', 7, 'end', rot=1,
           rows=mk(wires=('PLC OUT-B>UZ1 E3', 'PLC OUT-C>UZ1 E4', 'PLC OUT-D>UZ1 28')))
    s.text(1600, 903, '7, 8: est. ±1 col', 7, rows=mk(wires=('UZ1 7>XC50 6+9', 'UZ1 8>XC50 4')))
    s.text(1334, 664, '[?]', 7.5, rows=mk(wires=('ZF2 PE>UZ1 PE',)))      # far end: unlabeled circle on UZ1
    s.text(1570, 990, 'to PLC analog outputs (sheet 8)', 7.5, 'middle')
    s.el.append('<ellipse cx="1570" cy="880" rx="32" ry="8" fill="none" stroke="#111" stroke-width="0.8" stroke-dasharray="3 2"/>')
    # the printed variant for 230 V mains, dashed, not fitted
    for dev, x, bus, to in VARIANT:
        s.wire([(x, BUS[bus]), (x, 470)], net(('KM1B', {'L2': '3', 'L3': '5'}[bus])), dash=True)
        pole_v(s, dev, x, 470, 570, '1', '2', 'cb', dash='5 3')
        s.wire([(x, 570), (x, 605)], 'variant ' + dev, dash=True)
        s.arrow(x, 605, 'S')
        s.label_at((x, 605), 'to ' + to, 'd', 8)
    s.text(1497, 515, 'FA3 A,B', 9, 'end', bold=True)
    s.text(1497, 528, 'variant', 8, 'end')
    s.text(1498, 400, 'variant for 230 V mains, not fitted:', 8, 'end')
    s.text(1498, 413, '(ZAPOJENÍ MĚNIČE PRO 230V)', 8, 'end')
    # QF2, KM8, XC3, M3; K1, Y3, C3
    for x, (a, b) in zip((1700, 1735, 1770), (('1', '2'), ('3', '4'), ('5', '6'))):
        pole_v(s, 'QF2', x, 470, 560, a, b, 'cb')
        tn(s, x, 470, a, 3, 10)
        tn(s, x, 560, b, 3, -3)
        pole_v(s, 'KM8', x, 640, 710, a, b, 'k')
        tn(s, x, 640, a, 3, 10)
        tn(s, x, 710, b, 3, -3)
    s.line(1695.5, 516, 1765.5, 516, w=0.7, dash='4 3')
    s.line(1695.5, 676, 1765.5, 676, w=0.7, dash='4 3')
    s.text(1686, 505, 'QF2', 10, 'end', bold=True)
    lines(s, 1686, 518, parts('QF2'), 8, 'end')
    s.text(1686, 670, 'KM8', 10, 'end', bold=True)
    s.text(1686, 683, 'coil ' + ref('KM8'), 7.5, 'end')
    for t, x in (('1', 1700), ('2', 1735), ('3', 1770), ('PE', 1810), ('5', 1900), ('6', 1960)):
        s.term('XC3', t, x, 860)
        tn(s, x, 860, t, 3, 14, 7)
    s.rect(1688, 852, 1972, 868, w=0.9, rx=3)
    s.text(1855, 846, 'XC3', 10, 'middle', bold=True)
    motor(s, 'M3', 1735, 1000, 36, top=(('U1', 1700), ('V1', 1735), ('W1', 1770)), pe=('PE', 1810))
    s.text(1735, 1052, 'M3', 11, 'middle', bold=True)
    lines(s, 1735, 1065, parts('M3'), 8, 'middle')
    pole_v(s, 'K1', 1860, 470, 560, '11', '14', 'no')
    tn(s, 1860, 470, '11', 3, 10)
    tn(s, 1860, 560, '14', 3, -3)
    s.text(1846, 505, 'K1', 10, 'end', bold=True)
    s.text(1846, 518, 'coil ' + ref('K1'), 7.5, 'end')
    s.text(1846, 531, '11 (print 13)', 7.5, 'end')
    s.line(1900, 930, 1927, 930)
    s.line(1933, 930, 1960, 930)
    s.line(1927, 921, 1927, 939, w=1.6)
    s.line(1933, 921, 1933, 939, w=1.6)
    s.term('C3', '1', 1900, 930, 'E')
    s.term('C3', '2', 1960, 930, 'W')
    s.text(1894, 925, 'C3' + q('C3'), 8.5, 'end', bold=True, rows=mk('C3', wires=('XC3 5>C3 1', 'C3 2>XC3 6')))
    s.text(1894, 939, parts('C3')[0], 7.5, 'end')
    s.line(1900, 1015, 1915, 1015)
    s.line(1945, 1015, 1960, 1015)
    s.rect(1915, 1007, 1945, 1023, w=1.2)
    s.term('Y3', '1', 1900, 1015, 'E')
    s.term('Y3', '2', 1960, 1015, 'W')
    s.term('Y3', 'PE', 1930, 1023, 'S')                 # printed earth of Y3, joined with the M3 earth (2:31)
    tn(s, 1930, 1023, 'PE', 4, 9)
    s.text(1972, 1012, 'Y3', 11, bold=True)
    s.text(1972, 1026, parts('Y3')[0] + ' magnet', 7.5)
    q2_table(s)
    return s


def q2_table(s):
    x0, y0 = 50, 1196
    s.text(x0, y0 - 10, 'Q2 cam switch, contacts (x = closed); ' + '; '.join(parts('Q2')), 8.5, bold=True)
    rows = [('contact', '0', '1', 'LINIE')] + [(c, 'x', '', l) for c, l in (('1-2', '4:08'), ('3-4', '4:17'),
                                                                          ('5-6', '5:09'), ('7-8', '6:14'))]
    rows.append(('9-10', '', 'x', '4:16'))
    xs = (x0, x0 + 70, x0 + 110, x0 + 150, x0 + 230)
    for k, r in enumerate(rows):
        y = y0 + 16 * k
        for c, t in enumerate(r):
            s.text((xs[c] + xs[c + 1]) / 2, y + 12, t, 8, 'middle', bold=(k == 0))
        s.line(x0, y, xs[-1], y, w=0.5)
    s.rect(x0, y0, xs[-1], y0 + 16 * len(rows), w=0.9)
    for x in xs[1:-1]:
        s.line(x, y0, x, y0 + 16 * len(rows), w=0.5)


# ---------------------------------------------------------------- sheet 3: supply circuits
E3 = [40, 330, 560, 1410, 1660]
ZONES3 = [(1, 2, 'Transformer T1, primary breakers FA1 FA2', '(TRANSFORMÁTOR T1)'),
          (3, 4, 'Power-supply board UG50', '(PLOŠNÝ SPOJ SE ZDROJI UG50)')]
# FF1 option feeds, printed dashed with no cross-reference (20261113_232117), not fitted
OPTION = [('3', 325, 'FF1 ~230 V'), ('1', 415, 'FF1 0 V'), ('PE', 480, 'FF1 PE')]      # FF1's [?]: its note, once
TAPS = [('400V', 280), ('230V', 325), ('20V', 370), ('0V', 415), ('-20V', 460), ('-40V', 505)]
# winding voltage and power from the T1 row of power_devices.csv ('I 21V 120VA; II 19V 50VA; III unused; ...')
TW = {t.split()[0]: t.split()[1:] for t in parts('T1')}


def wind(w):
    v = TW.get(w, [])
    return (v[0], v[1]) if len(v) == 2 else ('', '')


WIND = [('I', 200, 270) + wind('I') + ('21', '22'), ('II', 310, 380) + wind('II') + ('23', '24'),
        ('III', 420, 460) + wind('III') + ('25', '26'), ('IV', 500, 570) + wind('IV') + ('27', '28'),
        ('V', 610, 680) + wind('V') + ('29', '30'), ('VI', 720, 860) + wind('VI') + ('31', '32')]
OUTV = {'I': '+27 V DC', 'II': '+24 V DC', 'IV': '+33 V DC', 'V': '~24 V', 'VI': '~48 V'}
RECT = [('I', 'FU21', ('V11', 'V21', 'R11'), 'V1', 'C1', ('1', '2', '3'), '4', '+27 V DC'),
        ('II', 'FU22', ('V12', 'V22', 'R12'), 'V2', 'C2', ('5', '6'), '7', '+24 V DC'),
        ('IV', 'FU24', ('UG50/V14', 'V24', 'UG50/R14'), 'V4', 'C4', ('10',), '11', '+33 V DC')]
OUTS = {'III': (('8', 420), ('9', 440)), 'V': (('12', 610), ('13', 624), ('14', 638), ('15', 652), ('16', 666), ('17', 680)),
        'VI': (('18', 720), ('19', 790), ('20', 860))}


def name(dev):
    return dev.split('/')[-1]


def indicator(s, d, led, r, x, y):
    """Fuse indicator below line y: diode d and LED led anti-parallel, resistor r below them."""
    diode_v(s, d, x, y + 12, y + 32)
    diode_v(s, led, x + 22, y + 12, y + 32, up=True, led=True)
    resistor_v(s, r, x + 11, y + 40, y + 58)
    s.text(x - 6, y + 25, name(d), 7, 'end')
    s.text(x + 35, y + 25, led, 7)
    s.text(x + 17, y + 53, '%s %s%s' % (name(r), DEV[r]['type_rating'].replace(' [?]', ''), q(r)), 6.5, rows=mk(r))


def bridge(s, dev, x0, x1, ya, yb):
    s.rect(x0, ya - 8, x1, yb + 8, w=1.1)
    s.term(dev, '~1', x0, ya, 'E')
    s.term(dev, '~2', x0, yb, 'E')
    s.term(dev, '+', x1, ya, 'W')
    s.term(dev, '-', x1, yb, 'W')
    s.text(x0 + 4, ya + 5, '~', 8, check=False)
    s.text(x0 + 4, yb + 1, '~', 8, check=False)
    s.text(x1 - 4, ya + 5, '+', 8, 'end', check=False)
    s.text(x1 - 4, yb + 1, '-', 8, 'end', check=False)
    m = (x0 + x1) / 2
    s.text(m, ya + 24, dev + q(dev), 9, 'middle', bold=True, rows=mk(dev))
    s.text(m, ya + 36, DEV[dev]['type_rating'].replace(' [?]', ''), 6.5, 'middle')
    s.path('M%s,%s L%s,%s L%s,%s Z' % (f(m - 5), f(ya + 42), f(m + 5), f(ya + 42), f(m), f(ya + 50)), w=0.8)
    s.line(m - 5, ya + 50, m + 5, ya + 50)


def sheet3():
    s = Sheet(3, 1700, 1010, E3)
    frame(s, ZONES3, 'supply circuits (NAPÁJECÍ OBVODY)', '20261113_232117')
    for dev, x in (('FA1', 230), ('FA2', 300)):
        pole_v(s, dev, x, 200, 250, '1', '2', 'cb')
        tn(s, x, 200, '1', 3, 10)
        tn(s, x, 250, '2', 3, -3)
        s.text(x - 14, 222, dev, 10, 'end', bold=True)
        s.text(x - 14, 235, part(dev, '568'), 8, 'end')
        s.text(x - 14, 248, part(dev, 'photo').split()[0], 7, 'end')
    for t, y in (('4', 295), ('3', 325), ('2', 385), ('1', 415), ('PE', 480)):
        s.term('X11', t, 170, y)
        tn(s, 170, y, t, 4, -4, 7)
    s.text(170, 278, 'X11', 10, 'middle', bold=True)
    for k, y in (('X11 3>X11 4', 312), ('X11 2>X11 1', 402)):     # bridges as drawn; photo differs (on-site list)
        s.text(176, y, '[?]', 7, rows=mk(wires=(k,)))
    for t, y, lab in OPTION:
        s.wire([(170, y), (80, y)], net(('X11', t)), dash=True)
        s.arrow(80, y, 'W')
        s.text(84, y - 4, lab, 7.5)
    s.text(50, 540, 'FF1%s light curtain: option, not fitted;' % q('FF1'), 7.5, rows=mk('FF1'))
    s.text(50, 552, 'printed dashed, no cross-reference', 7.5)
    s.text(50, 935, 'Board parts R14, V14 = UG50/R14, UG50/V14 in netlist/power_*.csv:', 7.5)
    s.text(50, 948, 'the names R14 and V14 also name other parts, on sheets 7 and 5.', 7.5)
    for t, y in TAPS:
        s.line(400, y, 412, y)
        s.term('T1', t, 400, y, 'E')
        s.text(396, y - 4, t, 7.5, 'end')
    s.path('M412,272' + ''.join(' a7.5,7.5 0 0 1 0,15' for _ in range(16)), w=1.2)
    s.line(432, 190, 432, 870, w=1.6)
    s.line(437, 190, 437, 870, w=1.6)
    for wn, ya, yb, v, va, ia, ib in WIND:
        s.path('M457,%d' % ya + ''.join(' a5,5 0 0 0 0,10' for _ in range((yb - ya) // 10)), w=1.2)
        s.line(457, ya, 500, ya)
        s.line(457, yb, 500, yb)
        if v:
            s.term('T1', wn + ' ' + v, 500, ya, 'W')
            s.term('T1', wn + ' 0V', 500, yb, 'W')
        s.text(505, ya - 4, ('%s %s %s' % (wn, v, va)) if v else 'III unused', 7.5)
        s.term('UG50', ia, 590, ya, 'E')
        s.term('UG50', ib, 590, yb, 'E')
        s.text(594, ya - 3, ia, 7)
        s.text(594, yb - 3, ib, 7)
    s.text(434, 178, 'T1', 11, 'middle', bold=True)
    s.text(434, 165, 'TRANSFORMÁTOR T1', 7.5, 'middle')
    s.line(434.5, 870, 434.5, 885)
    s.term('T1', 'PE', 434.5, 885, 'N')
    tn(s, 434.5, 885, 'PE', 5, 4, 7)
    s.rect(50, 590, 325, 676, w=0.9)
    s.text(55, 602, 'T1 taps by mains Un (20261113_231949)', 7, bold=True)
    rows = re.findall(r'(\d+V) (-?\d+)-(\d+)', DEV['T1']['note'])      # 'tap table 200V 20-230, ...'
    taps = [t for t, _y in TAPS]
    wired = {e[1] for w in WIRES for e in (w['a'], w['b']) if e[0] == 'T1'}
    fed = {w[x][1] for w in WIRES for x, y in (('a', 'b'), ('b', 'a'))           # tap fed by FA1 or FA2
           if w[x][0] == 'T1' and w[y][0] in ('FA1', 'FA2')}
    for k, (un, lo, hi) in enumerate(rows):
        miss = [t + 'V' for t in (lo, hi) if t + 'V' not in taps]
        s.text(55, 616 + 12 * k, un, 7)
        s.text(95, 616 + 12 * k, '%s - %s' % (lo, hi) + (' (drawn)' if hi + 'V' in fed and lo + 'V' in wired else '')
               + (' [?] no %s tap drawn' % ', '.join(miss) if miss else ''), 7)
    used = {t + 'V' for _u, lo, hi in rows for t in (lo, hi)}
    s.text(55, 692, '%s: in no row [?]' % ', '.join(t for t in taps if t not in used), 7)
    if 'no plate seen' in DEV['T1']['note']:
        ph = [x for x in DEV['T1']['source_path'].split('; ') if 'maxima_photos' in x]
        s.text(55, 704, 'no T1 plate seen (%s)' % ', '.join('c' + x[-10:-4] for x in ph), 7)
    # UG50 board
    s.rect(590, 160, 1410, 880, w=1.1, dash='8 4')
    s.text(600, 177, 'UG50', 10, bold=True)
    s.text(640, 177, 'power-supply board (PLOŠNÝ SPOJ SE ZDROJI), dashed = board outline', 7.5)
    wy = {wn: (ya, yb) for wn, ya, yb, *_ in WIND}
    for wn, fu, (d, led, r), br, cap, plus, minus, volt in RECT:
        ya, yb = wy[wn]
        pole_h(s, fu, 620, 680, ya, '1', '2', 'fuse')
        s.text(650, ya - 7, '%s %s' % (fu, DEV[fu]['type_rating']), 7, 'middle')
        indicator(s, d, led, r, 700, ya)
        bridge(s, br, 780, 840, ya, yb)
        ecap_v(s, cap, 890, ya + 18, yb - 18)
        s.text(902, ya + 33, cap + q(cap), 8.5, bold=True,             # C4: also its 4 board traces (repair [?])
               rows=mk(cap, wires=('%s +>%s +' % (br, cap), '%s ->%s -' % (br, cap), '%s +>UG50 %s' % (cap, plus[0]),
                                   '%s ->UG50 %s' % (cap, minus))))
        s.text(902, ya + 45, DEV[cap]['type_rating'].replace(' [?]', ''), 6.5)
        for k, o in enumerate(plus):
            s.term('UG50', o, 1410, ya + 15 * k, 'W')
            s.text(1404, ya + 15 * k - 3, o, 7, 'end')
        s.term('UG50', minus, 1410, yb, 'W')
        s.text(1404, yb - 3, minus, 7, 'end')
        s.text(1150, ya - 4, volt, 8, 'middle')
        s.text(1150, yb - 4, '0 V', 8, 'middle')
    for wn, outs in OUTS.items():
        for o, y in outs:
            s.term('UG50', o, 1410, y, 'W')
            s.text(1404, y - 3, o, 7, 'end')
    ya, yb = wy['V']
    pole_h(s, 'FU25', 620, 680, ya, '1', '2', 'fuse')
    s.text(650, ya - 7, 'FU25 ' + DEV['FU25']['type_rating'], 7, 'middle')
    indicator(s, 'V15', 'V25', 'R15', 700, ya)
    s.text(1150, ya - 4, '~24 V', 8, 'middle')
    s.text(1150, yb - 4, '0 V', 8, 'middle')
    ya, yb = wy['VI']
    for fu, y, x in (('FU26', ya, 1000), ('FU27', ya + 70, 700)):
        pole_h(s, fu, 620, 680, y, '1', '2', 'fuse')
        s.text(650, y - 7, '%s %s' % (fu, DEV[fu]['type_rating']), 7, 'middle')
        s.text(1150, y - 4, '~48 V', 8, 'middle')
    indicator(s, 'V16', 'V26', 'R16', 1000, ya)
    indicator(s, 'V17', 'V27', 'R17', 700, ya + 70)
    s.text(1150, yb - 4, '0 V', 8, 'middle')
    for k, t in enumerate((
            'Windings: ' + '; '.join('%s %s %s -> %s' % (w[0], w[3], w[4], OUTV[w[0]]) for w in WIND if w[3])
            + '; ' + ', '.join(w[0] for w in WIND if not w[3]) + ' unused.',
            'Outputs 3, 8, 9, 15, 16 printed without destination. V13, V23 (ranges V11-V17, V21-V27) are not drawn: '
            'winding III has no fuse.',
            'Indicator pairs drawn anti-parallel; diode polarity not read. C4: photo shows a blue SAMWHA 4700µF 63V '
            'over the empty board places C3/C4: a repair (c144231), on-site list.',
            'The X5 list (2:02) names 9UG50, this sheet prints 8 and 9 unused: conflict, on-site list.')):
        s.text(560, 905 + 13 * k, t, 7.5)
    return s


# ---------------------------------------------------------------- wire routes and stubs
# ROUTE: 'x' = cross-reference stubs at both ends (as the paper draws them), 'vh' / 'hv' = L-shape
# (vertical or horizontal first; 'hv' is the default), a list = corner points between the two ends.
ROUTE = {'XP L3>FA4 1': 'x', 'XP N>FA3 3': 'x', 'XP N>XC7 N': 'x', 'X5 >XC3 6': 'x',
         'PE >XC3 PE': 'x', 'PE >X10 PE': 'x', 'PE >XC7 PE': 'x', 'PE >UZ1 PE': 'x', 'ZF1 PE>PE ': 'vh',
         'QF1 2>KM2 1': [(730, 700), (570, 700)], 'QF1 4>KM2 3': [(760, 715), (600, 715)],
         'QF1 6>KM2 5': [(790, 730), (630, 730)],
         'X10 6>KM4 1': [(790, 880), (880, 880), (880, 740), (905, 740)], 'KM4 1>KM4 3': [(905, 740), (945, 740)],
         'KM4 2>X10 4': [(905, 900), (730, 900)], 'KM4 4>X10 5': [(945, 920), (760, 920)],
         'X10 4>M1 V1': [(730, 1265), (600, 1265)], 'X10 5>M1 W1': [(760, 1280), (630, 1280)],
         'X10 6>M1 U1': [(790, 1250), (570, 1250)], 'UZ1 PE>XC1 PE': [(1350, 725), (1175, 725), (1175, 930)],
         'K1 14>XC3 5': [(1860, 800), (1900, 800)],
         'ZF2 PE>UZ1 PE': [(1350, 670)], 'XC3 PE>Y3 PE': [(1810, 1035), (1930, 1035)],
         'FA1 2>X11 2': 'vh', 'FA2 2>T1 400V': 'vh',
         'FU25 2>UG50 13': [(1380, 610), (1380, 624)], 'FU25 2>UG50 14': [(1380, 610), (1380, 638)],
         'R15 2>UG50 30': 'vh', 'R16 2>UG50 32': 'vh', 'R17 2>UG50 32': 'vh',
         'UG50 31>FU27 1': [(605, 720), (605, 790)]}
for _wn, _fu, (_d, _led, _r), _br, _cap, _plus, _minus, _v in RECT:
    _ya = [x[1] for x in WIND if x[0] == _wn][0]
    ROUTE['%s 2>UG50 %s' % (_r, [x[6] for x in WIND if x[0] == _wn][0])] = 'vh'
    ROUTE['%s +>UG50 %s' % (_cap, _plus[0])] = 'vh'
    for _k, _o in enumerate(_plus[1:], 1):
        ROUTE['%s +>UG50 %s' % (_cap, _o)] = [(890, _ya), (1380, _ya), (1380, _ya + 15 * _k)]
    ROUTE['%s ->UG50 %s' % (_cap, _minus)] = 'vh'
# STUB: points after the terminal, the last one is the arrow tip (default: 30 px away from the device)
STUB = {('XP L3>FA4 1', 'a'): [(170, 341), (170, 530), (200, 530)],
        ('XP N>FA3 3', 'a'): [(185, 370), (185, 470), (200, 470)],
        ('XP N>XC7 N', 'a'): [(185, 370), (185, 495), (200, 495)],
        ('KM1A 1>FA2 1', 'a'): [(456, 283), (456, 669)], ('KM1A 3>FA1 1', 'a'): [(476, 312), (476, 618)],
        ('PE >X11 PE', 'b'): [(200, 480)], ('PE >UZ1 PE', 'b'): [(1350, 750), (1372, 750), (1372, 715)]}
_k = 0
for _w in WIRES:
    if _w['a'] == ('PE', '') and _w['b'] != ('X5', ''):          # earthing-strip list, 2:01
        STUB[(_w['k'], 'a')] = [(90, 660 + 26 * _k), (110, 660 + 26 * _k)]
        _k += 1
_k = 0
for _w in WIRES:
    if _w['a'] == ('X5', ''):                                     # X5 list, 2:02, in the paper's order
        STUB[(_w['k'], 'a')] = [(330, 650 + 26 * _k), (350, 650 + 26 * _k)]
        _k += 1
SIDE = {('KM1A 1>FA2 1', 'a'): 'r', ('KM1A 3>FA1 1', 'a'): 'r'}
LABEL = {('QF1 44>BMR1 19', 'a'): 'BMR1 19 (7:01)'}             # print "(4:10)" names the contact, not the end
AWAY = {'S': 'N', 'N': 'S', 'E': 'W', 'W': 'E'}


def far_label(w, end, tips, sh):
    other = 'b' if end == 'a' else 'a'
    far = w[other]
    if (w['k'], end) in LABEL:
        return LABEL[(w['k'], end)]
    note, ref_ = w['note'], None
    if end == 'a':
        m = re.search(r'arrow "(\d:\d\d)"', note)
        ref_ = m and m.group(1)
    if not ref_:
        for qt in re.findall(r'"([^"]*)"', note):
            m = re.search(r'\((\d:\d\d(?:-(?:\d:)?\d\d)?)\)', qt)
            if m and far[0] and far[0] in qt:
                ref_ = m.group(1)
                break
    if not ref_ and (w['i'], other) in tips:
        sn, (x, _y) = tips[(w['i'], other)]
        ref_ = '%d:%02d' % (sn, sh[sn].col_of(x))
    if not ref_ and end == 'a':
        m = re.search(r'(?:\(|also )(\d:\d\d(?:-(?:\d:)?\d\d)?)', note)
        ref_ = m and m.group(1)
    return ' '.join(t for t in far if t) + (' (%s)' % ref_ if ref_ else '')


def draw_wires(sh):
    """Draw every wire row on sheets 2-3; returns {row index: sheets where it is drawn}."""
    def where(node):
        return next((n for n in sorted(sh) if node in sh[n].T), None)
    drawn, tips, plan = defaultdict(set), {}, []
    for w in WIRES:
        sa, sb = where(w['a']), where(w['b'])
        hint = ROUTE.get(w['k'])
        if sa and sa == sb and hint != 'x':
            A, B = sh[sa].T[w['a']], sh[sa].T[w['b']]
            pts = ([A, (A[0], B[1]), B] if hint == 'vh' else [A] + hint + [B] if isinstance(hint, list)
                   else [A, (B[0], A[1]), B])
            sh[sa].wire(pts, net(w['a']))
            drawn[w['i']].add(sa)
            continue
        for end, node, sn in (('a', w['a'], sa), ('b', w['b'], sb)):
            if not sn:
                continue
            p0 = sh[sn].T[node]
            pts = STUB.get((w['k'], end))
            if pts is None:
                dx, dy = DIRV[AWAY[sorted(sh[sn].lead.get(p0, {'S'}))[0]]]
                pts = [(p0[0] + 30 * dx, p0[1] + 30 * dy)]
            path = [p0] + pts
            tips[(w['i'], end)] = (sn, path[-1])
            plan.append((sn, w, end, path))
    for sn, w, end, path in plan:
        s = sh[sn]
        s.wire(path, net(w['a']))
        (px, py), (tx, ty) = path[-2], path[-1]
        d = 'E' if tx > px else 'W' if tx < px else 'S' if ty > py else 'N'
        s.arrow(tx, ty, d)
        lab, key, rows = far_label(w, end, tips, sh), 'W:' + rkey(w), ()
        if mark_of(w['evidence']) and not any(key in r for r, _t in s.marks):   # the row's mark: once per sheet
            lab, rows = lab + ' ' + mark_of(w['evidence']), (key,)
        s.label_at((tx, ty), lab, SIDE.get((w['k'], end), {'E': 'r', 'W': 'l', 'N': 'u', 'S': 'd'}[d]), rows=rows)
        drawn[w['i']].add(sn)
    return drawn


# ---------------------------------------------------------------- sheet 1: tables, descriptions
T1_ORDER = ['S30', 'S28', 'S27', 'S24', '', '', 'S19', 'S12, S13, S14', 'S10, S11', 'SQ1, SQ2', '', 'S5', 'S4', 'S2', 'S1']
T2_ORDER = ['PE', 'X11', 'X10', 'X8', 'X5', 'XC7', 'XC4', 'XC3', 'XC2', 'XC1', 'XP', 'XC50, XC60, XC70']
# table 3, copied from T/11_568_sheet1_variants.csv (photos 20261113_213530, 20261113_193408)
VARS = [('', '380V 50Hz', '415V 50Hz', '220V 50Hz', '220V 60Hz', '200V 50Hz'),
        ('P [kW]',) + ('5.5/4.5',) * 5, ('I [A]', '12/10', '12/10', '20/17', '20/17', '20/17'),
        ('M1', '3x380V', '3x415V', '3x220V', '3x220V', '3x200V'), ('M2', '3x380V', '3x415V', '3x220V', '3x220V', '3x200V'),
        ('M3', '3x380V', '3x415V', '3x220V', '3x220V', '3x200V'), ('QF1',) + ('10-16A',) * 5, ('QF2',) + ('1.6-2.5A',) * 5,
        ('FA1, FA2',) + ('12A',) * 5, ('FA3',) + ('12A',) * 5, ('FA4',) + ('6A',) * 5,
        ('KM1A,B (KM1A, KM1B)', '50Hz', '50Hz', '50Hz', '60Hz', '50Hz'),
        ('KM6-8 (KM6, KM7, KM8)', '50Hz', '50Hz', '50Hz', '60Hz', '50Hz'),
        ('KM2-4 (KM2, KM3, KM4)', '50Hz', '50Hz', '50Hz', '60Hz', '60Hz [?]')]
# components table: sheet box, names as printed, the device whose netlist row gives the value
# (a fourth item is the text of a grouped row, which names what each member serves)
COMP = [('2', 'C3', 'C3'), ('4', 'RC...', 'RC...'), ('4', 'V20', 'V20'),
        ('5', 'V01, V14', 'V01', 'diodes of sheet 5 (V01; V14, not the board part UG50/V14)'), ('5', 'V10', 'V10'),
        ('5', 'R10', 'R10'), ('5', 'RC11', 'RC11'), ('7', 'R14', 'R14'),
        ('3', 'V1, V2', 'V1', 'UG50 rectifiers (V1: +27 V, V2: +24 V)'), ('3', 'V4', 'V4'),
        ('3', 'V11-V17', 'V11', 'fuse-output indicator diodes, UG50 (V11-V17)'),
        ('3', 'V21-V27', 'V21', 'fuse-output indicator LEDs, UG50 (V21-V27)'),
        ('3', 'C1, C2', 'C1', 'UG50 filter capacitors (C1: +27 V, C2: +24 V)'), ('3', 'C4', 'C4'),
        ('3', 'R11, R12', 'R11', 'indicator resistors, UG50 (R11: V11/V21; R12: V12/V22)'),
        ('3', 'R14, R15', 'UG50/R14', 'indicator resistors, UG50 (R14 = UG50/R14: UG50/V14/V24; R15: V15/V25)'),
        ('3', 'R16, R17', 'R16', 'indicator resistors, UG50 (R16: V16/V26; R17: V17/V27)')]
NOTES = [('3. BĚHEM POHYBU NOŽE JSOU SEPNUTY STYKAČE KM1A, KM1B, KM2, KM3, KM6, KM7',
          'During knife movement contactors KM1A, KM1B, KM2, KM3, KM6, KM7 are closed.'),
         ('2. V HORNÍ POLOZE NOŽE JSOU SEPNUTY STYKAČE KM1A, KM1B, KM2, KM3',
          'With the knife in its top position contactors KM1A, KM1B, KM2, KM3 are closed.'),
         ('1. SCHEMA KRESLENO VE VYPNUTÉM STAVU ŘEZAČKY, KONCOVÉ SPÍNAČE A OVLADAČE VE VÝCHOZÍCH POLOHÁCH NA POČÁTKU '
          'PRACOVNÍHO CYKLU', 'Scheme drawn with the cutter switched off; limit switches and controls in their starting '
                             'positions at the start of the working cycle.')]
SHEETS = [('4', 'OSVĚTLENÍ, OVLÁDACÍ OBVODY', 'lighting, control circuits'), ('3', 'NAPÁJECÍ OBVODY', 'supply circuits'),
          ('2', 'SILOVÉ OBVODY', 'power circuits'), ('1', 'TABULKY, POPISY', 'tables, descriptions'),
          ('8', 'ZAPOJENÍ PLC', 'PLC wiring'), ('7, 6', 'OBVODY OVLÁDÁNÍ ŘEZU', 'cut control circuits'),
          ('5', 'SPOJKA ŘEZU, EL. MAGNETY, SIGNÁLY PRO PLC', 'cut clutch, electromagnets, signals for PLC')]


def fit(s, x, y, wd, t, size=8.5, bold=False, rows=()):
    if not t:
        return
    sz = min(size, (wd - 8) / (CW * len(t)))
    if sz < 6:
        sz, t = 6, t[:int((wd - 8) / (CW * 6)) - 1] + '…'
    s.text(x + 4, y, t, round(sz, 2), bold=bold, rows=rows)


def table(s, x, y, widths, rows, rh=16, size=8.5):
    """A cell is a text or (text, row keys) for a cell that carries the mark of not-sure rows."""
    for k, r in enumerate(rows):
        xx = x
        for c, (wd, t) in enumerate(zip(widths, r)):
            t, keys = t if isinstance(t, tuple) else (t, ())
            fit(s, xx, y + rh * k + rh - 4.5, wd, t, size, bold=(k == 0 or c == 0), rows=keys)
            xx += wd
    y1 = y + rh * len(rows)
    s.rect(x, y, x + sum(widths), y1, w=1)
    for k in range(1, len(rows)):
        s.line(x, y + rh * k, x + sum(widths), y + rh * k, w=0.45)
    xx = x
    for wd in widths[:-1]:
        xx += wd
        s.line(xx, y, xx, y1, w=0.45)
    return y1


def names_row(group):
    d0 = DEV[group.split(',')[0].strip()]
    return (marked(group), d0['function_en'], d0['term_cz_ru'])


def sheet1():
    s = Sheet(1, 1800, 980)
    frame(s, [], 'tables, descriptions (TABULKY, POPISY)', '20261113_213049')
    s.text(40, 52, '568-70.9001 sheet 1 of 8: tables, descriptions (TABULKY, POPISY)', 12, bold=True)
    s.text(40, 70, 'Redrawn 2026 from photos (20261113_213049.jpg), not an original document. Names and functions: '
                   'netlist/power_devices.csv; [?] = unclear, see spec/power.md.', 8.5)
    s.text(40, 94, '1. Table of switches and controls (1. TABULKA SPÍNAČŮ A OVLADAČŮ)', 9, bold=True)
    table(s, 40, 100, (110, 370, 380), [('designation', 'function (English)', 'function as printed (Czech)')]
          + [names_row(g) if g else ('', '', '') for g in T1_ORDER])
    s.text(40, 394, '2. Table of terminal strips and connectors (2. TABULKA SVORKOVNIC A KONEKTORŮ)', 9, bold=True)
    y1 = table(s, 40, 400, (130, 430, 300), [('designation', 'function (English)', 'function as printed (Czech)')]
               + [names_row(g) for g in T2_ORDER])
    earth(s, 100, 424)
    s.text(40, 646, 'Notes as printed (3, 2, 1):', 9, bold=True)
    for k, (cz, en) in enumerate(NOTES):
        fit(s, 36, 662 + 26 * k, 870, en, 8)
        fit(s, 36, 674 + 26 * k, 870, '(%s)' % cz, 8)
    s.rect(40, 760, 600, 900, w=1.2)
    struck = '1. General tolerances ISO 2768-mK (1. Všeobecné tolerance ISO 2768-mK.)'
    for k, t in enumerate(('Wiring diagram (SCHEMA ZAPOJENÍ)', 'Drawing no. (Č. SNÍMKU) 568-70.9001',
                           'Type (TYP) MS80PS,DS MS115PS,DS', 'Drawn by (VYPRACOVAL) Ing. Fotr',
                           'Approved (DATUM SCHV.) 27.11.1996', struck + ', struck through on the print',
                           'Redrawn 2026 from photos of the paper set; not an original document.')):
        s.text(50, 778 + 17 * k, t, 9 if k else 10, bold=(k == 0))
    s.line(48, 775 + 17 * 5, 52 + len(struck) * 9 * 0.55, 775 + 17 * 5, w=1.1)   # Consolas advance 0.55 em
    s.text(940, 94, 'Table of used components, by sheet (TABULKA POUŽITÝCH SOUČÁSTEK)', 9, bold=True)
    table(s, 940, 100, (50, 120, 130, 460), [('sheet', 'designation', 'value', 'function (English)')]
          + [(c[0], marked(c[1]), DEV[c[2]]['type_rating'].split(';')[0].replace(' [?]', ''),
              c[3] if len(c) > 3 else DEV[c[2]]['function_en']) for c in COMP])
    s.text(940, 424, '3. Table of variant designs 115/80 (3. TABULKA VARIANTNÍCH PROVEDENÍ 115/80)', 9, bold=True)
    table(s, 940, 430, (210, 100, 100, 100, 100, 100), VARS)
    s.text(940, 694, 'Sheet list as printed', 9, bold=True)
    table(s, 940, 700, (50, 300, 330), [('sheet', 'English', 'as printed (Czech)')] + [(a, c, b) for a, b, c in SHEETS])
    return s


# ---------------------------------------------------------------- checks and main
def sheet_checks(s):
    bad, T, S_ = [], s.txt, s.seg
    for i, a in enumerate(T):
        for b in T[i + 1:]:
            if a[0] < b[2] - 0.3 and b[0] < a[2] - 0.3 and a[1] < b[3] - 0.3 and b[1] < a[3] - 0.3:
                bad.append('sheet %d text overlap %r / %r' % (s.n, a[4], b[4]))
        for x1, y1, x2, y2, _ in S_:
            if (y1 == y2 and a[1] + 0.3 < y1 < a[3] - 0.3 and min(x1, x2) < a[2] - 0.3 and max(x1, x2) > a[0] + 0.3) or \
                    (x1 == x2 and a[0] + 0.3 < x1 < a[2] - 0.3 and min(y1, y2) < a[3] - 0.3 and max(y1, y2) > a[1] + 0.3):
                bad.append('sheet %d text on a wire %r' % (s.n, a[4]))
                break
    for i, a in enumerate(S_):
        for b in S_[i + 1:]:
            if a[4] == b[4]:
                continue
            if (a[1] == a[3] == b[1] == b[3] and min(max(a[0], a[2]), max(b[0], b[2])) > max(min(a[0], a[2]), min(b[0], b[2]))) or \
                    (a[0] == a[2] == b[0] == b[2] and min(max(a[1], a[3]), max(b[1], b[3])) > max(min(a[1], a[3]), min(b[1], b[3]))):
                bad.append('sheet %d different nets overlap at %s' % (s.n, a[:4]))
            elif any(on_seg(p, b, True) for p in (a[:2], a[2:4])) or any(on_seg(p, a, True) for p in (b[:2], b[2:4])):
                bad.append('sheet %d different nets touch: %s / %s' % (s.n, a[:4], b[:4]))
    pos = defaultdict(set)
    for node, p in s.T.items():
        pos[p].add(find(node))
    bad += ['sheet %d terminals of different nets at %s' % (s.n, p) for p, ns in pos.items() if len(ns) > 1]
    return bad


def checks(sh, drawn):
    bad = []
    for d, row in DEV.items():
        if d not in sh[int(row['sheet'])].words:                   # literal designation, also UG50/R14
            bad.append('sheet %s does not print %s' % (row['sheet'], d))
    for n in (2, 3):
        for c in range(1, len(sh[n].edges)):
            if '%02d' % c not in sh[n].words:
                bad.append('sheet %d ruler lacks %02d' % (n, c))
    for w in WIRES:
        if w['sheet'] in ('2', '3') and int(w['sheet']) not in drawn[w['i']]:
            bad.append('wire row %d %s not drawn on sheet %s' % (w['i'] + 2, w['k'], w['sheet']))
    used = 0
    if TAB.exists():                    # the extracted paths tables are local only; skipped on a clone
        for n, fn in ((2, '11_568_sheet2_paths.csv'), (3, '11_568_sheet3_paths.csv')):
            for r in read(TAB / fn):
                for c in re.findall(r'\d+', r['column']):
                    used += 1
                    if not 1 <= int(c) < len(sh[n].edges) or '%02d' % int(c) not in sh[n].words:
                        bad.append('sheet %d lacks column %s of its paths table' % (n, c))
    for s in sh.values():
        bad += sheet_checks(s)
    # marks: each not-sure row shows its mark ('[?]', 'est. ±1 col') exactly once on its own sheet (the row's
    # sheet field) and at most once on any other sheet; no text carries a double mark
    keys = {'D:' + d: (r['sheet'], mark_of(r['evidence'])) for d, r in DEV.items() if mark_of(r['evidence'])}
    keys.update({'W:' + rkey(w): (w['sheet'], mark_of(w['evidence'])) for w in WIRES if mark_of(w['evidence'])})
    once = 0
    for key, (own, m) in sorted(keys.items()):
        per = {n: [t for r, t in s.marks if key in r] for n, s in sh.items()}
        if own.isdigit() and len(per.get(int(own), [])) == 1 and all(len(v) <= 1 and all(m in t for t in v)
                                                                    for v in per.values()):
            once += 1
        else:
            bad.append('mark "%s" of %s (own sheet %s): %s' % (m, key, own, {n: v for n, v in per.items() if v}))
    for s in sh.values():
        bad += ['sheet %d marks %s, not a not-sure row' % (s.n, k) for r, _t in s.marks for k in r if k not in keys]
        bad += ['sheet %d double mark: %s' % (s.n, e) for e in s.top if '[?] [?]' in e]
    return bad, used, once, len(keys)


def main():
    sh = {2: sheet2(), 3: sheet3()}
    drawn = draw_wires(sh)
    sh[1] = sheet1()
    bad, used, once, nkeys = checks(sh, drawn)
    titles = {1: 'tables, descriptions', 2: 'power circuits', 3: 'supply circuits'}
    for n, s in sorted(sh.items()):
        (HERE / ('power_sheet%d.svg' % n)).write_text(
            s.svg('568-70.9001 sheet %d: %s (redrawn 2026, not an original document)' % (n, titles[n])),
            encoding='utf-8', newline='\n')
    rows23 = [w for w in WIRES if w['sheet'] in ('2', '3')]
    if not TAB.exists():
        print('local sources absent (static_dynamic_memory/): paths-table column check skipped')
    print('power_sheet1-3.svg written; wire rows of sheets 2-3 drawn on their sheet %d/%d; not-sure rows marked once '
          'on their sheet %d/%d; texts %s (overlap-checked; all text elements %s); wire segments %s; junction dots %s; '
          'paths-table columns checked %d; bad %d' % (
              sum(1 for w in rows23 if int(w['sheet']) in drawn[w['i']]), len(rows23), once, nkeys,
              '/'.join(str(len(sh[n].txt)) for n in (1, 2, 3)),
              '/'.join(str(sum(1 for e in sh[n].top if e.startswith('<text'))) for n in (1, 2, 3)),
              '/'.join(str(len(sh[n].seg)) for n in (2, 3)), '/'.join(str(len(junctions(sh[n]))) for n in (2, 3)),
              used, len(bad)))
    for b in bad[:60]:
        print('BAD', b)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
