#!/usr/bin/env python3
"""8×8 얼굴 그림 아틀라스와 배치 정보 (17_visual_procgen.md 2-4).

출력
  assets/faces/face_atlas.png    64×64, 8×8 칸
  data/visual/face_atlas.json    그림 이름 → 칸 번호, 얼굴형 배치

규칙
  - 얼굴 정면 = 8×8. 0~1행은 머리카락 메시가 덮는다.
  - 눈, 눈썹은 왼쪽 것 하나만 그린다. 오른쪽은 좌우 반전해 대칭 위치에 놓는다.
  - 회색 #808080, #606060 → 유전자 눈색 × (밝기/128). #404040 → 머리색 × 0.7.
"""
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COLORS = {
    "O": (59, 42, 42, 255), "G": (128, 128, 128, 255), "g": (96, 96, 96, 255), "W": (255, 255, 255, 255),
    "t": (255, 143, 159, 255), "h": (64, 64, 64, 255), "p": (255, 130, 160, 170), "f": (150, 85, 55, 170),
    "w": (90, 50, 40, 90), "S": (196, 85, 63, 230), "M": (122, 42, 42, 255), "B": (255, 250, 240, 255),
    "b": (217, 212, 204, 255), ".": (0, 0, 0, 0),
}
EYES = {
    "점 눈": ["G", "g"],
    "큰 눈": ["WG", "gg"],
    "둥근 눈": ["GG", "gg"],
    "반짝 눈": ["WG", "Gg", "gg"],
    "가는 눈": ["Gg"],
    "졸린 눈": ["OO", "gg"],
    "웃는 눈": ["OO"],
    "감은 눈": ["..", "OO"],
    "짝눈 작은": ["g"],
    "짝눈 큰": ["WG", "gg"],
}
BROWS = {
    "없음": ["."],
    "기본": ["hh"],
    "치켜 올라간": ["h.", ".h"],
    "처진": [".h", "h."],
}
MOUTHS = {
    "기본": ["O"],
    "미소": ["O.O", ".O."],
    "활짝 웃음": ["OOO", ".t."],
    "놀람": ["O", "O"],
    "찡그림": [".O.", "O.O"],
    "무표정": ["OO"],
    "없음": ["."],
}


def overlay(points):
    g = [["."] * 8 for _ in range(8)]
    for ch, pts in points.items():
        for x, y in pts:
            g[y][x] = ch
    return ["".join(r) for r in g]


OVERLAYS = {
    "볼 홍조": overlay({"p": [(1, 5), (6, 5)]}),
    "주근깨": overlay({"f": [(1, 5), (2, 5), (5, 5), (6, 5)]}),
    "주름": overlay({"w": [(2, 2), (3, 2), (4, 2), (5, 2), (1, 6), (6, 6)]}),
    "흉터": overlay({"S": [(6, 3), (6, 5), (5, 6)]}),
    "낙인": overlay({"M": [(1, 5), (1, 6)]}),
    "붕대": overlay({"B": [(x, 1) for x in range(8)] + [(x, 2) for x in range(8)], "b": [(2, 1), (2, 2), (5, 1), (5, 2)]}),
    "눈물": overlay({"G": [(1, 5)]}),
}
LAYOUT = {
    "size": 8, "brow_dy": -1, "mouth_y": 6, "mouth_cx": 3.5,
    "face_shapes": [
        {"name": "둥근", "eye_x": 2, "eye_y": 3, "head_w": 1.0, "head_h": 1.0, "eyes": ["점 눈", "둥근 눈", "큰 눈"]},
        {"name": "갸름", "eye_x": 2, "eye_y": 3, "head_w": 0.9, "head_h": 1.05, "eyes": ["점 눈", "가는 눈", "졸린 눈"]},
        {"name": "넓은", "eye_x": 1, "eye_y": 3, "head_w": 1.1, "head_h": 0.95, "eyes": ["점 눈", "가는 눈"]},
        {"name": "긴", "eye_x": 2, "eye_y": 3, "head_w": 0.95, "head_h": 1.1, "eyes": ["가는 눈", "점 눈", "졸린 눈"]},
        {"name": "각진", "eye_x": 1, "eye_y": 4, "head_w": 1.05, "head_h": 1.0, "eyes": ["점 눈", "가는 눈"]},
        {"name": "아기", "eye_x": 2, "eye_y": 4, "head_w": 1.0, "head_h": 0.95, "eyes": ["큰 눈", "둥근 눈", "점 눈"]},
    ],
    "note": "왼쪽 눈의 오른쪽 끝 열 = eye_x(폭 2인 눈은 eye_x-1부터). 오른쪽 눈은 7-x로 대칭. 폭 2인 눈은 eye_x=1이어도 2로 본다",
}


def draw(grid):
    a = np.zeros((len(grid), len(grid[0]), 4), dtype=np.uint8)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            a[y, x] = COLORS[ch]
    return a


def main():
    atlas = np.zeros((64, 64, 4), dtype=np.uint8)
    index = {"눈": {}, "눈썹": {}, "입": {}, "덧그림": {}}
    k = 0

    def place(group, name, grid, center=True):
        nonlocal k
        a = draw(grid)
        cx, cy = (k % 8) * 8, (k // 8) * 8
        h, w = a.shape[:2]
        ox, oy = (cx + (8 - w) // 2, cy + (8 - h) // 2) if center else (cx, cy)
        atlas[oy:oy + h, ox:ox + w] = a
        index[group][name] = {"cell": k, "w": w, "h": h}
        k += 1

    for n, g in EYES.items():
        place("눈", n, g)
    k = 16
    for n, g in BROWS.items():
        place("눈썹", n, g)
    k = 24
    for n, g in MOUTHS.items():
        place("입", n, g)
    k = 32
    for n, g in OVERLAYS.items():
        place("덧그림", n, g, center=False)
    os.makedirs(os.path.join(ROOT, "assets", "faces"), exist_ok=True)
    Image.fromarray(atlas, "RGBA").save(os.path.join(ROOT, "assets", "faces", "face_atlas.png"))
    json.dump({"cell": 8, "columns": 8, "parts": index, "layout": LAYOUT, "iris_gray": [128, 96], "brow_gray": 64},
              open(os.path.join(ROOT, "data", "visual", "face_atlas.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("얼굴 그림", sum(len(v) for v in index.values()), "개 (8×8)")


if __name__ == "__main__":
    main()
