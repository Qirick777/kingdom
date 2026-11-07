#!/usr/bin/env python3
"""품목(32px), 상태(24px), 계층(24px) 아이콘과 UI 틀을 만든다.

출력
  assets/ui/icons_items.png, icons_status.png, icons_class.png   가로 8칸 아틀라스
  assets/ui/panel_light.png, panel_dark.png                       48×48, 9-slice 테두리 16
  assets/ui/button_normal.png, button_pressed.png, button_disabled.png   48×24, 테두리 8
  assets/ui/frame_commoner.png, frame_noble.png, frame_royal.png        64×64, 안쪽 48×48 투명
  assets/ui/cursor_default.png, cursor_interact.png                     32×32
  assets/ui/bar_bg.png, bar_fill.png                                     32×8
  data/visual/ui_atlas.json                                              이름 → 칸
"""
import json
import os

import numpy as np
from PIL import Image

from pixel import OUTLINE, Canvas, hexc, shade

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UI = os.path.join(ROOT, "assets", "ui")

WOOD = hexc("#c98c52")
WOOD_L = hexc("#e6b072")
WOOD_D = hexc("#774a2a")
STRAW = hexc("#f5d873")
STRAW_D = hexc("#bf953c")
STONE = hexc("#b3aea6")
STONE_L = hexc("#d4d0c9")
STEEL = hexc("#cfd8e0")
GOLD = hexc("#ffd34d")
RED = hexc("#e8574f")
PINK = hexc("#ff8fa8")
SKY = hexc("#7fc8f5")
GREEN = hexc("#6fbf4f")
CREAM = hexc("#fff6e3")
BEIGE = hexc("#e9d4b0")
WHITE = (255, 255, 255, 255)


def icon(size, fn):
    c = Canvas(size, size)
    fn(c)
    c.outline()
    return c.px


# ---------------------------------------------------------------- 품목 32px

def grain(c):
    c.fill(c.mask(lambda d: d.ellipse([7, 11, 25, 29], fill=1)), BEIGE, 0.25, 0.2)
    c.fill(c.mask(lambda d: d.rectangle([12, 8, 20, 12], fill=1)), shade(BEIGE, -0.1), 0.2, 0.2)
    c.fill(c.mask(lambda d: d.rectangle([11, 11, 21, 12], fill=1)), WOOD_D)
    for x, top in ((13, 3), (16, 2), (19, 4)):
        c.fill(c.mask(lambda d: d.line([x, top + 3, x, 9], fill=1)), STRAW_D)
        c.fill(c.mask(lambda d: d.ellipse([x - 1, top, x + 1, top + 4], fill=1)), STRAW, 0.3)
    for p in ((12, 20), (16, 23), (20, 19)):
        c.put(p[0], p[1], shade(BEIGE, -0.25))


def meat(c):
    c.fill(c.mask(lambda d: d.ellipse([5, 5, 21, 21], fill=1)), hexc("#d9735c"), 0.25, 0.25)
    c.fill(c.mask(lambda d: d.ellipse([8, 8, 15, 14], fill=1)), hexc("#f2a08a"))
    c.fill(c.mask(lambda d: d.line([18, 18, 25, 25], fill=1, width=3)), WHITE, 0.0, 0.15)
    c.fill(c.mask(lambda d: d.ellipse([23, 22, 28, 27], fill=1)), WHITE, 0.0, 0.15)
    c.fill(c.mask(lambda d: d.ellipse([22, 24, 27, 29], fill=1)), WHITE, 0.0, 0.15)


def wood(c):
    for y0 in (17, 9):
        c.fill(c.mask(lambda d: d.rectangle([6, y0, 25, y0 + 7], fill=1)), WOOD, 0.2, 0.25)
        c.fill(c.mask(lambda d: d.ellipse([22, y0, 29, y0 + 7], fill=1)), WOOD_L, 0.1, 0.1)
        c.put(25, y0 + 3, WOOD_D)
        c.put(26, y0 + 4, WOOD_D)


def stone_blocks(c):
    for box in ([4, 16, 15, 27], [16, 16, 27, 27], [10, 5, 21, 16]):
        c.fill(c.mask(lambda d: d.rectangle(box, fill=1)), STONE, 0.3, 0.25)


def ore(c):
    c.fill(c.mask(lambda d: d.polygon([(5, 22), (9, 9), (18, 5), (27, 12), (26, 25), (14, 28)], fill=1)), hexc("#8d8780"), 0.25, 0.25)
    for x, y in ((11, 13), (19, 10), (21, 20), (13, 22), (16, 15)):
        c.fill(c.mask(lambda d: d.rectangle([x, y, x + 2, y + 1], fill=1)), hexc("#e8954a"), 0.3)


def metal(c):
    c.fill(c.mask(lambda d: d.polygon([(4, 23), (9, 12), (26, 12), (29, 23)], fill=1)), STEEL, 0.25, 0.3)
    c.fill(c.mask(lambda d: d.line([10, 15, 24, 15], fill=1)), WHITE)


def fiber(c):
    c.fill(c.mask(lambda d: d.ellipse([6, 6, 26, 26], fill=1)), hexc("#e8d7b8"), 0.25, 0.25)
    for k in range(3):
        c.fill(c.mask(lambda d: d.arc([8 + k * 3, 6, 24 - k * 3, 26], 200, 340, fill=1)), shade(hexc("#e8d7b8"), -0.2))
    c.fill(c.mask(lambda d: d.line([24, 22, 29, 28], fill=1)), shade(hexc("#e8d7b8"), -0.2))


def clothing(c):
    c.fill(c.mask(lambda d: d.polygon([(10, 5), (22, 5), (29, 11), (25, 15), (23, 13), (23, 28), (9, 28), (9, 13), (7, 15), (3, 11)], fill=1)), hexc("#5f9ad6"), 0.25, 0.25)
    c.fill(c.mask(lambda d: d.ellipse([13, 4, 19, 8], fill=1)), shade(hexc("#5f9ad6"), -0.3))
    c.fill(c.mask(lambda d: d.line([9, 22, 23, 22], fill=1)), WOOD_D)


def tool_low(c):
    c.fill(c.mask(lambda d: d.line([8, 27, 22, 8], fill=1, width=3)), WOOD, 0.2, 0.2)
    c.fill(c.mask(lambda d: d.polygon([(18, 4), (28, 6), (26, 12), (20, 10)], fill=1)), WOOD_L, 0.2, 0.25)


def tool_high(c):
    c.fill(c.mask(lambda d: d.line([8, 28, 21, 10], fill=1, width=3)), WOOD, 0.2, 0.2)
    c.fill(c.mask(lambda d: d.polygon([(12, 7), (20, 3), (29, 9), (25, 15), (20, 10), (16, 11)], fill=1)), STONE, 0.3, 0.25)


def weapon(c):
    c.fill(c.mask(lambda d: d.polygon([(26, 3), (29, 3), (29, 6), (13, 22), (10, 19)], fill=1)), STEEL, 0.35, 0.25)
    c.fill(c.mask(lambda d: d.line([8, 17, 15, 24], fill=1, width=2)), GOLD, 0.2, 0.2)
    c.fill(c.mask(lambda d: d.line([5, 27, 11, 21], fill=1, width=3)), WOOD_D, 0.2)
    c.fill(c.mask(lambda d: d.ellipse([3, 26, 6, 29], fill=1)), GOLD)


def armor(c):
    c.fill(c.mask(lambda d: d.polygon([(6, 8), (12, 5), (20, 5), (26, 8), (27, 14), (23, 16), (23, 27), (9, 27), (9, 16), (5, 14)], fill=1)), STEEL, 0.3, 0.3)
    c.fill(c.mask(lambda d: d.line([16, 9, 16, 25], fill=1)), shade(STEEL, -0.25))
    c.fill(c.mask(lambda d: d.line([10, 20, 22, 20], fill=1)), shade(STEEL, -0.25))


def coin(c):
    c.fill(c.mask(lambda d: d.ellipse([5, 5, 26, 26], fill=1)), hexc("#dfe7ee"), 0.3, 0.3)
    c.fill(c.mask(lambda d: d.ellipse([10, 10, 21, 21], fill=1)), hexc("#c3ccd6"))
    c.fill(c.mask(lambda d: d.rectangle([14, 13, 17, 18], fill=1)), hexc("#dfe7ee"))
    c.put(9, 9, WHITE)
    c.put(10, 8, WHITE)


def document(c):
    c.fill(c.mask(lambda d: d.rectangle([8, 7, 24, 25], fill=1)), CREAM, 0.0, 0.15)
    c.fill(c.mask(lambda d: d.ellipse([5, 4, 27, 10], fill=1)), BEIGE, 0.2, 0.2)
    c.fill(c.mask(lambda d: d.ellipse([5, 22, 27, 28], fill=1)), BEIGE, 0.2, 0.2)
    for y in (12, 15, 18):
        c.fill(c.mask(lambda d: d.line([11, y, 21, y], fill=1)), hexc("#a08060"))
    c.fill(c.mask(lambda d: d.ellipse([18, 18, 23, 23], fill=1)), RED)


ITEMS = [("곡식", grain), ("육류", meat), ("목재", wood), ("석재", stone_blocks), ("광석", ore), ("금속", metal),
         ("섬유", fiber), ("의류", clothing), ("하급 도구", tool_low), ("상급 도구", tool_high), ("무기", weapon),
         ("갑옷", armor), ("은화", coin), ("문서", document)]


# ---------------------------------------------------------------- 상태 24px

def s_hunger(c):
    c.fill(c.mask(lambda d: d.chord([3, 6, 20, 20], 0, 180, fill=1)), WOOD, 0.2, 0.25)
    c.fill(c.mask(lambda d: d.rectangle([3, 12, 20, 13], fill=1)), WOOD_L)
    c.fill(c.mask(lambda d: d.line([14, 4, 19, 11], fill=1, width=2)), STEEL)


def s_cold(c):
    for a, b in (((12, 2), (12, 21)), ((3, 7), (20, 16)), ((3, 16), (20, 7))):
        c.fill(c.mask(lambda d: d.line([a, b], fill=1, width=2)), SKY, 0.3)


def s_stress(c):
    c.fill(c.mask(lambda d: d.ellipse([2, 3, 13, 12], fill=1)), hexc("#8f86a8"), 0.25, 0.2)
    c.fill(c.mask(lambda d: d.ellipse([9, 2, 21, 12], fill=1)), hexc("#8f86a8"), 0.25, 0.2)
    c.fill(c.mask(lambda d: d.polygon([(12, 11), (9, 17), (12, 17), (10, 22), (16, 15), (13, 15), (15, 11)], fill=1)), GOLD, 0.3)


def s_pregnant(c):
    c.fill(c.mask(lambda d: d.polygon([(12, 21), (3, 11), (4, 5), (8, 3), (12, 7), (16, 3), (20, 5), (21, 11)], fill=1)), PINK, 0.3, 0.2)
    c.fill(c.mask(lambda d: d.ellipse([9, 9, 15, 15], fill=1)), WHITE)


def s_injury(c):
    c.fill(c.mask(lambda d: d.ellipse([2, 2, 21, 21], fill=1)), WHITE, 0.0, 0.15)
    c.fill(c.mask(lambda d: d.rectangle([10, 5, 13, 18], fill=1)), RED)
    c.fill(c.mask(lambda d: d.rectangle([5, 10, 18, 13], fill=1)), RED)


def s_disease(c):
    c.fill(c.mask(lambda d: d.ellipse([3, 9, 13, 19], fill=1)), hexc("#9ad46a"), 0.3, 0.2)
    c.fill(c.mask(lambda d: d.ellipse([12, 4, 20, 12], fill=1)), hexc("#9ad46a"), 0.3, 0.2)
    c.fill(c.mask(lambda d: d.ellipse([14, 14, 19, 19], fill=1)), hexc("#9ad46a"), 0.3, 0.2)


def s_refuse(c):
    c.fill(c.mask(lambda d: d.ellipse([2, 2, 21, 21], fill=1)), RED, 0.25, 0.2)
    c.fill(c.mask(lambda d: d.rectangle([10, 5, 13, 13], fill=1)), WHITE)
    c.fill(c.mask(lambda d: d.rectangle([10, 16, 13, 18], fill=1)), WHITE)


def s_secret(c):
    c.fill(c.mask(lambda d: d.arc([6, 2, 17, 14], 180, 360, fill=1, width=2)), STONE)
    c.fill(c.mask(lambda d: d.rectangle([6, 8, 17, 9], fill=1)), STONE)
    c.fill(c.mask(lambda d: d.rectangle([4, 10, 19, 21], fill=1)), GOLD, 0.3, 0.25)
    c.fill(c.mask(lambda d: d.rectangle([11, 13, 12, 17], fill=1)), WOOD_D)


def s_grudge(c):
    c.fill(c.mask(lambda d: d.polygon([(12, 2), (17, 9), (19, 7), (21, 14), (18, 21), (6, 21), (3, 14), (6, 8), (9, 11)], fill=1)), hexc("#f0603c"), 0.3, 0.2)
    c.fill(c.mask(lambda d: d.polygon([(12, 10), (15, 15), (14, 20), (10, 20), (9, 15)], fill=1)), GOLD)


def s_like(c):
    c.fill(c.mask(lambda d: d.polygon([(12, 21), (3, 11), (4, 5), (8, 3), (12, 7), (16, 3), (20, 5), (21, 11)], fill=1)), RED, 0.3, 0.2)
    c.put(7, 6, WHITE)


def s_loyalty(c):
    c.fill(c.mask(lambda d: d.polygon([(4, 3), (19, 3), (19, 12), (12, 21), (4, 12)], fill=1)), hexc("#5f9ad6"), 0.3, 0.25)
    c.fill(c.mask(lambda d: d.line([(7, 11), (10, 14), (16, 7)], fill=1, width=2)), WHITE)


def s_fear(c):
    c.fill(c.mask(lambda d: d.polygon([(12, 2), (6, 13), (12, 21), (18, 13)], fill=1)), SKY, 0.35, 0.2)
    c.fill(c.mask(lambda d: d.ellipse([6, 10, 18, 22], fill=1)), SKY, 0.35, 0.2)


def s_trust(c):
    c.fill(c.mask(lambda d: d.ellipse([2, 6, 14, 18], outline=1, width=2)), GOLD, 0.3, 0.2)
    c.fill(c.mask(lambda d: d.ellipse([9, 6, 21, 18], outline=1, width=2)), hexc("#f2b84a"), 0.3, 0.2)
    c.fill(c.mask(lambda d: d.arc([2, 6, 14, 18], 300, 60, fill=1, width=2)), GOLD, 0.3)


STATUS = [("허기", s_hunger), ("추위", s_cold), ("스트레스", s_stress), ("임신", s_pregnant), ("부상", s_injury),
          ("질병", s_disease), ("거부 위험", s_refuse), ("비밀", s_secret), ("원한", s_grudge), ("호감", s_like),
          ("충성", s_loyalty), ("두려움", s_fear), ("신뢰", s_trust)]


# ---------------------------------------------------------------- 계층 24px

def c_slave(c):
    for x in (2, 9, 16):
        c.fill(c.mask(lambda d: d.ellipse([x, 8, x + 7, 15], fill=1, outline=1, width=2)), STONE, 0.3, 0.2)
        c.px[11:13, x + 3:x + 5] = 0


def c_landless(c):
    c.fill(c.mask(lambda d: d.line([3, 21, 18, 4], fill=1, width=2)), WOOD)
    c.fill(c.mask(lambda d: d.ellipse([12, 2, 22, 12], fill=1)), hexc("#d96f6f"), 0.25, 0.2)
    c.put(15, 5, WHITE)


def c_tenant(c):
    c.fill(c.mask(lambda d: d.arc([4, 2, 20, 18], 200, 360, fill=1, width=3)), STEEL, 0.3)
    c.fill(c.mask(lambda d: d.line([6, 20, 10, 14], fill=1, width=3)), WOOD)


def c_freeholder(c):
    for x in (8, 12, 16):
        c.fill(c.mask(lambda d: d.line([x, 10, 12, 21], fill=1, width=2)), STRAW_D)
        c.fill(c.mask(lambda d: d.ellipse([x - 2, 3, x + 2, 10], fill=1)), STRAW, 0.3)


def c_knight(c):
    c.fill(c.mask(lambda d: d.chord([4, 3, 20, 25], 180, 360, fill=1)), STEEL, 0.3, 0.25)
    c.fill(c.mask(lambda d: d.rectangle([4, 13, 20, 20], fill=1)), STEEL, 0.1, 0.25)
    c.fill(c.mask(lambda d: d.rectangle([7, 14, 17, 15], fill=1)), hexc("#3b2a2a"))


def c_noble(c):
    c.fill(c.mask(lambda d: d.rectangle([3, 12, 20, 18], fill=1)), hexc("#dfe7ee"), 0.3, 0.25)
    for x in (4, 11, 18):
        c.fill(c.mask(lambda d: d.ellipse([x - 1, 7, x + 2, 11], fill=1)), hexc("#dfe7ee"), 0.3)
    c.fill(c.mask(lambda d: d.rectangle([10, 14, 13, 16], fill=1)), hexc("#5f9ad6"))


def c_royal(c):
    c.fill(c.mask(lambda d: d.polygon([(3, 19), (3, 7), (8, 12), (12, 4), (16, 12), (21, 7), (21, 19)], fill=1)), GOLD, 0.3, 0.25)
    c.fill(c.mask(lambda d: d.rectangle([10, 14, 13, 17], fill=1)), RED)


CLASSES = [("노예", c_slave), ("무산", c_landless), ("소작농", c_tenant), ("자영농", c_freeholder),
           ("지주·기사", c_knight), ("귀족", c_noble), ("왕족", c_royal)]


# ---------------------------------------------------------------- 집단 32px

def g_family(c):
    c.fill(c.mask(lambda d: d.polygon([(5, 4), (26, 4), (26, 16), (16, 28), (5, 16)], fill=1)), hexc("#5f9ad6"), 0.3, 0.25)
    c.fill(c.mask(lambda d: d.ellipse([10, 7, 21, 17], fill=1)), GREEN, 0.3, 0.2)
    c.fill(c.mask(lambda d: d.rectangle([15, 16, 16, 22], fill=1)), WOOD_D)


def g_tribe(c):
    c.fill(c.mask(lambda d: d.polygon([(8, 28), (10, 22), (12, 12), (17, 4), (23, 3), (22, 10), (17, 18), (11, 24)], fill=1)), hexc("#e8954a"), 0.3, 0.25)
    c.fill(c.mask(lambda d: d.line([8, 28, 21, 6], fill=1)), WOOD_D)
    c.fill(c.mask(lambda d: d.polygon([(17, 4), (23, 3), (22, 8)], fill=1)), RED)


def g_village(c):
    c.fill(c.mask(lambda d: d.rectangle([8, 15, 24, 27], fill=1)), hexc("#fdf6e6"), 0.0, 0.2)
    c.fill(c.mask(lambda d: d.polygon([(5, 16), (16, 5), (27, 16)], fill=1)), STRAW, 0.3, 0.2)
    c.fill(c.mask(lambda d: d.rectangle([14, 20, 18, 27], fill=1)), WOOD)


def g_city(c):
    c.fill(c.mask(lambda d: d.rectangle([4, 14, 27, 27], fill=1)), STONE, 0.3, 0.25)
    for x in (4, 12, 20):
        c.fill(c.mask(lambda d: d.rectangle([x, 9, x + 7, 14], fill=1)), STONE_L, 0.3, 0.2)
    c.fill(c.mask(lambda d: d.chord([12, 18, 20, 30], 180, 360, fill=1)), WOOD_D)


def g_realm(c):
    c.fill(c.mask(lambda d: d.line([8, 4, 8, 28], fill=1, width=2)), WOOD_D)
    c.fill(c.mask(lambda d: d.polygon([(10, 5), (26, 5), (22, 11), (26, 17), (10, 17)], fill=1)), RED, 0.3, 0.25)
    c.fill(c.mask(lambda d: d.polygon([(13, 13), (13, 9), (15, 11), (17, 8), (19, 11), (21, 9), (21, 13)], fill=1)), GOLD)


def g_league(c):
    c.fill(c.mask(lambda d: d.polygon([(3, 6), (16, 6), (16, 16), (10, 24), (3, 16)], fill=1)), hexc("#5f9ad6"), 0.3, 0.25)
    c.fill(c.mask(lambda d: d.polygon([(14, 9), (28, 9), (28, 19), (21, 27), (14, 19)], fill=1)), RED, 0.3, 0.25)


def g_bandit(c):
    c.fill(c.mask(lambda d: d.polygon([(3, 12), (10, 9), (16, 12), (22, 9), (29, 12), (27, 20), (19, 21), (16, 18), (13, 21), (5, 20)], fill=1)), hexc("#3b3640"), 0.25, 0.2)
    c.px[13:16, 8:12] = (255, 255, 255, 255)
    c.px[13:16, 20:24] = (255, 255, 255, 255)


def g_merc(c):
    for a, b in (((6, 26), (24, 6)), ((26, 26), (8, 6))):
        c.fill(c.mask(lambda d: d.line([a, b], fill=1, width=3)), STEEL, 0.3, 0.2)
    c.fill(c.mask(lambda d: d.ellipse([12, 18, 20, 26], fill=1)), GOLD, 0.3, 0.2)


def g_order(c):
    c.fill(c.mask(lambda d: d.polygon([(5, 4), (26, 4), (26, 16), (16, 28), (5, 16)], fill=1)), WHITE, 0.0, 0.2)
    c.fill(c.mask(lambda d: d.rectangle([14, 6, 17, 24], fill=1)), RED)
    c.fill(c.mask(lambda d: d.rectangle([8, 11, 23, 14], fill=1)), RED)


def g_revolt(c):
    c.fill(c.mask(lambda d: d.line([16, 12, 16, 29], fill=1, width=2)), WOOD)
    c.fill(c.mask(lambda d: d.rectangle([9, 11, 23, 13], fill=1)), STEEL, 0.3)
    for x in (9, 16, 22):
        c.fill(c.mask(lambda d: d.line([x, 3, x, 12], fill=1, width=2)), STEEL, 0.3)


def g_trade(c):
    c.fill(c.mask(lambda d: d.ellipse([6, 10, 26, 29], fill=1)), hexc("#c98c52"), 0.3, 0.25)
    c.fill(c.mask(lambda d: d.polygon([(11, 10), (13, 4), (19, 4), (21, 10)], fill=1)), hexc("#a26a3a"), 0.2, 0.2)
    c.fill(c.mask(lambda d: d.ellipse([12, 15, 20, 23], fill=1)), GOLD, 0.3)


def g_guild(c):
    c.fill(c.mask(lambda d: d.rectangle([4, 20, 28, 27], fill=1)), hexc("#6b655f"), 0.25, 0.25)
    c.fill(c.mask(lambda d: d.line([8, 18, 20, 6], fill=1, width=3)), WOOD)
    c.fill(c.mask(lambda d: d.polygon([(16, 4), (22, 2), (27, 8), (23, 12)], fill=1)), STEEL, 0.3, 0.2)


def g_cult(c):
    c.fill(c.mask(lambda d: d.ellipse([10, 10, 22, 22], fill=1)), GOLD, 0.3, 0.2)
    for (a, b) in (((16, 2), (16, 7)), ((16, 25), (16, 30)), ((2, 16), (7, 16)), ((25, 16), (30, 16)),
                   ((6, 6), (9, 9)), ((23, 23), (26, 26)), ((26, 6), (23, 9)), ((9, 23), (6, 26))):
        c.fill(c.mask(lambda d: d.line([a, b], fill=1, width=2)), hexc("#f2b84a"))


def g_school(c):
    c.fill(c.mask(lambda d: d.polygon([(3, 9), (15, 11), (15, 27), (3, 25)], fill=1)), CREAM, 0.0, 0.2)
    c.fill(c.mask(lambda d: d.polygon([(17, 11), (29, 9), (29, 25), (17, 27)], fill=1)), CREAM, 0.0, 0.2)
    for y in (15, 18, 21):
        c.fill(c.mask(lambda d: d.line([6, y, 12, y + 1], fill=1)), hexc("#a08060"))
        c.fill(c.mask(lambda d: d.line([20, y + 1, 26, y], fill=1)), hexc("#a08060"))


def g_crime(c):
    c.fill(c.mask(lambda d: d.polygon([(22, 3), (25, 6), (13, 20), (10, 17)], fill=1)), STEEL, 0.35, 0.25)
    c.fill(c.mask(lambda d: d.line([8, 15, 15, 22], fill=1, width=2)), hexc("#6b655f"))
    c.fill(c.mask(lambda d: d.line([5, 27, 11, 21], fill=1, width=3)), hexc("#3b3640"))


def g_cabal(c):
    c.fill(c.mask(lambda d: d.polygon([(16, 3), (29, 27), (3, 27)], fill=1)), hexc("#7a3fb3"), 0.3, 0.25)
    c.fill(c.mask(lambda d: d.ellipse([10, 15, 22, 23], fill=1)), WHITE)
    c.fill(c.mask(lambda d: d.ellipse([14, 16, 18, 22], fill=1)), hexc("#3b2a2a"))


def g_faction(c):
    c.fill(c.mask(lambda d: d.line([8, 4, 8, 28], fill=1, width=2)), WOOD_D)
    c.fill(c.mask(lambda d: d.polygon([(10, 5), (18, 5), (18, 17), (10, 17)], fill=1)), hexc("#5f9ad6"), 0.3, 0.2)
    c.fill(c.mask(lambda d: d.polygon([(19, 7), (27, 5), (27, 17), (19, 19)], fill=1)), RED, 0.3, 0.2)


GROUPS = [("가문", g_family), ("부족", g_tribe), ("마을", g_village), ("자치 도시", g_city), ("나라", g_realm),
          ("연맹", g_league), ("도적단", g_bandit), ("용병단", g_merc), ("기사단", g_order), ("봉기군", g_revolt),
          ("상단", g_trade), ("장인 조합", g_guild), ("교단", g_cult), ("학파", g_school), ("범죄 조직", g_crime),
          ("비밀결사", g_cabal), ("파벌", g_faction)]


def atlas(entries, size):
    cols = 8
    rows = (len(entries) + cols - 1) // cols
    a = np.zeros((rows * size, cols * size, 4), dtype=np.uint8)
    idx = {}
    for k, (name, fn) in enumerate(entries):
        px = icon(size, fn)
        x, y = (k % cols) * size, (k // cols) * size
        a[y:y + size, x:x + size] = px
        idx[name] = k
    return a, idx


# ---------------------------------------------------------------- UI 틀

def rounded_panel(w, h, fill, border, r=4, bw=3):
    c = Canvas(w, h)
    c.fill(c.mask(lambda d: d.rounded_rectangle([0, 0, w - 1, h - 1], r, fill=1)), OUTLINE)
    c.fill(c.mask(lambda d: d.rounded_rectangle([1, 1, w - 2, h - 2], r - 1, fill=1)), border, 0.25, 0.2)
    c.fill(c.mask(lambda d: d.rounded_rectangle([bw, bw, w - 1 - bw, h - 1 - bw], max(1, r - 2), fill=1)), fill, 0.0, 0.0)
    for x in range(bw + 1, w - bw - 1):
        c.put(x, bw, shade(fill, 0.4))
    return c.px


def frame(color, gem=None):
    c = Canvas(64, 64)
    c.fill(c.mask(lambda d: d.rectangle([0, 0, 63, 63], fill=1)), OUTLINE)
    c.fill(c.mask(lambda d: d.rectangle([1, 1, 62, 62], fill=1)), color, 0.3, 0.25)
    c.fill(c.mask(lambda d: d.rectangle([7, 7, 56, 56], fill=1)), OUTLINE)
    c.px[8:56, 8:56] = 0
    if gem:
        for x, y in ((31, 2), (2, 31), (60, 31), (31, 60)):
            c.fill(c.mask(lambda d: d.rectangle([x - 1, y - 1, x + 2, y + 2], fill=1)), gem, 0.4)
    return c.px


def cursor(interact=False):
    c = Canvas(32, 32)
    c.fill(c.mask(lambda d: d.polygon([(1, 1), (1, 20), (6, 15), (10, 23), (13, 22), (9, 14), (16, 14)], fill=1)), WHITE, 0.0, 0.15)
    if interact:
        for (x, y) in ((22, 6), (26, 10), (22, 14)):
            c.fill(c.mask(lambda d: d.rectangle([x - 1, y, x + 1, y], fill=1)), GOLD)
            c.fill(c.mask(lambda d: d.rectangle([x, y - 1, x, y + 1], fill=1)), GOLD)
    c.outline()
    return c.px


def save(px, name):
    Image.fromarray(px, "RGBA").save(os.path.join(UI, name))


def main():
    os.makedirs(UI, exist_ok=True)
    meta = {}
    for name, entries, size in (("icons_items", ITEMS, 32), ("icons_status", STATUS, 24), ("icons_class", CLASSES, 24),
                                ("icons_group", GROUPS, 32)):
        a, idx = atlas(entries, size)
        save(a, name + ".png")
        meta[name] = {"cell": size, "columns": 8, "index": idx}
    save(rounded_panel(48, 48, CREAM, WOOD_L), "panel_light.png")
    save(rounded_panel(48, 48, hexc("#8a5a36"), WOOD_D), "panel_dark.png")
    save(rounded_panel(48, 24, hexc("#ffe98a"), WOOD, r=4, bw=2), "button_normal.png")
    save(rounded_panel(48, 24, hexc("#f2cf5a"), WOOD_D, r=4, bw=2), "button_pressed.png")
    save(rounded_panel(48, 24, hexc("#e2ddd4"), hexc("#a8a29a"), r=4, bw=2), "button_disabled.png")
    save(frame(WOOD), "frame_commoner.png")
    save(frame(hexc("#dfe7ee"), hexc("#5f9ad6")), "frame_noble.png")
    save(frame(GOLD, RED), "frame_royal.png")
    save(cursor(False), "cursor_default.png")
    save(cursor(True), "cursor_interact.png")
    save(rounded_panel(32, 8, hexc("#5a4040"), hexc("#3b2a2a"), r=2, bw=1), "bar_bg.png")
    save(rounded_panel(32, 8, hexc("#8fd16a"), hexc("#4f9e3f"), r=2, bw=1), "bar_fill.png")
    meta["nine_slice"] = {"panel": 16, "button": 8, "bar": 3}
    json.dump(meta, open(os.path.join(ROOT, "data", "visual", "ui_atlas.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("아이콘", len(ITEMS) + len(STATUS) + len(CLASSES) + len(GROUPS), "개, UI 틀 12장")


if __name__ == "__main__":
    main()
