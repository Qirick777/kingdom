#!/usr/bin/env python3
"""얼굴 그림 아틀라스와 배치 정보를 만든다 (17_visual_procgen.md 2-4, 9-1 A).

출력
  assets/faces/face_atlas.png    128×128, 16×16 칸
  data/visual/face_atlas.json    그림 이름 → 칸 번호, 얼굴 배치 좌표

규칙
  - 눈, 눈썹은 왼쪽 것 하나만 그린다. 셰이더가 좌우 대칭으로 놓는다.
  - 눈동자는 회색(#808080, #606060)으로 칠한다. 셰이더가 회색을 유전자 눈색으로 바꾼다
    (눈색 × 회색 밝기 / 128).
  - 덧그림은 칸 전체가 얼굴 정면이다.
"""
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

COLORS = {
    "O": (59, 42, 42, 255),        # 외곽선, 속눈썹, 입
    "G": (128, 128, 128, 255),     # 눈동자(셰이더가 눈색으로)
    "g": (96, 96, 96, 255),        # 눈동자 어두운 쪽
    "W": (255, 255, 255, 255),     # 반짝임
    "t": (255, 143, 159, 255),     # 혀, 입 안
    "p": (255, 143, 170, 150),     # 볼 홍조(반투명)
    "w": (90, 50, 40, 90),         # 주름(반투명)
    "h": (64, 64, 64, 255),        # 눈썹(셰이더가 머리색 × 0.7로)
    "f": (160, 90, 60, 150),       # 주근깨(반투명)
    "S": (196, 85, 63, 220),       # 흉터
    "M": (122, 42, 42, 255),       # 낙인
    "B": (255, 250, 240, 255),     # 붕대
    "b": (217, 212, 204, 255),     # 붕대 테이프 줄
    ".": (0, 0, 0, 0),
}

# 눈 (한쪽, 칸 가운데에 놓음)
EYES = {
    "기본": ["OO",
             "WG",
             "gg"],
    "큰 눈": [".OO.",
              "OWGO",
              "OGGO",
              ".gg."],
    "둥근 눈": ["OOO",
                "OWG",
                "Ggg"],
    "가는 눈": ["OOO",
                ".g."],
    "졸린 눈": ["OOO",
                "GGg"],
    "반짝 눈": ["O.OO",
                ".OWG",
                ".WGG",
                ".ggg"],
    "짝눈 작은": ["OO",
                  "gg"],
    "짝눈 큰": [".OO.",
                "OWGO",
                "OGgO",
                ".OO."],
    "감은 눈": ["O..O",
                ".OO."],
    "웃는 눈": [".OO.",
                "O..O"],
}

# 눈썹 (왼쪽 것: 바깥쪽이 왼편)
BROWS = {
    "기본": [".hhh"],
    "굵은": ["hhhh",
             ".hh."],
    "가는": [".hh."],
    "치켜 올라간": ["hh..",
                    "..hh"],
    "처진": ["..hh",
             "hh.."],
    "일자": ["hhhh"],
}

MOUTHS = {
    "기본": ["OO"],
    "미소": ["O..O",
             ".OO."],
    "활짝 웃음": ["OOOO",
                  "OttO",
                  ".OO."],
    "놀람": [".OO.",
             "O..O",
             ".OO."],
    "찡그림": [".OO.",
               "O..O"],
    "슬픔": [".O.",
             "O.O"],
    "무표정": ["OOO"],
    "작은 입": ["O"],
}

# 덧그림: 16×16 얼굴 전체. 얼굴 배치(LAYOUT)와 같은 좌표계
def overlay(points):
    g = [["."] * 16 for _ in range(16)]
    for ch, pts in points.items():
        for x, y in pts:
            g[y][x] = ch
    return ["".join(r) for r in g]


OVERLAYS = {
    "볼 홍조": overlay({"p": [(2, 10), (3, 10), (12, 10), (13, 10)]}),
    "이마 주름": overlay({"w": [(5, 2), (6, 2), (7, 2), (8, 2), (9, 2), (10, 2), (6, 3), (7, 3), (8, 3), (9, 3)]}),
    "눈가 주름": overlay({"w": [(1, 8), (2, 9), (14, 8), (13, 9), (5, 11), (10, 11)]}),
    "주근깨": overlay({"f": [(2, 10), (4, 10), (3, 11), (11, 10), (13, 10), (12, 11)]}),
    "흉터": overlay({"S": [(11, 8), (12, 9), (12, 10), (13, 11), (13, 12)]}),
    "낙인": overlay({"M": [(2, 11), (3, 11), (4, 11), (3, 10), (3, 12)]}),
    "붕대": overlay({"B": [(x, y) for x in range(16) for y in (1, 2, 3)],
                    "b": [(4, 1), (4, 2), (4, 3), (11, 1), (11, 2), (11, 3)]}),
}

# 얼굴 배치(16×16 얼굴 정면 기준). 얼굴형 유전자 6종이 눈 간격, 높이를 바꾼다
LAYOUT = {
    "eye_y": 8, "brow_y": 5, "mouth_y": 12, "mouth_x": 8,
    "face_shapes": [
        {"name": "둥근", "eye_dx": 3.5, "eye_dy": 0, "head_w": 1.0, "head_h": 1.0, "eyes": ["기본", "둥근 눈", "큰 눈"]},
        {"name": "갸름", "eye_dx": 3.0, "eye_dy": 0, "head_w": 0.92, "head_h": 1.05, "eyes": ["기본", "가는 눈", "졸린 눈"]},
        {"name": "넓은", "eye_dx": 4.0, "eye_dy": 0, "head_w": 1.08, "head_h": 0.96, "eyes": ["둥근 눈", "기본", "큰 눈"]},
        {"name": "긴", "eye_dx": 3.5, "eye_dy": -1, "head_w": 0.95, "head_h": 1.08, "eyes": ["가는 눈", "기본", "졸린 눈"]},
        {"name": "각진", "eye_dx": 3.5, "eye_dy": 0, "head_w": 1.05, "head_h": 1.0, "eyes": ["기본", "졸린 눈", "둥근 눈"]},
        {"name": "아기", "eye_dx": 3.0, "eye_dy": 1, "head_w": 1.0, "head_h": 0.98, "eyes": ["큰 눈", "둥근 눈", "기본"]},
    ],
    "note": "눈 중심 x = 8 ± eye_dx (왼쪽은 그림 그대로, 오른쪽은 좌우 반전), y = eye_y + eye_dy. 미모 형질은 반짝 눈, 추형은 짝눈 작은 + 짝눈 큰",
}


def draw(grid):
    h, w = len(grid), len(grid[0])
    a = np.zeros((h, w, 4), dtype=np.uint8)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            a[y, x] = COLORS[ch]
    return a


def main():
    atlas = np.zeros((128, 128, 4), dtype=np.uint8)
    index = {"눈": {}, "눈썹": {}, "입": {}, "덧그림": {}}
    k = 0

    def place(group, name, grid, center=True):
        nonlocal k
        a = draw(grid)
        cx, cy = (k % 8) * 16, (k // 8) * 16
        if center:
            h, w = a.shape[:2]
            ox, oy = cx + (16 - w) // 2, cy + (16 - h) // 2
        else:
            ox, oy = cx, cy
        atlas[oy:oy + a.shape[0], ox:ox + a.shape[1]] = a
        index[group][name] = {"cell": k, "w": len(grid[0]), "h": len(grid)}
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
    json.dump({"cell": 16, "columns": 8, "parts": index, "layout": LAYOUT,
               "iris_gray": [128, 96], "brow_gray": 64,
               "rule": "그림은 칸 가운데. 눈, 눈썹은 왼쪽 것. 회색 128, 96은 눈색으로, 64는 머리색 × 0.7로 칠한다"},
              open(os.path.join(ROOT, "data", "visual", "face_atlas.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("얼굴 그림", sum(len(v) for v in index.values()), "개")


if __name__ == "__main__":
    main()
