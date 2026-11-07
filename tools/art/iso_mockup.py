#!/usr/bin/env python3
"""2.5D 아이소메트릭 마을 목업. 640×360 내부 해상도, 텍셀 16/m, 3배 확대 저장."""
import json
import os
import random
import sys

import numpy as np
from PIL import Image

from face_compose import ROOT, face, hexc
from iso_render import Camera, box, gable, hip, render

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "images")
W, H, SCALE = 640, 360, 3

atlas = np.array(Image.open(os.path.join(ROOT, "assets", "textures", "material_atlas.png")))
midx = json.load(open(os.path.join(ROOT, "data", "visual", "material_atlas.json"), encoding="utf-8"))["materials"]
pal = json.load(open(os.path.join(ROOT, "data", "visual", "palettes.json"), encoding="utf-8"))
fmeta = json.load(open(os.path.join(ROOT, "data", "visual", "face_atlas.json"), encoding="utf-8"))


def tiles(name):
    var = 0
    if name.endswith("#1"):
        name, var = name[:-2], 1
    k = midx[name][var]
    return atlas[(k // 8) * 8:(k // 8) * 8 + 8, (k % 8) * 8:(k % 8) * 8 + 8]


def rgb(h):
    c = hexc(h)
    return (int(c[0]), int(c[1]), int(c[2]))


P = []

# ---------------------------------------------------------------- 땅
for (x0, z0, x1, z1, m) in [(-30, -30, 60, 13, "풀*"), (-30, 13, 60, 15.5, "흙길*"), (-30, 15.5, -2, 40, "풀*"),
                            (-2, 15.5, 12, 17, "풀*"), (-2, 17, 12, 24, "작물 익음"), (-2, 24, 60, 40, "풀*"),
                            (12, 15.5, 60, 24, "풀*")]:
    P.append(box(x0, -1, z0, x1, 0, z1, m, tag="ground"))


# ---------------------------------------------------------------- 나무, 바위, 울타리
def tree(x, z, h=2.5, r=1.25):
    P.append(box(x - r, 0, z - r + 0.25, x + r - 0.25, 0.01, z + r, (92, 150, 72), tag="shadow"))
    P.append(box(x - 0.25, 0, z - 0.25, x + 0.25, h, z + 0.25, "나무껍질"))
    P.append(box(x - r, h - 0.5, z - r, x + r, h + 1.0, z + r, "나뭇잎#1", tag=f"leaf{x}{z}"))
    P.append(box(x - r + 0.5, h + 1.0, z - r + 0.5, x + r - 0.5, h + 1.75, z + r - 0.5, "나뭇잎", tag=f"leaf{x}{z}"))


for x, z in ((-3, 4), (5.5, 1.5), (34, 12), (16, 19), (29, 20), (-4, 11)):
    tree(x, z)
for x, z, s in ((33, 17, 1.0), (34.2, 18, 0.5), (31.8, 18.2, 0.5)):
    P.append(box(x, 0, z, x + s, s * 0.8, z + s, "바위"))
for x in np.arange(-2, 12.5, 1.5):
    P.append(box(x, 0, 16.7, x + 0.25, 0.9, 16.95, "나무 판자", tag="fence"))
P.append(box(-2, 0.55, 16.75, 12.25, 0.75, 16.9, "나무 판자", tag="fence"))

# ---------------------------------------------------------------- 움막
P.append(box(0, 0, 7, 4.5, 2.0, 11.5, "나뭇가지 엮음"))
P.append(hip(-0.4, 6.6, 4.9, 11.9, 2.0, 4.4, "초가"))
P.append(box(1.75, 0, 11.5, 2.75, 1.75, 11.55, "나무 판자", "나무 판자", "나무 판자"))
for i in range(3):
    for j in range(2 - i // 2):
        P.append(box(4.6, i * 0.25, 9 + j * 0.5, 5.6, i * 0.25 + 0.25, 9.5 + j * 0.5, "통나무", "통나무", "나무껍질"))

# ---------------------------------------------------------------- 가옥
P.append(box(7, 0, 5, 15, 0.5, 11, "돌"))
P.append(box(7, 0.5, 5, 15, 2.75, 11, "회벽"))
for x in (7, 9.5, 12.5, 14.75):
    P.append(box(x, 0.5, 10.95, x + 0.25, 2.75, 11.05, "나무 판자#1", tag=f"post{x}"))
for z in (5, 8, 10.75):
    P.append(box(14.95, 0.5, z, 15.05, 2.75, z + 0.25, "나무 판자#1", tag=f"postz{z}"))
P.append(gable(6.6, 4.6, 15.4, 11.4, 2.75, 5.25, "너와", "회벽", "x"))
P.append(box(13, 3.0, 6.5, 13.75, 6.0, 7.25, "돌", tag="chim1"))
for x in (8.0, 10.0, 13.25):
    P.append(box(x, 1.25, 11.0, x + 0.5, 1.75, 11.06, "덧문 창#1" if x == 10.0 else "덧문 창", tag=f"w{x}"))
for z in (6.0, 9.25):
    P.append(box(15.0, 1.25, z, 15.06, 1.75, z + 0.5, "덧문 창", tag=f"wz{z}"))
P.append(box(11.0, 0.5, 11.0, 12.0, 2.5, 11.08, "나무 판자", tag="door1"))
P.append(box(15.5, 0, 9, 17.5, 0.12, 11.5, "작물 자람", "흙", "흙"))  # 텃밭

# ---------------------------------------------------------------- 저택
P.append(box(19, 0, 1, 31, 1.0, 10, "돌"))
P.append(box(19, 1.0, 1, 31, 5.5, 10, "회벽#1"))
P.append(box(19, 3.25, 9.95, 31, 3.5, 10.05, "나무 판자#1", tag="band"))
P.append(box(30.95, 3.25, 1, 31.05, 3.5, 10, "나무 판자#1", tag="bandx"))
P.append(hip(18.5, 0.5, 31.5, 10.5, 5.5, 8.25, "기와", inset_x=3.5, inset_z=4.75))
for cx in (21.5, 28.5):
    P.append(box(cx, 6.0, 4.5, cx + 0.75, 9.5, 5.25, "벽돌", tag=f"chim{cx}"))
for x in np.arange(20.0, 30.5, 1.5):
    P.append(box(x, 4.0, 10.0, x + 0.5, 4.5, 10.06, "격자 창#1", tag=f"mw{x}"))
    if abs(x - 24.5) > 1.0:
        P.append(box(x, 1.75, 10.0, x + 0.5, 2.25, 10.06, "격자 창#1", tag=f"mw2{x}"))
for z in np.arange(2.0, 9.5, 1.5):
    P.append(box(31.0, 4.0, z, 31.06, 4.5, z + 0.5, "격자 창#1", tag=f"mwz{z}"))
P.append(box(24.0, 1.0, 10.0, 25.5, 3.25, 10.1, "나무 판자", tag="door2"))
P.append(box(24.5, 0, 10.1, 25.0, 0.25, 12.0, "돌 바닥", tag="path"))
P.append(box(25.0, 8.25, 5.25, 25.12, 11.0, 5.37, (59, 42, 42), tag="pole"))
P.append(box(25.12, 10.25, 5.25, 26.4, 10.9, 5.3, rgb("#b8323f"), tag="flag"))
for x in np.arange(19, 31.5, 1.0):
    P.append(box(x, 0, 11.6, x + 0.25, 0.8, 11.85, "돌", tag="wall"))
P.append(box(19, 0.5, 11.65, 31.25, 0.75, 11.8, "돌", tag="wall"))

# ---------------------------------------------------------------- 주민
skins = pal["skin"]
hairs = pal["hair"]
eyes = list(pal["eye"].values())
shapes = fmeta["layout"]["face_shapes"]
cl = pal["cloth"]


def side_tex(skin, hair, long_hair):
    t = np.zeros((8, 8, 4), np.uint8)
    t[:, :] = hexc(skin)
    rows = 7 if long_hair else 3
    t[:rows, :] = hexc(hair)
    t[3:5, 2] = hexc(hair) * 0.8 if not long_hair else t[3:5, 2]
    return t


def solid_tex(color, belt=None, belt_row=5):
    t = np.zeros((8, 8, 4), np.uint8)
    t[:, :] = hexc(color)
    if belt:
        t[belt_row, :] = hexc(belt)
    return t


SHADOW = (92, 150, 72)


def person(x, z, facing, skin, hair, eye, cloth, pants, shape, eyes_kind="점 눈", mouth="기본",
           child=False, elder=False, long_hair=False, hat=None, overlays=(), tag="p"):
    s = 1 / 16
    P.append(box(x - 5 * s, 0, z - 3 * s, x + 5 * s, 0.01, z + 4 * s, SHADOW, tag="shadow"))
    leg_h, torso_h = (3 * s, 5 * s) if child else (6 * s, 7 * s)
    f = face(shape, hexc(skin), hexc(hair), hexc(eye), eyes_kind, "없음", mouth, overlays)
    side = side_tex(skin, hair, long_hair)
    back = solid_tex(hair)
    hx0, hz0 = x - 4 * s, z - 4 * s
    y_head = leg_h + torso_h
    if facing == "z":
        P.append(box(hx0, y_head, hz0, hx0 + 8 * s, y_head + 8 * s, hz0 + 8 * s, back, f, side, tag=tag))
    else:
        P.append(box(hx0, y_head, hz0, hx0 + 8 * s, y_head + 8 * s, hz0 + 8 * s, back, side, f, tag=tag))
    if hat:
        P.append(box(hx0 - s, y_head + 7 * s, hz0 - s, hx0 + 9 * s, y_head + 8.5 * s, hz0 + 9 * s, "초가", tag=tag))
    shirt = solid_tex(cloth, belt=pal["outline"] if not child else None, belt_row=5)
    P.append(box(x - 3 * s, leg_h, z - 2 * s, x + 3 * s, leg_h + torso_h, z + 2 * s, solid_tex(cloth), shirt, shirt, tag=tag))
    for dx in (-3 * s, 2 * s):
        ax = x + (dx - 1 * s if dx < 0 else dx + 1 * s)
        P.append(box(ax, leg_h + 1 * s, z - 1 * s, ax + 1 * s, leg_h + torso_h, z + 1 * s, solid_tex(cloth), shirt, shirt, tag=tag))
    pt = solid_tex(pants)
    pt[-1, :] = hexc("#5a4040")
    for dx in (-3 * s, 1 * s):
        P.append(box(x + dx, 0, z - 1 * s, x + dx + 2 * s, leg_h, z + 1 * s, pt, pt, pt, tag=tag))
    if elder:
        P.append(box(x + 4 * s, 0, z + 1 * s, x + 5 * s, leg_h + torso_h, z + 2 * s, rgb("#a26a3a"), tag=tag))


people = [
    (2.5, 14.0, "z", dict(skin=skins[1], hair=hairs["갈색"], eye=eyes[0], cloth=cl["평민"][0], pants="#6b5040", shape=shapes[0], hat=True)),
    (3.6, 14.6, "z", dict(skin=skins[2], hair=hairs["검정"], eye=eyes[0], cloth=cl["평민"][2], pants="#5a4a3a", shape=shapes[5], child=True, eyes_kind="큰 눈", mouth="미소")),
    (5.0, 14.1, "x", dict(skin=skins[0], hair=hairs["회색"], eye=eyes[2], cloth=cl["노예"][1], pants="#6b5a4a", shape=shapes[3], elder=True, overlays=["주름"])),
    (9.5, 14.4, "z", dict(skin=skins[3], hair=hairs["적발"], eye=eyes[1], cloth=cl["장인상인"][0], pants="#4a3f5c", shape=shapes[1], long_hair=True, overlays=["주근깨"])),
    (11.2, 13.8, "x", dict(skin=skins[2], hair=hairs["갈색"], eye=eyes[1], cloth=cl["평민"][1], pants="#5a4a3a", shape=shapes[2], child=True, eyes_kind="둥근 눈")),
    (23.0, 14.3, "z", dict(skin=skins[4], hair=hairs["검정"], eye=eyes[0], cloth=cl["귀족"][1], pants="#2f2a3a", shape=shapes[4], mouth="무표정")),
    (24.6, 14.5, "z", dict(skin=skins[0], hair=hairs["금발"], eye=eyes[2], cloth=cl["지주기사"][0], pants="#3f3a5a", shape=shapes[2], long_hair=True, mouth="미소", overlays=["볼 홍조"])),
    (15.5, 14.2, "x", dict(skin=skins[1], hair=hairs["금발"], eye=eyes[2], cloth=cl["평민"][3], pants="#5a4a3a", shape=shapes[0])),
    (26.5, 12.6, "x", dict(skin=skins[2], hair=hairs["갈색"], eye=eyes[0], cloth="#cfd8e0", pants="#6b655f", shape=shapes[4], mouth="무표정")),
    (21.0, 12.9, "z", dict(skin=skins[3], hair=hairs["검정"], eye=eyes[0], cloth=cl["노예"][0], pants="#8a7a64", shape=shapes[1], long_hair=True)),
    (24.0, 15.2, "z", dict(skin=skins[0], hair=hairs["적발"], eye=eyes[1], cloth=cl["귀족"][0], pants="#3a2a3a", shape=shapes[5], child=True, eyes_kind="반짝 눈", mouth="미소")),
]
for k, (x, z, fc, spec) in enumerate(people):
    person(x, z, fc, tag=f"person{k}", **spec)

os.makedirs(OUT_DIR, exist_ok=True)
for name, center in (("mockup_iso_village.png", (7.0, 1.0, 12.0)), ("mockup_iso_manor.png", (24.5, 3.0, 9.0))):
    cam = Camera(W, H, center=center, px_per_m_x=16.0)
    img = render(cam, P, tiles)
    out = os.path.join(OUT_DIR, name)
    Image.fromarray(img, "RGB").resize((W * SCALE, H * SCALE), Image.NEAREST).save(out)
    print(out)
