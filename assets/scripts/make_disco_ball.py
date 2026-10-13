#!/usr/bin/env python3
"""Rotating disco ball sprite frames (pixel-art, same style as the zombie set).

Output: disco_ball_0.png .. disco_ball_7.png (128x160 RGBA, alpha 0/255 only) plus
disco_ball_preview.png (contact sheet, not part of the set). The 8 frames loop
seamlessly: they cover a rotation of two mirror-tile columns, which is the
pattern's period. Drawn on a 32x40 logical grid, scaled 4x nearest-neighbour.

Tweak: FRAMES, R (radius), NCOLS/NROWS (tile density), SILVER (shades), TINTS.
Usage: python3 make_disco_ball.py [output_dir]
"""
import sys, os, math
import numpy as np
from PIL import Image

W, H, S = 32, 40, 4
CX, CY, R = 16, 23, 12
FRAMES = 8
NCOLS, NROWS = 14, 9          # tiles around the equator / pole to pole

OUTLINE = (24, 22, 38)
SILVER = [(58, 62, 88), (96, 104, 134), (140, 150, 178), (188, 198, 220), (228, 236, 250)]
WHITE = (255, 255, 255)
TINTS = [(120, 220, 255), (255, 130, 210), (255, 235, 120)]   # coloured glints
CHAIN = [(70, 70, 90), (150, 156, 180)]

def sphere_frame(f):
    g = np.zeros((H, W, 4), np.uint8)
    phase = (f / FRAMES) * 2 * (2 * math.pi / NCOLS)     # shift by two tile columns
    L = np.array([-0.5, -0.6, 0.62]); L /= np.linalg.norm(L)
    for y in range(H):
        for x in range(W):
            nx, ny = (x + .5 - CX) / R, (y + .5 - CY) / R
            d2 = nx * nx + ny * ny
            if d2 > 1: continue
            nz = math.sqrt(1 - d2)
            lon = math.atan2(nx, nz) + phase
            lat = math.asin(max(-1, min(1, -ny)))
            u = lon / (2 * math.pi / NCOLS); v = (lat + math.pi / 2) / (math.pi / NROWS)
            cu, cv = math.floor(u), min(NROWS - 1, math.floor(v))
            fu, fv = u - cu, v - math.floor(v)
            # dark grout lines between mirror tiles
            if fu < 0.16 or fv < 0.14:
                g[y, x] = (*SILVER[0], 255); continue
            light = nx * L[0] + ny * L[1] + nz * L[2]
            lvl = int(max(0, light) * 3.6) + (2 if (cu + cv) % 2 == 0 else 0) - 1
            lvl = max(0, min(4, lvl))
            col = SILVER[lvl]
            key = ((cu % 2) * 5 + cv * 4) % 11
            if key in (2, 6, 9) and nz > .25:                # a few coloured tiles
                col = TINTS[key % 3] if lvl >= 2 else SILVER[max(lvl, 1)]
            if key in (4, 8) and light > .55:                # white sparkle tiles
                col = WHITE
            g[y, x] = (*col, 255)
    return g

def add_chain_and_cap(g):
    for y in range(2, CY - R + 1):                           # hanging chain
        g[y, CX] = (*CHAIN[y % 2], 255)
    for x in range(CX - 2, CX + 2):                          # cap
        g[CY - R + 1, x] = (*CHAIN[1], 255)
    for x in range(CX - 1, CX + 1):
        g[CY - R, x] = (*CHAIN[0], 255)
    return g

def outline(g):
    a = g[..., 3] > 0
    n = np.zeros_like(a)
    n[1:] |= a[:-1]; n[:-1] |= a[1:]; n[:, 1:] |= a[:, :-1]; n[:, :-1] |= a[:, 1:]
    ring = n & ~a
    g[ring] = (*OUTLINE, 255)
    return g

def star(g, x, y, big, col=WHITE):
    """Hard-edged 4-point twinkle."""
    pts = [(0, 0)] + [(dx, 0) for dx in range(-big, big + 1) if dx] + [(0, dy) for dy in range(-big, big + 1) if dy]
    for dx, dy in pts:
        if 0 <= y + dy < H and 0 <= x + dx < W and g[y + dy, x + dx, 3] == 0:
            g[y + dy, x + dx] = (*col, 255)

# Twinkle sizes per frame for 3 spots around the ball (outside the silhouette)
TWINKLES = [(5, 12, 1, 0), (27, 30, 1, 0), (4, 33, 1, 0)]
def twinkles(g, f):
    for i, (x, y, _, _) in enumerate(TWINKLES):
        ph = (f + i * 3) % FRAMES
        size = (0, 1, 2, 1, 0, 0, 0, 0)[ph]
        if size: star(g, x, y, size, TINTS[i % 3] if size == 1 else WHITE)

def frame(f):
    g = sphere_frame(f)
    g = add_chain_and_cap(g)
    g = outline(g)
    twinkles(g, f)
    return g

def to_image(g):
    return Image.fromarray(g, "RGBA").resize((W * S, H * S), Image.NEAREST)

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "disco_ball")
    os.makedirs(out, exist_ok=True)
    ims = []
    for f in range(FRAMES):
        im = to_image(frame(f)); im.save(os.path.join(out, f"disco_ball_{f}.png")); ims.append(im)
    sheet = Image.new("RGBA", (FRAMES * W * S // 2, H * S // 2), (84, 90, 104, 255))
    for i, im in enumerate(ims):
        sheet.alpha_composite(im.resize((W * S // 2, H * S // 2), Image.NEAREST), (i * W * S // 2, 0))
    sheet.save(os.path.join(out, "disco_ball_preview.png"))

if __name__ == "__main__":
    main()
