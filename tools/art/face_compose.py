"""8×8 얼굴 조립(셰이더 동작과 같은 규칙). 미리보기와 장면 목업이 쓴다."""
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_atlas = None
_meta = None


def _load():
    global _atlas, _meta
    if _atlas is None:
        _atlas = np.array(Image.open(os.path.join(ROOT, "assets", "faces", "face_atlas.png"))).astype(np.float32)
        _meta = json.load(open(os.path.join(ROOT, "data", "visual", "face_atlas.json"), encoding="utf-8"))
    return _atlas, _meta


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)] + [255], dtype=np.float32)


def part(group, name):
    atlas, meta = _load()
    p = meta["parts"][group][name]
    k = p["cell"]
    x, y = (k % 8) * 8, (k // 8) * 8
    c = atlas[y:y + 8, x:x + 8]
    if group == "덧그림":
        return c
    w, h = p["w"], p["h"]
    ox, oy = (8 - w) // 2, (8 - h) // 2
    return c[oy:oy + h, ox:ox + w]


def _paste(face, img, x0, y0, eye, hair):
    h, w = img.shape[:2]
    for y in range(h):
        for x in range(w):
            px = img[y, x]
            if px[3] == 0:
                continue
            col = px.copy()
            if px[0] == px[1] == px[2]:
                if px[0] in (128, 96):
                    col = eye * (px[0] / 128.0)
                    col[3] = 255
                elif px[0] == 64:
                    col = hair * 0.7
                    col[3] = 255
            fx, fy = x0 + x, y0 + y
            if 0 <= fx < 8 and 0 <= fy < 8:
                a = col[3] / 255.0
                face[fy, fx, :3] = face[fy, fx, :3] * (1 - a) + col[:3] * a


def face(shape, skin, hair, eye, eyes="점 눈", brow="없음", mouth="기본", overlays=(), hair_rows=2):
    """8×8 얼굴 RGBA(uint8). shape는 face_atlas.json layout.face_shapes 하나."""
    _, meta = _load()
    L = meta["layout"]
    f = np.zeros((8, 8, 4), dtype=np.float32)
    f[:, :] = skin
    f[:hair_rows, :] = hair
    ex, ey = shape["eye_x"], shape["eye_y"]

    def put_eye(name, right):
        img = part("눈", name)
        w = img.shape[1]
        x_end = max(ex, 2) if w == 2 else ex          # 왼쪽 눈의 오른쪽 끝 열
        x0 = x_end - w + 1
        if right:
            img = img[:, ::-1]
            x0 = 7 - x_end
        _paste(f, img, x0, ey, eye, hair)

    if eyes == "짝눈":
        put_eye("짝눈 작은", False)
        put_eye("짝눈 큰", True)
    else:
        put_eye(eyes, False)
        put_eye(eyes, True)
    b = part("눈썹", brow)
    if b[..., 3].any():
        bw = b.shape[1]
        x_end = max(ex, 2) if bw == 2 else ex
        _paste(f, b, x_end - bw + 1, ey - b.shape[0], eye, hair)
        _paste(f, b[:, ::-1], 7 - x_end, ey - b.shape[0], eye, hair)
    m = part("입", mouth)
    _paste(f, m, int(round(L["mouth_cx"] - m.shape[1] / 2 + 0.01)), L["mouth_y"], eye, hair)
    for o in overlays:
        _paste(f, part("덧그림", o), 0, 0, eye, hair)
    return f.clip(0, 255).astype(np.uint8)
