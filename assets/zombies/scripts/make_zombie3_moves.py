#!/usr/bin/env python3
"""
Zombie 3 (cheerleader) - extra moves: 2 new dances, 8-direction walk cycle,
spawn (crawl out of the ground) and die (splat). Full-body 160x200 sprites only.

Run:   python3 make_zombie3_moves.py [output_dir]
Needs: make_zombie3.py in the same folder (parts, palette and canvas class are
       reused from it, so the cheerleader is guaranteed identical), Pillow, numpy.

Output (default ./zombie3_moves/):
    zombie3_danceB_0..7.png        "Pirouette"  - 360 degree spin through all 8 facings with a
                                   jump arc (crouch, launch, tuck, land), poms up, skirt flaring
    zombie3_danceC_0..7.png        "Cartwheel + toe-touch" (signature) - crouch, a sideways
                                   cartwheel (pixel-sampled in-plane rotation, star pose with
                                   poms out), landing, toe-touch jump (split legs, poms up), pose
    zombie3_walk_<DIR>_0..5.png    DIR = N NE E SE S SW W NW, 6-frame loop, poms pumping
    zombie3_spawn_0..7.png         crawls out of a dirt mound (hand, two hands, head, ... stands)
    zombie3_die_0..7.png           splat: flash, swell + goo cracks, burst into her real parts
                                   (head+ponytail, torso, arms, legs, poms), goo puddle + bones
    zombie3_moves_preview.png      contact sheet at half size (not part of the set)
The original dance is zombie3_dance0..7.png from make_zombie3.py.

How the 8 directions are made
  S  = the front view of make_zombie3.py     N  = back view (hair mass + ponytail on the back)
  E  = profile (head_side / torso_side / leg_side / arm_side)
  SE = 3/4 front view, NE = 3/4 back view (head_3q / torso crop)
  W, SW, NW = the E, SE, NE frames mirrored.
  The ponytail hangs at the back of the head in every view (in the front view it is the
  original side ponytail).

Where to change things
  * Dances ....... dance_pirouette(), dance_cartwheel()  (pose parameters per frame)
  * Walk timing .. BOB, lifts(), and the sin/cos lines in walk_frame()
  * Body parts ... head_side(), head_back(), head_3q(), torso_side(), torso_back(), leg_side(),
                   arm_side(), diag_leg()     (front parts come from make_zombie3.py)
  * Poses ........ v_front(), v_34(), v_side()  keyword arguments:
                   dx (shift) bob (knee bend) hop (jump height) tilt (head lean)
                   hyL/hyR or dyN/dyF (arm heights, negative = up) lift swing flare (skirt)
  * Colours ...... PAL in make_zombie3.py; extra dirt / goo colours (indices 16-20) below
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_zombie3 as Z                                  # noqa: E402
from make_zombie3 import C                                # noqa: E402
from PIL import Image, ImageDraw                          # noqa: E402

W, H, CX, GROUND = Z.W, Z.H, Z.CX, Z.GROUND
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "zombie3_moves")

# palette indices (same as make_zombie3.PAL)
OUTL, SKD, SKM, SKL, RED_D, RED_L, WH_D, WH = 1, 2, 3, 4, 5, 6, 7, 8
EYE, PUPIL, HAIR_L, HAIR_D, TONG, GOLD, GOLD_D = 9, 10, 11, 12, 13, 14, 15
# extra palette entries for spawn (dirt) and die (goo) - same indices as zombie 1
DIRT_D, DIRT_M, DIRT_L, GOO, GOO_D = 16, 17, 18, 19, 20
Z.PAL.update({DIRT_D: (74, 52, 40), DIRT_M: (112, 84, 60), DIRT_L: (150, 118, 84),
              GOO: (150, 230, 80), GOO_D: (70, 150, 56)})
GY = 47                                    # ground line (logical row) for spawn / die


# --------------------------------------------------------------- small helpers
def sheared(head, tilt, ox=3, chin=11):
    """Head leaning by `tilt` px at the top, pivoting around the chin row. The
    returned canvas is `ox` px wider on each side (paste at body_left - body_x0 - ox)."""
    o = C(head.w + 2 * ox, head.h)
    for r in range(head.h):
        sh = round(tilt * max(0, chin - r) / chin)
        for i in range(head.w):
            if head.g[r][i]:
                o.set(ox + sh + i, r, head.g[r][i])
    return o


def shade_far(c):
    """Darken a canvas (limbs on the far side of the body, for depth)."""
    m = {SKM: SKD, SKL: SKM, RED_L: RED_D, WH: WH_D, GOLD: GOLD_D, HAIR_L: HAIR_D}
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


def flare_skirt(c, x0, w, ty, flare):
    """Widen the pleated skirt of a torso sprite pasted at (x0, ty), width w.
    flare = extra px at the hem on each side (spin / jump swish)."""
    if not flare:
        return
    for r in range(10, 14):
        ext = round(flare * (r - 9) / 4)
        for e in range(1, ext + 1):
            for x in (x0 - e, x0 + w - 1 + e):
                c.set(x, ty + r, RED_L if ((x - x0) // 2) % 2 == 0 else RED_D)


def safe_clip(c):
    """Clear a 2px frame so the outline pass can never reach the canvas border."""
    for y in range(H):
        for x in range(W):
            if x < 2 or x >= W - 2 or y < 2 or y >= H - 2:
                c.g[y][x] = 0


def touches_border(c):
    return (any(c.g[0]) or any(c.g[H - 1]) or any(r[0] for r in c.g) or any(r[W - 1] for r in c.g))


# ------------------------------------------------------------ new body parts
def head_side():
    """Profile head looking right. Ponytail hangs from the back of the head.
    Returns (canvas, body_x0)."""
    c = C(16, 13)
    ox = 4
    rows = {1: (1, 9), 2: (0, 9), 3: (0, 9), 4: (0, 9), 5: (0, 9), 6: (0, 9),
            7: (0, 9), 8: (0, 9), 9: (1, 9), 10: (3, 8), 11: (4, 7)}
    for y, (a, b) in rows.items():
        for x in range(a, b + 1):
            c.set(ox + x, y, SKM)
    for y in range(3, 10):
        c.set(ox + 9, y, SKD)                      # front edge in shade
    c.rect(ox + 10, 6, 1, 2, SKM)                  # nose
    c.set(ox + 10, 7, SKD)
    for x in (2, 4, 5, 7, 9):                      # messy hair on top
        c.set(ox + x, 0, HAIR_D)
    c.set(ox + 3, 0, HAIR_L)
    c.set(ox + 8, 0, HAIR_L)
    c.rect(ox + 1, 1, 9, 1, HAIR_D)
    for x in (4, 5, 8):
        c.set(ox + x, 1, HAIR_L)
    c.rect(ox + 0, 2, 4, 6, HAIR_D)                # hair at the back of the head
    c.set(ox + 1, 3, HAIR_L)
    c.set(ox + 2, 5, HAIR_L)
    c.rect(ox + 6, 2, 3, 1, HAIR_D)                # fringe
    c.rect(ox + 3, 6, 2, 2, SKD)                   # ear
    c.set(ox + 3, 6, SKM)
    c.rect(ox + 6, 4, 3, 3, EYE)                   # eye
    c.rect(ox + 8, 5, 1, 2, PUPIL)
    c.set(ox + 9, 3, PUPIL)                        # lash flick
    c.set(ox + 6, 7, SKD)                          # eye bag
    c.rect(ox + 6, 9, 4, 1, RED_D)                 # lipstick grin
    c.set(ox + 7, 9, WH)
    c.rect(ox + 7, 10, 2, 1, TONG)                 # lolling tongue
    c.set(ox + 7, 11, TONG)
    return c, ox


def ponytail_side(c, ox, pn):
    """Ponytail behind the profile head (drawn separately so it can swing)."""
    c.rect(ox - 2, 2, 3, 2, RED_D)                 # scrunchie
    c.rect(ox - 2, 2, 3, 1, RED_L)
    for r in range(4, 12):
        sh = round(pn * (r - 4) / 7)
        wd = 3 if r < 10 else 2
        x0 = ox - 3 + sh + (0 if r < 10 else 1)
        c.rect(x0, r, wd, 1, HAIR_D)
        if r % 2 == 0:
            c.set(x0, r, HAIR_L)


def head_side_pn(pn=0):
    c, ox = head_side()
    ponytail_side(c, ox, pn)
    return c, ox


def head_back(pn=0, tdx=0, strip=False):
    """Back of the head: purple hair all over, scrunchie, ponytail hanging down the
    back. Returns (canvas, body_x0)."""
    c = C(16, 15)
    ox = 2
    rows = {2: (1, 10), 3: (0, 11), 4: (0, 11), 5: (0, 11), 6: (0, 11), 7: (0, 11),
            8: (0, 11), 9: (0, 11), 10: (1, 10), 11: (3, 8)}
    for y, (a, b) in rows.items():
        for x in range(a, b + 1):
            c.set(ox + x, y, SKM)
    for x in (2, 4, 5, 7, 9):
        c.set(ox + x, 0, HAIR_D)
    c.set(ox + 3, 0, HAIR_L)
    c.set(ox + 8, 0, HAIR_L)
    c.rect(ox + 1, 1, 10, 1, HAIR_D)
    for x in (4, 5, 8):
        c.set(ox + x, 1, HAIR_L)
    for y in range(2, 10):
        a, b = rows[y]
        for x in range(a, b + 1):
            if y in (5, 6) and x in (0, 11):
                continue                             # ears
            c.set(ox + x, y, HAIR_L if (x % 3 == 1 and y % 3 != 2) else HAIR_D)
    c.rect(ox + 2, 10, 8, 1, HAIR_D)                 # nape
    c.set(ox + 0, 5, SKD)
    c.set(ox + 0, 6, SKM)
    c.set(ox + 11, 5, SKD)
    c.set(ox + 11, 6, SKD)
    c.rect(ox + 3, 11, 6, 1, SKD)                    # neck
    # ponytail
    tx = ox + 4 + tdx
    c.rect(tx, 2, 4, 1, RED_L)                       # scrunchie
    c.rect(tx, 3, 4, 1, RED_D)
    for r in range(4, 14):
        sh = round(pn * (r - 4) / 9)
        a, wd = (tx + sh, 4) if r < 10 else ((tx + sh + 1, 3) if r < 13 else (tx + sh + 1, 2))
        c.rect(a, r, wd, 1, HAIR_L)                  # light tail stands out from the hair mass
        c.set(a + wd - 1, r, HAIR_D)
        if r in (5, 8, 11):
            c.set(a + 1, r, HAIR_D)
    if strip:                                        # a strip of cheek peeks out (3/4 back)
        for y in range(4, 10):
            c.set(ox + 11, y, SKM)
            c.set(ox + 10, y, SKD if y in (5, 6) else HAIR_D)
        c.set(ox + 11, 3, 0)
    return c, ox


def head_3q(pn=0):
    """3/4 front head turned to the right, ponytail hanging at the back (left).
    Returns (canvas, body_x0)."""
    c = C(15, 13)
    ox = 3
    rows = {2: (1, 10), 3: (0, 11), 4: (0, 11), 5: (0, 11), 6: (0, 11), 7: (0, 11),
            8: (0, 11), 9: (0, 11), 10: (1, 10), 11: (3, 8)}
    for y, (a, b) in rows.items():
        for x in range(a, b + 1):
            c.set(ox + x, y, SKM)
    for y in range(3, 10):
        c.set(ox + 0, y, SKL)
        c.set(ox + 11, y, SKD)
    c.set(ox + 10, 10, SKD)
    c.rect(ox + 3, 11, 6, 1, SKD)
    for x in (2, 4, 5, 7, 9):
        c.set(ox + x, 0, HAIR_D)
    c.set(ox + 3, 0, HAIR_L)
    c.set(ox + 8, 0, HAIR_L)
    c.rect(ox + 1, 1, 10, 1, HAIR_D)
    for x in (4, 5, 8):
        c.set(ox + x, 1, HAIR_L)
    c.rect(ox + 0, 2, 3, 5, HAIR_D)                  # hair down the back side
    c.set(ox + 1, 3, HAIR_L)
    c.rect(ox + 7, 2, 4, 1, HAIR_D)                  # fringe
    c.set(ox + 11, 2, HAIR_D)
    c.set(ox + 11, 3, HAIR_D)
    c.rect(ox + 3, 4, 2, 3, EYE)                     # far eye (narrow)
    c.rect(ox + 4, 5, 1, 2, PUPIL)
    c.set(ox + 2, 3, PUPIL)
    c.rect(ox + 7, 4, 3, 3, EYE)                     # near eye
    c.rect(ox + 9, 5, 1, 2, PUPIL)
    c.set(ox + 10, 3, PUPIL)
    c.set(ox + 6, 7, SKD)                            # nose
    c.set(ox + 7, 8, SKD)
    c.rect(ox + 5, 9, 6, 1, RED_D)                   # grin
    c.set(ox + 6, 9, WH)
    c.set(ox + 9, 9, WH)
    c.rect(ox + 6, 10, 4, 1, PUPIL)
    c.rect(ox + 8, 10, 2, 1, TONG)
    c.set(ox + 8, 11, TONG)
    ponytail_side(c, ox, pn)
    return c, ox


def torso_side():
    """Profile torso (facing right): red top, white trim, midriff, pleated skirt."""
    c = C(10, 14)
    c.rect(1, 0, 8, 7, RED_L)
    c.rect(6, 0, 3, 7, RED_D)
    c.rect(3, 0, 4, 1, SKD)                          # neckline
    c.rect(1, 6, 8, 1, WH)                           # trim
    c.rect(1, 2, 1, 3, WH)                           # a bit of white back trim
    c.rect(2, 7, 6, 2, SKM)                          # midriff
    c.rect(2, 7, 1, 2, SKL)
    c.rect(7, 7, 1, 2, SKD)
    c.set(6, 8, SKD)
    c.rect(1, 9, 8, 1, WH)                           # waistband
    for y in range(10, 14):                          # pleats
        for x in range(10):
            c.set(x, y, RED_L if (x // 2) % 2 == 0 else RED_D)
    for x, y in ((2, 13), (3, 13), (7, 13), (5, 12), (0, 13), (9, 13)):
        c.set(x, y, 0)                               # torn hem
    return c


def torso_back():
    """Back of the torso: same top with a Z print, closed collar, torn seam, skirt."""
    c = C(12, 14)
    c.g = [row[:] for row in Z.torso().g]
    c.rect(3, 0, 6, 1, RED_L)
    c.rect(8, 0, 1, 1, RED_D)
    c.rect(4, 1, 4, 1, RED_L)
    c.rect(4, 0, 4, 1, SKD)                          # back of the neck
    c.rect(8, 3, 2, 1, SKM)                          # torn seam
    c.set(8, 4, SKD)
    c.set(5, 8, SKD)                                 # spine dimple
    return c


def torso_3q(back):
    """Front/back torso narrowed to 10 columns for the 3/4 views."""
    tor = torso_back() if back else Z.torso()
    t2 = C(10, 14)
    t2.g = [row[1:11] for row in tor.g]
    return t2


def leg_side(swing, short=0):
    """Leg seen from the side, sneaker pointing right. `swing` = px the foot is
    shifted forward (+) / back (-) relative to the hip (sheared leg)."""
    n = 9 - short                                    # skin rows
    rows = 14 - short
    base = 6
    c = C(18, rows)
    sh_shoe = round(swing * (n + 2) / (rows - 1))
    for r in range(rows):
        x = base + round(swing * r / (rows - 1))
        if r < n:
            c.rect(x, r, 4, 1, SKM)
            c.set(x, r, SKL)
            c.set(x + 3, r, SKD)
        elif r == n:
            c.rect(x, r, 4, 1, RED_D)                # sock stripe
        elif r == n + 1:
            c.rect(x, r, 4, 1, WH)
        else:                                        # sneaker, toe forward
            xs = base + sh_shoe
            c.rect(xs - 1, r, 7, 1, WH_D if r == rows - 1 else WH)
            if r == n + 3:
                c.rect(xs + 4, r, 2, 1, RED_D)       # toe cap
    return c


def pom_small():
    return Z.pom()


def arm_side(dy, with_pom=True):
    """Arm stretched forward (right) with a pom-pom; hand `dy` px higher(-)/lower(+)
    than the shoulder. The shoulder row of the canvas is YB (paste so it matches)."""
    c = C(24, 28)
    yb = 14
    for x in range(10):
        y = yb + round(dy * x / 9)
        if x < 4:
            c.rect(x, y, 1, 4, RED_L if x < 2 else RED_D)       # sleeve
            if x == 3:
                c.rect(x, y, 1, 4, WH)                          # white cuff
        else:
            c.rect(x, y, 1, 3, SKM)
            c.set(x, y, SKL)
            c.set(x, y + 2, SKD)
    ye = yb + dy
    c.rect(9, ye - 1, 3, 5, SKM)                                # fist
    c.rect(9, ye - 1, 3, 1, SKL)
    c.rect(9, ye + 3, 3, 1, SKD)
    if with_pom:
        c.paste(pom_small(), 8, ye - 4)
    return c


SIDE_YB = 14


def diag_leg(c, hx, hy, fx, fy):
    """Leg from the hip (hx, hy) to the foot centre (fx, fy): skin, sock, sneaker.
    Used for the split / star poses where the legs leave the vertical."""
    leg = C(W, H)
    L = math.hypot(fx - hx, fy - hy)
    ux, uy = (fx - hx) / L, (fy - hy) / L
    steps = int(L * 3)
    for i in range(steps + 1):
        t = i / steps
        x, y = hx + (fx - hx) * t, hy + (fy - hy) * t
        d = t * L
        if d <= L - 5:
            col = SKM
        elif d <= L - 3.8:
            col = RED_D
        else:
            col = WH
        leg.rect(round(x) - 1, round(y) - 1, 4, 4, col)
    for y in range(H):                               # 3-tone shading from the silhouette
        for x in range(W):
            if leg.g[y][x] == SKM:
                if y == 0 or leg.g[y - 1][x] == 0:
                    leg.g[y][x] = SKL
                elif y + 1 >= H or leg.g[y + 1][x] == 0:
                    leg.g[y][x] = SKD
    horiz = abs(ux) > abs(uy)
    cx, cy = fx + ux * 1.5, fy + uy * 1.5            # sneaker
    sw, sh = (4, 5) if horiz else (5, 4)
    sx, sy = round(cx - sw / 2), round(cy - sh / 2)
    leg.rect(sx, sy, sw, sh, WH)
    if horiz:                                        # sole on the outer end
        leg.rect(sx if ux < 0 else sx + sw - 1, sy, 1, sh, WH_D)
        leg.rect(sx + (1 if ux < 0 else 0), sy + sh - 1, sw - 1, 1, WH_D)
        leg.rect(sx + 1, sy + 1, 2, 1, RED_D)
    else:
        leg.rect(sx, sy + sh - 1 if uy > 0 else sy, sw, 1, WH_D)
        leg.rect(sx + 1, sy + 1, 2, 1, RED_D)
    c.paste(leg, 0, 0)


def diag_arm(c, sx, sy, hx, hy):
    """Straight arm from the shoulder (sx, sy) to the hand (hx, hy): sleeve, white cuff,
    skin, pom-pom held at the hand. Used for the star pose of the cartwheel."""
    arm = C(W, H)
    L = math.hypot(hx - sx, hy - sy)
    steps = int(L * 3)
    for i in range(steps + 1):
        t = i / steps
        x, y, d = sx + (hx - sx) * t, sy + (hy - sy) * t, t * L
        col = RED_L if d < 3 else (WH if d < 4.2 else SKM)
        arm.rect(round(x) - 1, round(y) - 1, 3, 3, col)
    for y in range(H):
        for x in range(W):
            v = arm.g[y][x]
            if v in (SKM, RED_L):
                if y == 0 or arm.g[y - 1][x] == 0:
                    arm.g[y][x] = SKL if v == SKM else RED_L
                elif y + 1 >= H or arm.g[y + 1][x] == 0:
                    arm.g[y][x] = SKD if v == SKM else RED_D
    c.paste(arm, 0, 0)
    c.paste(Z.pom(), hx - 4, hy - 4)


# ------------------------------------------------------------ views (8 facings)
DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def v_front(dx=0, bob=0, hop=0, tilt=0, hyL=0, hyR=0, lift=None, flare=0, legs=None,
            arms=True, outline=True, starm=None, **_):
    """Front view (S). starm = ((dxL, dyL), (dxR, dyR)) straight diagonal arms (hand offsets
    from the shoulders) for the star pose. legs = ((fxL, fyL), (fxR, fyR)) foot offsets from the hips for
    split / star poses (None = standing legs)."""
    c = C(W, H)
    y0 = bob - hop
    if legs is None:
        kx = 1 if bob >= 2 else 0
        ly = GROUND - (14 - bob) - hop
        lyL = ly - (1 if lift == "L" else 0)
        lyR = ly - (1 if lift == "R" else 0)
        lxL = CX - 7 + dx - kx - (1 if lift == "L" else 0)
        lxR = CX + 1 + dx + kx + (1 if lift == "R" else 0)
        c.paste(Z.leg("L", bob), lxL, lyL)
        c.paste(Z.leg("R", bob), lxR, lyR)
    else:
        (fl, fr) = legs
        diag_leg(c, CX - 3 + dx, 36 + y0, CX - 3 + dx + fl[0], 36 + y0 + fl[1])
        diag_leg(c, CX + 2 + dx, 36 + y0, CX + 2 + dx + fr[0], 36 + y0 + fr[1])
    c.rect(CX - 6 + dx, 34 + y0, 12, 3, SKM)
    c.rect(CX + 2 + dx, 34 + y0, 4, 3, SKD)
    c.paste(Z.torso(), CX - 6 + dx, 21 + y0)
    flare_skirt(c, CX - 6 + dx, 12, 21 + y0, flare)
    if starm:
        diag_arm(c, CX - 6 + dx, 24 + y0, CX - 6 + dx + starm[0][0], 24 + y0 + starm[0][1])
        diag_arm(c, CX + 5 + dx, 24 + y0, CX + 5 + dx + starm[1][0], 24 + y0 + starm[1][1])
    elif arms:
        Z.put_arm(c, Z.arm(hyL), "L", dx, y0)
        Z.put_arm(c, Z.arm(hyR), "R", dx, y0)
    c.rect(CX - 2 + dx, 20 + y0, 4, 1, SKD)
    c.paste(sheared(Z.head(), tilt), CX - 9 + dx, 8 + y0)
    if outline:
        c.outline()
    return c


def put_arm_at(c, drawn, side, sx, y0, shade=False):
    """Paste a Z.arm() drawing so its sleeve edge sits at world column sx."""
    a, ax, sy = drawn
    if shade:
        a = shade_far(a)
    oy = 22 + y0 - sy
    if side == "L":
        c.paste(a, sx - ax, oy)
    else:
        a = a.flip()
        c.paste(a, sx - (a.w - 1 - ax), oy)


def v_34(back, dx=0, bob=0, hop=0, s=0, lift=None, hyL=0, hyR=0, tilt=0, pn=0, flare=0, **_):
    """Back (back=True, three_q=False -> see v_back) and 3/4 views. s = leg shift."""
    c = C(W, H)
    y0 = bob - hop
    ly = GROUND - (14 - bob) - hop
    c.paste(Z.leg("L", bob), CX - 5 + dx + s - (1 if lift == "L" else 0), ly - (1 if lift == "L" else 0))
    c.paste(Z.leg("R", bob), CX + dx - s + (1 if lift == "R" else 0), ly - (1 if lift == "R" else 0))
    tx = CX - 5 + dx
    c.rect(tx, 34 + y0, 10, 3, SKM)
    c.rect(tx + 6, 34 + y0, 4, 3, SKD)
    put_arm_at(c, Z.arm(hyL), "L", tx + 1, y0, shade=True)           # far arm, behind the body
    c.paste(torso_3q(back), tx, 21 + y0)
    flare_skirt(c, tx, 10, 21 + y0, flare)
    put_arm_at(c, Z.arm(hyR), "R", tx + 9, y0)                        # near arm
    c.rect(CX - 2 + dx, 20 + y0, 4, 1, SKD)
    if back:
        h, bx = head_back(pn, tdx=-1, strip=True)
    else:
        h, bx = head_3q(pn)
    c.paste(sheared(h, tilt, 2), CX - 8 + dx - bx - 2 + (2 if back else 3), 8 + y0)
    c.outline()
    return c


def v_back(dx=0, bob=0, hop=0, lift=None, hyL=0, hyR=0, tilt=0, pn=0, flare=0, **_):
    c = C(W, H)
    y0 = bob - hop
    kx = 1 if bob >= 2 else 0
    ly = GROUND - (14 - bob) - hop
    c.paste(Z.leg("L", bob), CX - 7 + dx - kx - (1 if lift == "L" else 0), ly - (1 if lift == "L" else 0))
    c.paste(Z.leg("R", bob), CX + 1 + dx + kx + (1 if lift == "R" else 0), ly - (1 if lift == "R" else 0))
    c.rect(CX - 6 + dx, 34 + y0, 12, 3, SKM)
    c.rect(CX + 2 + dx, 34 + y0, 4, 3, SKD)
    c.paste(torso_back(), CX - 6 + dx, 21 + y0)
    flare_skirt(c, CX - 6 + dx, 12, 21 + y0, flare)
    Z.put_arm(c, Z.arm(hyL), "L", dx, y0)
    Z.put_arm(c, Z.arm(hyR), "R", dx, y0)
    c.rect(CX - 2 + dx, 20 + y0, 4, 1, SKD)
    h, bx = head_back(pn)
    c.paste(sheared(h, tilt, 2), CX - 6 + dx - bx - 2, 8 + y0)
    c.outline()
    return c


def v_side(dx=0, bob=0, hop=0, swing=0, farswing=None, lift=None, dyN=-1, dyF=-1, tilt=1,
           lean=1, pn=0, flare=0, farfwd=False, **_):
    """Profile facing right. swing = near foot forward(+)/back(-); far foot defaults to -swing."""
    fs = -swing if farswing is None else farswing
    c = C(W, H)
    ly = GROUND - (14 - bob) - hop
    y0 = bob - hop
    c.paste(shade_far(leg_side(fs, bob)), CX - 9 + dx, ly - (1 if lift == "R" else 0))
    c.paste(leg_side(swing, bob), CX - 9 + dx, ly - (1 if lift == "L" else 0))
    tx = CX - 5 + lean + dx
    c.rect(tx + 1, 34 + y0, 8, 3, SKM)
    c.rect(tx + 6, 34 + y0, 3, 3, SKD)
    ay = 24 + y0 - SIDE_YB
    if farfwd:                                         # far arm also forward (a bit behind)
        c.paste(shade_far(arm_side(dyF)), tx + 1, ay + 1)
    else:                                              # far arm swings backwards
        c.paste(shade_far(arm_side(dyF)).flip(), tx + 5 - 23, ay)
    c.paste(torso_side(), tx, 21 + y0)
    flare_skirt(c, tx, 10, 21 + y0, flare)
    c.paste(arm_side(dyN), tx + 2, ay)
    c.rect(CX - 2 + lean + dx, 20 + y0, 3, 1, SKD)
    h, bx = head_side_pn(pn)
    c.paste(sheared(h, tilt, 2), CX - 8 + lean + dx - 2 - 0, 8 + y0)
    c.outline()
    return c


def view(direction, **pose):
    """Draw the cheerleader facing `direction`; W/SW/NW are mirrors of E/SE/NE."""
    flip = direction in ("SW", "W", "NW")
    d = {"SW": "SE", "W": "E", "NW": "NE"}.get(direction, direction)
    if d == "S":
        c = v_front(**pose)
    elif d == "N":
        c = v_back(**pose)
    elif d == "E":
        c = v_side(**pose)
    elif d == "SE":
        c = v_34(False, **pose)
    else:
        c = v_34(True, **pose)
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
    pump = round(4 * math.sin(2 * math.pi * p / 6 + .4))  # poms pump alternately up / down
    fl = 1 if p in (1, 4) else 0                          # skirt swishes a little
    if d == "S":
        pose = dict(dx=round(sn), tilt=round(2 * sn), bob=BOB[p], hyL=-2 + pump, hyR=-2 - pump,
                    lift=lifts(p), flare=fl)
    elif d == "E":
        pose = dict(bob=BOB[p], lift=lifts(p), swing=round(5 * cs), dyN=-3 + round(4 * sn),
                    dyF=3 - round(3 * sn), tilt=round(1.5 * sn) + 1, pn=round(-sn), flare=fl)
    elif d == "N":
        pose = dict(dx=round(sn), bob=BOB[p], lift=lifts(p), hyL=-2 + pump, hyR=-2 - pump,
                    tilt=round(1.5 * sn), pn=round(2 * sn), flare=fl)
    else:
        pose = dict(dx=round(sn), bob=BOB[p], lift=lifts(p), s=round(2 * cs),
                    hyL=-2 + pump, hyR=-2 - pump, tilt=round(1.5 * sn), pn=round(-sn), flare=fl)
    return view(direction, **pose)


# ------------------------------------------------------------------ dances
# B "Pirouette": a full 360 spin through all eight facings with a jump arc:
#    crouch (S), launch, tuck at the top, land. Poms are raised for the spin and the
#    skirt flares out on the way round.
SPIN = ["S", "SE", "E", "NE", "N", "NW", "W", "SW"]


def dance_pirouette(f):
    d = SPIN[f]
    hop = (0, 3, 5, 6, 6, 4, 2, 0)[f]
    bob = (2, 1, 2, 3, 3, 2, 1, 2)[f]
    flare = (0, 1, 2, 3, 3, 3, 2, 1)[f]
    up = f in (1, 2, 3, 4, 5, 6)
    hy = -8 if up else 0                               # poms straight up while spinning
    hyL, hyR = (hy, hy - 0) if f not in (1, 6) else (-4, -8)
    if d == "S":
        return view(d, bob=bob, hop=hop, hyL=-4, hyR=-4, tilt=0, flare=flare)
    if d in ("SE", "SW"):
        return view(d, bob=bob, hop=hop, hyL=hyL, hyR=hyR, tilt=1, flare=flare, pn=-1)
    if d in ("E", "W"):
        return view(d, bob=bob, hop=hop, dyN=-8 if up else 0, dyF=-6 if up else 0,
                    swing=1 if hop else 0, tilt=-1, flare=flare, pn=1, farfwd=True)
    if d in ("NE", "NW"):
        return view(d, bob=bob, hop=hop, hyL=hyL, hyR=hyR, tilt=-1, flare=flare, pn=1)
    return view(d, bob=bob, hop=hop, hyL=hy, hyR=hy, tilt=0, flare=flare, pn=0)


# C "Cartwheel + toe-touch": crouch, a sideways cartwheel (the finished star-pose frame
#    is re-sampled pixel by pixel for each angle, nothing is blurred), landing, a toe-touch
#    jump with the legs split sideways and poms up, and a final ta-da pose.
def rotate_fig(c, deg, scale=1.0, src=(20.0, 30.0), dst=(20.0, 22.0), outline=True):
    """Rotate a finished frame by `deg` (clockwise on screen) about `src`, drawing the
    result around `dst`. The outline is stripped first and redrawn afterwards."""
    base = unoutlined(c)
    sc_x, sc_y = scale if isinstance(scale, tuple) else (scale, scale)
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    out = C(W, H)
    offs = (-1 / 3, 0.0, 1 / 3)
    for Y in range(H):
        for X in range(W):
            votes, order = {}, []
            for oy in offs:
                for ox in offs:
                    dx, dy = (X + .5 + ox - dst[0]) / sc_x, (Y + .5 + oy - dst[1]) / sc_y
                    sx = src[0] + ca * dx + sa * dy          # inverse rotation
                    sy = src[1] - sa * dx + ca * dy
                    ix, iy = math.floor(sx), math.floor(sy)
                    v = base.g[iy][ix] if 0 <= ix < W and 0 <= iy < H else 0
                    votes[v] = votes.get(v, 0) + 1
                    if v not in order:
                        order.append(v)
            out.g[Y][X] = max(order, key=lambda v: (votes[v], -order.index(v)))
    if outline:
        out.outline()
    return out


def rotate_fit(c, deg, scale, src, dst):
    """rotate_fig, shrinking the figure a little until it clears the canvas border."""
    while True:
        o = rotate_fig(c, deg, scale, src, dst)
        if not touches_border(o):
            return o
        scale -= .03


STAR = dict(bob=0, tilt=0, legs=((-8, 11), (8, 11)), starm=((-9, -9), (9, -9)))


def dance_cartwheel(f):
    if f == 0:                                   # crouch, poms swung down and back
        return view("S", dx=-1, bob=2, hyL=4, hyR=4, tilt=-2)
    if f in (1, 2, 3, 4):                        # the cartwheel: star pose rotating clockwise
        ang, sc, dst = {1: (35, .88, (17, 25)), 2: (105, .80, (19, 23)),
                        3: (190, .80, (22, 21)), 4: (280, .80, (24, 23))}[f]
        return rotate_fit(view("S", **STAR), ang, sc, (20, 29), dst)
    if f == 5:                                   # landing, arms out, knees bent
        return view("S", dx=1, bob=2, hyL=0, hyR=0, tilt=2, flare=1)
    if f == 6:                                   # toe-touch jump: legs split, poms up
        return view("S", dx=0, bob=0, hop=6, hyL=-8, hyR=-8, tilt=0, flare=2,
                    legs=((-11, -1), (11, -1)))
    return view("S", dx=-1, bob=0, hyL=-8, hyR=-8, tilt=-1)   # final pose: poms up, ta-da


# ------------------------------------------------------- spawn (crawl out) & die (splat)
def hand_sprite():
    """A pale blue zombie hand with a bone stump (7x9)."""
    c = C(7, 9)
    for x in (0, 2, 4, 6):
        c.rect(x, 0, 1, 2, SKM)
    c.rect(0, 2, 7, 4, SKM)
    c.rect(0, 2, 1, 4, SKL)
    c.rect(6, 2, 1, 4, SKD)
    c.rect(0, 5, 7, 1, SKD)
    c.rect(1, 6, 5, 2, SKM)
    c.rect(5, 6, 1, 2, SKD)
    c.set(3, 7, WH)
    c.set(2, 8, SKD)
    c.set(4, 8, SKD)
    c.set(3, 8, WH)
    return c


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


def forearm_hand(c, x, h):
    """A hand + forearm reaching up out of the ground, h rows tall."""
    c.rect(x + 1, GY - h + 6, 5, h - 5, SKM)
    c.rect(x + 1, GY - h + 6, 1, h - 5, SKL)
    c.rect(x + 5, GY - h + 6, 1, h - 5, SKD)
    hand = hand_sprite()
    for j in range(6):
        for i in range(7):
            if hand.g[j][i]:
                c.set(x + i, GY - h + j, hand.g[j][i])


def spawn_frame(f):
    rng = random.Random(300 + f)
    c = C(W, H)
    rx = (5, 8, 11, 13, 14, 13, 11, 8)[f]
    if f < 3:
        if f == 1:
            forearm_hand(c, 13, 10)
        if f == 2:
            forearm_hand(c, 10, 12)
            c.paste(Z.pom(), 22, GY - 17)             # the other fist still holds a pom-pom
            forearm_hand(c, 26, 9)
    else:
        sink, pose = {
            3: (28, dict(hyL=4, hyR=4)),
            4: (19, dict(hyL=4, hyR=4, tilt=-1)),
            5: (9, dict(hyL=2, hyR=2, bob=1, tilt=2)),
            6: (2, dict(hyL=0, hyR=0, bob=2, tilt=2)),
            7: (0, dict(hyL=0, hyR=0, bob=0, tilt=0)),
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
    for _ in range((3, 5, 6, 6, 8, 10, 8, 5)[f]):         # flying / falling dirt specks
        x, y = rng.randint(6, 34), rng.randint(GY - 24, GY - 2) if f > 2 else rng.randint(GY - 14, GY - 2)
        col = rng.choice((DIRT_L, DIRT_M, DIRT_D))
        if not any(c.g[j][i] for j in range(y - 1, y + 2) for i in range(x - 1, x + 2)
                   if 0 <= i < W and 0 <= j < H):            # only in free air, never on the body
            c.set(x, y, col)
    safe_clip(c)
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


def tight(c):
    """Cropped copy of a canvas plus the (x, y) of its top-left corner."""
    ys = [y for y in range(c.h) if any(c.g[y])]
    xs = [x for x in range(c.w) if any(c.g[y][x] for y in range(c.h))]
    return c.crop(0), min(xs), min(ys)


def build_parts():
    """The cheerleader's real parts: (sprite, start centre, rest centre, rest quarter-turns
    (total quarter turns while tumbling), apex height of the throw). Parts are drawn in this
    order, so later ones land on top of the pile."""
    head = tight(Z.head())[0]
    tors = Z.torso()
    armL = tight(Z.arm(0, with_pom=False)[0])[0]
    armR = tight(Z.arm(0, with_pom=False)[0].flip())[0]
    legL, legR = Z.leg("L"), Z.leg("R")
    pom = Z.pom()
    return [
        (legL, (16, 41), (31, 43), 5, 10, -8),
        (legR, (24, 41), (31, 37), 5, 12, 8),
        (head, (21, 14), (8, 39), 5, 14, 2),
        (tors, (20, 28), (20, 39), 4, 8, 3),
        (pom, (7, 15), (8, 28), 0, 6, -9),
        (pom, (33, 15), (20, 28), 0, 8, 9),
        (armL, (8, 24), (34, 30), 4, 12, -9),
        (armR, (32, 24), (25, 30), 4, 12, 9),
    ]


def die_frame(f):
    rng = random.Random(11)
    c = C(W, H)
    if f == 0:                                       # hit: white flash + recoil
        fig = v_front(dx=-1, tilt=-3, hyL=-8, hyR=-4)
        for y in range(H):
            for x in range(W):
                if fig.g[y][x] > 1:
                    fig.g[y][x] = WH
        return fig
    if f in (1, 2):                                  # swelling up, cracks glowing
        k = (1.12, 1.06) if f == 1 else (1.28, 1.12)     # swells wider than tall
        body = v_front(dx=0, bob=0, tilt=(2 if f == 1 else -2), arms=False, outline=False)
        fig = rotate_fig(body, 0, k, (20, 47), (20, 47), outline=False)
        tmp = C(W, H)
        sx = 1 if f == 1 else -1
        Z.put_arm(tmp, Z.arm(-4 if f == 1 else -8), "L", sx, 0)
        Z.put_arm(tmp, Z.arm(-4 if f == 1 else -8), "R", sx, 0)
        fig.paste(tmp, 0, 0)
        fig.outline()
        for _ in range(5 * f):
            x, y = rng.randint(12, 28), rng.randint(14, 44)
            for (px, py) in [(x, y), (x + 1, y + 1), (x + 1, y + 2), (x + 2, y + 3)]:
                if 0 <= px < W and 0 <= py < H and fig.g[py][px] > 1:
                    fig.g[py][px] = GOO
        return fig
    t = f - 3                                         # 0..4 : burst, fall, land, rest
    u = (.25, .5, .75, .95, 1.0)[t]
    # --- goo puddle on the ground (behind the parts) + bones
    pr = (0, 0, 0, 5, 9, 12, 14, 14)[f]
    for y in range(GY - 8, GY + 5):
        for x in range(W):
            d = ((x + .5 - 20) / pr) ** 2 + ((y + .5 - (GY - 1)) / (pr * .34)) ** 2
            if d <= 1:
                col = GOO_D if d > .7 else GOO
                if x < 20 and y < GY - 2 and d > .3:
                    col = GOO
                if (x * 7 + y * 3) % 17 == 0 and d < .6:
                    col = WH                           # shine
                c.set(x, y, col)
    if f >= 5:                                        # a few bones in the puddle
        for (bx, by) in ((5, GY - 1), (27, GY), (12, GY + 1)):
            c.rect(bx, by, 5, 1, WH)
            c.set(bx - 1, by - 1, WH)
            c.set(bx + 5, by + 1, WH)
    # --- the parts: thrown out of the burst, tumbling, landing in a pile
    for sp, (x0, y0), (rx, ry), q, apex, bulge in build_parts():
        base = tight(unoutlined(sp))[0]
        spr = rot90(base, int(q * u + .5) if u < 1 else q)
        rest_h = rot90(base, q).h
        e = 1 - (1 - u) ** 2                          # ease-out sideways
        cx = x0 + (rx - x0) * e + bulge * math.sin(math.pi * u)   # thrown outwards, then settles
        cx = min(max(cx, spr.w / 2 + 3), W - 3 - spr.w / 2)
        cy = y0 + (ry - y0) * u ** 1.8 - apex * 4 * u * (1 - u)
        cy = max(cy, spr.h / 2 + 3)
        cy = min(cy, ry + (rest_h - spr.h) / 2) if u >= 1 else cy
        c.paste(spr, int(round(cx - spr.w / 2)), int(round(cy - spr.h / 2)))
    # --- flying goo droplets
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
            c.rect(int(x), int(y), 2 if i % 3 else 1, 2 if i % 2 else 1, GOO if i % 2 else GOO_D)
    safe_clip(c)
    c.outline()
    return c


# -------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    sheets = {}
    for tag, fn in (("danceB", dance_pirouette), ("danceC", dance_cartwheel),
                    ("spawn", spawn_frame), ("die", die_frame)):
        sheets[tag] = []
        for f in range(8):
            im = fn(f).image()
            im.save(os.path.join(OUT, f"zombie3_{tag}_{f}.png"))
            sheets[tag].append(im)
    for dname in DIRS:
        sheets[dname] = []
        for p in range(6):
            im = walk_frame(dname, p).image()
            im.save(os.path.join(OUT, f"zombie3_walk_{dname}_{p}.png"))
            sheets[dname].append(im)

    # preview at half size
    hw, hh = 80, 100
    keys = ["danceB", "danceC", "spawn", "die"] + DIRS
    prev = Image.new("RGBA", (8 * (hw + 6) + 20, len(keys) * (hh + 22) + 10), (88, 92, 104, 255))
    d = ImageDraw.Draw(prev)
    for r, key in enumerate(keys):
        y = 8 + r * (hh + 22)
        d.text((6, y), key, fill=(255, 255, 255, 255))
        for i, im in enumerate(sheets[key]):
            prev.alpha_composite(im.resize((hw, hh), Image.NEAREST), (6 + i * (hw + 6), y + 12))
    prev.save(os.path.join(OUT, "zombie3_moves_preview.png"))
    print("wrote", len(os.listdir(OUT)), "files to", OUT)


if __name__ == "__main__":
    main()
