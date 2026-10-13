#!/usr/bin/env python3
"""
make_backgrounds.py - apocalyptic, angled bird's-eye ("3/4 top-down") pixel-art
backgrounds for the zombie game.

Run:   python3 make_backgrounds.py [output_dir] [scene ...]
Needs: Pillow + numpy.   Default output ./backgrounds/, default = every scene.
Scenes:  street_intersection, empty_mall, airport, giant_picnic

THE WALKABLE-AREA RULE (same for every background)
  The canvas is 1920 x 1080 (480 x 270 logical px, scaled 4x). The middle 80% x 80%
  of it - the "main square" - is ALWAYS walkable and identical in every scene:
        x 192..1728, y 108..972   (PAD = 10% on every side)
  Inside the square there is only flat ground (roads, pavement, cracks, puddles, litter),
  so nothing blocks a character. Everything TALL (buildings, fences, wrecks, barricades,
  trees, fires) lives in the 10% padding around it, and the padding is darkened with a
  dither band so the edge reads clearly. Each scene also tells you where the walkable
  edge is via  walkable_area.json  and a *_walkable_preview.png overlay.
  Change PAD below if you want 15% or 20% padding.

VIEW: the camera looks down at an angle. Ground lies flat, buildings show their roof
plus their south-facing front wall; things that stand up show their top and front.

Same construction as the sprite scripts: a logical pixel grid scaled 4x with
nearest-neighbour; every object is drawn on its own tiny canvas, outlined automatically
with the dark outline colour, then pasted.

Where to change things
  * PAD ................ walkable-square padding (0.10 = 10%)
  * PAL ................ every colour, named once (darkened copies for the padding are
                         generated automatically from it)
  * ROAD_* ............. road positions (street scene)
  * scene_street() ..... what is placed where; the "INTERIOR" block = flat ground details,
                         the "PADDING" block = tall props. place_pad() refuses to put a
                         prop inside the walkable square.
  * object functions ... school_bus_h(), wreck_car_h(), fence_h(), dead_tree(), ...
"""
import json
import os
import random
import sys

import numpy as np
from PIL import Image

S = 4
W, H = 480, 270                      # logical canvas -> 1920 x 1080
PAD = 0.10                           # padding on every side (fraction of width / height)
WX0, WX1 = round(W * PAD), W - round(W * PAD)          # walkable square, logical px
WY0, WY1 = round(H * PAD), H - round(H * PAD)
SHADE_BAND = 10                      # width (logical px) of the dither fade into the dark padding

_args = [a for a in sys.argv[1:]]
OUT = _args[0] if _args and not _args[0].startswith("street") else \
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "backgrounds")

(OUTLINE, ASPH_DARK, ASPH_MID, ASPH_LIGHT, PAVE_DARK, PAVE_MID, PAVE_LIGHT,
 YELLOW, YELLOW_DARK, WHITE, BRICK_DARK, BRICK_MID, BRICK_LIGHT, TAN_DARK, TAN_MID,
 TAN_LIGHT, ROOF_DARK, ROOF_MID, ROOF_LIGHT, GLASS_DARK, GLASS_MID, GLASS_LIGHT,
 RED, RED_DARK, GREEN_DARK, GREEN_MID, GREEN_LIGHT, TRUNK, TIRE, ZSKIN_DARK,
 ZSKIN_MID, ORANGE, SLIME, SLIME_DARK, RUST, RUST_DARK, WOOD, WOOD_DARK, BONE,
 SMOKE, SOOT, WEED, FLAME_Y, FLAME_O, FLAME_R, DIRT, TEAL_DARK, TEAL_MID, TEAL_LIGHT, CREAM, RED_LIGHT, PINK,
 PINK_DARK, CYAN, CYAN_DARK, BLUE_MID, BLUE_DARK) = range(1, 58)

PAL = {
    OUTLINE: (22, 16, 26),
    ASPH_DARK: (44, 46, 56), ASPH_MID: (62, 64, 74), ASPH_LIGHT: (82, 84, 92),
    PAVE_DARK: (96, 94, 100), PAVE_MID: (128, 126, 130), PAVE_LIGHT: (160, 156, 158),
    YELLOW: (232, 190, 52), YELLOW_DARK: (176, 130, 38), WHITE: (232, 228, 214),
    BRICK_DARK: (88, 46, 48), BRICK_MID: (130, 70, 60), BRICK_LIGHT: (162, 92, 72),
    TAN_DARK: (104, 90, 72), TAN_MID: (148, 128, 98), TAN_LIGHT: (184, 160, 120),
    ROOF_DARK: (58, 60, 70), ROOF_MID: (88, 90, 100), ROOF_LIGHT: (122, 124, 134),
    GLASS_DARK: (26, 34, 50), GLASS_MID: (64, 100, 120), GLASS_LIGHT: (140, 176, 190),
    RED: (190, 52, 48), RED_DARK: (120, 32, 40),
    GREEN_DARK: (34, 70, 48), GREEN_MID: (56, 104, 62), GREEN_LIGHT: (100, 140, 80),
    TRUNK: (74, 52, 40), TIRE: (26, 24, 32),
    ZSKIN_DARK: (70, 104, 70), ZSKIN_MID: (108, 150, 94), ORANGE: (232, 120, 36),
    SLIME: (132, 230, 74), SLIME_DARK: (70, 150, 56),              # toxic goo (not gore)
    RUST: (140, 82, 48), RUST_DARK: (92, 52, 36), WOOD: (122, 88, 58), WOOD_DARK: (80, 56, 40),
    BONE: (226, 218, 190), SMOKE: (84, 80, 92), SOOT: (34, 30, 38), WEED: (116, 118, 58),
    FLAME_Y: (255, 226, 96), FLAME_O: (255, 148, 40), FLAME_R: (222, 60, 36),
    DIRT: (96, 76, 60),
    TEAL_DARK: (34, 78, 84), TEAL_MID: (54, 118, 122), TEAL_LIGHT: (104, 170, 162),
    CREAM: (214, 204, 172), RED_LIGHT: (222, 132, 120),
    PINK: (236, 150, 176), PINK_DARK: (190, 90, 124),
    CYAN: (90, 200, 220), CYAN_DARK: (46, 130, 160),
    BLUE_MID: (62, 90, 150), BLUE_DARK: (36, 52, 100),
}
EXEMPT = {FLAME_Y, FLAME_O, FLAME_R}          # fire stays bright inside the dark padding
SHADE = 64                                    # index offset of the darkened copy of a colour
LUT = np.zeros((2 * SHADE, 4), dtype=np.uint8)
for _k, _v in PAL.items():
    LUT[_k] = (*_v, 255)
    LUT[_k + SHADE] = (int(_v[0] * .52 + 6), int(_v[1] * .50 + 4), int(_v[2] * .62 + 14), 255)


class C:
    """Indexed-colour pixel canvas (0 = transparent)."""

    def __init__(s, w, h, fill=0):
        s.w, s.h = w, h
        s.a = np.full((h, w), fill, dtype=np.uint8)

    def set(s, x, y, c):
        if 0 <= x < s.w and 0 <= y < s.h:
            s.a[y, x] = c

    def get(s, x, y):
        return int(s.a[y, x]) if 0 <= x < s.w and 0 <= y < s.h else 0

    def rect(s, x, y, w, h, c):
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, s.w), min(y + h, s.h)
        if x1 > x0 and y1 > y0:
            s.a[y0:y1, x0:x1] = c

    def ell(s, cx, cy, rx, ry, c):
        for y in range(int(cy - ry - 1), int(cy + ry + 2)):
            for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                if ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1:
                    s.set(x, y, c)

    def disk(s, cx, cy, r, c):
        s.ell(cx, cy, r, r, c)

    def paste(s, o, x, y):
        for j in range(o.h):
            for i in range(o.w):
                v = o.a[j, i]
                if v:
                    s.set(x + i, y + j, v)

    def outline_pad(s):
        big = C(s.w + 2, s.h + 2)
        big.a[1:-1, 1:-1] = s.a
        m = big.a != 0
        p = np.pad(m, 1)
        near = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
        big.a[(~m) & near] = OUTLINE
        return big

    def image(s, scale=S):
        return Image.fromarray(LUT[s.a], "RGBA").resize((s.w * scale, s.h * scale), Image.NEAREST)


def noise(x, y):
    n = (x * 73856093) ^ (y * 19349663)
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return (n >> 16) & 0xFF


def line(c, x0, y0, x1, y1, col):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        c.set(x0, y0, col)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


# ---- tiny 3x5 font ---------------------------------------------------------------
FONT = {
    "A": (".#.", "#.#", "###", "#.#", "#.#"), "B": ("##.", "#.#", "##.", "#.#", "##."),
    "C": (".##", "#..", "#..", "#..", ".##"), "D": ("##.", "#.#", "#.#", "#.#", "##."),
    "E": ("###", "#..", "##.", "#..", "###"), "F": ("###", "#..", "##.", "#..", "#.."),
    "G": (".##", "#..", "#.#", "#.#", ".##"), "H": ("#.#", "#.#", "###", "#.#", "#.#"),
    "I": ("###", ".#.", ".#.", ".#.", "###"), "K": ("#.#", "#.#", "##.", "#.#", "#.#"),
    "L": ("#..", "#..", "#..", "#..", "###"), "M": ("#.#", "###", "###", "#.#", "#.#"),
    "N": ("##.", "#.#", "#.#", "#.#", "#.#"), "O": (".#.", "#.#", "#.#", "#.#", ".#."),
    "P": ("##.", "#.#", "##.", "#..", "#.."), "R": ("##.", "#.#", "##.", "#.#", "#.#"),
    "S": (".##", "#..", ".#.", "..#", "##."), "T": ("###", ".#.", ".#.", ".#.", ".#."),
    "U": ("#.#", "#.#", "#.#", "#.#", "###"), "X": ("#.#", "#.#", ".#.", "#.#", "#.#"),
    "Z": ("###", "..#", ".#.", "#..", "###"), "Y": ("#.#", "#.#", ".#.", ".#.", ".#."),
    "V": ("#.#", "#.#", "#.#", "#.#", ".#."), "W": ("#.#", "#.#", "###", "###", "#.#"),
    "J": ("..#", "..#", "..#", "#.#", ".#."), "-": ("...", "...", "###", "...", "..."), " ": ("...", "...", "...", "...", "..."),
}


def text(c, x, y, s, col, k=1):
    for ch in s:
        for j, row in enumerate(FONT[ch]):
            for i, v in enumerate(row):
                if v == "#":
                    c.rect(x + i * k, y + j * k, k, k, col)
        x += 4 * k


def text_w(s, k=1):
    return (len(s) * 4 - 1) * k


def sign_plate(s, bg, fg, border):
    c = C(text_w(s) + 6, 9, bg)
    c.rect(0, 0, c.w, 1, border)
    c.rect(0, c.h - 1, c.w, 1, border)
    c.rect(0, 0, 1, c.h, border)
    c.rect(c.w - 1, 0, 1, c.h, border)
    text(c, 3, 2, s, fg)
    return c.outline_pad()


# ======================================================================================
# TALL PROPS - only ever placed in the padding (never inside the walkable square)
# ======================================================================================
def flame(c, cx, base, h, seed=0):
    for i in range(h):
        sway = round(1.6 * np.sin(i * .8 + seed))
        wdt = max(1, round((1 - i / h) ** .8 * 4))
        y = base - i
        c.rect(cx + sway - wdt, y, 2 * wdt + 1, 1, FLAME_R)
        if i < h * .78 and wdt > 1:
            c.rect(cx + sway - wdt + 1, y, 2 * wdt - 1, 1, FLAME_O)
        if i < h * .45 and wdt > 1:
            c.rect(cx + sway - wdt + 2, y, max(1, 2 * wdt - 3), 1, FLAME_Y)


def smoke(c, x, y, n=3, r=3):
    for i in range(n):
        c.disk(x + (i % 2) * 2, y - i * r * 1.3, r + (i % 2) * .6 - i * .2, SMOKE)


def with_fire(obj, flames, extra=20, smokes=True):
    """Return obj with flames (list of (x, height)) and smoke on top of it."""
    c = C(obj.w, obj.h + extra)
    c.paste(obj, 0, extra)
    for k, (fx, fh) in enumerate(flames):
        flame(c, fx, extra + 3, fh, k * 2)
    if smokes:
        smoke(c, flames[0][0] - 1, extra - flames[0][1] + 2, 2, 3)
    return c


def school_bus_h():
    c = C(74, 26)
    c.rect(1, 1, 72, 9, YELLOW)                              # roof
    c.rect(1, 1, 72, 1, TAN_LIGHT)
    c.rect(6, 4, 8, 3, ROOF_LIGHT)
    c.rect(36, 4, 6, 3, ROOF_LIGHT)
    c.rect(0, 10, 73, 12, YELLOW)                            # side wall
    c.rect(0, 10, 73, 1, TAN_LIGHT)
    c.rect(0, 17, 73, 1, TIRE)
    c.rect(0, 20, 73, 1, TIRE)
    for i, x in enumerate(range(5, 58, 8)):
        c.rect(x, 11, 6, 5, GLASS_DARK)                      # windows
        c.set(x + 1, 12, GLASS_LIGHT)
        c.set(x + 3 + i % 2, 14, GLASS_MID)
    c.rect(29, 11, 6, 5, GLASS_DARK)                         # a passenger looks out
    c.rect(30, 12, 4, 4, ZSKIN_MID)
    c.set(30, 13, TIRE)
    c.set(33, 13, TIRE)
    c.rect(31, 15, 2, 1, TIRE)
    c.rect(62, 11, 8, 10, GLASS_DARK)                        # door
    c.rect(66, 11, 1, 10, YELLOW_DARK)
    for (x, y, w, h) in ((12, 18, 5, 2), (44, 12, 3, 2), (24, 19, 4, 2), (70, 19, 3, 3)):
        c.rect(x, y, w, h, RUST)                             # rust / dents
    c.rect(0, 12, 3, 8, SOOT)
    for x in (9, 53):
        c.rect(x, 21, 9, 5, TIRE)
        c.rect(x + 3, 22, 3, 3, ROOF_LIGHT)
    c.rect(53, 21, 9, 3, TIRE)                               # flat tyre
    c.rect(55, 22, 5, 1, ROOF_MID)
    return c.outline_pad()


def school_bus_v():
    c = C(26, 78)
    c.rect(1, 1, 24, 62, YELLOW)                             # roof
    c.rect(1, 1, 1, 62, TAN_LIGHT)
    c.rect(24, 1, 1, 62, YELLOW_DARK)
    for y in (6, 20, 40):
        c.rect(8, y, 10, 4, ROOF_LIGHT)
    c.rect(1, 62, 24, 14, YELLOW)                            # rear face
    c.rect(3, 64, 20, 6, GLASS_DARK)
    c.set(5, 65, GLASS_LIGHT)
    c.rect(12, 64, 1, 6, YELLOW_DARK)
    c.rect(3, 72, 4, 2, RED)
    c.rect(19, 72, 4, 2, RED)
    c.rect(10, 73, 6, 2, WHITE)
    c.rect(1, 58, 24, 1, TIRE)
    c.rect(5, 10, 5, 3, RUST)
    c.rect(15, 44, 4, 3, RUST)
    c.rect(1, 1, 24, 4, SOOT)
    for y in (48, 68):
        c.rect(0, y - 6, 2, 7, TIRE)
        c.rect(24, y - 6, 2, 7, TIRE)
    return c.outline_pad()


def car_h(body, body_d, body_l, flip=False):
    c = C(34, 18)
    c.rect(1, 1, 31, 9, body_l)
    c.rect(1, 1, 31, 1, body)
    c.rect(9, 2, 13, 7, GLASS_MID)
    c.rect(9, 2, 13, 2, GLASS_LIGHT)
    c.rect(14, 2, 3, 7, body)
    c.rect(0, 10, 33, 5, body)
    c.rect(0, 10, 33, 1, body_l)
    c.rect(0, 14, 33, 1, body_d)
    c.rect(11, 11, 5, 3, GLASS_DARK)
    c.rect(18, 11, 5, 3, GLASS_DARK)
    c.rect(30, 11, 3, 2, YELLOW)
    c.rect(0, 11, 2, 2, RED)
    for wx in (4, 24):
        c.rect(wx, 14, 6, 4, TIRE)
        c.rect(wx + 2, 15, 2, 2, ROOF_LIGHT)
    c = c.outline_pad()
    if flip:
        c.a = c.a[:, ::-1].copy()
    return c


def wreck_car_h(seed=0, flip=False):
    """Rusty abandoned car: smashed windows, soot, a missing wheel, a dented roof."""
    pal = ((RUST, RUST_DARK, TAN_DARK), (BRICK_MID, BRICK_DARK, RUST), (ROOF_MID, ROOF_DARK, ROOF_LIGHT))
    c = car_h(*pal[seed % 3], flip=False)
    for y in range(c.h):
        for x in range(c.w):
            v = c.a[y, x]
            if v in (GLASS_MID, GLASS_LIGHT):
                c.a[y, x] = GLASS_DARK if (x + y + seed) % 3 else GLASS_LIGHT
            elif v == YELLOW:
                c.a[y, x] = TIRE
            elif v in (RUST, BRICK_MID, ROOF_MID) and noise(x + seed, y) < 40:
                c.a[y, x] = SOOT
    c.rect(26, 15, 7, 4, 0)                                  # missing wheel
    c.rect(26, 17, 8, 2, OUTLINE)
    line(c, 12, 4, 16, 8, GLASS_LIGHT)                       # cracked screen
    line(c, 20, 3, 17, 8, GLASS_LIGHT)
    if flip:
        c.a = c.a[:, ::-1].copy()
    return c


def wreck_car_v(seed=0):
    pal = ((RUST, RUST_DARK, TAN_DARK), (BRICK_MID, BRICK_DARK, RUST))
    body, body_d, body_l = pal[seed % 2]
    c = C(18, 36)
    c.rect(1, 1, 16, 26, body_l)
    c.rect(1, 1, 1, 26, body)
    c.rect(3, 4, 12, 5, GLASS_DARK)
    line(c, 4, 4, 8, 8, GLASS_LIGHT)
    c.rect(3, 16, 12, 4, GLASS_DARK)
    c.rect(3, 10, 12, 6, body)
    c.rect(1, 27, 16, 6, body)
    c.rect(1, 32, 16, 1, body_d)
    c.rect(3, 28, 3, 2, SOOT)
    c.rect(12, 28, 3, 2, RED_DARK)
    c.rect(6, 30, 6, 2, WHITE)
    c.rect(2, 1, 6, 5, SOOT)
    for wx in (0, 15):
        c.rect(wx, 22, 3, 5, TIRE)
    c.rect(15, 31, 3, 4, TIRE)                               # one wheel missing
    return c.outline_pad()


def jersey_barrier():
    c = C(14, 9)
    c.rect(1, 0, 12, 8, PAVE_MID)
    c.rect(0, 5, 14, 3, PAVE_MID)
    c.rect(1, 0, 12, 1, PAVE_LIGHT)
    for x in range(1, 13):
        if (x // 2) % 2:
            c.rect(x, 2, 1, 3, YELLOW)
        else:
            c.rect(x, 2, 1, 3, TIRE)
    c.rect(0, 7, 14, 1, PAVE_DARK)
    return c.outline_pad()


def sandbags(n=5, rows=2):
    c = C(n * 6 + 2, rows * 4 + 2)
    for r in range(rows):
        for i in range(n - r):
            x, y = 1 + i * 6 + r * 3, 1 + r * 4
            c.rect(x, y, 6, 4, TAN_MID)
            c.rect(x, y, 6, 1, TAN_LIGHT)
            c.rect(x, y + 3, 6, 1, TAN_DARK)
            c.set(x + 5, y + 1, TAN_DARK)
    return c.outline_pad()


def fence_h(w, seed=0, wire=True):
    """Chain-link fence along the x direction (mesh only, no outline)."""
    c = C(w, 14)
    for x in range(0, w, 14):
        c.rect(x, 1, 3, 13, ROOF_MID)
        c.rect(x, 1, 1, 13, ROOF_LIGHT)
    c.rect(0, 1, w, 1, ROOF_LIGHT)
    c.rect(0, 12, w, 1, ROOF_MID)
    for y in range(2, 12):
        for x in range(w):
            if (x + y) % 2 == 0 and noise(x + seed, y) > 30:
                c.set(x, y, ROOF_LIGHT)
    if wire:
        for x in range(0, w):
            c.set(x, 0 if x % 4 < 2 else 1, TIRE if x % 2 else ROOF_DARK)
    return c


def fence_v(h, seed=0):
    c = C(7, h)
    for y in range(0, h, 14):
        c.rect(2, y, 3, 3, ROOF_MID)
        c.rect(2, y, 1, 3, ROOF_LIGHT)
    c.rect(2, 0, 1, h, ROOF_LIGHT)
    c.rect(4, 0, 1, h, ROOF_DARK)
    for y in range(h):
        if noise(seed, y) > 40:
            c.set(3 if y % 2 else 1, y, ROOF_LIGHT)
            c.set(5 if y % 2 else 6, y, ROOF_MID)
            c.set(3, y, ROOF_LIGHT)
    return c


def hazard_tape(w):
    c = C(w, 3)
    for x in range(w):
        for y in range(3):
            c.set(x, y, YELLOW if ((x + y) // 3) % 2 == 0 else TIRE)
    return c


def dead_tree(h=40, seed=0):
    rng = random.Random(seed)
    c = C(30, h)
    tx, ty = 15, h - 2
    c.rect(tx - 2, ty - h // 2, 4, h // 2 + 1, TRUNK)
    c.rect(tx - 2, ty - h // 2, 1, h // 2 + 1, TAN_DARK)
    c.rect(tx - 4, ty - 1, 8, 2, TRUNK)
    top = ty - h // 2
    for k in range(5):
        ex = rng.choice((-12, -9, -6, 6, 9, 12, 0 + rng.choice((-3, 3))))
        ey = top - rng.randint(6, 14)
        line(c, tx, top + 3, tx + ex, max(1, ey), TRUNK)
        line(c, tx + 1, top + 3, tx + ex + 1, max(1, ey), TRUNK)
        mx, my = tx + ex // 2, (top + 3 + max(1, ey)) // 2
        line(c, mx, my, mx + (4 if ex > 0 else -4), my - 4, TRUNK)
    for _ in range(6):
        c.set(rng.randint(3, 26), rng.randint(2, top), RUST)
    return c.outline_pad()


def barrel_fire():
    c = C(10, 13)
    c.rect(1, 2, 8, 10, RUST)
    c.rect(1, 2, 2, 10, TAN_DARK)
    c.rect(0, 5, 10, 1, RUST_DARK)
    c.rect(0, 9, 10, 1, RUST_DARK)
    c.rect(1, 1, 8, 2, SOOT)
    return with_fire(c.outline_pad(), [(6, 8)], extra=12, smokes=True)


def rubble(w, h, seed=0):
    rng = random.Random(seed)
    c = C(w, h)
    cols = (ROOF_MID, ROOF_DARK, ROOF_LIGHT, BRICK_MID, BRICK_DARK, TAN_MID)
    for _ in range(w * h // 9):
        x = rng.randint(2, w - 3)
        y = rng.randint(h // 2 - int(abs(x - w / 2) / (w / 2) * h * .4), h - 3)
        c.disk(x, y, rng.choice((1.5, 2, 2.5, 3)), rng.choice(cols))
    for _ in range(3):
        x = rng.randint(3, w - 4)
        line(c, x, h // 2 + 2, x + rng.choice((-3, 3)), h // 2 - 4, RUST)      # bent rebar
    return c.outline_pad()


def window(w, h, mode="ok"):
    c = C(w, h, GLASS_MID)
    for y in range(h):
        for x in range(w):
            if y > h - 4:
                c.set(x, y, GLASS_DARK)
            elif 2 < x + y < 7 or 10 < x + y < 12:
                c.set(x, y, GLASS_LIGHT)
    if mode == "broken":
        for y in range(h):
            for x in range(w):
                if noise(x * 5, y * 3) < 110 and 3 < x < w - 3:
                    c.set(x, y, GLASS_DARK)
        line(c, 2, 1, 7, 6, GLASS_LIGHT)
        line(c, w - 3, 1, w - 8, 5, GLASS_LIGHT)
    elif mode == "fire":
        c.rect(1, 1, w - 2, h - 2, FLAME_R)
        c.rect(2, 4, w - 4, h - 5, FLAME_O)
        c.rect(4, 7, w - 8, h - 8, FLAME_Y)
        for x in range(2, w - 2, 3):
            c.rect(x, 1, 1, 4, FLAME_O)
    elif mode == "boards":
        c.rect(0, 0, w, h, GLASS_DARK)
        for y, dx in ((1, 0), (5, 1), (9, 0)):
            c.rect(-1 + dx, y, w + 2, 3, WOOD)
            c.rect(-1 + dx, y, w + 2, 1, TAN_MID)
            c.set(1, y + 1, TIRE)
            c.set(w - 2, y + 1, TIRE)
    c.rect(0, 0, w, 1, WHITE)
    c.rect(0, 0, 1, h, WHITE)
    c.rect(w - 1, 0, 1, h, WHITE)
    c.rect(0, h - 1, w, 1, WHITE)
    return c.outline_pad()


def boarded_door(w, h):
    c = C(w, h, WOOD_DARK)
    for y in range(1, h, 4):
        c.rect(0, y, w, 3, WOOD)
        c.rect(0, y, w, 1, TAN_MID)
    line(c, 1, 2, w - 2, h - 3, WOOD_DARK)
    line(c, w - 2, 2, 1, h - 3, WOOD_DARK)
    c.set(3, 3, TIRE)
    c.set(w - 4, h - 4, TIRE)
    return c.outline_pad()


def building_wall(c, x, w, palette, name, graffiti, glow_windows=(), seed=0):
    """Ruined storefront: wall rows 0..WY0-1 (the part of the building we can see)."""
    rng = random.Random(seed)
    dk, md, lt = palette
    h = WY0
    c.rect(x, 0, w, h, md)
    for yy in range(h):
        if yy % 4 == 3:
            c.rect(x, yy, w, 1, dk)
        else:
            for xx in range(w):
                if (xx + (yy // 4) * 4) % 8 == 0:
                    c.set(x + xx, yy, dk)
    c.rect(x, h - 3, w, 3, dk)
    for _ in range(14):                                          # missing bricks / soot streaks
        px, py = x + rng.randint(2, w - 8), rng.randint(0, h - 8)
        c.rect(px, py, rng.randint(2, 5), rng.randint(2, 3), ROOF_DARK if rng.random() < .5 else SOOT)
    for _ in range(6):
        sx = x + rng.randint(4, w - 6)
        c.rect(sx, 0, 2, rng.randint(8, 16), SOOT)
    cxm = x + w // 2
    pl = sign_plate(name, RED_DARK, WHITE, YELLOW_DARK)
    c.paste(pl, cxm - pl.w // 2, 0)
    modes = ["broken", "boards", "ok", "broken", "boards", "broken"]
    for i, dxw in enumerate((-86, -58, 38, 66)):
        mode = "fire" if i in glow_windows else modes[(i + seed) % len(modes)]
        c.paste(window(20, 14, mode), cxm + dxw - 2, 6)
    c.paste(boarded_door(16, 16), cxm - 8, h - 16)
    for (gx, gtxt) in graffiti:
        text(c, x + gx, 8, gtxt, SLIME, 2)


# ======================================================================================
# FLAT GROUND DETAILS - these go inside the walkable square (they never block anything)
# ======================================================================================
def crack(c, x, y, n, rng, col, vertical=False, weeds=True):
    dx, dy = (0, 1) if vertical else (1, 0)
    for _ in range(n):
        c.set(x, y, col)
        r = rng.random()
        if r < .55:
            x, y = x + dx, y + dy
        elif r < .8:
            x, y = x + dx + dy, y + dy + dx
        else:
            x, y = x + dx - dy, y + dy - dx
        if weeds and rng.random() < .05:
            c.set(x, y - 1, WEED)
            c.set(x, y - 2, WEED)
        if rng.random() < .04 and n > 6:
            crack(c, x, y, n // 3, rng, col, not vertical, weeds)


def pothole(c, x, y, rx, ry):
    c.ell(x, y, rx + 1, ry + 1, ASPH_LIGHT)
    c.ell(x, y, rx, ry, ASPH_DARK)
    c.ell(x + .5, y + .5, rx - 1.5, ry - .8, SOOT)


def slime(c, x, y, rx, ry, rng):
    c.ell(x, y, rx, ry, SLIME_DARK)
    c.ell(x - .6, y - .4, rx - 1.6, ry - 1, SLIME)
    c.set(int(x - rx * .4), int(y - ry * .4), WHITE)
    c.set(int(x - rx * .4) + 1, int(y - ry * .4), WHITE)
    for _ in range(int(rx * 1.2)):
        c.set(int(x + rng.uniform(-rx - 3, rx + 3)), int(y + rng.uniform(-ry - 2, ry + 2)), SLIME_DARK)


def footprints(c, x, y, n, dx, dy=0):
    for i in range(n):
        px, py = x + i * dx, y + i * dy + (2 if i % 2 else -2)
        c.rect(px, py, 3, 2, SLIME_DARK)
        c.set(px, py, SLIME)


def scorch(c, x, y, rx, ry):
    c.ell(x, y, rx, ry, ASPH_DARK)
    for yy in range(int(y - ry), int(y + ry) + 1):
        for xx in range(int(x - rx), int(x + rx) + 1):
            if ((xx - x) / rx) ** 2 + ((yy - y) / ry) ** 2 < .7 and noise(xx, yy) > 60:
                c.set(xx, yy, SOOT)


def skull(c, x, y):
    for j, row in enumerate((".BBB.", "BBBBB", "B#B#B", ".BBB.", ".B#B.")):
        for i, v in enumerate(row):
            if v != ".":
                c.set(x + i, y + j, BONE if v == "B" else TIRE)


def bone(c, x, y):
    c.rect(x + 1, y + 1, 6, 1, BONE)
    for (i, j) in ((0, 0), (0, 2), (7, 0), (7, 2)):
        c.set(x + i, y + j, BONE)


def chalk_body(c, x, y):
    for a in range(0, 360, 20):
        c.set(round(x + 3 * np.cos(np.radians(a))), round(y + 3 * np.sin(np.radians(a))), WHITE)
    for (x0, y0, x1, y1) in ((5, -3, 15, -3), (5, 3, 15, 3), (5, -3, 5, 3), (15, -3, 15, 3),
                             (7, -3, 10, -8), (7, 3, 11, 8), (15, -2, 23, -5), (15, 2, 23, 5)):
        line(c, x + x0, y + y0, x + x1, y + y1, WHITE)


def crater(c, x, y, rx, ry, rng):
    c.ell(x, y, rx + 3, ry + 2, DIRT)
    c.ell(x, y, rx + 1, ry + 1, TRUNK)
    c.ell(x, y, rx, ry, SOOT)
    c.ell(x - 1, y - 1, rx - 4, ry - 2, TIRE)
    for _ in range(26):
        a = rng.uniform(0, 6.28)
        r = rng.uniform(1.0, 1.25)
        c.rect(int(x + np.cos(a) * (rx + 3) * r), int(y + np.sin(a) * (ry + 2) * r), 2, 1,
               rng.choice((ROOF_MID, BRICK_DARK, ROOF_LIGHT, DIRT)))
    for k in range(3):
        line(c, int(x - rx - 2 + k * 3), int(y - ry - 2), int(x - rx - 5 + k * 3), int(y - ry - 6), RUST)


def small_items(c):
    """Flat litter: banana, pizza box, skateboard, lost shoe, fallen sign."""
    for (x, y) in ((214, 150),):
        for dx, dy in ((0, 2), (1, 3), (2, 3), (3, 3), (4, 3), (5, 2), (6, 1)):
            c.set(x + dx, y + dy, YELLOW)
        c.set(x + 6, y, TRUNK)
    c.rect(318, 66, 9, 7, TAN_LIGHT)                                  # pizza box
    c.rect(318, 66, 9, 1, TAN_MID)
    c.rect(321, 68, 3, 3, RED)
    c.rect(318, 72, 9, 1, TAN_DARK)
    c.rect(312, 194, 14, 4, RED)                                      # skateboard
    c.rect(312, 194, 14, 1, WHITE)
    for wx in (314, 322):
        c.rect(wx, 198, 2, 1, TIRE)
    c.rect(66, 84, 6, 3, TRUNK)                                       # lone shoe
    c.rect(66, 84, 2, 1, TAN_MID)
    c.rect(114, 52, 3, 1, ROOF_MID)                                   # sign pole
    c.rect(114, 52, 22, 2, ROOF_MID)
    pl = sign_plate("ZOMBIE XING", YELLOW, TIRE, YELLOW_DARK)
    c.paste(pl, 124, 48)


def worn(layer, canvas):
    """Composite a marking layer with chipped-away pixels."""
    for y in range(layer.h):
        for x in range(layer.w):
            v = layer.a[y, x]
            if v and noise((x // 2) * 3 + 11, (y // 2) * 5 + 7) > 14:
                canvas.set(x, y, v)


# ======================================================================================
# SCENE: street intersection
# ======================================================================================
ROAD_H = (96, 170)        # y-range of the horizontal road
ROAD_V = (205, 275)       # x-range of the vertical road
CORNER_R = 6


def asphalt(x, y):
    n = noise(x, y)
    return ASPH_DARK if n < 9 else ASPH_LIGHT if n < 17 else ASPH_MID


def draw_ground(c):
    c.rect(0, 0, W, H, PAVE_MID)
    for y in range(H):
        for x in range(W):
            if y % 8 == 0 or (x + (y // 8) * 6) % 12 == 0:
                c.set(x, y, PAVE_DARK)
            elif noise(x, y) < 5:
                c.set(x, y, PAVE_LIGHT)
    for (x0, x1, y0, y1) in ((0, W, ROAD_H[0], ROAD_H[1]), (ROAD_V[0], ROAD_V[1], 0, H)):
        for y in range(y0, y1):
            for x in range(x0, x1):
                c.set(x, y, asphalt(x, y))
    r = CORNER_R
    for (cx, cy, sx, sy) in ((ROAD_V[0], ROAD_H[0], -1, -1), (ROAD_V[1], ROAD_H[0], 1, -1),
                             (ROAD_V[0], ROAD_H[1], -1, 1), (ROAD_V[1], ROAD_H[1], 1, 1)):
        ox, oy = cx + sx * r, cy + sy * r
        for j in range(r):
            for i in range(r):
                x = cx - 1 - i if sx < 0 else cx + i
                y = cy - 1 - j if sy < 0 else cy + j
                if (x + .5 - ox) ** 2 + (y + .5 - oy) ** 2 > r * r:
                    c.set(x, y, asphalt(x, y))
    x0, x1 = ROAD_V
    y0, y1 = ROAD_H
    for (a, b, y) in ((0, x0 - r, y0 - 1), (x1 + r, W, y0 - 1), (0, x0 - r, y1), (x1 + r, W, y1)):
        c.rect(a, y, b - a, 1, PAVE_LIGHT)
    for (x, a, b) in ((x0 - 1, 0, y0 - r), (x0 - 1, y1 + r, H), (x1, 0, y0 - r), (x1, y1 + r, H)):
        c.rect(x, a, 1, b - a, PAVE_LIGHT)


def draw_markings(c):
    m = C(W, H)
    y0, y1 = ROAD_H
    x0, x1 = ROAD_V
    cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
    zx = 22
    for x in list(range(0, x0 - zx - 6)) + list(range(x1 + zx + 6, W)):
        m.set(x, cy - 1, YELLOW)
        m.set(x, cy + 1, YELLOW)
    for y in list(range(0, y0 - 18)) + list(range(y1 + 18, H)):
        m.set(cx - 1, y, YELLOW)
        m.set(cx + 1, y, YELLOW)
    for lane in (y0 + 17, y1 - 17):
        for x in range(W):
            if (x // 10) % 2 == 0 and not (x0 - zx - 6 < x < x1 + zx + 6):
                m.set(x, lane, WHITE)
    for lane in (x0 + 17, x1 - 17):
        for y in range(H):
            if (y // 8) % 2 == 0 and not (y0 - 18 < y < y1 + 18):
                m.set(lane, y, WHITE)
    for k in range(y0 + 3, y1 - 3, 6):
        m.rect(x0 - zx, k, 14, 3, WHITE)
        m.rect(x1 + zx - 14, k, 14, 3, WHITE)
    for k in range(x0 + 3, x1 - 3, 6):
        m.rect(k, y0 - 18, 3, 12, WHITE)
        m.rect(k, y1 + 6, 3, 12, WHITE)
    m.rect(x0 - zx - 4, y0 + 2, 2, (y1 - y0) // 2 - 2, WHITE)
    m.rect(x1 + zx + 2, cy + 2, 2, (y1 - y0) // 2 - 3, WHITE)
    m.rect(x0 + 2, y0 - 22, (x1 - x0) // 2 - 3, 2, WHITE)
    m.rect(cx + 3, y1 + 20, (x1 - x0) // 2 - 4, 2, WHITE)
    worn(m, c)


def place_pad(c, obj, x, y, what=""):
    """Paste a tall prop, but only if it stays out of the walkable square."""
    if x < WX1 and x + obj.w > WX0 and y < WY1 and y + obj.h > WY0:
        raise ValueError("prop %s at %d,%d (%dx%d) intrudes into the walkable square"
                         % (what, x, y, obj.w, obj.h))
    c.paste(obj, x, y)


def scene_street():
    rng = random.Random(7)
    c = C(W, H)
    draw_ground(c)
    draw_markings(c)

    # ---------------------------------------------------------- INTERIOR (flat only)
    for (x, y, n, v, col) in ((60, 125, 40, 0, ASPH_DARK), (330, 150, 36, 0, ASPH_DARK),
                              (230, 60, 30, 1, PAVE_DARK), (252, 214, 34, 1, ASPH_DARK),
                              (90, 34, 38, 0, PAVE_DARK), (380, 38, 30, 0, PAVE_DARK),
                              (70, 190, 34, 0, PAVE_DARK), (390, 220, 32, 0, PAVE_DARK),
                              (140, 100, 26, 0, ASPH_DARK), (310, 105, 24, 0, ASPH_DARK),
                              (120, 160, 28, 0, ASPH_DARK), (420, 125, 14, 0, ASPH_DARK),
                              (160, 215, 30, 0, PAVE_DARK), (330, 80, 24, 1, PAVE_DARK)):
        crack(c, x, y, n, rng, col, bool(v))
    for (x, y, rx, ry) in ((130, 121, 5, 3), (333, 150, 6, 3), (404, 112, 4, 2), (172, 154, 4, 2)):
        pothole(c, x, y, rx, ry)
    # skid marks swerving towards the top-left plaza
    for k in (0, 5):
        for t in range(0, 60):
            c.set(300 - t * 2 + 0, 150 + k - int(t * .25), ASPH_DARK)
            c.set(300 - t * 2 + 1, 150 + k - int(t * .25), ASPH_DARK)
    scorch(c, 350, 56, 13, 6)
    scorch(c, 244, 150, 9, 5)                                       # oil / burn at the junction
    crater(c, 112, 212, 15, 6, rng)
    chalk_body(c, 70, 58)
    slime(c, 160, 70, 8, 4, rng)
    slime(c, 400, 40, 7, 3, rng)
    slime(c, 352, 206, 15, 6, rng)
    slime(c, 262, 130, 6, 3, rng)
    footprints(c, 262, 162, 14, -7, -1)                                 # trail from the manhole
    footprints(c, 398, 46, 9, -4, 3)
    skull(c, 100, 38)
    bone(c, 108, 44)
    skull(c, 308, 200)
    bone(c, 330, 214)
    bone(c, 150, 190)
    skull(c, 382, 100)
    small_items(c)
    text(c, 74, 108, "RUN", SLIME, 3)
    text(c, 372, 84, "HELP", SLIME_DARK, 2)
    c.paste(manhole_obj(False), 214, 118)
    c.paste(manhole_obj(True), 254, 156)
    for _ in range(70):                                                # litter + pebbles
        x, y = rng.randint(WX0 + 2, WX1 - 4), rng.randint(WY0 + 2, WY1 - 4)
        if rng.random() < .5:
            c.rect(x, y, 2, 1, rng.choice((WHITE, TAN_LIGHT)))
        else:
            c.set(x, y, rng.choice((ROOF_LIGHT, ROOF_DARK, DIRT)))
    for _ in range(24):                                                # dead weeds in the joints
        x, y = rng.randint(WX0 + 2, WX1 - 4), rng.randint(WY0 + 4, WY1 - 4)
        if not (ROAD_H[0] < y < ROAD_H[1] or ROAD_V[0] < x < ROAD_V[1]):
            c.set(x, y, WEED)
            c.set(x, y - 1, WEED)
            c.set(x + 1, y - 2, WEED)

    # ----------------------------------------------------------- PADDING (tall props)
    xl, xr = ROAD_V
    # top: ruined shopfronts + a school bus across the road, smoke from the roofs
    building_wall(c, 6, xl - 12 - 6, (BRICK_DARK, BRICK_MID, BRICK_LIGHT), "PI ZA", [],
                  glow_windows=(1,), seed=1)
    building_wall(c, xr + 12, W - 6 - xr - 12, (TAN_DARK, TAN_MID, TAN_LIGHT), "BRAINS CAFE",
                  [], glow_windows=(2,), seed=4)
    c.rect(xl - 12, 0, xr - xl + 24, WY0, PAVE_MID)                       # road mouth ground
    for y in range(WY0):
        for x in range(xl, xr):
            c.set(x, y, asphalt(x, y))
    place_pad(c, school_bus_h(), 203, -1, "bus")
    smoke_layer = C(W, H)
    for (sx, sy) in ((60, 6), (120, 4), (370, 5), (430, 4)):
        smoke(smoke_layer, sx, sy + 6, 3, 3)
    c.paste(smoke_layer, 0, 0)

    # left: fence, wrecks and a bus across the road mouth
    c.rect(0, WY0, WX0, WY1 - WY0, DIRT)
    for _ in range(90):
        c.set(rng.randint(0, WX0 - 1), rng.randint(WY0, WY1 - 1), rng.choice((TRUNK, ROOF_DARK, PAVE_DARK)))
    c.rect(0, ROAD_H[0], WX0, ROAD_H[1] - ROAD_H[0], ASPH_MID)
    for y in range(ROAD_H[0], ROAD_H[1]):
        for x in range(0, WX0):
            c.set(x, y, asphalt(x, y))
    for (x, y0, y1) in ((41, WY0, ROAD_H[0] - 2), (41, ROAD_H[1] + 2, WY1)):
        c.paste(fence_v(y1 - y0, x), x, y0)
    place_pad(c, school_bus_v(), 8, 94, "bus L")
    place_pad(c, dead_tree(40, 1), 4, 50, "tree")
    place_pad(c, with_fire(wreck_car_v(0), [(9, 9)], extra=16), 14, 178, "wreck L")
    place_pad(c, rubble(26, 16, 3), 6, 36, "rubble")
    place_pad(c, rubble(28, 16, 5), 4, 160 + 0, "rubble")                  # near the bus
    place_pad(c, barrel_fire(), 28, 76, "barrel")
    place_pad(c, dead_tree(36, 4), 8, 222 - 12, "tree")

    # right: fence, burning pile-up across the road mouth
    c.rect(WX1, WY0, W - WX1, WY1 - WY0, DIRT)
    for _ in range(90):
        c.set(rng.randint(WX1, W - 1), rng.randint(WY0, WY1 - 1), rng.choice((TRUNK, ROOF_DARK, PAVE_DARK)))
    for y in range(ROAD_H[0], ROAD_H[1]):
        for x in range(WX1, W):
            c.set(x, y, asphalt(x, y))
    for (x, y0, y1) in ((WX1, WY0, ROAD_H[0] - 2), (WX1, ROAD_H[1] + 2, WY1)):
        c.paste(fence_v(y1 - y0, x + 3), x, y0)
    place_pad(c, wreck_car_h(1, flip=True), 442, 116, "wreck R1")
    place_pad(c, with_fire(wreck_car_h(2), [(10, 10), (22, 7)], extra=18), 436, 128, "wreck R2")
    place_pad(c, wreck_car_v(1), 448, 140, "wreck R3")
    place_pad(c, dead_tree(40, 2), 446, 44, "tree")
    place_pad(c, rubble(28, 16, 7), 448, 62, "rubble")
    place_pad(c, barrel_fire(), 440, 84, "barrel")
    place_pad(c, dead_tree(36, 6), 450, 196, "tree")
    place_pad(c, rubble(26, 16, 9), 450, 224, "rubble")
    place_pad(c, with_fire(wreck_car_v(0), [(9, 9)], extra=16), 454, 176, "wreck R4") \
        if False else None

    # bottom: fence line, rubble heaps and a barricade across the road
    c.rect(0, WY1, W, H - WY1, DIRT)
    for _ in range(300):
        c.set(rng.randint(0, W - 1), rng.randint(WY1, H - 1), rng.choice((TRUNK, ROOF_DARK, PAVE_DARK, WEED)))
    for (x0, x1) in ((WX0, xl), (xr, WX1)):
        place_pad(c, fence_h(x1 - x0, x0), x0, WY1 + 1, "fence")
    for y in range(WY1, H):
        for x in range(xl, xr):
            c.set(x, y, asphalt(x, y))
    for i in range(5):
        place_pad(c, jersey_barrier(), xl + 2 + i * 14, WY1 + 4, "barrier")
    place_pad(c, sandbags(10, 2), xl + 4, WY1 + 14, "sandbags")
    place_pad(c, hazard_tape(70), xl, WY1 + 2, "tape")
    place_pad(c, with_fire(wreck_car_h(0), [(14, 7)], extra=0, smokes=False)
              if False else wreck_car_h(0), 104, WY1 + 7, "wreck B1")
    place_pad(c, wreck_car_h(2, flip=True), 330, WY1 + 7, "wreck B2")
    place_pad(c, rubble(40, 14, 11), 160, WY1 + 14, "rubble B1")
    place_pad(c, rubble(36, 14, 12), 392, WY1 + 12, "rubble B2")
    place_pad(c, rubble(30, 12, 13), 54, WY1 + 14, "rubble B3")
    place_pad(c, sign_plate("KEEP OUT", RED_DARK, WHITE, WHITE), 380, WY1 + 2, "sign") \
        if False else None

    shade_padding(c)
    return c


def manhole_obj(hand):
    c = C(16, 12)
    c.disk(8, 7, 5.5, ROOF_DARK)
    c.disk(8, 7, 4, ROOF_MID)
    for i in (-3, 0, 3):
        c.rect(5, 7 + i, 7, 1, ROOF_DARK)
    if hand:
        c.disk(8, 7, 4, TIRE)
        c.rect(6, 1, 5, 7, ZSKIN_MID)
        c.rect(6, 1, 1, 7, ZSKIN_DARK)
        for x in (4, 6, 8, 10):
            c.rect(x, 0, 1, 2, ZSKIN_MID)
        c.rect(4, 2, 7, 3, ZSKIN_MID)
        c.rect(4, 4, 7, 1, ZSKIN_DARK)
    return c.outline_pad()


BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def shade_padding(c):
    """Darken everything outside the walkable square with an ordered-dither fade."""
    for y in range(H):
        for x in range(W):
            d = max(WX0 - x, x - (WX1 - 1), WY0 - y, y - (WY1 - 1), 0)
            if d == 0:
                continue
            t = min(16, d * 16 // SHADE_BAND + 1)
            if BAYER[y % 4][x % 4] < t:
                v = int(c.a[y, x])
                if v and v not in EXEMPT and v < SHADE:
                    c.a[y, x] = v + SHADE


# ======================================================================================
# SHARED HELPERS FOR THE OTHER SCENES
# ======================================================================================
def poly(c, pts, col):
    """Fill a polygon (even-odd scanline)."""
    ys = [p[1] for p in pts]
    n = len(pts)
    for y in range(int(min(ys)), int(max(ys)) + 1):
        xs = []
        for i in range(n):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            if (y0 <= y + .5 < y1) or (y1 <= y + .5 < y0):
                xs.append(x0 + (y + .5 - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for a, b in zip(xs[0::2], xs[1::2]):
            for x in range(int(round(a)), int(round(b))):
                c.set(x, y, col)


def ring(c, cx, cy, r, col, th=1):
    for y in range(int(cy - r - 2), int(cy + r + 3)):
        for x in range(int(cx - r - 2), int(cx + r + 3)):
            d = ((x + .5 - cx) ** 2 + (y + .5 - cy) ** 2) ** .5
            if r - th < d <= r:
                c.set(x, y, col)


def pad_rects():
    return [(0, 0, W, WY0), (0, WY0, WX0, WY1 - WY0), (WX1, WY0, W - WX1, WY1 - WY0),
            (0, WY1, W, H - WY1)]


def fill_padding(c, base, specks, rng, n=260):
    for (x, y, w, h) in pad_rects():
        c.rect(x, y, w, h, base)
        for _ in range(n * w * h // 10000):
            c.set(rng.randint(x, x + w - 1), rng.randint(y, y + h - 1), rng.choice(specks))


def flat_ground_details(c, rng, crack_col, ncr=12, litter=True):
    """Cracks, litter, pebbles and toxic goo shared by the interior of every scene."""
    for _ in range(ncr):
        crack(c, rng.randint(WX0 + 6, WX1 - 40), rng.randint(WY0 + 6, WY1 - 6),
              rng.randint(18, 40), rng, crack_col, rng.random() < .4, weeds=False)
    for _ in range(3):
        slime(c, rng.randint(WX0 + 20, WX1 - 20), rng.randint(WY0 + 14, WY1 - 14),
              rng.randint(5, 12), rng.randint(3, 5), rng)
    for _ in range(4):
        footprints(c, rng.randint(WX0 + 30, WX1 - 60), rng.randint(WY0 + 20, WY1 - 20), 8,
                   rng.choice((-6, 6)), rng.choice((-1, 0, 1)))
    for _ in range(3):
        skull(c, rng.randint(WX0 + 10, WX1 - 14), rng.randint(WY0 + 8, WY1 - 10))
        bone(c, rng.randint(WX0 + 10, WX1 - 14), rng.randint(WY0 + 8, WY1 - 10))
    if litter:
        for _ in range(60):
            x, y = rng.randint(WX0 + 2, WX1 - 4), rng.randint(WY0 + 2, WY1 - 4)
            if rng.random() < .5:
                c.rect(x, y, 2, 1, rng.choice((WHITE, TAN_LIGHT, CREAM)))
            else:
                c.set(x, y, rng.choice((ROOF_LIGHT, ROOF_DARK, DIRT)))


def bench():
    c = C(18, 12)
    c.rect(0, 0, 18, 4, WOOD)
    c.rect(0, 0, 18, 1, TAN_MID)
    c.rect(0, 5, 18, 3, WOOD_DARK)
    c.rect(1, 8, 2, 3, ROOF_DARK)
    c.rect(15, 8, 2, 3, ROOF_DARK)
    return c.outline_pad()


def cone_obj():
    c = C(7, 9)
    c.rect(2, 1, 3, 6, ORANGE)
    c.rect(2, 3, 3, 1, WHITE)
    c.rect(0, 7, 7, 2, ORANGE)
    return c.outline_pad()


def dead_plant(h=16, seed=0):
    rng = random.Random(seed)
    c = C(18, h)
    for _ in range(6):
        line(c, 9, h - 1, 9 + rng.randint(-7, 7), rng.randint(0, h // 2), rng.choice((WEED, TRUNK, GREEN_DARK)))
    return c.outline_pad()


# ======================================================================================
# SCENE 2: the empty mall
# ======================================================================================
def storefront(c, x, w, name, pal, mode, seed):
    dk, md, lt = pal
    rng = random.Random(seed)
    c.rect(x, 0, w, WY0, md)
    c.rect(x, 0, 1, WY0, dk)
    c.rect(x + w - 1, 0, 1, WY0, dk)
    for _ in range(8):
        c.rect(x + rng.randint(2, w - 6), rng.randint(0, WY0 - 8), rng.randint(2, 4), 2, SOOT)
    pl = sign_plate(name, dk, WHITE, lt)
    if seed % 3 == 0:                                           # one flickered-out letter
        pl.rect(5, 3, 3, 5, dk)
    c.paste(pl, x + (w - pl.w) // 2, 0)
    wx, wy, ww, wh = x + 4, 11, w - 8, 13
    c.rect(wx - 1, wy - 1, ww + 2, wh + 2, TIRE)
    c.rect(wx, wy, ww, wh, GLASS_DARK)
    for i in range(0, ww, 9):
        line(c, wx + i + 2, wy + 1, wx + i + 6, wy + 5, GLASS_MID)
    if mode == "grille":
        for yy in range(wy, wy + 9, 2):
            c.rect(wx, yy, ww, 1, ROOF_MID)
        c.rect(wx, wy + 9, ww, 1, ROOF_LIGHT)
    elif mode == "broken":
        for _ in range(ww * wh // 5):
            c.set(wx + rng.randint(0, ww - 1), wy + rng.randint(0, wh - 1), GLASS_MID)
        line(c, wx + 2, wy, wx + ww // 2, wy + wh - 1, GLASS_LIGHT)
        line(c, wx + ww - 3, wy, wx + ww // 2 + 3, wy + wh - 4, GLASS_LIGHT)
    elif mode == "mannequin":
        for k in (ww // 3, 2 * ww // 3):
            c.rect(wx + k - 1, wy + 5, 3, 6, CREAM)
            c.disk(wx + k, wy + 3, 2, CREAM)
            c.rect(wx + k - 2, wy + 1, 4, 1, TIRE)
        c.rect(wx + ww // 3 + 4, wy + 6, 4, 1, CREAM)           # a dropped arm
    elif mode == "fire":
        c.rect(wx, wy + 5, ww, wh - 5, FLAME_R)
        c.rect(wx + 2, wy + 7, ww - 4, wh - 7, FLAME_O)
        c.rect(wx + 5, wy + 9, ww - 10, wh - 9, FLAME_Y)
    c.rect(x, WY0 - 3, w, 3, dk)


def vending(col_a, col_b):
    c = C(14, 22)
    c.rect(0, 0, 14, 22, col_a)
    c.rect(0, 0, 14, 2, col_b)
    c.rect(2, 3, 8, 11, GLASS_DARK)
    for r in range(3):
        for i in range(4):
            c.set(3 + i * 2, 4 + r * 3, (RED, YELLOW, CYAN, GREEN_LIGHT)[(i + r) % 4])
    c.rect(11, 4, 2, 5, ROOF_DARK)
    c.rect(3, 16, 8, 3, TIRE)
    c.rect(0, 20, 14, 2, ROOF_DARK)
    line(c, 3, 3, 8, 8, GLASS_LIGHT)
    return c.outline_pad()


def shopping_cart():
    c = C(20, 14)
    c.rect(1, 1, 16, 8, ROOF_LIGHT)
    c.rect(2, 2, 14, 6, ROOF_DARK)
    for x in range(3, 16, 3):
        c.rect(x, 2, 1, 6, ROOF_MID)
    c.rect(1, 4, 16, 1, ROOF_MID)
    line(c, 17, 1, 19, 4, ROOF_LIGHT)
    for x in (2, 14):
        c.rect(x, 10, 2, 3, TIRE)
    return c.outline_pad()


def dead_palm(h=34, seed=0):
    rng = random.Random(seed)
    c = C(30, h + 8)
    c.rect(11, h - 6, 10, 12, TAN_DARK)                         # planter
    c.rect(11, h - 6, 10, 2, TAN_MID)
    c.rect(14, h // 3, 3, h - h // 3 - 4, TRUNK)
    for k in range(7):
        ex = rng.choice((-13, -10, -7, 7, 10, 13))
        line(c, 15, h // 3, 15 + ex, h // 3 + rng.randint(2, 9), rng.choice((WEED, GREEN_DARK, TRUNK)))
        line(c, 15, h // 3 + 1, 15 + ex, h // 3 + rng.randint(3, 10), rng.choice((WEED, TRUNK)))
    return c.outline_pad()


def kiosk():
    c = C(24, 22)
    c.rect(1, 9, 22, 12, TEAL_MID)
    c.rect(1, 9, 22, 2, TEAL_LIGHT)
    c.rect(1, 18, 22, 3, TEAL_DARK)
    c.rect(4, 12, 16, 4, GLASS_DARK)
    for x in range(0, 24, 4):
        c.rect(x, 1, 4, 8, RED if (x // 4) % 2 == 0 else WHITE)
    for x in range(0, 24, 8):
        c.rect(x, 7, 4, 3, 0)                                   # torn awning
    return c.outline_pad()


def escalator(h=64):
    c = C(22, h)
    c.rect(0, 0, 3, h, ROOF_DARK)
    c.rect(19, 0, 3, h, ROOF_DARK)
    for y in range(0, h, 3):
        c.rect(3, y, 16, 2, ROOF_LIGHT if (y // 3) % 2 == 0 else ROOF_MID)
        c.rect(3, y + 2, 16, 1, YELLOW_DARK if y % 6 == 0 else ROOF_DARK)
    c.rect(3, h // 2 - 4, 16, 10, SOOT)                         # collapsed section
    for x in (4, 9, 14):
        line(c, x, h // 2 - 4, x + 3, h // 2 + 5, RUST)
    return c.outline_pad()


def mall_floor(c):
    for y in range(H):
        for x in range(W):
            v = PAVE_LIGHT if ((x // 16) + (y // 8)) % 2 == 0 else PAVE_MID
            if x % 16 == 0 or y % 8 == 0 or noise(x, y) < 5:
                v = PAVE_DARK
            c.set(x, y, v)


def medallion(c, cx, cy):
    for r, col in ((42, TEAL_DARK), (40, CREAM), (37, TEAL_MID), (26, CREAM), (24, TEAL_DARK)):
        c.disk(cx, cy, r, col)
    for k in range(8):
        a = np.radians(k * 45 + 22.5)
        for t in range(6, 23):
            c.rect(int(cx + np.cos(a) * t), int(cy + np.sin(a) * t * .9), 2, 2, TEAL_LIGHT)
    c.disk(cx, cy, 6, CREAM)
    c.disk(cx, cy, 3.5, TEAL_MID)


def beam(c, x0, y0, w, h, slope):
    for y in range(h):
        sx = x0 + int(y * slope)
        for x in range(sx, sx + w):
            if (x + y) % 2 == 0 and WX0 <= x < WX1 and WY0 <= y0 + y < WY1:
                c.set(x, y0 + y, CREAM)


def scene_mall():
    rng = random.Random(11)
    c = C(W, H)
    mall_floor(c)
    # ------------------------------------------------ INTERIOR (flat only)
    medallion(c, 240, 135)
    for (x, y, w, h, s) in ((70, 34, 24, 64, .7), (150, 120, 22, 70, .6), (330, 30, 26, 70, .6),
                            (372, 140, 20, 80, .7), (210, 190, 18, 48, .5)):
        beam(c, x, y, w, h, s)
    flat_ground_details(c, rng, PAVE_DARK, ncr=14)
    for (x, y, rx, ry) in ((110, 190, 14, 5), (360, 70, 12, 4), (290, 205, 9, 3), (190, 70, 7, 3)):
        c.ell(x, y, rx, ry, GLASS_DARK)                         # water from the leaking roof
        c.ell(x - 1, y - .5, rx - 2, ry - 1, GLASS_MID)
        c.rect(int(x - rx * .5), int(y - ry * .4), 4, 1, GLASS_LIGHT)
    for (x, y) in ((88, 70), (176, 150), (300, 60), (340, 168), (140, 90)):
        c.rect(x, y, 14, 9, CREAM)                              # fallen ceiling panel
        c.rect(x, y + 4, 14, 1, PAVE_DARK)
        c.rect(x + 6, y, 1, 9, PAVE_DARK)
        c.rect(x + 9, y, 5, 3, PAVE_DARK)
        c.disk(x + 4, y + 6, 2, TAN_MID)
        line(c, x + 11, y + 8, x + 13, y + 14, SOOT)
    for (x, y) in ((70, 206), (322, 120), (210, 100)):
        sc = shopping_cart()
        c.paste(sc, x, y)
    for (x, y) in ((130, 60), (270, 220), (386, 190)):
        line(c, x, y, x + 8, y + 1, CREAM)                      # mannequin arm
        c.rect(x + 8, y, 3, 2, CREAM)
        c.disk(x + 18, y + 6, 3, CREAM)                         # mannequin head
        c.rect(x + 15, y + 3, 6, 2, TIRE)
    c.rect(246, 212, 10, 6, YELLOW)                             # fallen WET FLOOR sign
    c.rect(246, 212, 10, 1, YELLOW_DARK)
    text(c, 247, 213, "WET", TIRE)
    text(c, 150, 36, "SALE", SLIME_DARK, 2)
    # ------------------------------------------------ PADDING
    fill_padding(c, PAVE_DARK, (TRUNK, ROOF_DARK, SOOT), rng, 200)
    names = ["SHOES", "SALE", "FOOD", "CAFE", "BOOKS", "GAMES", "TOYS", "SHOP", "PHONES", "FASHION"]
    pals = [(TEAL_DARK, TEAL_MID, TEAL_LIGHT), (BRICK_DARK, BRICK_MID, BRICK_LIGHT),
            (BLUE_DARK, BLUE_MID, CYAN_DARK), (TAN_DARK, TAN_MID, TAN_LIGHT)]
    modes = ["grille", "broken", "mannequin", "grille", "fire", "broken", "mannequin", "grille", "broken", "mannequin"]
    for i in range(10):
        storefront(c, i * 48, 48, names[i], pals[i % 4], modes[i], i + 1)
    # left: broken escalator + barricade of junk along the walkable edge
    place_pad(c, escalator(70), 8, 36, "escalator")
    place_pad(c, dead_palm(30, 1), 8, 112, "palm")
    for i, (o, y) in enumerate(((vending(RED, RED_DARK), 134), (shopping_cart(), 160), (bench(), 176),
                                (vending(BLUE_MID, BLUE_DARK), 192), (shopping_cart(), 218))):
        place_pad(c, o, 46 - o.w, y, "junk L")
    place_pad(c, with_fire(C(10, 4), [(5, 8)], extra=12), 6, 214, "fire L") if False else None
    place_pad(c, barrel_fire(), 6, 200, "barrel L")
    place_pad(c, rubble(22, 14, 21), 4, 226, "rubble L")
    # right: kiosk, vending machines, a dead palm
    place_pad(c, kiosk(), 436, 36, "kiosk")
    place_pad(c, dead_palm(30, 2), 446, 80, "palm R")
    for o, y in ((vending(CYAN_DARK, BLUE_DARK), 120), (shopping_cart(), 146), (vending(RED, RED_DARK), 164),
                 (bench(), 190), (shopping_cart(), 208)):
        place_pad(c, o, 434, y, "junk R")
    place_pad(c, barrel_fire(), 462, 150, "barrel R")
    place_pad(c, rubble(24, 14, 22), 454, 226, "rubble R")
    # bottom: balcony railing over the dark lower level + a barricaded entrance
    c.rect(0, WY1 + 9, W, H - WY1 - 9, SOOT)
    for _ in range(600):
        c.set(rng.randint(0, W - 1), rng.randint(WY1 + 9, H - 1), rng.choice((ROOF_DARK, TIRE, GLASS_DARK)))
    for x in range(0, W, 16):
        if abs(x + 8 - 240) < 44:
            continue
        pn = C(16, 9)
        pn.rect(0, 0, 16, 9, GLASS_MID if (x // 16) % 5 else GLASS_DARK)
        pn.rect(2, 2, 3, 1, GLASS_LIGHT)
        if (x // 16) % 4 == 1:
            line(pn, 3, 0, 10, 8, GLASS_LIGHT)
        pn.rect(0, 0, 1, 9, ROOF_LIGHT)
        pn.rect(0, 0, 16, 1, ROOF_LIGHT)
        c.paste(pn, x, WY1 + 1)
    c.rect(196, WY1, 88, 27, TAN_DARK)                          # barricaded entrance
    for k in range(3):
        c.rect(198, WY1 + 3 + k * 7, 84, 3, WOOD if k % 2 else WOOD_DARK)
        c.rect(198, WY1 + 3 + k * 7, 84, 1, TAN_MID)
    for x in (204, 236, 268):
        c.rect(x, WY1, 4, 27, WOOD_DARK)
    place_pad(c, hazard_tape(88), 196, WY1 + 1, "tape")
    place_pad(c, dead_plant(14, 3), 36, WY1 + 10, "plant")
    place_pad(c, dead_plant(14, 4), 420, WY1 + 10, "plant")
    shade_padding(c)
    return c


# ======================================================================================
# SCENE 3: the airport apron
# ======================================================================================
def suitcase(col, rng):
    c = C(8, 6)
    c.rect(0, 1, 8, 5, col)
    c.rect(0, 1, 8, 1, WHITE if col != WHITE else CREAM)
    c.rect(3, 0, 2, 1, TIRE)
    c.rect(1, 5, 6, 1, TIRE)
    if rng.random() < .4:
        c.rect(5, 2, 3, 2, PINK_DARK)                           # burst open, clothes out
    return c


def baggage_cart():
    c = C(30, 14)
    c.rect(1, 6, 28, 5, ROOF_MID)
    c.rect(1, 6, 28, 1, ROOF_LIGHT)
    for i, col in enumerate((RED, BLUE_MID, TAN_MID, TEAL_MID, PINK_DARK)):
        c.rect(2 + i * 5, 1 + (i % 2), 5, 6, col)
        c.rect(2 + i * 5, 1 + (i % 2), 5, 1, WHITE)
    for x in (3, 22):
        c.rect(x, 10, 5, 4, TIRE)
    line(c, 29, 7, 29, 2, ROOF_LIGHT)
    return c.outline_pad()


def fuel_truck():
    c = C(44, 22)
    c.rect(1, 3, 30, 14, ROOF_LIGHT)                            # tank
    c.rect(1, 3, 30, 3, WHITE)
    c.rect(1, 13, 30, 4, ROOF_MID)
    c.rect(12, 3, 4, 14, RED)
    c.rect(32, 6, 11, 11, RUST)                                 # cab
    c.rect(38, 8, 5, 4, GLASS_DARK)
    c.rect(1, 17, 42, 2, ROOF_DARK)
    for x in (4, 22, 34):
        c.rect(x, 17, 6, 4, TIRE)
    c.rect(3, 6, 8, 3, SOOT)
    return c.outline_pad()


def tail_fin():
    c = C(44, 100)
    poly(c, [(8, 0), (30, 0), (38, 52), (6, 52)], WHITE)
    poly(c, [(8, 0), (14, 0), (12, 52), (6, 52)], CREAM)
    poly(c, [(12, 10), (30, 10), (32, 30), (14, 30)], BLUE_MID)
    c.disk(21, 20, 4, WHITE)
    c.rect(20, 18, 2, 5, RED)
    poly(c, [(6, 52), (38, 52), (36, 72), (8, 72)], WHITE)     # fuselage stub, torn off
    c.rect(8, 56, 28, 3, BLUE_DARK)
    for x in range(10, 36, 5):
        c.rect(x, 62, 3, 3, GLASS_DARK)
    for x in range(7, 37, 4):                                   # ragged tear
        c.rect(x, 72, 3, 2 + (x * 7) % 5, ROOF_MID)
    poly(c, [(0, 60), (8, 56), (8, 70), (0, 76)], ROOF_LIGHT)   # stabiliser stub
    c = c.outline_pad()
    return with_fire(c, [(20, 12), (30, 9)], extra=22)


def wind_sock():
    c = C(18, 26)
    c.rect(2, 4, 2, 22, ROOF_LIGHT)
    for i in range(5):
        c.rect(4 + i * 2, 4 + i // 2, 2, 6 - i, ORANGE if i % 2 == 0 else WHITE)
    return c.outline_pad()


def jet_bridge():
    c = C(40, 14)
    c.rect(0, 0, 40, 10, ROOF_LIGHT)
    c.rect(0, 0, 40, 2, WHITE)
    for x in range(4, 32, 6):
        c.rect(x, 4, 4, 3, GLASS_DARK)
    c.rect(34, 0, 6, 10, ROOF_MID)
    c.rect(36, 10, 3, 4, TIRE)
    c.rect(2, 8, 6, 2, SOOT)
    return c.outline_pad()


def airport_ground(c):
    for y in range(H):
        for x in range(W):
            v = PAVE_LIGHT if ((x // 36) + (y // 24)) % 2 else PAVE_MID
            if x % 36 == 0 or y % 24 == 0 or noise(x, y) < 5:
                v = PAVE_DARK
            c.set(x, y, v)
    for y in range(96, 160):
        for x in range(W):
            c.set(x, y, asphalt(x, y))


def scene_airport():
    rng = random.Random(23)
    c = C(W, H)
    airport_ground(c)
    # ------------------------------------------------ INTERIOR (flat only)
    m = C(W, H)                                                 # worn paint layer
    m.rect(0, 98, W, 2, WHITE)
    m.rect(0, 156, W, 2, WHITE)
    for x in range(30, W - 30, 34):
        m.rect(x, 127, 20, 2, WHITE)
    for k in range(7):                                          # runway thresholds
        m.rect(52, 103 + k * 7, 22, 3, WHITE)
        m.rect(406, 103 + k * 7, 22, 3, WHITE)
    for (x0, y0, x1, y1) in ((300, 158, 304, 176), (304, 176, 318, 190), (318, 190, 330, 200),
                             ):
        for dx in (0, 1):
            line(m, x0 + dx, y0, x1 + dx, y1, YELLOW)
    for dx in (0, 1):
        line(m, 270 + dx, 158, 290 + dx, 176, YELLOW)
    m.rect(300, 200, 2, 40, YELLOW)                             # parking stand box
    m.rect(360, 200, 2, 40, YELLOW)
    m.rect(300, 238, 62, 2, YELLOW)
    ring(m, 108, 206, 22, YELLOW, 3)                            # helipad
    text(m, 100, 197, "H", WHITE, 4)
    text(m, 312, 214, "GATE", YELLOW, 2)
    worn(m, c)
    flat_ground_details(c, rng, PAVE_DARK, ncr=16)
    scorch(c, 200, 60, 16, 7)
    scorch(c, 360, 128, 18, 6)
    crater(c, 160, 205, 14, 6, rng)
    for _ in range(11):                                         # luggage everywhere
        s = suitcase(rng.choice((RED, BLUE_MID, TAN_MID, TEAL_MID, PINK_DARK, ROOF_MID)), rng)
        c.paste(s, rng.randint(WX0 + 10, WX1 - 20), rng.randint(WY0 + 6, WY1 - 12))
    c.disk(250, 190, 4, TIRE)                                   # a loose wheel
    c.disk(250, 190, 1.6, ROOF_LIGHT)
    ring(c, 90, 60, 7, ROOF_MID, 2)                             # engine cowl ring
    ring(c, 90, 60, 4, SOOT, 2)
    poly(c, [(300, 60), (326, 56), (330, 66), (312, 72), (298, 70)], ROOF_LIGHT)   # torn panel
    for (x, y) in ((306, 62), (320, 61), (312, 68)):
        c.set(x, y, ROOF_DARK)
    c.ell(150, 120, 10, 4, WHITE)                               # fire-foam stain
    for _ in range(40):
        c.set(int(150 + rng.uniform(-14, 14)), int(120 + rng.uniform(-6, 6)), WHITE)
    # ------------------------------------------------ PADDING
    fill_padding(c, DIRT, (TRUNK, WEED, ROOF_DARK, WEED), rng, 360)
    for x in range(0, W, 12):                                   # terminal glass wall
        for y in range(WY0):
            col = GLASS_DARK if (x // 12 + y // 9) % 3 else GLASS_MID
            c.rect(x, y, 12, 1, col)
        c.rect(x, 0, 1, WY0, ROOF_LIGHT)
    for x in range(0, W, 12):
        if noise(x, 3) < 70:
            c.rect(x + 1, 3, 11, WY0 - 8, SOOT)                 # missing panes
        elif noise(x, 5) < 130:
            line(c, x + 2, 2, x + 9, 18, GLASS_LIGHT)
    c.rect(0, WY0 - 4, W, 4, ROOF_MID)
    c.rect(0, WY0 - 4, W, 1, ROOF_LIGHT)
    pl = sign_plate("DEPARTURES", BLUE_DARK, WHITE, WHITE)
    c.paste(pl, 40, 1)
    pl2 = sign_plate("ARRIVALS", BLUE_DARK, WHITE, WHITE)
    c.paste(pl2, 330, 1)
    place_pad(c, jet_bridge(), 130, 10, "bridge")
    place_pad(c, jet_bridge(), 250, 10, "bridge")
    smoke_layer = C(W, H)
    for (sx, sy) in ((60, 10), (200, 8), (380, 9), (440, 6)):
        smoke(smoke_layer, sx, sy + 6, 3, 3)
    c.paste(smoke_layer, 0, 0)
    for (x, y0, y1) in ((41, WY0, WY1), (WX1, WY0, WY1)):
        c.paste(fence_v(y1 - y0, x), x, y0)
    place_pad(c, with_fire(fuel_truck(), [(12, 10), (22, 8)], extra=20), 2, 60, "fuel")
    place_pad(c, baggage_cart(), 4, 120, "cart")
    place_pad(c, baggage_cart(), 4, 138, "cart")
    place_pad(c, cone_obj(), 30, 160, "cone")
    place_pad(c, barrel_fire(), 20, 180, "barrel")
    place_pad(c, rubble(30, 16, 31), 4, 206, "rubble")
    place_pad(c, tail_fin(), 436, 60, "tail")
    place_pad(c, rubble(32, 16, 32), 440, 160, "rubble R")
    place_pad(c, with_fire(wreck_car_v(1), [(9, 9)], extra=16), 454, 184, "wreck R")
    place_pad(c, cone_obj(), 438, 216, "cone R")
    place_pad(c, cone_obj(), 456, 224, "cone R")
    place_pad(c, fence_h(WX1 - WX0, 3), WX0, WY1 + 1, "fence")
    for x in range(WX0 + 6, WX1, 12):                           # runway edge lights
        place_pad(c, _edge_light(BLUE_MID if (x // 12) % 2 else YELLOW), x, WY1 + 17, "light")
    place_pad(c, wind_sock(), 96, WY1 - 0 + 0, "sock")
    place_pad(c, wreck_car_h(1), 330, WY1 + 8, "wreck B")
    place_pad(c, rubble(34, 14, 33), 200, WY1 + 12, "rubble B")
    place_pad(c, hazard_tape(60), 40, WY1 + 4, "tape")
    shade_padding(c)
    return c


def _edge_light(col):
    c = C(3, 3, col)
    return c.outline_pad()


# ======================================================================================
# SCENE 4: the weird & goofy one - an abandoned GIANT picnic (everything is huge, the
# zombies are tiny). Gingham tablecloth, moldy giant food, ants, giant cutlery.
# ======================================================================================
def gingham(x, y):
    a, b = (x // 6) % 2 == 0, (y // 6) % 2 == 0
    return RED if (a and b) else RED_LIGHT if (a or b) else WHITE


def to_cloth(c, cx, cy, r):
    for y in range(int(cy - r), int(cy + r) + 1):
        for x in range(int(cx - r), int(cx + r) + 1):
            if (x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 <= r * r:
                c.set(x, y, gingham(x, y))


def bottle(body, light, cap, w=22, h=64):
    c = C(w, h)
    c.rect(w // 2 - 3, 0, 6, 16, body)
    c.rect(w // 2 - 3, 0, 6, 5, cap)
    c.rect(w // 2 - 6, 16, 12, 6, body)
    c.rect(1, 22, w - 2, h - 22, body)
    c.rect(3, 24, 2, h - 28, light)
    c.rect(4, 34, w - 8, 22, CREAM)
    skull(c, w // 2 - 2, 38)
    c.rect(4, 50, w - 8, 1, body)
    c.rect(1, h - 3, w - 2, 3, ROOF_DARK)
    return c.outline_pad()


def glass_tall(w=24, h=64):
    c = C(w, h)
    c.rect(1, 0, w - 2, h, GLASS_LIGHT)
    c.rect(3, 8, w - 6, h - 12, YELLOW)
    c.rect(3, 8, w - 6, 2, YELLOW_DARK)
    c.rect(5, 18, 7, 7, WHITE)
    c.rect(11, 34, 7, 7, WHITE)
    line(c, 16, 0, 11, 30, RED)
    line(c, 17, 0, 12, 30, WHITE)
    c.disk(w - 3, 4, 4, GREEN_LIGHT)
    c.rect(1, h - 3, w - 2, 3, CYAN_DARK)
    return c.outline_pad()


def shaker(w=20, h=44):
    c = C(w, h)
    c.rect(2, 12, w - 4, h - 12, GLASS_LIGHT)
    c.rect(2, 12, w - 4, 3, WHITE)
    c.rect(3, 20, w - 6, h - 22, WHITE)
    c.rect(1, 2, w - 2, 10, ROOF_LIGHT)
    for x in range(5, w - 4, 4):
        c.set(x, 5, ROOF_DARK)
    c.rect(1, 2, w - 2, 1, WHITE)
    c.rect(w - 6, 12, 3, h - 14, CREAM)
    return c.outline_pad()


def fork_v(h=100):
    c = C(14, h)
    for x in (0, 4, 8, 12):
        c.rect(x, 0, 2, 28, ROOF_LIGHT)
    c.rect(0, 24, 14, 8, ROOF_LIGHT)
    c.rect(4, 32, 6, h - 32, ROOF_LIGHT)
    c.rect(4, 32, 2, h - 32, WHITE)
    c.rect(8, 32, 2, h - 32, ROOF_MID)
    return c.outline_pad()


def knife_v(h=100):
    c = C(12, h)
    c.rect(1, 0, 8, 62, ROOF_LIGHT)
    c.rect(1, 0, 2, 62, WHITE)
    for y in range(2, 60, 4):
        c.set(9, y, ROOF_DARK)
    c.rect(2, 62, 7, h - 62, WOOD)
    c.rect(2, 62, 2, h - 62, TAN_MID)
    c.rect(3, 70, 5, 2, TIRE)
    return c.outline_pad()


def ant(carry=True, flip=False):
    c = C(36, 18)
    c.ell(26, 9, 7, 4.5, RED_DARK)
    c.ell(24, 8, 4, 2.5, RUST)
    c.ell(15, 9, 3.5, 3, RED_DARK)
    c.ell(8, 9, 4, 3.5, RED_DARK)
    for x in (13, 15, 17):
        line(c, x, 9, x - 3, 2, TIRE)
        line(c, x, 9, x - 3, 16, TIRE)
    line(c, 5, 6, 1, 1, TIRE)
    line(c, 5, 12, 1, 17, TIRE)
    c.set(6, 8, WHITE)
    c.set(6, 10, WHITE)
    if carry:
        c.disk(2, 9, 2.5, TAN_LIGHT)
    c = c.outline_pad()
    if flip:
        c.a = c.a[:, ::-1].copy()
    return c


def fly():
    c = C(10, 8)
    c.ell(5, 4, 2.5, 2, TIRE)
    c.rect(1, 0, 3, 3, CYAN)
    c.rect(6, 0, 3, 3, CYAN)
    c.set(5, 3, RED)
    return c.outline_pad()


def scene_picnic():
    rng = random.Random(41)
    c = C(W, H)
    # table (wood), then the tablecloth hanging over its edges
    for y in range(H):
        for x in range(W):
            c.set(x, y, WOOD if (y + (x // 9) % 3) % 5 else WOOD_DARK)
    cx0, cx1, cy1 = WX0 - 8, WX1 + 8, WY1 + 8
    for y in range(0, cy1):
        for x in range(cx0, cx1):
            v = gingham(x, y)
            if noise(x, y) < 5:
                v = RED_DARK if v != WHITE else TAN_LIGHT        # old stains
            c.set(x, y, v)
    for x in range(cx0, cx1):                                    # scalloped hem
        d = 2 + ((x // 3) % 2)
        c.rect(x, cy1 - 1, 1, d, WHITE if (x // 3) % 2 else CREAM)
        c.rect(x, cy1 - 1 + d, 1, 2, WOOD_DARK)
    for y in range(0, cy1):
        for (x, dxs) in ((cx0, -1), (cx1 - 1, 1)):
            d = 2 + ((y // 3) % 2)
            for k in range(d):
                c.set(x + dxs * k, y, WHITE if (y // 3) % 2 else CREAM)
            c.set(x + dxs * d, y, WOOD_DARK)
            c.set(x + dxs * (d + 1), y, WOOD_DARK)
    # ------------------------------------------------ INTERIOR (flat only)
    flat_ground_details(c, rng, RED_DARK, ncr=6, litter=False)
    for _ in range(140):
        c.set(rng.randint(WX0, WX1 - 1), rng.randint(WY0, WY1 - 1), rng.choice((TAN_LIGHT, TAN_MID, BONE)))
    # soda puddle
    c.ell(110, 70, 22, 11, RUST_DARK)
    c.ell(108, 68, 18, 8, RUST)
    for (x, y) in ((100, 66), (112, 70), (118, 64), (96, 72)):
        c.rect(x, y, 2, 2, WHITE)
    # mustard + ketchup splats
    c.ell(332, 62, 14, 7, YELLOW)
    c.ell(330, 60, 10, 4, YELLOW_DARK)
    for i in range(5):
        c.rect(322 + i * 5, 68, 2, 6 + (i * 3) % 5, YELLOW)
    c.ell(360, 200, 16, 7, RED_DARK)
    c.ell(358, 198, 12, 4, RED)
    # cheese slice (bitten)
    poly(c, [(70, 190), (112, 178), (112, 206), (70, 206)], YELLOW)
    c.rect(70, 190, 42, 2, YELLOW_DARK)
    for (x, y, r) in ((84, 196, 2.2), (98, 190, 2.6), (102, 200, 2), (78, 202, 1.5)):
        c.disk(x, y, r, TAN_DARK)
    to_cloth(c, 70, 190, 7)
    to_cloth(c, 74, 200, 5)
    for (x, y) in ((92, 196), (100, 196)):
        c.set(x, y, GREEN_LIGHT)                                 # mold
        c.set(x + 1, y + 1, GREEN_MID)
    # ant trail to the cheese
    for t in range(0, 12):
        px, py = 60 - t * 9, 196 - t * 7 // 2
        if WX0 + 2 < px:
            c.rect(px, py, 3, 2, TIRE)
            c.set(px + 3, py - 1, TIRE)
    # pizza slice
    poly(c, [(250, 46), (292, 56), (260, 86)], TAN_LIGHT)
    poly(c, [(254, 52), (284, 58), (262, 80)], YELLOW)
    for (x, y) in ((262, 60), (272, 62), (262, 70), (266, 76)):
        c.disk(x, y, 2.5, RED)
        c.set(x - 1, y - 1, RED_LIGHT)
    c.rect(272, 56, 3, 2, GREEN_LIGHT)
    # watermelon slice
    c.ell(170, 150, 20, 14, GREEN_DARK)
    c.ell(170, 150, 18, 12, WHITE)
    c.ell(170, 150, 16, 10, RED)
    for (x, y) in ((160, 150), (170, 154), (178, 148), (166, 144), (176, 156)):
        c.rect(x, y, 2, 2, TIRE)
    to_cloth(c, 170, 130, 20)
    # brain sandwich with a bite out of it
    c.rect(330, 120, 24, 18, TAN_MID)
    c.rect(330, 120, 24, 2, TAN_LIGHT)
    c.rect(334, 126, 22, 14, PINK)
    for x in range(335, 355, 4):
        line(c, x, 128, x + 2, 138, PINK_DARK)
    c.rect(332, 138, 24, 8, TAN_MID)
    to_cloth(c, 356, 134, 8)
    # rubber duck + paper plate with a fork
    c.ell(236, 210, 8, 6, YELLOW)
    c.ell(246, 204, 4, 3.5, YELLOW)
    c.rect(250, 204, 4, 2, ORANGE)
    c.set(246, 203, TIRE)
    c.ell(262, 120, 14, 11, WHITE)
    c.ell(262, 120, 11, 8, CREAM)
    for k in range(4):
        c.rect(256 + k * 3, 110, 2, 10, ROOF_LIGHT)
    c.rect(258, 120, 12, 2, ROOF_LIGHT)
    # confetti / glitter patch
    for _ in range(90):
        a, r = rng.uniform(0, 6.28), rng.uniform(0, 20)
        c.set(int(190 + np.cos(a) * r * 1.4), int(70 + np.sin(a) * r * .8),
              rng.choice((CYAN, PINK, YELLOW, GREEN_LIGHT, WHITE)))
    text(c, 292, 226, "ZOMBIE PICNIC", SLIME_DARK, 2)
    for (x, y) in ((140, 100), (300, 90), (190, 200)):
        c.paste(fly(), x, y)
    # ------------------------------------------------ PADDING (tall props)
    for (x, bot, o) in ((46, 26, bottle(RED, RED_LIGHT, WHITE)),
                        (104, 26, bottle(YELLOW, CREAM, RED)),
                        (170, 26, shaker()),
                        (236, 26, glass_tall()),
                        (320, 26, shaker(20, 40)),
                        (378, 26, bottle(GREEN_MID, GREEN_LIGHT, WHITE, 22, 58)),
                        (436, 26, glass_tall())):
        place_pad(c, o, x, bot - o.h + 1, "giant")
    place_pad(c, fork_v(110), 8, 70, "fork")
    place_pad(c, ant(True), 6, 190, "ant L")
    place_pad(c, ant(False), 4, 36, "ant L2")
    place_pad(c, knife_v(110), 456, 90, "knife")
    place_pad(c, ant(True, flip=True), 440, 40, "ant R")
    place_pad(c, ant(True, flip=True), 442, 214, "ant R2")
    for (x, y) in ((22, 150), (454, 70)):
        place_pad(c, fly(), x, y, "fly")
    # bottom: giant bread knife lying down + ants marching + crumbs
    kn = C(96, 14)
    kn.rect(0, 2, 70, 9, ROOF_LIGHT)
    kn.rect(0, 2, 70, 2, WHITE)
    for x in range(0, 70, 4):
        kn.set(x, 11, ROOF_DARK)
    kn.rect(70, 2, 26, 9, WOOD)
    kn.rect(70, 2, 26, 2, TAN_MID)
    kn.rect(80, 6, 2, 2, TIRE)
    kn.rect(90, 6, 2, 2, TIRE)
    place_pad(c, kn.outline_pad(), 70, WY1 + 10, "bread knife")
    for i in range(8):
        place_pad(c, ant(i % 2 == 0, flip=True) if False else _tiny_ant(), 240 + i * 22, WY1 + 14 + (i % 3) * 3, "ants")
    c.disk(430, WY1 + 14, 5, TAN_LIGHT)
    c.disk(436, WY1 + 17, 3, TAN_MID)
    shade_padding(c)
    return c


def _tiny_ant():
    c = C(9, 5)
    c.rect(0, 1, 3, 3, TIRE)
    c.rect(4, 1, 2, 3, TIRE)
    c.rect(7, 1, 2, 3, TIRE)
    c.set(2, 0, TIRE)
    c.set(5, 4, TIRE)
    return c


SCENES = {"street_intersection": scene_street, "empty_mall": scene_mall,
          "airport": scene_airport, "giant_picnic": scene_picnic}


def write_walkable(path):
    rect = dict(x=WX0 * S, y=WY0 * S, w=(WX1 - WX0) * S, h=(WY1 - WY0) * S)
    json.dump({
        "canvas_px": [W * S, H * S],
        "walkable_rect_px": rect,
        "padding_fraction": PAD,
        "walkable_fraction_of_each_side": 1 - 2 * PAD,
        "note": "Identical for every background. Everything outside the rectangle is "
                "decoration (not walkable); everything inside is flat, walkable ground.",
    }, open(path, "w"), indent=2)


def main():
    want = [a for a in sys.argv[1:] if a in SCENES] or list(SCENES)
    os.makedirs(OUT, exist_ok=True)
    write_walkable(os.path.join(OUT, "walkable_area.json"))
    done = []
    for name in want:
        cv = SCENES[name]()
        im = cv.image()
        assert not (cv.a == 0).any(), "transparent pixel left in " + name
        im.save(os.path.join(OUT, name + ".png"))
        ov = im.copy().convert("RGBA")
        tint = Image.new("RGBA", ((WX1 - WX0) * S, (WY1 - WY0) * S), (80, 255, 120, 46))
        ov.alpha_composite(tint, (WX0 * S, WY0 * S))
        ov.convert("RGB").save(os.path.join(OUT, name + "_walkable_preview.png"))
        print(name, im.size)
        done.append(im)
    if len(done) > 1:                                  # contact sheet (preview only)
        half = [i.resize((W * S // 2, H * S // 2), Image.NEAREST) for i in done]
        sheet = Image.new("RGB", (2 * half[0].width + 30, ((len(half) + 1) // 2) * (half[0].height + 10) + 10), (20, 20, 24))
        for k, im in enumerate(half):
            sheet.paste(im, (10 + (k % 2) * (half[0].width + 10), 10 + (k // 2) * (half[0].height + 10)))
        sheet.save(os.path.join(OUT, "backgrounds_preview.png"))


if __name__ == "__main__":
    main()
