#!/usr/bin/env python3
"""
Zombie 1 - extra moves: 2 new dances (8 frames each) + 8-direction walk cycle
(6 frames per direction). Full-body 160x200 sprites only (no body parts).

Run:   python3 make_zombie1_moves.py [output_dir]
Needs: make_zombie1.py in the same folder (parts, palette and canvas class are
       reused from it, so the zombie is guaranteed identical), Pillow, numpy.

Output (default ./zombie1_moves/):
    zombie1_danceB_0..7.png        "Twist & jump"   (wide sway, jumps, squat)
    zombie1_danceC_0..7.png        "Lurch & claw"   (reach arms, head wobble, claw jumps)
    zombie1_walk_<DIR>_0..5.png    DIR = N NE E SE S SW W NW, 6 frames each
    zombie1_moves_preview.png      contact sheet (not part of the set)
The original dance is zombie1_dance0..7.png from make_zombie1.py.

How the 8 directions are made
  S  = the front view you already have (reach arms, shuffling legs)
  N  = back view (hair-covered head, plain shirt back)
  E  = side profile (new head / torso / legs / arms drawn below)
  SE = 3/4 front view      NE = 3/4 back view
  W, SW, NW = the E, SE, NE frames mirrored.

Where to change things
  * Dances ........ DANCE_B / DANCE_C tables (same fields as DANCE in make_zombie1.py,
                    plus  hop = pixels the whole body jumps off the ground)
  * Walk timing ... BOB, SWING_SIDE, and the sin/cos lines inside the *_walk functions
  * New body parts  head_side(), torso_side(), leg_side(), arm_side(),
                    head_back(), torso_back(), head_3q()
  * Colours ....... PAL in make_zombie1.py
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_zombie1 as Z                                  # noqa: E402
from make_zombie1 import C                                # noqa: E402
from PIL import Image, ImageDraw                          # noqa: E402

W, H, CX, GROUND = Z.W, Z.H, Z.CX, Z.GROUND
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "zombie1_moves")

# palette indices (same as make_zombie1.PAL)
OUTL, SKD, SKM, SKL, SHD, SHL, PTD, PTL = 1, 2, 3, 4, 5, 6, 7, 8
EYE, PUPIL, TOOTH, SHOE, ROT, HAIR, SHOEL = 9, 10, 11, 12, 13, 14, 15

# ----------------------------------------------------------------- dances
# fields: dx tilt bob armL armR lift rdy  (see make_zombie1.py)  + hop
DANCE_B = [   # Twist & jump
    dict(dx=-3, tilt=-3, bob=0, armL="up",   armR="down", lift="R", rdy=(0, 0)),
    dict(dx=-2, tilt=-2, bob=1, armL="out",  armR="out",  lift=None, rdy=(0, 0)),
    dict(dx=0,  tilt=0,  bob=0, armL="up",   armR="up",   lift=None, rdy=(0, 0), hop=3),
    dict(dx=2,  tilt=2,  bob=1, armL="down", armR="up",   lift=None, rdy=(0, 0)),
    dict(dx=3,  tilt=3,  bob=0, armL="down", armR="up",   lift="L", rdy=(0, 0)),
    dict(dx=2,  tilt=2,  bob=2, armL="out",  armR="out",  lift=None, rdy=(0, 0)),
    dict(dx=0,  tilt=0,  bob=0, armL="up",   armR="up",   lift=None, rdy=(0, 0), hop=3),
    dict(dx=-2, tilt=-2, bob=1, armL="out",  armR="out",  lift=None, rdy=(0, 0)),
]
DANCE_C = [   # Lurch & claw
    dict(dx=-1, tilt=-3, bob=0, armL="reach", armR="reach", lift="R", rdy=(-1, 1)),
    dict(dx=-1, tilt=-2, bob=2, armL="reach", armR="reach", lift=None, rdy=(1, -1)),
    dict(dx=0,  tilt=0,  bob=0, armL="up",    armR="up",    lift=None, rdy=(0, 0), hop=2),
    dict(dx=1,  tilt=3,  bob=0, armL="reach", armR="reach", lift="L", rdy=(1, -1)),
    dict(dx=1,  tilt=3,  bob=2, armL="reach", armR="reach", lift=None, rdy=(-1, 1)),
    dict(dx=0,  tilt=0,  bob=0, armL="up",    armR="up",    lift=None, rdy=(0, 0), hop=2),
    dict(dx=-1, tilt=-3, bob=1, armL="out",   armR="out",   lift="R", rdy=(0, 0)),
    dict(dx=0,  tilt=-2, bob=2, armL="down",  armR="down",  lift=None, rdy=(0, 0)),
]
HAND_DY = Z.HAND_DY


def sheared(head, tilt, w=18, ox=3):
    """Head leaning by `tilt` px at the top, pivoting around the chin."""
    o = C(w, 12)
    for r in range(12):
        sh = round(tilt * (11 - r) / 11)
        for i in range(12):
            if head.g[r][i]:
                o.set(ox + sh + i, r, head.g[r][i])
    return o


def dance_frame(d):
    """Same drawing as make_zombie1.frame(), with an extra `hop` (jump) field."""
    dx, bob, hop = d["dx"], d["bob"], d.get("hop", 0)
    c = C(W, H)
    kx = 1 if bob >= 2 else 0
    ly = GROUND - (14 - bob) - hop
    lyL = ly - (1 if d["lift"] == "L" else 0)
    lyR = ly - (1 if d["lift"] == "R" else 0)
    lxL = CX - 7 + dx - kx - (1 if d["lift"] == "L" else 0)
    lxR = CX + 1 + dx + kx + (1 if d["lift"] == "R" else 0)
    c.paste(Z.leg("L", bob), lxL, lyL)
    c.paste(Z.leg("R", bob), lxR, lyR)
    c.rect(CX - 6 + dx, 34 + bob - hop, 12, 3, PTL)
    c.rect(CX + 2 + dx, 34 + bob - hop, 4, 3, PTD)
    c.paste(Z.torso(), CX - 6 + dx, 21 + bob - hop)
    for side, pose in (("L", d["armL"]), ("R", d["armR"])):
        if pose == "reach":
            a = Z.reach_arm()
            ydy = d["rdy"][0 if side == "L" else 1]
            if side == "L":
                c.paste(a, 12 + dx, 19 + bob + ydy - hop)
            else:
                c.paste(a.flip(), 20 + dx, 19 + bob + ydy - hop)
        else:
            a = Z.arm(HAND_DY[pose])
            if side == "L":
                c.paste(a, 5 + dx, 14 + bob - hop)
            else:
                c.paste(a.flip(), 25 + dx, 14 + bob - hop)
    c.rect(CX - 2 + dx, 20 + bob - hop, 4, 1, SKD)
    c.paste(sheared(Z.head(), d["tilt"]), CX - 9 + dx, 8 + bob - hop)
    c.outline()
    return c


# ------------------------------------------------------------ new body parts
def head_side():
    """Profile head looking right."""
    c = C(12, 12)
    for y, (a, b) in {1: (1, 9), 2: (0, 9), 3: (0, 9), 4: (0, 9), 5: (0, 9), 6: (0, 9),
                      7: (0, 9), 8: (0, 9), 9: (1, 9), 10: (3, 8), 11: (4, 7)}.items():
        for x in range(a, b + 1):
            c.set(x, y, SKM)
    for y in range(3, 10):
        c.set(9, y, SKD)                    # front edge in shade
    c.rect(10, 6, 1, 2, SKM)                # nose
    c.set(10, 7, SKD)
    c.rect(1, 0, 9, 2, HAIR)                # hair on top ...
    c.rect(0, 2, 4, 5, HAIR)                # ... and at the back
    c.rect(6, 1, 3, 1, ROT)
    c.rect(3, 6, 2, 2, SKD)                 # ear
    c.rect(6, 3, 3, 1, SKD)                 # brow
    c.rect(6, 4, 3, 3, EYE)
    c.rect(8, 5, 1, 2, PUPIL)
    c.rect(6, 7, 3, 1, SKD)                 # eye bag
    c.rect(6, 9, 4, 1, PUPIL)               # mouth
    c.rect(6, 10, 3, 1, PUPIL)
    c.set(8, 9, TOOTH)
    return c


def torso_side():
    c = C(8, 14)
    c.rect(0, 0, 8, 12, SHL)
    c.rect(5, 0, 3, 12, SHD)
    c.rect(2, 0, 4, 1, SKD)                 # collar
    c.rect(5, 6, 3, 1, SKM)                 # belly tear (front)
    c.rect(5, 7, 2, 1, TOOTH)
    c.rect(5, 8, 3, 1, SKD)
    for x in (0, 3, 6):
        c.set(x, 12, SHL if x < 5 else SHD)
    c.set(3, 13, SHL)
    return c


def leg_side(swing, short=0):
    """Leg seen from the side, foot pointing right. `swing` = how many px the
    foot is shifted forward (+) / back (-) relative to the hip (sheared leg)."""
    n = 8 - short
    rows = 14 - short
    base = 6
    c = C(16, rows)
    for r in range(rows):
        off = round(swing * r / (rows - 1))
        x = base + off
        if r < n:                                    # pants
            c.rect(x, r, 3, 1, PTL)
            c.set(x + 3, r, PTD)
            if r == 4:
                c.set(x + 1, r, SKM)                 # knee tear
        elif r < n + 3:                              # shin
            c.rect(x + 1, r, 2, 1, SKM)
            c.set(x + 3, r, SKD)
        else:                                        # shoe, toes forward
            c.rect(x, r, 5, 1, SHOE)
            if r == n + 3:
                c.rect(x, r, 3, 1, SHOEL)
    return c


def arm_side(dy):
    """Arm stretched forward (right), hand `dy` px higher(-)/lower(+) than the shoulder."""
    c = C(14, 18)
    yb = 7
    for x in range(10):
        y = yb + round(dy * x / 9)
        if x < 4:
            c.rect(x, y, 1, 4, SHL if x < 2 else SHD)      # sleeve
        else:
            c.rect(x, y, 1, 3, SKM)
            c.set(x, y, SKL)
            c.set(x, y + 2, SKD)
    ye = yb + dy
    c.rect(9, ye - 1, 4, 5, SKM)                            # hand
    c.rect(9, ye - 1, 4, 1, SKL)
    c.rect(9, ye + 3, 4, 1, SKD)
    c.set(13, ye - 1, SKM)
    c.set(13, ye + 1, SKM)
    c.set(13, ye + 3, SKM)
    return c


def head_back():
    """Back of the head: hair all over, ears, neck."""
    c = C(12, 12)
    for y, (a, b) in {2: (1, 10), 3: (0, 11), 4: (0, 11), 5: (0, 11), 6: (0, 11), 7: (0, 11),
                      8: (0, 11), 9: (1, 10), 10: (3, 8), 11: (3, 8)}.items():
        for x in range(a, b + 1):
            c.set(x, y, SKM)
    c.rect(1, 1, 10, 1, HAIR)
    for x in (1, 3, 6, 8, 10):
        c.set(x, 0, HAIR)
    c.rect(1, 2, 10, 7, HAIR)
    c.rect(0, 3, 12, 2, HAIR)
    c.rect(2, 9, 8, 1, HAIR)
    c.rect(3, 9, 1, 1, SKD)
    c.rect(7, 2, 3, 2, ROT)                 # rot patch
    c.set(0, 5, SKD)                        # ears
    c.set(0, 6, SKM)
    c.set(11, 5, SKD)
    c.set(11, 6, SKD)
    c.rect(4, 10, 4, 2, SKD)                # neck
    return c


def torso_back():
    c = C(12, 14)
    c.rect(0, 0, 12, 12, SHL)
    c.rect(8, 0, 4, 12, SHD)
    c.rect(3, 0, 6, 1, SKD)                 # collar
    c.rect(2, 5, 3, 2, ROT)                 # patched hole
    c.rect(6, 8, 3, 1, SKM)                 # small tear
    c.rect(6, 9, 2, 1, SKD)
    for x in (0, 1, 4, 5, 9, 10, 11):
        c.set(x, 12, SHL if x < 8 else SHD)
    for x in (0, 4, 10):
        c.set(x, 13, SHL if x < 8 else SHD)
    return c


def head_3q(back=False):
    """3/4 head turned to the right. back=True: seen from behind."""
    if back:
        h = head_back()
        for y in range(4, 10):               # a strip of cheek peeks out on the right
            h.set(11, y, SKM)
            h.set(10, y, SKD if y in (5, 6) else HAIR)
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
    c.rect(1, 1, 10, 1, HAIR)
    for x in (1, 3, 6, 8, 10):
        c.set(x, 0, HAIR)
    c.rect(0, 2, 3, 3, HAIR)
    c.rect(8, 2, 3, 1, ROT)
    c.rect(3, 3, 2, 1, SKD)                  # far brow / eye (narrow)
    c.rect(3, 4, 2, 3, EYE)
    c.rect(4, 5, 1, 2, PUPIL)
    c.rect(7, 3, 4, 1, SKD)                  # near brow / eye
    c.rect(7, 4, 3, 3, EYE)
    c.rect(9, 4, 1, 2, PUPIL)
    c.rect(3, 7, 2, 1, SKD)
    c.rect(7, 7, 3, 1, SKD)
    c.set(6, 7, SKD)                         # nose
    c.set(7, 8, SKD)
    c.rect(5, 9, 6, 1, PUPIL)                # mouth
    c.rect(6, 10, 4, 1, PUPIL)
    c.set(6, 9, TOOTH)
    c.set(9, 9, TOOTH)
    return c


def shade_far(c):
    """Darken a canvas (used for the limbs on the far side, for depth)."""
    m = {PTL: PTD, SKM: SKD, SKL: SKM, SHL: SHD, SHOEL: SHOE, SKD: SKD}
    o = C(c.w, c.h)
    o.g = [[m.get(v, v) for v in row] for row in c.g]
    return o


# ------------------------------------------------------------- views (8 facings)
# One builder per body view. Every builder takes a POSE (dx, bob, hop, leg swing ...),
# so the same drawings serve both the walks and the dances. hop = whole body jumps up;
# bob = knees bend (legs shorten, feet stay on the floor unless hop > 0).
DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def v_front(**k):
    d = dict(dx=0, tilt=0, bob=0, hop=0, armL="out", armR="out", lift=None, rdy=(0, 0))
    d.update(k)
    return dance_frame(d)


def v_back3q(back, three_q, dx=0, bob=0, hop=0, s=0, lift=None, hyL=3, hyR=3, near="arm",
             tilt=0, rdy=0):
    """N (back, three_q False) and NE / SE (three_q True).
    s = leg shift (3/4 views), hyL/hyR = arm height (3 = hanging, -6 = raised),
    near = 'arm' | 'reach' (SE only: near arm reaching toward the viewer)."""
    c = C(W, H)
    ly = GROUND - (14 - bob) - hop
    sep = 5 if three_q else 7
    c.paste(Z.leg("L", bob), CX - sep + dx + s - (1 if lift == "L" else 0), ly - (1 if lift == "L" else 0))
    c.paste(Z.leg("R", bob), CX + (0 if three_q else 1) + dx - s + (1 if lift == "R" else 0),
            ly - (1 if lift == "R" else 0))
    tor = torso_back() if back else Z.torso()
    tw = 12
    if three_q:
        t2 = C(10, 14)
        t2.g = [row[1:11] for row in tor.g]
        tor, tw = t2, 10
    tx = CX - tw // 2 + dx
    y0 = bob - hop
    c.rect(tx, 34 + y0, tw, 3, PTL)
    c.rect(tx + tw - 4, 34 + y0, 4, 3, PTD)
    if not three_q:
        c.paste(Z.arm(hyL), 5 + dx, 14 + y0)
        c.paste(Z.arm(hyR).flip(), 25 + dx, 14 + y0)
        c.paste(tor, tx, 21 + y0)
    else:
        c.paste(Z.arm(hyL), 7 + dx, 14 + y0)                 # far arm, behind the body
        c.paste(tor, tx, 21 + y0)
        if back or near == "arm":
            c.paste(Z.arm(hyR).flip(), 24 + dx, 14 + y0)
        else:
            c.paste(Z.reach_arm().flip(), 21 + dx, 21 + y0 - rdy)
    c.rect(CX - 2 + dx, 20 + y0, 4, 1, SKD)
    head = head_back() if (back and not three_q) else head_3q(back)
    c.paste(sheared(head, tilt), CX - 9 + dx + (1 if three_q else 0), 8 + y0)
    c.outline()
    return c


def v_side(dx=0, bob=0, hop=0, swing=0, lift=None, dyN=-1, dyF=-1, tilt=1, lean=1, farswing=None):
    """Profile facing right. swing = near foot forward(+)/back(-); far foot defaults to -swing."""
    fs = -swing if farswing is None else farswing
    c = C(W, H)
    ly = GROUND - (14 - bob) - hop
    y0 = bob - hop
    c.paste(shade_far(leg_side(fs, bob)), CX - 8 + dx, ly - (1 if lift == "R" else 0))
    c.paste(leg_side(swing, bob), CX - 8 + dx, ly - (1 if lift == "L" else 0))
    c.rect(CX - 4 + lean + dx, 34 + y0, 8, 3, PTL)
    c.rect(CX + lean + dx, 34 + y0, 4, 3, PTD)
    c.paste(shade_far(arm_side(dyF)), CX - 3 + lean + dx, 17 + y0)
    c.paste(torso_side(), CX - 4 + lean + dx, 21 + y0)
    c.paste(arm_side(dyN), CX - 3 + lean + dx, 17 + y0)
    c.rect(CX - 2 + lean + dx, 20 + y0, 3, 1, SKD)
    c.paste(sheared(head_side(), tilt), CX - 8 + lean + dx, 8 + y0)
    c.outline()
    return c


def view(direction, **pose):
    """Draw the zombie facing `direction` with the given pose; W/SW/NW are mirrors."""
    flip = direction in ("SW", "W", "NW")
    d = {"SW": "SE", "W": "E", "NW": "NE"}.get(direction, direction)
    if d == "S":
        c = v_front(**pose)
    elif d == "N":
        c = v_back3q(True, False, **pose)
    elif d == "E":
        c = v_side(**pose)
    elif d == "SE":
        c = v_back3q(False, True, **pose)
    else:
        c = v_back3q(True, True, **pose)
    return c.flip() if flip else c


# ------------------------------------------------------------------- walks
BOB = [1, 0, 0, 1, 0, 0]          # body is lowest when both feet are down


def ph(p):
    a = 2 * math.pi * p / 6
    return math.cos(a), math.sin(a)


def lifts(p):
    """Which foot is in the air: left swings forward at p 4-5, right at p 1-2."""
    return "L" if p in (4, 5) else ("R" if p in (1, 2) else None)


def walk_frame(direction, p):
    cs, sn = ph(p)
    d = {"SW": "SE", "W": "E", "NW": "NE"}.get(direction, direction)
    if d == "S":
        pose = dict(dx=round(sn), tilt=round(2 * sn), bob=BOB[p], armL="reach", armR="reach",
                    lift=lifts(p), rdy=(round(1.4 * sn), -round(1.4 * sn)))
    elif d == "E":
        pose = dict(bob=BOB[p], lift=lifts(p), swing=round(5 * cs), dyN=round(2 * sn) - 1,
                    dyF=-round(2 * sn) - 1, tilt=round(1.5 * sn) + 1)
    elif d == "N":
        pose = dict(dx=round(sn), bob=BOB[p], lift=lifts(p), hyL=3 + round(2 * sn),
                    hyR=3 - round(2 * sn), tilt=round(1.5 * sn))
    else:
        pose = dict(dx=round(sn), bob=BOB[p], lift=lifts(p), s=round(2 * cs),
                    hyL=3 + round(2 * sn), hyR=3 - round(2 * sn), tilt=round(1.5 * sn),
                    near="reach", rdy=round(sn))
    return view(direction, **pose)


# ------------------------------------------------------------------ dances
# B "Pirouette": a full 360 spin through all eight facings, with a jump (hop) arc:
#    crouch, launch, tuck at the top, land. Arms go up for the spin.
SPIN = ["S", "SE", "E", "NE", "N", "NW", "W", "SW"]


def dance_pirouette(f):
    d = SPIN[f]
    hop = (0, 3, 5, 6, 6, 4, 2, 0)[f]
    bob = (2, 1, 1, 2, 2, 1, 0, 2)[f]
    up = f in (1, 2, 3, 4, 5)
    if d in ("S",):
        return view(d, bob=bob, hop=hop, armL="out", armR="out", tilt=0)
    if d in ("SE", "SW"):
        return view(d, bob=bob, hop=hop, hyL=-6 if up else 0, hyR=-6 if up else 0, near="arm", tilt=1)
    if d in ("E", "W"):
        return view(d, bob=bob, hop=hop, dyN=-5 if up else -1, dyF=-5 if up else -1, swing=1 if hop else 0,
                    tilt=-1)
    if d in ("NE", "NW"):
        return view(d, bob=bob, hop=hop, hyL=-6, hyR=-6, tilt=-1)
    return view(d, bob=bob, hop=hop, hyL=-6, hyR=-6, tilt=0)


# C "Backflip": crouch, launch, a full in-air tuck-and-rotate (the finished frame is
#    re-sampled pixel by pixel for each angle, nothing is blurred), land, ta-da.
def rotate_fig(c, deg, scale=1.0, src=(20.0, 30.0), dst=(20.0, 22.0)):
    """Rotate a finished frame by `deg` (clockwise on screen) about `src`, drawing the
    result around `dst`. The outline is stripped first and redrawn afterwards."""
    base = C(W, H)
    base.g = [[0 if v == 1 else v for v in row] for row in c.g]
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
                    sx = src[0] + ca * dx + sa * dy          # inverse rotation
                    sy = src[1] - sa * dx + ca * dy
                    ix, iy = math.floor(sx), math.floor(sy)
                    v = base.g[iy][ix] if 0 <= ix < W and 0 <= iy < H else 0
                    votes[v] = votes.get(v, 0) + 1
                    if v not in order:
                        order.append(v)
            out.g[Y][X] = max(order, key=lambda v: (votes[v], -order.index(v)))
    out.outline()
    return out


def dance_backflip(f):
    if f == 0:                                       # crouch, arms swung back
        return view("E", bob=2, dyN=3, dyF=3, swing=-1, farswing=1, tilt=0, lean=1)
    if f == 1:                                       # take-off, leaning back
        return rotate_fig(view("E", bob=1, hop=4, dyN=-6, dyF=-6, tilt=-2),
                          -25, 1.0, (20, 30 - 4), (20, 26))
    if f in (2, 3, 4, 5):                            # tucked rotation (knees up, arms hug)
        ang = {2: -100, 3: -190, 4: -270, 5: -335}[f]
        return rotate_fig(view("E", bob=3, hop=0, dyN=5, dyF=5, tilt=1, swing=2, farswing=3),
                          ang, 0.78, (20, 32), (20, 21))
    if f == 6:                                       # landing
        return view("E", bob=2, dyN=-1, dyF=1, swing=2, farswing=-2, tilt=1)
    return view("S", bob=0, armL="up", armR="up", tilt=0, hop=1)           # ta-da


# D "Moonwalk": profile glide - feet slide without lifting, body leans back, near arm
#    points up, then a hop-turn to the front for a disco point.
def dance_moonwalk(f):
    k = f
    if k < 5:
        cs, sn = math.cos(2 * math.pi * k / 5), math.sin(2 * math.pi * k / 5)
        return view("E", bob=1 if k % 2 else 0, swing=round(3 * cs), farswing=round(-3 * cs),
                    lift="R" if sn > .3 else ("L" if sn < -.3 else None), lean=-1,
                    dyN=-6 if k in (1, 2) else -3, dyF=2, tilt=-3)
    if k == 5:
        return view("SE", hop=2, bob=1, hyL=2, hyR=-6, near="arm", tilt=-1)
    if k == 6:
        return view("S", bob=0, armL="down", armR="up", tilt=-3, dx=1)
    return view("SE", hop=2, bob=1, hyL=2, hyR=-6, near="arm", tilt=1)


# ------------------------------------------------------- spawn (crawl out) & die (splat)
# Two extra palettes entries: dirt (3 tones) and green goo (2 tones). Change them here.
DIRT_D, DIRT_M, DIRT_L, GOO, GOO_D = 16, 17, 18, 19, 20
Z.PAL.update({DIRT_D: (74, 52, 40), DIRT_M: (112, 84, 60), DIRT_L: (150, 118, 84),
              GOO: (150, 230, 80), GOO_D: (70, 150, 56)})
GY = 47                                    # ground line (logical row) the zombie rises from


def shifted(c, dx, dy):
    o = C(c.w, c.h)
    o.paste(c, dx, dy)
    return o


def unoutlined(c):
    o = C(c.w, c.h)
    o.g = [[0 if v == 1 else v for v in row] for row in c.g]
    return o


def mound(c, cx, rx, rng, front=True):
    """Pile of dirt at the ground line. rx = half width."""
    ry = max(2, round(rx * .42))
    for y in range(GY - ry - 1, GY + ry + 2):
        for x in range(cx - rx - 1, cx + rx + 2):
            d = ((x + .5 - cx) / rx) ** 2 + ((y + .5 - GY) / ry) ** 2
            if d <= 1:
                col = DIRT_M
                if d > .62 and y > GY:
                    col = DIRT_D
                elif d > .5 and y < GY - 1 and x < cx:
                    col = DIRT_L
                if d < .28:
                    col = DIRT_D                 # the dark hole in the middle
                c.set(x, y, col)
    for _ in range(rx):                          # loose clods
        x, y = cx + rng.randint(-rx - 2, rx + 2), GY + rng.randint(-ry - 2, ry + 1)
        c.set(x, y, rng.choice((DIRT_L, DIRT_M, DIRT_D)))


def forearm_hand(c, x, h):
    """A hand + forearm reaching up out of the ground, h rows tall."""
    c.rect(x + 1, GY - h + 6, 5, h - 5, SKM)
    c.rect(x + 1, GY - h + 6, 1, h - 5, SKL)
    c.rect(x + 5, GY - h + 6, 1, h - 5, SKD)
    hand = Z.extra_hand()
    for j in range(6):
        for i in range(7):
            if hand.g[j][i]:
                c.set(x + i, GY - h + j, hand.g[j][i])


def spawn_frame(f):
    rng = random.Random(100 + f)
    c = C(W, H)
    rx = (5, 8, 11, 13, 14, 13, 11, 8)[f]
    if f < 3:
        for x, h in {0: [], 1: [(13, 10)], 2: [(10, 12), (26, 9)]}[f]:
            forearm_hand(c, x, h)
    else:
        sink, pose = {
            3: (32, dict(armL="down", armR="down")),
            4: (21, dict(armL="down", armR="down", tilt=-1)),
            5: (10, dict(armL="down", armR="down", bob=1, tilt=2)),
            6: (3, dict(armL="out", armR="out", bob=2, tilt=2)),
            7: (0, dict(armL="out", armR="out", bob=0, tilt=0)),
        }[f]
        fig = view("S", **pose)
        fig = shifted(fig, 0, sink)
        if f < 6:
            for y in range(GY - 1, H):                    # everything below the ground is hidden
                for x in range(W):
                    fig.g[y][x] = 0
        if f in (3, 4):
            for x in (7, 28):
                forearm_hand(c, x, 7)
        if f >= 6:
            mound(c, 20, rx, rng)
        c.paste(fig, 0, 0)
    if f < 6:
        mound(c, 20, rx, rng)
    for _ in (3, 5, 6, 6, 8, 10, 8, 5)[f:f + 1][0] * [0]:
        pass
    for _ in (3, 5, 6, 6, 8, 10, 8, 5)[f] * [0]:
        c.set(rng.randint(6, 34), rng.randint(GY - 24, GY - 2) if f > 2 else rng.randint(GY - 14, GY - 2),
              rng.choice((DIRT_L, DIRT_M, DIRT_D)))
    c.outline()
    return c


def rot90(c, k):
    o = c
    for _ in range(k % 4):
        n = C(o.h, o.w)
        for y in range(o.h):
            for x in range(o.w):
                n.g[x][o.h - 1 - y] = o.g[y][x]
        o = n
    return o


def die_frame(f):
    rng = random.Random(7)
    c = C(W, H)
    stand = dict(armL="out", armR="out")
    if f == 0:                                       # hit: white flash + recoil
        fig = view("S", dx=-1, tilt=-3, armL="up", armR="up", **{})
        for y in range(H):
            for x in range(W):
                if fig.g[y][x] > 1:
                    fig.g[y][x] = TOOTH
        return fig
    if f in (1, 2):                                  # swelling up, cracks glowing
        fig = view("S", dx=(-1 if f == 1 else 1), bob=0, armL="out", armR="out", tilt=(2 if f == 1 else -2))
        k = 1.18 if f == 1 else 1.4
        fig = rotate_fig(fig, 0, k, (20, 36), (20, 36 + (0 if f == 1 else 1)))
        for _ in range(5 * f):
            x, y = rng.randint(10, 30), rng.randint(14, 44)
            line = [(x, y), (x + 1, y + 1), (x + 1, y + 2), (x + 2, y + 3)]
            for (px, py) in line:
                if 0 <= px < W and 0 <= py < H and fig.g[py][px] > 1:
                    fig.g[py][px] = GOO
        return fig
    t = f - 3                                         # 0..4 : burst, fall, land
    # --- flying parts: (sprite, x0, y0, vx, vy, spin)
    parts = [(sheared(Z.head(), 0).crop(0), 14, 8, -.4, -6.0, 1),
             (Z.torso(), 14, 21, .6, -2.4, 0),
             (Z.arm(0), 5, 17, -3.6, -3.4, 1),
             (Z.arm(0).flip(), 25, 17, 3.8, -3.8, 3),
             (Z.leg("L"), 13, 34, -1.8, -2.8, 1),
             (Z.leg("R"), 21, 34, 1.9, -2.2, 3)]
    g = 4.4
    for sp, x0, y0, vx, vy, spin in parts:
        sp = sp if sp.g[0][0] != 99 else sp
        k = (spin * min(t, 3)) % 4
        spr = rot90(unoutlined_keep(sp), k)
        x = x0 + vx * (t + 1) * 1.6
        y = y0 + vy * (t + 1) + .5 * g * (t + 1) ** 2
        y = min(y, GY - 1 - spr.h)
        c.paste(spr, int(round(x)), int(round(y)))
    # --- goo: puddle on the ground + flying droplets
    pr = (0, 0, 0, 5, 9, 12, 14, 14)[f]
    if pr:
        for y in range(GY - 8, GY + 5):
            for x in range(W):
                d = ((x + .5 - 20) / pr) ** 2 + ((y + .5 - (GY - 1)) / (pr * .34)) ** 2
                if d <= 1:
                    col = GOO_D if d > .7 else GOO
                    if x < 20 and y < GY - 2 and d > .3:
                        col = GOO
                    if (x * 7 + y * 3) % 17 == 0 and d < .6:
                        col = TOOTH                   # shine
                    c.set(x, y, col)
    for i in range(18):
        a = i * 2 * math.pi / 18 + .2
        sp = 4 + (i % 4) * 1.7
        life = t + 1
        x = 20 + math.cos(a) * sp * life * .9
        y = 28 + math.sin(a) * sp * life * .55 + .5 * 1.1 * life * life
        if y >= GY - 1:                              # landed: stays as a splat
            y = GY - 1 + (i % 4) - 1
            x = 20 + math.cos(a) * min(sp * 4, 17) * 1.15
        if 0 <= x < W - 1 and 0 <= y < H - 1:
            c.rect(int(x), int(y), 2 if i % 3 else 1, 2 if i % 2 else 1, GOO if i % 2 else GOO_D)
    if f >= 5:                                        # a few bones in the puddle
        for (bx, by) in ((8, GY - 1), (28, GY), (22, GY + 1)):
            c.rect(bx, by, 5, 1, TOOTH)
            c.set(bx - 1, by - 1, TOOTH)
            c.set(bx + 5, by + 1, TOOTH)
    c.outline()
    return c


def unoutlined_keep(c):
    return unoutlined(c)


# -------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    sheets = {}
    for tag, fn in (("B", dance_pirouette), ("C", dance_backflip), ("D", dance_moonwalk)):
        sheets["dance" + tag] = []
        for f in range(8):
            im = fn(f).image()
            im.save(os.path.join(OUT, f"zombie1_dance{tag}_{f}.png"))
            sheets["dance" + tag].append(im)
    for tag, fn in (("spawn", spawn_frame), ("die", die_frame)):
        sheets[tag] = []
        for f in range(8):
            im = fn(f).image()
            im.save(os.path.join(OUT, f"zombie1_{tag}_{f}.png"))
            sheets[tag].append(im)
    for dname in DIRS:
        sheets[dname] = []
        for p in range(6):
            im = walk_frame(dname, p).image()
            im.save(os.path.join(OUT, f"zombie1_walk_{dname}_{p}.png"))
            sheets[dname].append(im)

    # preview at half size: 2 dance rows + 8 walk rows
    hw, hh = 80, 100
    pw = 8 * (hw + 6) + 60
    prev = Image.new("RGBA", (pw, 13 * (hh + 22) + 10), (88, 92, 104, 255))
    d = ImageDraw.Draw(prev)
    for r, key in enumerate(["danceB", "danceC", "danceD", "spawn", "die"] + DIRS):
        y = 8 + r * (hh + 22)
        d.text((6, y), key, fill=(255, 255, 255, 255))
        for i, im in enumerate(sheets[key]):
            prev.alpha_composite(im.resize((hw, hh), Image.NEAREST), (6 + i * (hw + 6), y + 12))
    prev.save(os.path.join(OUT, "zombie1_moves_preview.png"))
    print("wrote", len(os.listdir(OUT)), "files to", OUT)


if __name__ == "__main__":
    main()
