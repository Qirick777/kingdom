#!/usr/bin/env python3
"""얼굴 아틀라스를 셰이더처럼 조립해 본다: 피부 + 머리카락 + 눈(좌우, 눈색) + 눈썹 + 입 + 덧그림."""
import json
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets", "_preview", "faces.png")

atlas = np.array(Image.open(os.path.join(ROOT, "assets", "faces", "face_atlas.png")))
meta = json.load(open(os.path.join(ROOT, "data", "visual", "face_atlas.json"), encoding="utf-8"))
pal = json.load(open(os.path.join(ROOT, "data", "visual", "palettes.json"), encoding="utf-8"))
font = ImageFont.truetype(os.path.join(ROOT, "assets", "fonts", "NanumGothic.ttf"), 13)


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)] + [255], dtype=np.float32)


def cell(group, name):
    p = meta["parts"][group][name]
    k = p["cell"]
    x, y = (k % 8) * 16, (k // 8) * 16
    c = atlas[y:y + 16, x:x + 16].astype(np.float32)
    w, h = p["w"], p["h"]
    ox, oy = (16 - w) // 2, (16 - h) // 2
    return c[oy:oy + h, ox:ox + w] if group != "덧그림" else c


def paste(face, part, cx, cy, eye_col=None, mirror=False, hair_col=None):
    if mirror:
        part = part[:, ::-1]
    h, w = part.shape[:2]
    x0 = int(round(cx - w / 2))
    y0 = int(round(cy - h / 2))
    for y in range(h):
        for x in range(w):
            px = part[y, x]
            if px[3] == 0:
                continue
            col = px.copy()
            if eye_col is not None and px[0] == px[1] == px[2] and px[0] in (128, 96):
                col = eye_col * (px[0] / 128.0)
                col[3] = 255
            if hair_col is not None and px[0] == px[1] == px[2] == 64:
                col = hair_col * 0.7
                col[3] = 255
            fx, fy = x0 + x, y0 + y
            if 0 <= fx < 16 and 0 <= fy < 16:
                a = col[3] / 255.0
                face[fy, fx, :3] = face[fy, fx, :3] * (1 - a) + col[:3] * a


def make_face(rng, shape, skin, hair, eye_col, eye, brow, mouth, overlays):
    L = meta["layout"]
    face = np.zeros((16, 16, 4), dtype=np.float32)
    face[:, :] = skin
    face[0:3, :] = hair
    face[3, :] = hair
    face[3, 4:12] = skin
    dx, dy = shape["eye_dx"], shape["eye_dy"]
    ey = L["eye_y"] + dy
    if eye == "짝눈":
        paste(face, cell("눈", "짝눈 작은"), 8 - dx, ey, eye_col)
        paste(face, cell("눈", "짝눈 큰"), 8 + dx, ey, eye_col, mirror=True)
    else:
        paste(face, cell("눈", eye), 8 - dx, ey, eye_col)
        paste(face, cell("눈", eye), 8 + dx, ey, eye_col, mirror=True)
    paste(face, cell("눈썹", brow), 8 - dx, L["brow_y"] + dy, hair_col=hair)
    paste(face, cell("눈썹", brow), 8 + dx, L["brow_y"] + dy, mirror=True, hair_col=hair)
    paste(face, cell("입", mouth), L["mouth_x"], L["mouth_y"])
    for o in overlays:
        paste(face, cell("덧그림", o), 8, 8)
    return face.clip(0, 255).astype(np.uint8)


def main():
    rng = random.Random(7)
    S = 7
    shapes = meta["layout"]["face_shapes"]
    skins = [hexc(c) for c in pal["skin"]]
    hairs = [hexc(c) for c in pal["hair"].values()]
    eyes = [hexc(c) for c in pal["eye"].values()]
    brows = list(meta["parts"]["눈썹"])
    mouths = list(meta["parts"]["입"])
    rows = []
    # 1줄: 눈 종류
    rows.append(("눈 종류", [(e, dict(eye=e, brow="기본", mouth="미소")) for e in
                             ["기본", "큰 눈", "둥근 눈", "가는 눈", "졸린 눈", "반짝 눈", "짝눈", "웃는 눈"]]))
    rows.append(("입, 표정", [(m, dict(eye="기본", brow="기본", mouth=m)) for m in mouths]))
    rows.append(("눈썹", [(b, dict(eye="둥근 눈", brow=b, mouth="기본")) for b in brows] + [("", None)] * 2))
    rows.append(("덧그림", [(o, dict(eye="기본", brow="기본", mouth="무표정", overlays=[o])) for o in meta["parts"]["덧그림"]] + [("", None)] * 1))
    rand = []
    for i in range(16):
        sh = rng.choice(shapes)
        rand.append((sh["name"], dict(shape=sh, eye=rng.choice(sh["eyes"]), brow=rng.choice(brows),
                                      mouth=rng.choice(["기본", "미소", "무표정", "작은 입"]),
                                      skin=rng.choice(skins), hair=rng.choice(hairs), eye_col=rng.choice(eyes))))
    rows.append(("무작위", rand[:8]))
    rows.append(("무작위", rand[8:]))
    W = 8 * (16 * S + 14) + 90
    H = len(rows) * (16 * S + 34)
    sheet = Image.new("RGBA", (W, H), (255, 246, 227, 255))
    d = ImageDraw.Draw(sheet)
    for r, (label, items) in enumerate(rows):
        oy = r * (16 * S + 34)
        d.text((4, oy + 50), label, font=font, fill=(59, 42, 42, 255))
        for c, (name, spec) in enumerate(items):
            if spec is None:
                continue
            ox = 90 + c * (16 * S + 14)
            sh = spec.get("shape", shapes[0])
            face = make_face(rng, sh, spec.get("skin", skins[1]), spec.get("hair", hairs[1]),
                             spec.get("eye_col", eyes[2]), spec["eye"], spec["brow"], spec["mouth"],
                             spec.get("overlays", []))
            sheet.alpha_composite(Image.fromarray(face, "RGBA").resize((16 * S, 16 * S), Image.NEAREST), (ox, oy + 4))
            d.text((ox, oy + 16 * S + 8), name, font=font, fill=(59, 42, 42, 255))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sheet.save(OUT)


if __name__ == "__main__":
    main()
