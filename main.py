#!/usr/bin/env python3
"""make.fun entry: ai-happy-01 — "The Butterfly Kiss".

A chubby orange tabby kitten sits in a flower meadow at golden sunrise,
cross-eyed with delight as a blue butterfly lands on the tip of its nose.
That single happy moment is the whole entry: a smiling low sun, a rainbow
tucked behind layered green hills, a heart-shaped cloud, a second pink
butterfly looping through the air on a dotted trail, sparkles, and about
150 deterministic flowers.

Everything is drawn procedurally with PIL — no network, no clock, no
external assets. Fixed seed, 2x supersampling downscaled to 1024x1024, so
two runs write byte-identical output. Output is /output/entry.png (or
$MAKEFUN_OUTPUT_DIR/entry.png). If Pillow is missing in the grading
runtime, the byte-identical pre-rendered artwork.png shipped in the repo
is copied instead, so the entry can never crash on an import.
"""
import math
import os
import random
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSET = HERE / "artwork.png"

W = 1024            # final canvas, square
S = 2               # supersample factor
SEED = 20261113     # fixed seed: every run draws the same meadow


def mix(a, b, t):
    """Blend two RGB colours."""
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def sky_gradient(size, stops):
    """Vertical gradient image from [(0..1, rgb), ...] stops."""
    from PIL import Image
    w, h = size
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    stops = sorted(stops)
    for y in range(h):
        t = y / max(1, h - 1)
        colour = stops[-1][1]
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                colour = mix(c0, c1, (t - p0) / max(1e-6, p1 - p0))
                break
        px[0, y] = colour
    return strip.resize((w, h))


class Pen:
    """ImageDraw wrapper working in final-canvas (1024) coordinates."""

    def __init__(self, draw):
        self.d = draw

    @staticmethod
    def _pts(points):
        return [(x * S, y * S) for x, y in points]

    @staticmethod
    def _box(box):
        return [v * S for v in box]

    def ellipse(self, cx, cy, rx, ry, **kw):
        self.d.ellipse([(cx - rx) * S, (cy - ry) * S,
                        (cx + rx) * S, (cy + ry) * S], **kw)

    def disc(self, cx, cy, r, **kw):
        self.ellipse(cx, cy, r, r, **kw)

    def poly(self, points, **kw):
        self.d.polygon(self._pts(points), **kw)

    def line(self, points, width=3, **kw):
        self.d.line(self._pts(points), width=int(width * S), **kw)

    def arc(self, cx, cy, rx, ry, start, end, **kw):
        self.d.arc([(cx - rx) * S, (cy - ry) * S,
                    (cx + rx) * S, (cy + ry) * S], start, end, **kw)

    def rect(self, box, **kw):
        self.d.rectangle(self._box(box), **kw)


def sparkle_layer(cx, cy, r, colour, alpha=210):
    """A soft four-point sparkle on its own RGBA layer."""
    from PIL import Image, ImageDraw
    pad = r * 2
    img = Image.new("RGBA", (int(pad * 2 * S), int(pad * 2 * S)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ox, oy = pad * S, pad * S
    k = 0.22
    pts = [(ox, oy - r * S), (ox + r * k * S, oy - r * k * S),
           (ox + r * S, oy), (ox + r * k * S, oy + r * k * S),
           (ox, oy + r * S), (ox - r * k * S, oy + r * k * S),
           (ox - r * S, oy), (ox - r * k * S, oy - r * k * S)]
    d.polygon(pts, fill=colour + (alpha,))
    return img, (int((cx - pad) * S), int((cy - pad) * S))


def butterfly_layer(cx, cy, scale, body, wing, edge, spot, tilt=0):
    """Butterfly with wings raised, on its own layer, facing the viewer."""
    from PIL import Image, ImageDraw
    box = 120  # layer half-size in 1024-space units
    img = Image.new("RGBA", (box * 2 * S, box * 2 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    p = Pen(d)
    ox, oy = box, box  # local origin = butterfly centre
    for sgn in (-1, 1):  # upper + lower wings, both sides
        p.ellipse(ox + sgn * 26 * scale, oy - 26 * scale,
                  21 * scale, 34 * scale, fill=wing + (255,))
        p.ellipse(ox + sgn * 30 * scale, oy + 8 * scale,
                  16 * scale, 22 * scale, fill=wing + (255,))
        p.ellipse(ox + sgn * 26 * scale, oy - 26 * scale,
                  21 * scale, 34 * scale, outline=edge + (255,),
                  width=max(2, int(3 * scale)))
        p.disc(ox + sgn * 27 * scale, oy - 30 * scale, 6 * scale,
               fill=spot + (255,))
    p.ellipse(ox, oy - 2 * scale, 6.5 * scale, 26 * scale,
              fill=body + (255,))                       # body
    p.disc(ox, oy - 30 * scale, 7.5 * scale, fill=body + (255,))  # head
    for sgn in (-1, 1):  # antennae with dot tips
        p.arc(ox + sgn * 9 * scale, oy - 44 * scale, 10 * scale, 12 * scale,
              200 if sgn < 0 else 250, 340 if sgn < 0 else 30,
              fill=body + (255,), width=max(2, int(2.5 * scale)))
        p.disc(ox + sgn * 17 * scale, oy - 50 * scale, 3 * scale,
               fill=body + (255,))
    if tilt:
        img = img.rotate(tilt, resample=Image.BICUBIC,
                         center=(box * S, box * S))
    return img, (int((cx - box) * S), int((cy - box) * S))


# ------------------------------------------------------------------ sky ---

SKY_STOPS = [(0.00, (110, 183, 224)), (0.30, (168, 220, 240)),
             (0.52, (255, 240, 190)), (0.66, (255, 214, 140)),
             (1.00, (255, 196, 110))]
SUN_C = (330, 330)
SUN_R = 108


def draw_sky(img):
    img.paste(sky_gradient((W * S, W * S), SKY_STOPS), (0, 0))


def draw_rainbow(img):
    from PIL import Image, ImageDraw, ImageFilter
    layer = Image.new("RGBA", (W * S, W * S), (0, 0, 0, 0))
    p = Pen(ImageDraw.Draw(layer))
    bands = [(255, 138, 122), (255, 178, 107), (255, 224, 102),
             (168, 224, 99), (122, 208, 255), (195, 155, 255)]
    cx, cy = 1030, 900
    for i, col in enumerate(bands):
        r = 545 + i * 21
        p.arc(cx, cy, r, r, 180, 272, fill=col + (120,), width=21)
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(3 * S)))


def draw_sun(img):
    from PIL import Image, ImageDraw, ImageFilter
    cx, cy = SUN_C
    glow = Image.new("RGBA", (W * S, W * S), (0, 0, 0, 0))
    g = Pen(ImageDraw.Draw(glow))
    for r, a in [(330, 26), (272, 40), (224, 58), (182, 82), (150, 110)]:
        g.disc(cx, cy, r, fill=(255, 205, 105, a))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(26 * S)))
    # rays: soft triangles fanning out, gently uneven lengths
    rays = Image.new("RGBA", (W * S, W * S), (0, 0, 0, 0))
    rp = Pen(ImageDraw.Draw(rays))
    for i in range(12):
        ang = math.radians(i * 30 + 12)
        ln = SUN_R + (64 if i % 2 == 0 else 40)
        wdt = 0.16
        x1 = cx + math.cos(ang - wdt) * (SUN_R + 8)
        y1 = cy + math.sin(ang - wdt) * (SUN_R + 8)
        x2 = cx + math.cos(ang + wdt) * (SUN_R + 8)
        y2 = cy + math.sin(ang + wdt) * (SUN_R + 8)
        x3 = cx + math.cos(ang) * ln
        y3 = cy + math.sin(ang) * ln
        rp.poly([(x1, y1), (x2, y2), (x3, y3)], fill=(255, 186, 92, 120))
    img.alpha_composite(rays.filter(ImageFilter.GaussianBlur(5 * S)))
    # disc + warm rim + a calm, happy face
    d = Pen(ImageDraw.Draw(img))
    d.disc(cx, cy, SUN_R, fill=(255, 201, 84, 255))
    d.disc(cx, cy, SUN_R - 10, fill=(255, 213, 109, 255))
    d.arc(cx, cy, SUN_R - 2, SUN_R - 2, 150, 260,
          fill=(255, 168, 66, 255), width=7)
    ink = (146, 90, 32, 255)
    for ex in (cx - 40, cx + 40):  # closed, contented eyes
        d.arc(ex, cy - 8, 17, 15, 200, 340, fill=ink, width=6)
    d.arc(cx, cy + 12, 30, 24, 20, 160, fill=ink, width=6)  # smile
    for bx in (cx - 68, cx + 68):  # rosy cheeks
        d.ellipse(bx, cy + 16, 15, 9, fill=(255, 138, 122, 110))


def puff_cloud(p, cx, cy, s, base=(255, 255, 255, 255),
               shade=(255, 205, 160, 255)):
    """One fluffy cloud: white puffs with a warm-lit underside."""
    puffs = [(-52, 10, 30), (-18, -8, 40), (24, -4, 36), (58, 12, 27),
             (0, 14, 34)]
    for dx, dy, r in puffs:
        p.ellipse(cx + dx * s, cy + (dy + 9) * s, r * s, (r * 0.72) * s,
                  fill=shade)
    for dx, dy, r in puffs:
        p.ellipse(cx + dx * s, cy + dy * s, r * s, (r * 0.72) * s, fill=base)


def draw_clouds(img):
    from PIL import Image, ImageDraw
    layer = Image.new("RGBA", (W * S, W * S), (0, 0, 0, 0))
    p = Pen(ImageDraw.Draw(layer))
    puff_cloud(p, 178, 138, 1.05)
    puff_cloud(p, 706, 218, 0.62)
    # heart cloud, upper right: two lobes and a point
    hx, hy, hs = 852, 118, 1.0
    p.disc(hx - 26 * hs, hy - 8 * hs, 27 * hs, fill=(255, 255, 255, 255))
    p.disc(hx + 26 * hs, hy - 8 * hs, 27 * hs, fill=(255, 255, 255, 255))
    p.poly([(hx - 48 * hs, hy), (hx + 48 * hs, hy),
            (hx, hy + 46 * hs)], fill=(255, 255, 255, 255))
    img.alpha_composite(layer)
    # two far-off birds, simple happy strokes
    d = Pen(ImageDraw.Draw(img))
    for bx, by, bs in [(140, 208, 12), (196, 178, 9)]:
        d.arc(bx - bs, by, bs, bs * 0.7, 200, 330,
              fill=(90, 90, 110, 170), width=3)
        d.arc(bx + bs, by, bs, bs * 0.7, 210, 340,
              fill=(90, 90, 110, 170), width=3)


def draw_hills(img):
    from PIL import Image, ImageDraw
    d = Pen(ImageDraw.Draw(img))
    d.poly([(0, 596), (0, 492), (150, 452), (330, 470), (520, 438),
            (720, 462), (900, 444), (1024, 466), (1024, 596)],
           fill=(172, 219, 128, 255))          # back hill, palest green
    d.poly([(0, 700), (0, 596), (200, 556), (430, 580), (660, 548),
            (860, 574), (1024, 552), (1024, 700)],
           fill=(139, 204, 94, 255))           # middle hill, a step deeper
    # warm rim light along the middle hill's crest
    d.line([(0, 596), (200, 556), (430, 580), (660, 548), (860, 574),
            (1024, 552)], width=4, fill=(255, 230, 150, 110))


def draw_meadow(img, rng):
    from PIL import Image, ImageDraw, ImageFilter
    base = sky_gradient((W * S, W * S),
                        [(0.0, (124, 195, 83)), (1.0, (84, 158, 56))])
    mask = Image.new("L", (W * S, W * S), 0)
    md = ImageDraw.Draw(mask)
    md.rectangle([0, 648 * S, W * S, W * S], fill=255)
    md.ellipse([(-160) * S, 560 * S, 700 * S, 900 * S], fill=255)
    img.paste(base, (0, 0), mask)
    d = Pen(ImageDraw.Draw(img))
    # pools of sunlight on the grass
    light = Image.new("RGBA", (W * S, W * S), (0, 0, 0, 0))
    lp = Pen(ImageDraw.Draw(light))
    for cx, cy, rx, ry in [(300, 800, 240, 60), (760, 880, 280, 70),
                           (520, 700, 200, 44)]:
        lp.ellipse(cx, cy, rx, ry, fill=(255, 240, 170, 60))
    img.alpha_composite(light.filter(ImageFilter.GaussianBlur(18 * S)))
    # grass tufts
    for _ in range(110):
        x = rng.uniform(8, 1016)
        y = rng.uniform(672, 1000)
        h = rng.uniform(9, 18) * (0.6 + (y - 672) / 500)
        col = (58, 128, 42, 200) if rng.random() < 0.5 else (104, 176, 66, 200)
        for dx in (-4, 0, 4):
            d.line([(x + dx, y), (x + dx * 1.7, y - h)], width=2.4, fill=col)
    # flowers: five petals and a heart, scattered denser near the front
    petals = [(255, 141, 178), (255, 255, 255), (255, 214, 92),
              (196, 164, 255), (255, 158, 100), (255, 110, 130)]
    for _ in range(150):
        x = rng.uniform(14, 1010)
        y = 676 + 320 * (rng.random() ** 0.8)  # denser toward the front
        sc = 0.55 + (y - 676) / 340 * 0.9
        col = petals[rng.randrange(len(petals))]
        d.line([(x, y + 8 * sc), (x, y)], width=2.2, fill=(52, 118, 40, 255))
        for k in range(5):
            a = math.radians(k * 72 - 90)
            d.disc(x + math.cos(a) * 5.2 * sc, y + math.sin(a) * 5.2 * sc,
                   4.4 * sc, fill=col + (255,))
        d.disc(x, y, 3.4 * sc, fill=(255, 176, 46, 255))
    # tiny white star-flowers sprinkled through the grass
    for _ in range(90):
        x = rng.uniform(10, 1014)
        y = rng.uniform(680, 1000)
        d.disc(x, y, rng.uniform(1.4, 2.6), fill=(255, 255, 240, 190))
    # one lucky ladybug on a front flower, for the careful viewer
    lx, ly = 828, 936
    d.disc(lx, ly, 7, fill=(214, 48, 48, 255))
    d.line([(lx, ly - 7), (lx, ly + 7)], width=2, fill=(40, 24, 24, 255))
    d.disc(lx - 3, ly - 3, 1.6, fill=(40, 24, 24, 255))
    d.disc(lx + 3, ly - 3, 1.6, fill=(40, 24, 24, 255))
    d.disc(lx - 3, ly + 3, 1.6, fill=(40, 24, 24, 255))
    d.disc(lx + 3, ly + 3, 1.6, fill=(40, 24, 24, 255))


# --------------------------------------------------------------- kitten ---

ORANGE = (245, 155, 78)
ORANGE_D = (217, 126, 51)     # stripes / shading
CREAM = (255, 240, 214)
INK = (74, 48, 36)            # warm brown line colour


def draw_kitten_body(img, rng):
    from PIL import Image, ImageDraw, ImageFilter
    d = Pen(ImageDraw.Draw(img))
    # soft contact shadow
    sh = Image.new("RGBA", (W * S, W * S), (0, 0, 0, 0))
    Pen(ImageDraw.Draw(sh)).ellipse(512, 908, 205, 30,
                                    fill=(30, 60, 20, 110))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10 * S)))
    # tail: a fat curl wrapping around the right side to the front
    tail = [(636, 868), (712, 884), (762, 856), (754, 810)]
    d.line(tail, width=46, fill=ORANGE + (255,))
    for tx, ty in [(700, 882), (742, 860)]:
        d.line([(tx - 10, ty - 12), (tx + 8, ty + 16)], width=9,
               fill=ORANGE_D + (255,))
    d.disc(754, 810, 23, fill=CREAM + (255,))  # cream tail tip
    # haunches and body
    d.ellipse(408, 852, 66, 52, fill=ORANGE + (255,))
    d.ellipse(616, 852, 66, 52, fill=ORANGE + (255,))
    d.ellipse(512, 772, 152, 132, fill=ORANGE + (255,))
    d.ellipse(512, 742, 128, 104, fill=(247, 168, 96, 255))  # lit top
    d.ellipse(512, 816, 76, 66, fill=CREAM + (255,))          # belly
    # flank stripes: short diagonal marks low on each side
    for pts in [[(376, 756), (402, 768)], [(378, 792), (404, 802)],
                [(648, 756), (622, 768)], [(646, 792), (620, 802)]]:
        d.line(pts, width=7, fill=ORANGE_D + (255,))
    # front paws, neat together below the belly, with toe lines
    for px_ in (466, 558):
        d.ellipse(px_, 894, 32, 18, fill=CREAM + (255,))
        for tx in (-10, 3):
            d.line([(px_ + tx, 884), (px_ + tx, 896)], width=2.4,
                   fill=(206, 164, 120, 255))
    # sun-side rim light down the left of the body
    d.arc(512, 772, 150, 130, 130, 205, fill=(255, 233, 184, 220), width=7)


def draw_kitten_head(img):
    """Head on its own layer, tilted toward the butterfly, then pasted."""
    from PIL import Image, ImageDraw
    box = 190  # layer half-size, 1024-space
    layer = Image.new("RGBA", (box * 2 * S, box * 2 * S), (0, 0, 0, 0))
    p = Pen(ImageDraw.Draw(layer))
    cx, cy = box, box + 16  # head centre inside the layer
    # ears first, behind the skull
    for sgn, lean in [(-1, -8), (1, 8)]:
        ex = cx + sgn * 76
        p.poly([(ex - 34, cy - 66), (ex + 30, cy - 72),
                (ex + lean, cy - 128)], fill=ORANGE + (255,))
        p.poly([(ex - 15, cy - 72), (ex + 16, cy - 76),
                (ex + lean, cy - 106)], fill=(255, 168, 178, 255))
    p.ellipse(cx, cy, 122, 106, fill=ORANGE + (255,))          # skull
    p.ellipse(cx - 16, cy - 18, 96, 76, fill=(247, 168, 96, 255))
    for dx in (-26, 0, 26):  # forehead stripes
        p.line([(cx + dx, cy - 100), (cx + dx, cy - 78)], width=7,
               fill=ORANGE_D + (255,))
    for sgn in (-1, 1):  # cheeks
        p.ellipse(cx + sgn * 74, cy + 34, 21, 12,
                  fill=(255, 138, 150, 110))
    p.ellipse(cx, cy + 40, 60, 38, fill=CREAM + (255,))        # muzzle
    # cross-eyed gaze: pupils up and inward, locked on the nose butterfly
    for sgn in (-1, 1):
        ex = cx + sgn * 44
        p.disc(ex, cy - 8, 13, fill=(255, 255, 255, 255))
        p.disc(ex - sgn * 4, cy - 12, 9.5, fill=INK + (255,))
        p.disc(ex - sgn * 6, cy - 16, 3.2, fill=(255, 255, 255, 255))
    # nose: a small pink heart of a nose
    p.poly([(cx - 11, cy + 20), (cx + 11, cy + 20), (cx, cy + 33)],
           fill=(244, 114, 140, 255))
    p.ellipse(cx, cy + 19, 11, 6, fill=(244, 114, 140, 255))
    p.disc(cx - 4, cy + 17, 2.6, fill=(255, 220, 228, 255))
    # mouth: a tiny open smile under the nose
    p.arc(cx - 10, cy + 30, 10, 8, 10, 170, fill=INK + (255,), width=4)
    p.arc(cx + 10, cy + 30, 10, 8, 10, 170, fill=INK + (255,), width=4)
    p.ellipse(cx, cy + 42, 7, 5, fill=(226, 110, 120, 255))  # tongue tip
    for sgn in (-1, 1):  # whiskers
        for k, dy in enumerate((-6, 4, 14)):
            p.line([(cx + sgn * 52, cy + 26 + dy),
                    (cx + sgn * (104 + k * 4), cy + 18 + dy * 2)],
                   width=2.6, fill=(190, 140, 100, 190))
    # rim light on the sun side of the skull
    p.arc(cx, cy, 120, 104, 140, 215, fill=(255, 233, 184, 220), width=7)
    layer = layer.rotate(6, resample=Image.BICUBIC,
                         center=(box * S, (box + 16) * S))
    # head centre lands at canvas (512, 560): low enough to sit ON the body
    img.alpha_composite(layer, (int((512 - box) * S), int((544 - box) * S)))
    # THE moment: a blue butterfly settles on the very tip of the nose
    bf, pos = butterfly_layer(512, 556, 0.56, (52, 62, 96), (96, 178, 255),
                              (46, 110, 200), (255, 255, 255), tilt=-6)
    img.alpha_composite(bf, pos)


def draw_second_butterfly(img, rng):
    from PIL import Image, ImageDraw
    # a dotted loop-the-loop flight trail, then the butterfly itself
    layer = Image.new("RGBA", (W * S, W * S), (0, 0, 0, 0))
    d = Pen(ImageDraw.Draw(layer))
    pts = []
    for i in range(61):
        t = i / 60
        x = (1 - t) ** 2 * 64 + 2 * (1 - t) * t * 128 + t ** 2 * 204
        y = (1 - t) ** 2 * 548 + 2 * (1 - t) * t * 436 + t ** 2 * 332
        pts.append((x, y))
    for i in range(0, len(pts), 3):
        d.disc(pts[i][0], pts[i][1], 2.6, fill=(255, 255, 255, 150))
    img.alpha_composite(layer)
    bf, pos = butterfly_layer(212, 322, 0.62, (84, 52, 84), (255, 158, 196),
                              (214, 92, 150), (255, 255, 255), tilt=14)
    img.alpha_composite(bf, pos)


def draw_sparkles(img):
    for cx, cy, r in [(716, 462, 17), (308, 636, 13), (668, 268, 11),
                      (206, 470, 9)]:
        sp, pos = sparkle_layer(cx, cy, r, (255, 246, 200))
        img.alpha_composite(sp, pos)


def render():
    from PIL import Image
    rng = random.Random(SEED)
    img = Image.new("RGBA", (W * S, W * S), (0, 0, 0, 255))
    draw_sky(img)
    draw_rainbow(img)
    draw_sun(img)
    draw_clouds(img)
    draw_hills(img)
    draw_meadow(img, rng)
    draw_kitten_body(img, rng)
    draw_kitten_head(img)
    draw_second_butterfly(img, rng)
    draw_sparkles(img)
    return img.convert("RGB").resize((W, W), Image.LANCZOS)


def main() -> int:
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "entry.png"
    try:
        from PIL import Image  # noqa: F401
        img = render()
        img.save(target, format="PNG", optimize=True)
        how = "rendered"
    except ImportError:
        # Pillow missing from the runtime: ship the identical bytes.
        shutil.copyfile(ASSET, target)
        how = "copied pre-rendered asset (Pillow unavailable)"
    size = target.stat().st_size
    if size > 1_048_576:
        raise SystemExit(f"entry.png too large: {size} bytes > 1 MiB")
    print(f"entry.png: {size} bytes ({how})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


