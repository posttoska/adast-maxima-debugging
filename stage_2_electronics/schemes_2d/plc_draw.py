#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Draw sheet 8 of the wiring set 568-70.9001 (PLC, console terminal TABLO, inverter UZ1 control side,
encoder BR40, backgauge positioning signals) as SVG.

Run:    python -B stage_2_electronics/schemes_2d/plc_draw.py      (from the project folder, or from anywhere)
Reads:  ../netlist/plc_drive_devices.csv and plc_drive_wires.csv: every device, terminal, wire label, signal
        and mark on the sheet. ../netlist/power_wires.csv, control_wires.csv and power_devices.csv: the
        (sheet:column) references of the conductors that sheet 8 shares with sheets 2 and 5-7, taken from
        the same conductor's row there. This file holds only the layout (measured on photo 20261113_191800)
        and the printed texts that are no netlist data: titles, the Czech function column of table (40), the
        later ink. When static_dynamic_memory/ is present, table (40) as drawn is compared with its
        12_568_plc_io.csv (read off the paper); without it that comparison is skipped (INFO).
Writes: plc_sheet8.svg next to this file; prints a summary and 'result: PASS' (exit 0), or each failed check
        and 'result: FAIL' (exit 1). The output is the same byte for byte on every run.
Self-checks: every wire row drawn once with both ends on placed pins; every designation of the devices file
        printed; every wire label printed; ruler 01-05 printed; no two texts overlap; every reference beside a
        lead taken from the same conductor's row of the other threads (one kept as printed must lie in that
        row's columns); table (40) holds every row of a PLC, XC50 or XC60 terminal once, in the printed order;
        the 14 PLC addresses of check 4 each drawn at their terminal; each abbreviation of ABBR has its full
        name in brackets at its first use in the prose (header line, notes, device block, title block; quotes
        and the paper's printed labels stay as printed).
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NET = os.path.normpath(os.path.join(HERE, '..', 'netlist'))
TAB = os.path.normpath(os.path.join(HERE, '..', '..', 'static_dynamic_memory', 'blocks', 'generation_002',
                                    'artifacts', 'tables'))
CW = 0.6          # advance width of the monospace font, per unit of font size
W = 1680
FAIL, INFO, REFS = [], [], []


def rd(name, folder=NET):
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        FAIL.append('input missing: ' + path)
        return []
    with open(path, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


DEVS = rd('plc_drive_devices.csv')
WIRES = rd('plc_drive_wires.csv')
DEV = {d['designation']: d for d in DEVS}
OTHER = [('power_wires.csv', rd('power_wires.csv')), ('control_wires.csv', rd('control_wires.csv'))]
PDEV = {d['designation']: d for d in rd('power_devices.csv')}


def f(v):
    s = '%.2f' % v
    s = s.rstrip('0').rstrip('.')
    return s if s not in ('-0', '') else '0'


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


def ends(r):
    return frozenset({(r['from_device'], r['from_terminal']), (r['to_device'], r['to_terminal'])})


def wkey(r):
    return '%s %s -> %s %s' % (r['from_device'], r['from_terminal'], r['to_device'], r['to_terminal'])


# ---------------------------------------------------------------- layout (SVG px)
# Measured on photo 20261113_191800 reduced to 1300 px wide (r = x or y there): x = 30 + (r - 90) * 1.5,
# y = 125 + (r - 195) * 1.5. The paper's ruler is five ticks at irregular places, each over the current path
# it names (r = 144.7, 251.3, 321.0, 586.0, 678.6); here each number stands at its tick and the column boxes
# end halfway between ticks.
TICK = [112.05, 271.95, 376.5, 774.0, 912.9]
LEFT, RIGHT = 30.0, 990.0                  # drawing part (39); table (40) to the right of it
TOP_Y, BOT_Y = 580.5, 868.5                # outer edges of the PLC's two terminal strips (lead pins)
PLC_RECT = (70, 573, 988.5, 874.5)         # the PLC box as drawn; no text box may be cut by one of its edges
TOP_X0, BOT_X0, PITCH = 104.0, 99.0, 18.7
LEAD_GAP = 5.0                             # an open lead end (conductor continues on another sheet) stands
                                           # this far past the far end of its row's label (or of its [?])
BIND_GAP = (2.0, 8.0)                      # the check: the gap an open lead end may have to its own label
BUS_Y, LEFT_X = 463.1, 40.5                # +24V line over the strip and round the left edge (5XC4)
LANE = {'4': 976.0, '3': 985.0, '2': 994.0, '1': 1003.0, '5': 1012.0}   # XC4 pin -> harness lane
XC4_TOP, XC4_BOT = 968.0, 1020.0          # XC4 box; its contact numbers (7 px) sit inside, one per lane
XC4_L, XC4_R = 524.0, 540.0
SH_L, SH_R, SH_Y, SH_TOP, SH_BOT = 460.0, 605.0, 958.0, 969.0, 1019.0
BR40_PIN = {'A': 678.5, 'B': 698.9, 'I': 717.8, '+': 736.5, '-': 755.1}
BR40_BOX = (665.4, 1032.8, 765.9, 1098.5)
DSUB_TOP, DSUB_TOP_Y = [510.6, 645.0, 779.0, 907.7], 598.7     # 3rd = XC60, 4th = XC50 (printed names)
DSUB_BOT, DSUB_BOT_Y = [547.4, 679.7, 903.9], 850.0
XC60_X, XC50_X = [800.0, 810.0, 820.0, 830.0], [935.0, 960.0]   # pins of the used contacts, sorted names
LINK_Y = [292.0, 282.0, 272.0, 262.0]       # lane of each XC60 contact on its way to XC70
XC70_X = 490.0
PIN_SIZE = 7.0                              # contact numbers of XC4, XC50, XC60, XC70 (lead labels: 7.5)
PIN_TXT_Y = 570.0                           # XC50/XC60 contact numbers start just above the PLC box line (573)
TABLO_BOX = (81.1, 131.1, 544.2, 415.7)
OCT = (89.5, 142.1, 388.4, 407.3, 50.5)     # octagon x0, y0, x1, y1, chamfer
# TABLO terminal: position, height of its line to X10, printed sign, place of the sign
TABLO_T = {'PE': ((348.9, 148.0), 114.2, '⏚', (333.0, 165.0)),
           '-': ((360.6, 158.9), 139.4, '−', (357.5, 180.0)),
           '+24V': ((374.1, 171.5), 167.2, '+', (371.0, 189.0))}
X10_X, X5_X = 771.5, 805.0
TABLE_X = [1010.0, 1072.0, 1128.0, 1192.0, 1318.0, 1590.0]
TABLE_Y0, TABLE_HEAD, TABLE_ROW = 148.0, 18.0, 14.0

# Where the paper draws one netlist terminal twice, the far end of a row picks the drawn copy.
SLOTS = {('PLC', '+24V'): {('X10', '35'): '1', ('XC4', '5'): '2'},
         ('PLC', 'GND'): {('UZ1', '39'): '1', ('X5', ''): '2'},
         ('PLC', 'IN-GND'): {('XC4', '4'): '1', ('XC4', 'shell'): '2'},
         ('X5', ''): {('X10', '45'): 'tablo', ('PLC', 'GND'): 'plc'}}
# An open end that meets a printed line instead of ending free: the +24V lead of 35X10 ends on the +24V line.
OPEN_AT = {('X10', '35', ''): BUS_Y}
# References printed differently from the conductor's row in the other thread's file: kept as printed and
# checked to lie in that row's columns.
PRINTED_REF = {'33X10': '(6:15)'}
# Table (40) cells printed differently from the netlist: kept as printed, marked [?], checked against the
# value the netlist gives (key = PLC column of the table).
PRINTED_LINIE = {'GND PLC': ('2:01', '2:02')}
# Table (40): order of the printed rows by its PLC column ('' = printed blank row) and the printed Czech
# function text of each (two texts where the PLC column repeats).
ORDER = (['IN-%X' % i for i in range(16)] + ['IN-GND'] + ['OUT-%X' % i for i in range(14)] +
         ['OUT +24V', 'OUT-GND', '', '+24V PLC', 'GND PLC', '', '6+9 XC50', '4 XC50', '', '2 XC60', '3 XC60',
          '5 XC60'])
CZ = {'IN-0': 'SIGNÁL PROVEDENÍ ŘEZU', 'IN-1': 'S28 - PLECH LISOVADLA', 'IN-2': 'S30 - POLOHA LISOVADLA',
      'IN-8': 'SIGNÁL FUNKCE POHONU', 'IN-9': 'S27 - ZADNÍ POLOHA SEDLA', 'IN-A': 'S24 - PŘEDNÍ POLOHA SEDLA',
      'IN-D': 'BR40 - INDEX (I)', 'IN-E': 'BR40 - KANÁL "B"', 'IN-F': 'BR40 - KANÁL "A"',
      'IN-GND': ('BR40 - GND', 'BR40 - STÍNĚNÍ'), 'OUT-0': 'BLOKOVÁNÍ POSUV - ŘEZ', 'OUT-9': 'OVLÁDÁNÍ Y3',
      'OUT-B': 'POSUV VPŘED', 'OUT-C': 'POSUV VZAD', 'OUT-D': 'BLOKOVÁNÍ UZ1', 'OUT +24V': 'BR40 - +24V',
      'OUT-GND': 'UZ1 - GND', '+24V PLC': 'NAPÁJENÍ PLC', 'GND PLC': 'NAPÁJENÍ PLC',
      '6+9 XC50': 'ŘÍZENÍ RYCHLOSTI SEDLA', '4 XC50': 'ŘÍZENÍ RYCHLOSTI SEDLA', '2 XC60': 'PROPOJENÍ PLC-TABLO',
      '3 XC60': '(STÍNĚNÍ PŘIPOJENO', '5 XC60': 'NA KOVOVÝ PLÁŠŤ KONEKTORU)'}
# The printed remark split over rows 3 and 5 XC60 (an open bracket in one row, its close in the next)
# belongs to the link shield (the shell row of plc_drive_wires.csv); its English is added to the
# English cell of the same two rows.
EN_REMARK = {'3 XC60': '(shield connected to the', '5 XC60': 'metal shell of the connector)'}
STALE = ('not saved',)     # a phrase of an older state that must not come back
ADDR14 = ['IN-0', 'IN-1', 'IN-2', 'IN-8', 'IN-9', 'IN-A', 'IN-D', 'IN-E', 'IN-F',
          'OUT-0', 'OUT-9', 'OUT-B', 'OUT-C', 'OUT-D']
# own devices: drawn extent in x (for the column INFO check)
EXTENT = {'PLC': (70.0, 988.5), 'TABLO': (81.1, 544.2), 'BR40': (665.4, 765.9), 'XC4': (SH_L, SH_R),
          'XC50': (852.7, 962.7), 'XC60': (724.0, 834.0), 'XC70': (380.0, 390.0)}


class Sheet:
    def __init__(s):
        s.body, s.texts, s.segs = [], [], []
        s.cores = []         # (core box, text): where the glyph strokes are; no line may run through one
        s.pins = {}          # (device, terminal, slot) -> (x, y, lead direction or '')
        s.ndrawn = 0
        s.labelled = set()
        s.circles = set()    # terminal circles: a junction there needs no dot
        s.open_ends = {}     # far end of a lead to a device not drawn here -> (row key, row, pin it leaves, key)
        s.rowpts = {}        # row key -> its drawn polyline
        s.dotpts = set()     # junction dot centres

    def add(s, frag):
        s.body.append(frag)

    @staticmethod
    def box(x, y, t, size, anchor, rot):
        w = len(t) * size * CW
        if rot:     # rotate(-90) about (x, y): the text runs upward, glyphs stand left of x
            y1 = y if anchor == 'start' else y + w / 2 if anchor == 'middle' else y + w
            return (x - size * 0.8, y1 - w, x + size * 0.22, y1)
        x0 = x - w if anchor == 'end' else x - w / 2 if anchor == 'middle' else x
        return (x0, y - size * 0.8, x0 + w, y + size * 0.22)

    def text(s, x, y, t, size=8, anchor='start', cls='t', rot=False):
        s.texts.append(s.box(x, y, t, size, anchor, rot) + (t,))
        w = len(t) * size * CW
        s0 = {'start': 0, 'middle': -w / 2, 'end': -w}[anchor]
        lo, hi = 0.05 * size, 0.62 * size      # the band above the baseline that the strokes fill
        s.cores.append(((x - hi, y - s0 - w + 0.4, x - lo, y - s0 - 0.4) if rot else
                        (x + s0 + 0.4, y - hi, x + s0 + w - 0.4, y - lo), t))
        a = '' if anchor == 'start' else ' text-anchor="%s"' % anchor
        r = ' transform="rotate(-90 %s %s)"' % (f(x), f(y)) if rot else ''
        body = esc(t)
        if cls != 'q':      # the unclear mark is always red, also inside a longer text
            body = body.replace('[?]', '<tspan class="q">[?]</tspan>')
        s.add('<text x="%s" y="%s" font-size="%s"%s%s class="%s">%s</text>' % (f(x), f(y), f(size), a, r, cls, body))

    def line(s, pts, cls='w', seg=True):
        pts = [(round(x, 2), round(y, 2)) for x, y in pts]
        if seg:
            for a, b in zip(pts, pts[1:]):
                if a != b:
                    s.segs.append((a, b))
        s.add('<polyline points="%s" class="%s"/>' % (' '.join('%s,%s' % (f(x), f(y)) for x, y in pts), cls))

    def rect(s, x0, y0, x1, y1, cls='r'):
        s.add('<rect x="%s" y="%s" width="%s" height="%s" class="%s"/>' % (f(x0), f(y0), f(x1 - x0), f(y1 - y0), cls))

    def poly(s, pts, cls='b'):
        s.add('<polygon points="%s" class="%s"/>' % (' '.join('%s,%s' % (f(x), f(y)) for x, y in pts), cls))

    def circle(s, x, y, r, cls='tc'):
        s.add('<circle cx="%s" cy="%s" r="%s" class="%s"/>' % (f(x), f(y), f(r), cls))

    def pin(s, key, x, y, d=''):
        if key in s.pins:
            FAIL.append('pin %s placed twice' % ':'.join(key))
        if key[0] not in DEV:
            FAIL.append('pin of a device not in plc_drive_devices.csv: %s' % key[0])
        s.pins[key] = (round(x, 2), round(y, 2), d)


def dlabel(s, x, y, name, size, anchor):
    """A device's name; a red [?] follows it when its row in plc_drive_devices.csv is not sure."""
    ev = DEV[name]['evidence'] if name in DEV else ''
    if ev in ('', 'sure'):
        s.text(x, y, name, size, anchor, 'd')
    else:
        s.text(x, y, '%s %s' % (name, ev), size, anchor, 'd')
        QLABEL.append(name)


QLABEL = []


def slot(dev, term, other):
    """The drawn copy of a terminal a row lands on, where the paper draws one terminal twice."""
    if dev == 'XC4' and term != 'shell':
        return 'L' if other[0] == 'PLC' else 'R'
    pick = SLOTS.get((dev, term))
    if pick is None:
        return ''
    if other not in pick:
        FAIL.append('no drawn copy of %s:%s for a row to %s:%s' % ((dev, term) + other))
        return '?'
    return pick[other]


def keys(r):
    a, b = (r['from_device'], r['from_terminal']), (r['to_device'], r['to_terminal'])
    return a + (slot(a[0], a[1], b),), b + (slot(b[0], b[1], a),)


def joined(r):
    e = ends(r)
    hits = [(name, i, o) for name, rows in OTHER for i, o in enumerate(rows, 2) if ends(o) == e]
    if len(hits) > 1:
        FAIL.append('row %s matches %d rows of the other threads' % (wkey(r), len(hits)))
    return hits[0] if hits else None


def ref(r, keep=True):
    """'(sheet:column)' of the same conductor's row in power_wires.csv or control_wires.csv ('' if none);
    keep=False only measures the label (no REFS line, no FAIL)."""
    j = joined(r)
    if not j:
        return ''
    name, i, o = j
    got = '(%s:%s)' % (o['sheet'], o['column'])
    if r['wire'] in PRINTED_REF:
        p = PRINTED_REF[r['wire']]
        m = re.fullmatch(r'\((\d+):(\d\d)\)', p)
        cols = [int(c) for c in re.findall(r'\d+', o['column'])]
        if keep and not (m and cols and m.group(1) == o['sheet'] and min(cols) <= int(m.group(2)) <= max(cols)):
            FAIL.append('reference of %s kept as printed %s does not fit %s line %d %s' % (r['wire'], p, name, i, got))
        if keep:
            REFS.append('%s %s (printed; %s line %d gives %s)' % (r['wire'], p, name, i, got))
        return p
    if keep:
        REFS.append('%s %s (%s line %d)' % (r['wire'], got, name, i))
    return got


def plc_pos(term, sl):
    if term.startswith('OUT-'):
        return TOP_X0 + PITCH * int(term[4:], 16), TOP_Y, 'up'
    if term == '+24V':
        return TOP_X0 + PITCH * (13 + int(sl)), TOP_Y, 'up'
    if term == 'GND':
        return TOP_X0 + PITCH * (15 + int(sl)), TOP_Y, 'up'
    if term == 'IN-GND':
        return BOT_X0 + PITCH * (15 + int(sl)), BOT_Y, 'down'
    if term.startswith('IN-'):
        return BOT_X0 + PITCH * int(term[3:], 16), BOT_Y, 'down'
    FAIL.append('PLC terminal %s has no place on the strips' % term)
    return None


# ---------------------------------------------------------------- symbols

def frame(s):
    s.text(LEFT, 24, xp('Wiring set 568-70.9001, sheet 8: PLC (programmable logic controller), console terminal '
                        'TABLO, inverter UZ1 control side, encoder BR40'), 11, 'start', 'd')
    bounds = [LEFT] + [(a + b) / 2 for a, b in zip(TICK, TICK[1:])] + [RIGHT]
    for c in range(5):
        s.rect(bounds[c], 38, bounds[c + 1], 54)
        s.text(TICK[c], 50, '%02d' % (c + 1), 8, 'middle', 'd')
    s.rect(RIGHT + 14, 38, W - 30, 54)
    s.text((RIGHT + W - 16) / 2, 50, 'table (40): no columns on the paper', 7, 'middle', 'n')
    zones = [(LEFT, RIGHT, '(39) ZAPOJENÍ ŘÍDÍCÍHO AUTOMATU - PLC (wiring of the control automaton, PLC)'),
             (RIGHT + 14, W - 30, '(40) TABULKA PŘIPOJENÍ ŘÍDÍCÍHO AUTOMATU - PLC A OVLÁDACÍHO TABLA '
                                  '(connection table of the PLC and the control panel)')]
    for x0, x1, t in zones:
        s.rect(x0 + 1, 62, x1 - 1, 98, 'z')
        n = int((x1 - x0 - 8) / (7 * CW))
        for i, ln in enumerate(wrap(t, n)):
            s.text((x0 + x1) / 2, 75 + i * 9, ln, 7, 'middle', 't')
    return bounds


def tablo(s):
    s.rect(*TABLO_BOX, cls='r')
    x0, y0, x1, y1, c = OCT
    s.poly([(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c),
            (x0, y0 + c)], 'e')
    # slanted terminal block on the upper right chamfer
    t0, t1 = TABLO_T['PE'][0], TABLO_T['+24V'][0]
    u, n = (0.7071, 0.7071), (0.7071, -0.7071)
    a = (t0[0] - 9 * u[0], t0[1] - 9 * u[1])
    b = (t1[0] + 9 * u[0], t1[1] + 9 * u[1])
    s.poly([(a[0] + 7 * n[0], a[1] + 7 * n[1]), (b[0] + 7 * n[0], b[1] + 7 * n[1]),
            (b[0] - 7 * n[0], b[1] - 7 * n[1]), (a[0] - 7 * n[0], a[1] - 7 * n[1])], 'b')
    for term, ((x, y), ly, sign, (lx, lyy)) in TABLO_T.items():
        s.circle(x, y, 2.6)
        s.pin(('TABLO', term, ''), x, y)
        s.text(lx, lyy, sign, 9 if term == 'PE' else 8, 'middle', 'd')
    for (sy0, sy1) in ((196.7, 243.0), (255.5, 302.0), (310.0, 348.0)):
        s.rect(380, sy0, 390, sy1, 'b')
    dlabel(s, 376, 282, 'XC70', 8, 'end')
    s.poly([(393, 270), (420, 270), (420, 260), (443, 277), (420, 294), (420, 284), (393, 284)], 'b')
    s.text(447, 281, 'PLC', 8, 'start', 'd')
    s.text(128, 360, 'POHLED ZE ZADNÍ STRANY (view from the rear side)', 7.5, 'start', 't')
    s.text(TABLO_BOX[0], 432, 'TABLO = OVLÁDACÍ TABLO (control panel in the console), drawn from its rear', 8, 'start', 'd')
    # X10 terminals at column 04 and the arrow to X5
    used = sorted({(r['from_terminal'] if r['from_device'] == 'TABLO' else r['to_terminal'],
                    r['to_terminal'] if r['from_device'] == 'TABLO' else r['from_terminal'],
                    r['to_device'] if r['from_device'] == 'TABLO' else r['from_device'])
                   for r in WIRES if 'TABLO' in (r['from_device'], r['to_device'])})
    for tt, ft, fd in used:
        if fd != 'X10' or tt not in TABLO_T:
            FAIL.append('TABLO terminal %s to %s:%s has no place' % (tt, fd, ft))
            continue
        y = TABLO_T[tt][1]
        s.circle(X10_X, y, 2.8)
        s.line([(X10_X - 2.4, y + 2.4), (X10_X + 2.4, y - 2.4)], 'e', seg=False)
        s.pin(('X10', ft, ''), X10_X, y)
        s.circles.add((X10_X, y))
    for r in WIRES:
        if {r['from_device'], r['to_device']} == {'X5', 'X10'}:
            ft = r['to_terminal'] if r['to_device'] == 'X10' else r['from_terminal']
            if ('X10', ft, '') not in s.pins:
                FAIL.append('X5 row %s: X10 %s not drawn' % (wkey(r), ft))
                continue
            y = s.pins[('X10', ft, '')][1]
            s.pin(('X5', '', 'tablo'), X5_X, y)
            s.poly([(X5_X, y - 5), (X5_X + 10, y), (X5_X, y + 5)], 'b')
            d = PDEV.get('X5')
            where = '(%s:%s)' % (d['sheet'], d['column']) if d else ''
            if not d:
                FAIL.append('X5 missing from power_devices.csv: no reference for the arrow')
            s.text(X5_X + 15, y + 3, 'X5 ' + where, 8, 'start', 'd')
            REFS.append('X5 arrow %s (power_devices.csv row X5)' % where)


def strip(s, y0, y1, yc, x0, nums, side):
    for i in range(18):
        x = x0 + PITCH * i
        s.rect(x - PITCH / 2, y0, x + PITCH / 2, y1)
        s.circle(x, yc, 4)
        s.line([(x - 2.8, yc + 2.8), (x + 2.8, yc - 2.8)], 'e', seg=False)
    ny = 646 if side == 'top' else 808
    for i, t in enumerate(nums):
        s.text(x0 + PITCH * i, ny, t, 8, 'middle', 't')


def brace(s, xa, xb, y, up):
    d = -1 if up else 1
    xm = (xa + xb) / 2
    s.line([(xa - 6, y), (xa - 3, y + 4 * d), (xm - 2, y + 4 * d), (xm, y + 8 * d), (xm + 2, y + 4 * d),
            (xb + 3, y + 4 * d), (xb + 6, y)], 'e', seg=False)


def dsub(s, cx, cy):
    s.rect(cx - 55, cy - 20, cx + 55, cy + 20)
    for dx in (-45, 45):
        s.circle(cx + dx, cy, 3.2, 'dot')
    s.poly([(cx - 30, cy - 11), (cx + 30, cy - 11), (cx + 37, cy + 11), (cx - 37, cy + 11)], 'b')
    for i in range(4):
        s.circle(cx - 15 + 10 * i, cy - 5, 1.8)
    for i in range(5):
        s.circle(cx - 20 + 10 * i, cy + 5, 1.8)


def arrow_up(s, cx, base, tip):
    s.poly([(cx - 7, base), (cx - 7, tip + 18), (cx - 14, tip + 18), (cx, tip), (cx + 14, tip + 18),
            (cx + 7, tip + 18), (cx + 7, base)], 'b')


def plc(s):
    s.rect(*PLC_RECT, cls='b')
    s.line([(70, 621), (988.5, 621)], 'e', seg=False)
    s.line([(70, 823), (988.5, 823)], 'e', seg=False)
    strip(s, 580.5, 621, 595, TOP_X0, list('0123456789ABCD'), 'top')
    strip(s, 832.5, 868.5, 858, BOT_X0, list('0123456789ABCDEF'), 'bottom')
    s.text(98, 668, 'OUT', 8, 'start', 't')
    p1, p2 = TOP_X0 + PITCH * 14, TOP_X0 + PITCH * 15
    g1, g2 = TOP_X0 + PITCH * 16, TOP_X0 + PITCH * 17
    brace(s, p1, p2, 632, False)
    brace(s, g1, g2, 632, False)
    s.text((p1 + p2) / 2, 665, '+24V', 8, 'middle', 't')
    s.text((g1 + g2) / 2, 665, 'GND', 8, 'middle', 't')
    s.text(BOT_X0 - 6, 789, 'IN', 8, 'start', 't')
    i1, i2 = BOT_X0 + PITCH * 16, BOT_X0 + PITCH * 17
    s.text((i1 + i2) / 2, 789, 'GND', 8, 'middle', 't')
    brace(s, i1, i2, 803, True)
    s.text(595, 730, 'COMPACT PLC', 13, 'middle', 'd')
    for i, cx in enumerate(DSUB_TOP):
        dsub(s, cx, DSUB_TOP_Y)
    for cx in DSUB_BOT:
        dsub(s, cx, DSUB_BOT_Y)
    dlabel(s, DSUB_TOP[2], 643, 'XC60', 8, 'middle')
    dlabel(s, DSUB_TOP[3], 643, 'XC50', 8, 'middle')
    arrow_up(s, DSUB_TOP[2], 547, 506.4)
    arrow_up(s, DSUB_TOP[3], 547, 506.4)
    s.text(DSUB_TOP[2], 497, 'TABLO', 8, 'middle', 'd')
    s.text(DSUB_TOP[3], 497, 'UZ1', 8, 'middle', 'd')
    # pins of the used PLC terminals
    for r in WIRES:
        for k in keys(r):
            if k[0] == 'PLC' and k not in s.pins:
                p = plc_pos(k[1], k[2])
                if p:
                    s.pin(k, *p)
    # contacts of XC60 and XC50 used by rows: pins on the top edge, sorted by contact name
    for dev, xs in (('XC60', XC60_X), ('XC50', XC50_X)):
        used = sorted({k[1] for r in WIRES for k in keys(r) if k[0] == dev})
        if len(used) > len(xs):
            FAIL.append('%s: %d contacts used, %d places' % (dev, len(used), len(xs)))
            continue
        for t, x in zip(used, xs):
            s.pin((dev, t, ''), x, DSUB_TOP_Y - 20, 'up' if dev == 'XC50' else '')   # XC50: leads to UZ1
            if dev == 'XC60':       # left of its lead (the leads stand 10 px apart)
                s.text(x - 2.2, PIN_TXT_Y, t, PIN_SIZE, 'start', 'n', rot=True)
            else:                   # right of its lead: the lead label stands left of it
                s.text(x + 7, PIN_TXT_Y, t, PIN_SIZE, 'start', 'n', rot=True)


def xc4_br40(s):
    s.rect(XC4_L, XC4_TOP, XC4_R, XC4_BOT, 'b')
    for t, y in LANE.items():
        s.pin(('XC4', t, 'L'), XC4_L, y)
        s.pin(('XC4', t, 'R'), XC4_R, y)
        s.text((XC4_L + XC4_R) / 2, y + 2.5, t, PIN_SIZE, 'middle', 'n')
    dlabel(s, (XC4_L + XC4_R) / 2, 1030, 'XC4', 8, 'middle')
    for x in (SH_L, SH_R):
        s.add('<ellipse cx="%s" cy="%s" rx="9" ry="%s" class="bd"/>' % (f(x), f((SH_TOP + SH_BOT) / 2), f((SH_BOT - SH_TOP) / 2)))
    s.pin(('XC4', 'shell', ''), SH_L, SH_TOP)
    s.line([(SH_L, SH_Y), (SH_R, SH_Y), (SH_R, SH_TOP)])     # 7XC4 bonds both shells (printed)
    x0, y0, x1, y1 = BR40_BOX
    s.rect(x0, y0, x1, y1, 'b')
    for t, x in BR40_PIN.items():
        s.pin(('BR40', t, ''), x, y0)
        s.text(x, y0 + 13, '−' if t == '-' else t, 8, 'middle', 't')
    dlabel(s, (x0 + x1) / 2, y0 + 45, 'BR40', 9, 'middle')


def xc70_pins(s):
    for r in WIRES:
        if {r['from_device'], r['to_device']} == {'XC60', 'XC70'}:
            a = (r['from_device'], r['from_terminal'])
            b = (r['to_device'], r['to_terminal'])
            p60, p70 = (a, b) if a[0] == 'XC60' else (b, a)
            used = sorted({k[1] for rr in WIRES for k in keys(rr) if k[0] == 'XC60'})
            y = LINK_Y[used.index(p60[1])]
            s.pin(('XC70', p70[1], ''), XC70_X, y)
            s.circle(XC70_X, y, 2.6)          # XC70's contact, right of the printed arrow "XC70 => PLC"
            s.circles.add((XC70_X, y))
            s.text(XC70_X - 5.5, y + 2.5, p70[1], PIN_SIZE, 'end', 'n')   # clear of the circle (r 2.6)


# ---------------------------------------------------------------- wires

def route(s, r, pa, pb, ka, kb):
    """Polyline of a row from pin a to pin b."""
    (ax, ay, _), (bx, by, _) = pa, pb
    devs = {ka[0], kb[0]}
    if ka[0] == 'TABLO' or kb[0] == 'TABLO':
        (tx, ty), (ox, oy) = ((ax, ay), (bx, by)) if ka[0] == 'TABLO' else ((bx, by), (ax, ay))
        mid = (tx + (ty - oy), oy)
        pts = [(tx, ty), mid, (ox, oy)]
        return pts if ka[0] == 'TABLO' else pts[::-1]
    if ('PLC', '+24V', '2') in (ka, kb):
        pts = [(ax, ay), (ax, BUS_Y), (LEFT_X, BUS_Y), (LEFT_X, by), (bx, by)]
        return pts if ka[0] == 'PLC' else pts[::-1]
    if ('XC4', 'shell', '') in (ka, kb):
        p, q = (pa, pb) if ka[0] == 'PLC' else (pb, pa)
        pts = [(p[0], p[1]), (p[0], SH_Y), (q[0], SH_Y), (q[0], q[1])]
        return pts if ka[0] == 'PLC' else pts[::-1]
    if devs == {'PLC', 'XC4'} or devs == {'XC60', 'XC70'}:     # down/up the lead first, then along the lane
        p, q = (pa, pb) if ka[0] in ('PLC', 'XC60') else (pb, pa)
        pts = [(p[0], p[1]), (p[0], q[1]), (q[0], q[1])]
        return pts if ka[0] in ('PLC', 'XC60') else pts[::-1]
    if devs == {'XC4', 'BR40'}:                                   # along the lane, then down into BR40
        p, q = (pa, pb) if ka[0] == 'XC4' else (pb, pa)
        pts = [(p[0], p[1]), (q[0], p[1]), (q[0], q[1])]
        return pts if ka[0] == 'XC4' else pts[::-1]
    if ax == bx or ay == by:
        return [(ax, ay), (bx, by)]
    FAIL.append('row %s: no route rule' % wkey(r))
    return [(ax, ay), (bx, by)]


def leads(s):
    """Open ends: a row from a pin with a lead direction to a device not drawn here gets a lead with
    'wire (sheet:column)', the conductor's place on the sheet where it continues; the lead ends LEAD_GAP past
    the far end of that label (lead_label() draws it), or where OPEN_AT says it meets a drawn line."""
    for r in WIRES:
        ka, kb = keys(r)
        for k, o in ((ka, kb), (kb, ka)):
            if k in s.pins and o not in s.pins and s.pins[k][2]:
                x, y, d = s.pins[k]
                near, far = label_span((r['wire'] + ' ' + ref(r, keep=False)).strip(),
                                       r['evidence'].startswith('[?]'), d)
                ye = OPEN_AT.get(o, far - LEAD_GAP if d == 'up' else far + LEAD_GAP)
                s.pin(o, x, ye)
                s.open_ends[(round(x, 2), round(ye, 2))] = (wkey(r), r, s.pins[k], o)


def label_span(t, q, d):
    """(near, far) y of a lead label as lead_label() draws it, its red [?] included."""
    w = len(t) * 7.5 * CW
    if d == 'up':
        return TOP_Y - 11, (TOP_Y - 15 - w - 3 * 7 * CW) if q else (TOP_Y - 11 - w)
    return BOT_Y + 10, (BOT_Y + 14 + w + 3 * 7 * CW) if q else (BOT_Y + 10 + w)


def lead_label(s, r, x, d):
    t = (r['wire'] + ' ' + ref(r)).strip()
    q = r['evidence'].startswith('[?]')
    # labels start outside the PLC box (edges y 573 and 874.5, beyond the pin rows), so no edge strikes a glyph
    if d == 'up':
        s.text(x - 2.5, TOP_Y - 11, t, 7.5, 'start', 'wl', rot=True)
        if q:
            s.text(x - 2.5, TOP_Y - 15 - len(t) * 7.5 * CW, '[?]', 7, 'start', 'q', rot=True)
    else:
        s.text(x - 2.5, BOT_Y + 10, t, 7.5, 'end', 'wl', rot=True)
        if q:
            s.text(x - 2.5, BOT_Y + 14 + len(t) * 7.5 * CW, '[?]', 7, 'end', 'q', rot=True)
    s.labelled.add(r['wire'])


def wires(s):
    linkn = 0
    for r in WIRES:
        ka, kb = keys(r)
        pa, pb = s.pins.get(ka), s.pins.get(kb)
        if pa is None or pb is None:
            FAIL.append('row %s: end not placed (%s)' % (wkey(r), ':'.join(ka if pa is None else kb)))
            continue
        pts = route(s, r, pa, pb, ka, kb)
        q = r['evidence'].startswith('[?]')
        s.line(pts, 'wq' if q else 'w')
        s.rowpts[wkey(r)] = [(round(x, 2), round(y, 2)) for x, y in pts]
        s.ndrawn += 1
        # label of the row
        lead = [(k, p) for k, p in ((ka, pa), (kb, pb)) if p[2]]
        if lead and r['wire']:
            k, p = lead[0]
            lead_label(s, r, p[0], p[2])
        elif 'TABLO' in (ka[0], kb[0]):
            x10 = pa if ka[0] == 'X10' else pb
            if r['wire'] not in s.labelled:
                if ka[1] == 'PE' or kb[1] == 'PE':
                    s.text(x10[0] + 6, x10[1] + 3, r['wire'], 7.5, 'start', 'wl')
                else:
                    s.text(x10[0], x10[1] + 11, r['wire'], 7.5, 'middle', 'wl')
                    rf = ref(r)
                    if rf:
                        s.text(x10[0], x10[1] + 20, rf, 7, 'middle', 't')
                s.labelled.add(r['wire'])
        elif {ka[0], kb[0]} == {'XC60', 'XC70'}:
            y = pts[-1][1]
            x = 560 + 60 * linkn
            linkn += 1
            if r['wire']:
                s.text(x, y - 2.5, r['wire'], 7, 'start', 'wl')
                s.labelled.add(r['wire'])
            if q:
                s.text(x + (len(r['wire']) * 4.2 + 4 if r['wire'] else 0), y - 2.5, '[?]', 7, 'start', 'q')
            if ka[1] == 'shell' or kb[1] == 'shell':
                s.text(x + 18, y - 2.5, 'shield (which end is bonded: not printed)', 6.5, 'start', 'n')
        elif r['wire'] and r['wire'] not in s.labelled:
            FAIL.append('row %s: label %s has no place' % (wkey(r), r['wire']))


def dots(s):
    segs = sorted({(a, b) if a < b else (b, a) for a, b in s.segs})
    pts = sorted({p for sg in segs for p in sg})
    n = 0
    for p in pts:
        if p in s.circles:
            continue
        dirs = set()
        for a, b in segs:
            for u, v in ((a, b), (b, a)):
                if u == p:
                    dirs.add((v[0] > u[0]) - (v[0] < u[0]) + 3 * ((v[1] > u[1]) - (v[1] < u[1])))
            if p != a and p != b and min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]):
                if a[0] == b[0] and p[0] == a[0]:
                    dirs.update((3, -3))
                elif a[1] == b[1] and p[1] == a[1]:
                    dirs.update((1, -1))
        if len(dirs) >= 3:
            s.circle(p[0], p[1], 2.3, 'dot')
            s.dotpts.add(p)
            n += 1
    return n


# ---------------------------------------------------------------- table (40)

def tkey(r):
    e = [(r['from_device'], r['from_terminal']), (r['to_device'], r['to_terminal'])]
    if any(d == 'PLC' for d, t in e):
        return r['plc_address']
    for d, t in e:
        if d in ('XC50', 'XC60') and t != 'shell':
            return '%s %s' % (t, d)
    return None


def linie(r):
    j = joined(r)
    sh, col = (j[2]['sheet'], j[2]['column']) if j else (r['sheet'], r['column'])
    c = col.split('-')
    return '%s:%s' % (sh, c[0]) if len(c) == 1 else '%s:%s / %s:%s' % (sh, c[0], sh, c[1])


def table(s):
    rows = {}
    for r in WIRES:
        k = tkey(r)
        if k is None:
            continue
        if k not in ORDER:
            FAIL.append('table (40): no place for row %s (PLC column %r)' % (wkey(r), k))
            continue
        rows.setdefault(k, []).append(r)
    lines = []
    for k in ORDER:
        if k == '':
            lines.append(None)
            continue
        rs = sorted(rows.get(k, []), key=lambda r: r['wire'])
        cz = CZ.get(k)
        czs = list(cz) if isinstance(cz, tuple) else [cz] * len(rs)
        if rs and (cz is None or len(czs) != len(rs)):
            FAIL.append('table (40): printed function text for %s missing or not one per row' % k)
            czs = [''] * len(rs)
        for r, c in zip(rs, czs):
            li = linie(r)
            sig = r['signal'] + ('; ' + EN_REMARK[k] if k in EN_REMARK else '')
            mark = False
            if k in PRINTED_LINIE:
                printed, expect = PRINTED_LINIE[k]
                if li != expect:
                    FAIL.append('table (40) %s: netlist gives %s, the printed %s was kept against %s' % (k, li, printed, expect))
                li, mark = printed, True
            lines.append((k, r['wire'], li, c, sig, mark, r))
    remark = sorted(k for k, v in CZ.items() if isinstance(v, str) and v.count('(') != v.count(')'))
    if remark != sorted(EN_REMARK):
        FAIL.append('table (40): printed remark rows %s, English given for %s' % (remark, sorted(EN_REMARK)))
    shell = [r for r in WIRES if {r['from_device'], r['to_device']} == {'XC60', 'XC70'}
             and r['from_terminal'] == 'shell']
    cz = ' '.join(CZ[k] for k in ORDER if k in EN_REMARK)
    if len(shell) != 1 or cz not in shell[0]['signal']:
        FAIL.append('table (40): the printed remark %r is not the signal of the XC60-XC70 shell row' % cz)
    x = TABLE_X
    y = TABLE_Y0
    s.rect(x[0], y, x[-1], y + TABLE_HEAD + TABLE_ROW * len(lines))
    heads = ['PLC', 'SMĚR', 'LINIE', 'PŘIPOJENÍ - FUNKCE', 'signal (English, from plc_drive_wires.csv)']
    for i, h in enumerate(heads):
        s.text(x[i] + 3, y + 12, h, 6.5, 'start', 'd')
    for i in range(1, len(x) - 1):
        s.line([(x[i], y), (x[i], y + TABLE_HEAD + TABLE_ROW * len(lines))], 'r', seg=False)
    y += TABLE_HEAD
    s.line([(x[0], y), (x[-1], y)], 'r', seg=False)
    for ln in lines:
        if ln:
            k, wire, li, c, sig, mark, r = ln
            cells = [k, wire, li, c, sig]
            for i, t in enumerate(cells):
                if len(t) * 6.5 * CW > x[i + 1] - x[i] - 5:
                    FAIL.append('table (40): cell %r wider than its column' % t)
                s.text(x[i] + 3, y + 10, t, 6.5, 'start', 'wl' if i == 1 else 't')
            if mark:
                s.text(x[2] + 3 + len(li) * 6.5 * CW + 3, y + 10, '[?]', 6.5, 'start', 'q')
        y += TABLE_ROW
        s.line([(x[0], y), (x[-1], y)], 'r', seg=False)
    return lines, y


def compare_table(lines):
    path = os.path.join(TAB, '12_568_plc_io.csv')
    if not os.path.exists(path):
        INFO.append('INFO table (40) not compared with 12_568_plc_io.csv: static_dynamic_memory/ absent')
        return
    with open(path, encoding='utf-8', newline='') as fh:
        io = list(csv.DictReader(fh))
    drawn = [ln for ln in lines if ln]
    ok = 0
    for i, q in enumerate(io, 2):
        a = q['plc_address']
        m = re.fullmatch(r'(XC\d\d) pins? (\S+)', a)
        k = '%s %s' % (m.group(2), m.group(1)) if m else a
        hits = [ln for ln in drawn if ln[0] == k and ln[1] == q['wire_SMER']]
        if not q['wire_SMER']:
            if any(ln[0] == k for ln in drawn):
                FAIL.append('table (40): %s is unused on the paper (12_568_plc_io.csv line %d) but drawn' % (k, i))
            else:
                ok += 1
            continue
        if len(hits) != 1:
            FAIL.append('table (40): 12_568_plc_io.csv line %d (%s %s) drawn %d times' % (i, a, q['wire_SMER'], len(hits)))
            continue
        k_, wire, li, c, sig, mark, r = hits[0]
        if li != q['line_LINIE'] or c != q['signal_cz']:
            FAIL.append('table (40) %s %s: drawn %r %r, paper %r %r' % (k, wire, li, c, q['line_LINIE'], q['signal_cz']))
            continue
        ok += 1
    n_paper = sum(1 for q in io if q['wire_SMER'])
    if n_paper != len(drawn):
        FAIL.append('table (40): %d rows drawn, %d wired rows on the paper' % (len(drawn), n_paper))
    INFO.append('table (40) vs 12_568_plc_io.csv: %d/%d rows agree' % (ok, len(io)))


# ---------------------------------------------------------------- ink, notes, legend, title block

INK = [(1010, 132, 9, 'start', 'blue ink: OMRON 1000P E6B2-CW26C'),
       (560, 232, 8, 'start', 'red ink: IN-8.-д. в конце хода пресса со вст.'),
       (1595, 172, 7, 'start', 'red ink'), (1595, 181, 7, 'start', 'by rows'), (1595, 190, 7, 'start', 'IN-0..2:'),
       (1595, 199, 7, 'start', 'короткий'), (1595, 208, 7, 'start', 'сто[п] –'), (1595, 217, 7, 'start', 'верх. пол.'),
       (1595, 226, 7, 'start', 'пр[есса]'),
       (1015, 640, 7.5, 'start', 'blue ink by the title block (a later hand):'),
       (1062, 658, 8.5, 'start', 'EUCHNER PA50/Welle 06/Imp. 1000'),
       (1062, 672, 8.5, 'start', 'Ident.Nr. 075043 Volt 5-30 Ver. 24'),
       (1062, 686, 8.5, 'start', 'Seriennummer: 9813 12 344'),
       (1018, 674, 9, 'start', 'BR40'),
       (1062, 708, 8.5, 'start', 'PA50-06-1000-24')]


def ink(s):
    for x, y, size, a, t in INK:
        s.text(x, y, t, size, a, 'ink')
    s.line([(1056, 648), (1050, 648), (1050, 690), (1056, 690)], 'ink2', seg=False)


# Abbreviations: the prose of the sheet (header line, notes, device block, title block), read in that order,
# gives each its full name in brackets at its first use outside a quotation; xp() inserts the bracket there
# unless the text already carries it. Labels printed on the paper (GND, PE, OUT, IN at the terminals) and
# quoted ink stay as printed. Designations (UZ1, XC50), type codes and units are no abbreviations here.
ABBR = [('PLC', 'programmable logic controller', None), ('GND', 'ground', None), ('PE', 'protective earth', None),
        ('D-sub', 'D-subminiature connector', None), ('IF1', 'interface 1', None),
        ('RS232', 'Recommended Standard 232', None), ('TxD', 'transmit data', None), ('RxD', 'receive data', None),
        ('I1', 'current output 1', None), ('OM', 'operating manual MS 80/115 PS, DS', None),
        ('B&R', 'Bernecker + Rainer', None), ('VDC', 'volts direct current', None),
        ('AT', 'amperes, time-lag', None), ('W', 'web source, weaker evidence', ':'),
        ('DC', 'direct current', None), ('AC', 'alternating current', None), ('RU', 'Russian', None),
        ('1/N/PE', 'one phase, neutral and protective earth', None), ('PRAC.', 'PRACOVNÍ = working', None),
        ('F.', 'Friedrich', ' Lütze')]      # third field: the text that must follow (W only as the mark "W:")


def abbr_re(a, e, after, done):
    """Pattern of abbreviation a as a whole token; with done, also when its bracket already follows."""
    head = r'(?<![\w&/.\-])' + re.escape(a)
    if after is None:
        return re.compile(head + r'(?![\w&/\-])')
    tail = re.escape(after)
    if done:
        tail = '(?:%s)?' % re.escape(' (%s)' % e) + tail
    return re.compile(head + '(?=%s)' % tail)


ABBR_RE = [(a, e, abbr_re(a, e, after, False)) for a, e, after in ABBR]
ABBR_CHK = [(a, e, abbr_re(a, e, after, True)) for a, e, after in ABBR]
PROSE, SEEN = [], set()


def first_use(t):
    """(position after the abbreviation, abbreviation, full name) of each abbreviation's first use in t
    outside a quotation, for those not met before."""
    quoted = [m.span() for m in re.finditer(r'"[^"]*"', t)]
    hits = []
    for a, e, rx in ABBR_RE:
        if a in SEEN:
            continue
        for m in rx.finditer(t):
            if not any(q0 <= m.start() < q1 for q0, q1 in quoted):
                hits.append((m.end(), a, e))
                break
    return hits


def xp(t):
    """Prose text with the full name of each abbreviation in brackets at its first use on the sheet."""
    hits = first_use(t)
    for end, a, e in sorted(hits, reverse=True):
        SEEN.add(a)
        if not t[end:].startswith(' (%s)' % e):
            t = t[:end] + ' (%s)' % e + t[end:]
    PROSE.append(t)
    return t


def check_abbr(s):
    """Each abbreviation of ABBR: its first use in the prose, outside a quotation, is followed by its full
    name in brackets; and every line drawn in the notes, device and title blocks is part of such a prose text
    (none bypassed xp)."""
    heads = {'Notes on reading this sheet', 'Title block (redrawn, not a copy)', LEGEND_HEAD}
    for b in s.texts[s.prose_from:]:
        ln = b[4][2:] if b[4].startswith('- ') else b[4]
        if b[4] not in heads and not any(ln in p for p in PROSE):
            FAIL.append('prose line drawn without the abbreviation pass: ' + b[4][:60])
    met = set()
    for t in PROSE:
        quoted = [m.span() for m in re.finditer(r'"[^"]*"', t)]
        for a, e, rx in ABBR_CHK:
            if a in met:
                continue
            for m in rx.finditer(t):
                if any(q0 <= m.start() < q1 for q0, q1 in quoted):
                    continue
                met.add(a)
                if not t[m.end():].startswith(' (%s)' % e):
                    FAIL.append('abbreviation %s: first use not followed by "(%s)": ...%s'
                                % (a, e, t[m.start():m.end() + 30]))
                break
    absent = [a for a, e, rx in ABBR_RE if a not in met]
    if absent:
        INFO.append('INFO abbreviations of the list not used on the sheet: ' + ', '.join(absent))
    return len(met)


def unused_note():
    """Notes line: PLC terminals without a row (no lead on the paper)."""
    used = {k[1] for r in WIRES for k in keys(r) if k[0] == 'PLC'}
    out = []
    for pre, n in (('IN', 16), ('OUT', 14)):
        free = [i for i in range(n) if '%s-%X' % (pre, i) not in used]
        runs, i = [], 0
        while i < len(free):
            j = i
            while j + 1 < len(free) and free[j + 1] == free[j] + 1:
                j += 1
            a, b = '%s-%X' % (pre, free[i]), '%s-%X' % (pre, free[j])
            runs.append(a if i == j else '%s, %s' % (a, b) if j == i + 1 else '%s to %s' % (a, b))
            i = j + 1
        out.append(', '.join(runs) or 'none')
    return ('PLC terminals with no lead on the paper, not used: inputs %s; outputs %s. Table (40) does not list '
            'them. Photo 144328 agrees for the inputs; on the output row it shows a wire on 9 or 8 [?] and none on '
            'A, so outputs 9, B, C and D are drawn dashed.' % (out[0], out[1]))


NOTES = [
    'Sheet 8 has two parts: (39) the PLC wiring drawing over columns 01-05 and (40) the connection table of the '
    'PLC and the control panel, which has no columns. Clean copies 20261114_015721 (top) and 20261114_015117 '
    '(bottom); the table and the later ink from 20261113_191800.',
    'Ruler: the paper marks 01-05 by ticks at irregular places, each over the current path it names; each number '
    'stands here at its tick, the boxes end halfway between ticks.',
    'PLC terminals as printed: OUT 0-D, +24V twice, GND twice (top strip); IN 0-F, GND twice (bottom strip). The '
    'two +24V are one node (the +24V line joins them with a junction dot); so are the two GND of each strip (a '
    'bracket on the paper). The netlist names the input-strip GND "IN-GND", as table (40) does.',
    'TABLO terminals are printed ⏚, − and +; the netlist names them PE, - and +24V (+24V is the key of the same '
    'conductor in control_wires.csv, where sheet 6 prints "TABLO +24V (8:03)"). The drawing shows the printed signs.',
    'A lead that ends free with "wire (sheet:column)" continues on that sheet; the reference comes from the same '
    'conductor\'s row in power_wires.csv or control_wires.csv. "(6:15)" under 33X10 is kept as printed '
    '(control_wires.csv: 6:14-15).',
    'Drawn here, not as lines on the paper: the four conductors of the PLC-TABLO link between XC60 and XC70 (the '
    'paper shows the arrows "XC70 ⇒ PLC" and "TABLO" over XC60 and lists the contacts in table (40); here they '
    'end at the contacts of XC70, circles right of the arrow "XC70 ⇒ PLC"); the two '
    'conductors from XC50 to UZ1 7 and 8 (paper: arrow "UZ1", table rows 6+9 XC50, 4 XC50); the harness to XC4 '
    'and BR40, printed as one bus line with slanted entries, is drawn as five parallel conductors (a crossing '
    'without a dot is no connection). XC4 is drawn as a box with its contact numbers.',
    'Dashed ellipses: the cable shields at both halves of XC4, bonded by 7XC4 as printed.',
    'Dashed line and red [?] = unclear, on the on-site check list of spec/plc_drive.md: outputs 9, B, C and D '
    '(the markers of the output row are not readable in photo 144328), the link shield (the paper does not say '
    'which end is bonded). A red [?] after a device name: that row of plc_drive_devices.csv is unclear (BR40: '
    'type; XC4, XC50, XC60, XC70: plug type and place, see the device block).',
    'Table (40): each row is filled from plc_drive_wires.csv (PLC = plc_address or contact, SMĚR (direction) = '
    'wire, LINIE (line) = sheet:column of the far end from the same conductor\'s row of the other thread, else of '
    'this sheet); PŘIPOJENÍ - FUNKCE (connection - function) is the printed Czech text, the last column the '
    'netlist\'s English signal. Rows 3 and 5 XC60 also carry the English of the printed remark split over them, '
    '"(STÍNĚNÍ PŘIPOJENO NA KOVOVÝ PLÁŠŤ KONEKTORU)" (shield connected to the metal shell of the connector), '
    'which belongs to the link shield (the shell row of plc_drive_wires.csv). "GND PLC X5 2:01" is kept as '
    'printed: the terminal label says (2:02) and column 01 of sheet 2 is PE, so it is marked [?].',
    'Contact functions read off the PLC port legends (estimated, see spec/plc_drive.md): XC60 = the 9-pin D-sub '
    'of port IF1, an RS232 serial port: 5 GND, 3 TxD, 2 RxD; XC50 = the ANALOG OUTPUTS port: pin 4 = I1, 6 and 9 '
    '= GND.',
    'ink: Grey italic = later handwriting, quoted, never print. Blue: "OMRON 1000P E6B2-CW26C" (1000P = 1000 '
    'pulses per turn); "EUCHNER PA50/Welle 06/Imp. 1000, Ident.Nr. 075043, Volt 5-30, Ver. 24, Seriennummer: 9813 '
    '12 344" (Welle = shaft, Imp. = pulses per turn, Ident.Nr. = identification number, Ver. = version [?], '
    'Seriennummer = serial number) bracketed "BR40", and "PA50-06-1000-24" (encoder type candidates). Red, left '
    'of the table: "IN-8.-д. в конце хода пресса со вст." (IN-8 - д. = датчик, sensor, at the end of the clamp '
    'stroke; "со вст." not resolved [?]) against the printed IN-8 = K12UZ1 drive signal. Red, right '
    'of table rows IN-0 to IN-2: "короткий сто[п] – верх. пол. пр[есса]" (short st[op] - top position of the '
    'clamp [?]).',
]


def textblock(s, y, head, items, size=7.5):
    x0 = 34
    n = int((W - 68 - 16) / (size * CW))
    s.text(x0 + 4, y + 12, head, 8.5, 'start', 'd')
    yy = y + 24
    for it in items:
        c = 't'
        if it.startswith('ink:'):
            c, it = 'ink', it[4:].strip()
        it = xp(it)
        for i, ln in enumerate(wrap(it, n - 2)):
            s.text(x0 + 6 + (0 if i == 0 else 12), yy, ('- ' if i == 0 else '') + ln, size, 'start', c)
            yy += size + 2.5
    s.rect(x0, y, W - 34, yy)
    return yy


LEGEND_HEAD = 'Devices on this sheet (from plc_drive_devices.csv; [?] = unclear, estimated = with likely error)'


def legend(s, y):
    items = []
    for d in DEVS:
        ev = d['evidence'] if d['evidence'].startswith('[') else '[%s]' % d['evidence']
        t = '%s %s %s' % (d['designation'], ev, d['function_en'])
        if d['term_cz_ru'] not in ('', '-'):
            t += ' (%s)' % d['term_cz_ru']
        t += '; %s; place: %s; device row: sheet %s, column %s' % (d['type_rating'], d['place'], d['sheet'], d['column'])
        items.append(xp(t))
    size = 7
    colw = (W - 68 - 24) / 2
    n = int((colw - 14) / (size * CW))
    blocks = [wrap(t, n) for t in items]
    total = sum(len(b) for b in blocks)
    acc, split = 0, len(blocks)
    for i, b in enumerate(blocks):
        if acc >= total / 2:
            split = i
            break
        acc += len(b)
    s.text(38, y + 12, LEGEND_HEAD, 8.5, 'start', 'd')
    bottom = y + 24
    for col, bl in enumerate((blocks[:split], blocks[split:])):
        yy = y + 24
        x = 40 + col * (colw + 24)
        for b in bl:
            for i, ln in enumerate(b):
                s.text(x + (0 if i == 0 else 10), yy, ln, size, 'start', 't')
                yy += size + 2.3
            yy += 1.5
        bottom = max(bottom, yy)
    s.rect(34, y, W - 34, bottom + 4)
    return bottom + 4


def finish(s, ybody):
    s.prose_from = len(s.texts)
    notes = NOTES[:3] + [unused_note()] + NOTES[3:]
    y = textblock(s, ybody + 20, 'Notes on reading this sheet', notes) + 10
    y = legend(s, y) + 10
    tb = ['Adast Maxima MS 115 PS (serial 578.0009, 1998), PLC and drive control: PLC, console terminal TABLO, '
          'inverter UZ1 control side, encoder BR40, backgauge positioning signals.',
          'Redrawn from the wiring set 568-70.9001 SCHÉMA ZAPOJENÍ (MS 80 PS.DS MS 115 PS.DS), sheet 8; columns '
          'as printed; title block of the paper: MS 80 PS.DS, MS 115 PS.DS, SCHÉMA ZAPOJENÍ, 568-70.9001, sheet 8.',
          'Sheet photos: preparatory_data_analysis/maxima_documents/adast_guillotine_wiring_and_plc_diagrams/'
          '20261114_015721.jpg (top), 20261114_015117.jpg (bottom), 20261113_191800.jpg (table, ink).',
          'Data: stage_2_electronics/netlist/plc_drive_devices.csv and plc_drive_wires.csv; references from '
          'power_wires.csv, control_wires.csv and power_devices.csv; drawn by stage_2_electronics/schemes_2d/plc_draw.py.',
          'Marks: dashed line or [?] = unclear (on-site check list, spec/plc_drive.md); grey italic = later ink, quoted.']
    return textblock(s, y, 'Title block (redrawn, not a copy)', tb) + 16


def write(s, H):
    head = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n' % (W, H, W, H) +
            '<style>.w,.e{fill:none;stroke:#000;stroke-width:1.2}.e{stroke-width:0.9}'
            '.wq{fill:none;stroke:#000;stroke-width:1.2;stroke-dasharray:5 3}'
            '.b{fill:#fff;stroke:#000;stroke-width:1.2}.bd{fill:none;stroke:#000;stroke-width:1;stroke-dasharray:4 3}'
            '.z{fill:#f3f3f3;stroke:#000;stroke-width:0.8}.r{fill:none;stroke:#000;stroke-width:0.8}'
            '.ink2{fill:none;stroke:#666;stroke-width:0.9}.tc{fill:#fff;stroke:#000;stroke-width:1}.dot{fill:#000}'
            'text{font-family:Consolas,"DejaVu Sans Mono","Courier New",monospace;fill:#000}.d{font-weight:bold}.n{fill:#333}'
            '.q{fill:#b00000}.ink{fill:#666;font-style:italic}.wl{fill:#0b4a8f}</style>\n'
            '<rect x="0" y="0" width="%d" height="%d" fill="#fff"/>\n<rect x="8" y="8" width="%d" height="%d" class="r"/>\n'
            % (W, H, W - 16, H - 16))
    path = os.path.join(HERE, 'plc_sheet8.svg')
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(head + '\n'.join(s.body) + '\n</svg>\n')
    return path


def edges(s):
    """Every straight piece of line drawn: polyline segments, polygon and rect edges (not circles, ellipses)."""
    out = []
    for frag in s.body:
        m = re.match(r'<(polyline|polygon) points="([^"]*)"', frag)
        if m:
            pts = [tuple(map(float, p.split(','))) for p in m.group(2).split()]
            if m.group(1) == 'polygon':
                pts.append(pts[0])
            out += [(p, q) for p, q in zip(pts, pts[1:]) if p != q]
            continue
        m = re.match(r'<rect x="([^"]*)" y="([^"]*)" width="([^"]*)" height="([^"]*)"', frag)
        if m:
            x0, y0, w, h = map(float, m.groups())
            c = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h), (x0, y0)]
            out += list(zip(c, c[1:]))
    return out


def bound_ends(s):
    """{open lead end: why it is not bound to its own row}. Bound: the end closes its own row's polyline;
    beside that lead (a text box ending 0-3 px left of it, over the lead's length) stand exactly that row's
    label 'wire (sheet:column)' and, for a [?] row, its red [?]; they lie wholly between the pin and the end;
    the end is BIND_GAP px past their far end, or, where OPEN_AT puts it on a drawn line, on a junction dot."""
    bad = {}
    for p, (key, r, pin, o) in s.open_ends.items():
        x, ye = p
        pts = s.rowpts.get(key)
        if not pts or p not in (pts[0], pts[-1]):
            bad[p] = 'it does not close the line of its own row %s' % key
            continue
        lo, hi = min(pin[1], ye), max(pin[1], ye)
        beside = [b for b in s.texts if x - 3 <= b[2] < x and b[1] < hi - 1 and b[3] > lo + 1]
        own = [(r['wire'] + ' ' + ref(r, keep=False)).strip()] + (['[?]'] if r['evidence'].startswith('[?]') else [])
        got = [b[4] for b in beside]
        if not r['wire'] or sorted(got) != sorted(own):
            bad[p] = 'beside its lead stand %s, its own row %s has %s' % (got, key, own)
            continue
        if min(b[1] for b in beside) < lo or max(b[3] for b in beside) > hi:
            bad[p] = 'the label of its own row %s runs past the lead' % key
            continue
        far = min(b[1] for b in beside) if ye < pin[1] else max(b[3] for b in beside)
        gap = abs(ye - far)
        if o in OPEN_AT:
            if p not in s.dotpts:
                bad[p] = 'it should meet a drawn line (OPEN_AT) but no junction dot is there'
        elif not BIND_GAP[0] <= gap <= BIND_GAP[1]:
            bad[p] = 'it is %.1f px past the label of its own row %s (allowed %g-%g)' % ((gap, key) + BIND_GAP)
    return bad


def free_ends(s, bad):
    """(wire ends, the ends in free space): each end of a drawn wire (polyline of class w or wq) sits on a
    terminal circle or junction dot, on an edge of a box or a polygon (arrow, outline), on a shell outline, or
    is the open end of a lead bound to its own row's label (bound_ends(); an end listed in bad holds only
    through a circle or dot)."""
    circ, rects, polys, ells, ends = [], [], [], [], []
    for frag in s.body:
        m = re.match(r'<ellipse cx="([^"]*)" cy="([^"]*)" rx="([^"]*)" ry="([^"]*)"', frag)
        if m:
            ells.append(tuple(map(float, m.groups())))
            continue
        m = re.match(r'<circle cx="([^"]*)" cy="([^"]*)" r="([^"]*)"', frag)
        if m:
            circ.append(tuple(map(float, m.groups())))
            continue
        m = re.match(r'<rect x="([^"]*)" y="([^"]*)" width="([^"]*)" height="([^"]*)"', frag)
        if m:
            x0, y0, w, h = map(float, m.groups())
            rects.append((x0, y0, x0 + w, y0 + h))
            continue
        m = re.match(r'<polygon points="([^"]*)"', frag)
        if m:
            pts = [tuple(map(float, p.split(','))) for p in m.group(1).split()]
            polys += list(zip(pts, pts[1:] + pts[:1]))       # its edges, the closing one included
            continue
        m = re.match(r'<polyline points="([^"]*)" class="wq?"', frag)
        if m:
            pts = [tuple(map(float, p.split(','))) for p in m.group(1).split()]
            ends += [pts[0], pts[-1]]

    def held(p):
        x, y = p
        if (round(x, 2), round(y, 2)) in s.open_ends and (round(x, 2), round(y, 2)) not in bad:
            return True
        if any(((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 <= r + 0.5 for cx, cy, r in circ):
            return True
        for cx, cy, rx, ry in ells:       # on the outline of a connector shell
            if abs((((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2) ** 0.5 - 1) * min(rx, ry) <= 0.6:
                return True
        for x0, y0, x1, y1 in rects:      # on an edge, not merely inside (the frame holds everything)
            inx, iny = x0 - 0.6 <= x <= x1 + 0.6, y0 - 0.6 <= y <= y1 + 0.6
            if (inx and min(abs(y - y0), abs(y - y1)) <= 0.6) or (iny and min(abs(x - x0), abs(x - x1)) <= 0.6):
                return True
        return any(seg_dist(p, a, b) <= 0.6 for a, b in polys)    # on an edge of a polygon, not merely inside
    return len(ends), [p for p in ends if not held(p)]


def seg_dist(p, a, b):
    """Distance from point p to the segment a-b."""
    (x, y), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
    return ((x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2) ** 0.5


def crosses(p, q, box):
    """Liang-Barsky: does the segment p-q enter the open box?"""
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0:
        return False
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pp == 0:
            if qq <= 0:
                return False
        else:
            r = qq / pp
            if pp < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 >= t1:
                return False
    return True


def overlaps(s):
    bad = []
    T = s.texts
    for i in range(len(T)):
        for j in range(i + 1, len(T)):
            a, b = T[i], T[j]
            if a[0] < b[2] - 0.3 and b[0] < a[2] - 0.3 and a[1] < b[3] - 0.3 and b[1] < a[3] - 0.3:
                bad.append('%r / %r' % (a[4], b[4]))
    return bad


def main():
    if FAIL:                       # an input is missing: nothing to draw
        for m in FAIL:
            print('FAIL ' + m)
        print('result: FAIL')
        return 1
    s = Sheet()
    bounds = frame(s)
    tablo(s)
    plc(s)
    xc4_br40(s)
    xc70_pins(s)
    leads(s)
    wires(s)
    nd = dots(s)
    lines, ytab = table(s)
    compare_table(lines)
    ink(s)
    H = int(finish(s, 1110))
    path = write(s, H)
    alltext = '\n'.join(t[4] for t in s.texts)
    if s.ndrawn != len(WIRES):
        FAIL.append('%d of %d wire rows drawn' % (s.ndrawn, len(WIRES)))
    for c in range(1, 6):
        if '%02d' % c not in alltext.split('\n'):
            FAIL.append('ruler column %02d missing' % c)
    for r in WIRES:
        if r['wire'] and r['wire'] not in alltext:
            FAIL.append('wire label %s not printed' % r['wire'])
    for d in DEVS:
        pat = re.compile(r'(?<![A-Za-z0-9])' + re.escape(d['designation']) + r'(?![A-Za-z0-9])')
        if not pat.search(alltext):
            FAIL.append('device %s not printed' % d['designation'])
    for a in ADDR14:
        if ('PLC', a, '') not in s.pins:
            FAIL.append('address %s not drawn at its terminal' % a)
    for o in overlaps(s):
        FAIL.append('text overlap %s' % o)
    bx0, by0, bx1, by1 = PLC_RECT
    for a, b, c, d, t in s.texts:       # an edge line of the PLC box must not run through a text box
        cut = [e for e in (by0, by1) if b < e < d and a < bx1 and c > bx0] + \
              [e for e in (bx0, bx1) if a < e < c and b < by1 and d > by0]
        if cut:
            FAIL.append('text %r cut by an edge of the PLC box (at %s)' % (t, f(cut[0])))
    for n in EXTENT:
        if n in DEV and DEV[n]['evidence'] not in ('', 'sure') and n not in QLABEL:
            FAIL.append('device %s is %s, but its drawn name carries no mark' % (n, DEV[n]['evidence']))
    for frag in s.body:
        rest = frag.replace('<tspan class="q">[?]</tspan>', '').replace('class="q">[?]</text>', '')
        if '[?]' in rest:
            FAIL.append('a [?] not drawn red: %s' % frag[:90])
    for t in s.texts:
        for p in STALE:
            if p in t[4]:
                FAIL.append('stale phrase %r in text %r' % (p, t[4][:60]))
    segs = edges(s)
    for core, t in s.cores:
        for p, q in segs:
            if crosses(p, q, core):
                FAIL.append('text %r struck by the line %s,%s-%s,%s' % (t[:40], f(p[0]), f(p[1]), f(q[0]), f(q[1])))
                break
    bad = bound_ends(s)
    for (x, y), why in sorted(bad.items()):      # each once, also where no drawn line ends at it
        FAIL.append('open lead end at %s,%s not bound to its own label: %s' % (f(x), f(y), why))
    nends, free = free_ends(s, bad)
    for x, y in free:
        if (round(x, 2), round(y, 2)) not in bad:
            FAIL.append('wire end in free space at %s,%s (no terminal circle, junction dot, box edge, shell outline, '
                        'arrow or bound open lead end)' % (f(x), f(y)))
    nab = check_abbr(s)
    for n, (x0, x1) in EXTENT.items():
        if n not in DEV:
            continue
        cols = [int(c) for c in re.findall(r'\d+', DEV[n]['column'])]
        lo, hi = bounds[min(cols) - 1], bounds[max(cols)]
        cx = (x0 + x1) / 2
        if not lo <= cx <= hi:
            INFO.append('INFO %s drawn at x %.0f, outside its column(s) %s (x %.0f-%.0f)' % (n, cx, DEV[n]['column'], lo, hi))
    print('sheet 8: wire rows %d/%d drawn, pins %d, junction dots %d, texts %d, table (40) rows %d, height %d px'
          % (s.ndrawn, len(WIRES), len(s.pins), nd, len(s.texts), sum(1 for ln in lines if ln), H))
    print('references beside leads (%d): %s' % (len(REFS), '; '.join(REFS)))
    print('abbreviations: %d of %d in the list used, each with its full name in brackets at its first use'
          % (nab, len(ABBR)))
    print('wire ends: %d/%d on a terminal circle, a junction dot, a box edge, a shell outline, an arrow or the open '
          'end of a lead' % (nends - len(free), nends))
    print('open lead ends: %d/%d bound to the label of their own row (%g-%g px past it, or on a junction dot)'
          % ((len(s.open_ends) - len(bad), len(s.open_ends)) + BIND_GAP))
    for m in INFO:
        print(m)
    for m in FAIL:
        print('FAIL ' + m)
    print('wrote ' + os.path.relpath(path, os.path.join(HERE, '..', '..')).replace(os.sep, '/'))
    print('result: ' + ('FAIL' if FAIL else 'PASS'))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
