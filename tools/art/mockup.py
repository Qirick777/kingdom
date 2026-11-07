#!/usr/bin/env python3
"""저해상도 장면 목업(정면): 480×270 내부 해상도, 0.5m 조각 = 8픽셀. 3배로 확대해 저장."""
import json
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw

from face_compose import ROOT, face, hexc

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "images", "mockup_village.png")
W, H = 480, 270
atlas = np.array(Image.open(os.path.join(ROOT, "assets", "textures", "material_atlas.png")))
midx = json.load(open(os.path.join(ROOT, "data", "visual", "material_atlas.json"), encoding="utf-8"))["materials"]
pal = json.load(open(os.path.join(ROOT, "data", "visual", "palettes.json"), encoding="utf-8"))
fmeta = json.load(open(os.path.join(ROOT, "data", "visual", "face_atlas.json"), encoding="utf-8"))
OUTL = np.array([59, 42, 42, 255], dtype=np.uint8)


def tile(name, v=0):
    k = midx[name][v]
    return atlas[(k // 8) * 8:(k // 8) * 8 + 8, (k % 8) * 8:(k % 8) * 8 + 8]


img = np.zeros((H, W, 4), dtype=np.uint8)


def fill_mask(mask, name, v=0, ox=0, oy=0):
    t = tile(name, v)
    ys, xs = np.nonzero(mask)
    for y, x in zip(ys, xs):
        px = t[(y - oy) % 8, (x - ox) % 8]
        if px[3]:
            img[y, x] = px


def mask_poly(pts):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(pts, fill=1)
    return np.array(m) > 0


def mask_rect(x0, y0, x1, y1):
    m = np.zeros((H, W), dtype=bool)
    m[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] = True
    return m


def outline_mask(mask, col=OUTL):
    edge = mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1))
    img[edge] = col


def put_sprite(sp, x0, y0):
    h, w = sp.shape[:2]
    for y in range(h):
        for x in range(w):
            if sp[y, x, 3] and 0 <= y0 + y < H and 0 <= x0 + x < W:
                img[y0 + y, x0 + x] = sp[y, x]


def shade(c, k):
    c = np.array(c, dtype=np.float32)
    if k >= 0:
        c[:3] = c[:3] + (255 - c[:3]) * k
    else:
        c[:3] = c[:3] * (1 + k)
    return c.astype(np.uint8)


# ---------------------------------------------------------------- 배경
for y in range(H):
    t = y / H
    img[y, :] = np.array([int(191 + 40 * t), int(230 + 18 * t), 255, 255], dtype=np.uint8)
hill = mask_poly([(0, 170), (60, 150), (140, 158), (220, 140), (320, 152), (400, 138), (480, 150), (480, 200), (0, 200)])
img[hill] = hexc("#b5e39a")
hill2 = mask_poly([(0, 182), (90, 168), (200, 178), (300, 166), (420, 176), (480, 170), (480, 200), (0, 200)])
img[hill2] = hexc("#9ad682")
GROUND = 206
fill_mask(mask_rect(0, GROUND, W, H), "풀", 0)
fill_mask(mask_rect(0, 228, W, 246), "흙길", 0)
outline_mask(mask_rect(-1, 228, W + 1, 246), np.array([168, 120, 82, 255], dtype=np.uint8))
fill_mask(mask_rect(0, 252, W, H), "작물 익음", 0)

# ---------------------------------------------------------------- 나무
def tree(x, y, s=1.0):
    trunk = mask_rect(x - 3, y - 18, x + 3, y)
    fill_mask(trunk, "나무껍질")
    outline_mask(trunk)
    crown = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(crown)
    r = int(14 * s)
    d.ellipse([x - r, y - 18 - 2 * r, x + r, y - 18 + 4], fill=1)
    d.ellipse([x - r - 6, y - 18 - r - 4, x + 2, y - 14], fill=1)
    d.ellipse([x - 2, y - 18 - r - 2, x + r + 6, y - 14], fill=1)
    m = np.array(crown) > 0
    fill_mask(m, "나뭇잎", 1)
    outline_mask(m, np.array([47, 110, 60, 255], dtype=np.uint8))


tree(14, GROUND, 0.9)
tree(470, GROUND, 1.1)

# ---------------------------------------------------------------- 집
def door(x, y, w=12, h=24):
    m = mask_rect(x, y, x + w, y + h)
    fill_mask(m, "나무 판자", 0, x, y)
    outline_mask(m)
    img[y + h // 2, x + w - 3] = hexc("#ffd34d")


def window(x, y, name, v=0):
    put_sprite(tile(name, v), x, y)


# 움막: 5m 폭 = 80px, 벽 2m = 32px
hx = 36
wall = mask_rect(hx, GROUND - 30, hx + 72, GROUND)
fill_mask(wall, "나뭇가지 엮음", 0)
outline_mask(wall)
roof = mask_poly([(hx - 8, GROUND - 26), (hx + 36, GROUND - 66), (hx + 80, GROUND - 26)])
fill_mask(roof, "초가", 0)
outline_mask(roof)
door(hx + 30, GROUND - 22, 12, 22)
for k in range(4):  # 장작더미
    put_sprite(np.tile(tile("통나무", 0)[:4], (1, 1, 1)), hx + 76 + (k % 2) * 8, GROUND - 4 - (k // 2) * 4)

# 가옥: 8m = 128px, 벽 2.5m = 40px
gx = 130
wall = mask_rect(gx, GROUND - 40, gx + 120, GROUND)
fill_mask(wall, "회벽", 0)
for xx in range(gx, gx + 121, 24):
    img[GROUND - 40:GROUND, xx:xx + 2] = hexc("#774a2a")
img[GROUND - 41:GROUND - 38, gx:gx + 120] = hexc("#774a2a")
fill_mask(mask_rect(gx, GROUND - 6, gx + 120, GROUND), "돌", 0)
outline_mask(wall)
roof = mask_poly([(gx - 10, GROUND - 38), (gx + 60, GROUND - 84), (gx + 130, GROUND - 38)])
fill_mask(roof, "너와", 0)
outline_mask(roof)
chim = mask_rect(gx + 92, GROUND - 82, gx + 102, GROUND - 58)
fill_mask(chim, "돌", 1)
outline_mask(chim)
window(gx + 14, GROUND - 30, "덧문 창", 0)
window(gx + 38, GROUND - 30, "덧문 창", 1)
window(gx + 84, GROUND - 30, "덧문 창", 0)
door(gx + 58, GROUND - 26, 14, 26)
fence = mask_rect(gx + 122, GROUND - 10, gx + 150, GROUND - 8)
img[fence] = hexc("#a26a3a")
for xx in range(gx + 122, gx + 152, 6):
    img[GROUND - 14:GROUND, xx:xx + 2] = hexc("#774a2a")

# 저택: 12m = 192px, 2층 = 72px
mx = 282
wall = mask_rect(mx, GROUND - 74, mx + 176, GROUND)
fill_mask(wall, "회벽", 1)
fill_mask(mask_rect(mx, GROUND - 16, mx + 176, GROUND), "돌", 0)
img[GROUND - 42:GROUND - 40, mx:mx + 176] = hexc("#a26a3a")
outline_mask(wall)
roof = mask_poly([(mx - 10, GROUND - 72), (mx + 26, GROUND - 112), (mx + 150, GROUND - 112), (mx + 186, GROUND - 72)])
fill_mask(roof, "기와", 0)
outline_mask(roof)
tower = mask_rect(mx + 140, GROUND - 104, mx + 170, GROUND - 74)
for xx in range(mx + 10, mx + 170, 24):
    window(xx, GROUND - 66, "격자 창", 1)
for xx in (mx + 10, mx + 34, mx + 130, mx + 154):
    window(xx, GROUND - 34, "격자 창", 1)
door(mx + 78, GROUND - 32, 20, 32)
for cx in (mx + 40, mx + 140):
    chim = mask_rect(cx, GROUND - 124, cx + 10, GROUND - 100)
    fill_mask(chim, "벽돌", 0)
    outline_mask(chim)
flag = mask_poly([(mx + 88, GROUND - 140), (mx + 104, GROUND - 136), (mx + 88, GROUND - 132)])
img[GROUND - 142:GROUND - 112, mx + 87] = hexc("#3b2a2a")
img[flag] = hexc("#b8323f")

# ---------------------------------------------------------------- 주민
rng = random.Random(4)
shapes = fmeta["layout"]["face_shapes"]
skins = [hexc(c) for c in pal["skin"]]
hairs = {k: hexc(v) for k, v in pal["hair"].items()}
eyes = [hexc(c) for c in pal["eye"].values()]


def person(skin, hair, eye, cloth, pants, shape, eyes_kind="점 눈", mouth="기본", child=False, elder=False,
           long_hair=False, hat=None, overlays=()):
    f = face(shape, skin, hair, eye, eyes_kind, "없음", mouth, overlays)
    torso_h, leg_h = (5, 3) if child else (7, 6)
    h = 1 + 8 + torso_h + leg_h
    sp = np.zeros((h, 12, 4), dtype=np.uint8)
    hc = np.array(hair, dtype=np.uint8)
    sp[0, 2:10] = hc                                    # 머리 위
    sp[1:9, 2:10] = f                                   # 얼굴
    sp[1:4, 1] = hc
    sp[1:4, 10] = hc
    if long_hair:
        sp[1:9, 1] = hc
        sp[1:9, 10] = hc
    if hat:
        sp[0, 1:11] = hexc(hat)
        sp[1, 2:10] = hexc(hat)
    cc = np.array(cloth, dtype=np.uint8)
    y0 = 9
    sp[y0:y0 + torso_h, 3:9] = cc
    sp[y0:y0 + torso_h, 2] = shade(cc, -0.15)
    sp[y0:y0 + torso_h, 9] = shade(cc, -0.15)
    sp[y0 + torso_h - 1, 2] = np.array(skin, dtype=np.uint8)
    sp[y0 + torso_h - 1, 9] = np.array(skin, dtype=np.uint8)
    sp[y0 + torso_h - 2, 3:9] = shade(cc, -0.3)        # 허리띠
    pc = np.array(pants, dtype=np.uint8)
    y1 = y0 + torso_h
    sp[y1:y1 + leg_h, 3:5] = pc
    sp[y1:y1 + leg_h, 7:9] = pc
    sp[y1 + leg_h - 1, 3:5] = hexc("#5a4040")
    sp[y1 + leg_h - 1, 7:9] = hexc("#5a4040")
    if elder:
        sp[y0 + 2:h, 10] = hexc("#a26a3a")             # 지팡이
    # 외곽선
    a = sp[..., 3] > 0
    out = sp.copy()
    big = np.zeros((h + 2, 14, 4), dtype=np.uint8)
    big[1:-1, 1:-1] = out
    m = big[..., 3] > 0
    edge = (~m) & (np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1))
    big[edge] = OUTL
    return big


cl = pal["cloth"]
people = [
    dict(skin=skins[1], hair=hairs["갈색"], eye=eyes[0], cloth=hexc(cl["평민"][0]), pants=hexc("#6b5040"), shape=shapes[0], hat="#f5d873"),
    dict(skin=skins[2], hair=hairs["검정"], eye=eyes[0], cloth=hexc(cl["평민"][2]), pants=hexc("#5a4a3a"), shape=shapes[5], child=True, eyes_kind="큰 눈", mouth="미소"),
    dict(skin=skins[0], hair=hairs["회색"], eye=eyes[2], cloth=hexc(cl["노예"][1]), pants=hexc("#6b5a4a"), shape=shapes[3], elder=True, overlays=["주름"]),
    dict(skin=skins[3], hair=hairs["적발"], eye=eyes[1], cloth=hexc(cl["장인상인"][0]), pants=hexc("#4a3f5c"), shape=shapes[1], long_hair=True, overlays=["주근깨"]),
    dict(skin=skins[4], hair=hairs["검정"], eye=eyes[0], cloth=hexc(cl["귀족"][1]), pants=hexc("#2f2a3a"), shape=shapes[4], mouth="무표정"),
    dict(skin=skins[0], hair=hairs["금발"], eye=eyes[2], cloth=hexc(cl["지주기사"][0]), pants=hexc("#3f3a5a"), shape=shapes[2], long_hair=True, mouth="미소", overlays=["볼 홍조"]),
    dict(skin=skins[2], hair=hairs["갈색"], eye=eyes[1], cloth=hexc(cl["평민"][1]), pants=hexc("#5a4a3a"), shape=shapes[2], child=True, eyes_kind="둥근 눈"),
]
xs = [70, 92, 112, 200, 330, 352, 250]
for x, p in zip(xs, people):
    sp = person(**p)
    put_sprite(sp, x, 240 - sp.shape[0])

out = Image.fromarray(img, "RGBA").resize((W * 3, H * 3), Image.NEAREST)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
out.save(OUT)
print(OUT)
