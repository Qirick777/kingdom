#!/usr/bin/env python3
"""팔레트와 재료 텍스처 아틀라스를 만든다.

출력
  data/visual/palettes.json            이름 붙은 색
  assets/palette.png                   팔레트 견본
  assets/textures/material_atlas.png   64×64, 8×8 칸 (재료 31종 × 변형 2). 0.5m 조각 하나 = 8×8
  data/visual/material_atlas.json      재료 이름 → 칸 번호
"""
import json
import os

import numpy as np
from PIL import Image

from pixel import Rng, hexc, mix, periodic_noise, shade

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

PALETTE = {
    "outline": "#3b2a2a",
    "ui": {"cream": "#fff6e3", "paper": "#f7ead2", "wood_light": "#e0a96d", "wood": "#c4864f",
           "wood_dark": "#774a2a", "pink": "#ff9fb4", "sky": "#9fd8ff", "mint": "#a8f0c8",
           "lemon": "#ffe98a", "lavender": "#c8b6ff", "coral": "#ff8f7a", "text": "#3b2a2a"},
    "skin": ["#ffe2c9", "#f6c7a0", "#d9a074", "#a8714a", "#6e4a33"],
    "hair": {"검정": "#3a3030", "갈색": "#7a4f33", "금발": "#f2cf6b", "적발": "#d4602f", "회색": "#c9c4c0"},
    "eye": {"갈색": "#3f2416", "녹색": "#4f9a4f", "청색": "#4f8fd6"},
    "cloth": {
        "노예": ["#d8c7a8", "#b9a88c", "#9d8f7a"],
        "평민": ["#9e7a52", "#8a8f4e", "#5f7a94", "#a35f45"],
        "장인상인": ["#e8954a", "#5fae6e", "#4f8fd6", "#d96f8a"],
        "지주기사": ["#e05a4f", "#3fa36b", "#3f7fd1", "#e3b23c"],
        "귀족": ["#b8323f", "#7a3fb3", "#2f56b8", "#1f8a6e"],
        "장식": ["#ffd34d", "#fffaf0"],
    },
    "material": {
        "grass": ["#8fd16a", "#6fbf4f", "#4f9e3f"], "leaf": ["#6ccf5f", "#49ad4a", "#2f8a43"],
        "dirt": ["#c8946a", "#a87552", "#85583c"], "sand": ["#f5dfa3", "#e8c983", "#d4ad66"],
        "stone": ["#d4d0c9", "#b3aea6", "#8d8780", "#6b655f"], "slate": ["#8a9ab0", "#6f7f96", "#56637a"],
        "water": ["#8fdcf5", "#5fc0e8", "#3f9fd0"], "wood": ["#e6b072", "#c98c52", "#a26a3a", "#774a2a"],
        "straw": ["#f5d873", "#e0b94e", "#bf953c"], "reed": ["#d6d27a", "#b3b25a", "#8c8c46"],
        "clay": ["#e8765c", "#c95a43", "#a34333"], "brick": ["#d9805f", "#bb6448", "#8f4a36"],
        "plaster": ["#fdf6e6", "#f2e6cc", "#e0d0b0"], "snow": ["#ffffff", "#eaf3fa", "#cfe1ef"],
        "bark": ["#9a6a44", "#7a5033", "#5c3b25"],
        "ore": {"철": "#c46a4f", "구리": "#e8954a", "금": "#ffd34d", "은": "#e3ecf2"},
    },
}

C = 8


def many(n):
    """16×16 기준 개수를 칸 넓이에 맞춘다."""
    return max(1, n * C * C // 256)


def cell_noise(seed, cells=2):
    return periodic_noise(C, cells, seed)


def pick(cols, v):
    """0~1 값을 색 목록 중 하나로."""
    i = min(len(cols) - 1, int(v * len(cols)))
    return hexc(cols[i])


def tile(fn, variant):
    a = np.zeros((C, C, 4), dtype=np.uint8)
    fn(a, Rng(fn.__name__, variant), variant)
    return a


M = PALETTE["material"]


# ---------------------------------------------------------------- 지붕

def thatch(a, r, v):
    n = cell_noise(("thatch", v), 4)
    for y in range(C):
        for x in range(C):
            row = (y + (x // 4) % 2) % 4
            base = M["straw"][0] if row < 2 else M["straw"][1]
            if row == 3:
                base = M["straw"][2]
            a[y, x] = shade(hexc(base), (n[y, x] - 0.5) * 0.25)
    for _ in range(many(18)):
        x, y = r.randrange(C), r.randrange(C)
        a[y, x] = hexc(M["straw"][2])
        a[(y + 1) % C, x] = hexc(M["straw"][2])


def reed(a, r, v):
    for x in range(C):
        col = M["reed"][r.choice([0, 0, 1])]
        off = r.randrange(4)
        for y in range(C):
            c = hexc(col)
            if (y + off) % 4 == 0:
                c = hexc(M["reed"][2])
            a[y, x] = c


def shingles(a, r, v):
    for y in range(C):
        row = y // 4
        for x in range(C):
            xx = (x + (2 if row % 2 else 0)) % C
            c = hexc(M["wood"][1 if (xx // 4 + row + v) % 3 else 0])
            if y % 4 == 3 or xx % 4 == 0:
                c = hexc(M["wood"][3])
            elif y % 4 == 0:
                c = shade(c, 0.2)
            a[y, x] = c


def clay_tiles(a, r, v):
    for y in range(C):
        for x in range(C):
            row = y // 4
            xx = (x + (2 if row % 2 else 0)) % C
            cx = xx % 4 - 1.5
            dy = y % 4
            curve = 3 - (cx * cx) / 2.2
            c = hexc(M["clay"][0])
            if dy > curve:
                c = hexc(M["clay"][2])
            elif dy > curve - 1:
                c = hexc(M["clay"][1])
            elif dy == 0:
                c = shade(c, 0.25)
            a[y, x] = c


def slate(a, r, v):
    for y in range(C):
        row = y // 4
        for x in range(C):
            xx = (x + (2 if row % 2 else 0)) % C
            c = hexc(M["slate"][(xx // 4 + row + v) % 2])
            if y % 4 == 3 or xx % 4 == 0:
                c = hexc(M["slate"][2])
            a[y, x] = c


# ---------------------------------------------------------------- 벽

def wattle(a, r, v):
    """세로 말뚝(4칸마다) 사이로 가로 가지가 번갈아 앞뒤로 지나간다."""
    for y in range(C):
        band, k = y // 4, y % 4
        for x in range(C):
            seg = x // 4
            front = (band + seg + v) % 2 == 0
            if x % 4 == 0:
                c = hexc(M["wood"][3]) if front else hexc(M["wood"][2])
            else:
                base = hexc(M["wood"][0] if front else M["wood"][2])
                tone = [0.18, 0.05, -0.08, -0.3][k]
                if not front and x % 4 in (1, 3):
                    tone -= 0.1
                c = shade(base, tone)
            a[y, x] = c


def logs(a, r, v):
    for y in range(C):
        k = y % 4
        tone = [0.25, 0.05, -0.05, -0.35][k]
        for x in range(C):
            c = shade(hexc(M["wood"][1]), tone)
            if (x + y * 3 + v * 5) % 8 == 0 and k in (1, 2):
                c = hexc(M["wood"][2])
            a[y, x] = c


def planks(a, r, v):
    n = cell_noise(("planks", v), 8)
    for y in range(C):
        for x in range(C):
            col = x // 4
            c = hexc(M["wood"][0 if col % 2 else 1])
            c = shade(c, (n[y, x] - 0.5) * 0.15)
            if x % 4 == 3:
                c = hexc(M["wood"][3])
            if (y + col * 5 + v * 3) % 8 == 0:
                c = hexc(M["wood"][3])
            a[y, x] = c
    for col in range(C // 4):
        y = (col * 3 + v * 4) % C
        a[y, col * 4 + 1] = hexc(M["stone"][3])


def plaster(a, r, v):
    n = cell_noise(("plaster", v), 4)
    for y in range(C):
        for x in range(C):
            a[y, x] = pick(M["plaster"][:2], n[y, x])
    for _ in range(many(6)):
        x, y = r.randrange(C), r.randrange(C)
        a[y, x] = hexc(M["plaster"][2])


def stone_wall(a, r, v):
    """높이 4인 두 줄에 너비 3~5의 돌을 엇갈려 쌓는다. 줄눈 1칸."""
    rows = [(0, 4), (4, 4)]
    for ri, (y0, hgt) in enumerate(rows):
        widths = []
        while sum(widths) < C:
            widths.append(r.randint(3, 5))
        widths[-1] -= sum(widths) - C
        if widths[-1] < 2 and len(widths) > 1:
            widths[-2] += widths[-1]
            widths.pop()
        off = r.randrange(C)
        x0 = 0
        for si, w in enumerate(widths):
            col = hexc(M["stone"][r.randrange(3)])
            for dy in range(hgt):
                for dx in range(w):
                    x = (off + x0 + dx) % C
                    y = y0 + dy
                    edge_x = dx == w - 1
                    edge_y = dy == hgt - 1
                    corner = (dx in (0, w - 2) and dy in (0, hgt - 2)) and not edge_x and not edge_y
                    if edge_x or edge_y:
                        c = hexc(M["stone"][3])
                    elif corner and (dx == 0 and dy == 0):
                        c = shade(col, 0.1)
                    elif dy == 0:
                        c = shade(col, 0.18)
                    elif dy == hgt - 2:
                        c = shade(col, -0.12)
                    else:
                        c = col
                    a[y, x] = c
            x0 += w


def brick(a, r, v):
    for y in range(C):
        row = y // 4
        for x in range(C):
            xx = (x + (2 if row % 2 else 0)) % C
            c = hexc(M["brick"][(xx // 4 + row + v) % 2])
            if y % 4 == 3 or xx % 4 == 3:
                c = hexc(M["plaster"][2])
            elif y % 4 == 0:
                c = shade(c, 0.12)
            a[y, x] = c


# ---------------------------------------------------------------- 바닥

def grass(a, r, v):
    n = cell_noise(("grass", v), 4)
    for y in range(C):
        for x in range(C):
            a[y, x] = pick(M["grass"][:2], n[y, x])
    for _ in range(many(7)):
        x, y = r.randrange(C), r.randrange(C)
        a[y, x] = hexc(M["grass"][2])
        a[(y - 1) % C, x] = shade(hexc(M["grass"][0]), 0.25)


def dirt(a, r, v):
    n = cell_noise(("dirt", v), 4)
    for y in range(C):
        for x in range(C):
            a[y, x] = pick(M["dirt"][:2], n[y, x])
    for _ in range(many(5)):
        x, y = r.randrange(C), r.randrange(C)
        a[y, x] = hexc(M["stone"][1])
        a[y, (x + 1) % C] = hexc(M["dirt"][2])


def furrows(a, r, v):
    for y in range(C):
        k = y % 4
        for x in range(C):
            c = hexc(M["dirt"][[0, 1, 2, 1][k]])
            if k == 0 and (x + v * 2) % 4 == 0:
                c = hexc(M["grass"][1])
            a[y, x] = c


def dirt_road(a, r, v):
    n = cell_noise(("road", v), 4)
    for y in range(C):
        for x in range(C):
            c = mix(hexc(M["dirt"][0]), hexc(M["sand"][1]), 0.45)
            a[y, x] = shade(c, (n[y, x] - 0.5) * 0.18)
    for _ in range(many(6)):
        x, y = r.randrange(C), r.randrange(C)
        a[y, x] = shade(hexc(M["sand"][0]), 0.2)
    for _ in range(many(4)):
        x, y = r.randrange(C), r.randrange(C)
        a[y, x] = hexc(M["dirt"][1])
        a[y, (x + 1) % C] = hexc(M["dirt"][1])


def gravel(a, r, v):
    for y in range(C):
        for x in range(C):
            a[y, x] = mix(hexc(M["dirt"][1]), hexc(M["stone"][2]), 0.5)
    for _ in range(many(22)):
        x, y = r.randrange(C), r.randrange(C)
        c = hexc(M["stone"][r.randrange(3)])
        a[y, x] = c
        a[y, (x + 1) % C] = shade(c, -0.2)


def flagstone(a, r, v):
    for y in range(C):
        for x in range(C):
            bx = (x + (2 if (y // 4) % 2 else 0)) % C
            c = hexc(M["stone"][(bx // 4 + y // 4 + v) % 2])
            if y % 4 == 3 or bx % 4 == 3:
                c = hexc(M["stone"][3])
            elif y % 4 == 0 or bx % 4 == 0:
                c = shade(c, 0.15)
            a[y, x] = c


def sand(a, r, v):
    n = cell_noise(("sand", v), 4)
    for y in range(C):
        for x in range(C):
            a[y, x] = pick(M["sand"][:2], n[y, x])
    for _ in range(many(8)):
        x, y = r.randrange(C), r.randrange(C)
        a[y, x] = hexc(M["sand"][2])


def snow(a, r, v):
    n = cell_noise(("snow", v), 4)
    for y in range(C):
        for x in range(C):
            a[y, x] = pick(M["snow"][:2], n[y, x] * 0.9)
    for _ in range(many(5)):
        x, y = r.randrange(C), r.randrange(C)
        a[y, x] = hexc(M["snow"][2])


def water(a, r, v):
    for y in range(C):
        for x in range(C):
            a[y, x] = hexc(M["water"][1])
    for _ in range(many(6)):
        x, y = r.randrange(C), r.randrange(C)
        for k in range(3):
            a[y, (x + k) % C] = hexc(M["water"][0])
        a[(y + 1) % C, (x + 1) % C] = hexc(M["water"][2])


# ---------------------------------------------------------------- 자연

def rock(a, r, v):
    n = cell_noise(("rock", v), 4)
    for y in range(C):
        for x in range(C):
            a[y, x] = pick(M["stone"][1:3], n[y, x])
    x, y = r.randrange(C), r.randrange(C)
    for k in range(4):
        a[y % C, x % C] = hexc(M["stone"][3])
        x += r.choice([1, 1, 0])
        y += r.choice([1, 0, 1])


def bark(a, r, v):
    for x in range(C):
        off = r.randrange(4)
        for y in range(C):
            c = hexc(M["bark"][(x // 2 + v) % 2])
            if x % 4 == 3 or (y + off) % 4 == 0:
                c = hexc(M["bark"][2])
            a[y, x] = c


def leaves(a, r, v):
    for y in range(C):
        for x in range(C):
            a[y, x] = hexc(M["leaf"][1])
    for _ in range(many(12)):
        x, y = r.randrange(C), r.randrange(C)
        for dx, dy, t in ((0, 0, 0), (1, 0, 0), (0, 1, 2), (1, 1, 2), (-1, 0, 0)):
            a[(y + dy) % C, (x + dx) % C] = hexc(M["leaf"][t])


def ore_overlay(a, r, v):
    for _ in range(many(5 + v * 2)):
        x, y = r.randrange(1, C - 2), r.randrange(1, C - 2)
        a[y, x] = (255, 255, 255, 255)
        a[y + 1, x] = (180, 180, 180, 255)


# ---------------------------------------------------------------- 밭 작물 (계절)

def _crop(a, r, v, stage):
    furrows(a, r, v)
    for x in range(1, C, 4):
        for y in range(0, C, 4):
            yy = (y + 1) % C
            if stage == 0:
                a[yy, x] = hexc(M["grass"][0])
            elif stage == 1:
                a[yy, x] = hexc(M["grass"][1])
                a[(yy - 1) % C, x] = hexc(M["grass"][0])
                a[yy, (x + 1) % C] = hexc(M["grass"][2])
            elif stage == 2:
                for k in range(3):
                    a[(yy - k) % C, x] = hexc(M["straw"][0 if k == 2 else 1])
                a[(yy - 2) % C, (x + 1) % C] = hexc(M["straw"][2])
            else:
                a[yy, x] = hexc(M["straw"][2])


def crop_sprout(a, r, v):
    _crop(a, r, v, 0)


def crop_growing(a, r, v):
    _crop(a, r, v, 1)


def crop_ripe(a, r, v):
    _crop(a, r, v, 2)


def crop_stubble(a, r, v):
    _crop(a, r, v, 3)


# ---------------------------------------------------------------- 건물 부품 (이음매 없음 아님)

def grid(a, rows, cmap):
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                a[y, x] = hexc(cmap[ch])


def door(a, r, v):
    rows = ["..4444..",
            ".412214.",
            ".412214.",
            ".4122g4." if v == 0 else ".4g2214.",
            ".412214.",
            ".412214.",
            ".412214.",
            ".444444."]
    grid(a, rows, {"1": M["wood"][0], "2": M["wood"][1], "4": M["wood"][3], "g": "#ffd34d"})


def window_shutter(a, r, v):
    if v == 0:
        rows = ["........", ".4444444", ".4124124", ".4214214", ".4124124", ".4214214", ".4444444", "........"]
    else:
        rows = ["........", ".4444444", ".41ddd14", ".41ddd14", ".41ddd14", ".41ddd14", ".4444444", "........"]
    grid(a, rows, {"1": M["wood"][0], "2": M["wood"][1], "4": M["wood"][3], "d": "#5a4a6e"})


def window_lattice(a, r, v):
    glass = "#ffe9a8" if v == 1 else "#4a3f5c"
    rows = ["........", ".4444444", ".4gg4gg4", ".4gg4gg4", ".4444444", ".4gg4gg4", ".4gg4gg4", ".4444444"]
    grid(a, rows, {"4": M["wood"][3], "g": glass})


MATERIALS = [
    ("초가", thatch), ("갈대", reed), ("너와", shingles), ("기와", clay_tiles), ("슬레이트", slate),
    ("나뭇가지 엮음", wattle), ("통나무", logs), ("나무 판자", planks), ("회벽", plaster), ("돌", stone_wall), ("벽돌", brick),
    ("풀", grass), ("흙", dirt), ("밭 고랑", furrows), ("흙길", dirt_road), ("자갈길", gravel), ("돌 바닥", flagstone), ("모래", sand), ("눈", snow),
    ("물", water), ("바위", rock), ("나무껍질", bark), ("나뭇잎", leaves), ("광석 점", ore_overlay),
    ("나무 문", door), ("덧문 창", window_shutter), ("격자 창", window_lattice),
    ("작물 새싹", crop_sprout), ("작물 자람", crop_growing), ("작물 익음", crop_ripe), ("작물 그루터기", crop_stubble),
]
SEAMLESS = {name for name, _ in MATERIALS} - {"나무 문", "덧문 창", "격자 창", "광석 점"}


def main():
    atlas = np.zeros((8 * C, 8 * C, 4), dtype=np.uint8)
    index = {}
    k = 0
    for name, fn in MATERIALS:
        index[name] = []
        for v in range(2):
            t = tile(fn, v)
            cx, cy = k % 8, k // 8
            atlas[cy * C:(cy + 1) * C, cx * C:(cx + 1) * C] = t
            index[name].append(k)
            k += 1
    os.makedirs(os.path.join(ROOT, "assets", "textures"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "data", "visual"), exist_ok=True)
    Image.fromarray(atlas, "RGBA").save(os.path.join(ROOT, "assets", "textures", "material_atlas.png"))
    json.dump({"cell": C, "columns": 8, "seamless": sorted(SEAMLESS), "materials": index},
              open(os.path.join(ROOT, "data", "visual", "material_atlas.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(PALETTE, open(os.path.join(ROOT, "data", "visual", "palettes.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    # 팔레트 견본
    cols = []

    def walk(o):
        if isinstance(o, str) and o.startswith("#"):
            cols.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(PALETTE)
    sw = Image.new("RGBA", (16 * 16, 16 * ((len(cols) + 15) // 16)), (0, 0, 0, 0))
    for i, c in enumerate(cols):
        Image.new("RGBA", (16, 16), hexc(c)).copy()
        sw.paste(Image.new("RGBA", (16, 16), hexc(c)), ((i % 16) * 16, (i // 16) * 16))
    sw.save(os.path.join(ROOT, "assets", "palette.png"))
    print(f"재료 {len(MATERIALS)}종 × 2 = {k}칸, 팔레트 {len(cols)}색")


if __name__ == "__main__":
    main()
