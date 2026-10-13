#!/usr/bin/env python3
"""
Zombie 2 (office zombie) - extra moves: 2 new dances (8 frames each), an
8-direction walk cycle (6 frames per direction), a spawn ("crawl out of the
ground") and a die ("splat") animation.  Full-body 160x200 sprites only.

Run:   python3 make_zombie2_moves.py [output_dir]
Needs: make_zombie2.py in the same folder (palette, canvas class C and the
       front-view parts are reused from it, so the zombie stays identical),
       Pillow, numpy.

Output (default ./zombie2_moves/ next to this script):
    zombie2_danceB_0..7.png        "Pirouette"  360-degree spin through all eight
                                   facings with a jump arc (crouch, launch, tuck, land)
    zombie2_danceC_0..7.png        "The Robot"  stiff snapping poses: head snaps in
                                   45-degree steps, right-angle arms, pop-and-lock bobs
    zombie2_walk_<DIR>_0..5.png    DIR = N NE E SE S SW W NW, 6-frame loop each
    zombie2_spawn_0..7.png         crawls out of a dirt mound, briefcase comes up last
    zombie2_die_0..7.png           "splat": flash, swell, burst into parts + goo +
                                   open briefcase with papers, rests as a pile
    zombie2_moves_preview.png      contact sheet (not part of the set)
The original dance is zombie2_dance0..7.png from make_zombie2.py.

How the 8 directions are made
  S  = front view (the original art)       N  = back view
  E  = side profile                        SE = 3/4 front      NE = 3/4 back
  W, SW, NW = mirrors of E, SE, NE (so the briefcase swaps hands there - this is
  intentional and keeps the case visible in every facing).
  The case hand is the character's RIGHT hand: screen-left in S, near side in E,
  screen-right in N.  The torn shirt side is the character's LEFT.

Where to change things
  * Dances ........ dance_pirouette() / dance_robot() (the ROBOT table)
  * Walk timing ... BOB, lifts() and walk_pose()
  * Poses ......... view(direction, **pose): dx, bob (knee bend), hop (jump),
                    lift, swing, tilt, head (head facing override),
                    caseArm 'low'|'mid'|'high', tornArm 'up'|'upP'|'out'|'down'|'fwd'
  * New parts ..... head_side(), head_back(), head_3q(), torso_side(), torso_back(),
                    torso_3q(), leg_side(), side_arm(), briefcase_open()
  * Colours ....... PAL in make_zombie2.py; extra colours are added at runtime in the
                    "PALETTE ADDITIONS" block below.  NOTE: zombie 2 already uses
                    palette index 16 (briefcase dark), so dirt/goo start at 17
                    (zombie 1 used 16-20).
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_zombie2 as Z                                      # noqa: E402
from make_zombie2 import C                                    # noqa: E402
from PIL import Image, ImageDraw                              # noqa: E402

W, H, CX, GROUND = Z.W, Z.H, Z.CX, Z.GROUND
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "zombie2_moves")

# palette indices of make_zombie2.PAL
OUTL, SKD, SKM, SKL, SHD, SHW, PTD, PTL = 1, 2, 3, 4, 5, 6, 7, 8
EYE, PUPIL, TAG, DARK, TIE, TIED, CASE, CASED = 9, 10, 11, 12, 13, 14, 15, 16

# ------------------------------------------------------ PALETTE ADDITIONS
DIRT_D, DIRT_M, DIRT_L, GOO, GOO_D, FLASH = 17, 18, 19, 20, 21, 22
Z.PAL.update({DIRT_D: (74, 52, 40), DIRT_M: (112, 84, 60), DIRT_L: (150, 118, 84),
              GOO: (150, 230, 80), GOO_D: (70, 150, 56), FLASH: (250, 250, 244)})
MY = 44                                    # spawn: ground line (row) the zombie rises from
REST = 47                                  # die: bottom content row of parts lying on the ground


# ------------------------------------------------------------ small helpers
def sheared(head, tilt, w=18, ox=3):
    """Head leaning by `tilt` px at the top, pivoting around the chin."""
    o = C(w, 12)
    for r in range(12):
        sh = round(tilt * (11 - r) / 11)
        for i in range(12):
            if head.g[r][i]:
                o.set(ox + sh + i, r, head.g[r][i])
    return o


def shade_far(c):
    """Darken a canvas (limbs on the far side of the body, for depth)."""
    m = {PTL: PTD, SKM: SKD, SKL: SKM, SHW: SHD, CASE: CASED, TIE: TIED, TAG: SHD}
    o = C(c.w, c.h)
    o.g = [[m.get(v, v) for v in row] for row in c.g]
    return o


def unoutlined(c):
    o = C(c.w, c.h)
    o.g = [[0 if v == 1 else v for v in row] for row in c.g]
    return o


def shifted(c, dx, dy):
    o = C(c.w, c.h)
    o.paste(c, dx, dy)
    return o


# ------------------------------------------------------------ new body parts
def head_side():
    """Profile head looking right: thin combed hair, ear, half-lidded eye, frown."""
    c = C(12, 12)
    for y, (a, b) in {1: (1, 9), 2: (0, 9), 3: (0, 9), 4: (0, 9), 5: (0, 9), 6: (0, 9),
                      7: (0, 9), 8: (0, 9), 9: (1, 9), 10: (3, 8), 11: (4, 7)}.items():
        for x in range(a, b + 1):
            c.set(x, y, SKM)
    for y in range(3, 10):
        c.set(9, y, SKD)                    # front edge in shade
        c.set(0, y, SKL)
    c.rect(10, 6, 1, 2, SKM)                # nose
    c.set(10, 7, SKD)
    c.rect(1, 1, 9, 1, DARK)                # thin hair on top
    c.rect(0, 2, 4, 1, DARK)
    c.rect(0, 3, 2, 1, DARK)
    for x in (4, 7, 8):
        c.set(x, 0, DARK)
    c.rect(3, 5, 2, 3, SKD)                 # ear
    c.set(3, 6, SKM)
    c.rect(6, 3, 2, 1, SKD)                 # brow
    c.rect(6, 4, 3, 1, SKD)                 # heavy lid
    c.rect(6, 5, 3, 2, EYE)
    c.set(8, 6, PUPIL)
    c.rect(6, 7, 3, 1, SKD)                 # eye bag
    c.rect(6, 9, 3, 1, PUPIL)               # frown
    c.set(8, 10, PUPIL)
    return c


def head_back():
    """Back of the head: thin comb-over hair, ears, neck, grey cheek blotch."""
    c = C(12, 12)
    for y, (a, b) in {2: (1, 10), 3: (0, 11), 4: (0, 11), 5: (0, 11), 6: (0, 11), 7: (0, 11),
                      8: (0, 11), 9: (0, 11), 10: (1, 10), 11: (3, 8)}.items():
        for x in range(a, b + 1):
            c.set(x, y, SKM)
    for y in range(3, 10):
        c.set(0, y, SKL)
        c.set(11, y, SKD)
    c.rect(3, 11, 6, 1, SKD)                # neck
    c.set(10, 10, SKD)
    c.rect(1, 1, 10, 1, DARK)
    c.rect(1, 2, 10, 4, DARK)               # hair covers the crown
    for (x, y) in ((3, 3), (6, 4), (9, 3), (4, 5)):
        c.set(x, y, SKM)                    # thin: scalp shows through
    c.rect(1, 6, 2, 2, DARK)                # side hair
    c.rect(9, 6, 2, 2, DARK)
    for x in (2, 3, 6, 7):
        c.set(x, 0, DARK)
    c.set(0, 5, SKD)                        # ears
    c.set(0, 6, SKM)
    c.set(11, 5, SKD)
    c.set(11, 6, SKD)
    c.rect(1, 8, 2, 2, SKD)                 # blotch (character's left cheek)
    return c


def head_3q(back=False):
    """3/4 head turned to the right. back=True: seen from behind."""
    if back:
        h = head_back()
        for y in range(4, 10):               # a strip of cheek peeks out on the right
            h.set(11, y, SKM)
            if y in (5, 6):
                h.set(10, y, SKD)
        h.set(11, 3, 0)
        return h
    c = C(12, 12)
    for y, (a, b) in {2: (1, 10), 3: (0, 11), 4: (0, 11), 5: (0, 11), 6: (0, 11), 7: (0, 11),
                      8: (0, 11), 9: (0, 11), 10: (1, 10), 11: (3, 8)}.items():
        for x in range(a, b + 1):
            c.set(x, y, SKM)
    for y in range(3, 10):
        c.set(0, y, SKL)
        c.set(11, y, SKD)
    c.rect(1, 1, 10, 1, DARK)                # thin hair
    c.rect(0, 2, 4, 3, DARK)
    for x in (5, 8, 9):
        c.set(x, 0, DARK)
    c.rect(1, 5, 2, 3, SKD)                  # ear on the near side
    c.set(1, 6, SKM)
    c.set(4, 3, SKD)                         # near brow / lid / eye / bag
    c.set(5, 3, SKD)
    c.rect(4, 4, 3, 1, SKD)
    c.rect(4, 5, 3, 2, EYE)
    c.set(6, 6, PUPIL)
    c.rect(4, 7, 3, 1, SKD)
    c.rect(9, 4, 2, 1, SKD)                  # far eye (narrow)
    c.rect(9, 5, 2, 2, EYE)
    c.set(10, 6, PUPIL)
    c.rect(9, 7, 2, 1, SKD)
    c.set(9, 3, SKD)
    c.set(10, 3, SKD)
    c.set(7, 6, SKD)                         # nose
    c.set(7, 7, SKD)
    c.set(8, 8, SKD)
    c.rect(6, 9, 4, 1, PUPIL)                # frown
    c.set(5, 10, PUPIL)
    c.set(9, 10, PUPIL)
    return c


def torso_side():
    """Right side of the shirt (the intact side) with the tie at the front edge."""
    c = C(8, 14)
    c.rect(0, 0, 8, 12, SHW)
    c.rect(5, 0, 3, 12, SHD)
    c.rect(2, 0, 5, 1, SKD)                 # open collar
    c.rect(6, 1, 2, 2, TIE)                 # tie knot
    c.rect(6, 3, 2, 7, TIE)
    c.rect(7, 3, 1, 7, TIED)
    c.rect(6, 10, 2, 2, TIE)
    c.set(7, 11, TIED)
    c.rect(1, 4, 1, 2, TAG)                 # name tag edge
    for x in (0, 2, 4):                     # ragged hem
        c.set(x, 12, SHW)
    c.set(2, 13, SHW)
    return c


def torso_back():
    """Back of the shirt: torn away on the screen-left (character's left) flank."""
    c = C(12, 14)
    c.rect(0, 0, 12, 12, SHW)
    c.rect(9, 0, 3, 12, SHD)
    c.rect(4, 0, 4, 1, SKD)                 # collar / neck
    c.rect(5, 1, 2, 1, TAG)                 # label
    edge = {3: 1, 4: 2, 5: 1, 6: 3, 7: 2, 8: 3, 9: 2, 10: 3, 11: 2}
    for y, e in edge.items():               # torn flank: skin up to the ragged edge
        for x in range(0, e + 1):
            c.set(x, y, SKM)
        c.set(0, y, SKD)
        c.set(e, y, SKL)
    c.rect(0, 11, 3, 1, SKD)
    c.rect(7, 6, 2, 1, SKM)                 # little tear
    c.set(8, 7, SKM)
    c.set(7, 7, SKD)
    for x in (5, 7, 8, 10, 11):
        c.set(x, 12, SHW if x < 9 else SHD)
    for x in (8, 11):
        c.set(x, 13, SHW if x < 9 else SHD)
    return c


def torso_3q():
    """Front 3/4 (turned right): tie shifted right, tag on the near chest, small torn strip."""
    c = C(10, 14)
    c.rect(0, 0, 10, 12, SHW)
    c.rect(6, 0, 2, 12, SHD)
    c.rect(4, 0, 4, 1, SKD)
    edge = {3: 9, 4: 8, 5: 9, 6: 8, 7: 9, 8: 8, 9: 9, 10: 8, 11: 9}
    for y, e in edge.items():
        for x in range(e, 10):
            c.set(x, y, SKM)
        c.set(9, y, SKD)
        c.set(e, y, SKL)
    c.rect(8, 11, 2, 1, SKD)
    c.rect(1, 4, 2, 2, TAG)                 # name tag
    c.set(1, 4, TIE)
    c.set(2, 5, PUPIL)
    c.rect(5, 1, 2, 2, TIE)                 # tie
    c.rect(5, 3, 2, 5, TIE)
    c.rect(6, 3, 1, 5, TIED)
    c.rect(5, 8, 3, 3, TIE)
    c.rect(7, 8, 1, 3, TIED)
    c.rect(6, 11, 2, 1, TIED)
    for x in (0, 2, 3, 5):
        c.set(x, 12, SHW)
    for x in (0, 3):
        c.set(x, 13, SHW)
    return c


def torso_back_3q():
    t = torso_back()
    o = C(10, 14)
    o.g = [row[1:11] for row in t.g]
    return o


def leg_side(swing, short=0):
    """Leg seen from the side, shoe pointing right. `swing` = px the foot is shifted
    forward (+) / back (-) relative to the hip (sheared leg)."""
    n = 10 - short                          # pants rows
    rows = 14 - short
    c = C(18, rows)
    for r in range(rows):
        x = 7 + round(swing * r / (rows - 1))
        if r < n:
            c.rect(x, r, 3, 1, PTL)
            c.set(x + 3, r, PTD)
            if r == n - 1:
                c.rect(x, r, 4, 1, PTD)     # cuff shadow
        elif r == n:
            c.rect(x + 1, r, 2, 1, SKM)     # grey ankle
            c.set(x + 3, r, SKD)
        else:
            c.rect(x, r, 6, 1, DARK)        # shoe, toes forward
            if r == n + 1:
                c.rect(x, r, 4, 1, PTL)
    return c


# ---- thick-limb drawing for the profile arms (angle 0 = down, 90 = forward, 180 = up)
def limb_pts(p0, p1, size):
    pts = set()
    steps = max(1, int(round(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1])) * 2)))
    for i in range(steps + 1):
        t = i / steps
        x = round(p0[0] + (p1[0] - p0[0]) * t)
        y = round(p0[1] + (p1[1] - p0[1]) * t)
        for j in range(size):
            for k in range(size):
                pts.add((x - size // 2 + k, y - size // 2 + j))
    return pts


def paint(c, pts, light, mid, dark):
    """Hard 3-tone shading: light on the top/left edge, dark on the bottom/right edge."""
    for (x, y) in pts:
        if (x - 1, y) not in pts or (x, y - 1) not in pts:
            col = light
        elif (x + 1, y) not in pts or (x, y + 1) not in pts:
            col = dark
        else:
            col = mid
        c.set(x, y, col)


def side_arm(sx, sy, ang, torn=False, case=False):
    """Profile arm on a full-size canvas. Shoulder at (sx, sy); ang = (upper, fore) angles.
    Upper arm = shirt sleeve (or bare skin + scrap if torn), forearm = skin, hand = 4x4,
    case=True hangs the briefcase from the hand."""
    a1, a2 = (math.radians(a) for a in ang)
    c = C(W, H)
    el = (sx + 4 * math.sin(a1), sy + 4 * math.cos(a1))
    hd = (el[0] + 5 * math.sin(a2), el[1] + 5 * math.cos(a2))
    if torn:
        paint(c, limb_pts((sx, sy), el, 3), SKL, SKM, SKD)
        paint(c, limb_pts((sx, sy), (sx, sy), 3), SHW, SHW, SHD)       # shirt scrap on the shoulder
    else:
        paint(c, limb_pts((sx, sy), el, 3), SHW, SHW, SHD)
    paint(c, limb_pts(el, hd, 3), SKL, SKM, SKD)
    hx, hy = round(hd[0] + 1.2 * math.sin(a2)), round(hd[1] + 1.2 * math.cos(a2))
    if case:
        c.paste(Z.briefcase(), hx - 4, hy + 2)
    paint(c, limb_pts((hx, hy), (hx, hy), 4), SKL, SKM, SKD)
    return c


# ---- the 5 base views --------------------------------------------------------
DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
CASE_HY = {"low": 3, "mid": 0, "high": -3}               # front/back/3q: hand height
SIDE_NEAR = {"low": (8, 18), "mid": (55, 95), "high": (70, 120)}   # profile case arm angles
SIDE_FAR = {"up": (90, 130), "upP": (90, 130), "out": (85, 95), "fwd": (75, 90),
            "down": (-6, 8)}


def torn_arm(tok):
    """Front-view torn arm drawings (disco finger variants end in P)."""
    return {"up": lambda: Z.arm(-9, torn=True),
            "upP": lambda: Z.arm(-9, point="up", torn=True),
            "out": lambda: Z.arm(0, torn=True),
            "down": lambda: Z.arm(5, torn=True),
            "fwd": lambda: Z.reach_arm(torn=True)}[tok]()


def get_head(o):
    """Head canvas for a facing (S SE E NE N, and mirrored SW W NW)."""
    base = {"S": Z.head, "SE": head_3q, "E": head_side, "NE": lambda: head_3q(True),
            "N": head_back}
    if o in base:
        return base[o]()
    return get_head({"SW": "SE", "W": "E", "NW": "NE"}[o]).flip()


HEAD_OFF = {"S": 0, "SE": 1, "SW": -1, "E": 1, "W": -1, "N": 0, "NE": 1, "NW": -1}


def put_head(c, o, dx, y, tilt):
    h = sheared(get_head(o), tilt)
    c.paste(h, CX - 9 + dx + HEAD_OFF[o], y)


def legs_front(c, dx, bob, hop, lift, sep=7, s=0):
    kx = 1 if bob >= 2 else 0
    ly = GROUND - (14 - bob) - hop
    c.paste(Z.leg("L", bob), CX - sep + dx - kx - (1 if lift == "L" else 0) + s,
            ly - (1 if lift == "L" else 0))
    c.paste(Z.leg("R", bob), CX + (1 if sep == 7 else 0) + dx + kx + (1 if lift == "R" else 0) - s,
            ly - (1 if lift == "R" else 0))


def v_front(dx=0, bob=0, hop=0, lift=None, tilt=0, headdy=0, head="S", caseArm="low",
            tornArm="down", **_):
    c = C(W, H)
    y0 = bob - hop
    legs_front(c, dx, bob, hop, lift)
    c.rect(CX - 6 + dx, 34 + y0, 12, 3, PTL)
    c.rect(CX + 2 + dx, 34 + y0, 4, 3, PTD)
    c.paste(Z.torso(), CX - 6 + dx, 21 + y0)
    Z.put_arm(c, Z.arm(CASE_HY[caseArm], case=True), "L", dx, y0)
    Z.put_arm(c, torn_arm(tornArm), "R", dx, y0)
    c.rect(CX - 2 + dx, 20 + y0, 4, 1, SKD)
    put_head(c, head, dx, 8 + y0 + headdy, tilt)
    c.outline()
    return c


def v_back(dx=0, bob=0, hop=0, lift=None, tilt=0, headdy=0, head="N", caseArm="low",
           tornArm="down", **_):
    """Back view: the case hand is on the screen-RIGHT, torn left arm on the screen-left."""
    c = C(W, H)
    y0 = bob - hop
    legs_front(c, dx, bob, hop, lift)
    c.rect(CX - 6 + dx, 34 + y0, 12, 3, PTL)
    c.rect(CX + 2 + dx, 34 + y0, 4, 3, PTD)
    c.paste(torso_back(), CX - 6 + dx, 21 + y0)
    Z.put_arm(c, Z.arm({"fwd": 2}.get(tornArm, torn_hy(tornArm)), torn=True), "L", dx, y0)
    Z.put_arm(c, Z.arm(CASE_HY[caseArm], case=True), "R", dx, y0)
    c.rect(CX - 2 + dx, 20 + y0, 4, 1, SKD)
    put_head(c, head, dx, 8 + y0 + headdy, tilt)
    c.outline()
    return c


def torn_hy(tok):
    return {"up": -9, "upP": -9, "out": 0, "down": 5, "fwd": 2}[tok]


def arm_at(c, drawn, flip, edge_x, y0):
    """Paste an arm drawing from make_zombie2 so its sleeve edge column sits at x=edge_x."""
    a, ax, sy = drawn
    oy = 22 + y0 - sy
    if flip:
        a = a.flip()
        c.paste(a, edge_x - (a.w - 1 - ax), oy)
    else:
        c.paste(a, edge_x - ax, oy)


def v_3q(back, dx=0, bob=0, hop=0, lift=None, s=0, tilt=0, headdy=0, head=None, caseArm="low",
         tornArm="down", **_):
    """SE (back False) / NE (back True).  SE: case arm near = screen-left, torn arm far =
    screen-right behind the torso.  NE: case arm near = screen-right, torn arm far = left."""
    c = C(W, H)
    y0 = bob - hop
    legs_front(c, dx, bob, hop, lift, sep=5, s=s)
    tor = torso_back_3q() if back else torso_3q()
    tx = CX - 5 + dx
    c.rect(tx, 34 + y0, 10, 3, PTL)
    c.rect(tx + 6, 34 + y0, 4, 3, PTD)
    far = Z.arm(torn_hy(tornArm), torn=True) if (back or tornArm != "fwd") else Z.reach_arm(torn=True)
    near = Z.arm(CASE_HY[caseArm], case=True)
    if back:                                    # far (left, torn) behind, then torso, then near
        arm_at(c, far, False, tx + 1, y0)
        c.paste(tor, tx, 21 + y0)
        arm_at(c, near, True, tx + 8, y0)
    else:
        arm_at(c, far, True, tx + 8, y0)
        c.paste(tor, tx, 21 + y0)
        arm_at(c, near, False, tx + 1, y0)
    c.rect(CX - 2 + dx, 20 + y0, 4, 1, SKD)
    put_head(c, head or ("NE" if back else "SE"), dx, 8 + y0 + headdy, tilt)
    c.outline()
    return c


def v_side(dx=0, bob=0, hop=0, swing=0, farswing=None, lift=None, tilt=1, lean=1, headdy=0,
           caseArm="low", tornArm="out", near=None, far=None, head="E", **_):
    """Profile facing right.  Near arm = case arm (the character's right), far arm = the
    torn one.  swing = near foot forward(+)/back(-); far foot defaults to -swing."""
    fs = -swing if farswing is None else farswing
    near = near or SIDE_NEAR[caseArm]
    far = far or SIDE_FAR[tornArm]
    c = C(W, H)
    y0 = bob - hop
    ly = GROUND - (14 - bob) - hop
    lx = CX - 9 + dx
    c.paste(shade_far(leg_side(fs, bob)), lx, ly - (1 if lift == "R" else 0))
    c.paste(leg_side(swing, bob), lx, ly - (1 if lift == "L" else 0))
    tx = CX - 4 + lean + dx
    c.rect(tx, 34 + y0, 8, 3, PTL)
    c.rect(tx + 4, 34 + y0, 4, 3, PTD)
    sx, sy = tx + 3, 23 + y0
    c.paste(shade_far(side_arm(sx, sy, far, torn=True)), 0, 0)
    c.paste(torso_side(), tx, 21 + y0)
    c.paste(side_arm(sx, sy, near, case=True), 0, 0)
    c.rect(tx + 1, 20 + y0, 3, 1, SKD)
    c.paste(sheared(get_head(head), tilt), CX - 8 + lean + dx, 8 + y0 + headdy)
    c.outline()
    return c


def view(direction, **pose):
    """Draw the zombie facing `direction` with `pose`; W/SW/NW are mirrors."""
    flip = direction in ("SW", "W", "NW")
    d = {"SW": "SE", "W": "E", "NW": "NE"}.get(direction, direction)
    if d == "S":
        c = v_front(**pose)
    elif d == "N":
        c = v_back(**pose)
    elif d == "E":
        c = v_side(**pose)
    elif d == "SE":
        c = v_3q(False, **pose)
    else:
        c = v_3q(True, **pose)
    return c.flip() if flip else c


# ------------------------------------------------------------------- walks
BOB = [1, 0, 0, 1, 0, 0]          # body lowest when both feet are down


def ph(p):
    a = 2 * math.pi * p / 6
    return math.cos(a), math.sin(a)


def lifts(p):
    """Which foot is in the air: left swings forward at p 4-5, right at p 1-2."""
    return "L" if p in (4, 5) else ("R" if p in (1, 2) else None)


WALK_CASE = ["low", "low", "mid", "mid", "mid", "low"]      # case arm lifts in the middle of the step
WALK_TORN = ["out", "out", "down", "down", "out", "out"]    # torn arm alternates


def walk_pose(d, p):
    cs, sn = ph(p)
    case, torn = WALK_CASE[p], WALK_TORN[p]
    if d in ("S", "N"):
        return dict(dx=round(sn), tilt=round(1.5 * sn), bob=BOB[p], lift=lifts(p),
                    caseArm=case, tornArm=torn)
    if d == "E":
        return dict(bob=BOB[p], lift=lifts(p), swing=round(5 * cs), tilt=round(1.5 * sn) + 1,
                    near=(round(6 - 24 * cs), round(18 - 20 * cs)),
                    far=(round(62 + 22 * cs), round(88 + 12 * cs)))
    return dict(dx=round(sn), tilt=round(1.5 * sn), bob=BOB[p], lift=lifts(p), s=round(2 * cs),
                caseArm=case, tornArm=torn)


def walk_frame(direction, p):
    d = {"SW": "SE", "W": "E", "NW": "NE"}.get(direction, direction)
    return view(direction, **walk_pose(d, p))


# ------------------------------------------------------------------ dances
# B "Pirouette": a full 360 spin through eight facings with a jump arc.
SPIN = ["S", "SE", "E", "NE", "N", "NW", "W", "SW"]


def dance_pirouette(f):
    d = SPIN[f]
    hop = (0, 3, 5, 6, 6, 4, 2, 0)[f]
    bob = (2, 1, 1, 2, 2, 1, 0, 2)[f]          # tuck at the top (frames 3, 4)
    up = f in (1, 2, 3, 4, 5, 6)
    tornArm = "up" if up else "out"
    caseArm = "mid" if up else "low"
    return view(d, bob=bob, hop=hop, caseArm=caseArm, tornArm=tornArm,
                tilt=(0, 1, 1, -1, -1, -1, 1, 0)[f],
                swing=1 if hop else 0, lift=None)


# C "The Robot": stiff, precise poses.  Body stays square to the viewer, the head snaps
# in 45-degree steps S -> SE -> E -> SE -> S -> SW -> W -> SW; the torn arm snaps between
# right-angle poses, the case arm pops between hang / raised; bob = pop-and-lock.
ROBOT = [
    dict(head="S",  tornArm="out",  caseArm="low",  bob=0, dx=0),                # attention
    dict(head="SE", tornArm="up",   caseArm="low",  bob=1, dx=0),
    dict(head="E",  tornArm="up",   caseArm="mid",  bob=0, dx=1, lift="R", body="SE"),
    dict(head="SE", tornArm="down", caseArm="mid",  bob=1, dx=1),
    dict(head="S",  tornArm="down", caseArm="low",  bob=2, dx=0),                # lock
    dict(head="SW", tornArm="out",  caseArm="mid",  bob=1, dx=-1),
    dict(head="E",  tornArm="up",   caseArm="low",  bob=0, dx=-1, lift="L", body="SW"),
    dict(head="S",  tornArm="upP",  caseArm="mid",  bob=0, dx=0),                # sharp finish
]


def dance_robot(f):
    pose = dict(ROBOT[f])
    body = pose.pop("body", "S")
    return view(body, tilt=0, **pose)


# ------------------------------------------------------- spawn (crawl out) & die
def mound(c, cx, rx, rng):
    """Pile of dirt at the ground line MY. rx = half width (kept inside the canvas)."""
    ry = max(2, round(rx * .3))
    for y in range(MY - ry - 1, MY + ry + 1):
        for x in range(cx - rx - 1, cx + rx + 2):
            d = ((x + .5 - cx) / rx) ** 2 + ((y + .5 - MY) / ry) ** 2
            if d <= 1 and y <= 47:
                col = DIRT_M
                if d > .62 and y > MY:
                    col = DIRT_D
                elif d > .5 and y < MY - 1 and x < cx:
                    col = DIRT_L
                if d < .28:
                    col = DIRT_D                 # the dark hole in the middle
                c.set(x, y, col)
    for _ in range(rx):                          # loose clods
        x, y = cx + rng.randint(-rx - 2, rx + 2), MY + rng.randint(-ry - 2, ry - 1)
        c.set(x, y, rng.choice((DIRT_L, DIRT_M, DIRT_D)))


def forearm_hand(c, x, h, cuff=False):
    """A hand + forearm reaching out of the ground, h rows tall. cuff: white shirt cuff."""
    top = MY - h
    c.rect(x + 1, top + 6, 4, h - 5, SKM)                   # forearm
    c.rect(x + 1, top + 6, 1, h - 5, SKL)
    c.rect(x + 4, top + 6, 1, h - 5, SKD)
    if cuff and h > 9:
        c.rect(x, top + 10, 6, h - 9, SHW)
        c.rect(x + 4, top + 10, 2, h - 9, SHD)
    c.rect(x, top + 2, 6, 5, SKM)                           # palm
    c.rect(x, top + 2, 1, 5, SKL)
    c.rect(x + 5, top + 2, 1, 5, SKD)
    c.rect(x, top + 6, 6, 1, SKD)
    for k in (0, 2, 4):                                     # fingers up
        c.rect(x + k, top, 1, 2, SKM)
    c.set(x + 5, top + 3, SKM)
    c.set(x + 6, top + 4, SKM)                              # thumb


def spawn_frame(f):
    rng = random.Random(200 + f)
    c = C(W, H)
    rx = (5, 8, 11, 13, 14, 13, 11, 8)[f]
    if f < 3:
        for x, h, cuff in {0: [], 1: [(13, 10, False)],
                           2: [(10, 12, False), (26, 9, True)]}[f]:
            forearm_hand(c, x, h, cuff)
        if f == 2:                                          # case handle peeking out of the dirt
            c.rect(19, MY - 3, 4, 1, CASED)
            c.set(19, MY - 2, CASED)
            c.set(22, MY - 2, CASED)
    else:
        sink, pose = {
            3: (30, dict(caseArm="low", tornArm="down")),
            4: (19, dict(caseArm="low", tornArm="down", tilt=-1)),
            5: (9, dict(caseArm="low", tornArm="down", bob=1, tilt=2)),
            6: (3, dict(caseArm="mid", tornArm="out", bob=2, tilt=2)),
            7: (0, dict(caseArm="low", tornArm="down", bob=0, tilt=0)),
        }[f]
        fig = shifted(unoutlined(view("S", **pose)), 0, sink)   # outline is redrawn at the end
        clip = {3: MY - 1, 4: MY - 1, 5: MY - 1, 6: 46}.get(f, H)
        for y in range(clip, H):                            # everything below ground is hidden
            for x in range(W):
                fig.g[y][x] = 0
        if f in (3, 4):
            forearm_hand(c, 7, 7)
            forearm_hand(c, 28, 7, True)
        if f == 7:
            mound(c, 20, rx, rng)
        c.paste(fig, 0, 0)
    if f < 7:
        mound(c, 20, rx, rng)
    for _ in range((3, 5, 6, 6, 8, 10, 8, 5)[f]):           # falling / flying clods
        c.set(rng.randint(6, 34), rng.randint(MY - 24, MY - 2) if f > 2 else rng.randint(MY - 14, MY - 2),
              rng.choice((DIRT_L, DIRT_M, DIRT_D)))
    c.outline()
    return c


def rotate_fig(c, deg, scale=1.0, src=(20.0, 30.0), dst=(20.0, 22.0)):
    """Rotate/scale a finished frame about `src`, drawn around `dst`, by per-pixel majority
    sampling (no blur).  The outline is stripped first and redrawn afterwards."""
    base = unoutlined(c)
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    out = C(W, H)
    offs = (-1 / 3, 0.0, 1 / 3)
    for Y in range(H):
        for X in range(W):
            votes, order = {}, []
            for oy in offs:
                for ox in offs:
                    dx, dy = (X + .5 + ox - dst[0]) / scale, (Y + .5 + oy - dst[1]) / scale
                    sx = src[0] + ca * dx + sa * dy
                    sy = src[1] - sa * dx + ca * dy
                    ix, iy = math.floor(sx), math.floor(sy)
                    v = base.g[iy][ix] if 0 <= ix < W and 0 <= iy < H else 0
                    votes[v] = votes.get(v, 0) + 1
                    if v not in order:
                        order.append(v)
            out.g[Y][X] = max(order, key=lambda v: (votes[v], -order.index(v)))
    out.outline()
    return out


def rot90(c, k):
    o = c
    for _ in range(k % 4):
        n = C(o.h, o.w)
        for y in range(o.h):
            for x in range(o.w):
                n.g[x][o.h - 1 - y] = o.g[y][x]
        o = n
    return o


def paper(flat=False):
    """A sheet of paper (4x5, or 5x4 lying flat) with two text lines."""
    c = C(4, 5)
    c.rect(0, 0, 4, 5, SHW)
    c.rect(1, 1, 2, 1, SHD)
    c.rect(1, 3, 2, 1, SHD)
    return rot90(c, 1) if flat else c


def briefcase_open():
    """Briefcase burst open (11x9): lid flung up and back, papers sticking out of the body."""
    c = C(11, 9)
    for r in range(4):                       # lid, slanted up-left from the hinge
        c.rect(1 + (3 - r), r, 6, 1, CASE)
        c.set(1 + (3 - r), r, CASED)
        c.set(6 + (3 - r), r, CASED)
    c.rect(4, 0, 2, 1, CASED)                # lid handle
    c.rect(2, 4, 8, 1, CASED)                # lid edge meets body
    c.rect(2, 4, 8, 5, CASE)                 # body
    c.rect(3, 4, 6, 2, CASED)                # dark inside
    c.rect(3, 3, 3, 2, SHW)                  # papers poking out
    c.rect(6, 2, 3, 3, SHW)
    c.set(4, 4, SHD)
    c.set(7, 3, SHD)
    c.set(7, 4, SHD)
    c.rect(2, 7, 8, 1, CASED)                # belt
    c.rect(2, 8, 8, 1, CASED)
    c.rect(9, 4, 1, 5, CASED)
    c.set(5, 7, TAG)
    c.set(6, 7, TAG)
    return c


# Burst parts:  name -> (sprite, start x,y, final x,y, rotation per frame t=0..4, arc height)
def die_parts():
    arm_l = unoutlined(Z.arm(0)[0]).crop(0)
    arm_r = unoutlined(Z.arm(0, torn=True)[0].flip()).crop(0)
    return [
        ("legL", unoutlined(Z.leg("L")), (13, 34), (2, 27), (3, 2, 1, 1, 1), 5),
        ("legR", unoutlined(Z.leg("R")), (21, 34), (24, 30), (1, 2, 3, 3, 3), 5),
        ("torso", unoutlined(Z.torso()), (14, 21), (14, 31), (0, 3, 2, 0, 0), 6),
        ("head", unoutlined(Z.head()), (14, 8), (2, 33), (1, 2, 3, 0, 0), 8),
        ("case", briefcase_open(), (5, 30), (27, 36), (0, 0, 0, 0, 0), 12),
        ("armL", arm_l, (5, 21), (15, 25), (1, 2, 3, 0, 0), 8),
        ("armR", arm_r, (25, 21), (3, 21), (3, 2, 1, 0, 0), 8),
    ]


PROG = (0.2, 0.5, 0.8, 0.96, 1.0)                     # flight progress per burst frame
PAPER_PROG = (0.1, 0.38, 0.66, 0.9, 1.0)
PAPER_SPOTS = [(26, 26), (32, 26), (19, 43)]


def die_frame(f):
    rng = random.Random(7)
    c = C(W, H)
    if f == 0:                                       # hit: white flash + recoil
        fig = view("S", dx=-1, tilt=-3, caseArm="mid", tornArm="up", head="S")
        for y in range(H):
            for x in range(W):
                if fig.g[y][x] > 1:
                    fig.g[y][x] = FLASH
        return fig
    if f in (1, 2):                                  # swelling up, cracks glowing
        fig = view("S", dx=(-1 if f == 1 else 1), tilt=(2 if f == 1 else -2),
                   caseArm="mid", tornArm="out")
        k = 1.08 if f == 1 else 1.15              # pivot on the head top so nothing leaves the canvas
        fig = rotate_fig(fig, 0, k, (20, 8), (20, 3 if f == 1 else 2.5))
        for _ in range(5 * f):
            x, y = rng.randint(10, 30), rng.randint(14, 44)
            for (px, py) in ((x, y), (x + 1, y + 1), (x + 1, y + 2), (x + 2, y + 3)):
                if 0 <= px < W and 0 <= py < H and fig.g[py][px] > 1:
                    fig.g[py][px] = GOO
        return fig
    t = f - 3                                         # 0..4: burst, fall, land
    # goo puddle on the ground (behind the parts)
    pr = (0, 0, 0, 6, 10, 14, 16, 17)[f]
    if pr:
        for y in range(36, REST + 1):
            for x in range(W):
                d = ((x + .5 - 20) / pr) ** 2 + ((y + .5 - 44) / (pr * .3)) ** 2
                if d <= 1:
                    col = GOO_D if d > .7 else GOO
                    if x < 20 and y < 43 and d > .3:
                        col = GOO
                    if (x * 7 + y * 3) % 17 == 0 and d < .6:
                        col = TAG                     # shine
                    c.set(x, y, col)
    if f >= 5:                                        # a few bones in the puddle
        for (bx, by) in ((4, 46), (27, 47), (11, 47)):
            c.rect(bx, by, 5, 1, TAG)
            c.set(bx - 1, by - 1, TAG)
            c.set(bx + 5, by - 1, TAG)
    # burst parts: centre moves from the standing spot to the resting spot along an arc
    p = PROG[t]
    for name, spr, (sx, sy), (fx, fy), ks, arc in die_parts():
        fin = rot90(spr, ks[-1])
        cur = rot90(spr, ks[t])
        scx, scy = sx + spr.w / 2, sy + spr.h / 2
        fcx, fcy = fx + fin.w / 2, fy + fin.h / 2
        cx_ = scx + (fcx - scx) * p
        cy_ = scy + (fcy - scy) * p - arc * 4 * p * (1 - p)
        x = max(2, min(W - 2 - cur.w, round(cx_ - cur.w / 2)))
        y = max(2, round(cy_ - cur.h / 2))
        c.paste(cur, x, y)
    # papers flutter out of the case, drift sideways and settle flat on the ground
    pp = PAPER_PROG[t]
    for i, (fx, fy) in enumerate(PAPER_SPOTS):
        scx, scy = 12 + i, 34
        cx_ = scx + (fx - scx) * pp + math.sin(pp * 7 + i * 1.7) * 4 * (1 - pp)
        cy_ = scy + (fy - scy) * pp - 15 * 4 * pp * (1 - pp) * (0.7 + .1 * i)
        flat = t >= 3 or (t + i) % 2 == 0
        spr = unoutlined(paper(flat))
        x = max(2, min(W - 2 - spr.w, round(cx_)))
        c.paste(spr, x, max(2, min(REST + 1 - spr.h, round(cy_))))
    # flying goo droplets
    for i in range(18):
        a = i * 2 * math.pi / 18 + .2
        sp = 4 + (i % 4) * 1.7
        life = t + 1
        x = 20 + math.cos(a) * sp * life * .9
        y = 28 + math.sin(a) * sp * life * .55 + .5 * 1.1 * life * life
        if y >= 45:                                  # landed: stays as a splat
            y = 44 + (i % 3)
            x = 20 + math.cos(a) * min(sp * 4, 17) * 1.15
        if 2 <= x < W - 3 and 2 <= y < REST - 1:
            c.rect(int(x), int(y), 2 if i % 3 else 1, 2 if i % 2 else 1, GOO if i % 2 else GOO_D)
    c.outline()
    return c


# -------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    sheets = {}
    jobs = [("danceB", dance_pirouette, "danceB"), ("danceC", dance_robot, "danceC"),
            ("spawn", spawn_frame, "spawn"), ("die", die_frame, "die")]
    for key, fn, tag in jobs:
        sheets[key] = []
        for f in range(8):
            im = fn(f).image()
            im.save(os.path.join(OUT, f"zombie2_{tag}_{f}.png"))
            sheets[key].append(im)
    for dname in DIRS:
        sheets[dname] = []
        for p in range(6):
            im = walk_frame(dname, p).image()
            im.save(os.path.join(OUT, f"zombie2_walk_{dname}_{p}.png"))
            sheets[dname].append(im)

    hw, hh = 80, 100
    prev = Image.new("RGBA", (8 * (hw + 6) + 12, 12 * (hh + 22) + 10), (88, 92, 104, 255))
    d = ImageDraw.Draw(prev)
    for r, key in enumerate(["danceB", "danceC", "spawn", "die"] + DIRS):
        y = 8 + r * (hh + 22)
        d.text((6, y), key, fill=(255, 255, 255, 255))
        for i, im in enumerate(sheets[key]):
            prev.alpha_composite(im.resize((hw, hh), Image.NEAREST), (6 + i * (hw + 6), y + 12))
    prev.save(os.path.join(OUT, "zombie2_moves_preview.png"))
    print("wrote", len(os.listdir(OUT)), "files to", OUT)


if __name__ == "__main__":
    main()
