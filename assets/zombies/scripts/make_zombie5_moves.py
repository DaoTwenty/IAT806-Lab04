#!/usr/bin/env python3
"""
Zombie 5 (the BRUTE) - extra moves: 2 new dances (8 frames each), an 8-direction
stompy walk cycle (6 frames per direction), a spawn ("crawl out of the ground")
and a splat death. Full-body 160x200 sprites only (no body parts).

Run:   python3 make_zombie5_moves.py [output_dir]
Needs: make_zombie5.py in the same folder (parts, palette and canvas class are
       reused from it, so the brute is guaranteed identical), Pillow, numpy.

Output (default ./zombie5_moves/):
    zombie5_danceB_0..7.png        "Pirouette"    heavy 360 spin through all 8 facings,
                                   deep crouch -> weighty jump -> landing thud
    zombie5_danceC_0..7.png        "Ground pound" SIGNATURE: arms-up wind-up, high jump,
                                   slam into a squat with both fists on the ground,
                                   dust ring + 1 px body shake, then a flex
    zombie5_walk_<DIR>_0..5.png    DIR = N NE E SE S SW W NW, 6-frame stompy loop
    zombie5_spawn_0..7.png         crawls out of a dirt mound, last frame = neutral stand
    zombie5_die_0..7.png           white flash, swell, burst into its own parts + goo,
                                   last frame = resting pile that may stay on the ground
    zombie5_moves_preview.png      contact sheet at half size (not part of the set)
The original dance is zombie5_dance0..7.png from make_zombie5.py.

GROUND LINE (important): the original brute's feet outline sits on the very last
canvas row (49), which would touch the border. Everything here is drawn in the
brute's native coordinates (DG = 49) and then lifted by exactly 1 logical row, with
the neutral stance being bob = 1 (legs 1 row shorter, a hair of knee bend). So the
feet outline lands on row 48 - the same ground line as zombies 1-4 - and no pixel
ever touches the outer row/column.

How the 8 directions are made
  S = front view (make_zombie5 parts)       N = back view (open-backed gown, ties)
  E = side profile (new head / torso / legs / swinging arms)
  SE = 3/4 front      NE = 3/4 back         W, SW, NW = mirrors of E, SE, NE

Where to change things
  * Dances ........ dance_pirouette() / dance_pound() (one branch per frame; the
                    numbers are bob = knee bend, hop = jump height in px, sc = size
                    of the figure while airborne, lifts, arm poses)
  * Walk timing ... BOB_W, LIFT_L / LIFT_R and the swing amounts in walk_pose()
  * New body parts  head_side(), head_back(), head_3q(), torso_side(), torso_back(),
                    leg_side(), limb() (generic swinging / flexing arm)
  * Colours ....... PAL in make_zombie5.py; the extra colours (dirt, goo, dust, flash)
                    are added at runtime in the "palette additions" block below.
  * Airborne size . the `sc` values: the brute fills the canvas, so airborne frames
                    are re-sampled slightly smaller (pixel voting, no blur) to leave
                    head-room for the jump.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_zombie5 as Z                                  # noqa: E402
from make_zombie5 import C                                # noqa: E402
from PIL import Image, ImageDraw                          # noqa: E402

W, H, CX = Z.W, Z.H, Z.CX
DG = 49                    # ground row in the brute's native drawing coordinates
GR = 48                    # ground row after the 1-row lift (outline row of the feet)
GY = 47                    # last foot row on screen (what the spawn mound rises from)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "zombie5_moves")

# palette indices (same as make_zombie5.PAL)
OUTL, SKD, SKM, SKL, GWD, GWM, GWL, THR, SCAR = 1, 2, 3, 4, 5, 6, 7, 8, 9
EYE, PUPIL, TUSK, NAIL, PRINT, BAND = 10, 11, 12, 13, 14, 15

# ---- palette additions (added at runtime; dirt + goo exactly as in zombie 1) ----
DIRT_D, DIRT_M, DIRT_L, GOO, GOO_D = 16, 17, 18, 19, 20
DUST_D, DUST_M, DUST_L, FLASH = 21, 22, 23, 24
Z.PAL.update({DIRT_D: (74, 52, 40), DIRT_M: (112, 84, 60), DIRT_L: (150, 118, 84),
              GOO: (150, 230, 80), GOO_D: (70, 150, 56),
              DUST_D: (146, 138, 130), DUST_M: (196, 189, 178), DUST_L: (234, 229, 218),
              FLASH: (252, 250, 242)})

DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


# ============================================================== generic helpers
def shifted(c, dx, dy):
    o = C(c.w, c.h)
    o.paste(c, dx, dy)
    return o


def unoutlined(c):
    o = C(c.w, c.h)
    o.g = [[0 if v == 1 else v for v in row] for row in c.g]
    return o


def crop_cols(c, a, b):
    """Columns a..b (inclusive) of a canvas, as a new canvas."""
    o = C(b - a + 1, c.h)
    o.g = [row[a:b + 1] for row in c.g]
    return o


def shade_far(c):
    """Darken a canvas (limbs on the far side of the body, for depth)."""
    m = {SKL: SKM, SKM: SKD, GWL: GWM, GWM: GWD, NAIL: SKD, BAND: 9}
    o = C(c.w, c.h)
    o.g = [[m.get(v, v) for v in row] for row in c.g]
    return o


def sheared(head, tilt):
    """Head leaning by `tilt` px at the top, pivoting around the chin (20 px wide canvas)."""
    o = C(20, 13)
    for r in range(13):
        sh = round(tilt * (12 - r) / 12)
        for i in range(head.w):
            if head.g[r][i]:
                o.set(3 + sh + i, r, head.g[r][i])
    return o


def lean_shear(c, lean, pivot=31, top=2):
    """Lean the upper body: rows above `pivot` slide sideways, more the higher they are."""
    if not lean:
        return c
    o = C(c.w, c.h)
    for y in range(c.h):
        sh = round(lean * max(0, pivot - y) / (pivot - top)) if y < pivot else 0
        for x in range(c.w):
            if c.g[y][x]:
                o.set(x + sh, y, c.g[y][x])
    return o


def xform(c, sx, sy, hop, anchor=(20.0, 48.0)):
    """Re-sample an (un-outlined) figure scaled by sx/sy about the feet and lifted by
    `hop` rows. 3x3 sub-pixel voting keeps every pixel hard-edged (no blending)."""
    out = C(W, H)
    offs = (-1 / 3, 0.0, 1 / 3)
    for Y in range(H):
        for X in range(W):
            votes, order = {}, []
            for oy in offs:
                for ox in offs:
                    sxp = anchor[0] + (X + .5 + ox - anchor[0]) / sx
                    syp = anchor[1] + (Y + .5 + oy - (anchor[1] - hop)) / sy
                    ix, iy = math.floor(sxp), math.floor(syp)
                    v = c.g[iy][ix] if 0 <= ix < W and 0 <= iy < H else 0
                    votes[v] = votes.get(v, 0) + 1
                    if v not in order:
                        order.append(v)
            out.g[Y][X] = max(order, key=lambda v: (votes[v], -order.index(v)))
    return out


def lift_to_ground(c):
    """Native drawing (ground row DG) -> on-screen figure (ground row GR), un-outlined."""
    return shifted(unoutlined(c), 0, GR - DG)


def fig(c, hop=0, sc=1.0, sy=None, lean=0):
    """Finish a drawn pose: lean, lift by 1 row, optional airborne scale + hop."""
    c = lift_to_ground(lean_shear(c, lean))
    sy = sc if sy is None else sy
    if hop or sc != 1.0 or sy != 1.0:
        c = xform(c, sc, sy, hop)
    return c


def compose(figure, back=None, front=None):
    """background effects, figure, foreground effects, then the automatic 1 px outline."""
    out = C(W, H)
    if back:
        back(out)
    out.paste(figure, 0, 0)
    if front:
        front(out)
    out.outline()
    return out


# ============================================================= new body parts
def head_side():
    """Profile head looking right: bald, stitched crown, heavy brow, big nose, tusk."""
    c = C(14, 13)
    rows = {0: (3, 9), 1: (2, 10), 2: (1, 11), 3: (0, 12), 4: (0, 12), 5: (0, 12),
            6: (0, 12), 7: (0, 12), 8: (0, 12), 9: (1, 12), 10: (2, 12), 11: (3, 10), 12: (4, 9)}
    for y, (a, b) in rows.items():
        for x in range(a, b + 1):
            c.set(x, y, SKM)
    for y in range(3, 9):
        c.set(0, y, SKL)
    c.rect(3, 1, 3, 1, SKL)                 # bald shine
    c.set(2, 2, SKL)
    c.rect(4, 12, 6, 1, SKD)                # jaw shadow
    c.rect(3, 11, 1, 1, SKD)
    c.rect(10, 11, 1, 1, SKD)
    c.rect(13, 5, 1, 3, SKM)                # big nose
    c.set(13, 7, SKD)
    c.rect(11, 8, 2, 1, SKD)                # nose shadow
    c.rect(3, 5, 3, 3, SKD)                 # ear
    c.set(4, 6, SKM)
    c.rect(3, 2, 7, 1, SCAR)                # stitched crown scar (seen from the side)
    for x in (4, 6, 8):
        c.set(x, 1, THR)
        c.set(x, 3, THR)
    c.rect(8, 4, 5, 1, PUPIL)               # heavy brow
    c.rect(9, 5, 3, 2, EYE)                 # small angry eye
    c.set(11, 6, PUPIL)
    c.rect(9, 7, 3, 1, SKD)                 # eye bag
    c.rect(6, 9, 7, 1, PUPIL)               # grimace
    c.rect(7, 10, 6, 1, PUPIL)
    c.set(12, 8, TUSK)                      # upturned tusk
    c.set(12, 9, TUSK)
    c.set(9, 9, TUSK)
    c.rect(6, 7, 1, 3, SCAR)                # cheek scar with stitches
    c.set(5, 8, THR)
    c.set(7, 8, THR)
    return c


def head_back():
    """Back of the head: bald, crown scar wrapping over, vertical stitched scar, ears."""
    c = C(14, 13)
    rows = {0: (4, 9), 1: (2, 11), 2: (1, 12), 3: (0, 13), 4: (0, 13), 5: (0, 13),
            6: (0, 13), 7: (0, 13), 8: (0, 13), 9: (1, 12), 10: (1, 12), 11: (3, 10), 12: (4, 9)}
    for y, (a, b) in rows.items():
        for x in range(a, b + 1):
            c.set(x, y, SKM)
    for y in range(3, 11):
        c.set(0, y, SKL)
        c.set(13, y, SKD)
    c.rect(3, 1, 3, 1, SKL)
    c.set(2, 2, SKL)
    c.rect(0, 5, 1, 3, SKD)                 # ears peeking out
    c.rect(13, 5, 1, 3, SKD)
    c.set(0, 6, SKM)
    c.rect(4, 2, 6, 1, SCAR)                # crown scar
    for x in (5, 7, 9):
        c.set(x, 1, THR)
        c.set(x, 3, THR)
    c.rect(6, 4, 2, 7, SCAR)                # long scar down the back of the skull
    for y in (5, 7, 9):
        c.set(5, y, THR)
        c.set(8, y, THR)
    c.rect(3, 11, 8, 1, SKD)                # neck shadow
    c.rect(4, 12, 6, 1, SKD)
    c.rect(2, 11, 1, 1, SKD)
    c.rect(11, 11, 1, 1, SKD)
    return c


def head_3q(back=False):
    """3/4 head turned to the right (back=True: seen from behind, cheek peeking out)."""
    if back:
        h = head_back()
        for y in range(4, 10):
            h.set(13, y, SKM)
            h.set(12, y, SKD if y in (5, 6, 7) else SKM)
        h.set(13, 3, 0)
        return h
    c = C(14, 13)
    rows = {0: (4, 9), 1: (2, 11), 2: (1, 12), 3: (0, 13), 4: (0, 13), 5: (0, 13),
            6: (0, 13), 7: (0, 13), 8: (0, 13), 9: (1, 12), 10: (1, 12), 11: (3, 10), 12: (4, 9)}
    for y, (a, b) in rows.items():
        for x in range(a, b + 1):
            c.set(x, y, SKM)
    for y in range(3, 11):
        c.set(0, y, SKL)
        c.set(13, y, SKD)
    c.rect(3, 1, 3, 1, SKL)
    c.set(2, 2, SKL)
    c.rect(4, 12, 6, 1, SKD)
    c.rect(5, 2, 6, 1, SCAR)                # crown scar, shifted toward the facing side
    for x in (6, 8, 10):
        c.set(x, 1, THR)
        c.set(x, 3, THR)
    c.rect(1, 4, 3, 1, PUPIL)               # far brow / eye (narrow)
    c.rect(2, 5, 2, 2, EYE)
    c.set(3, 6, PUPIL)
    c.rect(1, 7, 3, 1, SKD)
    c.rect(7, 4, 5, 1, PUPIL)               # near brow / eye
    c.rect(8, 5, 3, 2, EYE)
    c.set(10, 6, PUPIL)
    c.rect(7, 7, 4, 1, SKD)
    c.rect(5, 6, 2, 2, SKD)                 # nose, toward the facing side
    c.rect(4, 9, 8, 1, PUPIL)               # grimace
    c.rect(5, 10, 6, 1, PUPIL)
    c.set(11, 8, TUSK)
    c.set(6, 9, TUSK)
    c.set(9, 9, TUSK)
    c.rect(12, 5, 1, 5, SCAR)               # cheek scar
    c.set(11, 6, THR)
    c.set(13, 6, THR)
    c.set(11, 8, THR)
    c.set(13, 8, THR)
    return c


def torso_side():
    """Gown in profile (12 wide, pot belly toward the right)."""
    c = C(12, 19)
    for y in range(17):
        a, b = (1, 9) if y < 4 else (0, 11)
        c.rect(a, y, b - a + 1, 1, GWM)
        c.set(a, y, GWL)
        if y >= 4:
            c.set(a + 1, y, GWL)
        c.rect(b - 1, y, 2, 1, GWD)
    for y, (a, b) in {0: (5, 9), 1: (6, 9), 2: (7, 9)}.items():   # open neckline
        c.rect(a, y, b - a + 1, 1, SKM)
        c.set(a - 1, y, PRINT)
    c.rect(7, 3, 3, 1, PRINT)
    for x, y in ((3, 6), (5, 11), (2, 13), (7, 15), (8, 5), (4, 9), (1, 8)):
        c.set(x, y, PRINT)
    c.rect(9, 7, 3, 6, SKM)                 # torn belly, scar on the front
    c.rect(11, 7, 1, 6, SKD)
    c.rect(10, 7, 1, 6, SCAR)
    for y in (8, 10, 12):
        c.set(9, y, THR)
    c.rect(0, 5, 1, 3, PRINT)               # gown tie at the back
    c.set(1, 6, PRINT)
    for x in (0, 1, 2, 4, 5, 7, 8, 10, 11):
        c.set(x, 17, GWL if x < 3 else (GWD if x >= 9 else GWM))
    for x in (0, 2, 5, 8, 11):
        c.set(x, 18, GWL if x < 3 else (GWD if x >= 9 else GWM))
    return c


def torso_back():
    """Hospital gown from behind: open slit down the back showing skin, ties, a patched rip."""
    c = C(16, 19)
    c.rect(0, 0, 16, 17, GWM)
    c.rect(0, 0, 3, 17, GWL)
    c.rect(12, 0, 4, 17, GWD)
    for y, (a, b) in {0: (4, 11), 1: (5, 10)}.items():     # back of the neckline
        for x in range(a, b + 1):
            c.set(x, y, SKM)
        c.set(a - 1, y, PRINT)
        c.set(b + 1, y, PRINT)
    c.rect(6, 2, 4, 1, PRINT)
    c.rect(7, 2, 2, 15, SKM)                # the open back
    c.rect(8, 2, 1, 15, SKD)
    c.rect(6, 3, 1, 14, GWL)
    c.rect(9, 3, 1, 14, GWD)
    for y in (5, 11):                       # two little ties
        c.rect(5, y, 6, 1, PRINT)
        c.set(4, y + 1, PRINT)
        c.set(11, y + 1, PRINT)
        c.set(4, y - 1, PRINT)
        c.set(11, y - 1, PRINT)
    for x, y in ((2, 5), (4, 9), (13, 4), (1, 13), (14, 8), (12, 12), (3, 15), (10, 14)):
        c.set(x, y, PRINT)
    c.rect(11, 7, 3, 3, PRINT)              # patched rip on the right shoulder blade
    c.rect(11, 7, 3, 1, GWL)
    for x, y in ((11, 7), (13, 7), (11, 9), (13, 9)):
        c.set(x, y, THR)
    for x in (0, 1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 15):
        c.set(x, 17, GWL if x < 3 else (GWD if x >= 12 else GWM))
    for x in (0, 2, 5, 8, 11, 14):
        c.set(x, 18, GWL if x < 3 else (GWD if x >= 12 else GWM))
    return c


def leg_side(swing, short=0, near=True):
    """Thick bare leg in profile, big foot pointing right. `swing` = px the foot is shifted
    forward (+) / back (-) relative to the hip (sheared leg). short = knee bend."""
    rows, n = 19 - short, 16 - short
    c = C(22, rows)
    base = 7
    for r in range(rows):
        x = base + round(swing * r / (rows - 1))
        if r < n:
            c.rect(x, r, 7, 1, SKM)
            c.rect(x, r, 2, 1, SKL)
            c.rect(x + 5, r, 2, 1, SKD)
            if near and r == 6:                       # stitched knee scar
                c.rect(x + 1, r, 5, 1, SCAR)
            if near and r in (5, 7):
                c.set(x + 2, r, THR)
                c.set(x + 4, r, THR)
        elif r == n:                                   # foot, top row
            c.rect(x - 1, r, 10, 1, SKL)
        elif r == n + 1:
            c.rect(x - 1, r, 11, 1, SKM)
            c.set(x + 9, r, NAIL)
        else:                                          # sole
            c.rect(x - 1, r, 11, 1, SKD)
            c.set(x + 3, r, NAIL)
            c.set(x + 6, r, NAIL)
    return c


def arm_front(hy=0):
    """Same drawing as make_zombie5.arm(), but the canvas grows with hy (fists can reach the
    ground in a squat). Returns (canvas, ax, sy) like make_zombie5.arm()."""
    sy = 14
    ht = sy - 1 + hy
    c = C(11, max(sy + 6, ht + 8))
    y0, y1 = min(sy + 1, ht + 2), max(sy + 3, ht + 5)
    c.rect(5, y0, 3, y1 - y0 + 1, 3)
    c.rect(5, y0, 3, 1, 4)
    c.rect(5, y1, 3, 1, 2)
    c.rect(1, ht, 5, 7, 3)
    c.rect(1, ht, 1, 7, 4)
    c.rect(5, ht, 1, 7, 2)
    c.rect(1, ht + 6, 5, 1, 2)
    for k in (1, 3, 5):
        c.set(0, ht + k, 3)
    c.rect(2, ht - 1, 2, 1, 3)
    c.rect(6, ht + 1, 1, 5, BAND)
    c.rect(7, sy, 4, 5, GWM)
    c.rect(7, sy, 4, 1, GWL)
    c.rect(10, sy, 1, 5, GWD)
    c.rect(7, sy + 1, 1, 3, PRINT)
    c.set(7, sy + 4, 0)
    return c, 10, sy


def limb(pts, T_slv=5, T=4):
    """Generic gown-sleeved arm: a polyline of offsets from the shoulder, e.g. a hanging arm
    [(0,0),(hx,hy)] or a flex [(0,0),(-7,0),(-8,-8)]. Skin brush + sleeve + big fist with a
    wristband, edge-shaded (light top/left, dark bottom/right). Drawn on a 56x64 canvas with
    the shoulder at (28,32). Returns (canvas, shoulder_x, shoulder_y)."""
    ox, oy = 28, 32
    skin, slv, band, trim = set(), set(), set(), set()

    def brush(x, y, t, tgt):
        cx, cy = round(x) - t // 2, round(y) - t // 2
        for j in range(t):
            for i in range(t):
                tgt.add((cx + i, cy + j))

    def cross(x, y, ux, uy, t, tgt):
        """1 px thick line across the limb (perpendicular to its direction)."""
        for k in range(-t, t + 1):
            tgt.add((round(x - uy * k * .5), round(y + ux * k * .5)))

    segs = list(zip(pts, pts[1:]))
    total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs)
    dist = 0.0
    for a, b in segs:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        n = max(1, int(L * 6))
        for i in range(n + 1):
            t = i / n
            x, y = ox + a[0] + (b[0] - a[0]) * t, oy + a[1] + (b[1] - a[1]) * t
            d = dist + L * t
            if d < 2.2:
                brush(x, y, T_slv, slv)
            else:
                brush(x, y, T, skin)
            if abs(d - 1.6) < .17:
                cross(x, y, ux, uy, T_slv, trim)
            if abs(d - (total - 3.4)) < .17:
                cross(x, y, ux, uy, T, band)
        dist += L
    ex, ey = ox + pts[-1][0], oy + pts[-1][1]
    fist = {(round(ex) - 2 + i, round(ey) - 2 + j) for i in range(5) for j in range(6)}
    allm = skin | slv | fist
    c = C(56, 64)
    skin -= slv
    for (x, y) in skin | fist:
        col = SKM
        if (x + 1, y) not in allm or (x, y + 1) not in allm:
            col = SKD
        if (x, y - 1) not in allm or (x - 1, y) not in allm:
            col = SKL
        c.set(x, y, col)
    for (x, y) in slv:                      # sleeve: dark rim (so it reads against the gown)
        col = GWM
        if (x - 1, y) not in allm or (x + 1, y) not in allm or (x, y + 1) not in allm:
            col = GWD
        elif (x, y - 1) not in allm:
            col = GWL
        c.set(x, y, col)
    for (x, y) in trim & slv:
        c.set(x, y, PRINT)
    for (x, y) in band & (skin | slv):
        c.set(x, y, BAND)
    fx, fy = round(ex) - 2, round(ey) - 2
    c.rect(fx + 1, fy + 2, 3, 1, SKD)       # finger line
    c.set(fx + 2, fy, SKL)
    return c, ox, oy


def paste_limb(c, arm, side, sx, sy):
    """Paste a limb() arm so its shoulder lands on (sx, sy). side 'R' mirrors it."""
    a, ox, oy = arm
    if side == "R":
        a, ox = a.flip(), a.w - 1 - ox
    c.paste(a, sx - ox, sy - oy)


def arm_flex():
    """Bodybuilder flex for the screen-left arm: upper arm out, forearm up, fist above."""
    return limb([(0, 0), (-5, 1), (-6, -6)], T_slv=5, T=5)


def put_front_arm(c, drawn, side, dx, bob, edge=1):
    """Like make_zombie5.put_arm. `drawn` = (canvas, ax, sy)."""
    a, ax, sy = drawn
    oy = 15 + bob - sy
    if side == "L":
        c.paste(a, CX - 8 + dx - ax + edge, oy)
    else:
        a = a.flip()
        c.paste(a, CX + 7 + dx - (a.w - 1 - ax) - edge, oy)


def front_arm(h, side):
    """h = int hand offset (arm_front) or 'flex'."""
    if h == "flex":
        a, ox, oy = arm_flex()
        return a, ox + 2, oy - 2          # (canvas, edge col, sleeve top row)
    return arm_front(h)


# ===================================================== the 8 facings (one drawing each)
# Every view builder returns an UN-OUTLINED drawing in native coordinates (ground DG), taking
# the same kind of pose: dx (sideways shift), bob (knee bend, >= 1), tilt (head lean),
# lift L/R (px a foot is raised), arm hand-offsets. fig() then lifts / scales / hops it.
def v_front(back=False, dx=0, bob=1, tilt=0, liftL=0, liftR=0, hyL=0, hyR=0, spread=0, **_):
    c = C(W, H)
    for side, lift, x in (("L", liftL, 11 + dx - spread), ("R", liftR, 21 + dx + spread)):
        lg = Z.leg(side, bob)
        c.paste(lg, x, DG - lg.h - lift)
    c.rect(CX - 8 + dx, 30 + bob, 16, 3, SKM)
    c.rect(CX + 4 + dx, 30 + bob, 4, 3, SKD)
    c.paste(torso_back() if back else Z.torso(), CX - 8 + dx, 13 + bob)
    put_front_arm(c, front_arm(hyL, "L"), "L", dx, bob)
    put_front_arm(c, front_arm(hyR, "R"), "R", dx, bob)
    hd = head_back() if back else Z.head()
    c.paste(sheared(hd, tilt), CX - 10 + dx, 2 + bob)
    return c


def v_3q(back, dx=0, bob=1, tilt=0, liftL=0, liftR=0, s=0, hyL=3, hyR=3, **_):
    """SE (back False) and NE (back True): facing right, 3/4 view. s = leg stride shift."""
    c = C(W, H)
    for side, lift, x in (("L", liftL, CX - 8 + dx + s), ("R", liftR, CX - 1 + dx - s)):
        lg = Z.leg(side, bob)
        c.paste(lg, x, DG - lg.h - lift)
    tor = torso_back() if back else Z.torso()
    tor = crop_cols(tor, 3, 15) if back else crop_cols(tor, 0, 12)
    if not back:                           # re-shade the cut-off right side of the gown
        for y in range(17):
            for x in (10, 11, 12):
                if tor.g[y][x] in (GWM, GWL):
                    tor.g[y][x] = GWD
    tx = CX - 6 + dx
    c.rect(tx, 30 + bob, 13, 3, SKM)
    c.rect(tx + 9, 30 + bob, 4, 3, SKD)
    far = front_arm(hyL, "L")
    c.paste(far[0], tx + 2 - far[1], 15 + bob - far[2])       # far arm: behind the body
    c.paste(tor, tx, 13 + bob)
    near = front_arm(hyR, "R")
    a = near[0].flip()
    c.paste(a, tx + 11, 15 + bob - near[2])
    hd = head_3q(back)
    c.paste(sheared(hd, tilt), CX - 9 + dx, 2 + bob)
    return c


def v_side(dx=0, bob=1, tilt=1, lean=1, swing=0, farswing=None, liftN=0, liftF=0,
           armN=(6, 11), armF=(-6, 11), **_):
    """Profile facing right. swing = near foot forward(+)/back(-); far foot defaults to -swing.
    armN/armF = hand offset (right, down) from the shoulder."""
    fs = -swing if farswing is None else farswing
    c = C(W, H)
    tx = CX - 6 + lean + dx
    lgF = leg_side(fs, bob, near=False)
    lgN = leg_side(swing, bob, near=True)
    c.paste(shade_far(lgF), tx - 5, DG - lgF.h - liftF)
    c.paste(lgN, tx - 5, DG - lgN.h - liftN)
    c.rect(tx, 30 + bob, 12, 3, SKM)
    c.rect(tx + 8, 30 + bob, 4, 3, SKD)
    sx, sy = tx + 5, 17 + bob
    far = limb([(0, 0), armF])
    paste_limb(c, (shade_far(far[0]), far[1], far[2]), "L", sx, sy)
    c.paste(torso_side(), tx, 13 + bob)
    paste_limb(c, limb([(0, 0), armN]), "L", sx, sy)
    c.paste(sheared(head_side(), tilt), CX - 10 + lean + dx, 2 + bob)
    return c


def view(direction, **pose):
    """Draw the brute facing `direction` (un-outlined, native coordinates).
    W / SW / NW are mirrors of E / SE / NE."""
    flip = direction in ("SW", "W", "NW")
    d = {"SW": "SE", "W": "E", "NW": "NE"}.get(direction, direction)
    if d == "S":
        c = v_front(False, **pose)
    elif d == "N":
        c = v_front(True, **pose)
    elif d == "E":
        c = v_side(**pose)
    elif d == "SE":
        c = v_3q(False, **pose)
    else:
        c = v_3q(True, **pose)
    return c.flip() if flip else c


def arms(direction, name):
    """Named arm poses for any facing -> keyword arguments for view()."""
    d = {"SW": "SE", "W": "E", "NW": "NE"}.get(direction, direction)
    if d == "E":
        t = {"out": ((11, -1), (-11, -1)), "up": ((3, -13), (-2, -13)),
             "mid": ((9, -7), (-9, -7)), "down": ((2, 14), (-2, 14)), "low": ((2, 14), (-2, 14)),
             "over": ((3, -15), (-2, -15))}[name]
        return dict(armN=t[0], armF=t[1])
    h = {"out": 0, "up": -6, "mid": -3, "down": 4, "low": 9, "over": -10, "flex": "flex"}[name]
    return dict(hyL=h, hyR=h)


# ======================================================================== walks
BOB_W = [3, 2, 1, 3, 2, 1]                      # body lowest at each heavy foot-fall (p0, p3)
LIFT_L = [0, 0, 0, 0, 3, 4]                     # left foot stomps up at p4-p5, lands p0
LIFT_R = [0, 3, 4, 0, 0, 0]                     # right foot up at p1-p2, lands p3


def walk_pose(direction, p):
    a = 2 * math.pi * p / 6
    cs, sn = math.cos(a), math.sin(a)
    d = {"SW": "SE", "W": "E", "NW": "NE"}.get(direction, direction)
    if d == "E":
        hx = round(7 * cs)
        hy = lambda k: round(math.sqrt(max(1, 12 ** 2 - k ** 2)))   # constant arm length
        return dict(bob=BOB_W[p], swing=round(4 * cs), liftN=LIFT_L[p], liftF=LIFT_R[p],
                    armN=(-hx, hy(hx)), armF=(hx, hy(hx)), tilt=round(1.5 * sn) + 1, lean=1)
    dx = (-1 if LIFT_R[p] else (1 if LIFT_L[p] else 0))
    pose = dict(dx=dx, bob=BOB_W[p], liftL=LIFT_L[p], liftR=LIFT_R[p], tilt=round(1.5 * sn),
                hyL=3 + round(2 * math.sin(a + .5)), hyR=3 - round(2 * math.sin(a + .5)))
    if d in ("SE", "NE"):
        pose["s"] = round(2 * cs)
    return pose


def walk_frame(direction, p):
    return compose(fig(view(direction, **walk_pose(direction, p))))


# ======================================================================== dust

def cloud(c, cx, cy, r, fade=0):
    """Hard-edged lumpy dust cloud: three overlapping discs, rim-shaded (light top-left,
    dark bottom-right). Stays 2 px inside the canvas border and above the ground line."""
    cells = set()
    for ccx, ccy, rr in ((cx, cy, r), (cx + r * .95, cy + r * .25, r * .7), (cx - r * .85, cy + r * .35, r * .62)):
        for y in range(int(ccy - rr - 1), int(ccy + rr + 2)):
            for x in range(int(ccx - rr - 1), int(ccx + rr + 2)):
                if (x + .5 - ccx) ** 2 + (y + .5 - ccy) ** 2 <= rr * rr and 2 <= x <= W - 3 and 2 <= y <= GY:
                    cells.add((x, y))
    for (x, y) in cells:
        col = DUST_L                        # puffy: light inside, grey rim on the lower right
        if (x + 1, y) not in cells or (x, y + 1) not in cells:
            col = DUST_M
        if (x + 1, y) not in cells and (x, y + 1) not in cells:
            col = DUST_D
        if fade and col == DUST_L and (x - 1, y) in cells and (x, y - 1) in cells and (x + x // 2 + y) % 3 == 0:
            col = DUST_M                    # fading cloud: broken up with grey flecks
        c.set(x, y, col)


def debris(c, pts):
    """Little flying clods of dirt (2x2 / 1x1)."""
    for i, (x, y) in enumerate(pts):
        if 2 <= x <= W - 4 and 2 <= y <= GY - 1:
            c.rect(x, y, 2 if i % 2 == 0 else 1, 2 if i % 3 else 1, (DIRT_L, DIRT_M, DIRT_D)[i % 3])


def dust_back(c, t):
    spec = {0: [(6, 43, 4), (33, 43, 4), (14, 44, 3), (26, 44, 3)],
            1: [(5, 38, 4), (34, 38, 4), (4, 44, 3), (35, 44, 3), (11, 43, 3), (28, 43, 3)],
            2: [(4, 35, 2), (35, 35, 2), (4, 42, 3), (35, 42, 3)]}[t]
    for cx, cy, r in spec:
        cloud(c, cx, cy, r, 1 if t == 2 else 0)
    if t == 0:
        debris(c, [(3, 37), (35, 36), (2, 41), (36, 40), (9, 39)])
    if t == 1:
        debris(c, [(3, 33), (35, 32), (2, 38), (36, 37)])


def dust_front(c, t):
    spec = {0: [(11, 46, 2), (28, 46, 2), (20, 46, 2), (5, 46, 2), (34, 46, 2)],
            1: [(8, 46, 3), (31, 46, 3), (16, 47, 2), (23, 47, 2)],
            2: [(7, 46, 2), (32, 46, 2)]}[t]
    for cx, cy, r in spec:
        cloud(c, cx, cy, r, 1 if t == 2 else 0)


def thud_dust(c, big=False):
    """Small landing puffs at both feet."""
    r = 3 if big else 2
    for cx in (7, 32):
        cloud(c, cx, 46, r)
    if big:
        cloud(c, 12, 47, 2)
        cloud(c, 27, 47, 2)


# ====================================================================== dances
# B  "Pirouette": heavy 360 through all 8 facings. Crouch (f0) -> launch (f1-2) -> hang
#    (f3-4) -> descend (f5-6) -> land with a thud (f7), which flows back into the crouch.
SPIN = ["S", "SE", "E", "NE", "N", "NW", "W", "SW"]
PIR = [   # bob = knee bend, lift = px both feet tuck up, hop = px off the ground, sc = size, a = arms
    dict(bob=6, lift=0, hop=0, sc=1.0, a="low"),
    dict(bob=3, lift=2, hop=3, sc=.92, a="out"),
    dict(bob=3, lift=3, hop=6, sc=.86, a="out"),
    dict(bob=4, lift=3, hop=8, sc=.82, a="out"),
    dict(bob=4, lift=3, hop=8, sc=.82, a="up"),
    dict(bob=3, lift=3, hop=6, sc=.86, a="out"),
    dict(bob=3, lift=2, hop=3, sc=.92, a="out"),
    dict(bob=4, lift=0, hop=0, sc=1.0, a="mid"),
]


def dance_pirouette(f):
    d, k = SPIN[f], PIR[f]
    pose = dict(bob=k["bob"], tilt=0 if d not in ("E", "W") else 1, **arms(d, k["a"]))
    if d == "E" or d == "W":
        pose.update(liftN=k["lift"], liftF=k["lift"], swing=1 if k["lift"] else 0)
    else:
        pose.update(liftL=k["lift"], liftR=k["lift"])
        if f in (0, 7):
            pose["spread"] = 2 if f == 0 else 1
    fg = fig(view(d, **pose), hop=k["hop"], sc=k["sc"])
    if f == 7:
        return compose(fg, front=lambda c: thud_dust(c, True))
    if f == 0:
        return compose(fg, front=lambda c: thud_dust(c, False))
    return compose(fg)


# C  "Ground pound": see dance_pound(). Frame list:
#   0 wind-up: arms overhead, leaning back     1 coil: deep crouch, arms still up
#   2 launch                                   3 apex: tucked, fists raised
#   4 SLAM: deep squat, fists on the ground, dust ring, body shakes left
#   5 hold: shakes right, bigger dust          6 rise, dust drifts off     7 flex pose
def dance_pound(f):
    if f == 0:
        return compose(fig(view("S", dx=1, bob=1, tilt=-3, **arms("S", "over")), lean=-2))
    if f == 1:
        return compose(fig(view("S", dx=1, bob=5, tilt=-2, spread=1, **arms("S", "over")), lean=-2))
    if f == 2:
        return compose(fig(view("S", bob=3, tilt=0, liftL=2, liftR=2, **arms("S", "over")),
                           hop=5, sc=.88))
    if f == 3:
        return compose(fig(view("S", bob=4, tilt=2, liftL=3, liftR=3, hyL=-9, hyR=-9),
                           hop=9, sc=.8))
    if f in (4, 5):
        bob = 10
        hy = 28 - bob                                  # fists land exactly on the ground
        dx = -1 if f == 4 else 1
        c = view("S", dx=dx, bob=bob, tilt=0, spread=2, hyL=hy, hyR=hy)
        t = 0 if f == 4 else 1
        return compose(fig(c), back=lambda o: dust_back(o, t), front=lambda o: dust_front(o, t))
    if f == 6:
        c = view("S", dx=0, bob=5, tilt=-1, spread=1, hyL=10, hyR=10)
        return compose(fig(c), back=lambda o: dust_back(o, 2), front=lambda o: dust_front(o, 2))
    return compose(fig(view("S", bob=1, tilt=0, **arms("S", "flex"))))


# ========================================================== spawn (crawl out) & die
def mound(c, cx, rx, rng):
    """Pile of dirt at the ground line (rows above GY plus a flat base). rx = half width."""
    ry = max(2, round(rx * .42))
    for y in range(GY - ry - 1, GY + 1):
        for x in range(cx - rx - 1, cx + rx + 2):
            d = ((x + .5 - cx) / rx) ** 2 + ((y + .5 - GY) / ry) ** 2
            if d <= 1 and 2 <= x <= W - 3:
                col = DIRT_M
                if d > .62 and y > GY - 2:
                    col = DIRT_D
                elif d > .5 and y < GY - 1 and x < cx:
                    col = DIRT_L
                if d < .28:
                    col = DIRT_D                  # the dark hole in the middle
                c.set(x, y, col)
    for _ in range(rx):                           # loose clods
        x, y = cx + rng.randint(-rx - 2, rx + 2), GY + rng.randint(-ry - 2, 0)
        if 2 <= x <= W - 3:
            c.set(x, y, rng.choice((DIRT_L, DIRT_M, DIRT_D)))


def forearm_hand(c, x, h):
    """A hand + forearm reaching out of the ground, h rows tall (x = left edge)."""
    top = GY - h
    c.rect(x + 1, top + 8, 5, h - 7, SKM)
    c.rect(x + 1, top + 8, 1, h - 7, SKL)
    c.rect(x + 5, top + 8, 1, h - 7, SKD)
    c.rect(x + 1, top + 9, 5, 1, BAND)
    hand = Z.stitched_hand()
    for j in range(8):
        for i in range(8):
            if hand.g[j][i]:
                c.set(x + i, top + j, hand.g[j][i])


def spawn_frame(f):
    rng = random.Random(500 + f)
    c = C(W, H)
    rx = (6, 10, 13, 15, 16, 16, 14, 11)[f]
    if f < 3:
        for x, h in {0: [], 1: [(16, 12)], 2: [(8, 14), (26, 12)]}[f]:
            forearm_hand(c, x, h)
    else:
        sink, pose = {
            3: (33, dict(bob=1, hyL=4, hyR=4)),
            4: (24, dict(bob=1, hyL=4, hyR=4, tilt=-1)),
            5: (14, dict(bob=2, hyL=4, hyR=4, tilt=2)),
            6: (6, dict(bob=3, hyL=1, hyR=1, tilt=2)),
            7: (0, dict(bob=1, hyL=0, hyR=0)),
        }[f]
        figc = shifted(fig(view("S", **pose)), 0, sink)
        if f < 7:
            for y in range(GY - 1, H):            # everything below the ground is hidden
                for x in range(W):
                    figc.g[y][x] = 0
        if f in (3, 4):
            for x in (6, 27):
                forearm_hand(c, x, 9)
        if f >= 7:
            mound(c, 20, rx, rng)             # last frame: the mound stays behind the feet
        c.paste(figc, 0, 0)
    if f < 7:
        mound(c, 20, rx, rng)
    for _ in range((3, 5, 7, 8, 10, 12, 9, 6)[f]):         # flying / falling dirt specks
        x = rng.randint(4, 35)
        y = rng.randint(GY - 26, GY - 2) if f > 2 else rng.randint(GY - 16, GY - 2)
        if not c.g[y][x] and 2 <= x <= W - 3 and y >= 2:
            c.set(x, y, rng.choice((DIRT_L, DIRT_M, DIRT_D)))
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


def goo_cracks(figc, rng, n):
    """Glowing green cracks painted onto an (un-outlined) figure."""
    for _ in range(n):
        for _try in range(30):
            x, y = rng.randint(8, 31), rng.randint(8, 44)
            if figc.g[y][x] and figc.g[y + 3][min(x + 2, W - 1)]:
                break
        for (px, py) in ((x, y), (x + 1, y + 1), (x + 1, y + 2), (x + 2, y + 3)):
            if 0 <= px < W and 0 <= py < H and figc.g[py][px]:
                figc.g[py][px] = GOO


# resting pile: sprite, rotation, x, y of the landed part (screen coordinates)
def part_sprites():
    arm = Z.arm(0)[0].crop(0)
    return {
        "head": Z.head(),
        "torso": Z.torso(),
        "armL": arm,
        "armR": arm.flip(),
        "legL": Z.leg("L"),
        "legR": Z.leg("R"),
    }


# Hand-placed keyframes for the burst, one (x, y, quarter-turns k) per frame f3..f7:
#   f3 parts just blown apart   f4 flying and tumbling   f5 falling
#   f6 landed (small bounce)    f7 resting pile
KF = {
    "legL":  [(7, 29, 0), (2, 36, 1), (1, 38, 1), (2, 38, 1), (2, 40, 1)],
    "legR":  [(25, 29, 0), (19, 37, 3), (20, 39, 3), (19, 39, 3), (19, 40, 3)],
    "torso": [(12, 17, 0), (11, 21, 0), (7, 27, 1), (6, 29, 1), (6, 31, 1)],
    "head":  [(13, 2, 0), (14, 3, 1), (21, 20, 2), (22, 33, 0), (22, 35, 0)],
    "armL":  [(2, 12, 0), (2, 9, 1), (3, 24, 2), (4, 29, 2), (4, 30, 2)],
    "armR":  [(27, 12, 0), (30, 9, 3), (26, 20, 0), (24, 28, 0), (24, 29, 0)],
}


def die_frame(f):
    rng = random.Random(7)
    c = C(W, H)
    if f == 0:                                         # hit: white flash + recoil
        figc = fig(view("S", dx=-1, tilt=-3, bob=1, **arms("S", "up")))
        for y in range(H):
            for x in range(W):
                if figc.g[y][x]:
                    figc.g[y][x] = FLASH
        return compose(figc)
    if f in (1, 2):                                    # swelling up, glowing cracks
        figc = fig(view("S", dx=(-1 if f == 1 else 1), bob=1, tilt=(2 if f == 1 else -2),
                        **arms("S", "down")),
                   sc=(.86 if f == 1 else 1.0), sy=(.9 if f == 1 else .86))
        goo_cracks(figc, rng, 3 * f + 2)
        return compose(figc)
    t = f - 3                                          # 0..4 : burst, fly, fall, land, rest
    spr = part_sprites()
    for name in ("legL", "legR", "torso", "head", "armL", "armR"):
        x, y, k = KF[name][t]
        r = rot90(unoutlined(spr[name]), k)
        c.paste(r, max(2, min(W - 2 - r.w, x)), max(2, min(GY + 1 - r.h, y)))
    # --- goo: puddle on the ground + flying droplets
    pr = (0, 0, 0, 7, 10, 13, 15, 16)[f]
    if pr:
        for y in range(GY - 8, GY + 1):
            for x in range(2, W - 2):
                d = ((x + .5 - 20) / pr) ** 2 + ((y + .5 - GY) / (pr * .34)) ** 2
                if d <= 1:
                    col = GOO_D if d > .7 else GOO
                    if x < 20 and y < GY - 2 and d > .3:
                        col = GOO
                    if (x * 7 + y * 3) % 17 == 0 and d < .6:
                        col = TUSK
                    if not c.g[y][x] or f >= 6 and d > .55:
                        c.set(x, y, col)
    life = t + 1
    for i in range(20):
        a = i * 2 * math.pi / 20 + .2
        sp = 4 + (i % 4) * 1.7
        x = 20 + math.cos(a) * sp * life * .9
        y = 26 + math.sin(a) * sp * life * .55 + .5 * 1.1 * life * life
        if y >= GY - 1:                                # landed: stays as a splat
            y = GY - 1 + (i % 2)
            x = 20 + math.cos(a) * min(sp * 4, 17) * 1.15
        x, y = int(x), int(y)
        if 3 <= x < W - 4 and 3 <= y < GY and (t < 2 or not c.g[y][x] or y > GY - 4):
            c.rect(x, y, 2 if i % 3 else 1, 2 if i % 2 else 1, GOO if i % 2 else GOO_D)
    if f >= 5:                                         # a few bones in the puddle
        for (bx, by) in ((6, GY - 1), (30, GY), (16, GY)):
            c.rect(bx, by, 5, 1, TUSK)
            c.set(bx - 1, by - 1, TUSK)
            c.set(bx + 5, by + 1 if by < GY else by, TUSK)
    for y in range(GY + 1, H):                         # nothing below the ground line
        for x in range(W):
            c.g[y][x] = 0
    c.outline()
    return c


# ========================================================================= main
def main():
    os.makedirs(OUT, exist_ok=True)
    sheets = {}
    for name, fn in (("danceB", dance_pirouette), ("danceC", dance_pound),
                     ("spawn", spawn_frame), ("die", die_frame)):
        sheets[name] = []
        for f in range(8):
            im = fn(f).image()
            im.save(os.path.join(OUT, f"zombie5_{name}_{f}.png"))
            sheets[name].append(im)
    for dname in DIRS:
        sheets[dname] = []
        for p in range(6):
            im = walk_frame(dname, p).image()
            im.save(os.path.join(OUT, f"zombie5_walk_{dname}_{p}.png"))
            sheets[dname].append(im)

    hw, hh = 80, 100
    keys = ["danceB", "danceC", "spawn", "die"] + DIRS
    prev = Image.new("RGBA", (8 * (hw + 6) + 12, len(keys) * (hh + 22) + 10), (88, 92, 104, 255))
    d = ImageDraw.Draw(prev)
    for r, key in enumerate(keys):
        y = 8 + r * (hh + 22)
        d.text((6, y), key, fill=(255, 255, 255, 255))
        for i, im in enumerate(sheets[key]):
            prev.alpha_composite(im.resize((hw, hh), Image.NEAREST), (6 + i * (hw + 6), y + 12))
    prev.save(os.path.join(OUT, "zombie5_moves_preview.png"))
    print("wrote", len(os.listdir(OUT)), "files to", OUT)


if __name__ == "__main__":
    main()
