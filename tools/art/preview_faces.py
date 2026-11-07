#!/usr/bin/env python3
"""8×8 얼굴을 조립해 본다."""
import json
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

from face_compose import ROOT, face, hexc

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "images", "art_faces.png")
meta = json.load(open(os.path.join(ROOT, "data", "visual", "face_atlas.json"), encoding="utf-8"))
pal = json.load(open(os.path.join(ROOT, "data", "visual", "palettes.json"), encoding="utf-8"))
font = ImageFont.truetype(os.path.join(ROOT, "assets", "fonts", "NanumGothic.ttf"), 13)
S = 10


def main():
    rng = random.Random(11)
    shapes = meta["layout"]["face_shapes"]
    skins = [hexc(c) for c in pal["skin"]]
    hairs = [hexc(c) for c in list(pal["hair"].values())[:4]]
    eyes = [hexc(c) for c in pal["eye"].values()]
    base = dict(shape=shapes[0], skin=skins[1], hair=hairs[1], eye=eyes[2])
    rows = [
        ("눈", [(e, dict(base, eyes=e)) for e in ["점 눈", "큰 눈", "둥근 눈", "반짝 눈", "가는 눈", "졸린 눈", "웃는 눈", "감은 눈", "짝눈"]]),
        ("입", [(m, dict(base, mouth=m)) for m in meta["parts"]["입"]]),
        ("눈썹", [(b, dict(base, brow=b, mouth="무표정")) for b in meta["parts"]["눈썹"]]),
        ("덧그림", [(o, dict(base, overlays=[o])) for o in meta["parts"]["덧그림"]]),
        ("감정", [("평소", dict(base)), ("기쁨", dict(base, eyes="웃는 눈", mouth="활짝 웃음", overlays=["볼 홍조"])),
                  ("화남", dict(base, brow="치켜 올라간", mouth="찡그림")), ("슬픔", dict(base, brow="처진", mouth="찡그림", overlays=["눈물"])),
                  ("놀람", dict(base, eyes="둥근 눈", mouth="놀람")), ("졸림", dict(base, eyes="졸린 눈", mouth="무표정")),
                  ("잠", dict(base, eyes="감은 눈", mouth="없음"))]),
    ]
    rand = []
    for i in range(20):
        sh = rng.choice(shapes)
        rand.append((sh["name"], dict(shape=sh, skin=rng.choice(skins), hair=rng.choice(hairs), eye=rng.choice(eyes),
                                      eyes=rng.choice(sh["eyes"]), mouth=rng.choice(["기본", "기본", "미소", "무표정"]),
                                      overlays=rng.choice([[], [], [], ["주근깨"], ["볼 홍조"]]))))
    rows.append(("무작위", rand[:10]))
    rows.append(("무작위", rand[10:]))
    W = 10 * (8 * S + 14) + 70
    H = len(rows) * (8 * S + 30) + 6
    sheet = Image.new("RGBA", (W, H), (255, 246, 227, 255))
    d = ImageDraw.Draw(sheet)
    for r, (label, items) in enumerate(rows):
        oy = 6 + r * (8 * S + 30)
        d.text((6, oy + 32), label, font=font, fill=(59, 42, 42, 255))
        for c, (name, spec) in enumerate(items):
            ox = 70 + c * (8 * S + 14)
            img = face(spec["shape"], spec["skin"], spec["hair"], spec["eye"], spec.get("eyes", "점 눈"),
                       spec.get("brow", "없음"), spec.get("mouth", "기본"), spec.get("overlays", []))
            sheet.alpha_composite(Image.fromarray(img, "RGBA").resize((8 * S, 8 * S), Image.NEAREST), (ox, oy))
            d.text((ox, oy + 8 * S + 4), name, font=font, fill=(59, 42, 42, 255))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sheet.save(OUT)


if __name__ == "__main__":
    main()
