#!/usr/bin/env python3
"""
Zombie 4 (rocker) - extra moves: 2 new dances (8 frames each), 8-direction walk
cycle (6 frames per direction), spawn (crawl out of the ground) and die (splat).
Full-body 160x200 sprites only (no body parts).

Run:   python3 make_zombie4_moves.py [output_dir]
Needs: make_zombie4.py in the same folder (parts, palette and canvas class are
       reused from it, so the zombie is guaranteed identical), Pillow, numpy.

Output (default ./zombie4_moves/):
    zombie4_danceB_0..7.png        "Pirouette"      360-degree spin through all 8 facings with a jump arc
    zombie4_danceC_0..7.png        "Rock star solo" power stance, split jump, KNEE SLIDE, horns
    zombie4_walk_<DIR>_0..5.png    DIR = N NE E SE S SW W NW, 6 frames each
    zombie4_spawn_0..7.png         crawls out of the ground (last frame = neutral standing pose)
    zombie4_die_0..7.png           splat: flash, swell, burst into parts + goo (last = resting pile)
    zombie4_moves_preview.png      contact sheet (not part of the set)
The original dance is zombie4_dance0..7.png from make_zombie4.py.

How the 8 directions are made
  S  = front view (existing head/torso/legs/arms, guitar slung on the back so only
       the strap, the neck above the shoulder and the body edge at the hip show)
  N  = back view (all-pink hair, leather jacket back with a star, guitar on the back)
  E  = side profile      SE = 3/4 front       NE = 3/4 back
  W, SW, NW = the E, SE, NE frames mirrored.
The guitar is a left-handed electric (neck over the zombie's right shoulder). One
upright guitar drawing (guitar_art) is rotated / squeezed for every view.

Where to change things
  * Colours ....... PAL additions (GT_D, GT_L, NECK, DIRT_*, GOO*) just below the imports;
                    the zombie's own colours are PAL in make_zombie4.py
  * Guitar ........ guitar_art() / guitar_side_art(), put_guitar() (placement per view)
  * Body parts .... head_side/head_back/head_3q, torso_side/torso_back/torso_3q,
                    leg_side, arm_hang, arm_fwd
  * Poses ......... the view() functions take dx bob hop tilt armL/armR lift ... (see
                    v_front docstring); dances are dance_pirouette() / dance_solo()
  * Walk timing ... walk_frame()
  * Spawn / die ... spawn_frame(), die_frame()
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_zombie4 as Z                                      # noqa: E402
from make_zombie4 import C                                    # noqa: E402
from PIL import Image, ImageDraw                              # noqa: E402

W, H, CX, GROUND = Z.W, Z.H, Z.CX, Z.GROUND
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "zombie4_moves")

# ---------------------------------------------------------------- palette
# zombie 4's own colours are 1..16 (see make_zombie4.PAL). Added here (runtime):
DIRT_D, DIRT_M, DIRT_L, GOO, GOO_D = 17, 18, 19, 20, 21     # spawn dirt, die goo
GT_D, GT_L, NECK = 22, 23, 24                               # guitar body dark/light, wood
Z.PAL.update({DIRT_D: (74, 52, 40), DIRT_M: (112, 84, 60), DIRT_L: (150, 118, 84),
              GOO: (150, 230, 80), GOO_D: (70, 150, 56),
              GT_D: (190, 92, 36), GT_L: (246, 182, 56), NECK: (178, 128, 72)})

# ascii-art legend: char -> palette index ('.' = transparent)
LEG = {"o": 1, "d": 2, "m": 3, "l": 4, "k": 5, "L": 6, "j": 7, "J": 8, "w": 9, "p": 10,
       "t": 11, "s": 12, "H": 13, "h": 14, "b": 15, "r": 16, "G": GT_L, "g": GT_D, "n": NECK,
       "e": DIRT_L}
OUTL, SKD, SKM, SKL, LTD, LTL, JND, JNL = 1, 2, 3, 4, 5, 6, 7, 8
EYE, PUPIL, TOOTH, SILV, HAIR_L, HAIR_D, BOOT, RED = 9, 10, 11, 12, 13, 14, 15, 16


def art(rows):
    """Build a canvas from a list of equal-length strings (see LEG)."""
    c = C(max(len(r) for r in rows), len(rows))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != ".":
                c.set(x, y, LEG[ch])
    return c


def line(c, x0, y0, x1, y1, col):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        c.set(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n), col)


def rot(c, deg, pivot, scale=1.0):
    """Rotate a sprite by `deg` (clockwise on screen) about the pixel `pivot`
    (nearest-neighbour with 3x3 majority vote, nothing is blurred). scale may be a
    float or an (sx, sy) tuple.
    Returns (canvas, px, py) where (px, py) is where the pivot ended up."""
    px0, py0 = pivot
    sxs, sys_ = scale if isinstance(scale, tuple) else (scale, scale)
    far = max(math.hypot(x - px0, y - py0) for x in (0, c.w) for y in (0, c.h)) * max(sxs, sys_)
    n = int(far) * 2 + 4
    o = C(n, n)
    ox = oy = n // 2
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    offs = (-1 / 3, 0.0, 1 / 3)
    for Y in range(n):
        for X in range(n):
            votes, order = {}, []
            for jy in offs:
                for jx in offs:
                    dx, dy = (X + .5 + jx - ox - .5) / sxs, (Y + .5 + jy - oy - .5) / sys_
                    sx = px0 + .5 + ca * dx + sa * dy
                    sy = py0 + .5 - sa * dx + ca * dy
                    ix, iy = math.floor(sx), math.floor(sy)
                    v = c.g[iy][ix] if 0 <= ix < c.w and 0 <= iy < c.h else 0
                    votes[v] = votes.get(v, 0) + 1
                    if v not in order:
                        order.append(v)
            o.g[Y][X] = max(order, key=lambda v: (votes[v], -order.index(v)))
    return o, ox, oy


def paste_rot(dst, spr, deg, pivot, at, scale=1.0):
    """Rotate `spr` about `pivot` (sprite px) and paste so the pivot lands on `at`."""
    r, px, py = rot(spr, deg, pivot, scale)
    dst.paste(r, at[0] - px, at[1] - py)


def squeeze(c, f):
    """Narrow a sprite horizontally by factor f (nearest), for 3/4 views."""
    nw = max(1, round(c.w * f))
    o = C(nw, c.h)
    for y in range(c.h):
        for x in range(nw):
            o.g[y][x] = c.g[y][min(c.w - 1, int((x + .5) / f))]
    return o


def sheared(head, tilt):
    """Head leaning by `tilt` px at the top, pivoting around the chin."""
    o = C(head.w + 6, 12)
    for r in range(12):
        sh = round(tilt * (11 - r) / 11)
        for i in range(head.w):
            if head.g[r][i]:
                o.set(3 + sh + i, r, head.g[r][i])
    return o


def shade_far(c):
    """Darken a canvas (limbs on the far side, for depth)."""
    m = {JNL: JND, SKM: SKD, SKL: SKM, LTL: LTD, SKD: SKD}
    o = C(c.w, c.h)
    o.g = [[m.get(v, v) for v in row] for row in c.g]
    return o


def flipped_x(c):
    return c.flip()


# ---------------------------------------------------------------- the guitar
def guitar_art():
    """Upright electric guitar seen from the front (headstock up). 13 x 30.
    Body centre (the anchor used by put_guitar) is local (6, 22)."""
    return art([
        "....nnnnn....",
        "...snnnnns...",
        "....nnnnn....",
        ".....nbn.....",
        ".....nbn.....",
        ".....nbn.....",
        ".....nsn.....",
        ".....nbn.....",
        ".....nbn.....",
        ".....nsn.....",
        ".....nbn.....",
        ".....nbn.....",
        ".....nsn.....",
        ".....nbn.....",
        ".....nbn.....",
        ".....nsn.....",
        "..gGGnbnGGg..",
        ".gGGGnbnGGGg.",
        ".gGGGGGGGGGg.",
        ".gGGGGGGGGGg.",
        "..gGGGGGGGg..",
        "..gGGGGGGGg..",
        "..gGsssssGg..",
        ".gGGGGGGGGGg.",
        ".gGGGsssGGGg.",
        ".gGGGGGGGsGg.",
        ".gGGGGGGGGGg.",
        "..gGGGGGGGg..",
        "...ggGGGgg...",
        "....ggggg....",
    ])


GS_NECK = 10                                   # neck rows of the profile guitar (shorter: less sticking out)


def guitar_side_art():
    """The same guitar edge-on (profile). 6 wide, body centre local (3, GS_NECK + 9)."""
    rows = []
    for y in range(GS_NECK + 3 + 14):
        if y < 3:
            rows.append(".nnn..")
        elif y < 3 + GS_NECK:
            rows.append("..nb..")
        elif y < GS_NECK + 3 + 12:
            rows.append(".gGGg." if y not in (GS_NECK + 9, GS_NECK + 10) else ".gsGg.")
        else:
            rows.append("..gg..")
    return art(rows)


G_ANCHOR = (6, 22)
GS_ANCHOR = (3, GS_NECK + 9)


def put_guitar(c, deg, at, kind="front", flip=False, sq=1.0):
    """Draw the guitar rotated by deg (clockwise; negative = neck leans left) with its
    body centre at `at`. kind 'front' or 'side'; flip mirrors it (back views);
    sq < 1 narrows it for 3/4 views."""
    g = guitar_art() if kind == "front" else guitar_side_art()
    anc = G_ANCHOR if kind == "front" else GS_ANCHOR
    if sq != 1.0:
        g = squeeze(g, sq)
        anc = (int(anc[0] * sq), anc[1])
    if flip:
        g = g.flip()
        anc = (g.w - 1 - anc[0], anc[1])
    paste_rot(c, g, deg, anc, at)


# ----------------------------------------------------------- new body parts
def head_side():
    """Profile head looking right, 14 wide. The popped eye bulges out front."""
    c = art([
        "..H..H..h.....",
        ".HHHHHhhhh....",
        "HHHHHHhhhh....",
        "HHHHmmmmmwww..",
        "HHHmmmmmwwppw.",
        "HHHddmmmwwppw.",
        "HHHddmmmmwww..",
        "HHHsmmmmmdm...",
        "HHmmmmmmmdmd..",
        ".Hmmmmmmpppd..",
        "...mmmpppd....",
        "....dmmd......",
    ])
    for x, y in ((9, 3), (12, 4), (8, 5), (10, 6)):
        c.set(x, y, RED)
    c.set(8, 9, TOOTH)
    c.set(10, 9, TOOTH)
    c.set(9, 10, TOOTH)
    c.set(7, 5, SKD)
    c.set(7, 4, SKD)                         # brow shadow
    return c


def head_back():
    """Back of the head (viewer sees hair), 13 wide. Popped eye bulges at the LEFT
    (the zombie's left eye), stud earring in the right ear."""
    c = art([
        "..H..H..h....",
        ".HHHHHhhhhh..",
        ".HHHHHhhhhh..",
        "HHHHHHhhhhhh.",
        "HHHHHHhhhhhhw",
        "dHHHHHhhhhhdr",
        "mHHHHHhhhhhd.",
        "sHHHHHhhhhhh.",
        "HHHHHHhhhhhh.",
        "mHHHHHHhhhhd.",
        ".dmmmmmmmmd..",
        "...dmmmmd....",
    ])
    c.set(5, 3, HAIR_D)
    c.set(2, 6, HAIR_D)
    c.set(8, 7, HAIR_L)
    return c.flip()


def head_3q(back=False):
    """3/4 head turned to the right, 13 wide. back=True: seen from behind."""
    if back:
        h = head_back().flip()               # popped eye on the right again ...
        h.set(12, 4, 0)
        h.set(12, 5, 0)                      # ... but hidden behind the head here
        for y in range(4, 10):
            h.set(11, y, SKD if y in (5, 6) else SKM)   # a strip of cheek on the right
        h.set(11, 7, SILV)
        return h
    c = C(13, 12)
    for y, (a, b) in {2: (1, 10), 3: (0, 11), 4: (0, 11), 5: (0, 11), 6: (0, 11), 7: (0, 11),
                      8: (0, 11), 9: (0, 11), 10: (1, 10), 11: (3, 8)}.items():
        for x in range(a, b + 1):
            c.set(x, y, SKM)
    for y in range(3, 10):
        c.set(0, y, SKL)
        c.set(11, y, SKD)
    for x in (2, 5, 8):
        c.set(x, 0, HAIR_L if x < 6 else HAIR_D)
    c.rect(1, 1, 5, 1, HAIR_L)
    c.rect(6, 1, 5, 1, HAIR_D)
    c.rect(1, 2, 5, 1, HAIR_L)
    c.rect(6, 2, 5, 1, HAIR_D)
    c.rect(0, 3, 3, 3, HAIR_L)               # hair on the far side of the head
    c.rect(3, 3, 2, 1, SKD)                  # far eye (narrow)
    c.rect(3, 4, 2, 3, EYE)
    c.rect(4, 5, 1, 2, PUPIL)
    c.rect(3, 7, 2, 1, SKD)
    for y, (a, b) in {3: (8, 10), 4: (7, 11), 5: (7, 11), 6: (8, 10)}.items():   # popped eye
        for x in range(a, b + 1):
            c.set(x, y, EYE)
    c.rect(9, 4, 2, 2, PUPIL)
    for x, y in ((8, 3), (11, 4), (7, 5), (9, 6)):
        c.set(x, y, RED)
    c.set(6, 7, SKD)                         # nose
    c.set(7, 8, SKD)
    c.rect(5, 9, 6, 1, PUPIL)                # snarl
    c.rect(6, 10, 4, 1, PUPIL)
    for x in (6, 8, 9):
        c.set(x, 9, TOOTH)
    c.set(0, 7, SILV)                        # earring stud on the near side
    return c


def torso_side():
    """Leather jacket in profile (facing right), 8 x 14: lapel + tee at the front."""
    c = C(8, 14)
    c.rect(0, 0, 8, 12, LTD)
    c.rect(0, 0, 3, 12, LTL)
    c.rect(2, 0, 4, 1, SKD)                  # neck hole
    c.rect(6, 1, 2, 11, TOOTH)               # tee shirt at the front
    c.rect(5, 1, 1, 11, LTL)                 # lapel edge
    c.set(7, 4, RED)
    c.set(7, 5, RED)
    c.set(7, 6, RED)
    for y in (3, 6, 9):
        c.set(1, y, SILV)
    c.set(5, 11, SILV)
    c.rect(0, 12, 6, 2, LTD)
    c.rect(0, 12, 1, 2, LTL)
    c.rect(6, 12, 2, 1, TOOTH)
    return c


def torso_back():
    """Back of the jacket, 12 x 14: pink star made of paint, studded shoulders."""
    c = C(12, 14)
    c.rect(0, 0, 12, 12, LTD)
    c.rect(0, 0, 4, 12, LTL)
    c.rect(3, 0, 1, 12, LTD)
    c.rect(8, 0, 1, 12, LTL)
    c.rect(4, 0, 4, 2, SKD)                  # neck / collar
    c.rect(5, 2, 2, 1, SKD)
    for dx_, dy_, col in ((0, 0, HAIR_L), (-2, 1, HAIR_L), (-1, 1, HAIR_L), (0, 1, HAIR_L), (1, 1, HAIR_D),
                          (2, 1, HAIR_D), (-1, 2, HAIR_L), (0, 2, HAIR_D), (1, 2, HAIR_D),
                          (-1, 3, HAIR_L), (1, 3, HAIR_D)):
        c.set(3 + dx_, 3 + dy_, col)         # pink star (left of the guitar neck)
    for x, y in ((0, 0), (11, 0), (1, 9), (10, 9), (5, 11), (6, 11)):
        c.set(x, y, SILV)
    c.rect(0, 12, 4, 2, LTD)                 # jacket flaps
    c.rect(8, 12, 4, 2, LTD)
    c.rect(0, 12, 1, 2, LTL)
    return c


def torso_3q(back=False):
    """3/4 torso, 10 wide."""
    if back:
        t = torso_back()
        o = C(10, 14)
        o.g = [row[1:11] for row in t.g]
        return o
    c = C(10, 14)
    c.rect(0, 0, 10, 12, LTD)
    c.rect(0, 0, 2, 12, LTL)
    c.rect(4, 0, 3, 1, SKD)
    c.rect(5, 1, 3, 11, TOOTH)               # tee strip
    c.rect(4, 1, 1, 11, LTL)
    for x, y in ((6, 4), (5, 5), (6, 5), (7, 5), (6, 6)):
        c.set(x, y, RED)
    for y in (2, 5, 8):
        c.set(1, y, SILV)
    c.set(9, 0, SILV)
    c.set(9, 4, SILV)
    c.set(9, 8, SILV)
    c.rect(5, 11, 2, 1, SILV)
    c.rect(0, 12, 4, 2, LTD)
    c.rect(0, 12, 1, 2, LTL)
    c.rect(8, 12, 2, 2, LTD)
    c.rect(4, 12, 4, 1, TOOTH)
    return c


def leg_side(swing, short=0):
    """Leg in profile (foot to the right). swing = foot shifted forward(+)/back(-)."""
    n = 9 - short
    rows = 14 - short
    c = C(16, rows)
    for r in range(rows):
        off = round(swing * r / (rows - 1))
        x = 6 + off
        if r < n:                                    # jeans
            c.rect(x, r, 3, 1, JNL)
            c.set(x + 3, r, JND)
            if r in (4, 5):
                c.rect(x + 1, r, 2, 1, SKM)          # torn knee
        elif r < n + 3:                              # boot shaft
            c.rect(x, r, 4, 1, BOOT)
            if r == n + 1:
                c.set(x + 3, r, SILV)                # buckle
        else:                                        # boot foot, toe forward
            c.rect(x, r, 6, 1, BOOT)
            if r == n + 3:
                c.set(x + 5, r, SILV)
    return c


def arm_hang(swing):
    """Arm hanging down in profile, swinging fore(+)/back(-). 12 wide x 15 tall,
    shoulder centre at local (5, 0)."""
    c = C(12, 15)
    for r in range(15):
        x = 4 + round(swing * r / 14)
        if r < 5:
            c.rect(x, r, 4, 1, LTD)
            c.set(x, r, LTL)
            if r == 2:
                c.set(x + 2, r, SILV)
        elif r < 10:
            c.rect(x, r, 3, 1, SKM)
            c.set(x + 2, r, SKD)
        elif r < 14:
            c.rect(x, r, 4, 1, SKM)
            c.set(x, r, SKL if r == 10 else SKM)
            c.set(x + 3, r, SKD)
        else:
            c.rect(x, r, 3, 1, SKD)
    return c


def arm_fwd(dy, horns=False, n=10):
    """Arm stretched forward (right) in profile, hand dy px higher(-)/lower(+) than the
    shoulder. 15 wide x 26 tall; the shoulder is local (2, 12)."""
    c = C(15, 26)
    yb = 12
    for x in range(n):
        y = yb + round(dy * x / (n - 1))
        if x < 4:
            c.rect(x, y, 1, 4, LTL if x < 2 else LTD)
            if x == 2:
                c.set(x, y + 1, SILV)
        else:
            c.rect(x, y, 1, 3, SKM)
            c.set(x, y, SKL)
            c.set(x, y + 2, SKD)
    ye = yb + dy
    hx = n - 1
    c.rect(hx, ye - 1, 4, 5, SKM)
    c.rect(hx, ye - 1, 4, 1, SKL)
    c.rect(hx, ye + 3, 4, 1, SKD)
    c.set(hx + 4, ye - 1, SKM)
    c.set(hx + 4, ye + 1, SKM)
    c.set(hx + 4, ye + 3, SKM)
    if horns:
        c.rect(hx, ye - 3, 1, 2, SKM)
        c.rect(hx + 3, ye - 3, 1, 2, SKM)
    return c


# ------------------------------------------------------------- views (8 facings)
# One builder per body view. Every builder takes a POSE (dx, bob, hop, ...), so the same
# drawings serve walks, dances, spawn and die.  hop = whole body jumps up; bob = knees
# bend (legs shorten, feet stay on the floor unless hop > 0).
DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
TAN = NECK                                     # guitar strap colour


def arm_spec(spec):
    """Arm drawing for the front/back/3q views: a POSES name from make_zombie4
    ('out' 'up' 'horns' 'down' 'strum0' 'strum2'), an int hy (hand height) or (hy, 'horns')."""
    if isinstance(spec, str):
        return Z.POSES[spec]()
    if isinstance(spec, tuple):
        return Z.arm(spec[0], horns=True)
    return Z.arm(spec)


def hair_flare(c, x, y, d, n, long=6):
    """Pink hair strands streaming out sideways from (x, y); d = -1 left / +1 right."""
    for k in range(n):
        for i in range(1, long + 1 - k):
            yy = y + 2 * k + (i * i) // 6
            col = HAIR_L if (k + i // 3) % 2 == 0 else HAIR_D
            c.set(x + d * i, yy, col)
            if i < 3:
                c.set(x + d * i, yy + 1, HAIR_D)


def stand_legs(c, dx, bob, hop, lift, spread, y0):
    """The standard pair of legs (front view). spread = px each leg moves outward."""
    kx = (1 if bob >= 2 else 0) + spread
    ly = GROUND - (14 - bob) - hop
    lyL = ly - (1 if lift == "L" else 0)
    lyR = ly - (1 if lift == "R" else 0)
    c.paste(Z.leg("L", bob), CX - 7 + dx - kx - (1 if lift == "L" else 0), lyL)
    c.paste(Z.leg("R", bob), CX + 1 + dx + kx + (1 if lift == "R" else 0), lyR)


def v_front(dx=0, bob=0, hop=0, tilt=0, headdy=0, armL="out", armR="out", lift=None,
            spread=0, split=0, guitar="back", hrot=0, flare=0, outline=True, gdeg=None,
            gy=0, **_):
    """Front view. dx shift, bob knee bend, hop jump height, tilt head lean, headdy head
    drop, armL/armR arm specs (see arm_spec), lift = foot raised ('L'/'R'), spread = legs
    apart, split = mid-air split angle (deg, needs hop), guitar = 'back' (slung) |
    'hold' (played) | None, hrot = head rotated by deg (negative = thrown back),
    flare = hair strands streaming out, gdeg = override guitar angle."""
    c = C(W, H)
    y0 = bob - hop
    if guitar == "back":
        put_guitar(c, -35 if gdeg is None else gdeg, (CX + 2 + dx, 33 + y0 + gy))
    if split:
        for side, sgn in (("L", 1), ("R", -1)):
            lg = Z.leg(side)
            hx = CX - 3 * sgn + dx
            paste_rot(c, lg, sgn * split, (3, 0), (hx, 35 + y0))
    else:
        stand_legs(c, dx, bob, hop, lift, spread, y0)
    c.rect(CX - 6 + dx, 34 + y0, 12, 3, JNL)                  # hips
    c.rect(CX + 2 + dx, 34 + y0, 4, 3, JND)
    c.paste(Z.torso(), CX - 6 + dx, 21 + y0)
    if guitar == "back":
        line(c, CX - 5 + dx, 22 + y0, CX + 4 + dx, 33 + y0, TAN)   # strap across the chest
        line(c, CX - 4 + dx, 22 + y0, CX + 5 + dx, 33 + y0, TAN)
    if guitar == "hold":
        line(c, CX + 5 + dx, 21 + y0, CX + 7 + dx, 31 + y0, TAN)
        line(c, CX + 4 + dx, 21 + y0, CX + 6 + dx, 31 + y0, TAN)
        # fretting arm: sleeve behind the neck, then the guitar, then the hand on top of the neck
        t = C(W, H)
        Z.put_arm(t, arm_spec(armL), "L", dx, y0)
        c.paste(t, 0, 0)
        put_guitar(c, -45 if gdeg is None else gdeg, (CX + 3 + dx, 33 + y0 + gy))
        t.g = [[v if v in (SKM, SKL, SKD) else 0 for v in row] for row in t.g]
        c.paste(t, 0, 0)
    else:
        Z.put_arm(c, arm_spec(armL), "L", dx, y0)
    Z.put_arm(c, arm_spec(armR), "R", dx, y0)
    c.rect(CX - 2 + dx, 20 + y0, 4, 1, SKD)
    hy = 8 + y0 + headdy
    if flare:
        hair_flare(c, CX - 7 + dx, hy + 3, -1, flare)
        hair_flare(c, CX + 6 + dx, hy + 3, 1, flare)
    if hrot:
        paste_rot(c, sheared(Z.head(), tilt), hrot, (9, 11), (CX + dx, 19 + y0 + headdy))
    else:
        c.paste(sheared(Z.head(), tilt), CX - 9 + dx, hy)
    if outline:
        c.outline()
    return c


def v_back(dx=0, bob=0, hop=0, tilt=0, headdy=0, armL=3, armR=3, lift=None, spread=0,
           guitar="back", flare=0, gdeg=None, **_):
    """Back view (N). armL/armR are arm specs for the screen-left/right arm."""
    c = C(W, H)
    y0 = bob - hop
    stand_legs(c, dx, bob, hop, lift, spread, y0)
    c.rect(CX - 6 + dx, 34 + y0, 12, 3, JNL)
    c.rect(CX + 2 + dx, 34 + y0, 4, 3, JND)
    c.paste(torso_back(), CX - 6 + dx, 21 + y0)
    if guitar:
        line(c, CX - 5 + dx, 33 + y0, CX + 5 + dx, 22 + y0, TAN)   # strap over the shoulder
        line(c, CX - 4 + dx, 33 + y0, CX + 4 + dx, 22 + y0, TAN)
        put_guitar(c, 35 if gdeg is None else gdeg, (CX - 2 + dx, 32 + y0), flip=True)
    Z.put_arm(c, arm_spec(armL), "L", dx, y0)
    Z.put_arm(c, arm_spec(armR), "R", dx, y0)
    c.rect(CX - 2 + dx, 20 + y0, 4, 1, SKD)
    hy = 8 + y0 + headdy
    if flare:
        hair_flare(c, CX - 7 + dx, hy + 3, -1, flare)
        hair_flare(c, CX + 6 + dx, hy + 3, 1, flare)
    c.paste(sheared(head_back(), tilt), CX - 10 + dx, hy)
    c.outline()
    return c


def v_3q(back, dx=0, bob=0, hop=0, tilt=0, headdy=0, armL=3, armR=3, lift=None, s=0,
         guitar="back", flare=0, **_):
    """3/4 views facing right: SE (back False) and NE (back True). s = leg shift."""
    c = C(W, H)
    y0 = bob - hop
    tw = 10
    tx = CX - 5 + dx
    ly = GROUND - (14 - bob) - hop
    if guitar and not back:
        put_guitar(c, -33, (CX - 4 + dx, 32 + y0), sq=.7)
    c.paste(Z.leg("L", bob), CX - 5 + dx + s - (1 if lift == "L" else 0), ly - (1 if lift == "L" else 0))
    c.paste(Z.leg("R", bob), CX + dx - s + (1 if lift == "R" else 0), ly - (1 if lift == "R" else 0))
    c.rect(tx, 34 + y0, tw, 3, JNL)
    c.rect(tx + tw - 4, 34 + y0, 4, 3, JND)
    fa, ax, sy = arm_spec(armL)
    c.paste(shade_far(fa), tx - ax + 1, 22 + y0 - sy)               # far arm, behind the body
    c.paste(torso_3q(back), tx, 21 + y0)
    if guitar and not back:
        line(c, tx + 1, 22 + y0, tx + 8, 33 + y0, TAN)
        line(c, tx + 2, 22 + y0, tx + 9, 33 + y0, TAN)
    if guitar and back:
        line(c, tx + 1, 33 + y0, tx + 8, 22 + y0, TAN)
        put_guitar(c, 32, (tx + 3, 31 + y0), flip=True, sq=.7)
    na, ax, sy = arm_spec(armR)
    na = na.flip()
    c.paste(na, tx + tw - 1 - (na.w - 1 - ax), 22 + y0 - sy)         # near arm
    c.rect(CX - 2 + dx, 20 + y0, 4, 1, SKD)
    hy = 8 + y0 + headdy
    if flare:
        hair_flare(c, CX - 7 + dx, hy + 3, -1, flare)
    c.paste(sheared(head_3q(back), tilt), CX - 9 + dx + 1, hy)
    c.outline()
    return c


def _side_arm(spec, far):
    """(canvas, shoulder offset) for a profile arm spec."""
    if spec[0] == "hang":
        a = arm_hang(spec[1])
        off = (-5, 0)
    else:
        a = arm_fwd(spec[1], horns=len(spec) > 3 and spec[3] == "horns", n=spec[2] if len(spec) > 2 else 10)
        off = (-2, -12)
    return (shade_far(a) if far else a), off


def v_side(dx=0, bob=0, hop=0, swing=0, farswing=None, lift=None, lean=1, tilt=1, headdy=0,
           hrot=0, armN=("hang", 0), armF=("hang", 0), guitar="back", gdeg=-17,
           gat=None, upper_only=False, flare=0, **_):
    """Profile facing right. swing = near foot forward(+)/back(-); far foot defaults to
    -swing. armN/armF = ('hang', swing) | ('fwd', dy[, 'horns']). gat = guitar anchor
    override (x, y) relative to (CX+dx+lean, y0). upper_only: only torso/head/arms/guitar
    (no legs, no outline) - used to build the leaning body of the knee slide."""
    fs = -swing if farswing is None else farswing
    c = C(W, H)
    y0 = bob - hop
    ly = GROUND - (14 - bob) - hop
    if not upper_only:
        c.paste(shade_far(leg_side(fs, bob)), CX - 8 + dx, ly - (1 if lift == "R" else 0))
        c.paste(leg_side(swing, bob), CX - 8 + dx, ly - (1 if lift == "L" else 0))
        c.rect(CX - 4 + lean + dx, 34 + y0, 8, 3, JNL)
        c.rect(CX + lean + dx, 34 + y0, 4, 3, JND)
    bx = CX + dx + lean
    if guitar == "back":
        put_guitar(c, gdeg, (bx - 5, 32 + y0), kind="side")
    a, off = _side_arm(armF, True)
    if guitar != "hold":
        c.paste(a, bx + 1 + off[0], 22 + y0 + off[1])
    c.paste(torso_side(), bx - 4, 21 + y0)
    if guitar == "back":
        line(c, bx - 2, 22 + y0, bx + 3, 32 + y0, TAN)
    if guitar == "hold":
        gx, gy_ = gat if gat else (4, 33)
        put_guitar(c, gdeg, (bx + gx, y0 + gy_), kind="side")
        a, off = _side_arm(armF, False)                 # fretting hand grips the neck
        c.paste(a, bx + 1 + off[0], 22 + y0 + off[1])
    a, off = _side_arm(armN, False)
    c.paste(a, bx + 1 + off[0] + (0 if armN[0] == "hang" else 0), 22 + y0 + off[1])
    c.rect(CX - 2 + lean + dx, 20 + y0, 3, 1, SKD)
    hy = 8 + y0 + headdy
    if flare:
        hair_flare(c, bx - 5, hy + 3, -1, flare)
    if hrot:
        paste_rot(c, sheared(head_side(), tilt), hrot, (3 + 5, 11), (bx + 3, 19 + y0 + headdy))
    else:
        c.paste(sheared(head_side(), tilt), CX - 8 + lean + dx, hy)
    if not upper_only:
        c.outline()
    return c


def view(direction, **pose):
    """Draw the zombie facing `direction`; W/SW/NW are mirrors of E/SE/NE."""
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
    hL, hR = 3 + round(1.6 * sn + .8 * cs), 3 - round(1.6 * sn + .8 * cs)   # arm heights (hanging, swinging)
    if d == "S":
        pose = dict(dx=round(sn), tilt=round(2 * sn + cs), bob=BOB[p], armL=hL, armR=hR, lift=lifts(p))
    elif d == "E":
        pose = dict(bob=BOB[p], lift=lifts(p), swing=round(5 * cs), tilt=round(1.5 * sn) + 1,
                    armN=("hang", -round(4 * cs)), armF=("hang", round(4 * cs)))
    elif d == "N":
        pose = dict(dx=round(sn), bob=BOB[p], lift=lifts(p), armL=hL, armR=hR, tilt=round(1.5 * sn + cs))
    else:
        pose = dict(dx=round(sn), bob=BOB[p], lift=lifts(p), s=round(2 * cs), armL=hL, armR=hR,
                    tilt=round(1.5 * sn))
    return view(direction, **pose)


# ------------------------------------------------------------------ dances
# B "Pirouette": a full 360 spin through all eight facings with a jump arc:
#    crouch, launch, tuck at the top, land. Arms go up, the pink hair whips out.
SPIN = ["S", "SE", "E", "NE", "N", "NW", "W", "SW"]
PIROUETTE = [   # (hop, bob, hair flare strands)  per frame
    (0, 2, 0), (3, 0, 1), (6, 1, 2), (8, 3, 3), (8, 3, 3), (6, 2, 3), (3, 0, 2), (0, 2, 1),
]


def dance_pirouette(f):
    d = SPIN[f]
    hop, bob, fl = PIROUETTE[f]
    up = f in (1, 2, 3, 4, 5, 6)
    if d == "S":
        return view(d, bob=bob, hop=hop, armL="up" if up else "out", armR=(-9, "h") if up else "out",
                    tilt=-1 if up else 0, flare=fl)
    if d in ("SE", "SW"):
        return view(d, bob=bob, hop=hop, armL="up", armR="up", tilt=1, flare=fl)
    if d in ("E", "W"):
        return view(d, bob=bob, hop=hop, armN=("fwd", -8) if up else ("hang", 0),
                    armF=("fwd", -6) if up else ("hang", 0), swing=1 if hop else 0, tilt=-1, flare=fl)
    if d in ("NE", "NW"):
        return view(d, bob=bob, hop=hop, armL="up", armR="up", tilt=-1, flare=fl)
    return view(d, bob=bob, hop=hop, armL="up", armR=(-9, "h"), tilt=0, flare=fl)


# C "Rock star solo": power stance -> crouch wind-up -> launch -> split jump with the head
#    thrown back -> landing -> KNEE SLIDE (leaning back, guitar neck to the sky) -> rock pose.
def fret(bob):
    """Arm height (hy) that puts the fretting hand on the guitar neck."""
    return -6 - bob


def slide_frame(hx, hy, rear_bottom, lean, gdeg, armN, armF, headrot, dust, sparks, tilt=0):
    """Knee slide in profile (facing right). (hx, hy) = hip joint, rear_bottom = lowest row of
    the kneeling shin (47 = on the ground), lean = degrees the upper body leans (negative =
    back), gdeg = guitar angle relative to the body."""
    c = C(W, H)
    upper = v_side(bob=0, hop=0, lean=0, tilt=tilt, headdy=0, hrot=headrot, armN=armN, armF=armF,
                   guitar="hold", gdeg=gdeg, gat=(4, 31), upper_only=True)
    # rear leg: thigh down to the knee, shin lying along the floor, boot toe back
    kb = rear_bottom
    c.rect(hx - 3, hy, 4, kb - 2 - hy, JNL)
    c.rect(hx, hy, 1, kb - 2 - hy, JND)
    c.rect(hx - 11, kb - 2, 12, 3, JNL)
    c.rect(hx - 11, kb, 12, 1, JND)
    c.rect(hx - 3, kb - 2, 2, 2, SKM)                      # torn knee
    c.rect(hx - 15, kb - 3, 4, 4, BOOT)
    c.set(hx - 15, kb - 3, SILV)
    c.rect(hx - 14, kb - 1, 3, 1, 0)
    c.rect(hx - 14, kb - 1, 3, 1, BOOT)
    # front leg: thigh forward, shin down, boot flat on the floor
    c.rect(hx, hy, 8, 4, JNL)
    c.rect(hx, hy + 3, 8, 1, JND)
    c.rect(hx + 5, hy + 1, 2, 2, SKM)
    c.rect(hx + 4, hy + 4, 4, 43 - hy - 3, JNL)
    c.rect(hx + 7, hy + 4, 1, 43 - hy - 3, JND)
    c.rect(hx + 4, 44, 4, 2, BOOT)
    c.set(hx + 7, 44, SILV)
    c.rect(hx + 3, 46, 8, 2, BOOT)
    c.set(hx + 10, 46, SILV)
    c.rect(hx - 4, hy - 1, 12, 3, JNL)                       # hips
    c.rect(hx + 2, hy - 1, 6, 3, JND)
    paste_rot(c, upper, lean, (CX + 1, 35), (hx + 1, hy - 2))
    if dust:
        rng = random.Random(5 + dust)
        for _ in range(dust * 3):
            c.set(max(3, hx - 15 - rng.randint(0, 3 + dust)), rng.randint(43, 47), rng.choice((DIRT_L, DIRT_M, DIRT_L)))
    for i, (sx, sy) in enumerate(((-1, -2), (1, -3), (2, -1), (-3, -2))[:sparks]):
        c.set(hx - 3 + sx * 2, 44 + sy, SILV if i % 2 else TOOTH)
    c.outline()
    return c


def dance_solo(f):
    if f == 0:     # power stance: legs wide, guitar low, head down, ready
        return v_front(bob=2, spread=3, headdy=2, tilt=-1, guitar="hold", armL=fret(2), armR="strum0")
    if f == 1:     # crouch wind-up: pick arm cocked high above the head
        return v_front(bob=3, spread=4, headdy=3, tilt=-2, dx=-1, guitar="hold", armL=fret(3),
                       armR=-9, gdeg=-48)
    if f == 2:     # launch: legs push off and spread
        return v_front(bob=0, hop=3, spread=3, headdy=0, tilt=1, guitar="hold", armL=fret(0),
                       armR=(-9, "h"), gdeg=-50)
    if f == 3:     # apex: mid-air split, head thrown back, hair streaming
        return v_front(bob=0, hop=6, split=76, hrot=-24, flare=3, tilt=0, guitar="hold", armL=-8,
                       armR=(-9, "h"), gdeg=-58, gy=-1)
    if f == 4:     # coming down, legs closing, scream
        return v_front(bob=0, hop=4, split=38, hrot=-12, flare=2, tilt=0, guitar="hold", armL=-7,
                       armR=-9, gdeg=-52)
    if f == 5:     # touchdown: front boot plants, rear knee drops
        return slide_frame(CX - 1, 36, 44, -14, 18, ("fwd", 7, 6), ("fwd", -9, 11), -10, 1, 0)
    if f == 6:     # full knee slide: leaning back, neck to the sky, sparks and dust
        return slide_frame(CX + 1, 38, 47, -36, 40, ("fwd", 7, 6), ("fwd", -9, 11), -24, 3, 3)
    # rock pose: standing again, horns up, guitar still raised, proud head
    return v_front(bob=1, spread=3, headdy=-1, tilt=2, dx=1, guitar="hold", armL=fret(1),
                   armR=(-9, "h"), gdeg=-40)


# ------------------------------------------------------- spawn (crawl out) & die (splat)
GY = 47                                    # ground line (logical row) the zombie rises from


def clip_ground(c):
    """Nothing is painted below the ground line (row 47); the outline then ends on row 48,
    so the sprite never touches the bottom border of the canvas."""
    for y in range(GY + 1, H):
        for x in range(W):
            c.g[y][x] = 0


def shifted(c, dx, dy):
    o = C(c.w, c.h)
    o.paste(c, dx, dy)
    return o


def unoutlined(c):
    o = C(c.w, c.h)
    o.g = [[0 if v == 1 else v for v in row] for row in c.g]
    return o


def mound(c, cx, rx, rng):
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


def ground_hand():
    """A rocker hand clawing up: fingers, palm, leather cuff. 7 wide x 9 tall."""
    return art([
        "m.m.m.m",
        "m.m.m.m",
        "mmmmmmm",
        "lmmmmmd",
        "lmmmmmd",
        "mddddmd",
        ".mmmmd.",
        ".kLkkk.",
        ".kLkks.",
    ])


def forearm_hand(c, x, h):
    """A hand + arm reaching up out of the ground, h rows tall (leather sleeve at the bottom)."""
    top = GY - h
    c.rect(x + 1, top + 6, 5, h - 5, SKM)
    c.rect(x + 1, top + 6, 1, h - 5, SKL)
    c.rect(x + 5, top + 6, 1, h - 5, SKD)
    if h > 8:                                    # jacket sleeve with a stud
        c.rect(x + 1, GY - 5, 5, 5, LTD)
        c.rect(x + 1, GY - 5, 1, 5, LTL)
        c.set(x + 3, GY - 3, SILV)
    hand = ground_hand()
    for j in range(6):
        for i in range(7):
            if hand.g[j][i]:
                c.set(x + i, top + j, hand.g[j][i])


def spawn_frame(f):
    rng = random.Random(100 + f)
    c = C(W, H)
    rx = (5, 8, 11, 13, 14, 13, 11, 8)[f]
    if f < 3:
        for x, h in {0: [], 1: [(13, 10)], 2: [(10, 12), (26, 9)]}[f]:
            forearm_hand(c, x, h)
    else:
        sink, pose = {
            3: (32, dict(armL=4, armR=4, guitar=None)),
            4: (21, dict(armL=4, armR=4, tilt=-1, guitar=None)),
            5: (10, dict(armL=4, armR=4, bob=1, tilt=2, guitar=None)),
            6: (3, dict(armL="out", armR="out", bob=2, tilt=2, guitar="back", gy=5)),   # guitar yanked up last
            7: (0, dict(armL="out", armR="out", bob=0, tilt=0, guitar="back")),
        }[f]
        fig = shifted(v_front(**pose), 0, sink)
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
    for _ in range((3, 5, 6, 6, 8, 10, 8, 5)[f]):           # flying / falling dirt
        c.set(rng.randint(6, 34), rng.randint(GY - 24, GY - 2) if f > 2 else rng.randint(GY - 14, GY - 2),
              rng.choice((DIRT_L, DIRT_M, DIRT_D)))
    clip_ground(c)
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


def cropped(c):
    """(sprite cropped to its pixels, x offset, y offset)."""
    ys = [y for y in range(c.h) if any(c.g[y])]
    xs = [x for x in range(c.w) if any(c.g[y][x] for y in range(c.h))]
    return c.crop(0), min(xs), min(ys)


def die_parts():
    """The zombie's own pieces: (name, sprite, centre x, centre y) in the standing pose,
    plus the resting layout (final rotation k, rest centre x, rest bottom row, hop height)."""
    g = guitar_art()
    gs = {"neck": C(g.w, 10), "mid": C(g.w, 10), "body": C(g.w, 12)}
    for r in range(10):
        gs["neck"].g[r] = list(g.g[r])
        gs["mid"].g[r] = list(g.g[10 + r])
    for r in range(12):
        gs["body"].g[r] = list(g.g[18 + r])
    for i in range(g.w):                                   # splintered, jagged breaks
        if i % 2:
            gs["mid"].g[9][i] = 0
            gs["body"].g[0][i] = 0
        if i % 3 == 0:
            gs["neck"].g[9][i] = 0
    ang = math.radians(-35)

    def gpos(r0, h):                                       # standing position of a guitar chunk
        u = 22 - (r0 + h / 2)
        return CX + 2 + u * math.sin(ang), 33 - u * math.cos(ang)
    arm, ax, ay = cropped(Z.arm(0)[0])
    legL, lx, ly = cropped(Z.leg("L"))
    legR, rx_, ry_ = cropped(Z.leg("R"))
    tors, tx, ty = cropped(Z.torso())
    head, hx, hy = cropped(Z.head())
    # (sprite, start cx, start cy, rest k, rest cx, rest bottom, hop)
    gs = {k: v.crop(0) for k, v in gs.items()}           # drop the empty margins
    parts = [      # drawn in this order: back of the pile first
        ("gbody", gs["body"], *gpos(18, 12), 0, 9, 46, 12),
        ("legL", legL, CX - 7 + legL.w / 2, 34 + legL.h / 2, 1, 21, 46, 9),
        ("gmid", gs["mid"], *gpos(10, 10), 1, 8, 35, 15),
        ("torso", tors, CX, 21 + tors.h / 2, 1, 21, 40, 13),
        ("gneck", gs["neck"], *gpos(0, 10), 2, 8, 27, 16),
        ("armL", arm, CX - 15 + ax + arm.w / 2, 22 - 14 + ay + arm.h / 2, 0, 17, 29, 14),
        ("legR", legR, CX + 1 + legR.w / 2, 34 + legR.h / 2, 3, 25, 29, 11),
        ("head", head, CX, 8 + head.h / 2, 0, 31, 46, 18),
        ("armR", arm.flip(), CX + 6 + arm.w / 2, 22 - 14 + ay + arm.h / 2, 2, 29, 34, 14),
    ]
    return parts


def die_frame(f):
    rng = random.Random(7)
    c = C(W, H)
    if f == 0:                                       # hit: white flash + recoil
        fig = view("S", dx=-1, tilt=-3, armL="up", armR="up")
        for y in range(H):
            for x in range(W):
                if fig.g[y][x] > 1:
                    fig.g[y][x] = TOOTH
        return fig
    if f in (1, 2):                                  # swelling up, cracks glowing
        fig = v_front(dx=(-1 if f == 1 else 1), tilt=(2 if f == 1 else -2), armL="strum0",
                      armR="strum0", guitar="back", outline=False)
        sx, sy_ = (1.22, 1.04) if f == 1 else (1.5, 1.08)
        big, px, py = rot(fig, 0, (20, 47), (sx, sy_))
        fig = C(W, H)
        fig.paste(big, 20 - px, 47 - py)
        fig.outline()
        for _ in range(7 * f):
            x, y = rng.randint(10, 30), rng.randint(14, 44)
            for (px_, py_) in [(x, y), (x + 1, y + 1), (x + 1, y + 2), (x + 2, y + 3)]:
                if 0 <= px_ < W and 0 <= py_ < H and fig.g[py_][px_] > 1:
                    fig.g[py_][px_] = GOO
        return fig
    t = f - 3                                         # 0..4 : burst, fly, land, settle
    u = (0.3, 0.55, 0.78, 0.94, 1.0)[t]
    # --- goo puddle on the ground (under the pieces)
    pr = (5, 9, 12, 14, 15)[t]
    for y in range(GY - 8, GY + 4):
        for x in range(W):
            d = ((x + .5 - 20) / pr) ** 2 + ((y + .5 - (GY - 1)) / (pr * .3)) ** 2
            if d <= 1:
                col = GOO_D if d > .7 else GOO
                if x < 20 and y < GY - 2 and d > .3:
                    col = GOO
                if (x * 7 + y * 3) % 17 == 0 and d < .6:
                    col = TOOTH                       # shine
                c.set(x, y, col)
    # --- flying parts, drawn from the standing layout to the resting pile
    for name, sp, x0, y0, kf, rcx, rbot, hop in die_parts():
        spin = (1, 2, 3, 1, 2, 3, 2, 1, 0)[len(name) % 9]
        k = (kf + round((1 - u) * 4 * (1 if spin % 2 else -1))) % 4 if u < 1 else kf
        spr = rot90(sp, k)
        fin = rot90(sp, kf)
        x1, y1 = rcx, rbot - fin.h / 2
        x = x0 + (x1 - x0) * u
        y = y0 + (y1 - y0) * u - hop * 4 * u * (1 - u)
        if t == 4:                                    # last frame: pieces settled (tiny drop vs. t=3)
            y = y1
        if t == 3:
            y = y1 - 1
        px = int(round(x - spr.w / 2))
        py = int(round(y - spr.h / 2))
        px = max(3, min(W - 3 - spr.w, px))
        py = max(3, min(GY - 1 - spr.h, py))
        c.paste(spr, px, py)
    # --- splinters and goo droplets
    for i in range(18):
        a = i * 2 * math.pi / 18 + .2
        sp = 4 + (i % 4) * 1.7
        life = t + 1
        x = 20 + math.cos(a) * sp * life * .9
        y = 28 + math.sin(a) * sp * life * .55 + .5 * 1.1 * life * life
        if y >= GY - 1:                              # landed: stays as a splat
            y = GY - 1 + (i % 4) - 1
            x = 20 + math.cos(a) * min(sp * 4, 17) * 1.15
        if 3 <= x < W - 4 and 3 <= y < H - 3:
            col = (GOO if i % 2 else GOO_D) if i % 3 else (GT_L if i % 2 else NECK)   # some are guitar splinters
            c.rect(int(x), int(y), 2 if i % 3 else 1, 2 if i % 2 else 1, col)
    if t >= 3:                                        # a few bones in the puddle
        for (bx, by) in ((14, GY - 1), (27, GY), (21, GY + 1))[: t - 1]:
            c.rect(bx, by, 4, 1, TOOTH)
            c.set(bx - 1, by - 1, TOOTH)
            c.set(bx + 4, by + 1, TOOTH)
    clip_ground(c)
    c.outline()
    return c


# -------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    sheets = {}
    for tag, fn in (("danceB", dance_pirouette), ("danceC", dance_solo), ("spawn", spawn_frame),
                    ("die", die_frame)):
        sheets[tag] = []
        for f in range(8):
            im = fn(f).image()
            im.save(os.path.join(OUT, f"zombie4_{tag.replace('dance', 'dance')}_{f}.png"))
            sheets[tag].append(im)
    for dname in DIRS:
        sheets[dname] = []
        for p in range(6):
            im = walk_frame(dname, p).image()
            im.save(os.path.join(OUT, f"zombie4_walk_{dname}_{p}.png"))
            sheets[dname].append(im)

    # preview at half size: 4 move rows + 8 walk rows
    hw, hh = 80, 100
    pw = 8 * (hw + 6) + 60
    keys = ["danceB", "danceC", "spawn", "die"] + DIRS
    prev = Image.new("RGBA", (pw, len(keys) * (hh + 22) + 10), (88, 92, 104, 255))
    d = ImageDraw.Draw(prev)
    for r, key in enumerate(keys):
        y = 8 + r * (hh + 22)
        d.text((6, y), key, fill=(255, 255, 255, 255))
        for i, im in enumerate(sheets[key]):
            prev.alpha_composite(im.resize((hw, hh), Image.NEAREST), (6 + i * (hw + 6), y + 12))
    prev.save(os.path.join(OUT, "zombie4_moves_preview.png"))
    print("wrote", len(os.listdir(OUT)), "files to", OUT)


if __name__ == "__main__":
    main()
